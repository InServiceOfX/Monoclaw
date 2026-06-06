//! FSW Orin — Starship Flight Software AI
//! Runs on Jetson Orin Nano (aarch64).
//!
//! 1. Receives 64-byte UDP telemetry from Isaac Sim (:50505)
//! 2. Evaluates deterministic FSW rules in real time
//! 3. On anomaly: queries Qwen3.5-2B via llama-server (localhost:8080)
//! 4. Transmits FSW decision JSON to ground station via UDP (:55055)
//!
//! Usage: fsw_orin [GROUND_STATION_IP]
//!   default GS IP: 192.168.86.91 (desktop wired)

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream, UdpSocket};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

// ── Network ───────────────────────────────────────────────────────────────
const TELEMETRY_PORT: u16  = 50505;
const GS_PORT: u16         = 55055;
const CMD_PORT: u16        = 8083;   // FSW command server (desktop → Jetson)
const ISAAC_API_PORT: u16  = 8282;
const LLAMA_URL: &str      = "http://127.0.0.1:8080/v1/chat/completions";

// ── FSW rule thresholds ───────────────────────────────────────────────────
const ALTITUDE_ABORT_M:     f32 = 100.0; // fires on descent below 100m AGL
const DESCENT_ABORT_MPS:    f32 = -2.0;
const ATTITUDE_ANOMALY_DEG: f32 = 45.0;
const SPIN_ANOMALY_RADS:    f32 = 1.0;

// ── LLM rate limiting ─────────────────────────────────────────────────────
const LLM_COOLDOWN_SECS: f64 = 8.0;

// ── Packet ────────────────────────────────────────────────────────────────
const PACKET_SIZE: usize = 64;

// ── ANSI ──────────────────────────────────────────────────────────────────
const RED:    &str = "\x1b[1;31m";
const YELLOW: &str = "\x1b[1;33m";
const CYAN:   &str = "\x1b[1;36m";
const GREEN:  &str = "\x1b[1;32m";
const BOLD:   &str = "\x1b[1m";
const RESET:  &str = "\x1b[0m";

// ── Telemetry frame ───────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy)]
struct TelemetryFrame {
    seq: u32, sim_time: f64,
    x: f32, y: f32, z: f32,
    qw: f32, qx: f32, qy: f32, qz: f32,
    vx: f32, vy: f32, vz: f32,
    wx: f32, wy: f32, wz: f32,
}

impl TelemetryFrame {
    fn from_bytes(b: &[u8; PACKET_SIZE]) -> Self {
        Self {
            seq:      u32::from_le_bytes(b[0..4].try_into().unwrap()),
            sim_time: f64::from_le_bytes(b[4..12].try_into().unwrap()),
            x:        f32::from_le_bytes(b[12..16].try_into().unwrap()),
            y:        f32::from_le_bytes(b[16..20].try_into().unwrap()),
            z:        f32::from_le_bytes(b[20..24].try_into().unwrap()),
            qw:       f32::from_le_bytes(b[24..28].try_into().unwrap()),
            qx:       f32::from_le_bytes(b[28..32].try_into().unwrap()),
            qy:       f32::from_le_bytes(b[32..36].try_into().unwrap()),
            qz:       f32::from_le_bytes(b[36..40].try_into().unwrap()),
            vx:       f32::from_le_bytes(b[40..44].try_into().unwrap()),
            vy:       f32::from_le_bytes(b[44..48].try_into().unwrap()),
            vz:       f32::from_le_bytes(b[48..52].try_into().unwrap()),
            wx:       f32::from_le_bytes(b[52..56].try_into().unwrap()),
            wy:       f32::from_le_bytes(b[56..60].try_into().unwrap()),
            wz:       f32::from_le_bytes(b[60..64].try_into().unwrap()),
        }
    }

    fn attitude_error_deg(&self) -> f32 {
        2.0 * self.qw.abs().min(1.0).acos() * 180.0 / std::f32::consts::PI
    }

    fn spin_rate_rads(&self) -> f32 {
        (self.wx * self.wx + self.wy * self.wy + self.wz * self.wz).sqrt()
    }
}

// ── FSW rules ─────────────────────────────────────────────────────────────

