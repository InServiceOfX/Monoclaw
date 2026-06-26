"""
Landing-burn PD controller (INTERFACES.md §8 control params).

Velocity-only PD targeting a soft touchdown at target_touchdown_velocity_mps.

Physical intuition:
  - Vehicle falling fast  (vz << target): error_v >> 0 → high throttle → brake
  - Vehicle at target rate (vz == target): error_v == 0 → hover throttle → sustain descent
  - Vehicle rising        (vz > 0):        error_v < 0  → throttle < hover → let gravity re-engage

The vehicle naturally settles to vz ≈ target_v as the control loop converges.
"""
from dataclasses import dataclass

HOVER_THROTTLE = 0.21    # Mars: 830t × 3.72 m/s² / 14.7 MN
MAX_THROTTLE   = 0.85    # FSW hard limit (mirror of starship_controller.py)
LANDED_ALT_MM  = 2_000   # below 2 m → declare landed, cut engines


@dataclass
class ControlConfig:
    target_touchdown_velocity_mps: float = -2.0
    kp: float = 0.05   # altitude proportional (ramps up near ground)
    kd: float = 0.30   # velocity derivative


@dataclass
class ControlOutput:
    throttle: float       # 0.0 – MAX_THROTTLE
    engine_enable: bool
    abort: bool
    landed: bool


def run_control(
    altitude_mm: int,
    velocity_z_cms: int,
    fault_active: bool,
    cfg: ControlConfig,
) -> ControlOutput:
    """
    Single-step control law. Call once per received sensor frame.
    Returns throttle + flags to pack into the command frame.
    """
    if fault_active:
        # Isaac telemetry unreachable — maintain hover so Starship holds altitude
        # until the sensor link is restored (cutting engines causes uncontrolled free-fall)
        return ControlOutput(throttle=HOVER_THROTTLE, engine_enable=True, abort=False, landed=False)

    alt_m = altitude_mm / 1_000.0
    vz    = velocity_z_cms / 100.0        # cm/s → m/s

    # Landed detection — below threshold with near-zero velocity
    if 0 < altitude_mm <= LANDED_ALT_MM and abs(vz) < 3.0:
        return ControlOutput(throttle=0.0, engine_enable=False, abort=False, landed=True)

    # Velocity error: positive → falling faster than target → need more thrust
    target_v = cfg.target_touchdown_velocity_mps
    error_v  = target_v - vz               # e.g. -2 - (-50) = +48

    # Altitude proportional term: ramps from 0 at 500 m to kp at ground
    # Adds extra braking authority close to surface
    alt_factor = max(0.0, 1.0 - alt_m / 500.0)
    alt_term   = cfg.kp * alt_factor * (-target_v)   # bias toward braking near ground

    throttle = HOVER_THROTTLE + cfg.kd * error_v + alt_term
    throttle = max(0.0, min(MAX_THROTTLE, throttle))

    return ControlOutput(
        throttle=throttle,
        engine_enable=True,
        abort=False,
        landed=False,
    )
