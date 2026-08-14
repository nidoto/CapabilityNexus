# CapabilityNexus Development Log

## Version

V1.7.0 development snapshot

## Focus

This cycle improves runtime stability, device lifecycle handling, firmware
boundaries and product documentation.

## Completed

- Added runtime dependency detection for vgamepad, ViGEmBus and HidHide
- Added `start.cmd` launcher for stable project-root startup
- Added atomic JSON configuration writes and configuration shape validation
- Added thread-safe event bus with subscriber isolation and unsubscribe support
- Added runtime mapping reload with locking
- Added runtime device and output add/remove synchronization
- Added network stream buffering for split TCP and Bluetooth lines
- Added connection error backoff and clean thread shutdown
- Added keyboard and mouse pressed-state release on exit
- Added FTMS and ANT shutdown handling
- Added persistent reverse-request history with idle zero-rumble filtering
- Added browser/process context to reverse-request monitoring
- Removed the old request detail tree from the main GUI
- Improved device/output monitor layout and scrolling
- Added case-insensitive ESP32 serial aliases
- Ignored `FRAME=` transport metadata in serial input
- Added final control-value capabilities: `control.right_x` and `control.right_y`
- Moved ESP32 angle wrapping, clamping and XInput scaling into firmware
- Updated public wording to use XInput-compatible terminology
- Added product, installation and third-party documentation
- Added HidHide game-exclusive mode (`tools/hidhide.py` + CLI + GUI dialog)
  - Locates HidHideCLI and enumerates HID devices via Windows PnP
  - Hides / unhides physical controllers and toggles cloaking (UAC elevated)
  - Registers CapabilityNexus itself as an exempt app so it can keep reading a
    hidden physical controller
  - Verified with a Bluetooth Xbox One controller: after cloaking, XInput slot
    reports only the virtual x360 gamepad; the real controller stays readable
    by the engine once python.exe is exempted
- Added per-game profiles (`profiles/<game>.json`, GUI: Mappings > Game Profiles)
  - `config/active_profile.json` records the selected game
  - Each profile carries its own mappings and an optional `processors` section
  - Engine and request handler reload the active profile at runtime
  - Local device-tuning profiles live in `profiles/local/` (gitignored) so a
    hardware vendor's per-game tuning stays with the device and is not shared
    to users with different hardware
- Added `curve` processor (`processors/curve.py`) for gyro response curves
  - Two modes: `linear` (segment interpolation) and `step` (fixed output per
    angle band, recommended for combat games)
  - Configurable deadzone, max angle and per-band percentages
  - Used by the Cyberpunk 2077 profile: X axis ±12 deg to 80%, Y axis ±6 deg
    to 60%, 1.5 deg deadzone, axes reversed via `gain: -1.0`
- First in-game test with Cyberpunk 2077: HidHide hides the real Xbox One pad,
  the virtual XInput-compatible controller is the only pad the game sees, and
  the gyro steers the in-game camera (tuning still in progress)

## ESP32 Boundary

The firmware now owns orientation conversion, calibration offset, signed angle
normalization, `-180..180` clamping and conversion to `-32768..32767` controller
axis values. The open client forwards final control values.

## Verification

- Python `compileall` passes
- Serial alias and frame parsing tests pass
- Mapping reload and event lifecycle tests pass
- Configuration atomic-save and shape-validation tests pass
- Runtime dependency detection reports the local Windows installation

## Remaining Work

- Add official third-party installer assets and license bundles
- Add automated hardware-in-the-loop tests
- Test multiple games and controller selection behavior

## Product Documentation Update

- Added bilingual product positioning and capability overview.
- Clarified the distinction between the open routing client and closed firmware
  algorithms.
- Clarified that the product provides XInput-compatible controller output and
  is not an Xbox emulator.
- Added installation, dependency and third-party distribution guidance.
