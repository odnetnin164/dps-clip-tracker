import cv2
import numpy as np
import mss
import threading
import time
import platform
import subprocess
from typing import Optional, Tuple, Dict
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
        
    def _get_focused_window_bounds(self) -> Optional[Dict[str, int]]:
        """Get the bounds of the currently focused window."""
        try:
            system = platform.system()
            
            if system == "Windows":
                return self._get_windows_focused_window()
            elif system == "Linux":
                return self._get_linux_focused_window()
            elif system == "Darwin":  # macOS
                return self._get_macos_focused_window()
            else:
                return None
        except Exception:
            return None
    
    def _get_windows_focused_window(self) -> Optional[Dict[str, int]]:
        """Get focused window bounds on Windows."""
        try:
            import win32gui
            import win32con
            
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                # Get window rectangle
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top
                
                # Skip if window is minimized or invalid size
                if width <= 0 or height <= 0:
                    return None
                    
                # Check if window is maximized or normal (not minimized)
                placement = win32gui.GetWindowPlacement(hwnd)
                if placement[1] == win32con.SW_SHOWMINIMIZED:
                    return None
                
                return {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height
                }
        except ImportError:
            # Fallback using PowerShell to get foreground window
            try:
                ps_script = '''
                Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    public class Win32 {
                        [DllImport("user32.dll")]
                        public static extern IntPtr GetForegroundWindow();
                        [DllImport("user32.dll")]
                        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
                        [StructLayout(LayoutKind.Sequential)]
                        public struct RECT {
                            public int Left, Top, Right, Bottom;
                        }
                    }
"@
                $hwnd = [Win32]::GetForegroundWindow()
                $rect = New-Object Win32+RECT
                $result = [Win32]::GetWindowRect($hwnd, [ref]$rect)
                if ($result) {
                    $width = $rect.Right - $rect.Left
                    $height = $rect.Bottom - $rect.Top
                    if ($width -gt 0 -and $height -gt 0) {
                        Write-Output "$($rect.Left),$($rect.Top),$width,$height"
                    }
                }
                '''
                
                result = subprocess.run([
                    "powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        x, y, w, h = map(int, result.stdout.strip().split(','))
                        if w > 0 and h > 0:
                            return {"left": x, "top": y, "width": w, "height": h}
                    except (ValueError, IndexError):
                        pass
            except Exception:
                pass
        except Exception:
            pass
        return None
    
    def _get_linux_focused_window(self) -> Optional[Dict[str, int]]:
        """Get focused window bounds on Linux."""
        try:
            # Try using xdotool first
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowgeometry"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'Geometry:' in line:
                        # Parse geometry line: "Geometry: WIDTHxHEIGHT+X+Y"
                        geometry = line.split('Geometry: ')[1]
                        size_pos = geometry.split('+')
                        width, height = map(int, size_pos[0].split('x'))
                        x, y = int(size_pos[1]), int(size_pos[2])
                        return {"left": x, "top": y, "width": width, "height": height}
        except (subprocess.SubprocessError, FileNotFoundError, IndexError):
            # Try wmctrl as fallback
            try:
                result = subprocess.run(
                    ["wmctrl", "-l", "-G"],
                    capture_output=True, text=True, timeout=5
                )
                
                if result.returncode == 0:
                    # Get active window ID
                    active_result = subprocess.run(
                        ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                        capture_output=True, text=True, timeout=5
                    )
                    
                    if active_result.returncode == 0:
                        active_id = active_result.stdout.split()[-1]
                        
                        # Find the active window in wmctrl output
                        for line in result.stdout.strip().split('\n'):
                            parts = line.split()
                            if len(parts) >= 6 and parts[0] == active_id:
                                x, y, w, h = map(int, parts[2:6])
                                return {"left": x, "top": y, "width": w, "height": h}
            except (subprocess.SubprocessError, FileNotFoundError, IndexError):
                pass
        
        return None
    
    def _get_macos_focused_window(self) -> Optional[Dict[str, int]]:
        """Get focused window bounds on macOS.""" 
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set frontWindow to front window of frontApp
                set windowPosition to position of frontWindow
                set windowSize to size of frontWindow
                return (item 1 of windowPosition) & "," & (item 2 of windowPosition) & "," & (item 1 of windowSize) & "," & (item 2 of windowSize)
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                x, y, w, h = map(int, result.stdout.strip().split(','))
                return {"left": x, "top": y, "width": w, "height": h}
        except (subprocess.SubprocessError, ValueError):
            pass
        
        return None
        
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
            # Get focused window bounds, fallback to primary monitor
            window_bounds = self._get_focused_window_bounds()
            print(f"DEBUG: Window bounds detected: {window_bounds}")  # Debug output
            
            if window_bounds is None:
                monitor = sct.monitors[1]  # Primary monitor fallback
                print("DEBUG: Using full screen fallback")
            else:
                # Ensure window bounds are valid (positive width/height)
                if window_bounds["width"] <= 0 or window_bounds["height"] <= 0:
                    monitor = sct.monitors[1]  # Primary monitor fallback
                    print("DEBUG: Invalid window bounds, using full screen fallback")
                else:
                    monitor = window_bounds
                    print(f"DEBUG: Using window bounds: {monitor}")
            
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
                        
                        # Update window bounds each frame in case window moves/resizes
                        if window_bounds is not None:
                            updated_bounds = self._get_focused_window_bounds()
                            if updated_bounds and updated_bounds["width"] > 0 and updated_bounds["height"] > 0:
                                monitor = updated_bounds
                        
                        # Capture and process frame
                        screenshot = sct.grab(monitor)
                        frame = np.array(screenshot)
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        
                        # Resize frame if window size changed
                        if frame_bgr.shape[1] != width or frame_bgr.shape[0] != height:
                            frame_bgr = cv2.resize(frame_bgr, (width, height))
                        
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