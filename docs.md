# LED Controller CLI — Full Documentation

This document explains every feature, command-line option, configuration file, internals, and BLE signals used by the project. It is intended as a complete reference for users and developers.

----

## Table of contents
- Overview
- Quick start / Examples
- CLI reference (detailed flags)
- Presets and configuration file (`.led_controller_config.json`)
- Default MAC behavior and resolution priority
- Building and distribution (PyInstaller notes)
- Internals: `main.py` structure and flow
- Internals: `ble_led_controller` package — important functions and commands
- BLE signals, notifications, and callbacks
- Error handling & troubleshooting
- Frequently asked examples

----

## Overview

This project provides a command-line interface (`main.py`) to control BLE LED controllers compatible with the Apollo Lightning protocol (the phone app: "Apollo Lightning"). The CLI supports scanning for devices, setting RGB/white, brightness, selecting modes, saving and loading color presets, and storing a default MAC address to avoid scanning.

Files of interest:
- `main.py` — the CLI entrypoint
- `README.md` — short intro and quick usage
- `docs.md` — this full reference
- `ble_led_controller/` — the library module that implements BLE commands
- `.led_controller_config.json` — runtime config file (created in script/exe directory)

----

## Quick start / Examples

Install dependencies and run (Windows example):

```powershell
py -m venv env
env\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --scan
python main.py --rgb 255,255,255 --brightness 80
python main.py --on
python main.py --off
```

Save a default MAC so future commands skip scanning:

```powershell
python main.py --default-mac AA:BB:CC:DD:EE:FF
python main.py --on              # uses saved default
```

Save and use presets:

```powershell
python main.py --save SoftPink --rgb 255,182,193 --brightness 85
python main.py --presets
python main.py --load SoftPink --on
```

