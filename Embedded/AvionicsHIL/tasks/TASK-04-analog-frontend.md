# TASK-04 — Analog front-end designed from Art of Electronics + the parts bin (Act 2)

> Self-contained brief. Read [../AGENTS.md](../AGENTS.md), [../HARDWARE.md](../HARDWARE.md),
> [../INTERFACES.md](../INTERFACES.md) first.

## Objective
Have the agent **design a real sensor-conditioning circuit** — temperature sensor → op-amp gain
stage → anti-alias filter → ADC — by (a) deriving the equations from the OCR-resolved *Art of
Electronics 3e*, (b) selecting actual components from the vision-scanned parts bin, and (c) emitting
a pin-by-pin breadboard build + a verification procedure. Then read the real channel from the DUT.

## Why it matters (SpaceX mapping + differentiator)
"Analog and digital circuit boards" are explicitly in scope for SpaceX Avionics Test. More
importantly this is the demo's unique flex: **an LLM designing a real analog circuit, citing the
textbook it just OCR-reconciled, with parts pulled from a bin it scanned by vision.** Nobody else's
demo does this.

## Dependencies
- TASK-01 (a sensor input path to the DUT — ADC pin or an I²C ADC). Otherwise standalone desk+bench work.

## Inputs
- Textbook (cite specific equations): `Data/Public/books/EngineeringPhysics/HorowitzHill-ArtOfElectronics3e/ocr-compare/reconciled/resolved.md`.
- Parts available: `Data/Public/embedded/HomeElectronicsInventory/inventory.json` (LM358N op-amp; 10 kΩ thermistor RS 271-110; LM335Z; NTE resistors/caps; Inland 3.3 V PSU).
- Wiring/safety: [../HARDWARE.md](../HARDWARE.md) §6, §7.

## Deliverables (under `analog/`)
- `analog/design.md` — the worked design: sensor choice, transfer function, **gain set with the AoE non-inverting-amp equation `G = 1 + R₂/R₁`** (cite the eq + section from `resolved.md`), anti-alias RC corner `f_c = 1/(2πRC)`, chosen component values **with the exact inventory part numbers used**, and the expected output voltage vs temperature.
- `analog/breadboard_build.md` — **pin-by-pin** wiring (LM358 pinout, power, the thermistor divider, the RC filter, the connection to the DUT ADC). Explicit, beginner-friendly (per AGENTS.md).
- `analog/verify.py` — reads the conditioned channel from the DUT and checks it tracks a known temperature within tolerance; writes `reports/analog_check.json`.

## Steps
1. **Pick the sensor.** Recommended: 10 kΩ NTC thermistor (RS 271-110) in a divider with a fixed resistor, OR LM335Z (direct 10 mV/K). State the trade-off; pick one.
2. **Derive the conditioning math from `resolved.md`:** non-inverting gain `G = 1 + R₂/R₁`; choose `R₁,R₂` from values present in `inventory.json` to map the sensor's output span into the ADC's input range (state the ADC range — Jetson ADC or an external one). Quote the equation and its book location.
3. **Design the anti-alias filter:** single-pole RC at a corner safely below the loop Nyquist; compute `R,C` using `f_c = 1/(2πRC)` with in-bin values (the NTE ceramic caps + resistors). Cite the AoE RC-filter section.
4. **Bill the design** strictly from `inventory.json` — every part must be one you actually have; reference its inventory `id`/part number. If an exact value isn't in the bin, choose the nearest available and note the resulting error.
5. **Write `breadboard_build.md`** pin-by-pin (LM358 power pins, the half used, input divider, filter, output to ADC, grounds, 3.3 V from the Inland PSU). Include the safety checklist (3.3 V only; cap polarity).
6. **Write `verify.py`:** sample the channel from the DUT; convert ADC counts → voltage → temperature using the derived transfer function; compare to a reference (room temp / a second thermometer / finger-warming test). PASS if within stated tolerance.
7. Update STATUS.md.

## Acceptance criteria
- `design.md` cites at least two specific AoE equations from `resolved.md` (gain + filter) with their numbers/sections.
- Every component in the BOM maps to a real `inventory.json` entry (id + part number).
- `breadboard_build.md` is explicit enough to wire without further questions.
- `verify.py` reads the channel and produces `reports/analog_check.json` with a PASS within tolerance.

## Definition of done
Acceptance met; STATUS.md updated. (Optional stretch: feed this real temperature channel into the
FSW as an additional sensor field so Act 2 and Act 3 visibly connect.)
