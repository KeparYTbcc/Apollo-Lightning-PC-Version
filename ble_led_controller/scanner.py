"""
BLE Device Scanner

Provides functionality to scan for and discover BLE LED controllers.
"""

import asyncio
import logging
import importlib
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

from .constants import COMPANY_NAMES, COMPILED_PATTERNS

logger = logging.getLogger(__name__)

# Check for bleak availability and get version safely
BLEAK_AVAILABLE = False
BLEAK_VERSION = (0, 0)

try:
    import bleak
    BLEAK_AVAILABLE = True
    try:
        # Try to get version from version attribute
        BLEAK_VERSION = tuple(int(x) for x in bleak.__version__.split('.')[:2])
    except (AttributeError, ValueError):
        try:
            # Fallback: try importlib.metadata
            from importlib.metadata import version
            BLEAK_VERSION = tuple(int(x) for x in version('bleak').split('.')[:2])
        except:
            BLEAK_VERSION = (0, 20)  # Default to newer API
except ImportError:
    pass


@dataclass
class ScannedDevice:
    """Represents a scanned BLE device."""
    address: str
    name: Optional[str] = None
    rssi: int = 0
    manufacturer_data: bytes = None
    service_data: Dict[str, bytes] = field(default_factory=dict)
    service_uuids: List[str] = field(default_factory=list)
    is_led_controller: bool = False
    device_type: str = "unknown"
    
    def __post_init__(self):
        """Identify if this is an LED controller."""
        if self.name:
            for device_type, pattern in COMPILED_PATTERNS.items():
                if pattern.search(self.name):
                    self.is_led_controller = True
                    self.device_type = device_type
                    break
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "address": self.address,
            "name": self.name,
            "rssi": self.rssi,
            "is_led_controller": self.is_led_controller,
            "device_type": self.device_type
        }


