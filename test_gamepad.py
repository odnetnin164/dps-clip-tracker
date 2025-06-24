#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.input_handler import InputHandler, InputBinding, InputType
import time

def test_gamepad_binding():
    print("Testing gamepad binding...")
    
    # Create input handler
    handler = InputHandler()
    
    # Set up gamepad listener
    handler.set_gamepad_listener()
    
    # Test binding to button 1 (B button on Xbox controller)
    binding = handler.bind_input(InputType.GAMEPAD, 1)
    print(f"Created binding: {binding.display_name}")
    
    # Define callback for when input is received
    def on_input_received(binding):
        print(f"INPUT RECEIVED: {binding.display_name}")
    
    def on_idle():
        print("Idle timeout")
    
    # Start monitoring
    print("Starting monitoring... Press button 1 (B button) on your controller")
    handler.start_monitoring(on_input_received, on_idle)
    
    # Wait for input
    try:
        print("Waiting for controller input (press Ctrl+C to exit)...")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
        handler.stop_monitoring()

if __name__ == "__main__":
    test_gamepad_binding()
