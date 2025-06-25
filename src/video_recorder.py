import subprocess
import time
import platform
from pathlib import Path
from typing import Optional
from .ffmpeg_installer import FFmpegInstaller


class VideoRecorder:
    def __init__(self, output_dir: str = "recordings", fps: int = 30, ffmpeg_path: Optional[str] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.fps = fps
        self.is_recording = False
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.current_filename: Optional[str] = None
        
        # Get ffmpeg path from FFmpegInstaller
        if ffmpeg_path:
            self.ffmpeg_path = ffmpeg_path
        else:
            self.ffmpeg_path = FFmpegInstaller.get_ffmpeg_path()
            if not self.ffmpeg_path:
                raise RuntimeError("FFmpeg is not available. Please install FFmpeg first.")
    
    def _get_focused_window_title(self) -> Optional[str]:
        """Get the title of the currently focused window."""
        system = platform.system()
        
        try:
            if system == "Windows":
                return self._get_windows_focused_window_title()
            elif system == "Linux":
                return self._get_linux_focused_window_title()
            elif system == "Darwin":  # macOS
                return self._get_macos_focused_window_title()
        except Exception as e:
            print(f"DEBUG: Could not get focused window title: {e}")
        
        return None
    
    def _get_windows_focused_window_title(self) -> Optional[str]:
        """Get focused window title on Windows."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd)
                return title if title else None
        except ImportError:
            # Fallback using PowerShell
            try:
                ps_script = '''
                Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    using System.Text;
                    public class Win32 {
                        [DllImport("user32.dll")]
                        public static extern IntPtr GetForegroundWindow();
                        [DllImport("user32.dll")]
                        public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
                    }
"@
                $hwnd = [Win32]::GetForegroundWindow()
                $sb = New-Object System.Text.StringBuilder(256)
                $length = [Win32]::GetWindowText($hwnd, $sb, $sb.Capacity)
                if ($length -gt 0) {
                    Write-Output $sb.ToString()
                }
                '''
                result = subprocess.run([
                    "powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                pass
        except Exception:
            pass
        
        return None
    
    def _get_linux_focused_window_title(self) -> Optional[str]:
        """Get focused window title on Linux."""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return None
    
    def _get_macos_focused_window_title(self) -> Optional[str]:
        """Get focused window title on macOS."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set frontWindow to front window of frontApp
                return name of frontWindow
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, ValueError):
            pass
        
        return None
    
    def _get_ffmpeg_command(self, output_file: str) -> list:
        """Build ffmpeg command for recording focused window with audio."""
        system = platform.system()
        cmd = [self.ffmpeg_path, "-y"]  # -y to overwrite existing files
        
        if system == "Windows":
            # Windows: Use gdigrab to capture window and dshow for audio
            window_title = self._get_focused_window_title()
            if window_title:
                cmd.extend(["-f", "gdigrab", "-i", f"title={window_title}"])
            else:
                # Fallback to desktop capture
                cmd.extend(["-f", "gdigrab", "-i", "desktop"])
            
            # Add audio input (default audio device)
            cmd.extend(["-f", "dshow", "-i", "audio="])
            
        elif system == "Linux":
            # Linux: Use x11grab for screen and pulse/alsa for audio
            cmd.extend(["-f", "x11grab"])
            
            # Try to get focused window position for more precise capture
            window_title = self._get_focused_window_title()
            if window_title:
                # For now, capture full screen - window-specific capture is complex on Linux
                cmd.extend(["-i", ":0.0"])
            else:
                cmd.extend(["-i", ":0.0"])
            
            # Add audio input (PulseAudio default)
            cmd.extend(["-f", "pulse", "-i", "default"])
            
        elif system == "Darwin":  # macOS
            # macOS: Use avfoundation
            cmd.extend(["-f", "avfoundation", "-i", "1:0"])  # Screen:Audio
            
        # Video and audio encoding options
        cmd.extend([
            "-c:v", "libx264",     # H.264 video codec
            "-preset", "ultrafast", # Fast encoding
            "-crf", "23",          # Good quality
            "-r", str(self.fps),   # Frame rate
            "-c:a", "aac",         # AAC audio codec
            "-b:a", "128k",        # Audio bitrate
            output_file
        ])
        
        return cmd
    
    def start_recording(self, filename: Optional[str] = None) -> str:
        """Start recording the focused window with audio."""
        if self.is_recording:
            raise RuntimeError("Recording already in progress")
        
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"clip_{timestamp}.mp4"
        
        self.current_filename = str(self.output_dir / filename)
        
        # Build ffmpeg command
        cmd = self._get_ffmpeg_command(self.current_filename)
        
        print(f"DEBUG: Starting ffmpeg with command: {' '.join(cmd)}")
        
        try:
            # Start ffmpeg process
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give ffmpeg a moment to start
            time.sleep(0.5)
            
            # Check if process started successfully
            if self.ffmpeg_process.poll() is not None:
                stdout, stderr = self.ffmpeg_process.communicate()
                raise RuntimeError(f"FFmpeg failed to start: {stderr}")
            
            self.is_recording = True
            print(f"DEBUG: Recording started, saving to {self.current_filename}")
            
        except Exception as e:
            print(f"ERROR: Failed to start recording: {e}")
            self.ffmpeg_process = None
            raise
        
        return self.current_filename
    
    def stop_recording(self) -> Optional[str]:
        """Stop the current recording."""
        if not self.is_recording or not self.ffmpeg_process:
            return None
        
        print("DEBUG: Stopping recording...")
        
        try:
            # Send quit signal to ffmpeg
            self.ffmpeg_process.stdin.write('q')
            self.ffmpeg_process.stdin.flush()
        except:
            # If stdin is not available, terminate the process
            self.ffmpeg_process.terminate()
        
        # Wait for process to finish (with timeout)
        try:
            stdout, stderr = self.ffmpeg_process.communicate(timeout=10)
            if stderr:
                print(f"DEBUG: FFmpeg output: {stderr}")
        except subprocess.TimeoutExpired:
            print("DEBUG: FFmpeg didn't stop gracefully, forcing termination")
            self.ffmpeg_process.kill()
            self.ffmpeg_process.communicate()
        
        self.is_recording = False
        result_filename = self.current_filename
        self.current_filename = None
        self.ffmpeg_process = None
        
        print(f"DEBUG: Recording stopped, saved to {result_filename}")
        return result_filename