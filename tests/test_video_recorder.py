import pytest
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.video_recorder import VideoRecorder


class TestVideoRecorder:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = VideoRecorder(output_dir=self.temp_dir)
        
    def teardown_method(self):
        if self.recorder.is_recording:
            self.recorder.stop_recording()
            
    def test_init(self):
        assert self.recorder.output_dir == Path(self.temp_dir)
        assert self.recorder.fps == 30
        assert not self.recorder.is_recording
        assert self.recorder.writer is None
        assert self.recorder.recording_thread is None
        assert self.recorder.current_filename is None
        
    def test_output_directory_creation(self):
        new_dir = Path(self.temp_dir) / "new_recordings"
        recorder = VideoRecorder(output_dir=str(new_dir))
        assert new_dir.exists()
        
    @patch('src.video_recorder.mss.mss')
    @patch('src.video_recorder.cv2.VideoWriter')
    def test_start_recording_default_filename(self, mock_writer, mock_mss):
        mock_sct = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct
        mock_sct.monitors = [None, {"width": 1920, "height": 1080}]
        
        filename = self.recorder.start_recording()
        
        assert self.recorder.is_recording
        assert filename is not None
        assert filename.startswith(str(self.recorder.output_dir))
        assert filename.endswith('.mp4')
        
        # Clean up
        self.recorder.stop_recording()
        
    @patch('src.video_recorder.mss.mss')
    @patch('src.video_recorder.cv2.VideoWriter')
    def test_start_recording_custom_filename(self, mock_writer, mock_mss):
        mock_sct = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct
        mock_sct.monitors = [None, {"width": 1920, "height": 1080}]
        
        custom_name = "test_recording.mp4"
        filename = self.recorder.start_recording(custom_name)
        
        expected_path = str(self.recorder.output_dir / custom_name)
        assert filename == expected_path
        
        # Clean up
        self.recorder.stop_recording()
        
    @patch('src.video_recorder.mss.mss')
    @patch('src.video_recorder.cv2.VideoWriter')
    def test_start_recording_already_recording(self, mock_writer, mock_mss):
        mock_sct = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct
        mock_sct.monitors = [None, {"width": 1920, "height": 1080}]
        
        self.recorder.start_recording()
        
        with pytest.raises(RuntimeError, match="Recording already in progress"):
            self.recorder.start_recording()
            
        # Clean up
        self.recorder.stop_recording()
        
    def test_stop_recording_not_recording(self):
        result = self.recorder.stop_recording()
        assert result is None
        
    @patch('src.video_recorder.mss.mss')
    @patch('src.video_recorder.cv2.VideoWriter')
    def test_stop_recording_success(self, mock_writer, mock_mss):
        mock_sct = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct
        mock_sct.monitors = [None, {"width": 1920, "height": 1080}]
        
        filename = self.recorder.start_recording()
        time.sleep(0.1)  # Let recording start
        
        result = self.recorder.stop_recording()
        
        assert result == filename
        assert not self.recorder.is_recording
        assert self.recorder.current_filename is None
        
    @patch('src.video_recorder.mss.mss')
    def test_get_screen_size(self, mock_mss):
        mock_sct = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct
        mock_sct.monitors = [None, {"width": 1920, "height": 1080}]
        
        width, height = self.recorder.get_screen_size()
        
        assert width == 1920
        assert height == 1080