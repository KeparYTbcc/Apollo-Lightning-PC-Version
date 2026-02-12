# BLE LED Controller Python Module

A Python module for controlling Bluetooth Low Energy (BLE) LED controllers. This module was reverse-engineered from Android APK analysis to provide a clean Python interface for controlling compatible LED light strips.

## Supported Controllers

This module supports the following LED controller brands and naming patterns:

- **APM Series**: Names starting with `APM-` or `AP`
- **Triones Series**: Names starting with `Triones-`, `Triones+`, or `Triones`
- **Consmart Series**: Names containing `Consmart`
- **Dream/Flash Series**: Names starting with `Dream` or `Flash`
- **QHM Series**: Names starting with `QHM`

## Installation

1. Install the required dependency:
```bash
pip install bleak
```

2. Install the module:
```bash
# From source
pip install .
```

## Quick Start

```python
import asyncio
from ble_led_controller import BLELedController, LEDColor

async def main():
    # Create controller instance
    controller = BLELedController("XX:XX:XX:XX:XX:XX", "MyLEDStrip")
    
    # Connect
    await controller.connect()
    
    # Turn on and set color
    await controller.turn_on()
    await controller.set_rgb(255, 0, 0)  # Red
    await asyncio.sleep(2)
    
    # Change color
    await controller.set_rgb(0, 255, 0)  # Green
    await asyncio.sleep(2)
    
    # Turn off
    await controller.turn_off()
    
    # Disconnect
    await controller.disconnect()

asyncio.run(main())
```

## Finding Your Device

Use the scanner to find LED controllers:

```python
import asyncio
from ble_led_controller import DeviceScanner

async def find_devices():
    scanner = DeviceScanner()
    devices = await scanner.scan_and_print(duration=10)
    return devices

asyncio.run(find_devices())
```

## API Reference

### BLELedController

The main class for controlling LED controllers.

#### Constructor
```python
controller = BLELedController(address: str, name: Optional[str] = None)
```

**Parameters:**
- `address`: Bluetooth MAC address (e.g., "AA:BB:CC:DD:EE:FF")
- `name`: Optional device name for logging purposes

#### Connection Methods

```python
# Connect to device
await controller.connect(timeout=10.0)

# Disconnect from device
await controller.disconnect()

# Check connection status
if controller.is_connected:
    print("Connected")
```

#### Color Control

```python
# Set RGB color
await controller.set_rgb(red, green, blue, brightness=100)

# Set full color with warm white
color = LEDColor(red=255, green=100, blue=50, warm_white=128, brightness=80)
await controller.set_color(color)

# White-only mode
await controller.set_white_mode(brightness=100)

# Turn on/off
await controller.turn_on()
await controller.turn_off()
```

#### Mode Control

```python
# Set built-in mode by enum
from ble_led_controller import LEDMode
await controller.set_mode(LEDMode.BREATHING, speed=100)

# Set mode by numeric ID
await controller.set_mode_by_id(0x2b, speed=50)

# Set animation speed
await controller.set_speed(150)
```

#### Music Sync

```python
# Enable music sync with microphone
await controller.set_music_mode(255, 128, mic_on=True)

# Enable music sync with line-in
await controller.set_music_mode(255, 128, mic_on=False)
```

#### Timer/Schedule

```python
# Set timer (index 0-5)
await controller.set_timer(
    index=0,
    hour=7,
    minute=30,
    weekday=0x1F,  # Monday-Friday
    enabled=True,
    turn_on=True
)
```

#### Date/Time Sync

```python
# Set device date/time
await controller.set_date_time(
    year=2024,
    month=1,
    day=15,
    hour=12,
    minute=30,
    second=0,
    weekday=1  # Monday
)
```

### LEDColor

Data class for representing colors.

```python
# Create from RGB
color = LEDColor.from_rgb(255, 128, 0, brightness=100)

# Create from RGBW
color = LEDColor.from_rgbw(255, 128, 0, 64, brightness=80)

# Get hex value
hex_color = color.to_hex()  # "#ff8000"
```

### LEDMode

Enum for built-in lighting modes.

```python
from ble_led_controller import LEDMode

# Available modes
LEDMode.MODE_1   # 0x25 - Static
LEDMode.MODE_2   # 0x26 - Breathing
LEDMode.MODE_3   # 0x27 - Cross-fade
LEDMode.MODE_11  # 0x2f - Twinkle
# ... and more
```

### DeviceScanner

For discovering BLE LED controllers.

```python
# Create scanner
scanner = DeviceScanner()

# Scan for devices
devices = await scanner.scan(duration=10, led_only=True)

# Scan with auto-retry
devices = await scanner.scan_with_retry(max_retries=3)

# Get supported device types
types = scanner.get_supported_types()
```

## Protocol Details

### BLE UUIDs

- **Service UUID**: `0000ffd5-0000-1000-8000-00805f9b34fb`
- **Write Characteristic**: `0000ffd9-0000-1000-8000-00805f9b34fb`
- **Notify Characteristic**: `0000ffd4-0000-1000-8000-00805f9b34fb`

### Command Formats

| Function | Command Bytes |
|----------|---------------|
| Set Color | `[0x56, R%, G%, B%, WW%, 0xF0, 0xAA]` |
| Turn On | `[0xCC, 0x23, 0x33]` |
| Turn Off | `[0xCC, 0x24, 0x33]` |
| Set Mode | `[0xBB, mode, speed, 0x44]` |
| Music Mode | `[0x64, 0xF0, R, G, 0x00, 0xF0, 0x76]` |
| Get Data | `[0xEF, 0x01, 0x77]` |

## Requirements

- Python 3.7+
- bleak >= 0.20.0
- Operating System with BLE support:
  - Windows 10/11 with Bluetooth 4.0+
  - Linux with BlueZ
  - macOS

## Platform-Specific Notes

### Windows
- Ensure Bluetooth is enabled
- May require administrator privileges on some systems
- Use format: "XX:XX:XX:XX:XX:XX"

### Linux
- Requires BlueZ installed: `sudo apt install bluez`
- May need Bluetooth permissions: `sudo usermod -aG bluetooth $USER`

### macOS
- Works out of the box with built-in Bluetooth

## License

MIT License

## Credits

Protocol reverse-engineered from Android application analysis.

