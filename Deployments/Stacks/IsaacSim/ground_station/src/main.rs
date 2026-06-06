//! Ground Station — Starship Mission Control
//! Runs on the desktop (x86_64).
//!
//! Listens UDP :55055 for FSW AI decisions transmitted by fsw_orin on the
//! Jetson Orin Nano. Displays a formatted mission-control readout.
//!
//! Usage: ground_station [BIND_PORT]  (default 55055)

use std::net::UdpSocket;
use std::time::{SystemTime, UNIX_EPOCH};

const DEFAULT_PORT: u16 = 55055;

const RED:    &str = "\x1b[1;31m";
const YELLOW: &str = "\x1b[1;33m";
const CYAN:   &str = "\x1b[1;36m";
const GREEN:  &str = "\x1b[1;32m";
const BOLD:   &str = "\x1b[1m";
const DIM:    &str = "\x1b[2m";
const RESET:  &str = "\x1b[0m";

fn wall_clock_hms() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let s = secs % 86400;
    format!("{:02}:{:02}:{:02}", s / 3600, (s % 3600) / 60, s % 60)
}

fn rule_color(rule: &str) -> &'static str {
    match rule {
        "ALTITUDE_ABORT" => RED,
        _ => YELLOW,
    }
}

fn print_banner(port: u16) {
    println!();
    println!("{BOLD}╔══════════════════════════════════════════════════════════════╗");
    println!("║       STARSHIP MISSION CONTROL — FSW AI UPLINK               ║");
    println!("║       Listening UDP :{port:<5}  (Jetson Orin Nano → Desktop)     ║");
    println!("╚══════════════════════════════════════════════════════════════╝{RESET}");
    println!();
    println!("{DIM}  Waiting for FSW decisions from Jetson Orin Nano…{RESET}");
    println!();
}

fn main() {
    let port: u16 = std::env::args()
        .nth(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(DEFAULT_PORT);

    print_banner(port);

    let sock = UdpSocket::bind(("0.0.0.0", port))
        .unwrap_or_else(|e| { eprintln!("bind :{port} failed: {e}"); std::process::exit(1) });

    let mut buf    = vec![0u8; 8192];
    let mut count  = 0u64;

    loop {
        match sock.recv_from(&mut buf) {
            Err(e) => { eprintln!("recv error: {e}"); continue; }
            Ok((n, src)) => {
                let raw = match std::str::from_utf8(&buf[..n]) {
                    Ok(s)  => s,
                    Err(_) => { eprintln!("[warn] non-UTF8 packet from {src}"); continue; }
                };

                let j: serde_json::Value = match serde_json::from_str(raw) {
                    Ok(v)  => v,
                    Err(e) => { eprintln!("[warn] JSON parse error: {e}"); continue; }
                };

                count += 1;
                let time_str = wall_clock_hms();
                let rule     = j["rule"].as_str().unwrap_or("UNKNOWN");
                let rc       = rule_color(rule);

                println!("{BOLD}┌─ [{time_str}] 📡 FSW UPLINK #{count}  ←  {src} ─────────────────────────{RESET}");

                // Rule
                println!("│  {rc}{BOLD}RULE      {RESET}  {rc}{BOLD}{rule}{RESET}");

                // Telemetry snapshot
                let t = &j["telemetry"];
                println!(
                    "│  {BOLD}TELEMETRY{RESET}   alt={:.1}m  vy={:.2}m/s  \
                     att_err={:.1}°  spin={:.3}rad/s",
                    t["altitude_m"].as_f64().unwrap_or(0.0),
                    t["vy_mps"].as_f64().unwrap_or(0.0),
                    t["att_err_deg"].as_f64().unwrap_or(0.0),
                    t["spin_rads"].as_f64().unwrap_or(0.0),
                );

                // Sim time + seq
                println!(
                    "│  {DIM}sim_time={:.3}s   seq={}   source={}{RESET}",
                    j["sim_time"].as_f64().unwrap_or(0.0),
                    j["jetson_seq"].as_u64().unwrap_or(0),
                    j["source"].as_str().unwrap_or("?"),
                );

                // Reasoning (thinking chain)
                if let Some(reasoning) = j["reasoning"].as_str() {
                    if !reasoning.is_empty() {
                        let preview = if reasoning.len() > 220 {
                            format!("{}…", &reasoning[..220])
                        } else {
                            reasoning.to_string()
                        };
                        println!("│");
                        println!("│  {CYAN}{BOLD}AI THINKS{RESET}  {CYAN}{preview}{RESET}");
                    }
                }

                // Decision
                let decision = j["decision"].as_str().unwrap_or("(no decision)");
                let llm_secs = j["llm_secs"].as_f64().unwrap_or(0.0);
                println!("│");
                println!("│  {GREEN}{BOLD}DECISION  {RESET}  {GREEN}{BOLD}{decision}{RESET}");
                println!("│  {DIM}inference: {llm_secs:.1}s on Jetson Orin Nano (Qwen3.5-2B Q4_K_M){RESET}");
                println!("└─────────────────────────────────────────────────────────────────────\n");
            }
        }
    }
}
