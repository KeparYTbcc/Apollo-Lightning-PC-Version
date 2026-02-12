"""
BLE LED Controller Constants

Contains all the protocol constants, UUIDs, and configuration values
for communicating with BLE LED controllers.
"""

# BLE Service and Characteristic UUIDs
# These are standard Nordic Semiconductor UART-like UUIDs
SERVICE_UUID = "0000ffd5-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000ffd9-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "0000ffd4-0000-1000-8000-00805f9b34fb"
DESCRIPTOR_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# Additional UUIDs used by some devices
DEVICE_INFO_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
SERIAL_NUMBER_UUID = "00002a25-0000-1000-8000-00805f9b34fb"
MANUFACTURER_NAME_UUID = "00002a29-0000-1000-8000-00805f9b34fb"

# Device Company Names/Patterns
# Used to identify compatible LED controllers during scanning
COMPANY_NAMES = {
    "APM": r"^APM-|^AP",
    "TRIONES": r"^Triones-|^Triones\+|^Triones",
    "CONSMART": r"Consmart",
    "DREAM": r"^Dream|^Flash",
    "QHM": r"^QHM"
}

# Device name patterns as compiled regex
import re
COMPILED_PATTERNS = {
    name: re.compile(pattern) 
    for name, pattern in COMPANY_NAMES.items()
}

# Lighting Modes (21 modes + extended)
# These correspond to the built-in lighting patterns
MODES = {
    0x25: "Static",
    0x26: "Breathing",
    0x27: "Cross-fade",
    0x28: "Strobe",
    0x29: "Color jump",
    0x2a: "Color cycle",
    0x2b: "Rainbow",
    0x2c: "Wave",
    0x2d: "Candle",
    0x2e: "Fireplace",
    0x2f: "Twinkle",
    0x30: "Sparks",
    0x31: "Plasma",
    0x32: "Mood",
    0x33: "Ocean",
    0x34: "Forest",
    0x35: "Rain",
    0x36: "Music sync 1",
    0x37: "Music sync 2",
    0x38: "Music sync 3",
    0x61: "Custom 1",
    0x62: "Custom 2",
    0x63: "Custom 3"
}

# Mode categories for easier selection
MODE_CATEGORIES = {
    "Static": [0x25],
    "Fading": [0x26, 0x27, 0x32],  # Breathing, Cross-fade, Mood
    "Strobe": [0x28],  # Strobe
    "Color Effects": [0x29, 0x2a, 0x2b, 0x2c],  # Color jump, cycle, rainbow, wave
    "Nature": [0x2d, 0x2e, 0x33, 0x34, 0x35],  # Candle, Fireplace, Ocean, Forest, Rain
    "Special": [0x2f, 0x30, 0x31],  # Twinkle, Sparks, Plasma
    "Music": [0x36, 0x37, 0x38],  # Music sync modes
    "Custom": [0x61, 0x62, 0x63],  # Custom modes
}

# Mode descriptions with speed recommendations
MODE_INFO = {
    0x25: {"name": "Static", "description": "Solid color, no animation", "speed_range": (0, 0)},
    0x26: {"name": "Breathing", "description": "Smooth fade in and out", "speed_range": (5, 200)},
    0x27: {"name": "Cross-fade", "description": "Fade between colors", "speed_range": (5, 200)},
    0x28: {"name": "Strobe", "description": "Rapid blinking", "speed_range": (10, 255)},
    0x29: {"name": "Color jump", "description": "Jump between colors", "speed_range": (10, 200)},
    0x2a: {"name": "Color cycle", "description": "Cycle through colors", "speed_range": (5, 200)},
    0x2b: {"name": "Rainbow", "description": "Rainbow color spectrum", "speed_range": (5, 200)},
    0x2c: {"name": "Wave", "description": "Color wave effect", "speed_range": (10, 200)},
    0x2d: {"name": "Candle", "description": "Candle-like flickering", "speed_range": (20, 150)},
    0x2e: {"name": "Fireplace", "description": "Flickering fire effect", "speed_range": (20, 150)},
    0x2f: {"name": "Twinkle", "description": "Stars twinkle effect", "speed_range": (10, 150)},
    0x30: {"name": "Sparks", "description": "Sparkle effect", "speed_range": (10, 150)},
    0x31: {"name": "Plasma", "description": "Liquid plasma effect", "speed_range": (10, 200)},
    0x32: {"name": "Mood", "description": "Mood lighting transitions", "speed_range": (5, 150)},
    0x33: {"name": "Ocean", "description": "Ocean wave colors", "speed_range": (10, 200)},
    0x34: {"name": "Forest", "description": "Nature green colors", "speed_range": (10, 200)},
    0x35: {"name": "Rain", "description": "Rain drop effect", "speed_range": (10, 200)},
    0x36: {"name": "Music 1", "description": "Music sync - mode 1", "speed_range": (0, 0)},
    0x37: {"name": "Music 2", "description": "Music sync - mode 2", "speed_range": (0, 0)},
    0x38: {"name": "Music 3", "description": "Music sync - mode 3", "speed_range": (0, 0)},
    0x61: {"name": "Custom 1", "description": "User custom pattern", "speed_range": (5, 200)},
    0x62: {"name": "Custom 2", "description": "User custom pattern", "speed_range": (5, 200)},
    0x63: {"name": "Custom 3", "description": "User custom pattern", "speed_range": (5, 200)},
}


