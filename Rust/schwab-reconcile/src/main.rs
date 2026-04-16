use anyhow::{Context, Result};
use clap::Parser;
use serde::Deserialize;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Reconcile Schwab positions against balance data using live Yahoo Finance prices.
#[derive(Parser, Debug)]
#[command(name = "schwab-reconcile")]
struct Args {
    /// Base Schwab brokerage data directory
    #[arg(long, default_value = "~/.openclaw/workspace/Data/Private/finance/schwab-brokerage")]
    base_dir: String,

    /// Use snapshot prices from CSV instead of fetching live prices
    #[arg(long, default_value_t = false)]
    offline: bool,
}

// ── CSV row ───────────────────────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
struct PositionRow {
    #[serde(rename = "Symbol")]
    symbol: String,
    #[serde(rename = "Qty (Quantity)")]
    qty: String,
    #[serde(rename = "Price")]
    price: String,
    #[serde(rename = "Mkt Val (Market Value)")]
    mkt_val: String,
    #[serde(rename = "Cost Basis")]
    cost_basis: String,
    #[serde(rename = "Asset Type")]
    asset_type: String,
}

// ── helpers ───────────────────────────────────────────────────────────────────

fn parse_dollar(s: &str) -> Option<f64> {
    let clean: String = s.trim_matches('"').trim()
        .replace('$', "").replace('%', "").replace(',', "");
    if clean == "--" || clean.is_empty() { return None; }
    clean.parse().ok()
}

fn is_summary_row(sym: &str) -> bool {
    let s = sym.trim().to_lowercase();
    s == "positions total" || s == "total"
}

// ── Position ──────────────────────────────────────────────────────────────────

struct Position {
    symbol: String,
    qty: Option<f64>,
    snap_price: Option<f64>,
    snap_mv: Option<f64>,
    cost_basis: Option<f64>,
    is_cash: bool,
}

fn read_positions(positions_dir: &Path) -> Result<Vec<Position>> {
    let mut files: Vec<PathBuf> = std::fs::read_dir(positions_dir)?
        .filter_map(|e| e.ok()).map(|e| e.path())
        .filter(|p| p.extension().map_or(false, |e| e.eq_ignore_ascii_case("csv"))
            && !p.file_name().unwrap_or_default().to_string_lossy().to_lowercase().contains("master"))
        .collect();
    files.sort();
    let path = files.last().context("No positions CSV found")?;
    eprintln!("Positions: {}", path.display());

    let content = std::fs::read_to_string(path)?;
    let mut lines = content.lines();
    let meta = lines.next().unwrap_or("").trim_matches('"');
    eprintln!("Snapshot: {meta}");

    // skip blank lines to find header
    let header_line = loop {
        match lines.next() {
            None => anyhow::bail!("no header in positions CSV"),
            Some(l) if l.trim().is_empty() => continue,
            Some(l) => break l.to_string(),
        }
    };
    let remaining = std::iter::once(header_line.as_str()).chain(lines)
        .collect::<Vec<_>>().join("\n");

    let mut rdr = csv::ReaderBuilder::new().has_headers(true).trim(csv::Trim::All)
        .from_reader(remaining.as_bytes());

    let mut out = Vec::new();
    for row in rdr.deserialize::<PositionRow>().flatten() {
        if is_summary_row(&row.symbol) { continue; }
        let is_cash = row.asset_type.to_lowercase().contains("cash")
            || row.symbol == "Cash & Cash Investments"
            || row.qty.trim() == "--";
        out.push(Position {
            symbol: row.symbol,
            qty: parse_dollar(&row.qty),
            snap_price: parse_dollar(&row.price),
            snap_mv: parse_dollar(&row.mkt_val),
            cost_basis: parse_dollar(&row.cost_basis),
            is_cash,
        });
    }
    eprintln!("Loaded {} rows ({} securities, {} cash/other)",
        out.len(),
        out.iter().filter(|p| !p.is_cash).count(),
        out.iter().filter(|p| p.is_cash).count());
    Ok(out)
}

// ── Balances CSV ──────────────────────────────────────────────────────────────

struct Balances {
    account_value: f64,
    cash: f64,
    securities_mv: f64,
    day_change: f64,
    snapshot_label: String,
}

