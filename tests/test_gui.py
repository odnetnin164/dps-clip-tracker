import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.gui import (
    KeyBindingWidget, VideoListWidget, VideoPlayerWidget,
    MainWindow, create_application
)
from src.input_handler import InputBinding, InputType


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    

class TestKeyBindingWidget:
    def test_init(self, qapp):
        widget = KeyBindingWidget()
        
        assert widget.current_binding is None
        assert widget.input_type_combo.count() == 3
        assert widget.bind_button.text() == "Click to Bind Key"
        assert widget.current_binding_label.text() == "No binding set"
        
    def test_on_input_type_changed(self, qapp):
        widget = KeyBindingWidget()
        
        widget.on_input_type_changed("Keyboard")
        assert widget.selected_input_type == InputType.KEYBOARD
        
        widget.on_input_type_changed("Mouse")
        assert widget.selected_input_type == InputType.MOUSE
        
        widget.on_input_type_changed("Gamepad")
        assert widget.selected_input_type == InputType.GAMEPAD
        
    def test_start_key_binding(self, qapp):
        widget = KeyBindingWidget()
        
        widget.start_key_binding()
        
        assert widget.bind_button.text() == "Press a key..."
        assert not widget.bind_button.isEnabled()
        
    def test_set_binding(self, qapp):
        widget = KeyBindingWidget()
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        
        with patch.object(widget, 'binding_changed') as mock_signal:
            widget.set_binding(binding)
            
            assert widget.current_binding == binding
            assert widget.current_binding_label.text() == "Bound: A"
            assert widget.bind_button.text() == "Click to Bind Key"
            assert widget.bind_button.isEnabled()
            mock_signal.emit.assert_called_once_with(binding)


class TestVideoListWidget:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def test_init(self, qapp):
        widget = VideoListWidget()
        
        assert widget.recordings_dir == Path("recordings")
        assert widget.video_list.count() == 0
        
    def test_refresh_video_list_no_directory(self, qapp):
        widget = VideoListWidget()
        widget.recordings_dir = Path(self.temp_dir) / "nonexistent"
        
        widget.refresh_video_list()
        
        assert widget.video_list.count() == 0
        
    def test_refresh_video_list_with_videos(self, qapp):
        widget = VideoListWidget()
        widget.recordings_dir = Path(self.temp_dir)
        
        # Create test video files
        (Path(self.temp_dir) / "test1.mp4").touch()
        (Path(self.temp_dir) / "test2.mp4").touch()
        
        widget.refresh_video_list()
        
        assert widget.video_list.count() == 2
        
    @patch('src.gui.QMessageBox.question')
    def test_delete_selected_video_confirmed(self, mock_question, qapp):
        mock_question.return_value = mock_question.StandardButton.Yes = 16384
        
        widget = VideoListWidget()
        widget.recordings_dir = Path(self.temp_dir)
        
        # Create and add test video file
        test_file = Path(self.temp_dir) / "test.mp4"
        test_file.touch()
        widget.refresh_video_list()
        
        # Select the item
        widget.video_list.setCurrentRow(0)
        
        with patch.object(widget, 'refresh_video_list') as mock_refresh:
            widget.delete_selected_video()
            
            assert not test_file.exists()
            mock_refresh.assert_called_once()


class TestVideoPlayerWidget:
    def test_init(self, qapp):
        widget = VideoPlayerWidget()
        
        assert widget.media_player is not None
        assert widget.video_widget is not None
        assert widget.play_button.text() == "Play"
        assert widget.time_label.text() == "00:00 / 00:00"
        
    def test_format_time(self, qapp):
        widget = VideoPlayerWidget()
        
        assert widget.format_time(0) == "00:00"
        assert widget.format_time(60000) == "01:00"
        assert widget.format_time(125000) == "02:05"
        
    @patch('src.gui.os.path.exists')
    def test_load_video_existing_file(self, mock_exists, qapp):
        mock_exists.return_value = True
        widget = VideoPlayerWidget()
        
        with patch.object(widget.media_player, 'setSource') as mock_set_source:
            widget.load_video("/path/to/video.mp4")
            
            mock_set_source.assert_called_once()
            
    @patch('src.gui.os.path.exists')
    def test_load_video_nonexistent_file(self, mock_exists, qapp):
        mock_exists.return_value = False
        widget = VideoPlayerWidget()
        
        with patch.object(widget.media_player, 'setSource') as mock_set_source:
            widget.load_video("/path/to/nonexistent.mp4")
            
            mock_set_source.assert_not_called()


class TestMainWindow:
    @patch('src.gui.ClipRecorderController')
    def test_init(self, mock_controller_class, qapp):
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        
        window = MainWindow()
        
        assert window.controller == mock_controller
        assert window.windowTitle() == "DPS Clip Tracker"
        
    @patch('src.gui.ClipRecorderController')
    def test_on_binding_changed(self, mock_controller_class, qapp):
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        
        window = MainWindow()
        binding = InputBinding(InputType.KEYBOARD, 'a', 'A')
        
        window.on_binding_changed(binding)
        
        mock_controller.set_input_binding.assert_called_once_with(binding)
        
    @patch('src.gui.ClipRecorderController')
    def test_toggle_recording_start(self, mock_controller_class, qapp):
        mock_controller = Mock()
        mock_controller.is_recording = False
        mock_controller_class.return_value = mock_controller
        
        window = MainWindow()
        
        window.toggle_recording()
        
        mock_controller.start_recording.assert_called_once()
        
    @patch('src.gui.ClipRecorderController')
    def test_toggle_recording_stop(self, mock_controller_class, qapp):
        mock_controller = Mock()
        mock_controller.is_recording = True
        mock_controller_class.return_value = mock_controller
        
        window = MainWindow()
        
        window.toggle_recording()
        
        mock_controller.stop_recording.assert_called_once()
        
    @patch('src.gui.ClipRecorderController')
    def test_on_recording_started(self, mock_controller_class, qapp):
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        
        window = MainWindow()
        
        window.on_recording_started()
        
        assert "Recording..." in window.status_label.text()
        assert window.record_button.text() == "Stop Recording"
        
    @patch('src.gui.ClipRecorderController')
    @patch('src.gui.os.path.exists')
    def test_on_recording_stopped(self, mock_exists, mock_controller_class, qapp):
        mock_exists.return_value = True
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        
        window = MainWindow()
        
        with patch.object(window.video_list_widget, 'refresh_video_list') as mock_refresh:
            with patch.object(window.video_player, 'load_video') as mock_load:
                window.on_recording_stopped("test.mp4")
                
                assert "Ready" in window.status_label.text()
                assert window.record_button.text() == "Start Recording"
                mock_refresh.assert_called_once()
                mock_load.assert_called_once_with("test.mp4")


def test_create_application():
    app = create_application()
    
    assert isinstance(app, QApplication)
    assert app.applicationName() == "DPS Clip Tracker"
    assert app.applicationVersion() == "1.0.0"