def get_mode_name(mode_id: int) -> str:
    """Get the name of a mode by ID."""
    return MODES.get(mode_id, f"Unknown (0x{mode_id:02x})")


def get_mode_info(mode_id: int) -> dict:
    """Get detailed information about a mode."""
    return MODE_INFO.get(mode_id, {
        "name": get_mode_name(mode_id),
        "description": "Unknown mode",
        "speed_range": (0, 255)
    })


def list_modes_by_category() -> dict:
    """List all modes organized by category."""
    result = {}
    for category, mode_ids in MODE_CATEGORIES.items():
        result[category] = []
        for mode_id in mode_ids:
            info = MODE_INFO.get(mode_id, {})
            result[category].append({
                "id": mode_id,
                "name": info.get("name", get_mode_name(mode_id)),
                "description": info.get("description", ""),
                "hex_id": f"0x{mode_id:02x}"
            })
    return result


def list_all_modes() -> list:
    """List all available modes with details."""
    return [
        {
            "id": mode_id,
            "name": info.get("name", name),
            "description": info.get("description", ""),
            "speed_min": info.get("speed_range", (0, 255))[0],
            "speed_max": info.get("speed_range", (0, 255))[1],
            "hex_id": f"0x{mode_id:02x}"
        }
        for mode_id, name in MODES.items()
        for info in [MODE_INFO.get(mode_id, {})]
    ]

# Timer/Schedule Header and Tail Bytes
# Used for timer configuration
TIME_HEAD = bytearray([0x23, 0x25, 0x27, 0x43, 0x45, 0x47])
TIME_TAIL = bytearray([0x32, 0x52, 0x72, 0x34, 0x54, 0x74])

# LED Command Prefixes/Keywords
COMMAND_PREFIX = {
    "SET_COLOR": 0x56,
    "TURN_ON": 0xCC,
    "TURN_OFF": 0xCC,
    "SET_MODE": 0xBB,
    "SET_SPEED": 0xFF,
    "MUSIC_MODE": 0x64,
    "GET_DATA": 0xEF,
    "GET_TIME": 0x24,
    "SET_DATE": 0x10,
    "READ_HUANCAI": 0x1D,
    "READ_QICAI": 0xE5,
}

# Command End/Termination Bytes
COMMAND_TAIL = {
    "COLOR": 0xAA,
    "COLOR_EXT": 0xF0,
    "MODE": 0x44,
    "MUSIC": 0x76,
}

# Default connection parameters
DEFAULT_CONNECTION_PARAMS = {
    "timeout": 10.0,  # seconds
    "scan_duration": 10.0,  # seconds
    "max_connections": 5,
    "mtu_size": 20,  # bytes
    "write_timeout": 5.0,  # seconds
}

# Color profiles for common colors
COMMON_COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "white": (255, 255, 255),
    "warm_white": (0, 0, 0, 255),
    "orange": (255, 165, 0),
    "pink": (255, 105, 180),
    "purple": (128, 0, 128),
    "light_blue": (173, 216, 230),
    "light_green": (144, 238, 144),
}

# Animation speeds
SPEED_SLOW = 20
SPEED_NORMAL = 100
SPEED_FAST = 200

# Brightness levels
BRIGHTNESS_OFF = 0
BRIGHTNESS_LOW = 25
BRIGHTNESS_MEDIUM = 50
BRIGHTNESS_HIGH = 75
BRIGHTNESS_FULL = 100

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL_DEFAULT = "INFO"

# Protocol version
PROTOCOL_VERSION = "1.0.0"
API_VERSION = "1.0.0"

