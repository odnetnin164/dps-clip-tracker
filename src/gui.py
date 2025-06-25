import sys
import os
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGroupBox, QMessageBox, QSlider,
    QGridLayout, QScrollArea, QSizePolicy, QFrame, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget

from .input_handler import InputType, InputBinding
from .controller import ClipRecorderController


class KeyBindingWidget(QWidget):
    binding_changed = pyqtSignal(InputBinding)
    gamepad_binding_detected = pyqtSignal(InputBinding)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_binding: Optional[InputBinding] = None
        self.temp_listener = None
        self.is_binding = False
        self.selected_input_type = InputType.KEYBOARD  # Default to keyboard
        
        # Connect gamepad signal
        self.gamepad_binding_detected.connect(self._on_binding_captured)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        
        self.input_type_combo = QComboBox()
        self.input_type_combo.addItems(["Keyboard", "Mouse", "Gamepad"])
        self.input_type_combo.currentTextChanged.connect(self.on_input_type_changed)
        
        self.bind_button = QPushButton("Click to Bind Key")
        self.bind_button.clicked.connect(self.start_key_binding)
        
        self.current_binding_label = QLabel("No binding set")
        
        layout.addWidget(QLabel("Input Type:"))
        layout.addWidget(self.input_type_combo)
        layout.addWidget(self.bind_button)
        layout.addWidget(self.current_binding_label)
        
        self.setLayout(layout)
        
    def on_input_type_changed(self, text: str):
        input_type_map = {
            "Keyboard": InputType.KEYBOARD,
            "Mouse": InputType.MOUSE,
            "Gamepad": InputType.GAMEPAD
        }
        self.selected_input_type = input_type_map.get(text, InputType.KEYBOARD)
        
    def start_key_binding(self):
        if self.is_binding:
            return
            
        self.bind_button.setText("Press a key...")
        self.bind_button.setEnabled(False)
        self.is_binding = True
        
        try:
            if self.selected_input_type == InputType.KEYBOARD:
                self._start_keyboard_binding()
            elif self.selected_input_type == InputType.MOUSE:
                self._start_mouse_binding()
            elif self.selected_input_type == InputType.GAMEPAD:
                self._start_gamepad_binding()
        except Exception as e:
            self._reset_binding_state()
            self.current_binding_label.setText(f"Error: {str(e)}")
    
    def _start_keyboard_binding(self):
        try:
            from pynput import keyboard
            self.temp_listener = keyboard.Listener(on_press=self._on_key_captured)
            self.temp_listener.start()
        except ImportError:
            raise RuntimeError("pynput not available for keyboard input")
    
    def _start_mouse_binding(self):
        try:
            from pynput import mouse
            self.temp_listener = mouse.Listener(on_click=self._on_mouse_captured)
            self.temp_listener.start()
        except ImportError:
            raise RuntimeError("pynput not available for mouse input")
    
    def _start_gamepad_binding(self):
        try:
            # Import InputHandler to use for gamepad detection
            from .input_handler import InputHandler
            
            # Create temporary input handler for binding detection
            if not hasattr(self, 'temp_input_handler'):
                self.temp_input_handler = InputHandler()
            
            # Start gamepad binding detection
            success = self.temp_input_handler.detect_and_bind_gamepad_button(
                self._on_gamepad_button_detected
            )
            
            if not success:
                raise RuntimeError("Failed to start gamepad detection")
                
        except Exception as e:
            raise RuntimeError(f"Gamepad binding failed: {str(e)}")
    
    def _on_gamepad_button_detected(self, binding):
        """Called when a gamepad button is detected during binding"""
        # Stop the temporary detection
        if hasattr(self, 'temp_input_handler'):
            self.temp_input_handler.stop_gamepad_binding_detection()
            
        # Emit the binding signal to the main thread
        self.gamepad_binding_detected.emit(binding)
    
    def _on_key_captured(self, key):
        display_name = self._get_key_display_name(key)
        binding = InputBinding(InputType.KEYBOARD, key, display_name)
        self._on_binding_captured(binding)
    
    def _on_mouse_captured(self, x, y, button, pressed):
        if pressed:  # Only respond to button press, not release
            display_name = f"Mouse {button.name.title()}"
            binding = InputBinding(InputType.MOUSE, button, display_name)
            self._on_binding_captured(binding)
    
    def _on_binding_captured(self, binding: InputBinding):
        self._stop_temp_listener()
        # Small delay to ensure cleanup is complete
        import time
        time.sleep(0.1)
        self.set_binding(binding)
    
    def _stop_temp_listener(self):
        if self.temp_listener:
            self.temp_listener.stop()
            self.temp_listener = None
        
        # Stop temporary input handler for gamepad binding
        if hasattr(self, 'temp_input_handler'):
            print("KeyBindingWidget: Stopping gamepad binding detection...")
            self.temp_input_handler.stop_gamepad_binding_detection()
            self.temp_input_handler = None
            print("KeyBindingWidget: Gamepad binding detection stopped")
    
    def _reset_binding_state(self):
        self._stop_temp_listener()
        self.is_binding = False
        self.bind_button.setText("Click to Bind Key")
        self.bind_button.setEnabled(True)
    
    def _get_key_display_name(self, key) -> str:
        if hasattr(key, 'char') and key.char:
            return key.char.upper()
        elif hasattr(key, 'name'):
            return key.name.replace('_', ' ').title()
        else:
            return str(key)
        
    def set_binding(self, binding: InputBinding):
        self.current_binding = binding
        self.current_binding_label.setText(f"Bound: {binding.display_name}")
        self.is_binding = False
        self.bind_button.setText("Click to Bind Key")
        self.bind_button.setEnabled(True)
        self.binding_changed.emit(binding)


