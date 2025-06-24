# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development
- `make run` - Run the application
- `python -m src.main` - Run directly without make
- `scripts/run.ps1` - Run on Windows using PowerShell
- `make test` - Run full test suite 
- `python3 -m pytest tests/test_video_recorder.py -v` - Run specific test file
- `python3 -m pytest tests/test_controller.py::TestClipRecorderController::test_init -v` - Run single test

### Dependencies
- `pip3 install -r requirements.txt` - Install dependencies (note: NumPy must be <2.0.0 for OpenCV compatibility)
- `make dev-install` - Install with development dependencies
- **IMPORTANT**: Always use requirements.txt or Makefile for dependency management. Never install packages directly with pip.

### Code Quality
- `make lint` - Check code style with flake8, black, and isort
- `make format` - Auto-format code with black and isort

### Building
- `make build` - Build executable for current platform
- `python3 build_spec.py` - Direct PyInstaller build
- `make build-linux` or `make build-windows` - Cross-platform builds using Docker

## Architecture Overview

This is a video clip recording application with a **Controller-View pattern** where the `ClipRecorderController` acts as the central coordinator between three main subsystems:

### Core Components

**ClipRecorderController** (`src/controller.py`):
- Central coordinator inheriting from `QObject` for Qt signal integration
- Manages application state (recording/monitoring status) 
- Orchestrates interactions between VideoRecorder, InputHandler, and GUI
- Emits Qt signals: `recording_started`, `recording_stopped`, `status_changed`

**VideoRecorder** (`src/video_recorder.py`):
- Handles screen capture using MSS (Multi-Screen-Shot) library
- Uses OpenCV for video encoding (mp4v codec)
- Runs recording in separate thread with threading.Event for coordination
- Saves to configurable output directory (default: "recordings/")

**InputHandler** (`src/input_handler.py`):
- Strategy pattern implementation with `InputListener` abstract base class
- Three concrete listeners: `KeyboardListener`, `MouseListener`, `GamepadListener`
- Uses pynput for global keyboard/mouse detection, pygame for gamepad
- Implements 3-second idle timeout using threading.Timer
- Gracefully handles missing dependencies (pygame/pynput unavailable)

**GUI** (`src/gui.py`):
- PyQt6-based interface with custom widgets
- `MainWindow` contains `KeyBindingWidget`, `VideoListWidget`, `VideoPlayerWidget`
- Video playback via `QMediaPlayer` (note: requires audio libraries on Linux)
- Signal-slot architecture connects GUI events to controller methods

### Key Data Flow

1. User sets input binding via GUI → `ClipRecorderController.set_input_binding()`
2. Controller configures appropriate `InputListener` and starts monitoring
3. Global input detected → `InputHandler._on_input_received()` → `Controller._on_input_triggered()`
4. Recording starts via `VideoRecorder.start_recording()` in separate thread
5. After 3 seconds of inactivity → `InputHandler._on_idle_timeout()` → recording stops
6. GUI automatically refreshes video list and can play the new recording

### Testing Architecture

- Comprehensive unit tests using pytest with PyQt6 support
- Extensive mocking of external dependencies (OpenCV, pynput, pygame)
- Test structure mirrors source: `tests/test_<component>.py` for each `src/<component>.py`
- Known issue: Some threading warnings in tests due to background recording threads

### Platform Considerations

**Linux**: May need `sudo apt-get install python3-dev libxcb-xinerama0` for screen recording and `libpulse.so.0` for GUI audio components.

**Windows**: Requires administrator privileges for global hotkey functionality.

The application uses NumPy <2.0.0 due to OpenCV compatibility requirements.