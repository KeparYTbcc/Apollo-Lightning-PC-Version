"""
BLECustom exceptions for the LED Controller Exceptions

 LED controller module.
"""


class LEDControllerError(Exception):
    """Base exception for LED controller errors."""
    pass


class ConnectionError(LEDControllerError):
    """Exception raised when connection fails."""
    pass


class CommandError(LEDControllerError):
    """Exception raised when a command fails."""
    pass


class DiscoveryError(LEDControllerError):
    """Exception raised when device discovery fails."""
    pass


class TimeoutError(LEDControllerError):
    """Exception raised when a command times out."""
    pass


class AuthenticationError(LEDControllerError):
    """Exception raised when authentication fails."""
    pass


class UnsupportedDeviceError(LEDControllerError):
    """Exception raised when device is not supported."""
    pass


class ProtocolError(LEDControllerError):
    """Exception raised for protocol errors."""
    pass