class DeviceScanner:
    """
    Scanner for discovering BLE LED controllers.
    
    Usage:
        scanner = DeviceScanner()
        devices = await scanner.scan(duration=10)
        for device in devices:
            if device.is_led_controller:
                print(f"Found: {device.name} ({device.address})")
    """
    
    def __init__(self):
        """Initialize the scanner."""
        self._scan_callbacks: List[Callable[[ScannedDevice], None]] = []
        self._scanner = None
        
        if BLEAK_AVAILABLE:
            try:
                from bleak import BleakScanner
                self._scanner = BleakScanner()
            except Exception as e:
                logger.error(f"Failed to initialize scanner: {e}")
    
    def add_discovered_callback(self, callback: Callable[[ScannedDevice], None]) -> None:
        """
        Add a callback for when devices are discovered.
        
        Args:
            callback: Function to call with ScannedDevice on discovery
        """
        self._scan_callbacks.append(callback)
    
    def remove_discovered_callback(self, callback: Callable[[ScannedDevice], None]) -> None:
        """
        Remove a discovered callback.
        
        Args:
            callback: The callback function to remove
        """
        if callback in self._scan_callbacks:
            self._scan_callbacks.remove(callback)
    
    async def scan(self, duration: float = 10.0, 
                   led_only: bool = True) -> List[ScannedDevice]:
        """
        Scan for BLE devices.
        
        Args:
            duration: Scan duration in seconds
            led_only: If True, return only LED controllers
            
        Returns:
            List of discovered devices
        """
        if not BLEAK_AVAILABLE:
            raise ImportError("bleak library not installed. Run: pip install bleak")
        
        devices: Dict[str, ScannedDevice] = {}
        
        try:
            from bleak import BleakScanner
            
            # Use the discover method for newer bleak versions
            discovered = await BleakScanner.discover(timeout=duration)
            
            for device in discovered:
                address = device.address
                name = getattr(device, 'name', None) or "Unknown"
                rssi = getattr(device, 'rssi', 0)
                
                if address not in devices:
                    devices[address] = ScannedDevice(
                        address=address,
                        name=name,
                        rssi=rssi
                    )
                
                devices[address].__post_init__()
                
        except Exception as e:
            logger.error(f"Scanning error: {e}")
            # Fallback to older method if available
            try:
                await self._legacy_scan(duration, devices)
            except Exception as e2:
                logger.error(f"Legacy scan also failed: {e2}")
        
        # Filter results
        results = list(devices.values())
        if led_only:
            results = [d for d in results if d.is_led_controller]
        
        # Sort by RSSI (strongest first)
        results.sort(key=lambda d: d.rssi, reverse=True)
        
        return results
    
    async def _legacy_scan(self, duration: float, devices: Dict[str, ScannedDevice]) -> None:
        """Legacy scanning method for older bleak versions."""
        from bleak import BleakScanner
        
        def detection_callback(device, advertisement_data):
            """Handle device detection."""
            address = device.address
            name = device.name or advertisement_data.local_name or "Unknown"
            rssi = advertisement_data.rssi
            
            if address not in devices:
                devices[address] = ScannedDevice(
                    address=address,
                    name=name,
                    rssi=rssi
                )
            
            devices[address].service_uuids = list(advertisement_data.service_uuids)
            devices[address].__post_init__()
            
            for callback in self._scan_callbacks:
                try:
                    callback(devices[address])
                except Exception as e:
                    logger.error(f"Scan callback error: {e}")
        
        scanner = BleakScanner()
        await scanner.start()
        await asyncio.sleep(duration)
        await scanner.stop()
    
    async def scan_and_print(self, duration: float = 10.0) -> List[ScannedDevice]:
        """
        Scan for devices and print results.
        
        Args:
            duration: Scan duration in seconds
            
        Returns:
            List of discovered LED controllers
        """
        print(f"Scanning for {duration} seconds...")
        print("-" * 60)
        
        devices = await self.scan(duration=duration, led_only=True)
        
        if not devices:
            print("No LED controllers found.")
        else:
            print(f"Found {len(devices)} LED controller(s):")
            for i, device in enumerate(devices, 1):
                rssi_bar = self._rssi_to_bar(device.rssi)
                print(f"  {i}. {device.name} ({device.address})")
                print(f"     Type: {device.device_type} | Signal: {device.rssi} dBm {rssi_bar}")
        
        print("-" * 60)
        return devices
    
    def _rssi_to_bar(self, rssi: int) -> str:
        """Convert RSSI to a visual bar."""
        if rssi >= -50:
            return "██████"
        elif rssi >= -60:
            return "█████ "
        elif rssi >= -70:
            return "████  "
        elif rssi >= -80:
            return "███   "
        elif rssi >= -90:
            return "██    "
        else:
            return "█     "
    
    async def scan_with_retry(self, max_retries: int = 3, 
                              delay: float = 2.0) -> List[ScannedDevice]:
        """
        Scan with automatic retries.
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            List of discovered LED controllers
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await self.scan_and_print()
            except Exception as e:
                last_error = e
                logger.warning(f"Scan attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
        
        raise Exception(f"All scan attempts failed: {last_error}")
    
    @staticmethod
    def get_supported_types() -> List[str]:
        """
        Get list of supported device types.
        
        Returns:
            List of device type names
        """
        return list(COMPANY_NAMES.keys())
    
    @staticmethod
    def get_device_patterns() -> Dict[str, str]:
        """
        Get the name patterns for each device type.
        
        Returns:
            Dictionary mapping device type to name pattern
        """
        return dict(COMPANY_NAMES)
    
    async def get_device_info(self, address: str) -> Optional[ScannedDevice]:
        """
        Get detailed info about a specific device.
        
        Args:
            address: Device MAC address
            
        Returns:
            ScannedDevice or None if not found
        """
        if not BLEAK_AVAILABLE:
            raise ImportError("bleak library not installed")
        
        try:
            from bleak import BleakClient
            
            async with BleakClient(address) as client:
                services = await client.get_services()
                
                return ScannedDevice(
                    address=address,
                    name=client.address,
                    rssi=0,
                    service_uuids=[str(s.uuid) for s in services.services.values()]
                )
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
            return None

