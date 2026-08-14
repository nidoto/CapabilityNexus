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
- Release packaging prep
  - `requirements.txt` with pinned runtime dependencies (vgamepad, pyserial,
    pygame, bleak, openant, pynput)
  - `LICENSE` (MIT) for the project itself
  - Expanded `THIRD_PARTY_NOTICES.md` with licenses for all Python packages
  - `tools/build_release.py`: produces a source distribution under `dist/`
    (client code, default config, docs, launcher); excludes local device
    tuning (`profiles/local`), caches and `__pycache__`
- Frozen executable (PyInstaller)
  - `CapabilityNexus.spec` (one-dir, windowed) collects sanitized
    `config/profiles/packages` data (no caches, no `active_profile`, no
    `profiles/local`)
  - `tools/build_release.py` now builds a frozen `windows/CapabilityNexus.exe`
    alongside the source distribution; verified it starts and stays running
- Bundled official driver installers
  - `tools/fetch_drivers.py` downloads official HidHide 1.5.230 setup plus its
    MIT license into the release `drivers/` directory
  - ViGEmBus is bundled from a locally verified source when provided
    (`--vigembus-src`): the full x64/x86 driver package (1.21.442.0, from a
    vendor bundle such as QKeyMapper) is copied so the released driver is
    complete and self-contained; official 1.22.0 is used as fallback
  - Drivers are never installed silently; official builds require user consent
- Driver install helper
  - `tools/install_drivers.cmd` is copied to the release root; it auto-elevates
    (UAC) and installs the bundled ViGEmBus (via nefconw.exe --install-driver)
    and HidHide setup, then reminds the user to reboot
- End-to-end verified: the frozen exe starts and stays running; the release
  source distribution boots the engine, creates the virtual XInput-compatible
  controller on XInput slot 0 and shuts down cleanly
- In-app driver management (System > Driver Management)
  - `tools/drivers.py` detects, installs and uninstalls ViGEmBus and HidHide;
    elevated operations run through UAC via ShellExecute "runas" with
    synchronous completion and captured exit codes
  - GUI dialog shows install state, resolves the bundled drivers/ directory
    (exe or source dist), and offers install/uninstall buttons per driver
  - Verified with the bundled 1.21.442.0 driver: nefconw uninstall and install
    both report success, and the virtual XInput-compatible controller returns
    to XInput slot 0 after reinstall

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

- Add automated hardware-in-the-loop tests
- Test multiple games and controller selection behavior
- Consider code signing for the frozen executable
- Create a setup wizard / bundler that installs Python, drivers and the app
  in one step for non-technical users

## Product Documentation Update

- Added bilingual product positioning and capability overview.
- Clarified the distinction between the open routing client and closed firmware
  algorithms.
- Clarified that the product provides XInput-compatible controller output and
  is not an Xbox emulator.
- Added installation, dependency and third-party distribution guidance.