class VideoGridWidget(QWidget):
    video_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recordings_dir = Path("recordings")
        self.video_widgets = []
        self.current_selected = None
        self.media_players = []  # Track all media players
        self.setup_ui()
        self.refresh_video_grid()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Create scroll area for video grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Container widget for the grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.grid_container.setLayout(self.grid_layout)
        
        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)
        
        self.setLayout(layout)
        
    def refresh_video_grid(self):
        # Clear existing widgets and cleanup media players
        for widget in self.video_widgets:
            if hasattr(widget, 'media_player'):
                widget.media_player.stop()
                widget.media_player.deleteLater()
            widget.deleteLater()
        self.video_widgets.clear()
        self.media_players.clear()
        self.current_selected = None
        
        # Clear layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.recordings_dir.exists():
            return
            
        video_files = list(self.recordings_dir.glob("*.mp4"))
        video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not video_files:
            return
            
        # If only one video, make it take full space
        if len(video_files) == 1:
            video_widget = self.create_video_thumbnail(video_files[0])
            self.grid_layout.addWidget(video_widget, 0, 0)
            self.video_widgets.append(video_widget)
        else:
            # Multiple videos - arrange in grid
            cols = min(3, len(video_files))  # Max 3 columns
            for i, video_file in enumerate(video_files):
                row = i // cols
                col = i % cols
                video_widget = self.create_video_thumbnail(video_file)
                self.grid_layout.addWidget(video_widget, row, col)
                self.video_widgets.append(video_widget)
                
        # Emit signal when videos are loaded
        if self.media_players:
            self.video_selected.emit("")  # Trigger connection setup
                
    def create_video_thumbnail(self, video_file: Path) -> QWidget:
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        widget.setMinimumSize(200, 150)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        widget.setStyleSheet("""
            QFrame {
                border: 2px solid #ccc;
                border-radius: 5px;
                background-color: #000;
            }
            QFrame:hover {
                border-color: #007acc;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Video widget for actual video display
        video_widget = QVideoWidget()
        video_widget.setMinimumSize(200, 150)
        video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Create media player for this video
        media_player = QMediaPlayer()
        media_player.setVideoOutput(video_widget)
        media_player.setSource(QUrl.fromLocalFile(str(video_file)))
        
        # Track if we've reached the end to prevent reset
        video_ended = False
        last_valid_position = 0
        
        # Set up media player to show first frame and stay on last frame
        def on_media_status_changed(status):
            nonlocal video_ended
            if status == QMediaPlayer.MediaStatus.LoadedMedia:
                # Seek to first frame and pause to show it
                media_player.setPosition(0)
                media_player.pause()
                video_ended = False
            elif status == QMediaPlayer.MediaStatus.EndOfMedia:
                # Mark that video has ended
                video_ended = True
                
        def on_position_changed(position):
            nonlocal video_ended, last_valid_position
            duration = media_player.duration()
            
            # If video ended and position resets to 0, seek back to end
            if video_ended and position == 0 and duration > 0:
                media_player.setPosition(duration - 33)  # Go to last frame
                media_player.pause()
            elif not video_ended and position > 0:
                last_valid_position = position
        
        def on_duration_changed(duration):
            if duration > 0:
                print(f"Duration changed for {video_file.name}: {duration}ms")  # Debug
                # Trigger timeline refresh when duration is available
                self.video_selected.emit("")
        
        media_player.mediaStatusChanged.connect(on_media_status_changed)
        media_player.positionChanged.connect(on_position_changed)
        media_player.durationChanged.connect(on_duration_changed)
        
        layout.addWidget(video_widget)
        widget.setLayout(layout)
        
        # Store video path and media player for selection
        widget.video_path = str(video_file)
        widget.media_player = media_player
        widget.video_widget = video_widget
        
        # Add to list of all media players
        self.media_players.append(media_player)
        
        # Make clickable
        widget.mousePressEvent = lambda event: self.select_video(widget)
        
        return widget
        
    def select_video(self, widget):
        # Update selection styling
        if self.current_selected:
            self.current_selected.setStyleSheet("""
                QFrame {
                    border: 2px solid #ccc;
                    border-radius: 5px;
                    background-color: #000;
                }
                QFrame:hover {
                    border-color: #007acc;
                }
            """)
            
        widget.setStyleSheet("""
            QFrame {
                border: 3px solid #007acc;
                border-radius: 5px;
                background-color: #000;
            }
        """)
        
        self.current_selected = widget
        self.video_selected.emit(widget.video_path)
        
    def delete_selected_video(self):
        if not self.current_selected:
            return
            
        video_path = Path(self.current_selected.video_path)
        
        reply = QMessageBox.question(
            self, 
            "Delete Video", 
            f"Are you sure you want to delete {video_path.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                video_path.unlink()
                self.refresh_video_grid()
            except OSError as e:
                QMessageBox.warning(self, "Error", f"Could not delete file: {e}")
                
    def play_all_videos(self):
        """Start playing all videos simultaneously"""
        for player in self.media_players:
            player.play()
            
    def pause_all_videos(self):
        """Pause all videos simultaneously"""
        for player in self.media_players:
            player.pause()
            
    def stop_all_videos(self):
        """Stop all videos simultaneously and show first frame"""
        for player in self.media_players:
            player.stop()
            player.setPosition(0)
            player.pause()
            
    def seek_all_videos(self, position: int):
        """Seek all videos to the same position"""
        for player in self.media_players:
            player.setPosition(position)
            
    def restart_all_videos(self):
        """Restart all videos from the beginning"""
        for player in self.media_players:
            player.setPosition(0)
            player.pause()
            
    def get_primary_player(self):
        """Get the first media player for timeline/duration reference"""
        return self.media_players[0] if self.media_players else None


class MediaControlsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_grid = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # Restart button
        self.restart_button = QPushButton("⏮")
        self.restart_button.setToolTip("Restart")
        self.restart_button.setFixedSize(40, 40)
        self.restart_button.clicked.connect(self.restart_video)
        layout.addWidget(self.restart_button)
        
        # Step backward button
        self.step_back_button = QPushButton("⏪")
        self.step_back_button.setToolTip("Step 1 frame backward")
        self.step_back_button.setFixedSize(40, 40)
        self.step_back_button.clicked.connect(self.step_backward)
        layout.addWidget(self.step_back_button)
        
        # Play/Pause button
        self.play_button = QPushButton("▶")
        self.play_button.setToolTip("Play/Pause")
        self.play_button.setFixedSize(50, 40)
        self.play_button.clicked.connect(self.toggle_playback)
        layout.addWidget(self.play_button)
        
        # Step forward button
        self.step_forward_button = QPushButton("⏩")
        self.step_forward_button.setToolTip("Step 1 frame forward")
        self.step_forward_button.setFixedSize(40, 40)
        self.step_forward_button.clicked.connect(self.step_forward)
        layout.addWidget(self.step_forward_button)
        
        # Spacer
        layout.addItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Time display
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        layout.addWidget(self.time_label)
        
        self.setLayout(layout)
        
    def set_video_grid(self, video_grid: 'VideoGridWidget'):
        self.video_grid = video_grid
        
    def restart_video(self):
        if self.video_grid:
            self.video_grid.restart_all_videos()
            
    def toggle_playback(self):
        if not self.video_grid:
            return
            
        primary_player = self.video_grid.get_primary_player()
        if primary_player and primary_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.video_grid.pause_all_videos()
            self.play_button.setText("▶")
        else:
            self.video_grid.play_all_videos()
            self.play_button.setText("⏸")
            
    def step_backward(self):
        if self.video_grid:
            primary_player = self.video_grid.get_primary_player()
            if primary_player:
                current_pos = primary_player.position()
                new_pos = max(0, current_pos - 33)  # ~1 frame at 30fps
                self.video_grid.seek_all_videos(new_pos)
            
    def step_forward(self):
        if self.video_grid:
            primary_player = self.video_grid.get_primary_player()
            if primary_player:
                current_pos = primary_player.position()
                duration = primary_player.duration()
                new_pos = min(duration, current_pos + 33)  # ~1 frame at 30fps
                self.video_grid.seek_all_videos(new_pos)
            
    def update_time_display(self, position: int, duration: int):
        if duration > 0:
            current_time = self.format_time(position)
            total_time = self.format_time(duration)
            self.time_label.setText(f"{current_time} / {total_time}")
            
    def media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_button.setText("▶")
            # When video ends, ensure all videos stay on last frame
            if self.video_grid:
                self.video_grid.pause_all_videos()
            
    def format_time(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


class VideoTimelineWidget(QWidget):
    position_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_grid = None
        self.timeline_widgets = []
        self.max_duration = 0
        self.setup_ui()
        
    def setup_ui(self):
        self.main_layout = QVBoxLayout()
        
        # Scroll area for multiple timelines
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setMaximumHeight(200)
        
        # Container for timelines
        self.timeline_container = QWidget()
        self.timeline_layout = QVBoxLayout()
        self.timeline_container.setLayout(self.timeline_layout)
        
        self.scroll_area.setWidget(self.timeline_container)
        self.main_layout.addWidget(self.scroll_area)
        
        self.setLayout(self.main_layout)
        
    def set_video_grid(self, video_grid: 'VideoGridWidget'):
        self.video_grid = video_grid
        self.refresh_timelines()
        
    def refresh_timelines(self):
        # Clear existing timelines and disconnect signals
        for widget in self.timeline_widgets:
            if hasattr(widget, 'media_player') and hasattr(widget, 'position_connection'):
                try:
                    widget.media_player.positionChanged.disconnect(widget.position_connection)
                except:
                    pass
            widget.deleteLater()
        self.timeline_widgets.clear()
        
        # Clear layout
        while self.timeline_layout.count():
            item = self.timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.video_grid or not self.video_grid.media_players:
            return
            
        # Check if durations are available now
        durations = []
        for player in self.video_grid.media_players:
            duration = player.duration()
            durations.append(duration)
            print(f"Duration for player: {duration}ms")  # Debug output 
            
        # Calculate max duration for proportional scaling
        self.max_duration = max(durations) if durations else 0
                
        if self.max_duration == 0:
            # Connect to duration changed signals and retry when available
            for player in self.video_grid.media_players:
                player.durationChanged.connect(self._on_duration_available)
            return
            
        # Create timeline for each video
        for i, (player, duration) in enumerate(zip(self.video_grid.media_players, durations)):
            if duration > 0:  # Only create timeline if duration is valid
                timeline_widget = self.create_individual_timeline(player, duration, i)
                self.timeline_layout.addWidget(timeline_widget)
                self.timeline_widgets.append(timeline_widget)
                
    def _on_duration_available(self, duration):
        """Called when a media player's duration becomes available"""
        if duration > 0:
            # Disconnect all duration changed signals to avoid multiple calls
            for player in self.video_grid.media_players:
                try:
                    player.durationChanged.disconnect(self._on_duration_available)
                except:
                    pass
            # Now refresh timelines
            self.refresh_timelines()
            
    def create_individual_timeline(self, media_player, duration, index):
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Video label
        video_name = f"Video {index + 1}"
        name_label = QLabel(video_name)
        name_label.setFixedWidth(80)
        name_label.setStyleSheet("font-size: 10px; font-weight: bold;")
        layout.addWidget(name_label)
        
        # Timeline slider - width proportional to duration
        timeline_slider = QSlider(Qt.Orientation.Horizontal)
        timeline_slider.setMinimumHeight(20)
        
        # Calculate proportional width (minimum 100px, max based on duration ratio)
        if self.max_duration > 0:
            width_ratio = duration / self.max_duration
            min_width = max(100, int(300 * width_ratio))
            timeline_slider.setMinimumWidth(min_width)
        
        timeline_slider.setRange(0, duration)
        timeline_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 6px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 12px;
                margin: -2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d4d4d4, stop:1 #afafaf);
            }
        """)
        
        # Connect slider to specific media player
        timeline_slider.sliderMoved.connect(lambda pos, player=media_player: self.on_individual_slider_moved(player, pos))
        
        layout.addWidget(timeline_slider)
        
        # Duration label
        duration_label = QLabel(self.format_time(duration))
        duration_label.setFixedWidth(50)
        duration_label.setStyleSheet("font-size: 9px; color: #666;")
        layout.addWidget(duration_label)
        
        container.setLayout(layout)
        
        # Store references for updates
        container.slider = timeline_slider
        container.media_player = media_player
        container.duration_label = duration_label
        
        # Connect position updates with proper cleanup
        def update_slider_position(pos):
            if timeline_slider and not timeline_slider.isHidden():
                timeline_slider.setValue(pos)
        
        media_player.positionChanged.connect(update_slider_position)
        container.position_connection = update_slider_position
        
        return container
        
    def on_individual_slider_moved(self, media_player, position):
        # When individual timeline is moved, seek that specific video
        media_player.setPosition(position)
        
        # Also seek all other videos to the proportional position if they're shorter
        if self.video_grid:
            current_duration = media_player.duration()
            if current_duration > 0:
                time_ratio = position / current_duration
                
                # Seek other videos to the same time point if they have that time
                for other_player in self.video_grid.media_players:
                    if other_player != media_player:
                        other_duration = other_player.duration()
                        if other_duration > 0:
                            target_position = min(position, other_duration - 1)
                            other_player.setPosition(target_position)
                            
    def update_position(self, position: int):
        # This gets called by the primary player - update all timeline positions
        pass  # Individual timelines update themselves via their connected signals
        
    def update_duration(self, duration: int):
        # Refresh timelines when durations change
        self.refresh_timelines()
        
    def format_time(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


class VideoPlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.media_player = QMediaPlayer()
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(300)
        self.media_player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget)
        
        self.setLayout(layout)
        
    def setup_connections(self):
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        
    def load_video(self, video_path: str):
        if os.path.exists(video_path):
            self.media_player.setSource(QUrl.fromLocalFile(video_path))
            
    def get_media_player(self):
        return self.media_player
        
    def media_status_changed(self, status):
        pass  # Handled by controls widget
        
    def position_changed(self, position: int):
        pass  # Handled by controls and timeline widgets
        
    def duration_changed(self, duration: int):
        pass  # Handled by controls and timeline widgets


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = ClipRecorderController()
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        self.setWindowTitle("DPS Clip Tracker")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - vertical stack
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        
        # Top section - Video grid (takes most space)
        self.video_grid = VideoGridWidget()
        self.video_grid.setMinimumHeight(400)
        main_layout.addWidget(self.video_grid, stretch=3)
        
        # Middle section - Media controls
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        controls_frame.setMaximumHeight(60)
        controls_layout = QVBoxLayout()
        
        self.media_controls = MediaControlsWidget()
        self.media_controls.set_video_grid(self.video_grid)
        controls_layout.addWidget(self.media_controls)
        
        controls_frame.setLayout(controls_layout)
        main_layout.addWidget(controls_frame)
        
        # Bottom section - Timeline
        timeline_frame = QFrame()
        timeline_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        timeline_frame.setMaximumHeight(80)
        timeline_layout = QVBoxLayout()
        
        self.timeline_widget = VideoTimelineWidget()
        self.timeline_widget.set_video_grid(self.video_grid)
        timeline_layout.addWidget(self.timeline_widget)
        
        timeline_frame.setLayout(timeline_layout)
        main_layout.addWidget(timeline_frame)
        
        # Bottom panel - Recording controls (compact)
        controls_panel = QFrame()
        controls_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        controls_panel.setMaximumHeight(120)
        controls_layout = QHBoxLayout()
        
        # Recording status
        status_group = QGroupBox("Recording")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        status_layout.addWidget(self.record_button)
        
        status_group.setLayout(status_layout)
        controls_layout.addWidget(status_group)
        
        # Key binding
        binding_group = QGroupBox("Input Binding")
        binding_layout = QVBoxLayout()
        
        self.key_binding_widget = KeyBindingWidget()
        binding_layout.addWidget(self.key_binding_widget)
        
        binding_group.setLayout(binding_layout)
        controls_layout.addWidget(binding_group)
        
        # Video management
        management_group = QGroupBox("Video Management")
        management_layout = QVBoxLayout()
        
        refresh_button = QPushButton("Refresh Videos")
        refresh_button.clicked.connect(self.video_grid.refresh_video_grid)
        management_layout.addWidget(refresh_button)
        
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.video_grid.delete_selected_video)
        management_layout.addWidget(delete_button)
        
        management_group.setLayout(management_layout)
        controls_layout.addWidget(management_group)
        
        controls_panel.setLayout(controls_layout)
        main_layout.addWidget(controls_panel)
        
        central_widget.setLayout(main_layout)
        
    def setup_connections(self):
        self.key_binding_widget.binding_changed.connect(self.on_binding_changed)
        self.video_grid.video_selected.connect(self.on_video_selected)
        
        self.controller.recording_started.connect(self.on_recording_started)
        self.controller.recording_stopped.connect(self.on_recording_stopped)
        self.controller.status_changed.connect(self.on_status_changed)
        
        # Check if FFmpeg installation is needed
        self.check_ffmpeg_installation()
        
    def connect_primary_player_signals(self):
        """Connect the primary media player signals to timeline and controls"""
        primary_player = self.video_grid.get_primary_player()
        if primary_player:
            # Disconnect any existing connections first
            try:
                primary_player.mediaStatusChanged.disconnect()
                primary_player.positionChanged.disconnect()
                primary_player.durationChanged.disconnect()
            except:
                pass
                
            primary_player.mediaStatusChanged.connect(self.media_controls.media_status_changed)
            primary_player.positionChanged.connect(lambda pos: self.media_controls.update_time_display(
                pos, primary_player.duration()))
            primary_player.durationChanged.connect(lambda dur: self.media_controls.update_time_display(
                primary_player.position(), dur))
            # Refresh timelines when videos are loaded
            self.timeline_widget.refresh_timelines()
        
    def on_binding_changed(self, binding: InputBinding):
        self.controller.set_input_binding(binding)
        
    def on_video_selected(self, video_path: str):
        # Connect signals for the primary player after video grid loads
        self.connect_primary_player_signals()
        
    def toggle_recording(self):
        if self.controller.is_recording:
            self.controller.stop_recording()
        else:
            self.controller.start_recording()
            
    def on_recording_started(self):
        self.status_label.setText("Recording...")
        self.status_label.setStyleSheet("color: red; font-size: 12px; font-weight: bold;")
        self.record_button.setText("Stop Recording")
        
    def on_recording_stopped(self, filename: str):
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: green; font-size: 12px; font-weight: bold;")
        self.record_button.setText("Start Recording")
        self.video_grid.refresh_video_grid()
        
        # Connect signals for the primary player after refresh
        self.connect_primary_player_signals()
            
    def on_status_changed(self, status: str):
        self.status_label.setText(status)
        
    def check_ffmpeg_installation(self):
        """Check if FFmpeg installation is needed and prompt user."""
        if not self.controller.is_ready_to_record():
            reply = QMessageBox.question(
                self,
                "FFmpeg Required",
                "FFmpeg is required for video recording but was not found on your system.\n\n"
                "Would you like to download and install FFmpeg automatically?\n\n"
                "This will download approximately 50-100MB depending on your platform.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.install_ffmpeg()
            else:
                self.status_label.setText("FFmpeg installation declined - recording unavailable")
                self.status_label.setStyleSheet("color: red; font-size: 12px; font-weight: bold;")
    
    def install_ffmpeg(self):
        """Install FFmpeg with progress dialog."""
        success = self.controller.install_ffmpeg_with_progress(self)
        
        if success:
            self.status_label.setText("FFmpeg installed successfully - ready to record")
            self.status_label.setStyleSheet("color: green; font-size: 12px; font-weight: bold;")
            
            # Show success message
            QMessageBox.information(
                self,
                "Installation Complete",
                "FFmpeg has been installed successfully!\n\n"
                "You can now set up input bindings and start recording clips."
            )
        else:
            self.status_label.setText("FFmpeg installation failed - recording unavailable")
            self.status_label.setStyleSheet("color: red; font-size: 12px; font-weight: bold;")
            
            # Show error message with manual installation option
            reply = QMessageBox.critical(
                self,
                "Installation Failed",
                "FFmpeg installation failed. You can:\n\n"
                "1. Try the installation again\n"
                "2. Install FFmpeg manually and restart the application\n"
                "3. Continue without recording functionality\n\n"
                "Would you like to try installing again?",
                QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Retry
            )
            
            if reply == QMessageBox.StandardButton.Retry:
                self.install_ffmpeg()
        
    def closeEvent(self, event):
        self.controller.cleanup()
        event.accept()


def create_application() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName("DPS Clip Tracker")
    app.setApplicationVersion("1.0.0")
    return app