# DPS Clip Tracker

A Python application for recording video clips triggered by customizable input bindings (keyboard, mouse, or Xbox controller). Features a modern GUI with video playback capabilities and automatic recording stop after 3 seconds of inactivity.

## Features

- **Multi-input Support**: Bind recording to keyboard keys, mouse buttons, or Xbox controller buttons
- **Global Hotkeys**: Works even when the application is not in focus
- **Screen Recording**: Captures the entire screen with high quality
- **Auto-stop**: Automatically stops recording after 3 seconds of input inactivity
- **Video Playback**: Built-in video player to review recorded clips
- **Cross-platform**: Runs on Windows and Linux

## Requirements

- Python 3.8 or higher
- Webcam or screen recording capability
- (Optional) Xbox controller for gamepad input

## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/username/dps-clip-tracker.git
cd dps-clip-tracker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python -m src.main
```

### Using Make (Linux/macOS)

```bash
make install  # Install dependencies
make run      # Run the application
make test     # Run tests
make build    # Build executable
```

### Using Build Scripts

**Linux/macOS:**
```bash
chmod +x scripts/build.sh
./scripts/build.sh
```

**Windows:**
```batch
scripts\build.bat
```

## Usage

1. **Launch the Application**: Run the application using one of the methods above
2. **Set Input Binding**: 
   - Select input type (Keyboard, Mouse, or Gamepad)
   - Click "Click to Bind Key" and press your desired key/button
3. **Start Recording**: The application will automatically start recording when you press the bound key
4. **Auto-stop**: Recording stops automatically after 3 seconds of inactivity
5. **Playback**: Double-click any recorded clip in the list to play it back

## Architecture

The application follows an object-oriented design with the following main components:

- **VideoRecorder**: Handles screen recording using OpenCV and MSS
- **InputHandler**: Manages global input detection for keyboard, mouse, and gamepad
- **GUI**: PyQt6-based user interface with video playback
- **Controller**: Coordinates between components and manages application state

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Or using Make:
```bash
make test
```

## Building Executables

### Current Platform
```bash
make build
```

### Cross-platform (using Docker)
```bash
make build-windows  # Build Windows executable
make build-linux    # Build Linux executable
```

## Development

### Setup Development Environment
```bash
make dev-install
```

### Code Formatting
```bash
make format  # Format code
make lint    # Check code style
```

### Project Structure
```
dps-clip-tracker/
├── src/
│   ├── main.py           # Application entry point
│   ├── video_recorder.py # Screen recording functionality
│   ├── input_handler.py  # Input detection and binding
│   ├── gui.py            # PyQt6 GUI components
│   └── controller.py     # Application controller
├── tests/
│   └── test_*.py         # Unit tests
├── scripts/
│   ├── build.sh          # Linux build script
│   └── build.bat         # Windows build script
├── requirements.txt      # Python dependencies
└── README.md
```

## Dependencies

- **PyQt6**: GUI framework
- **OpenCV**: Video processing
- **MSS**: Screen capture
- **pynput**: Global input detection
- **pygame**: Gamepad support
- **pytest**: Testing framework
- **pyinstaller**: Executable building

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

**"No gamepad detected"**: Ensure your Xbox controller is properly connected and recognized by the system.

**"pynput not available"**: Install pynput: `pip install pynput`

**Recording not working**: Check that the application has screen recording permissions on your system.

**Build failures**: Ensure all dependencies are installed and you're using Python 3.8+.

### Platform-specific Notes

**Linux**: May require additional packages for screen recording:
```bash
sudo apt-get install python3-dev libxcb-xinerama0
```

**Windows**: Run as administrator for global hotkey functionality.

## Support

For issues and questions, please open an issue on the GitHub repository.