fn read_balances(balances_dir: &Path) -> Result<Balances> {
    let mut files: Vec<PathBuf> = std::fs::read_dir(balances_dir)?
        .filter_map(|e| e.ok()).map(|e| e.path())
        .filter(|p| p.extension().map_or(false, |e| e.eq_ignore_ascii_case("csv")))
        .collect();
    files.sort();
    let path = files.last().context("No balances CSV found")?;
    eprintln!("Balances: {}", path.display());

    let content = std::fs::read_to_string(path)?;
    let mut account_value = 0.0_f64;
    let mut cash = 0.0_f64;
    let mut securities_mv = 0.0_f64;
    let mut day_change = 0.0_f64;
    let mut snapshot_label = String::new();

    for line in content.lines() {
        let l = line.trim();
        if l.is_empty() { continue; }
        if l.starts_with('"') && !l.contains(',') {
            snapshot_label = l.trim_matches('"').to_string();
            continue;
        }
        let parts: Vec<&str> = l.splitn(2, ',').collect();
        if parts.len() < 2 { continue; }
        let key = parts[0].trim_matches('"').trim().to_lowercase();
        let val = parts[1].trim_matches('"').trim();
        match key.as_str() {
            "account value" => { account_value = parse_dollar(val).unwrap_or(0.0); }
            "day change"    => { day_change = parse_dollar(val).unwrap_or(0.0); }
            "cash & cash investments" if cash == 0.0 => { cash = parse_dollar(val).unwrap_or(0.0); }
            "market value"  if securities_mv == 0.0  => { securities_mv = parse_dollar(val).unwrap_or(0.0); }
            _ => {}
        }
    }
    Ok(Balances { account_value, cash, securities_mv, day_change, snapshot_label })
}

// ── Yahoo Finance ─────────────────────────────────────────────────────────────

