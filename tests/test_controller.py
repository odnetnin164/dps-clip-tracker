import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QObject

from src.controller import ClipRecorderController
from src.input_handler import InputBinding, InputType


class TestClipRecorderController:
    def setup_method(self):
        self.controller = ClipRecorderController()
        
    def teardown_method(self):
        self.controller.cleanup()
        
    def test_init(self):
        assert isinstance(self.controller, QObject)
        assert self.controller.video_recorder is not None
        assert self.controller.input_handler is not None
        assert self.controller.current_binding is None
        assert not self.controller.is_recording
        assert not self.controller.is_monitoring
        
    @patch.object(ClipRecorderController, 'start_monitoring')
    @patch.object(ClipRecorderController, 'stop_monitoring')
    def test_set_input_binding_keyboard(self, mock_stop, mock_start):
        # Set up the controller to be in monitoring state first
        self.controller.is_monitoring = True
        
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        
        self.controller.set_input_binding(binding)
        
        assert self.controller.current_binding == binding
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
        
    @patch.object(ClipRecorderController, 'start_monitoring')
    @patch.object(ClipRecorderController, 'stop_monitoring')
    def test_set_input_binding_mouse(self, mock_stop, mock_start):
        binding = InputBinding(InputType.MOUSE, 'left', 'Mouse Left')
        
        self.controller.set_input_binding(binding)
        
        assert self.controller.current_binding == binding
        
    @patch.object(ClipRecorderController, 'start_monitoring')
    @patch.object(ClipRecorderController, 'stop_monitoring')
    def test_set_input_binding_gamepad(self, mock_stop, mock_start):
        binding = InputBinding(InputType.GAMEPAD, 0, 'Controller Button 0')
        
        self.controller.set_input_binding(binding)
        
        assert self.controller.current_binding == binding
        
    def test_start_monitoring_no_binding(self):
        with patch.object(self.controller, 'status_changed') as mock_signal:
            self.controller.start_monitoring()
            
            mock_signal.emit.assert_called_with("No input binding set")
            
    @patch('src.controller.InputHandler.start_monitoring')
    def test_start_monitoring_success(self, mock_start):
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        self.controller.current_binding = binding
        
        with patch.object(self.controller, 'status_changed') as mock_signal:
            self.controller.start_monitoring()
            
            assert self.controller.is_monitoring
            mock_start.assert_called_once()
            mock_signal.emit.assert_called_with("Monitoring A")
            
    @patch('src.controller.InputHandler.start_monitoring')
    def test_start_monitoring_exception(self, mock_start):
        mock_start.side_effect = Exception("Test error")
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        self.controller.current_binding = binding
        
        with patch.object(self.controller, 'status_changed') as mock_signal:
            self.controller.start_monitoring()
            
            mock_signal.emit.assert_called_with("Error starting monitoring: Test error")
            
    @patch('src.controller.InputHandler.stop_monitoring')
    def test_stop_monitoring(self, mock_stop):
        self.controller.is_monitoring = True
        
        self.controller.stop_monitoring()
        
        assert not self.controller.is_monitoring
        mock_stop.assert_called_once()
        
    @patch('src.controller.VideoRecorder.start_recording')
    def test_start_recording_success(self, mock_start):
        mock_start.return_value = "test_file.mp4"
        
        with patch.object(self.controller, 'recording_started') as mock_signal:
            with patch.object(self.controller, 'status_changed') as mock_status:
                self.controller.start_recording()
                
                assert self.controller.is_recording
                mock_start.assert_called_once()
                mock_signal.emit.assert_called_once()
                mock_status.emit.assert_called_with("Recording to test_file.mp4")
                
    def test_start_recording_already_recording(self):
        self.controller.is_recording = True
        
        with patch('src.controller.VideoRecorder.start_recording') as mock_start:
            self.controller.start_recording()
            
            mock_start.assert_not_called()
            
    @patch('src.controller.VideoRecorder.start_recording')
    def test_start_recording_exception(self, mock_start):
        mock_start.side_effect = Exception("Test error")
        
        with patch.object(self.controller, 'status_changed') as mock_signal:
            self.controller.start_recording()
            
            assert not self.controller.is_recording
            mock_signal.emit.assert_called_with("Error starting recording: Test error")
            
    @patch('src.controller.VideoRecorder.stop_recording')
    def test_stop_recording_success(self, mock_stop):
        mock_stop.return_value = "test_file.mp4"
        self.controller.is_recording = True
        
        with patch.object(self.controller, 'recording_stopped') as mock_signal:
            with patch.object(self.controller, 'status_changed') as mock_status:
                self.controller.stop_recording()
                
                assert not self.controller.is_recording
                mock_stop.assert_called_once()
                mock_signal.emit.assert_called_with("test_file.mp4")
                mock_status.emit.assert_called_with("Recording stopped")
                
    def test_stop_recording_not_recording(self):
        with patch('src.controller.VideoRecorder.stop_recording') as mock_stop:
            self.controller.stop_recording()
            
            mock_stop.assert_not_called()
            
    @patch('src.controller.VideoRecorder.stop_recording')
    def test_stop_recording_exception(self, mock_stop):
        mock_stop.side_effect = Exception("Test error")
        self.controller.is_recording = True
        
        with patch.object(self.controller, 'status_changed') as mock_signal:
            self.controller.stop_recording()
            
            mock_signal.emit.assert_called_with("Error stopping recording: Test error")
            
    @patch.object(ClipRecorderController, 'start_recording')
    def test_on_input_triggered_not_recording(self, mock_start):
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        
        self.controller._on_input_triggered(binding)
        
        mock_start.assert_called_once()
        
    @patch.object(ClipRecorderController, 'start_recording')
    def test_on_input_triggered_already_recording(self, mock_start):
        self.controller.is_recording = True
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        
        self.controller._on_input_triggered(binding)
        
        mock_start.assert_not_called()
        
    @patch.object(ClipRecorderController, 'stop_recording')
    def test_on_idle_timeout_recording(self, mock_stop):
        self.controller.is_recording = True
        
        self.controller._on_idle_timeout()
        
        mock_stop.assert_called_once()
        
    @patch.object(ClipRecorderController, 'stop_recording')
    def test_on_idle_timeout_not_recording(self, mock_stop):
        self.controller._on_idle_timeout()
        
        mock_stop.assert_not_called()
        
    @patch.object(ClipRecorderController, 'stop_monitoring')
    @patch.object(ClipRecorderController, 'stop_recording')
    def test_cleanup(self, mock_stop_recording, mock_stop_monitoring):
        self.controller.is_recording = True
        
        self.controller.cleanup()
        
        mock_stop_monitoring.assert_called_once()
        mock_stop_recording.assert_called_once()