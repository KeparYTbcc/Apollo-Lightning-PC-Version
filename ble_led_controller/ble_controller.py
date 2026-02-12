"""
BLE LED Controller Class

Main class for communicating with BLE LED controllers.
Handles connection, color setting, mode control, and other operations.
"""

import asyncio
import logging
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .constants import (
    SERVICE_UUID,
    WRITE_CHAR_UUID,
    NOTIFY_CHAR_UUID,
    COMPANY_NAMES,
    TIME_HEAD,
    TIME_TAIL
)

logger = logging.getLogger(__name__)

# Try to import bleak for BLE communication
try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.characteristic import BleakGATTCharacteristic
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    BleakClient = None
    BleakScanner = None
    BleakGATTCharacteristic = object  # Fallback for type hints


@dataclass
class LEDColor:
    """Represents an LED color with RGBW values and brightness."""
    red: int = 0          # 0-255
    green: int = 0        # 0-255
    blue: int = 0        # 0-255
    warm_white: int = 0   # 0-255
    brightness: int = 100 # 0-100 percentage
    
    def __post_init__(self):
        """Validate and clamp values."""
        self.red = max(0, min(255, self.red))
        self.green = max(0, min(255, self.green))
        self.blue = max(0, min(255, self.blue))
        self.warm_white = max(0, min(255, self.warm_white))
        self.brightness = max(0, min(100, self.brightness))
    
    @classmethod
    def from_rgb(cls, red: int, green: int, blue: int, brightness: int = 100):
        """Create LEDColor from RGB values."""
        return cls(red=red, green=green, blue=blue, brightness=brightness)
    
    @classmethod
    def from_rgbw(cls, red: int, green: int, blue: int, warm_white: int, brightness: int = 100):
        """Create LEDColor from RGBW values."""
        return cls(red=red, green=green, blue=blue, warm_white=warm_white, brightness=brightness)
    
    def to_hex(self) -> str:
        """Return hex color string."""
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"


class LEDMode(Enum):
    """Predefined LED lighting modes."""
    MODE_1 = 0x25  # Static
    MODE_2 = 0x26  # Breathing
    MODE_3 = 0x27  # Cross-fade
    MODE_4 = 0x28  # Strobe
    MODE_5 = 0x29  # Color jump
    MODE_6 = 0x2a  # Color cycle
    MODE_7 = 0x2b  # Rainbow
    MODE_8 = 0x2c  # Wave
    MODE_9 = 0x2d  # Candle
    MODE_10 = 0x2e  # Fireplace
    MODE_11 = 0x2f  # Twinkle
    MODE_12 = 0x30  # Sparks
    MODE_13 = 0x31  # Plasma
    MODE_14 = 0x32  # Mood
    MODE_15 = 0x33  # Ocean
    MODE_16 = 0x34  # Forest
    MODE_17 = 0x35  # Rain
    MODE_18 = 0x36  # Music sync 1
    MODE_19 = 0x37  # Music sync 2
    MODE_20 = 0x38  # Music sync 3
    MODE_21 = 0x61  # Custom 1
    MODE_22 = 0x62  # Custom 2
    MODE_23 = 0x63  # Custom 3
    
    @classmethod
    def from_id(cls, mode_id: int) -> 'LEDMode':
        """Get mode from numeric ID."""
        for mode in cls:
            if mode.value == mode_id:
                return mode
        raise ValueError(f"Invalid mode ID: {mode_id}")


