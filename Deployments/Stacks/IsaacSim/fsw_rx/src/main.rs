//! FSW Telemetry Receiver — Jetson Orin Nano
//!
//! Receives 64-byte UDP datagrams from Isaac Sim (`enable_ros2_bridge.py`)
//! and evaluates flight software rules in real time.
//!
//! Packet layout (little-endian, 64 bytes total):
//!   [0..4]   u32   seq          monotonic counter
//!   [4..12]  f64   sim_time     simulation clock (s)
//!   [12..16] f32   x            position x (m)
//!   [16..20] f32   y            position y / altitude (m, Y-up)
//!   [20..24] f32   z            position z (m)
//!   [24..28] f32   qw           quaternion w (scalar first)
//!   [28..32] f32   qx
//!   [32..36] f32   qy
//!   [36..40] f32   qz
//!   [40..44] f32   vx           linear velocity (m/s)
//!   [44..48] f32   vy
//!   [48..52] f32   vz
//!   [52..56] f32   wx           angular velocity (rad/s)
//!   [56..60] f32   wy
//!   [60..64] f32   wz

use std::net::UdpSocket;
use std::time::{Duration, Instant};

const PACKET_SIZE: usize = 64;

// FSW rule thresholds
const ALTITUDE_ABORT_M: f32 = 5.0;
const DESCENT_ABORT_MS: f32 = -2.0;
const ATTITUDE_ANOMALY_DEG: f32 = 45.0;
const SPIN_ANOMALY_RADS: f32 = 1.0;

// ANSI colours — fall back gracefully on terminals that don't support them
const RED: &str = "\x1b[1;31m";
const YELLOW: &str = "\x1b[1;33m";
const RESET: &str = "\x1b[0m";

#[derive(Debug, Clone, Copy)]
struct TelemetryFrame {
    seq: u32,
    sim_time: f64,
    x: f32,
    y: f32,
    z: f32,
    qw: f32,
    qx: f32,
    qy: f32,
    qz: f32,
    vx: f32,
    vy: f32,
    vz: f32,
    wx: f32,
    wy: f32,
    wz: f32,
}

impl TelemetryFrame {
    fn from_bytes(b: &[u8; PACKET_SIZE]) -> Self {
        // Both aarch64 (Jetson) and x86_64 (Isaac Sim host) are little-endian.
        // Using explicit from_le_bytes is correct and portable.
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
        // Angle from upright: 2·acos(|qw|), clamped to [-1,1] before acos
        let qw_clamped = self.qw.abs().min(1.0);
        2.0 * qw_clamped.acos() * 180.0 / std::f32::consts::PI
    }

    fn spin_rate_rads(&self) -> f32 {
        (self.wx * self.wx + self.wy * self.wy + self.wz * self.wz).sqrt()
    }
}

// Evaluated once per frame; returned as flags for display and logging
struct FswStatus {
    altitude_abort: bool,
    attitude_anomaly: bool,
    spin_anomaly: bool,
    att_err_deg: f32,
    spin_rads: f32,
}

fn evaluate_fsw(f: &TelemetryFrame) -> FswStatus {
    let att_err = f.attitude_error_deg();
    let spin    = f.spin_rate_rads();
    FswStatus {
        altitude_abort:  f.y < ALTITUDE_ABORT_M && f.vy < DESCENT_ABORT_MS,
        attitude_anomaly: att_err > ATTITUDE_ANOMALY_DEG,
        spin_anomaly:    spin > SPIN_ANOMALY_RADS,
        att_err_deg:     att_err,
        spin_rads:       spin,
    }
}

fn print_banner(port: u16) {
    println!("╔══════════════════════════════════════════════════════════╗");
    println!("║  FSW Telemetry Receiver — Jetson Orin Nano (Rust)       ║");
    println!("║  Listening UDP :{port:<5}   packet size {PACKET_SIZE} bytes          ║");
    println!("╠══════════════════════════════════════════════════════════╣");
    println!("║  FSW Rules:                                              ║");
    println!("║    1. ALTITUDE ABORT  y < {ALTITUDE_ABORT_M:.1}m AND vy < {DESCENT_ABORT_MS:.1}m/s     ║");
    println!("║    2. ATTITUDE ANOMALY  tilt > {ATTITUDE_ANOMALY_DEG:.0}°                   ║");
    println!("║    3. SPIN ANOMALY  |ω| > {SPIN_ANOMALY_RADS:.1} rad/s                  ║");
    println!("╚══════════════════════════════════════════════════════════╝");
    println!();
}

fn main() {
    let port: u16 = std::env::args()
        .nth(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(50505);

    print_banner(port);

    let sock = UdpSocket::bind(("0.0.0.0", port))
        .unwrap_or_else(|e| { eprintln!("bind failed: {e}"); std::process::exit(1) });

    sock.set_read_timeout(Some(Duration::from_secs(5)))
        .expect("set_read_timeout failed");

    let start = Instant::now();
    let mut buf = [0u8; 256];
    let mut last_seq: Option<u32> = None;
    let mut total_pkts: u64 = 0;
    let mut total_drops: u64 = 0;

    loop {
        match sock.recv_from(&mut buf) {
            Err(e) if e.kind() == std::io::ErrorKind::WouldBlock
                   || e.kind() == std::io::ErrorKind::TimedOut => {
                let elapsed = start.elapsed().as_secs_f32();
                eprintln!("  [timeout at {elapsed:.1}s — no packet received]");
                continue;
            }
            Err(e) => { eprintln!("recv error: {e}"); continue; }
            Ok((n, _addr)) => {
                if n != PACKET_SIZE {
                    eprintln!("[warn] unexpected packet size {n} (expected {PACKET_SIZE})");
                    continue;
                }

                let raw: &[u8; PACKET_SIZE] = buf[..PACKET_SIZE].try_into().unwrap();
                let frame = TelemetryFrame::from_bytes(raw);
                let fsw   = evaluate_fsw(&frame);

                let drops = match last_seq {
                    None    => 0u32,
                    Some(s) => frame.seq.wrapping_sub(s).wrapping_sub(1),
                };
                last_seq     = Some(frame.seq);
                total_pkts  += 1;
                total_drops += drops as u64;

                // Main telemetry line
                print!(
                    "seq={:<7} t={:7.3}  y={:8.2}m  vy={:7.3}m/s  \
                     att={:5.1}°  spin={:5.3}r/s  drops={}",
                    frame.seq, frame.sim_time, frame.y, frame.vy,
                    fsw.att_err_deg, fsw.spin_rads, drops,
                );

                // FSW rule alerts (coloured)
                if fsw.altitude_abort {
                    print!("  {RED}*** FSW RULE 1: ALTITUDE ABORT ***{RESET}");
                }
                if fsw.attitude_anomaly {
                    print!("  {YELLOW}*** FSW RULE 2: ATTITUDE ANOMALY {:.1}° ***{RESET}",
                           fsw.att_err_deg);
                }
                if fsw.spin_anomaly {
                    print!("  {YELLOW}*** FSW RULE 3: SPIN ANOMALY {:.3} r/s ***{RESET}",
                           fsw.spin_rads);
                }

                println!();

                // Stats every 500 packets
                if total_pkts % 500 == 0 {
                    let drop_pct = 100.0 * total_drops as f64 / total_pkts as f64;
                    println!(
                        "  [stats]  total={total_pkts}  drops={total_drops}  \
                         drop_rate={drop_pct:.3}%"
                    );
                }
            }
        }
    }
}
