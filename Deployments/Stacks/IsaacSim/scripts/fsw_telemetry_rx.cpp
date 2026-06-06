/*
 * fsw_telemetry_rx.cpp — Flight Software Telemetry Receiver
 *
 * Runs on the Jetson Orin Nano (aarch64, Ubuntu 20.04, JetPack 5.x).
 * Receives 64-byte UDP datagrams from Isaac Sim and applies FSW rules.
 *
 * Compile on Jetson:
 *   g++ -O2 -std=c++17 -o fsw_rx fsw_telemetry_rx.cpp
 *
 * Run:
 *   ./fsw_rx [port]   default port 50505
 *
 * Packet layout (little-endian, 64 bytes — matches enable_ros2_bridge.py):
 *   uint32  seq              4 B   monotonic packet counter
 *   float64 sim_time         8 B   simulation clock (s)
 *   float32 x, y, z         12 B   position (m, Y-up)
 *   float32 qw,qx,qy,qz     16 B   orientation quaternion (w first)
 *   float32 vx,vy,vz        12 B   linear velocity (m/s)
 *   float32 wx,wy,wz        12 B   angular velocity (rad/s)
 *                            64 B  total
 */

#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <unistd.h>

// ── Telemetry frame (must match Python struct.pack("<Id13f")) ──────────────
// Both x86 host and aarch64 Jetson are little-endian — no byte-swap needed.
#pragma pack(push, 1)
struct TelemetryFrame {
    uint32_t seq;
    double   sim_time;
    float    x, y, z;
    float    qw, qx, qy, qz;   // w first, Isaac Sim convention
    float    vx, vy, vz;
    float    wx, wy, wz;
};
#pragma pack(pop)

static_assert(sizeof(TelemetryFrame) == 64, "TelemetryFrame must be 64 bytes");

// ── FSW rule thresholds ────────────────────────────────────────────────────
constexpr float ALTITUDE_ABORT_M      = 5.0f;    // y < this AND descending
constexpr float DESCENT_ABORT_MS      = -2.0f;   // vy below this triggers
constexpr float ATTITUDE_ANOMALY_DEG  = 45.0f;   // tilt from upright
constexpr float SPIN_ANOMALY_RADS     = 1.0f;    // rad/s total angular rate

// ── Helpers ────────────────────────────────────────────────────────────────
static float attitude_error_deg(const TelemetryFrame& f) {
    // Angle from upright: 2·acos(|qw|)
    float qw_clamped = std::min(1.0f, std::abs(f.qw));
    return 2.0f * std::acos(qw_clamped) * 180.0f / M_PI;
}

static float spin_rate_rads(const TelemetryFrame& f) {
    return std::sqrt(f.wx*f.wx + f.wy*f.wy + f.wz*f.wz);
}

static const char* timestamp() {
    static char buf[32];
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    snprintf(buf, sizeof(buf), "%6ld.%03lds",
             (long)ts.tv_sec, (long)(ts.tv_nsec / 1'000'000));
    return buf;
}

// ── FSW rule evaluation ────────────────────────────────────────────────────
static void evaluate_fsw_rules(const TelemetryFrame& f, uint32_t drops) {
    float att_err  = attitude_error_deg(f);
    float spin     = spin_rate_rads(f);
    bool  abort_alt = (f.y < ALTITUDE_ABORT_M && f.vy < DESCENT_ABORT_MS);
    bool  att_anom  = (att_err > ATTITUDE_ANOMALY_DEG);
    bool  spin_anom = (spin > SPIN_ANOMALY_RADS);

    printf("[%s]  seq=%-7u  t=%7.3f  y=%8.2fm  vy=%7.3fm/s  "
           "att=%5.1f°  spin=%5.3f r/s  drops=%u",
           timestamp(), f.seq, f.sim_time, f.y, f.vy,
           att_err, spin, drops);

    if (abort_alt)  printf("  \033[1;31m*** FSW RULE 1: ALTITUDE ABORT ***\033[0m");
    if (att_anom)   printf("  \033[1;33m*** FSW RULE 2: ATTITUDE ANOMALY %.1f° ***\033[0m", att_err);
    if (spin_anom)  printf("  \033[1;33m*** FSW RULE 3: SPIN ANOMALY %.3f r/s ***\033[0m", spin);

    printf("\n");
    fflush(stdout);
}

// ── Main ───────────────────────────────────────────────────────────────────
int main(int argc, char* argv[]) {
    const int port = (argc > 1) ? atoi(argv[1]) : 50505;

    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) { perror("socket"); return 1; }

    // Allow quick restart without TIME_WAIT blocking
    int reuse = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    sockaddr_in addr{};
    addr.sin_family      = AF_INET;
    addr.sin_port        = htons(static_cast<uint16_t>(port));
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
        perror("bind"); return 1;
    }

    printf("╔══════════════════════════════════════════════════════════╗\n");
    printf("║  FSW Telemetry Receiver — Jetson Orin Nano (JetPack 5)  ║\n");
    printf("║  Listening UDP :%d   packet size %zu bytes            ║\n",
           port, sizeof(TelemetryFrame));
    printf("╠══════════════════════════════════════════════════════════╣\n");
    printf("║  FSW Rules:                                              ║\n");
    printf("║    1. ALTITUDE ABORT  y < %.1fm AND vy < %.1fm/s      ║\n",
           ALTITUDE_ABORT_M, DESCENT_ABORT_MS);
    printf("║    2. ATTITUDE ANOMALY  tilt > %.0f°                    ║\n",
           ATTITUDE_ANOMALY_DEG);
    printf("║    3. SPIN ANOMALY  |ω| > %.1f rad/s                   ║\n",
           SPIN_ANOMALY_RADS);
    printf("╚══════════════════════════════════════════════════════════╝\n\n");
    fflush(stdout);

    TelemetryFrame frame;
    uint32_t last_seq    = UINT32_MAX;  // will wrap to 0 on first packet
    uint64_t total_pkts  = 0;
    uint64_t total_drops = 0;

    while (true) {
        ssize_t n = recv(fd, &frame, sizeof(frame), 0);
        if (n < 0) { perror("recv"); continue; }
        if (static_cast<size_t>(n) != sizeof(frame)) {
            fprintf(stderr, "[warn] unexpected packet size %zd (expected %zu)\n",
                    n, sizeof(frame));
            continue;
        }

        uint32_t drops = (last_seq == UINT32_MAX)
                          ? 0
                          : (frame.seq - last_seq - 1);
        last_seq     = frame.seq;
        total_pkts  += 1;
        total_drops += drops;

        evaluate_fsw_rules(frame, drops);

        // Print running stats every 500 packets
        if (total_pkts % 500 == 0) {
            printf("  [stats]  total_pkts=%lu  total_drops=%lu  "
                   "drop_rate=%.3f%%\n",
                   total_pkts, total_drops,
                   100.0 * total_drops / total_pkts);
            fflush(stdout);
        }
    }

    close(fd);
    return 0;
}
