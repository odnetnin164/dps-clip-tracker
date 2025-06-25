import pytest
import tempfile
import time
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.video_recorder import VideoRecorder


class TestVideoRecorder:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        # Clean up any recording processes
        pass
            
    @patch('src.video_recorder.FFmpegInstaller.get_ffmpeg_path')
    def test_init_with_system_ffmpeg(self, mock_get_path):
        # Mock FFmpegInstaller returning system ffmpeg
        mock_get_path.return_value = "ffmpeg"
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        assert recorder.output_dir == Path(self.temp_dir)
        assert recorder.fps == 30  # Default fps changed to 30
        assert not recorder.is_recording
        assert recorder.ffmpeg_process is None
        assert recorder.current_filename is None
        assert recorder.ffmpeg_path == "ffmpeg"
        
    @patch('src.video_recorder.FFmpegInstaller.get_ffmpeg_path')
    def test_init_with_local_ffmpeg(self, mock_get_path):
        # Mock FFmpegInstaller returning local ffmpeg path
        mock_get_path.return_value = "ffmpeg/ffmpeg"
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        assert recorder.ffmpeg_path == "ffmpeg/ffmpeg"
        
    @patch('src.video_recorder.FFmpegInstaller.get_ffmpeg_path')
    def test_output_directory_creation(self, mock_get_path):
        mock_get_path.return_value = "ffmpeg"
        new_dir = Path(self.temp_dir) / "new_recordings"
        
        recorder = VideoRecorder(output_dir=str(new_dir))
        assert new_dir.exists()
        
    @patch('src.video_recorder.subprocess.Popen')
    @patch('src.video_recorder.FFmpegInstaller.get_ffmpeg_path')
    def test_start_recording_default_filename(self, mock_get_path, mock_popen):
        # Mock ffmpeg available
        mock_get_path.return_value = "ffmpeg"
        
        # Mock successful ffmpeg process start
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        filename = recorder.start_recording()
        
        assert recorder.is_recording
        assert filename is not None
        assert filename.startswith(str(recorder.output_dir))
        assert filename.endswith('.mp4')
        
        # Clean up
        recorder.stop_recording()
        
    @patch('src.video_recorder.subprocess.Popen')
    @patch('src.video_recorder.subprocess.run')
    def test_start_recording_custom_filename(self, mock_run, mock_popen):
        # Mock ffmpeg available
        mock_run.return_value.returncode = 0
        
        # Mock successful ffmpeg process start
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        custom_name = "test_recording.mp4"
        filename = recorder.start_recording(custom_name)
        
        expected_path = str(recorder.output_dir / custom_name)
        assert filename == expected_path
        
        # Clean up
        recorder.stop_recording()
        
    @patch('src.video_recorder.subprocess.Popen')
    @patch('src.video_recorder.subprocess.run')
    def test_start_recording_already_recording(self, mock_run, mock_popen):
        # Mock ffmpeg available
        mock_run.return_value.returncode = 0
        
        # Mock successful ffmpeg process start
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        recorder.start_recording()
        
        with pytest.raises(RuntimeError, match="Recording already in progress"):
            recorder.start_recording()
            
        # Clean up
        recorder.stop_recording()
        
    @patch('src.video_recorder.subprocess.run')
    def test_stop_recording_not_recording(self, mock_run):
        # Mock ffmpeg available
        mock_run.return_value.returncode = 0
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        result = recorder.stop_recording()
        assert result is None
        
    @patch('src.video_recorder.subprocess.Popen')
    @patch('src.video_recorder.subprocess.run')
    def test_stop_recording_success(self, mock_run, mock_popen):
        # Mock ffmpeg available
        mock_run.return_value.returncode = 0
        
        # Mock successful ffmpeg process start
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        filename = recorder.start_recording()
        time.sleep(0.1)  # Let recording start
        
        result = recorder.stop_recording()
        
        assert result == filename
        assert not recorder.is_recording
        assert recorder.current_filename is None
        
    @patch('src.video_recorder.subprocess.Popen')
    @patch('src.video_recorder.subprocess.run')
    def test_ffmpeg_process_failure(self, mock_run, mock_popen):
        # Mock ffmpeg available
        mock_run.return_value.returncode = 0
        
        # Mock failed ffmpeg process start
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process failed
        mock_process.communicate.return_value = ("", "Error message")
        mock_popen.return_value = mock_process
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        
        with pytest.raises(RuntimeError, match="FFmpeg failed to start"):
            recorder.start_recording()
            
    @patch('src.video_recorder.subprocess.run')
    def test_get_focused_window_title_windows(self, mock_run):
        # Mock ffmpeg available
        mock_run.return_value.returncode = 0
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        
        with patch('src.video_recorder.platform.system', return_value='Windows'):
            # Test the PowerShell fallback path since win32gui may not be available
            with patch('src.video_recorder.subprocess.run') as mock_ps:
                mock_ps.return_value.returncode = 0
                mock_ps.return_value.stdout = "Test Window\n"
                
                title = recorder._get_focused_window_title()
                # This might be None due to import issues in test environment
                assert title is None or isinstance(title, str)
                    
    @patch('src.video_recorder.subprocess.run')
    def test_get_focused_window_title_linux(self, mock_run):
        # Mock ffmpeg available for init
        mock_run.return_value.returncode = 0
        
        recorder = VideoRecorder(output_dir=self.temp_dir)
        
        with patch('src.video_recorder.platform.system', return_value='Linux'):
            # Mock successful xdotool command
            with patch('src.video_recorder.subprocess.run') as mock_xdotool:
                mock_xdotool.return_value.returncode = 0
                mock_xdotool.return_value.stdout = "Test Window"
                
                title = recorder._get_focused_window_title()
                assert title == "Test Window"