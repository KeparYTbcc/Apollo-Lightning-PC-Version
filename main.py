#!/usr/bin/env python3
"""
BLE LED Controller - Command-line Interface

A unified command-line tool for controlling BLE LED controllers.
Supports various lighting modes and color controls.

Usage:
    py main.py --on                                    # Turn on LED
    py main.py --off                                   # Turn off LED
    py main.py --scan                                  # Scan for available devices
    py main.py --rgb 255,0,0                           # Set RGB color
    py main.py --rgb 255,0,0 --mac XX:XX:XX:XX:XX:XX  # Set color on specific device
    py main.py --default-mac XX:XX:XX:XX:XX:XX        # Save default MAC to skip scanning
    py main.py --remove-default-mac                    # Remove saved default MAC
    py main.py --brightness 50                         # Set brightness (0-100)
    py main.py --list-modes                            # List all available modes
    py main.py --set-mode MODE_1                       # Set LED mode
    py main.py --set-mode MODE_2 --mac XX:XX:XX:XX:XX:XX  # Set mode on specific device
    py main.py                                         # Launch GUI (not yet implemented)
"""

import argparse
import asyncio
import sys
import json
from typing import Optional, List
from pathlib import Path

# Add parent directory to path to import ble_led_controller
sys.path.insert(0, str(Path(__file__).parent))

from ble_led_controller import (
    BLELedController,
    LEDColor,
    LEDMode,
    DeviceScanner,
    list_all_modes,
    list_modes_by_category,
)


# Configuration file for storing default MAC address
CONFIG_FILE = Path(__file__).parent / ".led_controller_config.json"


def load_default_mac() -> Optional[str]:
    """Load default MAC address from config file."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config.get("default_mac")
    except Exception as e:
        print(f"Warning: Could not load config: {e}")
    return None


def save_default_mac(mac_address: str) -> bool:
    """Save default MAC address to config file."""
    try:
        config = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        
        config["default_mac"] = mac_address
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error: Could not save config: {e}")
        return False


def remove_default_mac() -> bool:
    """Remove default MAC address from config file."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            
            if "default_mac" in config:
                del config["default_mac"]
                
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error: Could not remove config: {e}")
        return False


def load_presets() -> dict:
    """Load saved color presets from config file."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config.get("presets", {})
    except Exception as e:
        print(f"Warning: Could not load presets: {e}")
    return {}


def save_preset(name: str, r: int, g: int, b: int, brightness: int = 100) -> bool:
    """Save a named color preset to the config file."""
    try:
        config = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)

        presets = config.get("presets", {})
        presets[name] = {"r": int(r), "g": int(g), "b": int(b), "brightness": int(brightness)}
        config["presets"] = presets

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        return True
    except Exception as e:
        print(f"Error: Could not save preset: {e}")
        return False


def remove_preset(name: str) -> bool:
    """Remove a named preset from the config file."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)

            presets = config.get("presets", {})
            if name in presets:
                del presets[name]
                config["presets"] = presets
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error: Could not remove preset: {e}")
        return False


def get_preset(name: str) -> Optional[dict]:
    """Retrieve a preset by name."""
    presets = load_presets()
    return presets.get(name)