#[derive(Deserialize)]
struct YfResponse { #[serde(rename = "quoteResponse")] qr: YfResult }
#[derive(Deserialize)]
struct YfResult { result: Vec<YfQuote> }
#[derive(Deserialize)]
struct YfQuote {
    symbol: String,
    #[serde(rename = "regularMarketPrice")] price: Option<f64>,
}

fn schwab_to_yahoo(s: &str) -> Option<String> {
    let s = s.trim();
    if s.is_empty() || s == "--" || s.starts_with("Cash") { return None; }
    Some(s.replace('/', "-"))
}

fn build_client() -> Result<reqwest::blocking::Client> {
    Ok(reqwest::blocking::Client::builder()
        .user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        .cookie_store(true)
        .timeout(std::time::Duration::from_secs(30))
        .build()?)
}

fn fetch_crumb(client: &reqwest::blocking::Client) -> Result<String> {
    // Step 1: visit Yahoo Finance to set session cookies
    client.get("https://finance.yahoo.com/")
        .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        .header("Accept-Language", "en-US,en;q=0.9")
        .send()
        .context("Failed to fetch Yahoo Finance homepage")?;

    // Step 2: fetch crumb token
    let crumb = client
        .get("https://query1.finance.yahoo.com/v1/test/getcrumb")
        .header("Accept", "text/plain")
        .send()
        .context("Failed to fetch Yahoo Finance crumb")?
        .text()
        .context("Failed to read crumb response")?;

    if crumb.is_empty() || crumb.contains("Unauthorized") {
        anyhow::bail!("Empty or unauthorized crumb response: {:?}", crumb);
    }
    Ok(crumb.trim().to_string())
}

fn fetch_prices(symbols: &[String]) -> Result<HashMap<String, f64>> {
    let yahoo: Vec<String> = symbols.iter().filter_map(|s| schwab_to_yahoo(s)).collect();
    if yahoo.is_empty() { return Ok(HashMap::new()); }

    let client = build_client()?;
    let crumb = fetch_crumb(&client)?;
    eprintln!("Got Yahoo crumb (len={})", crumb.len());

    // Batch in chunks of 100 to avoid URL length limits
    let mut map = HashMap::new();
    for chunk in yahoo.chunks(100) {
        let url = format!(
            "https://query1.finance.yahoo.com/v7/finance/quote?symbols={}&crumb={}&fields=regularMarketPrice",
            chunk.join(","),
            urlencoding::encode(&crumb),
        );
        let body: YfResponse = client.get(&url)
            .header("Accept", "application/json")
            .send()
            .context("Yahoo Finance quote request failed")?
            .json()
            .context("Failed to parse Yahoo Finance quote response")?;
        for q in body.qr.result {
            if let Some(p) = q.price {
                let schwab_sym = q.symbol.replace('-', "/");
                map.insert(q.symbol.clone(), p);
                if schwab_sym != q.symbol { map.insert(schwab_sym, p); }
            }
        }
    }
    Ok(map)
}

// ── Main ──────────────────────────────────────────────────────────────────────

fn run(args: &Args) -> Result<()> {
    let base = PathBuf::from(shellexpand::tilde(&args.base_dir).as_ref());
    let balances = read_balances(&base.join("balances"))?;
    let positions = read_positions(&base.join("positions"))?;

    let live: HashMap<String, f64> = if args.offline {
        eprintln!("Offline mode — using snapshot prices");
        HashMap::new()
    } else {
        eprintln!("Fetching live prices…");
        let syms: Vec<String> = positions.iter().filter(|p| !p.is_cash)
            .map(|p| p.symbol.clone()).collect();
        match fetch_prices(&syms) {
            Ok(m) => { eprintln!("Prices received: {}/{}", m.len(), syms.len()); m }
            Err(e) => { eprintln!("Price fetch failed: {e} — using snapshot prices"); HashMap::new() }
        }
    };

    // Compute
    let mut sec_mv = 0.0_f64;
    let mut cash_mv = 0.0_f64;
    let mut no_price: Vec<String> = Vec::new();
    let mut drifters: Vec<String> = Vec::new();

    println!("\n{:<12} {:>8} {:>10} {:>10} {:>12} {:>12}",
        "Symbol", "Qty", "SnapPrice", "LivePrice", "ComputedMV", "SnapMV");
    println!("{}", "─".repeat(68));

    for p in &positions {
        if p.is_cash {
            let v = p.snap_mv.unwrap_or(0.0);
            cash_mv += v;
            println!("{:<12} {:>8} {:>10} {:>10} {:>12.2} {:>12.2}",
                p.symbol, "--", "--", "cash", v, v);
            continue;
        }
        let qty = p.qty.unwrap_or(0.0);
        let snap = p.snap_price.unwrap_or(0.0);
        let snap_mv_val = p.snap_mv.unwrap_or(snap * qty);
        let live_opt = live.get(&p.symbol).copied();
        let eff = live_opt.unwrap_or(snap);
        let computed = qty * eff;
        sec_mv += computed;

        if live_opt.is_none() && !args.offline { no_price.push(p.symbol.clone()); }
        if let Some(lp) = live_opt {
            if snap > 0.0 && ((lp - snap) / snap).abs() > 0.02 {
                drifters.push(format!("  {}: snap={:.2} live={:.2} ({:+.1}%)",
                    p.symbol, snap, lp, (lp - snap) / snap * 100.0));
            }
        }

        println!("{:<12} {:>8.2} {:>10.2} {:>10} {:>12.2} {:>12.2}",
            p.symbol, qty, snap,
            live_opt.map(|v| format!("{v:.2}")).unwrap_or("--".into()),
            computed, snap_mv_val);
    }

    let total = sec_mv + cash_mv;
    let diff_total = total - balances.account_value;
    let diff_sec   = sec_mv - balances.securities_mv;
    let diff_cash  = cash_mv - balances.cash;
    let tol = 50.0_f64;
    let status = if diff_total.abs() < tol { "✓ MATCH" } else { "✗ MISMATCH" };

    println!("\n{}", "═".repeat(68));
    println!("  {}", balances.snapshot_label);
    println!("{}", "═".repeat(68));
    println!("{:<38} {:>14}", "Schwab account value:", format!("${:.2}", balances.account_value));
    println!("{:<38} {:>14}", "  Cash & cash investments:", format!("${:.2}", balances.cash));
    println!("{:<38} {:>14}", "  Securities market value:", format!("${:.2}", balances.securities_mv));
    println!("{}", "─".repeat(52));
    println!("{:<38} {:>14}", "Computed securities MV (live prices):", format!("${:.2}", sec_mv));
    println!("{:<38} {:>14}", "Computed cash:", format!("${:.2}", cash_mv));
    println!("{:<38} {:>14}", "Computed total:", format!("${:.2}", total));
    println!("{}", "─".repeat(52));
    println!("{:<38} {:>14}  {}", "Difference (computed − Schwab):", format!("{:+.2}", diff_total), status);
    println!("{:<38} {:>14}", "  Securities diff:", format!("{:+.2}", diff_sec));
    println!("{:<38} {:>14}", "  Cash diff:", format!("{:+.2}", diff_cash));
    println!("{:<38} {:>14}", "Schwab day change:", format!("${:.2}", balances.day_change));

    if !drifters.is_empty() {
        println!("\n⚠  Price drift >2% vs snapshot (after-hours movement):");
        for d in &drifters { println!("{d}"); }
    }
    if !no_price.is_empty() {
        println!("\n⚠  No live price for {} symbol(s); used snapshot:", no_price.len());
        println!("   {}", no_price.join(", "));
    }

    Ok(())
}

fn main() {
    let args = Args::parse();
    if let Err(e) = run(&args) {
        eprintln!("Error: {e:#}");
        std::process::exit(1);
    }
}
