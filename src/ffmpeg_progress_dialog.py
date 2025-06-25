from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from .ffmpeg_installer import FFmpegInstaller


class FFmpegInstallThread(QThread):
    """Thread for installing FFmpeg without blocking the GUI."""
    
    progress_updated = pyqtSignal(str, int)  # message, percentage
    installation_completed = pyqtSignal(str)  # ffmpeg_path
    installation_failed = pyqtSignal(str)  # error_message
    
    def run(self):
        """Run the FFmpeg installation in a separate thread."""
        try:
            installer = FFmpegInstaller(progress_callback=self._progress_callback)
            ffmpeg_path = installer.ensure_ffmpeg_available()
            self.installation_completed.emit(ffmpeg_path)
        except Exception as e:
            self.installation_failed.emit(str(e))
    
    def _progress_callback(self, message: str, percentage: int):
        """Callback to report progress to the main thread."""
        self.progress_updated.emit(message, percentage)


class FFmpegProgressDialog(QDialog):
    """Progress dialog for FFmpeg installation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ffmpeg_path = None
        self.install_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the progress dialog UI."""
        self.setWindowTitle("Installing FFmpeg")
        self.setFixedSize(400, 150)
        self.setModal(True)
        
        # Make dialog stay on top and prevent closing
        self.setWindowFlags(Qt.WindowType.Dialog | 
                           Qt.WindowType.WindowTitleHint |
                           Qt.WindowType.CustomizeWindowHint)
        
        layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Preparing FFmpeg installation...")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Details label for file sizes, etc.
        self.details_label = QLabel("")
        self.details_label.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.details_label)
        
        # Cancel button (initially hidden, shown if installation takes too long)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_installation)
        self.cancel_button.hide()
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
    
    def start_installation(self):
        """Start the FFmpeg installation process."""
        self.install_thread = FFmpegInstallThread()
        
        # Connect signals
        self.install_thread.progress_updated.connect(self.update_progress)
        self.install_thread.installation_completed.connect(self.installation_completed)
        self.install_thread.installation_failed.connect(self.installation_failed)
        
        # Start the installation
        self.install_thread.start()
        
        # Show cancel button after 10 seconds
        from PyQt6.QtCore import QTimer
        self.cancel_timer = QTimer()
        self.cancel_timer.setSingleShot(True)
        self.cancel_timer.timeout.connect(lambda: self.cancel_button.show())
        self.cancel_timer.start(10000)  # 10 seconds
    
    def update_progress(self, message: str, percentage: int):
        """Update the progress display."""
        self.status_label.setText(message)
        self.progress_bar.setValue(percentage)
        
        # Extract details from message for better UX
        if "MB" in message:
            self.details_label.setText(message)
        elif percentage == 100:
            self.details_label.setText("Installation completed successfully!")
    
    def installation_completed(self, ffmpeg_path: str):
        """Handle successful installation completion."""
        self.ffmpeg_path = ffmpeg_path
        self.status_label.setText("FFmpeg installation completed!")
        self.progress_bar.setValue(100)
        self.details_label.setText(f"FFmpeg installed at: {ffmpeg_path}")
        
        # Auto-close after 1 second
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, self.accept)
    
    def installation_failed(self, error_message: str):
        """Handle installation failure."""
        self.status_label.setText("FFmpeg installation failed!")
        self.details_label.setText(f"Error: {error_message}")
        self.progress_bar.setValue(0)
        
        # Show retry/cancel options
        self.cancel_button.setText("Close")
        self.cancel_button.show()
    
    def cancel_installation(self):
        """Cancel the installation process."""
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.terminate()
            self.install_thread.wait(3000)  # Wait up to 3 seconds
        
        self.reject()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Prevent closing during installation unless explicitly cancelled
        if self.install_thread and self.install_thread.isRunning():
            event.ignore()
        else:
            event.accept()
    
    @staticmethod
    def install_ffmpeg_with_progress(parent=None):
        """
        Convenience method to show progress dialog and install FFmpeg.
        
        Returns:
            str or None: Path to FFmpeg executable, or None if cancelled/failed
        """
        dialog = FFmpegProgressDialog(parent)
        dialog.start_installation()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.ffmpeg_path
        return None