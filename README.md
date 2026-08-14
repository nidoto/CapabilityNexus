# CapabilityNexus

CapabilityNexus is an open-source real-world input abstraction layer.
It connects sensors, controllers and custom hardware to applications through
capability-based mapping and XInput-compatible output.

## Positioning

CapabilityNexus is not an Xbox emulator and does not replace vendor drivers.
It is an input/output routing layer:

```text
Physical device -> CapabilityNexus -> XInput-compatible controller -> Game
```

The application can combine multiple sources. For example, an Xbox controller
can provide buttons and triggers while an ESP32 motion sensor controls the
right stick of the XInput-compatible controller.

## Features

- XInput, HID, serial, TCP, UDP, Bluetooth, FTMS and ANT input sources
- XInput-compatible, keyboard, mouse and DualShock-compatible outputs
- Capability registry and configurable mappings
- Processor pipeline with normalization, deadzone, sensitivity and clamp
- Runtime input/output monitoring
- Reverse request capture for controller feedback such as rumble
- ESP32/BNO085 Arduino firmware example
- Device library and game request library integration
- Optional HidHide integration for game-exclusive device visibility

## Quick Start

1. Install Python 3.11 or newer.
2. Install project dependencies and Windows drivers.
3. Double-click `start.cmd`.
4. Connect an input device from the device tree context menu.
5. Configure mappings by double-clicking a capability.
6. Configure the target game to use the XInput-compatible controller.

The client checks `vgamepad`, ViGEmBus and HidHide at startup. ViGEmBus is
required for XInput-compatible output. HidHide is required only when physical
inputs must be hidden from a game while remaining available to the client.

## ESP32 Protocol

The included firmware sends final controller-axis values after calibration and
range handling:

```text
FRAME=42
X=-12000
Y=8000
```

`X` and `Y` are signed XInput axis values in the range `-32768..32767`.
The client forwards them as `control.right_x` and `control.right_y`; sensor
algorithm work remains in the firmware.

## Documentation

- [Product Overview](docs/PRODUCT_OVERVIEW.md)
- [Installation and Runtime Dependencies](docs/INSTALLATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development Log](docs/DEVELOPMENT_LOG_V1.7.0.md)
- [Documentation Index](docs/README.md)
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)

## License

See the repository license and [third-party notices](THIRD_PARTY_NOTICES.md).
