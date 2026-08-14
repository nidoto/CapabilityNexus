# Third-Party Components

CapabilityNexus can use the following third-party components. Licenses are
MIT unless stated otherwise. Source and license notices must remain
identifiable in any distributed package.

## Kernel Drivers (Windows)

Drivers are installed from their official releases only, with user consent.
Administrator privileges or a system reboot may be required.

### HidHide

- Project: https://github.com/nefarius/HidHide
- License: MIT
- Purpose: hide selected physical input devices from selected applications
- Source and license must remain identifiable in any distributed package.

### ViGEmBus

- Project: https://github.com/nefarius/ViGEmBus
- Purpose: provide the XInput-compatible controller backend
- Distribute only an official release (or a vendor-verified copy such as the
  1.21.442.0 driver shipped with a key remapper) and include its license and
  notices.

## Python Packages

Installed via `requirements.txt`. Keep each package's license and copyright
notices with distributed copies.

### vgamepad

- Project: https://github.com/yannbizeul/pyvgamepad
- License: MIT
- Purpose: Python binding that sends reports to the XInput-compatible backend

### pyserial

- Project: https://github.com/pyserial/pyserial
- License: BSD-3-Clause
- Purpose: USB serial communication (ESP32, Arduino and other boards)

### pygame

- Project: https://www.pygame.org/
- License: LGPL-2.1
- Purpose: generic USB HID input (gamepads, wheels, joysticks)

### bleak

- Project: https://github.com/hbldh/bleak
- License: MIT
- Purpose: Bluetooth Low Energy (FTMS cycling trainers)

### openant

- Project: https://github.com/Tigge/openant
- License: MIT
- Purpose: ANT+ cycling devices (requires a USB ANT+ adapter)

### pynput

- Project: https://github.com/moses-palmer/pynput
- License: LGPL-3.0
- Purpose: virtual keyboard and mouse output

## Notes

CapabilityNexus does not claim ownership of these components. Driver
installation is optional, requires user consent and may require administrator
privileges or a reboot.
