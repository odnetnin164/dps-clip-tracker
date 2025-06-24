#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.input_handler import InputHandler, InputBinding, InputType
import time

def test_consolidated_pygame():
    print("Testing consolidated pygame management...")
    
    # Create input handler
    handler = InputHandler()
    
    print("Testing gamepad binding detection...")
    
    binding_detected = False
    
    def on_binding_detected(binding):
        global binding_detected
        print(f"BINDING DETECTED: {binding.display_name}")
        binding_detected = True
        # Note: The listener will stop itself after binding, so no need to manually stop
    
    # Test gamepad binding detection
    success = handler.detect_and_bind_gamepad_button(on_binding_detected)
    
    if success:
        print("Gamepad binding detection started. Press any button on your controller...")
        
        # Wait for button press or timeout
        start_time = time.time()
        while not binding_detected and (time.time() - start_time) < 10:
            time.sleep(0.1)
        
        if binding_detected:
            print("✅ Binding detection successful!")
        else:
            print("⏰ Timeout waiting for button press")
    else:
        print("❌ Failed to start gamepad binding detection")
    
    # Clean up
    try:
        handler.stop_gamepad_binding_detection()
    except:
        pass
    
    print("Test complete")

if __name__ == "__main__":
    test_consolidated_pygame()
