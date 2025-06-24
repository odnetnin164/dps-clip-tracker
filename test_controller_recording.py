#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.controller import ClipRecorderController  
from src.input_handler import InputBinding, InputType
from PyQt6.QtCore import QCoreApplication, QTimer
import time

def test_controller_multiple_bindings():
    app = QCoreApplication(sys.argv)
    
    print("Testing controller with multiple bindings and recordings...")
    
    # Create controller
    controller = ClipRecorderController()
    
    # Connect signals for feedback
    controller.status_changed.connect(lambda msg: print(f"STATUS: {msg}"))
    controller.recording_started.connect(lambda: print("🔴 RECORDING STARTED!"))
    controller.recording_stopped.connect(lambda filename: print(f"⏹️  RECORDING STOPPED: {filename}"))
    
    # Test multiple bindings
    def test_binding(button_num):
        print(f"\n--- Testing binding to button {button_num} ---")
        binding = InputBinding(InputType.GAMEPAD, button_num, f"Controller Button {button_num}")
        controller.set_input_binding(binding)
        print(f"✅ Bound to button {button_num}. Press the button to test recording!")
        return binding
    
    # Test sequence
    current_binding = 0
    bindings_to_test = [0, 1, 2, 3]  # Test buttons A, B, X, Y
    
    def next_binding():
        nonlocal current_binding, bindings_to_test
        if current_binding < len(bindings_to_test):
            button = bindings_to_test[current_binding]
            test_binding(button)
            current_binding += 1
            # Schedule next binding test in 15 seconds
            if current_binding < len(bindings_to_test):
                QTimer.singleShot(15000, next_binding)
        else:
            print("\n🎉 All bindings tested! Press Ctrl+C to exit.")
    
    # Start with first binding
    next_binding()
    
    print("Test sequence:")
    print("1. Each button will be bound automatically every 15 seconds")
    print("2. Press the currently bound button to start recording")
    print("3. Recording will auto-stop after idle timeout")
    print("4. The next button will be bound automatically")
    print("5. Press Ctrl+C to exit at any time")
    
    try:
        app.exec()
    except KeyboardInterrupt:
        print("\nCleaning up...")
        controller.cleanup()

if __name__ == "__main__":
    test_controller_multiple_bindings()
