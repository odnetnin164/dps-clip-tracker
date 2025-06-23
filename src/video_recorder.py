import cv2
import numpy as np
import mss
import threading
import time
from typing import Optional, Tuple
from pathlib import Path


class VideoRecorder:
    def __init__(self, output_dir: str = "recordings", fps: int = 15):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.fps = fps
        self.is_recording = False
        self.writer: Optional[cv2.VideoWriter] = None
        self.recording_thread: Optional[threading.Thread] = None
        self.current_filename: Optional[str] = None
        self.stop_recording_event = threading.Event()
        
    def start_recording(self, filename: Optional[str] = None) -> str:
        if self.is_recording:
            raise RuntimeError("Recording already in progress")
            
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"clip_{timestamp}.mp4"
            
        self.current_filename = str(self.output_dir / filename)
        self.stop_recording_event.clear()
        self.is_recording = True
        
        self.recording_thread = threading.Thread(target=self._record_screen)
        self.recording_thread.start()
        
        return self.current_filename
        
    def stop_recording(self) -> Optional[str]:
        if not self.is_recording:
            return None
            
        self.stop_recording_event.set()
        if self.recording_thread:
            self.recording_thread.join()
            
        self.is_recording = False
        filename = self.current_filename
        self.current_filename = None
        return filename
        
    def _record_screen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            width = monitor["width"]
            height = monitor["height"]
            
            self.writer = cv2.VideoWriter(
                self.current_filename, 
                fourcc, 
                self.fps, 
                (width, height)
            )
            
            frame_time = 1.0 / self.fps  # Time per frame
            last_frame_time = time.time()
            
            try:
                while not self.stop_recording_event.is_set():
                    current_time = time.time()
                    elapsed = current_time - last_frame_time
                    
                    if elapsed >= frame_time:
                        last_frame_time = time.time()  # Update last frame timestamp
                        
                        # Capture and process frame
                        screenshot = sct.grab(monitor)
                        frame = np.array(screenshot)
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        
                        self.writer.write(frame_bgr)
                        
                    # Calculate remaining time to sleep, if any
                    remaining_time = frame_time - (time.time() - last_frame_time)
                    if remaining_time > 0:
                        time.sleep(remaining_time)
                        
            finally:
                if self.writer:
                    self.writer.release()
                    self.writer = None


                    
    def get_screen_size(self) -> Tuple[int, int]:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            return monitor["width"], monitor["height"]