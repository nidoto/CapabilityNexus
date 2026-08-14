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
- Implement HidHide session-blacklist configuration
- Add automated hardware-in-the-loop tests
- Test multiple games and controller selection behavior

## Product Documentation Update

- Added bilingual product positioning and capability overview.
- Clarified the distinction between the open routing client and closed firmware
  algorithms.
- Clarified that the product provides XInput-compatible controller output and
  is not an Xbox emulator.
- Added installation, dependency and third-party distribution guidance.