class BLELedController:
    """
    Main class for controlling BLE LED controllers.
    
    Usage:
        controller = BLELedController("XX:XX:XX:XX:XX:XX")
        await controller.connect()
        await controller.set_color(255, 0, 0)  # Red
        await controller.disconnect()
    """
    
    # Class-level device cache
    _device_cache: Dict[str, 'BLELedController'] = {}
    
    def __init__(self, address: str, name: Optional[str] = None):
        """
        Initialize the LED controller.
        
        Args:
            address: Bluetooth MAC address (e.g., "XX:XX:XX:XX:XX:XX")
            name: Optional device name for logging
        """
        self.address = address.upper()
        self.name = name
        self._client = None
        self._connected = False
        self._notify_callbacks: List[callable] = []
        
        # Cache instance
        BLELedController._device_cache[address] = self
    
    def __repr__(self):
        return f"<BLELedController addr={self.address} name={self.name} connected={self._connected}>"
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to the device."""
        return self._connected and self._client is not None
    
    async def connect(self, timeout: float = 10.0) -> None:
        """
        Connect to the BLE device.
        
        Args:
            timeout: Connection timeout in seconds
            
        Raises:
            ConnectionError: If connection fails
        """
        if not BLEAK_AVAILABLE:
            raise ImportError("bleak library not installed. Run: pip install bleak")
        
        try:
            self._client = BleakClient(self.address, timeout=timeout)
            await self._client.connect()
            self._connected = True
            
            # Set up notification handler
            await self._client.start_notify(NOTIFY_CHAR_UUID, self._notification_handler)
            
            logger.info(f"Connected to {self.address}")
            
        except Exception as e:
            self._connected = False
            self._client = None
            raise ConnectionError(f"Failed to connect to {self.address}: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the BLE device."""
        if self._client and self._connected:
            try:
                await self._client.stop_notify(NOTIFY_CHAR_UUID)
                await self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connected = False
                self._client = None
                logger.info(f"Disconnected from {self.address}")
    
    def _notification_handler(self, characteristic, data: bytearray) -> None:
        """Handle notifications from the device."""
        logger.debug(f"Notification from {characteristic.uuid}: {data.hex()}")
        for callback in self._notify_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Notification callback error: {e}")
    
    def add_notification_callback(self, callback: callable) -> None:
        """Add a callback for device notifications."""
        self._notify_callbacks.append(callback)
    
    def remove_notification_callback(self, callback: callable) -> None:
        """Remove a notification callback."""
        if callback in self._notify_callbacks:
            self._notify_callbacks.remove(callback)
    
    async def _write_command(self, data: bytearray) -> bool:
        """
        Write a command to the LED controller.
        
        Args:
            data: Command byte array
            
        Returns:
            True if write was successful
            
        Raises:
            CommandError: If write fails
        """
        if not self._connected or not self._client:
            raise CommandError("Not connected to device")
        
        try:
            await self._client.write_gatt_char(WRITE_CHAR_UUID, data)
            logger.debug(f"Written: {data.hex()}")
            return True
        except Exception as e:
            raise CommandError(f"Write failed: {e}")
    
    async def set_color(self, color: LEDColor) -> bool:
        """
        Set the LED color.
        
        Args:
            color: LEDColor object with RGBW values
            
        Returns:
            True if successful
        """
        # Calculate color values based on brightness
        brightness_factor = color.brightness / 100.0
        
        red = int(color.red * brightness_factor)
        green = int(color.green * brightness_factor)
        blue = int(color.blue * brightness_factor)
        warm_white = int(color.warm_white * brightness_factor)
        
        # Build command: [0x56, R, G, B, WW, 0xF0, 0xAA]
        command = bytearray([
            0x56,
            red & 0xFF,
            green & 0xFF,
            blue & 0xFF,
            warm_white & 0xFF,
            0xF0,
            0xAA
        ])
        
        return await self._write_command(command)
    
    async def set_rgb(self, red: int, green: int, blue: int, brightness: int = 100) -> bool:
        """
        Set RGB color with brightness.
        
        Args:
            red: Red value (0-255)
            green: Green value (0-255)
            blue: Blue value (0-255)
            brightness: Brightness percentage (0-100)
            
        Returns:
            True if successful
        """
        color = LEDColor.from_rgb(red, green, blue, brightness)
        return await self.set_color(color)
    
    async def turn_on(self) -> bool:
        """
        Turn on the LED.
        
        Returns:
            True if successful
        """
        command = bytearray([0xCC, 0x23, 0x33])
        return await self._write_command(command)
    
    async def turn_off(self) -> bool:
        """
        Turn off the LED.
        
        Returns:
            True if successful
        """
        command = bytearray([0xCC, 0x24, 0x33])
        return await self._write_command(command)
    
    async def set_mode(self, mode: LEDMode, speed: int = 50) -> bool:
        """
        Set the lighting mode/pattern.
        
        Args:
            mode: LEDMode enum value
            speed: Animation speed (0-255, higher is faster)
            
        Returns:
            True if successful
        """
        speed = max(0, min(255, speed))
        
        # Command: [0xBB, mode_byte, speed, 0x44]
        command = bytearray([
            0xBB,
            mode.value,
            speed & 0xFF,
            0x44
        ])
        
        return await self._write_command(command)
    
    async def set_mode_by_id(self, mode_id: int, speed: int = 50) -> bool:
        """
        Set mode by numeric ID.
        
        Args:
            mode_id: Mode ID (0x25-0x63)
            speed: Animation speed (0-255)
            
        Returns:
            True if successful
        """
        mode = LEDMode.from_id(mode_id)
        return await self.set_mode(mode, speed)
    
    async def set_music_mode(self, red: int, green: int, mic_on: bool = True) -> bool:
        """
        Enable music sync mode.
        
        Args:
            red: Red component
            green: Green component
            mic_on: Use microphone input (True) or audio line-in (False)
            
        Returns:
            True if successful
        """
        if mic_on:
            command = bytearray([0x64, 0xF0, red & 0xFF, green & 0xFF, 0x00, 0xF0, 0x76])
        else:
            command = bytearray([0x64, 0x0F, red & 0xFF, green & 0xFF, 0x00, 0x0F, 0x76])
        
        return await self._write_command(command)
    
    async def get_light_data(self) -> bool:
        """
        Query the current light status.
        
        Returns:
            True if command sent successfully
        """
        command = bytearray([0xEF, 0x01, 0x77])
        return await self._write_command(command)
    
    async def get_time_data(self) -> bool:
        """
        Query the device's time/timer data.
        
        Returns:
            True if command sent successfully
        """
        command = bytearray([0x24, 0x2A, 0x2B, 0x42])
        return await self._write_command(command)
    
    async def set_date_time(self, year: int, month: int, day: int, 
                           hour: int, minute: int, second: int,
                           weekday: int = 0) -> bool:
        """
        Set the device's date and time.
        
        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)
            day: Day (1-31)
            hour: Hour (0-23)
            minute: Minute (0-59)
            second: Second (0-59)
            weekday: Day of week (0=Sunday, 1=Monday, etc.)
            
        Returns:
            True if successful
        """
        # Build 17-byte date command
        command = bytearray([
            0x10,  # Command prefix
            0x14,  # Year high byte (20)
            second & 0xFF,
            minute & 0xFF,
            hour & 0xFF,
            day & 0xFF,
            month & 0xFF,
            year % 100,  # Year low byte
            weekday & 0xFF,
            0x00,  # Reserved
            0x00,  # Reserved
        ])
        
        return await self._write_command(command)
    
    async def set_timer(self, index: int, hour: int, minute: int, 
                       second: int = 0, weekday: int = 0xFF,
                       enabled: bool = True, turn_on: bool = True) -> bool:
        """
        Set a timer/schedule.
        
        Args:
            index: Timer index (0-5)
            hour: Hour (0-23)
            minute: Minute (0-59)
            second: Second (0-59)
            weekday: Day of week bitmask (bit 0=Sunday, bit 1=Monday, etc.)
            enabled: Enable this timer
            turn_on: Turn on (True) or off (False) at timer time
            
        Returns:
            True if successful
        """
        if index < 0 or index > 5:
            raise ValueError("Timer index must be 0-5")
        
        # Build 8-byte timer command
        valid_byte = 0xF0 if enabled else 0x0F
        on_off_byte = 0xF0 if turn_on else 0x0F
        
        command = bytearray([
            TIME_HEAD[index],
            TIME_HEAD[index],
            valid_byte,
            hour & 0xFF,
            minute & 0xFF,
            second & 0xFF,
            weekday & 0xFF,
            on_off_byte
        ])
        
        return await self._write_command(command)
    
    async def set_speed(self, speed: int) -> bool:
        """
        Set animation speed for current mode.
        
        Args:
            speed: Speed value (0-255, higher is faster)
            
        Returns:
            True if successful
        """
        speed = max(0, min(255, speed))
        
        # Use mode 0xFF with speed
        command = bytearray([0xFF, speed & 0xFF, 0x00, 0x00])
        return await self._write_command(command)
    
    async def read_huancai(self) -> bool:
        """
        Read color data from device.
        
        Returns:
            True if command sent successfully
        """
        command = bytearray([0x1D, 0xF0, 0x00, 0xF1])
        return await self._write_command(command)
    
    async def read_qicai(self) -> bool:
        """
        Read device information and configuration.
        
        Returns:
            True if command sent successfully
        """
        command = bytearray([0xE5, 0xF0, 0x5E])
        return await self._write_command(command)
    
    async def set_white_mode(self, brightness: int = 100) -> bool:
        """
        Set white-only mode (warm white LED).
        
        Args:
            brightness: Brightness (0-100)
            
        Returns:
            True if successful
        """
        ww_value = int((brightness / 100.0) * 255)
        
        # Command: [0x56, 0x00, 0x00, 0x00, WW, 0xF0, 0xAA]
        command = bytearray([
            0x56,
            0x00,
            0x00,
            0x00,
            ww_value & 0xFF,
            0xF0,
            0xAA
        ])
        
        return await self._write_command(command)
    
    async def fade_to_color(self, color: LEDColor, duration_ms: int = 500) -> bool:
        """
        Gradually fade to a color.
        
        Note: This is a convenience method. The actual fade
        smoothness depends on the controller's mode.
        
        Args:
            color: Target LEDColor
            duration_ms: Fade duration in milliseconds
            
        Returns:
            True if successful
        """
        # For smooth fading, we could implement gradual color transitions
        # For now, just set the target color
        return await self.set_color(color)
    
    @classmethod
    def get_cached_controller(cls, address: str) -> Optional['BLELedController']:
        """
        Get a cached controller instance by address.
        
        Args:
            address: Device MAC address
            
        Returns:
            Cached controller or None
        """
        return cls._device_cache.get(address.upper())
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached controller instances."""
        cls._device_cache.clear()


# Custom exceptions for error handling
class LEDControllerError(Exception):
    """Base exception for LED controller errors."""
    pass


class ConnectionError(LEDControllerError):
    """Exception raised when connection fails."""
    pass


class CommandError(LEDControllerError):
    """Exception raised when a command fails."""
    pass

