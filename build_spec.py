import PyInstaller.__main__
import sys
import os
from pathlib import Path

# PyInstaller spec file for building executables

def build_windows():
    PyInstaller.__main__.run([
        '--name=DPSClipTracker',
        '--onefile',
        '--windowed',
        '--icon=assets/icon.ico',
        '--add-data=assets;assets',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtMultimedia',
        '--hidden-import=PyQt6.QtMultimediaWidgets',
        '--hidden-import=cv2',
        '--hidden-import=mss',
        '--hidden-import=pynput',
        '--hidden-import=pygame',
        '--collect-all=cv2',
        '--collect-all=mss',
        'src/main.py'
    ])

def build_linux():
    PyInstaller.__main__.run([
        '--name=DPSClipTracker',
        '--onefile',
        '--windowed',
        '--add-data=assets:assets',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtMultimedia',
        '--hidden-import=PyQt6.QtMultimediaWidgets',
        '--hidden-import=cv2',
        '--hidden-import=mss',
        '--hidden-import=pynput',
        '--hidden-import=pygame',
        '--collect-all=cv2',
        '--collect-all=mss',
        'src/main.py'
    ])

if __name__ == "__main__":
    platform = sys.platform
    
    if platform.startswith('win'):
        print("Building for Windows...")
        build_windows()
    elif platform.startswith('linux'):
        print("Building for Linux...")
        build_linux()
    else:
        print(f"Unsupported platform: {platform}")
        sys.exit(1)
        
    print("Build completed!")