fn check_fsw(f: &TelemetryFrame, att: f32, spin: f32) -> Option<&'static str> {
    if f.y < ALTITUDE_ABORT_M && f.vy < DESCENT_ABORT_MPS {
        return Some("ALTITUDE_ABORT");
    }
    if att > ATTITUDE_ANOMALY_DEG {
        return Some("ATTITUDE_ANOMALY");
    }
    if spin > SPIN_ANOMALY_RADS {
        return Some("SPIN_ANOMALY");
    }
    None
}

// ── LLM query (blocking, runs in spawned thread) ──────────────────────────

#[derive(Clone)]
struct FswAlert {
    rule:        &'static str,
    frame:       TelemetryFrame,
    att_err_deg: f32,
    spin_rads:   f32,
}

fn query_llm(alert: &FswAlert) -> Option<(String, String, f64)> {
    let t0  = Instant::now();
    let f   = &alert.frame;

    let user_msg = format!(
        "FSW ALERT — rule={rule}  altitude={alt:.1}m  vy={vy:.2}m/s  \
         attitude_error={att:.1}°  spin={spin:.3}rad/s  sim_time={st:.3}s\n\
         State your FSW action in one sentence.",
        rule = alert.rule,
        alt  = f.y,
        vy   = f.vy,
        att  = alert.att_err_deg,
        spin = alert.spin_rads,
        st   = f.sim_time,
    );

    let body = serde_json::json!({
        "model": "qwen",
        "messages": [
            {
                "role": "system",
                "content": "You are the onboard Flight Software AI on Starship. \
                           Deterministic FSW rules already fired. \
                           Give your FSW action command in ONE sentence. Be direct."
            },
            { "role": "user", "content": user_msg }
        ],
        "max_tokens": 400,
        "stream": false
    });

    let resp = ureq::post(LLAMA_URL)
        .timeout(Duration::from_secs(20))
        .set("Content-Type", "application/json")
        .send_string(&body.to_string())
        .ok()?;

    let json: serde_json::Value = resp.into_json().ok()?;

    let reasoning = json["choices"][0]["message"]["reasoning_content"]
        .as_str().unwrap_or("").to_string();
    let decision = json["choices"][0]["message"]["content"]
        .as_str().unwrap_or("").to_string();

    Some((reasoning, decision, t0.elapsed().as_secs_f64()))
}

// ── Ground station uplink ─────────────────────────────────────────────────

fn unix_now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64()
}

fn transmit_decision(
    sock:      &UdpSocket,
    gs_addr:   &str,
    alert:     &FswAlert,
    reasoning: &str,
    decision:  &str,
    llm_secs:  f64,
) {
    let f = &alert.frame;
    let reasoning_trimmed = if reasoning.len() > 600 {
        format!("{}…", &reasoning[..600])
    } else {
        reasoning.to_string()
    };

    let packet = serde_json::json!({
        "timestamp":  unix_now(),
        "jetson_seq": f.seq,
        "sim_time":   f.sim_time,
        "rule":       alert.rule,
        "telemetry": {
            "altitude_m":  f.y,
            "vy_mps":      f.vy,
            "att_err_deg": alert.att_err_deg,
            "spin_rads":   alert.spin_rads,
            "pos":         [f.x, f.y, f.z],
            "vel":         [f.vx, f.vy, f.vz],
        },
        "reasoning": reasoning_trimmed,
        "decision":  decision,
        "llm_secs":  llm_secs,
        "source":    "jetson-orin-nano"
    });

    let payload = packet.to_string();
    match sock.send_to(payload.as_bytes(), gs_addr) {
        Ok(_)  => println!("{GREEN}[↑ GS] decision transmitted → {gs_addr}{RESET}"),
        Err(e) => eprintln!("[fsw_orin] GS transmit error: {e}"),
    }
}

// ── Banner ────────────────────────────────────────────────────────────────

fn print_banner(gs_addr: &str) {
    println!("╔══════════════════════════════════════════════════════════╗");
    println!("║  FSW Orin — Starship Flight Software AI                 ║");
    println!("║  Jetson Orin Nano  │  telemetry :{}  │  LLM :8080  ║", TELEMETRY_PORT);
    println!("║  Ground station uplink → {:<33}║", gs_addr);
    println!("╠══════════════════════════════════════════════════════════╣");
    println!("║  Rules:                                                  ║");
    println!("║    ALTITUDE_ABORT   y < {:.0}m  AND  vy < {:.0}m/s         ║",
             ALTITUDE_ABORT_M, DESCENT_ABORT_MPS);
    println!("║    ATTITUDE_ANOMALY tilt > {:.0}°                          ║",
             ATTITUDE_ANOMALY_DEG);
    println!("║    SPIN_ANOMALY     |ω| > {:.0} rad/s                     ║",
             SPIN_ANOMALY_RADS);
    println!("╚══════════════════════════════════════════════════════════╝\n");
}

