# CapabilityNexus Development Log

## Version

V1.8.0 development snapshot

## Focus

This cycle turns the phone Web page into a full X360-compatible controller
(wheel / pad presets, per-phone config persistence, game capability matching,
vibration forwarding, map/menu buttons) and then performs a systematic
code-cleanup pass.

## Completed

### Phone Web -> X360 (input device -> capability -> client -> output)

- Completed the full mapping so the phone Web wheel really becomes an X360
  controller: wheel -> left stick X, pitch -> right stick Y, gas -> RT,
  brake -> LT, buttons/dpad -> X360 buttons, plus vibration.
- Added per-phone config persistence: the client saves each phone's settings
  (inverts, wheel max angle, gas gain) as `config/phone_profiles/<user>-<phone>.json`,
  and restores them automatically on reconnect. Manual "save" button on the page.
- Added wheel max angle and gas gain input boxes (inside the sensor box).
- Auto-save config after 500ms idle; no manual save button needed for edits
  (plus a top-right explicit Save button).

### Phone Web presets ("device + mode" templates)

- Added `config/phone_presets.json` with `interface: web` templates:
  - `phone_web_wheel` (wheel) and `phone_pad` (pad).
  - Each carries device config, capability list, mappings, processors, latency
    estimate and `start_web` action.
- Applying a preset: ensures the phone device, merges mappings/processors into
  the active game profile, ensures X360 output, activates the profile and
  auto-starts the Web service (no manual toggle needed).
- Game capability configs: `tools/game_library/programs/<game>/capabilities.json`
  records supported modes, latency requirement and reverse capabilities
  (vibration/gyro). If a game does not support a wheel (e.g. Rush Rally 3),
  the client auto-degrades to an X360-pad mapping (wheel -> left stick).
- Latency color coding: green = low, yellow = medium, red = high, shown in the
  device tree (per device) and the game list (per requirement). Replaces popups.
- Auto game detection: when a process (e.g. RushRally3.exe) sends reverse
  output, the client auto-selects that process in the dropdown and shows its
  capabilities, even if the user never picked it manually.

### Vibration

- Forward game rumble requests (`xbox.motor_left/right`) to the phone as
  `navigator.vibrate`. Fixed the 0-65535 -> 0-255 normalization bug (vgamepad
  callback uses 0-255), plus a sqrt curve and a 30ms minimum so low values are
  perceptible. Zero values are filtered (no idle vibration spam).
- Fixed the broadcast event-loop bug: `send_json` now uses the server's own
  event loop (`self._loop`) instead of `asyncio.get_event_loop()` from the GUI
  thread, so messages actually reach the phone.
- Vibration forwarding subscription is now created after the engine starts
  (`_ensure_phone_vibration_sub`), fixing the "never forwarded" issue.
- Added a "test vibration" menu entry on the phone page.

### Phone page UX

- Top bar: left "More" (function menu), center "Map" (X360 Back) and "Menu"
  (X360 Start) mapped buttons, right "Save". Address bar removed.
- `phone.button_back`/`phone.button_start` added to parser, capability package
  and presets.
- Multi-touch fix: brake drag now tracks `pointerId`, so a second finger
  touching elsewhere no longer clears the brake.
- Portrait/landscape handling: wheel max angle and gas gain are in the sensor
  box; orientation still flips on some devices (see Remaining Work).

### Code cleanup (bug fixes first)

- `device_manager.close_all()` now isolates per-device close errors so one
  failure no longer leaks remaining connections.
- `xinput_device` simplified a redundant if/else that ran the same branch.
- `output/router._find_managed` now uses exact `output_type` matching instead
  of fragile substring matching (`realxinputoutput` no longer matches `xinput`).
- Relative-path config reads replaced with absolute paths based on
  `config_io.PROJECT_ROOT` (request_library cache, custom_connection,
  output.manager, device_manager defaults).
- GUI: removed the dead `request_tree` chain (a Treeview that was never built,
  driven by a 200ms no-op tick, plus ~60 lines of unreachable mapping code).
