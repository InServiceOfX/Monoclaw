# BeagleBone Black Bring-Up Progress

**Board**: BeagleBone Black Rev C / C.1  
**Image**: BeagleBoard.org Debian Bullseye IoT (2023-08-05)  
**Purpose**: EGSE / sensor emulator + Isaac bridge for Jetson Orin Nano HIL (see top-level HARDWARE.md, INTERFACES.md, ORCHESTRATION.md)

## Current Connections & Power

- Powered via micro-USB from host computer. Boots reliably.
- USB also provides:
  - Serial console
  - USB Ethernet gadget (`usb0` / `usb1`)
- Real Ethernet (`eth0`) connected to local switch (behind Google WiFi router).
- No external capes or heavy loads attached yet.
- P8 and P9 expansion headers available.

**Power guidance**:
- USB is adequate for bring-up, serial access, and light header usage.
- Use the 5 V barrel jack (2.1 mm center-positive, ≥1 A) when driving significant current through the headers or adding capes.
- The PMIC will prefer the barrel supply when both are present.

## Access Methods

### Serial Console
- Host side: `/dev/ttyACM0`
- Parameters: 115200 8N1 (no hardware or software flow control)
- Example: `minicom -D /dev/ttyACM0 -b 115200`

### Network Access
- **USB Gadget**: Direct connection from host (address in the 192.168.7.x range on the host's `usb0` interface).
- **Real Ethernet**: DHCP client on `eth0`. The board receives an address on the local LAN subnet.

**Re-plug behavior**: Unplugging and re-plugging the Ethernet cable causes a fresh DHCP request. The router may return the same address or a different one. Acceptable for development.

### Users with Shell Access
- debian (default)
- bbblack (member of sudo group)
- beagle (elevated privileges added)
- beaglebone (elevated privileges added)
- root
- node-red

The `beagle` and `beaglebone` accounts were added with sudo and relevant hardware groups (gpio, i2c, dialout, adm, video, plugdev, netdev, etc.).

## Verified This Session

- Clean boot (power LED solid, heartbeat activity on user LEDs).
- Serial console reachable.
- Both USB gadget networking and real Ethernet functional.
- Real Ethernet:
  - Link up (`eth0`)
  - DHCP lease obtained
  - Gateway pingable
  - External internet reachable
  - Reachable from other machines on the same LAN
- No built-in WiFi (no `wlan*` interfaces, no wireless modules).
- Expansion header reference data parsed and available (see Generated/ directory).

## Key Reference Files

Located in `Data/Public/embedded/BeagleBoneBlack/Generated/`:
- `bbb_p8_p9_pinout.csv` (primary)
- `bbb_p8_pinout.csv`
- `bbb_p9_pinout.csv`
- `bbb_bom.csv`
- `bringup_notes.md`
- Power and connector excerpts

These were produced by the parser in `Embedded/JetsonOrinNano/parse_bbb.py`.

Cross-reference:
- `Embedded/AvionicsHIL/HARDWARE.md` (intended Jetson ↔ BBB wiring, safety)
- Original PDFs in the parent `BeagleBoneBlack/` directory

## Expansion Header State

- P9.19/20 (I2C2) and P9.21/22 (UART2) currently in default mux.
- `config-pin` tool is present.
- Example to enable UART2 (adjust after checking resulting device):
  ```bash
  config-pin P9.21 uart
  config-pin P9.22 uart
  ls /dev/ttyS*
  ```
- Exact device that appears for the expansion UART (likely one of `/dev/ttyS*`) should be recorded once enabled.

## Current Limitations

- Still on USB power only.
- Ethernet address is dynamic.
- No WiFi.
- P9 pins not yet reconfigured for the planned Jetson transport.
- Integration with Jetson FSW / EGSE code not yet exercised.

## Suggested Continuation Steps

1. Add 5 V barrel supply if header current draw increases.
2. Enable and identify the correct `/dev/tty*` for P9.21/22 UART (or I2C2) per HARDWARE.md.
3. Verify end-to-end link with the Jetson (UART or I2C as defined in INTERFACES.md).
4. Decide on permanent networking (DHCP reservation vs. static).
5. Update `STATUS.md` (top level) and/or `HARDWARE.md` with discovered device names and any deviations.
6. Use the CSVs in Generated/ for all pin questions rather than re-parsing PDFs.

## How Another Agent Should Pick This Up

- Connect the USB cable → you get both serial (`/dev/ttyACM0`) and gadget network.
- Or use the real Ethernet IP (discover with `ip -br addr` after logging in via gadget).
- Serial is the most reliable fallback.
- All pinout details live in the CSVs.
- The two non-default development users already have the necessary privileges.
- Start with the verification commands in this directory's sibling `Generated/` files and the top-level HARDWARE.md.

This file + the Generated/ artifacts + existing AvionicsHIL docs should let a follow-on agent continue without repeating the initial discovery work.ve.

## Current Limitations / Notes
- Relying on USB power for now.
- Ethernet address is dynamic (re-plug behavior noted above).
- No wireless.
- Expansion UART/I2C pins still need to be muxed for the Jetson link.
- `bbblack` user already had sudo before this session; additional development users were added with equivalent privileges.

## Recommended Next Steps (for agent continuation)

1. Decide on stable networking for the bench (DHCP reservation on router or static IP via `/etc/network/interfaces` or systemd-networkd).
2. Add the 5V barrel supply if/when attaching real hardware to P8/P9.
3. Enable and verify UART2 on P9.21/22 (or I2C2) per HARDWARE.md wiring diagram to Jetson.
4. Confirm device names on this kernel (`/dev/ttyS*` vs older `ttyO*` expectations).
5. Test bidirectional frames between BBB EGSE and Jetson (per INTERFACES.md).
6. Record exact `config-pin` commands and resulting `/dev/tty*` in STATUS.md or a dedicated config file.
7. Update HARDWARE.md with any verified device paths, power measurements, or deviations.

## How to Resume Work
- Connect via USB (serial + gadget network) or real Ethernet.
- Preferred entry: `ssh` to the current Ethernet IP or the gadget address.
- Serial fallback always available.
- Reference the CSVs in Generated/ for any pin questions instead of re-reading the large PDFs.
- Cross-check against `HARDWARE.md` for the intended Jetson <-> BBB wiring.

This document captures the state after initial power-on, network verification, user provisioning (names only), and reference data parsing. It is intended to allow a follow-on agent to continue without re-deriving the basics.

Generated during the session that also produced the BBB doc parser and initial bring-up checks.