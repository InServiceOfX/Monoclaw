# ESP32 DevKit

Bring-up and Rust firmware for a generic ESP32 DevKitC-style board (Silicon
Labs CP2102 USB-UART bridge, ESP32-D0WDQ6 rev v1.0, MAC `0c:b8:15:c1:43:84`).

Reference documentation (datasheets, TRM, schematic) and the full bring-up
write-up live outside this repo, alongside the other board dumps, at
`/media/ernest/Samsung980ProPCI/openclaw-workspace/Data/Public/embedded/ESP32DevKit/`
— see `Generated/ESP32_BRINGUP_STATUS.md` there for chip details, the
ModemManager/reset-handshake gotchas hit during bring-up, and current flash
status.

## rust-blinky

Minimal `no_std` Rust firmware: toggles GPIO2 (the usual onboard LED pin on
most DevKitC clones) and prints a heartbeat over UART. Confirmed to build
cleanly; see the bring-up doc above for why flashing wasn't completed yet.

### Build

Requires the Espressif Rust fork (Xtensa target — the original ESP32 is
Xtensa LX6, not RISC-V, so upstream `rustc` can't target it):

```bash
# one-time: espup install
source ~/export-esp.sh
cd rust-blinky
cargo +esp build --release
```

`Cargo.toml` pins several transitive dependencies under `[build-dependencies]`
(not `[dependencies]`) — the crates.io ecosystem has moved past what this
toolchain's era of Cargo supports (`edition2024`), and pinning them as
build-dependencies avoids trying to compile host-only tooling crates for the
bare-metal Xtensa target.

### Flash

```bash
sudo systemctl stop ModemManager  # avoid it racing esptool for the port
espflash flash --port /dev/ttyUSB0 --monitor target/xtensa-esp32-none-elf/release/esp32-blinky
```
