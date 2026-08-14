# Installation and Runtime Dependencies

## Windows Requirements

- Windows 10 or newer
- Python 3.11 or newer
- A working Python environment for the project
- ViGEmBus for XInput-compatible output
- `vgamepad` Python package
- HidHide for game-exclusive physical-device visibility

## Starting the Client

From the project root, run:

```text
start.cmd
```

The launcher changes to the project directory before starting the GUI, so
configuration paths remain stable when started by double-clicking.

## Installing Dependencies

Install the Python packages:

```text
py -3 -m pip install -r requirements.txt
```

`requirements.txt` pins the runtime dependencies used by the client. Missing
packages are reported at startup in the log and in the GUI warning dialog.

## Dependency Behavior

At startup the client checks:

- `vgamepad`
- ViGEmBus service
- HidHide service or installation registry entries

Missing dependencies are reported in the client and log. The XInput-compatible
output requires vgamepad and ViGEmBus. HidHide is required when a game must not
see a physical source device.

## ESP32 Serial Input

Close Arduino Serial Monitor before starting the client because only one
process can own a COM port. The default firmware baud rate is `115200`.

The firmware sends:

```text
FRAME=1
X=-12000
Y=8000
```

`X` and `Y` are final signed controller-axis values. The client maps them to
`control.right_x` and `control.right_y` and does not apply angle processing.

## Game Testing

For a first test, keep only one controller visible to the game. If both an
Xbox One and an XInput-compatible controller are visible, a game may select the
physical controller automatically. Use HidHide or temporarily disconnect the
physical controller to make the test unambiguous.

## Driver Installation

Drivers must be installed from their official releases and with user consent.
Do not silently install kernel drivers. Keep the corresponding license and
copyright notices with any distributed package.
