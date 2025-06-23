import time
import threading
from abc import ABC, abstractmethod
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

try:
    import pygame

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Key
    from pynput.mouse import Button

    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

    # Create dummy classes for type hints when pynput is not available
    class Button:
        pass

    class Key:
        pass


class InputType(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"


@dataclass
class InputBinding:
    input_type: InputType
    key_code: Any
    display_name: str


class InputListener(ABC):
    @abstractmethod
    def start_listening(self, callback: Callable[[InputBinding], None]):
        pass

    @abstractmethod
    def stop_listening(self):
        pass


class KeyboardListener(InputListener):
    def __init__(self):
        self.listener: Optional[keyboard.Listener] = None
        self.callback: Optional[Callable] = None
        self.bound_key: Optional[Any] = None

    def set_key_binding(self, key_code: Any):
        self.bound_key = key_code

    def start_listening(self, callback: Callable[[InputBinding], None]):
        if not PYNPUT_AVAILABLE:
            raise RuntimeError("pynput not available for keyboard input")

        self.callback = callback
        self.listener = keyboard.Listener(on_press=self._on_key_press)
        self.listener.start()

    def stop_listening(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    def _on_key_press(self, key):
        if self.bound_key and key == self.bound_key and self.callback:
            binding = InputBinding(
                InputType.KEYBOARD, key, self._get_key_display_name(key)
            )
            self.callback(binding)

    def _get_key_display_name(self, key) -> str:
        if hasattr(key, "char") and key.char:
            return key.char.upper()
        elif hasattr(key, "name"):
            return key.name.replace("_", " ").title()
        else:
            return str(key)


class MouseListener(InputListener):
    def __init__(self):
        self.listener: Optional[mouse.Listener] = None
        self.callback: Optional[Callable] = None
        self.bound_button: Optional[Button] = None

    def set_button_binding(self, button: Button):
        self.bound_button = button

    def start_listening(self, callback: Callable[[InputBinding], None]):
        if not PYNPUT_AVAILABLE:
            raise RuntimeError("pynput not available for mouse input")

        self.callback = callback
        self.listener = mouse.Listener(on_click=self._on_click)
        self.listener.start()

    def stop_listening(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    def _on_click(self, x, y, button, pressed):
        if (
            pressed
            and self.bound_button
            and button == self.bound_button
            and self.callback
        ):
            binding = InputBinding(
                InputType.MOUSE, button, f"Mouse {button.name.title()}"
            )
            self.callback(binding)


class GamepadListener(InputListener):
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.callback: Optional[Callable] = None
        self.bound_button: Optional[int] = None
        self.joystick = None

    def set_button_binding(self, button_index: int):
        self.bound_button = button_index

    def start_listening(self, callback: Callable[[InputBinding], None]):
        if not PYGAME_AVAILABLE:
            raise RuntimeError("pygame not available for gamepad input")

        # Initialize pygame and joystick subsystem
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError("No gamepad detected")

        # Initialize the first joystick
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        
        print(f"GamepadListener: Initialized joystick '{self.joystick.get_name()}' with {self.joystick.get_numbuttons()} buttons")

        # Set up pygame display (required for joystick events in some cases)
        try:
            pygame.display.set_mode((1, 1))
            print("GamepadListener: Created minimal display for event handling")
        except:
            print("GamepadListener: Could not create display, continuing without")

        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._gamepad_loop, daemon=False)
        self.thread.start()

    def stop_listening(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        if self.joystick:
            self.joystick.quit()
            self.joystick = None

    def _gamepad_loop(self):
        print(f"GamepadListener: Started monitoring controller, bound_button={self.bound_button}")
        button_states = [False] * self.joystick.get_numbuttons()

        try:
            while self.running:
                try:
                    # Use direct joystick polling instead of events
                    # This approach is more reliable than pygame events
                    for i in range(self.joystick.get_numbuttons()):
                        current_state = self.joystick.get_button(i)
                        
                        # Button press detected (wasn't pressed before, now is)
                        if current_state and not button_states[i]:
                            print(f"GamepadListener: Button {i} pressed, bound_button={self.bound_button}")
                            
                            # Only trigger callback for the bound button
                            if (
                                self.bound_button is not None
                                and i == self.bound_button
                                and self.callback
                            ):
                                print(f"GamepadListener: Triggering callback for button {i}")
                                binding = InputBinding(
                                    InputType.GAMEPAD, i, f"Controller Button {i}"
                                )
                                self.callback(binding)
                            else:
                                print(f"GamepadListener: Not triggering - bound_button={self.bound_button}, callback={self.callback is not None}")
                        
                        button_states[i] = current_state

                    time.sleep(0.01)
                except Exception as e:
                    print(f"GamepadListener: Error in polling loop: {e}")
                    time.sleep(0.1)  # Wait longer on error to avoid tight loop
                    
        except Exception as e:
            print(f"GamepadListener: Fatal error in gamepad loop: {e}")
        finally:
            print("GamepadListener: Gamepad monitoring loop ended")


class InputHandler:
    def __init__(self):
        self.listeners: Dict[InputType, InputListener] = {}
        self.current_binding: Optional[InputBinding] = None
        self.recording_callback: Optional[Callable] = None
        self.last_input_time = 0
        self.idle_timeout = 10.0
        self.idle_timer: Optional[threading.Timer] = None
        self.idle_callback: Optional[Callable] = None

    def set_keyboard_listener(self):
        self.listeners[InputType.KEYBOARD] = KeyboardListener()

    def set_mouse_listener(self):
        self.listeners[InputType.MOUSE] = MouseListener()

    def set_gamepad_listener(self):
        self.listeners[InputType.GAMEPAD] = GamepadListener()

    def bind_input(self, input_type: InputType, key_code: Any) -> InputBinding:
        print(f"InputHandler: Binding input - type={input_type}, key_code={key_code}")
        binding = InputBinding(
            input_type, key_code, self._get_display_name(input_type, key_code)
        )
        self.current_binding = binding

        # Stop all existing listeners first
        print(f"InputHandler: Stopping {len(self.listeners)} existing listeners")
        for listener_type, listener in self.listeners.items():
            print(f"InputHandler: Stopping {listener_type} listener")
            listener.stop_listening()
        self.listeners.clear()

        # Create and configure the new listener
        if input_type == InputType.KEYBOARD:
            print("InputHandler: Creating keyboard listener")
            self.set_keyboard_listener()
            self.listeners[InputType.KEYBOARD].set_key_binding(key_code)
        elif input_type == InputType.MOUSE:
            print("InputHandler: Creating mouse listener")
            self.set_mouse_listener()
            self.listeners[InputType.MOUSE].set_button_binding(key_code)
        elif input_type == InputType.GAMEPAD:
            print("InputHandler: Creating gamepad listener")
            self.set_gamepad_listener()
            self.listeners[InputType.GAMEPAD].set_button_binding(key_code)
            print(f"InputHandler: Gamepad listener created and bound to button {key_code}")

        print(f"InputHandler: Binding complete, active listeners: {list(self.listeners.keys())}")
        return binding

    def start_monitoring(self, recording_callback: Callable, idle_callback: Callable):
        print(f"InputHandler: Starting monitoring with {len(self.listeners)} listeners")
        self.recording_callback = recording_callback
        self.idle_callback = idle_callback

        for listener_type, listener in self.listeners.items():
            print(f"InputHandler: Starting {listener_type} listener")
            try:
                listener.start_listening(self._on_input_received)
                print(f"InputHandler: {listener_type} listener started successfully")
            except Exception as e:
                print(f"InputHandler: Error starting {listener_type} listener: {e}")

    def stop_monitoring(self):
        for listener in self.listeners.values():
            listener.stop_listening()

        if self.idle_timer:
            self.idle_timer.cancel()

    def _on_input_received(self, binding: InputBinding):
        self.last_input_time = time.time()

        if self.recording_callback:
            self.recording_callback(binding)

        self._reset_idle_timer()

    def _reset_idle_timer(self):
        if self.idle_timer:
            self.idle_timer.cancel()

        self.idle_timer = threading.Timer(self.idle_timeout, self._on_idle_timeout)
        self.idle_timer.start()

    def _on_idle_timeout(self):
        if self.idle_callback:
            self.idle_callback()

    def _get_display_name(self, input_type: InputType, key_code: Any) -> str:
        if input_type == InputType.KEYBOARD:
            if hasattr(key_code, "char") and key_code.char:
                return key_code.char.upper()
            elif hasattr(key_code, "name"):
                return key_code.name.replace("_", " ").title()
            else:
                return str(key_code)
        elif input_type == InputType.MOUSE:
            return (
                f"Mouse {key_code.name.title()}"
                if hasattr(key_code, "name")
                else str(key_code)
            )
        elif input_type == InputType.GAMEPAD:
            return f"Controller Button {key_code}"
        else:
            return str(key_code)
