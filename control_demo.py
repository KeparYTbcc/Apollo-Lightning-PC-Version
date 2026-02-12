"""
BLE LED Controller - Simple Control Example

This script demonstrates how to use the LED controller module.
"""

import asyncio
from ble_led_controller import BLELedController, LEDColor, DeviceScanner


async def main():
    """Main control function."""
    print("=" * 60)
    print("BLE LED Controller - Simple Example")
    print("=" * 60)
    
    # Step 1: Scan for devices
    print("\n1. Scanning for LED controllers...")
    scanner = DeviceScanner()
    devices = await scanner.scan(duration=5, led_only=True)
    
    if not devices:
        print("No LED controllers found!")
        return
    
    # Use the first found device
    target = devices[0]
    print(f"\n   Found: {target.name} ({target.address})")
    print(f"   Type: {target.device_type}")
    print(f"   Signal: {target.rssi} dBm")
    
    # Step 2: Connect to the device
    print("\n2. Connecting to device...")
    controller = BLELedController(target.address, target.name)
    
    try:
        await controller.connect(timeout=10)
        print(f"   Connected to {controller.address}")
        
        # Step 3: Turn on and set color
        print("\n3. Testing LED commands...")
        
        # Turn on (red color)
        print("   Setting color to RED...")
        await controller.set_rgb(255, 0, 0, brightness=100)
        await asyncio.sleep(2)
        
        # Green
        print("   Setting color to GREEN...")
        await controller.set_rgb(0, 255, 0, brightness=100)
        await asyncio.sleep(2)
        
        # Blue
        print("   Setting color to BLUE...")
        await controller.set_rgb(0, 0, 255, brightness=100)
        await asyncio.sleep(2)
        
        # White
        print("   Setting WHITE mode...")
        await controller.set_white_mode(brightness=80)
        await asyncio.sleep(2)
        
        # Turn off
        print("   Turning OFF...")
        await controller.turn_off()
        await asyncio.sleep(1)
        
        # Demo: Cycle through a few colors
        print("\n4. Color cycling demo...")
        colors = [
            (255, 0, 0),      # Red
            (0, 255, 0),      # Green
            (0, 0, 255),      # Blue
            (255, 255, 0),    # Yellow
            (255, 0, 255),    # Magenta
            (0, 255, 255),    # Cyan
            (255, 255, 255),  # White
        ]
        
        for i, (r, g, b) in enumerate(colors):
            print(f"   Color {i+1}: RGB({r}, {g}, {b})")
            await controller.set_rgb(r, g, b, brightness=80)
            await asyncio.sleep(0.5)
        
        # Turn off at the end
        print("\n5. Turning off at the end...")
        await controller.turn_off()
        
        print("\n" + "=" * 60)
        print("Demo complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Always disconnect
        if controller.is_connected:
            await controller.disconnect()
            print("\nDisconnected.")


async def quick_connect_example(address: str = "XX:XX:XX:XX:XX:XX"):
    """Quick example to connect to a known device."""
    print(f"\nQuick connect to {address}...")
    
    controller = BLELedController(address)
    
    try:
        await controller.connect()
        print("Connected!")
        
        # Set a nice purple color
        print("Setting purple color...")
        await controller.set_rgb(128, 0, 128, brightness=100)
        
        return controller
        
    except Exception as e:
        print(f"Connection failed: {e}")
        return None


if __name__ == "__main__":
    # Run the main demo
    asyncio.run(main())

