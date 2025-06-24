import cv2
import numpy as np
import mss
import threading
import time
import platform
import subprocess
import wave
import pyaudio
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
        self.audio_thread: Optional[threading.Thread] = None
        self.current_filename: Optional[str] = None
        self.current_audio_filename: Optional[str] = None
        self.stop_recording_event = threading.Event()
        
        # Audio configuration
        self.audio_format = pyaudio.paInt16
        self.audio_channels = 2
        self.audio_rate = 44100
        self.audio_chunk = 1024
        self.audio_frames = []
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.audio_stream = None
        
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
        self.current_audio_filename = str(self.output_dir / filename.replace('.mp4', '_audio.wav'))
        self.stop_recording_event.clear()
        self.is_recording = True
        self.audio_frames = []
        
        # Start audio recording thread
        self.audio_thread = threading.Thread(target=self._record_audio)
        self.audio_thread.start()
        
        # Start video recording thread
        self.recording_thread = threading.Thread(target=self._record_screen)
        self.recording_thread.start()
        
        return self.current_filename
        
    def stop_recording(self) -> Optional[str]:
        if not self.is_recording:
            return None
            
        self.stop_recording_event.set()
        
        # Wait for both threads to complete
        if self.recording_thread:
            self.recording_thread.join()
        if self.audio_thread:
            self.audio_thread.join()
            
        # Save audio file
        if self.current_audio_filename and self.audio_frames:
            self._save_audio_file()
            
        # Combine video and audio into final file
        final_filename = self._combine_audio_video()
            
        self.is_recording = False
        self.current_filename = None
        self.current_audio_filename = None
        self.audio_frames = []
        
        return final_filename
        
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

    def _record_audio(self):
        """Record system audio using PyAudio with WASAPI loopback."""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Find WASAPI loopback device for system audio
            loopback_device_index = self._find_wasapi_loopback_device()
            
            if loopback_device_index is None:
                print("WARNING: No WASAPI loopback device found. Trying to enable programmatically...")
                # Fallback to default device (might be microphone)
                loopback_device_index = None
            
            try:
                # Open audio stream for recording
                self.audio_stream = self.pyaudio_instance.open(
                    format=self.audio_format,
                    channels=self.audio_channels,
                    rate=self.audio_rate,
                    input=True,
                    input_device_index=loopback_device_index,
                    frames_per_buffer=self.audio_chunk
                )
                
                print("DEBUG: System audio recording started")
                self.audio_frames = []
                
                # Record audio until stop event is set
                while not self.stop_recording_event.is_set():
                    try:
                        data = self.audio_stream.read(self.audio_chunk, exception_on_overflow=False)
                        self.audio_frames.append(data)
                    except Exception as e:
                        print(f"DEBUG: Audio read error: {e}")
                        break
                        
            except Exception as e:
                print(f"WARNING: Could not open audio stream: {e}")
                return
                
        except Exception as e:
            print(f"WARNING: Audio recording initialization failed: {e}")
        finally:
            # Clean up audio resources
            if self.audio_stream:
                try:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                except:
                    pass
                self.audio_stream = None
                
            if self.pyaudio_instance:
                try:
                    self.pyaudio_instance.terminate()
                except:
                    pass
                self.pyaudio_instance = None
                
            print("DEBUG: Audio recording stopped")

    def _find_wasapi_loopback_device(self) -> Optional[int]:
        """Find WASAPI loopback device for system audio recording."""
        if not self.pyaudio_instance:
            return None
            
        try:
            # Get all audio devices
            device_count = self.pyaudio_instance.get_device_count()
            
            print("DEBUG: Available audio devices:")
            for i in range(device_count):
                try:
                    device_info = self.pyaudio_instance.get_device_info_by_index(i)
                    device_name = device_info.get('name', '')
                    max_input_channels = device_info.get('maxInputChannels', 0)
                    print(f"  {i}: {device_name} (input channels: {max_input_channels})")
                    
                    # Look for WASAPI loopback devices
                    device_name_lower = device_name.lower()
                    if any(keyword in device_name_lower for keyword in [
                        'stereo mix', 'wave out mix', 'what u hear', 'loopback'
                    ]) and max_input_channels > 0:
                        print(f"DEBUG: Found system audio device: {device_name}")
                        return i
                        
                    # Alternative: look for speakers/headphones with WASAPI that support input
                    if ('speakers' in device_name_lower or 'headphones' in device_name_lower) and \
                       'wasapi' in device_name_lower and max_input_channels > 0:
                        print(f"DEBUG: Found potential WASAPI loopback device: {device_name}")
                        return i
                        
                except Exception as e:
                    print(f"DEBUG: Error checking device {i}: {e}")
                    continue
                    
            # If no specific loopback device found, try to enable stereo mix programmatically
            self._try_enable_stereo_mix()
            
            # Try again after attempting to enable stereo mix
            for i in range(device_count):
                try:
                    device_info = self.pyaudio_instance.get_device_info_by_index(i)
                    device_name = device_info.get('name', '').lower()
                    if 'stereo mix' in device_name and device_info.get('maxInputChannels', 0) > 0:
                        print(f"DEBUG: Found stereo mix after enabling: {device_info['name']}")
                        return i
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"DEBUG: Error finding WASAPI loopback device: {e}")
            
        return None

    def _try_enable_stereo_mix(self):
        """Try to enable stereo mix on Windows using PowerShell."""
        if platform.system() != "Windows":
            return
            
        try:
            # PowerShell script to enable stereo mix
            ps_script = '''
            $devices = Get-WmiObject -Class Win32_SoundDevice
            foreach ($device in $devices) {
                if ($device.Name -like "*Stereo Mix*") {
                    Write-Output "Found Stereo Mix device"
                }
            }
            '''
            
            # This is a simplified attempt - full implementation would require more complex registry manipulation
            print("DEBUG: Attempting to enable stereo mix (may require manual intervention)")
            
        except Exception as e:
            print(f"DEBUG: Could not enable stereo mix programmatically: {e}")

    def _save_audio_file(self):
        """Save recorded audio frames to a WAV file."""
        try:
            if not self.audio_frames:
                print("DEBUG: No audio frames to save")
                return
                
            # Save audio frames to WAV file
            with wave.open(self.current_audio_filename, 'wb') as wav_file:
                wav_file.setnchannels(self.audio_channels)
                wav_file.setsampwidth(2)  # 16-bit audio = 2 bytes
                wav_file.setframerate(self.audio_rate)
                wav_file.writeframes(b''.join(self.audio_frames))
                
            print(f"DEBUG: Audio saved to {self.current_audio_filename}")
        except Exception as e:
            print(f"WARNING: Failed to save audio file: {e}")

    def _combine_audio_video(self) -> Optional[str]:
        """Combine video and audio files using ffmpeg."""
        if not self.current_filename or not self.current_audio_filename:
            return self.current_filename
            
        try:
            # Check if audio file exists and has content
            audio_path = Path(self.current_audio_filename)
            if not audio_path.exists() or audio_path.stat().st_size == 0:
                print("DEBUG: No audio file to combine, returning video-only file")
                return self.current_filename
                
            # Create output filename with audio
            video_with_audio = self.current_filename.replace('.mp4', '_with_audio.mp4')
            
            # Use ffmpeg to combine video and audio
            ffmpeg_cmd = [
                'ffmpeg', '-y',  # -y to overwrite existing files
                '-i', self.current_filename,  # video input
                '-i', self.current_audio_filename,  # audio input
                '-c:v', 'copy',  # copy video codec
                '-c:a', 'aac',  # encode audio as AAC
                '-shortest',  # finish when shortest stream ends
                video_with_audio
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Clean up temporary files
                try:
                    Path(self.current_filename).unlink()  # Remove video-only file
                    Path(self.current_audio_filename).unlink()  # Remove audio file
                except Exception as e:
                    print(f"DEBUG: Could not clean up temporary files: {e}")
                
                print(f"DEBUG: Combined video and audio saved to {video_with_audio}")
                return video_with_audio
            else:
                print(f"WARNING: ffmpeg failed: {result.stderr}")
                return self.current_filename
                
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"WARNING: Could not combine audio and video (ffmpeg not available?): {e}")
            return self.current_filename
        except Exception as e:
            print(f"WARNING: Unexpected error combining audio and video: {e}")
            return self.current_filename
                    
    def get_screen_size(self) -> Tuple[int, int]:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            return monitor["width"], monitor["height"]