- Deleted dead `core/transport.py` (never referenced at runtime) and its test.
- Deleted unused GUI helpers and variables (`_append_monitor`,
  `_on_request_double_click`, `_clear_requests`, `_device_targets`, etc.).
- Deleted unused methods in `status_monitor` and `device_manager`.
- Deduplicated `DeviceLibrary` / `RequestLibrary` behind a shared
  `devices/remote_library.py` base (cache read/write + file/network fetch).
- Unified XInput polling through `xinput_api.get_state`.
- Narrowed overly broad `except Exception` clauses to concrete exception types
  (`ValueError`, `tk.TclError`, `ImportError`/`AttributeError`, ...).
- Removed unused imports (websocket_connection, virtual_keyboard).

## ESP32 Boundary

Unchanged this cycle: firmware still owns orientation conversion, calibration
offset, signed-angle normalization, `-180..180` clamping and conversion to
controller axis values. The open client forwards final control values.

## Verification

- `python -m compileall` passes.
- `py -3 -m pytest`: 109 tests pass (dropped the 6 transport tests after
  removing the dead module; added tests for phone-back/start parsing in the
  sensors frame, presets/latency, phone profile store, phone->X360 mapping).
- End-to-end phone Web -> X360 verified: steering (left stick X), gas (RT),
  brake (LT), map/menu buttons, and game-rumble -> phone vibration.
- Auto game detection verified with RushRally3.exe.

## Remaining Work

- iOS Safari cannot use `navigator.vibrate` (Android Chrome only).
- Some devices still auto-rotate on tilt despite the orientation-lock attempt;
  suggest system rotation lock as fallback.
- GitHub submission of learned game configs is deferred (needs a fine-grained
  PAT scoped to the `CapabilityNexus-Requests` repo).
- Consider code signing for the frozen executable.
- Create a setup wizard / bundler for non-technical users.

---

## Same-day follow-up (still V1.8.0)

Everything below was done in the same development day and folded into V1.8.0.

### Phone Web — control schemes & fan pedals

- Added a scheme concept in the wheel mode:
  - `gyro` (陀螺仪油门, unchanged legacy behaviour): gyro steering + tilt gas, touch brake.
  - `touch` (触摸油门): gyro steering, gas and brake both finger-drag bars with 20 levels.
- Scheme switching lives in the "More" menu together with the mode switch
  (方向盘 / 手柄 are also in the menu now; the on-page buttons were removed).
- Touch scheme landscape layout: brake = fan (quarter circle, centre at screen
  bottom-left), gas = fan (centre at bottom-right), wheel + info panel centred,
  both pedals flush at the bottom edge. `display:contents` + flex `order` drive it.
- Wheel rotation input redefined as **left-right TOTAL angle** (racing-wheel
  convention). Default 90° (≈ F1, ±45° per side); normalised as
  `steer / (total / 2)`. Variable renamed to `wheelTotalAngle`.
- Gas gain input hidden in the touch scheme (it only applied to gyro gas).

### Phone Web — screen lock with pass-through zones

- Lock overlay (`#lockOverlay`) blocks everything except elements marked
  `lock-allow`: the gas/brake pedals, Map, Start and a new lock button (left of Map).
- Pass-through is element-based, so a future circular gas pedal is allowed
  automatically without touching the lock logic.
- New `lockButton` toggles lock/unlock and is the only functional key that stays
  usable while locked.

### Client device tree (real phone info)

- The phone node is now rendered from the **Web service connection state**
  (real reported name, capabilities, latency), independent of the engine's
  config-driven device discovery.
- Connected = Web service has a client AND real sensor/button data arrived in
  the last 3 s. A phone page left open in the background (WebSocket alive but no
  data) is treated as disconnected.
- The node disappears automatically on disconnect (polled every 200 ms).
- Device tree shows the reported capabilities
  (gyroscope / accelerometer / buttons / dpad / gas / brake / vibration / GPS).

### Latency: real data arrival, no ping

