from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from .video_recorder import VideoRecorder
from .input_handler import InputHandler, InputBinding, InputType


class ClipRecorderController(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.video_recorder = VideoRecorder()
        self.input_handler = InputHandler()
        self.current_binding: Optional[InputBinding] = None
        self.is_recording = False
        self.is_monitoring = False
        
    def set_input_binding(self, binding: InputBinding):
        self.current_binding = binding
        
        # Stop current monitoring if active
        if self.is_monitoring:
            self.stop_monitoring()
            
        # Bind the input (this will create listener if needed)
        self.input_handler.bind_input(binding.input_type, binding.key_code)
        
        # Start monitoring for the bound input
        self.start_monitoring()
        
        self.status_changed.emit(f"Bound to {binding.display_name}")
        
    def start_monitoring(self):
        if not self.current_binding:
            self.status_changed.emit("No input binding set")
            return
            
        try:
            self.input_handler.start_monitoring(
                self._on_input_triggered,
                self._on_idle_timeout
            )
            self.is_monitoring = True
            self.status_changed.emit(f"Monitoring {self.current_binding.display_name}")
        except Exception as e:
            self.status_changed.emit(f"Error starting monitoring: {str(e)}")
            
    def stop_monitoring(self):
        if self.is_monitoring:
            self.input_handler.stop_monitoring()
            self.is_monitoring = False
            
    def start_recording(self):
        if self.is_recording:
            return
            
        try:
            filename = self.video_recorder.start_recording()
            self.is_recording = True
            self.recording_started.emit()
            self.status_changed.emit(f"Recording to {filename}")
        except Exception as e:
            self.status_changed.emit(f"Error starting recording: {str(e)}")
            
    def stop_recording(self):
        if not self.is_recording:
            return
            
        try:
            filename = self.video_recorder.stop_recording()
            self.is_recording = False
            self.recording_stopped.emit(filename or "")
            self.status_changed.emit("Recording stopped")
        except Exception as e:
            self.status_changed.emit(f"Error stopping recording: {str(e)}")
            
    def _on_input_triggered(self, binding: InputBinding):
        print(f"Controller: Input triggered - {binding.display_name}, is_recording={self.is_recording}")
        if not self.is_recording:
            print("Controller: Starting recording due to input trigger")
            self.start_recording()
        else:
            print("Controller: Already recording, ignoring input trigger")
            
    def _on_idle_timeout(self):
        if self.is_recording:
            self.stop_recording()
            
    def cleanup(self):
        self.stop_monitoring()
        if self.is_recording:
            self.stop_recording()