"""
BLE LED Controller Python Module

This module provides a Python interface for controlling Bluetooth Low Energy (BLE) LED controllers
based on the protocol reverse-engineered from Android applications.

Supported controllers:
- APM series (APM-xxx)
- Triones series (Triones-xxx, Triones+xxx)
- Consmart series
- Dream/Flash series
- QHM series

Author: Generated from decompiled APK analysis
Version: 1.0.0
"""

from .ble_controller import BLELedController, LEDColor, LEDMode
from .scanner import DeviceScanner, ScannedDevice
from .exceptions import (
    LEDControllerError, 
    ConnectionError, 
    CommandError,
    DiscoveryError,
    TimeoutError,
    AuthenticationError,
    UnsupportedDeviceError,
    ProtocolError
)
from .constants import (
    MODES, 
    COMPANY_NAMES, 
    COMMON_COLORS,
    list_all_modes,
    list_modes_by_category,
    get_mode_name,
    get_mode_info,
    MODE_CATEGORIES,
    MODE_INFO
)

__version__ = "1.0.0"
__all__ = [
    'BLELedController',
    'LEDColor',
    'LEDMode',
    'DeviceScanner',
    'ScannedDevice',
    'LEDControllerError',
    'ConnectionError',
    'CommandError',
    'DiscoveryError',
    'TimeoutError',
    'AuthenticationError',
    'UnsupportedDeviceError',
    'ProtocolError',
    'MODES',
    'COMPANY_NAMES',
    'COMMON_COLORS',
    'list_all_modes',
    'list_modes_by_category',
    'get_mode_name',
    'get_mode_info',
    'MODE_CATEGORIES',
    'MODE_INFO'
]

