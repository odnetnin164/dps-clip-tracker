import os
import subprocess
import platform
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional, Callable


class FFmpegInstaller:
    """Handles ffmpeg installation and availability checking."""
    
    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        """
        Initialize the FFmpeg installer.
        
        Args:
            progress_callback: Optional callback function that receives (message, percentage)
        """
        self.progress_callback = progress_callback
        
    def _report_progress(self, message: str, percentage: int):
        """Report progress to the callback if available."""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        else:
            print(f"DEBUG: {message} ({percentage}%)")
    
    def ensure_ffmpeg_available(self) -> str:
        """
        Ensure ffmpeg is available, download if necessary.
        
        Returns:
            str: Path to ffmpeg executable
        """
        self._report_progress("Checking for FFmpeg...", 0)
        
        # Check if ffmpeg is in PATH first
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._report_progress("Found system FFmpeg", 100)
                return "ffmpeg"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Check local ffmpeg folder
        local_ffmpeg_dir = Path("ffmpeg")
        system = platform.system()
        
        if system == "Windows":
            ffmpeg_exe = local_ffmpeg_dir / "bin" / "ffmpeg.exe"
        else:
            ffmpeg_exe = local_ffmpeg_dir / "ffmpeg"
            
        if ffmpeg_exe.exists():
            self._report_progress("Found local FFmpeg", 100)
            return str(ffmpeg_exe)
        
        # Download ffmpeg
        self._report_progress("FFmpeg not found, downloading...", 5)
        return self._download_ffmpeg()
    
    def _download_ffmpeg(self) -> str:
        """Download ffmpeg for the current platform."""
        system = platform.system()
        
        # Create platform-specific directory
        if system == "Windows":
            platform_dir = Path("ffmpeg/windows")
        elif system == "Linux":
            platform_dir = Path("ffmpeg/linux")
        elif system == "Darwin":  # macOS
            platform_dir = Path("ffmpeg/macos")
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
        
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        self._report_progress("Preparing download...", 10)
        
        if system == "Windows":
            return self._download_ffmpeg_windows()
        elif system == "Linux":
            return self._download_ffmpeg_linux()
        elif system == "Darwin":  # macOS
            return self._download_ffmpeg_macos()
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
    
    def _download_with_progress(self, url: str, filepath: Path):
        """Download a file with progress reporting."""
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percentage = min(int((downloaded / total_size) * 50) + 20, 70)  # 20-70% range
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                self._report_progress(f"Downloading FFmpeg... {mb_downloaded:.1f}/{mb_total:.1f} MB", percentage)
        
        urllib.request.urlretrieve(url, filepath, reporthook=progress_hook)
    
    def _download_ffmpeg_windows(self) -> str:
        """Download ffmpeg for Windows."""
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        platform_dir = Path("ffmpeg/windows")
        zip_path = platform_dir / "ffmpeg-windows.zip"
        
        self._report_progress("Downloading FFmpeg for Windows...", 15)
        self._download_with_progress(url, zip_path)
        
        self._report_progress("Extracting FFmpeg...", 75)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(platform_dir)
        
        # Find the extracted ffmpeg.exe and move it to the platform directory
        for root, dirs, files in os.walk(platform_dir):
            if "ffmpeg.exe" in files and "bin" in root:
                source_ffmpeg = Path(root) / "ffmpeg.exe"
                target_ffmpeg = platform_dir / "ffmpeg.exe"
                
                # Move ffmpeg.exe to the platform directory root
                if source_ffmpeg != target_ffmpeg:
                    source_ffmpeg.rename(target_ffmpeg)
                
                self._report_progress("FFmpeg installation complete!", 95)
                
                # Clean up zip file and extracted folders
                zip_path.unlink()
                # Clean up the extracted directory structure, keeping only ffmpeg.exe
                for item in platform_dir.iterdir():
                    if item.is_dir() and item.name.startswith("ffmpeg-"):
                        import shutil
                        shutil.rmtree(item)
                
                self._report_progress("Installation finished", 100)
                return str(target_ffmpeg)
        
        raise RuntimeError("Could not find ffmpeg.exe after extraction")
    
    def _download_ffmpeg_linux(self) -> str:
        """Download ffmpeg for Linux."""
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        platform_dir = Path("ffmpeg/linux")
        tar_path = platform_dir / "ffmpeg-linux.tar.xz"
        
        self._report_progress("Downloading FFmpeg for Linux...", 15)
        self._download_with_progress(url, tar_path)
        
        self._report_progress("Extracting FFmpeg...", 75)
        subprocess.run(["tar", "-xf", str(tar_path), "-C", str(platform_dir), "--strip-components=1"], 
                      check=True)
        
        ffmpeg_exe = platform_dir / "ffmpeg"
        if ffmpeg_exe.exists():
            # Make executable
            ffmpeg_exe.chmod(0o755)
            self._report_progress("FFmpeg installation complete!", 95)
            # Clean up tar file
            tar_path.unlink()
            self._report_progress("Installation finished", 100)
            return str(ffmpeg_exe)
        
        raise RuntimeError("Could not find ffmpeg after extraction")
    
    def _download_ffmpeg_macos(self) -> str:
        """Download ffmpeg for macOS."""
        url = "https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip"
        platform_dir = Path("ffmpeg/macos")
        zip_path = platform_dir / "ffmpeg-macos.zip"
        
        self._report_progress("Downloading FFmpeg for macOS...", 15)
        self._download_with_progress(url, zip_path)
        
        self._report_progress("Extracting FFmpeg...", 75)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(platform_dir)
        
        ffmpeg_exe = platform_dir / "ffmpeg"
        if ffmpeg_exe.exists():
            # Make executable
            ffmpeg_exe.chmod(0o755)
            self._report_progress("FFmpeg installation complete!", 95)
            # Clean up zip file
            zip_path.unlink()
            self._report_progress("Installation finished", 100)
            return str(ffmpeg_exe)
        
        raise RuntimeError("Could not find ffmpeg after extraction")
    
    @staticmethod
    def is_ffmpeg_available() -> bool:
        """
        Quick check if ffmpeg is available without downloading.
        
        Returns:
            bool: True if ffmpeg is available locally
        """
        return FFmpegInstaller.get_ffmpeg_path() is not None
    
    @staticmethod
    def get_ffmpeg_path() -> Optional[str]:
        """
        Get the path to ffmpeg executable if available.
        
        Returns:
            str or None: Path to ffmpeg executable, or None if not available
        """
        # Check system PATH first
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "ffmpeg"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Check local platform-specific installation
        system = platform.system()
        if system == "Windows":
            ffmpeg_exe = Path("ffmpeg/windows/ffmpeg.exe")
        elif system == "Linux":
            ffmpeg_exe = Path("ffmpeg/linux/ffmpeg")
        elif system == "Darwin":  # macOS
            ffmpeg_exe = Path("ffmpeg/macos/ffmpeg")
        else:
            return None
            
        if ffmpeg_exe.exists():
            return str(ffmpeg_exe)
        
        return None
    
    @staticmethod
    def validate_ffmpeg_installation(ffmpeg_path: str) -> bool:
        """
        Validate that the given ffmpeg path is functional.
        
        Args:
            ffmpeg_path: Path to ffmpeg executable
            
        Returns:
            bool: True if ffmpeg is functional
        """
        try:
            result = subprocess.run([ffmpeg_path, "-version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False