class LEDControllerCLI:
    """Command-line interface for LED controller."""
    
    def __init__(self, device_address: Optional[str] = None):
        """Initialize the CLI."""
        self.device_address = device_address
        self.controller: Optional[BLELedController] = None
    
    async def discover_device(self, timeout: int = 5) -> Optional[str]:
        """
        Discover the first available LED controller.
        
        Args:
            timeout: Scan timeout in seconds
            
        Returns:
            Device address or None if not found
        """
        print(f"Scanning for LED controllers ({timeout}s)...")
        scanner = DeviceScanner()
        devices = await scanner.scan(duration=timeout, led_only=True)
        
        if not devices:
            print("❌ No LED controllers found!")
            return None
        
        device = devices[0]
        print(f"✓ Found: {device.name} ({device.address})")
        print(f"  Signal: {device.rssi} dBm")
        return device.address
    
    async def connect_device(self, address: str) -> bool:
        """
        Connect to a device.
        
        Args:
            address: Device MAC address
            
        Returns:
            True if successful
        """
        try:
            self.controller = BLELedController(address)
            print(f"Connecting to {address}...")
            await self.controller.connect(timeout=10)
            print("✓ Connected!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def disconnect_device(self) -> None:
        """Disconnect from device."""
        if self.controller and self.controller.is_connected:
            await self.controller.disconnect()
            print("✓ Disconnected")
    
    async def turn_on(self) -> bool:
        """Turn LED on."""
        if not await self._ensure_connected():
            return False
        try:
            await self.controller.turn_on()
            print("✓ LED turned ON")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def turn_off(self) -> bool:
        """Turn LED off."""
        if not await self._ensure_connected():
            return False
        try:
            await self.controller.turn_off()
            print("✓ LED turned OFF")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def set_rgb(self, r: int, g: int, b: int, brightness: int = 100) -> bool:
        """
        Set RGB color.
        
        Args:
            r, g, b: Color values (0-255)
            brightness: Brightness (0-100)
        """
        if not await self._ensure_connected():
            return False
        
        # Validate input
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        brightness = max(0, min(100, brightness))
        
        try:
            await self.controller.set_rgb(r, g, b, brightness)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            print(f"✓ Color set to {hex_color} (brightness: {brightness}%)")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def set_brightness(self, brightness: int) -> bool:
        """
        Set brightness for current color.
        
        Args:
            brightness: Brightness percentage (0-100)
        """
        if not await self._ensure_connected():
            return False
        
        brightness = max(0, min(100, brightness))
        
        try:
            # Set white mode with specified brightness
            await self.controller.set_white_mode(brightness)
            print(f"✓ Brightness set to {brightness}%")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def set_mode(self, mode_name: str, speed: int = 50) -> bool:
        """
        Set LED mode.
        
        Args:
            mode_name: Mode name (e.g., "MODE_1", "0x25")
            speed: Animation speed (0-255)
        """
        if not await self._ensure_connected():
            return False
        
        speed = max(0, min(255, speed))
        
        try:
            # Try to parse mode name
            mode = None
            
            # Check if it's a hex value
            if mode_name.startswith("0x") or mode_name.startswith("0X"):
                try:
                    mode_id = int(mode_name, 16)
                    mode = LEDMode.from_id(mode_id)
                except (ValueError, AttributeError):
                    print(f"❌ Invalid mode ID: {mode_name}")
                    return False
            else:
                # Try to get by enum name
                try:
                    mode = LEDMode[mode_name.upper()]
                except KeyError:
                    print(f"❌ Unknown mode: {mode_name}")
                    print("   Use --list-modes to see available modes")
                    return False
            
            await self.controller.set_mode(mode, speed)
            print(f"✓ Mode set to {mode.name} (speed: {speed})")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def list_modes(self) -> bool:
        """List all available LED modes."""
        modes = list_all_modes()
        
        print("\n" + "=" * 80)
        print("                        AVAILABLE LED MODES")
        print("=" * 80)
        print(f"\n{'ID':<8} {'Enum Name':<20} {'Description':<40} {'Speed Range':<15}")
        print("-" * 80)
        
        for mode in modes:
            mode_id = mode['id']
            enum_name = f"MODE_{(mode_id - 0x24)}"  # MODE_1 = 0x25, etc.
            name = mode['name']
            desc = mode['description'][:38]
            speed_min = mode['speed_min']
            speed_max = mode['speed_max']
            
            if speed_min == 0 and speed_max == 0:
                speed_range = "N/A"
            else:
                speed_range = f"{speed_min}-{speed_max}"
            
            print(f"0x{mode_id:02X}    {enum_name:<20} {desc:<40} {speed_range:<15}")
        
        print("-" * 80)
        print(f"\nTotal modes: {len(modes)}")
        print("\nUsage: py main.py --set-mode <mode_name> [--speed <0-255>]")
        print("       py main.py --set-mode MODE_1")
        print("       py main.py --set-mode 0x25")
        print("=" * 80 + "\n")
        
        return True
    
    async def scan_devices(self, timeout: int = 5) -> bool:
        """
        Scan for and list available LED controllers.
        
        Args:
            timeout: Scan timeout in seconds
        """
        print(f"\nScanning for LED controllers ({timeout}s)...\n")
        
        try:
            scanner = DeviceScanner()
            devices = await scanner.scan(duration=timeout, led_only=True)
            
            if not devices:
                print("❌ No LED controllers found!")
                return False
            
            print("=" * 80)
            print(f"{'Found {0} device(s):'.format(len(devices)):<40}")
            print("=" * 80)
            print(f"\n{'#':<3} {'Name':<20} {'Address':<20} {'Signal (dBm)':<15} {'Type':<10}")
            print("-" * 80)
            
            for i, device in enumerate(devices, 1):
                name = device.name[:18] if device.name else "Unknown"
                address = device.address
                rssi = device.rssi or "N/A"
                device_type = device.device_type or "Unknown"
                
                print(f"{i:<3} {name:<20} {address:<20} {rssi:<15} {device_type:<10}")
            
            print("-" * 80)
            print(f"\nTotal: {len(devices)} device(s) found")
            print("=" * 80 + "\n")
            
            return True
        except Exception as e:
            print(f"❌ Scan error: {e}")
            return False
    
    async def _ensure_connected(self) -> bool:
        """Ensure device is connected, discover and connect if needed."""
        if self.controller and self.controller.is_connected:
            return True
        
        # Try to discover device
        address = self.device_address or await self.discover_device()
        if not address:
            return False
        
        # Connect
        return await self.connect_device(address)


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BLE LED Controller - Command-line Control",
        epilog="""
Examples:
  python main.py --on                                     # Turn LED on
  python main.py --off                                    # Turn LED off
  python main.py --scan                                   # Scan for devices
  python main.py --rgb 255,0,0                            # Set to red
  python main.py --rgb 0,255,0 --brightness 80            # Green at 80% brightness
  python main.py --brightness 50                          # Set brightness to 50%
  python main.py --list-modes                             # Show all available modes
  python main.py --set-mode MODE_1                        # Set static mode
  python main.py --set-mode 0x25 --speed 100              # Set mode by hex ID with speed
  python main.py --on --mac AA:BB:CC:DD:EE:FF             # Turn on specific device
  python main.py --rgb 255,0,0 --mac AA:BB:CC:DD:EE:FF   # Set color on specific device
  python main.py --default-mac AA:BB:CC:DD:EE:FF          # Save default MAC address
  python main.py --on                                     # Turn on using default MAC
  python main.py --remove-default-mac                     # Remove saved default MAC
  python main.py                                          # Launch GUI (not yet implemented)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--on",
        action="store_true",
        help="Turn LED on"
    )
    parser.add_argument(
        "--off",
        action="store_true",
        help="Turn LED off"
    )
    parser.add_argument(
        "--rgb",
        type=str,
        metavar="R,G,B",
        help="Set RGB color (e.g., 255,0,0 for red)"
    )
    parser.add_argument(
        "--brightness",
        type=int,
        metavar="<0-100>",
        help="Set brightness percentage (0-100)"
    )
    parser.add_argument(
        "--list-modes",
        action="store_true",
        help="List all available LED modes"
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan for and list available LED controller devices"
    )
    parser.add_argument(
        "--set-mode",
        type=str,
        metavar="MODE",
        help="Set LED mode (e.g., MODE_1 or 0x25)"
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=50,
        metavar="<0-255>",
        help="Animation speed (default: 50)"
    )
    parser.add_argument(
        "--mac",
        type=str,
        metavar="ADDRESS",
        help="Device MAC address (e.g., XX:XX:XX:XX:XX:XX)"
    )
    parser.add_argument(
        "--device",
        type=str,
        metavar="ADDRESS",
        help="Device MAC address (auto-discover if not provided)"
    )
    parser.add_argument(
        "--default-mac",
        type=str,
        metavar="ADDRESS",
        help="Set default MAC address to skip device scanning"
    )
    parser.add_argument(
        "--remove-default-mac",
        action="store_true",
        help="Remove the saved default MAC address"
    )
    parser.add_argument(
        "--save",
        type=str,
        metavar="NAME",
        help="Save the provided RGB color under a custom name (requires --rgb)"
    )
    parser.add_argument(
        "--presets",
        action="store_true",
        help="List saved color presets"
    )
    parser.add_argument(
        "--colours",
        action="store_true",
        help="Alias for --presets"
    )
    parser.add_argument(
        "--load",
        type=str,
        metavar="NAME",
        help="Load a saved color preset by name and apply it"
    )
    parser.add_argument(
        "--remove-preset",
        type=str,
        metavar="NAME",
        help="Remove a saved color preset by name"
    )
    
    args = parser.parse_args()
    
    # Handle special commands that don't need device connection
    if args.default_mac:
        if save_default_mac(args.default_mac):
            print(f"✓ Default MAC saved: {args.default_mac}")
            print("  Future commands will use this device by default")
        return 0
    
    if args.remove_default_mac:
        if remove_default_mac():
            print("✓ Default MAC address removed")
        return 0

    # Preset management commands (do not require device connection)
    if args.presets or args.colours:
        presets = load_presets()
        if not presets:
            print("No presets saved.")
            return 0
        print("\nSaved Color Presets:\n")
        for name, value in presets.items():
            r = value.get("r")
            g = value.get("g")
            b = value.get("b")
            br = value.get("brightness", 100)
            print(f"- {name}: RGB({r},{g},{b}) brightness={br}%")
        print("")
        return 0

    if args.remove_preset:
        if remove_preset(args.remove_preset):
            print(f"✓ Removed preset: {args.remove_preset}")
            return 0
        else:
            return 1

    if args.save:
        # Save requires an RGB value
        if not args.rgb:
            print("❌ To save a preset provide a color with --rgb R,G,B")
            return 1
        try:
            parts = args.rgb.split(",")
            if len(parts) != 3:
                print("❌ RGB format must be: R,G,B (e.g., 255,0,0)")
                return 1
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            brightness = args.brightness or 100
            if save_preset(args.save, r, g, b, brightness):
                print(f"✓ Preset '{args.save}' saved: RGB({r},{g},{b}) brightness={brightness}%")
                return 0
            else:
                return 1
        except ValueError as e:
            print(f"❌ Invalid RGB values: {e}")
            return 1

    if args.load:
        preset = get_preset(args.load)
        if not preset:
            print(f"❌ Preset not found: {args.load}")
            return 1
        # Inject into args so later execution picks it up
        args.rgb = f"{preset['r']},{preset['g']},{preset['b']}"
        args.brightness = preset.get('brightness', args.brightness or 100)
    
    # Check if any command-line arguments were provided
    has_command = any([
        args.on,
        args.off,
        args.rgb,
        args.brightness,
        args.list_modes,
        args.scan,
        args.set_mode,
        args.save,
        args.presets,
        args.colours,
        args.load,
        args.remove_preset,
    ])
    
    # If no command, launch GUI
    if not has_command:
        print("=" * 60)
        print("BLE LED Controller - Graphical Interface")
        print("=" * 60)
        print("\nNo command-line arguments provided.")
        print("Launching graphical interface...\n")
        print("GUI implementation not yet available.")
        print("Please use command-line arguments to control the LED:\n")
        print("  py main.py --help    # Show all available commands")
        print("  py main.py --on      # Turn LED on")
        print("  py main.py --off     # Turn LED off")
        print("  py main.py --list-modes  # List available modes\n")
        return 0
    
    # Create CLI instance
    # Priority: --mac > --device > saved default MAC
    device_address = args.mac or args.device or load_default_mac()
    cli = LEDControllerCLI(device_address=device_address)
    
    try:
        # Handle list-modes command first (doesn't need device connection)
        if args.list_modes:
            cli.list_modes()
            return 0
        
        # Handle scan command (doesn't need device connection)
        if args.scan:
            await cli.scan_devices()
            return 0
        
        # Execute requested commands
        success = True
        
        if args.on:
            success = await cli.turn_on() and success
        
        if args.off:
            success = await cli.turn_off() and success
        
        if args.rgb:
            try:
                parts = args.rgb.split(",")
                if len(parts) != 3:
                    print("❌ RGB format must be: R,G,B (e.g., 255,0,0)")
                    return 1
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                success = await cli.set_rgb(r, g, b, args.brightness or 100) and success
            except ValueError as e:
                print(f"❌ Invalid RGB values: {e}")
                return 1
        
        if args.brightness and not args.rgb:
            success = await cli.set_brightness(args.brightness) and success
        
        if args.set_mode:
            success = await cli.set_mode(args.set_mode, args.speed) and success
        
        # Disconnect
        await cli.disconnect_device()
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        await cli.disconnect_device()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        await cli.disconnect_device()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