Build a single exe with PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --onefile --name led-controller --collect-all bleak main.py
# executable: dist\led-controller.exe
```

----

## CLI reference (detailed flags)

All flags are available when running `python main.py [flags]` (or the built exe).

- `--on` : Turn the LED device on (sends power-on command).
- `--off` : Turn the LED device off.
- `--rgb R,G,B` : Set RGB color. Provide values 0–255 comma-separated (exactly three values). Example: `--rgb 255,0,0`.
- `--brightness N` : Brightness percentage 0–100. If used with `--rgb` it is applied to the color command. If used alone it calls the white-only brightness command.
- `--scan` : Scan for available LED controller devices and print a list (name, MAC, RSSI, type). Does not require connecting to a device.
- `--list-modes` : Print the built-in modes (IDs, names, brief description, speed ranges).
- `--set-mode MODE` : Set a lighting mode. `MODE` can be an enum name (e.g., `MODE_1`, `MODE_2`) or a hex ID (e.g., `0x25`). Use `--speed` to additional control animation speed.
- `--speed N` : Speed value 0–255 used with `--set-mode` (default 50).

Device addressing / connection control flags:
- `--mac ADDRESS` : Use the specified MAC address (overrides saved/default). Example: `--mac AA:BB:CC:DD:EE:FF`.
- `--device ADDRESS` : Legacy alias for passing device address.
- `--default-mac ADDRESS` : Save the given MAC as the default in `.led_controller_config.json`. Future runs will use this address if `--mac` is not provided.
- `--remove-default-mac` : Remove the saved default MAC from the config file.

Preset management flags:
- `--save NAME` : Save the color passed with `--rgb` (and optional `--brightness`) under `NAME` in the config file.
- `--presets` or `--colours` : List saved presets.
- `--load NAME` : Load a saved preset and inject its color into the current command execution (you can combine `--load NAME --on` to apply and power on).
- `--remove-preset NAME` : Remove a saved preset by name.

Notes:
- Flags that don't require device connection (like `--presets`, `--default-mac`, `--remove-default-mac`, `--save` and `--remove-preset`) are handled early and will terminate after executing.
- The CLI will auto-discover device address by scanning if no address is provided by `--mac`, `--device` or the saved default.

----

## Presets and configuration file (`.led_controller_config.json`)

Location:
- When running `main.py` the config file is created next to `main.py`.
- When running a built exe, the file is created next to the executable (current working directory behavior applies).

Format example (JSON):

```json
{
  "default_mac": "AA:BB:CC:DD:EE:FF",
  "presets": {
    "SoftPink": { "r": 255, "g": 182, "b": 193, "brightness": 85 },
    "CinemaWarm": { "r": 255, "g": 140, "b": 80, "brightness": 60 }
  }
}
```

Schema summary:
- `default_mac` (string): Optional default device address.
- `presets` (object): Map of preset name -> color object.
  - color object: `{ r: int, g: int, b: int, brightness: int }` (brightness optional, default 100).

Important behavior:
- Setting `--default-mac` writes `default_mac` to the config file and future commands use it automatically unless `--mac`/`--device` is provided.
- `--remove-default-mac` deletes the `default_mac` key from the file.
- `--save NAME --rgb R,G,B` will create/overwrite the named preset.

----

## Default MAC behavior and resolution priority

When connecting, the CLI chooses the target address in this order (highest precedence first):
1. `--mac` parameter
2. `--device` parameter
3. Saved default in `.led_controller_config.json` (created via `--default-mac`)
4. Auto-discovery scan (first discovered device)

Using a default MAC avoids scanning which speeds up execution and is useful for automation.

----

## Building and distribution (PyInstaller notes)

Recommended command to build a single exe (Windows):

```powershell
pyinstaller --onefile --name led-controller --collect-all bleak main.py
```

Notes:
- During the build you may see a warning about `bleak.backends.corebluetooth` or `objc` — these are macOS-only backends and can be safely ignored on Windows.
- The produced `dist/led-controller.exe` is self-contained. The config file will be created next to that exe when it runs.

----

## Internals — `main.py` structure and flow

High-level flow:
1. Parse CLI args with `argparse`.
2. Handle early commands that do not require a device (save default MAC, remove default, preset list/save/remove/load).
3. Determine device address using the priority above.
4. Instantiate `LEDControllerCLI` with `device_address` (can be `None`).
5. For device commands, ensure a connection (connect to provided address or scan to discover one), run commands, and disconnect at the end.

Key functions / objects in `main.py`:
- `load_default_mac()` / `save_default_mac()` / `remove_default_mac()` — manage default MAC in config file.
- `load_presets()` / `save_preset()` / `remove_preset()` / `get_preset()` — presets management helpers.
- `LEDControllerCLI` — class wrapping connection and high-level commands. Important methods:
  - `discover_device(timeout=5)` — scans and returns the first matching device's address.
  - `connect_device(address)` — creates `BLELedController(address)` and calls its `connect()`.
  - `set_rgb(r,g,b,brightness)` — sets an RGB color via `BLELedController.set_rgb()`.
  - `set_mode(mode_name, speed)` — resolves enum or hex ID then calls `BLELedController.set_mode()`.
  - `turn_on()` / `turn_off()` / `set_brightness()` / `scan_devices()` / `list_modes()` — convenience wrappers.

Error handling:
- Early command failures (invalid arguments) print readable error messages and exit with nonzero codes.
- Connection errors are caught and reported; `disconnect()` is run in `finally` blocks where appropriate.

----

## Internals — `ble_led_controller` package (commands and payloads)

The `ble_led_controller` module exposes `BLELedController`, `LEDColor`, and `LEDMode`. Important high-level commands implemented in `ble_controller.py` include:

- `connect(timeout)` / `disconnect()` — manage BLE connection using `bleak`.
- `set_color(LEDColor)` — send color command: command bytes `[0x56, R, G, B, WW, 0xF0, 0xAA]` where WW is warm white.
- `set_rgb(r,g,b,brightness)` — convenience around `LEDColor` + `set_color`.
- `turn_on()` — command bytes `[0xCC, 0x23, 0x33]`.
- `turn_off()` — command bytes `[0xCC, 0x24, 0x33]`.
- `set_mode(LEDMode, speed)` — command bytes `[0xBB, mode_byte, speed, 0x44]`.
- `set_mode_by_id(mode_id, speed)` — resolves numeric mode id then calls `set_mode`.
- `set_music_mode(red, green, mic_on)` — music sync command (two variants depending on mic_on).
- `get_light_data()` — query light status: `[0xEF, 0x01, 0x77]`.
- `get_time_data()` / `set_date_time(...)` — time queries and setters (device-specific format).
- `set_timer(index, hour, minute, ...)` — schedule timers.
- `set_speed(speed)` — set animation speed (uses `0xFF` pseudo-mode in this implementation).
- `read_huancai()` / `read_qicai()` — device-specific reads.
- `set_white_mode(brightness)` — white-only command: `[0x56, 0x00, 0x00, 0x00, WW, 0xF0, 0xAA]`.

Enums and helpers:
- `LEDColor` — dataclass with red/green/blue/warm_white/brightness and helpers `from_rgb`/`from_rgbw`.
- `LEDMode` — Enum mapping human-readable mode names to device numeric IDs. `LEDMode.from_id(mode_id)` resolves ID to enum.

Note: exact command byte structure is implemented inside `BLELedController`. If you need to extend or debug, consult `ble_led_controller/ble_controller.py`.

----

## BLE signals, notifications, and callbacks

The library supports notifications from the device via a GATT notify characteristic. Key points:

- `BLELedController._notification_handler(self, characteristic, data)` is registered when connected and simply forwards raw `bytearray` payloads to any registered callbacks.
- Use `BLELedController.add_notification_callback(callback)` to register a function that receives `data: bytearray` for processing device notifications (e.g., status updates, timers, sensor input from music mode).
- Use `remove_notification_callback(callback)` to unregister.

Notification format is device-specific. The project preserves raw bytes and leaves parsing to user code; typical messages come from the controller firmware and may include status responses, mode confirmations, or sensor values.

If you want automatic parsing, add a helper callback that inspects `data.hex()` or individual bytes, and maps known response formats (investigate with a logic/logging callback while interacting with the device).

----

## Error handling & troubleshooting

- `bleak` not installed: ensure you run the CLI with the correct Python interpreter (use `python` inside an activated venv). On Windows, avoid the `py` launcher if it chooses a different interpreter.
- Connection failures: check device is powered, in Bluetooth range, and not connected to another device (phone app may lock it). Use `--scan` to verify RSSI and that device is visible.
- PyInstaller warnings: macOS backend warnings for `corebluetooth` are normal on Windows.
- If preset/config file becomes corrupted JSON, delete `.led_controller_config.json` or back it up and fix manually.

----

## Frequently asked examples

- Apply a saved preset and keep the device off (only set color):

```powershell
python main.py --load SoftPink
```

- Apply a saved preset and turn device on:

```powershell
python main.py --load SoftPink --on
```

- Set default device and run commands quickly:

```powershell
python main.py --default-mac AA:BB:CC:DD:EE:FF
python main.py --rgb 255,255,255 --brightness 100
```

- Remove preset and default MAC:

```powershell
python main.py --remove-preset SoftPink
python main.py --remove-default-mac
```

----

## Developer notes and extending the project

- To add more high-level commands, extend `LEDControllerCLI` and call `BLELedController` methods. Keep CLI argument parsing in `main()` and add early handlers for non-device commands.
- To add parsed notification handlers, register callbacks with `BLELedController.add_notification_callback()` after `connect()`.
- To support additional device models or modes, extend `LEDMode` or add mapping utilities in `ble_led_controller/constants.py`.

----

