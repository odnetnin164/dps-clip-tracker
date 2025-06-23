import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

from src.input_handler import (
    InputHandler, InputBinding, InputType,
    KeyboardListener, MouseListener, GamepadListener
)


class TestInputBinding:
    def test_input_binding_creation(self):
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        
        assert binding.input_type == InputType.KEYBOARD
        assert binding.key_code == 'a'
        assert binding.display_name == 'A'


class TestKeyboardListener:
    def setup_method(self):
        self.listener = KeyboardListener()
        
    def teardown_method(self):
        self.listener.stop_listening()
        
    def test_set_key_binding(self):
        self.listener.set_key_binding('a')
        assert self.listener.bound_key == 'a'
        
    @patch('src.input_handler.PYNPUT_AVAILABLE', False)
    def test_start_listening_without_pynput(self):
        callback = Mock()
        
        with pytest.raises(RuntimeError, match="pynput not available"):
            self.listener.start_listening(callback)
            
    @patch('src.input_handler.keyboard.Listener')
    def test_start_listening_success(self, mock_listener_class):
        mock_listener = Mock()
        mock_listener_class.return_value = mock_listener
        
        callback = Mock()
        self.listener.start_listening(callback)
        
        assert self.listener.callback == callback
        mock_listener_class.assert_called_once()
        mock_listener.start.assert_called_once()
        
    def test_get_key_display_name_char(self):
        key = Mock()
        key.char = 'a'
        
        display_name = self.listener._get_key_display_name(key)
        assert display_name == 'A'
        
    def test_get_key_display_name_special(self):
        key = Mock()
        key.char = None
        key.name = 'space'
        
        display_name = self.listener._get_key_display_name(key)
        assert display_name == 'Space'


class TestMouseListener:
    def setup_method(self):
        self.listener = MouseListener()
        
    def teardown_method(self):
        self.listener.stop_listening()
        
    @patch('src.input_handler.PYNPUT_AVAILABLE', False)
    def test_start_listening_without_pynput(self):
        callback = Mock()
        
        with pytest.raises(RuntimeError, match="pynput not available"):
            self.listener.start_listening(callback)
            
    @patch('src.input_handler.mouse.Listener')
    def test_start_listening_success(self, mock_listener_class):
        mock_listener = Mock()
        mock_listener_class.return_value = mock_listener
        
        callback = Mock()
        self.listener.start_listening(callback)
        
        assert self.listener.callback == callback
        mock_listener_class.assert_called_once()
        mock_listener.start.assert_called_once()


class TestGamepadListener:
    def setup_method(self):
        self.listener = GamepadListener()
        
    def teardown_method(self):
        self.listener.stop_listening()
        
    @patch('src.input_handler.PYGAME_AVAILABLE', False)
    def test_start_listening_without_pygame(self):
        callback = Mock()
        
        with pytest.raises(RuntimeError, match="pygame not available"):
            self.listener.start_listening(callback)
            
    @patch('src.input_handler.pygame')
    def test_start_listening_no_gamepad(self, mock_pygame):
        mock_pygame.joystick.get_count.return_value = 0
        
        callback = Mock()
        
        with pytest.raises(RuntimeError, match="No gamepad detected"):
            self.listener.start_listening(callback)
            
    @patch('src.input_handler.pygame')
    def test_start_listening_success(self, mock_pygame):
        mock_pygame.joystick.get_count.return_value = 1
        mock_joystick = Mock()
        mock_pygame.joystick.Joystick.return_value = mock_joystick
        
        callback = Mock()
        self.listener.start_listening(callback)
        
        assert self.listener.callback == callback
        assert self.listener.running
        assert self.listener.thread is not None


class TestInputHandler:
    def setup_method(self):
        self.handler = InputHandler()
        
    def teardown_method(self):
        self.handler.stop_monitoring()
        
    def test_init(self):
        assert len(self.handler.listeners) == 0
        assert self.handler.current_binding is None
        assert self.handler.recording_callback is None
        assert self.handler.idle_timeout == 3.0
        
    def test_set_keyboard_listener(self):
        self.handler.set_keyboard_listener()
        
        assert InputType.KEYBOARD in self.handler.listeners
        assert isinstance(self.handler.listeners[InputType.KEYBOARD], KeyboardListener)
        
    def test_set_mouse_listener(self):
        self.handler.set_mouse_listener()
        
        assert InputType.MOUSE in self.handler.listeners
        assert isinstance(self.handler.listeners[InputType.MOUSE], MouseListener)
        
    def test_set_gamepad_listener(self):
        self.handler.set_gamepad_listener()
        
        assert InputType.GAMEPAD in self.handler.listeners
        assert isinstance(self.handler.listeners[InputType.GAMEPAD], GamepadListener)
        
    def test_bind_input_keyboard(self):
        self.handler.set_keyboard_listener()
        
        binding = self.handler.bind_input(InputType.KEYBOARD, 'a')
        
        assert binding.input_type == InputType.KEYBOARD
        assert binding.key_code == 'a'
        assert self.handler.current_binding == binding
        
    def test_get_display_name_keyboard_char(self):
        key = Mock()
        key.char = 'a'
        
        display_name = self.handler._get_display_name(InputType.KEYBOARD, key)
        assert display_name == 'A'
        
    def test_get_display_name_mouse(self):
        button = Mock()
        button.name = 'left'
        
        display_name = self.handler._get_display_name(InputType.MOUSE, button)
        assert display_name == 'Mouse Left'
        
    def test_get_display_name_gamepad(self):
        display_name = self.handler._get_display_name(InputType.GAMEPAD, 0)
        assert display_name == 'Controller Button 0'
        
    def test_on_input_received_calls_recording_callback(self):
        recording_callback = Mock()
        idle_callback = Mock()
        
        self.handler.recording_callback = recording_callback
        
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        self.handler._on_input_received(binding)
        
        recording_callback.assert_called_once_with(binding)
        
    def test_idle_timer_reset(self):
        self.handler.idle_callback = Mock()
        
        # Start a timer
        self.handler._reset_idle_timer()
        first_timer = self.handler.idle_timer
        
        # Reset the timer
        self.handler._reset_idle_timer()
        second_timer = self.handler.idle_timer
        
        assert first_timer != second_timer
        assert not first_timer.is_alive()  # First timer should be cancelled