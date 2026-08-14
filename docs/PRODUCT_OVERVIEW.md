# CapabilityNexus Product Overview

## What It Is

CapabilityNexus is an open-source bridge between real-world devices and
digital applications. It turns device data into named capabilities, processes
those capabilities and routes them to standard application inputs.

The product is designed around capabilities rather than hardware brands:

```text
ESP32 / IMU / Xbox / HID / trainer / custom sensor
                         |
                         v
                CapabilityNexus Core
                         |
                         v
       XInput-compatible controller / keyboard / mouse
                         |
                         v
                    Game / App
```

## Product Principles

- Hardware produces capabilities; it does not know the target game.
- Games receive standard compatible outputs rather than vendor-specific data.
- The client remains open and extensible.
- Private device algorithms can remain inside closed firmware.
- Input and feedback are both first-class directions.
- Device isolation is explicit and user-controlled.

## Typical Scenarios

### Motion Camera Control

An ESP32 with a BNO085 calculates orientation in firmware and sends final
signed controller-axis values. CapabilityNexus forwards them to the right
stick of an XInput-compatible controller. A game can use that right stick for
camera control.

### Existing Controller Enhancement

An Xbox One controller supplies buttons, triggers and the left stick while an
ESP32 supplies camera or motion axes. Mapping combines both sources into one
compatible output device.

### Feedback Capture

When a game sends a rumble request to the XInput-compatible output, the client
can capture the left and right motor values as reverse requests. These requests
can be displayed, logged or routed to another supported output.

## Device Visibility

Windows may expose both the physical input device and the XInput-compatible
output to a game. If a game must see only the compatible output, HidHide can
hide the physical device from that game while allowing CapabilityNexus to read
it. This is an optional Windows integration and requires user consent,
administrator privileges and possibly a reboot.

## Privacy and IP Boundary

The open client handles transport, capability registration, processing and
routing. A closed hardware device may perform calibration, sensor fusion,
filtering and proprietary algorithms internally. The recommended firmware
boundary is to send only final control values, not raw sensor streams.

## Current Status

- Core event pipeline: operational
- XInput-compatible output: operational with ViGEmBus
- Xbox and ESP32 serial input: operational
- Runtime input/output monitoring: operational
- Reverse rumble request capture: operational
- Dependency detection: operational
- HidHide configuration workflow: integration in progress
- Hardware and game compatibility: requires per-device testing
