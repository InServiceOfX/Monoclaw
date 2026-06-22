# TASK-03 — Jetson flight software + closed-loop HIL (Act 3)

> Self-contained brief. Read [../AGENTS.md](../AGENTS.md), [../ARCHITECTURE.md](../ARCHITECTURE.md),
> [../INTERFACES.md](../INTERFACES.md), [../HARDWARE.md](../HARDWARE.md) first. Honor INTERFACES exactly.

## Objective
Write the **flight software (FSW)** that runs on the Jetson (the DUT): read 32-byte sensor frames,
run a landing-burn control law, and emit 16-byte command frames. Then **close the HIL loop**
(Isaac ⇄ BBB ⇄ Jetson) and demonstrate a soft simulated touchdown.

## Why it matters (SpaceX mapping)
This is the "embedded software on the avionics device under test" + "test execution in HIL." The
loop closing is the headline demo moment: a Starship landing flown by code on the Jetson.

## Dependencies
- **TASK-01** (Jetson transport enumerated + checked out).
- **TASK-02** (BBB streaming valid sensor frames + relaying commands to Isaac).
- Isaac stack running (physics-only, Z-up).

## Inputs
- Frame contract: [../INTERFACES.md](../INTERFACES.md) §3–4 (must byte-match TASK-02's `frames.py`).
- Isaac command API + the continuous-throttle TODO: [../INTERFACES.md](../INTERFACES.md) §7.
- Existing FSW skeleton to adapt: `~/.openclaw/workspace/jetson-fsw/` (Rust; already parses datagrams + has a UDP loop test). Reuse its structure.
- Control params: `config.yaml` (INTERFACES §8).

## Deliverables (under `jetson/fsw/`)
- FSW that reads the sensor UART, runs the control law, writes the command UART. **Recommended: extend the existing Rust `jetson-fsw`** (credible "flight code"); a Python first-spike is acceptable to close the loop fast, but port to Rust for the demo.
- `jetson/fsw/frames.rs` (or `.py`) — mirror of INTERFACES §3–4; **cross-checked against `bbb/egse/frames.py`** (same CRC, same bytes).
- `jetson/fsw/control.rs|py` — landing-burn law (PD on vertical velocity; see below).
- `jetson/fsw/README.md` — build/run steps.
- Isaac side: confirm or add a continuous throttle/gimbal command route (see step 2).
- `reports/hil_run.json` — telemetry trace + landing verdict for one descent.

## The control law (MVP)
PD controller on vertical velocity targeting a soft touchdown:
```
error_v = target_touchdown_velocity_mps - velocity_z     # target ~ -2.0 m/s
throttle = clamp(kp_alt*(some_alt_term) + kd*error_v ... , 0, 1)   # tune
```
Keep it simple — it must (a) arrest the fall and (b) respond to injected faults later. Start with a
hover/soft-land law: increase throttle as `velocity_z` becomes more negative and as altitude → 0.
Gimbal can stay 0 for the MVP (pure vertical). Tune `kp`/`kd` in config.yaml against the sim.

## Steps
1. **Implement/port `frames`** to match INTERFACES §3–4 exactly; add a test that decodes a frame produced by `bbb/egse/frames.py` and re-encodes a command the BBB can parse (golden-bytes cross-check).
2. **Isaac command route:** confirm whether `POST /starship/command` accepts a continuous throttle/gimbal (INTERFACES §7). If only `action:"liftoff"` exists, **add a throttle route** in the Isaac control server mapping to `starship/starship_controller.py` (the known TODO in `STATUS_ZUP_PHYSICS.md`). Keep the Z-up force convention.
3. **FSW main loop:** open sensor UART; on each valid frame → update state → run control → send command frame (echo the sensor `seq`). Reject frames with bad CRC or `fault_active`; define a safe-state (e.g., hold-last / max-decel) for missing data.
4. **Close the loop on the bench:** Isaac descending → BBB sensor frames → FSW → command frames → BBB → Isaac. Log altitude/velocity_z each tick.
5. **Tune** until the vehicle reaches `|velocity_z| < 2 m/s` at touchdown (altitude ≈ 0) without crashing or flying off.
6. **Measure loop timing:** using the echoed seq + BBB timestamps, record loop rate and round-trip latency → into `reports/hil_run.json` (this is the "deterministic timing" evidence).
7. Update STATUS.md.

## Acceptance criteria
- Jetson `frames` and BBB `frames` interoperate (golden-bytes cross-check passes both directions).
- Full loop runs ≥ 60 s without desync; measured loop rate within 20% of `config.loop.rate_hz`.
- A descent from altitude ends in a **soft touchdown: `|velocity_z| < 2 m/s`** at altitude ≈ 0.
- `reports/hil_run.json` contains the telemetry trace, measured loop rate/latency, and PASS verdict.

## Known unknowns / how to resolve
- **Isaac throttle route** may need adding (step 2) — that is expected work, not a blocker.
- **FSW language**: if Rust iteration is slow on first loop-closure, spike in Python, then port; note the decision in STATUS.md.
- **Stability/tuning**: if the law oscillates, reduce gains, lower loop rate, or add a small filter on velocity_z (and cite the Art of Electronics filter material if you build an analog one in TASK-04).

## Definition of done
Acceptance met; STATUS.md updated; `jetson/fsw/README.md` reproduces the run. The vertical slice
(TASK-01+02+03) is now complete — note that explicitly in STATUS.md.