// ── FSW Command Server (desktop → Jetson) ────────────────────────────────

fn fsw_validate(action: &str) -> Result<(), &'static str> {
    match action {
        "liftoff" | "abort" | "safe_mode" | "reset_position" => Ok(()),
        _ => Err("unknown FSW action"),
    }
}

fn handle_cmd_stream(mut stream: TcpStream, isaac_host: &str) {
    stream.set_read_timeout(Some(Duration::from_secs(5))).ok();
    let mut buf = vec![0u8; 4096];
    let n = match stream.read(&mut buf) { Ok(n) => n, Err(_) => return };
    let req = String::from_utf8_lossy(&buf[..n]);

    // CORS preflight
    if req.starts_with("OPTIONS") {
        let _ = stream.write_all(
            b"HTTP/1.1 204 No Content\r\nAccess-Control-Allow-Origin: *\r\n\
              Access-Control-Allow-Methods: POST, OPTIONS\r\n\
              Access-Control-Allow-Headers: Content-Type\r\n\r\n"
        );
        return;
    }

    let body_str = req.find("\r\n\r\n")
        .map(|p| req[p + 4..].trim().to_string())
        .unwrap_or_default();

    let cmd: serde_json::Value = match serde_json::from_str(&body_str) {
        Ok(v) => v,
        Err(_) => {
            let _ = stream.write_all(
                b"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n\
                  Access-Control-Allow-Origin: *\r\n\r\n{\"error\":\"invalid JSON\"}"
            );
            return;
        }
    };

    let action = cmd["action"].as_str().unwrap_or("").to_string();

    match fsw_validate(&action) {
        Err(reason) => {
            println!("{YELLOW}[CMD] FSW rejected '{action}': {reason}{RESET}");
            let resp = format!(
                "HTTP/1.1 403 Forbidden\r\nContent-Type: application/json\r\n\
                 Access-Control-Allow-Origin: *\r\n\r\n\
                 {{\"status\":\"rejected\",\"reason\":\"{reason}\"}}"
            );
            let _ = stream.write_all(resp.as_bytes());
        }
        Ok(()) => {
            println!("{CYAN}[CMD] FSW validated '{action}' → forwarding to Isaac Sim{RESET}");
            let url = format!("http://{}:{}/starship/command", isaac_host, ISAAC_API_PORT);
            match ureq::post(&url)
                .timeout(Duration::from_secs(6))
                .set("Content-Type", "application/json")
                .send_string(&cmd.to_string())
            {
                Ok(r) => {
                    let body = r.into_string().unwrap_or_default();
                    println!("{GREEN}[CMD] '{action}' forwarded OK: {body}{RESET}");
                    let resp = format!(
                        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\
                         Access-Control-Allow-Origin: *\r\n\r\n\
                         {{\"status\":\"ok\",\"action\":\"{action}\",\"fsw\":\"validated\",\"isaac\":{body}}}"
                    );
                    let _ = stream.write_all(resp.as_bytes());
                }
                Err(e) => {
                    println!("{YELLOW}[CMD] Isaac Sim unreachable: {e}{RESET}");
                    let resp = format!(
                        "HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\n\
                         Access-Control-Allow-Origin: *\r\n\r\n\
                         {{\"status\":\"error\",\"reason\":\"Isaac Sim unreachable\"}}"
                    );
                    let _ = stream.write_all(resp.as_bytes());
                }
            }
        }
    }
}

fn spawn_command_server(isaac_host: String) {
    thread::spawn(move || {
        let listener = match TcpListener::bind(format!("0.0.0.0:{CMD_PORT}")) {
            Ok(l) => l,
            Err(e) => { eprintln!("[CMD] bind failed: {e}"); return; }
        };
        println!("{BOLD}[CMD] FSW command server :{CMD_PORT} (desktop → Jetson){RESET}");
        for stream in listener.incoming().flatten() {
            let host = isaac_host.clone();
            thread::spawn(move || handle_cmd_stream(stream, &host));
        }
    });
}

// ── Main ──────────────────────────────────────────────────────────────────

fn main() {
    let gs_host = std::env::args().nth(1)
        .unwrap_or_else(|| "192.168.86.91".to_string());
    let gs_addr = format!("{gs_host}:{GS_PORT}");

    print_banner(&gs_addr);
    spawn_command_server(gs_host.clone());

    let recv_sock = UdpSocket::bind(("0.0.0.0", TELEMETRY_PORT))
        .unwrap_or_else(|e| { eprintln!("bind :{TELEMETRY_PORT} failed: {e}"); std::process::exit(1) });
    recv_sock.set_read_timeout(Some(Duration::from_secs(5))).unwrap();

    let send_sock = UdpSocket::bind("0.0.0.0:0").expect("send socket bind failed");

    let last_llm_time: Arc<Mutex<f64>> = Arc::new(Mutex::new(0.0));
    let mut buf       = [0u8; 256];
    let mut last_seq: Option<u32> = None;
    let mut total_pkts  = 0u64;
    let mut total_drops = 0u64;

    loop {
        match recv_sock.recv_from(&mut buf) {
            Err(e) if matches!(e.kind(),
                std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut) => {
                eprintln!("  [waiting for Isaac Sim telemetry on :{TELEMETRY_PORT}…]");
                continue;
            }
            Err(e) => { eprintln!("recv error: {e}"); continue; }
            Ok((n, _src)) => {
                if n != PACKET_SIZE { continue; }

                let raw: &[u8; PACKET_SIZE] = buf[..PACKET_SIZE].try_into().unwrap();
                let frame = TelemetryFrame::from_bytes(raw);
                let att   = frame.attitude_error_deg();
                let spin  = frame.spin_rate_rads();

                let drops = last_seq.map_or(0, |s| frame.seq.wrapping_sub(s).wrapping_sub(1));
                last_seq     = Some(frame.seq);
                total_pkts  += 1;
                total_drops += drops as u64;

                // Telemetry line
                print!(
                    "seq={:<7} t={:7.3}  y={:8.2}m  vy={:7.3}m/s  \
                     att={:5.1}°  spin={:5.3}r/s",
                    frame.seq, frame.sim_time, frame.y, frame.vy, att, spin,
                );
                if drops > 0 { print!("  {YELLOW}[drops={drops}]{RESET}"); }

                if let Some(rule) = check_fsw(&frame, att, spin) {
                    let color = if rule == "ALTITUDE_ABORT" { RED } else { YELLOW };
                    print!("  {color}{BOLD}*** {rule} ***{RESET}");

                    let now   = unix_now();
                    let mut t = last_llm_time.lock().unwrap();
                    let since = now - *t;

                    if since >= LLM_COOLDOWN_SECS {
                        *t = now;
                        drop(t);

                        println!("\n  {CYAN}[→ LLM] querying Qwen3.5-2B on Jetson…{RESET}");

                        let alert      = FswAlert { rule, frame, att_err_deg: att, spin_rads: spin };
                        let llm_guard  = Arc::clone(&last_llm_time);
                        let sock2      = send_sock.try_clone().expect("clone sock");
                        let gs2        = gs_addr.clone();

                        thread::spawn(move || {
                            let _ = llm_guard; // keep alive
                            match query_llm(&alert) {
                                None => eprintln!("[fsw_orin] LLM unreachable — is llama-server up?"),
                                Some((reasoning, decision, elapsed)) => {
                                    println!("\n{CYAN}╔═ FSW AI DECISION ({elapsed:.1}s) ═══════════════{RESET}");
                                    if !reasoning.is_empty() {
                                        let preview = if reasoning.len() > 300 {
                                            format!("{}…", &reasoning[..300])
                                        } else { reasoning.clone() };
                                        println!("{CYAN}║ THINK:    {preview}{RESET}");
                                    }
                                    println!("{CYAN}║ DECISION: {decision}{RESET}");
                                    println!("{CYAN}╚════════════════════════════════════════════{RESET}\n");

                                    transmit_decision(&sock2, &gs2, &alert,
                                                      &reasoning, &decision, elapsed);
                                }
                            }
                        });
                    } else {
                        print!("  [LLM cooldown {:.1}s]", LLM_COOLDOWN_SECS - since);
                    }
                }

                println!();

                if total_pkts % 500 == 0 {
                    let pct = 100.0 * total_drops as f64 / total_pkts as f64;
                    println!("  {BOLD}[stats] pkts={total_pkts}  drops={total_drops}  \
                              loss={pct:.3}%{RESET}");
                }
            }
        }
    }
}