- Removed the ping/pong mechanism entirely (it added tiny control messages).
- "Latency" shown in the tree = average **real data frame arrival interval**
  measured purely server-side (last 50 frames). ~10 ms at 100 Hz → green.
- Transport analysis documented: WebSocket runs over TCP (port 8765). UDP is not
  reachable from a browser; WebRTC unreliable DataChannel is the potential path
  if loss-resistance is needed later.

### Web service / engine fixes

- Engine no longer creates its own phone WebSocket server → no port 8765
  conflict with the Web service; the Web service owns the phone link.
- Web service starts **lazily** (on phone-preset apply or manual toggle), so
  Bluetooth/serial users are not affected.
- `app.py` now reads the same exe-side config as `config_io` (frozen builds no
  longer read the empty embedded `_MEIPASS/config/devices.json`).
- Removed the preset-apply device re-discovery, which had made the client's own
  virtual XInput pad appear as a phantom "Microsoft Xbox One".
- Send throttle raised 20 ms → 10 ms (~100 Hz); wheel CSS transition
  0.05 s → 0.01 s.

### Client logging (file)

- All GUI log messages are now also written to `logs/client.log`
  (exe-side `logs/` when frozen) with `[YYYY-MM-DD HH:MM:SS.mmm]` timestamps,
  auto-rotated to `client.log.old` above 2 MB.
- Captured events include: app start, engine start/stop, preset apply,
  device connect/disconnect (all drivers), phone connect/disconnect,
  phone hello (name + capabilities), phone config saves, ~1 Hz sensor frame
  samples, ~1 Hz output value samples, vibration forwarding, heartbeats.

### Verification

- `py -3 -m pytest`: 109 tests pass.
- Phone Web → X360 end-to-end re-verified with the touch scheme (fan gas/brake,
  lock/unlock, map/menu), real reported capabilities and data-arrival latency.
- Game test: Rush Rally 3 — went from "cannot finish" to finishing around 16th
  place with the phone-wheel setup.

---

## Device Identity layer (follow-up, still V1.8.0)

Introduced a stable per-phone identity so configuration survives phone renames
and is independent of any user account. The model is **Device → Profile**
(device_id is the key; no user/account dimension is introduced).

### Data shape

- hello / config frames now carry `device_id` in addition to `name` /
  `capabilities`. `name` is display-only.
- Identity priority: `device_id` > `name`.

### Phone web page

- Generates a stable `device_id` (UUID) on first launch and persists it in
  `localStorage` (`cnx_device_id`); re-sent on every reconnect.
- If the phone connects without a `device_id`, the server generates one and
  returns it via a `device_id` message so the page can persist it.

### Server side (`PhoneFrameParser` / `PhoneProfileStore` / `WebService`)

- `PhoneFrameParser.device` is now `{"device_id", "name", "capabilities"}`;
  added `device_id` property.
- `PhoneProfileStore` keys files by `<device_id>.json` (was
  `<user>-<phone>.json`). `name` no longer affects the filename.
- Legacy `<*>-<phone>.json` files are **not deleted**: on first connect the
  store copies (migrates) a matching legacy file into the new
  `<device_id>.json` by phone display name. No username/env dependency.

### QR code for the Web service URL

- New `tools/qrcode_utils.py` (pure-python `qrcode`, no Pillow) renders the
  phone page URL(s) as PNG.
- GUI: once the Web phone service is started, the **right-side panel**
  (request column) **directly shows** a scannable QR per LAN IP (no button /
  no popup) so the phone can open the page by scanning; it hides automatically
  when the service stops.
- Library-missing is handled honestly: if `qrcode` is not importable the QR
  area shows a text hint + an **Install** button that runs
  `py -3 -m pip install qrcode` in the background and auto-refreshes the QR
  on success (no misleading dialog).

### Tests

- `tests/test_phone_profile.py` rewritten for `device_id` keying + legacy
  migration; `tests/test_qrcode_utils.py` added (skips if `qrcode` absent).
- Full suite: 111 passed, 1 skipped.
