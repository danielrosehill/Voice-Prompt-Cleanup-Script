#!/usr/bin/env python3
"""
Voice Prompt Cleanup GUI
A PyQt6-based GUI for batch processing audio files for STT workflows.
"""

import sys
import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTextEdit, QGroupBox, QCheckBox, QMessageBox, QStatusBar,
    QListWidget, QListWidgetItem, QAbstractItemView, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon


@dataclass
class AppSettings:
    """Persistent application settings."""
    output_folder: str = ""
    use_custom_output: bool = False
    last_input_folder: str = ""
    window_geometry: bytes = b""


class SettingsManager:
    """Handles loading and saving application settings."""

    CONFIG_DIR = Path.home() / ".config" / "voice-prompt-cleanup"
    CONFIG_FILE = CONFIG_DIR / "settings.json"

    @classmethod
    def load(cls) -> AppSettings:
        """Load settings from disk."""
        settings = AppSettings()
        if cls.CONFIG_FILE.exists():
            try:
                with open(cls.CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    settings.output_folder = data.get("output_folder", "")
                    settings.use_custom_output = data.get("use_custom_output", False)
                    settings.last_input_folder = data.get("last_input_folder", "")
            except (json.JSONDecodeError, IOError):
                pass
        return settings

    @classmethod
    def save(cls, settings: AppSettings) -> None:
        """Save settings to disk."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "output_folder": settings.output_folder,
            "use_custom_output": settings.use_custom_output,
            "last_input_folder": settings.last_input_folder,
        }
        with open(cls.CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)


class ProcessingWorker(QThread):
    """Worker thread for processing audio files."""

    progress = pyqtSignal(int, int, str)  # current, total, message
    file_complete = pyqtSignal(str, bool, str)  # filename, success, message
    all_complete = pyqtSignal(int, int)  # successful, failed
    log_message = pyqtSignal(str)

    def __init__(self, files: List[Path], output_folder: Optional[Path], script_path: Path):
        super().__init__()
        self.files = files
        self.output_folder = output_folder
        self.script_path = script_path
        self._cancelled = False

    def cancel(self):
        """Request cancellation of processing."""
        self._cancelled = True

    def run(self):
        """Process all files."""
        successful = 0
        failed = 0
        total = len(self.files)

        for i, input_file in enumerate(self.files):
            if self._cancelled:
                self.log_message.emit("\n⚠️  Processing cancelled by user")
                break

            self.progress.emit(i, total, f"Processing: {input_file.name}")

            # Determine output path
            output_name = f"{input_file.stem}_processed.mp3"
            if self.output_folder:
                output_path = self.output_folder / output_name
            else:
                output_path = input_file.parent / output_name

            self.log_message.emit(f"\n{'='*60}")
            self.log_message.emit(f"Processing: {input_file.name}")
            self.log_message.emit(f"Output: {output_path}")
            self.log_message.emit(f"{'='*60}\n")

            try:
                result = subprocess.run(
                    [str(self.script_path), str(input_file), str(output_path)],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout per file
                )

                if result.returncode == 0:
                    successful += 1
                    self.file_complete.emit(input_file.name, True, "Success")
                    self.log_message.emit(result.stdout)
                else:
                    failed += 1
                    error_msg = result.stderr or "Unknown error"
                    self.file_complete.emit(input_file.name, False, error_msg)
                    self.log_message.emit(f"❌ Error: {error_msg}")

            except subprocess.TimeoutExpired:
                failed += 1
                self.file_complete.emit(input_file.name, False, "Timeout (>10 min)")
                self.log_message.emit("❌ Error: Processing timeout exceeded")
            except Exception as e:
                failed += 1
                self.file_complete.emit(input_file.name, False, str(e))
                self.log_message.emit(f"❌ Error: {e}")

        self.progress.emit(total, total, "Complete")
        self.all_complete.emit(successful, failed)


class FileDropListWidget(QListWidget):
    """List widget that accepts file drops."""

    files_dropped = pyqtSignal(list)

    SUPPORTED_EXTENSIONS = {
        '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma',
        '.opus', '.webm', '.mp4', '.mkv', '.avi', '.mov'
    }

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                files.append(path)
            elif path.is_dir():
                for ext in self.SUPPORTED_EXTENSIONS:
                    files.extend(path.glob(f"*{ext}"))
                    files.extend(path.glob(f"*{ext.upper()}"))

        if files:
            self.files_dropped.emit(files)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.settings = SettingsManager.load()
        self.files_to_process: List[Path] = []
        self.worker: Optional[ProcessingWorker] = None

        # Find the processing script
        self.script_path = self._find_script()

        self.init_ui()
        self.check_dependencies()

    def _find_script(self) -> Path:
        """Find the process_audio.sh script."""
        # Check multiple locations
        locations = [
            Path(__file__).parent / "process_audio.sh",
            Path("/usr/share/voice-prompt-cleanup/process_audio.sh"),
            Path("/usr/local/share/voice-prompt-cleanup/process_audio.sh"),
            Path.home() / ".local/share/voice-prompt-cleanup/process_audio.sh",
        ]

        for loc in locations:
            if loc.exists() and loc.is_file():
                return loc

        # Default to same directory as script
        return Path(__file__).parent / "process_audio.sh"

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Voice Prompt Cleanup")
        self.setMinimumSize(800, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Input section
        input_group = QGroupBox("Input Files")
        input_layout = QVBoxLayout(input_group)

        # File list with drag-drop
        self.file_list = FileDropListWidget()
        self.file_list.files_dropped.connect(self.add_files)
        input_layout.addWidget(QLabel("Drag and drop files/folders here, or use the buttons below:"))
        input_layout.addWidget(self.file_list)

        # Input buttons
        input_btn_layout = QHBoxLayout()

        self.add_files_btn = QPushButton("Add Files...")
        self.add_files_btn.clicked.connect(self.browse_files)
        input_btn_layout.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("Add Folder...")
        self.add_folder_btn.clicked.connect(self.browse_folder)
        input_btn_layout.addWidget(self.add_folder_btn)

        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.clicked.connect(self.clear_files)
        input_btn_layout.addWidget(self.clear_btn)

        self.remove_selected_btn = QPushButton("Remove Selected")
        self.remove_selected_btn.clicked.connect(self.remove_selected)
        input_btn_layout.addWidget(self.remove_selected_btn)

        input_layout.addLayout(input_btn_layout)
        layout.addWidget(input_group)

        # Output section
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout(output_group)

        self.use_custom_output = QCheckBox("Use custom output folder (otherwise saves next to original)")
        self.use_custom_output.setChecked(self.settings.use_custom_output)
        self.use_custom_output.stateChanged.connect(self.toggle_output_folder)
        output_layout.addWidget(self.use_custom_output)

        output_folder_layout = QHBoxLayout()
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setText(self.settings.output_folder)
        self.output_folder_edit.setPlaceholderText("Select output folder...")
        self.output_folder_edit.setEnabled(self.settings.use_custom_output)
        output_folder_layout.addWidget(self.output_folder_edit)

        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.setEnabled(self.settings.use_custom_output)
        self.browse_output_btn.clicked.connect(self.browse_output_folder)
        output_folder_layout.addWidget(self.browse_output_btn)

        output_layout.addLayout(output_folder_layout)

        output_layout.addWidget(QLabel(
            "Note: Output files are named <original>_processed.mp3 to avoid overwriting originals."
        ))

        layout.addWidget(output_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_label = QLabel("Ready")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_group)

        # Log output
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout(log_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)
        log_layout.addWidget(self.log_output)

        layout.addWidget(log_group)

        # Action buttons
        action_layout = QHBoxLayout()

        self.process_btn = QPushButton("Process Files")
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setEnabled(False)
        self.process_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 10px; }")
        action_layout.addWidget(self.process_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        action_layout.addWidget(self.cancel_btn)

        layout.addLayout(action_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Add files to begin")

    def check_dependencies(self):
        """Check if required dependencies are available."""
        # Check ffmpeg
        if not shutil.which("ffmpeg"):
            QMessageBox.warning(
                self,
                "Missing Dependency",
                "ffmpeg is not installed.\n\n"
                "Install with: sudo apt install ffmpeg"
            )

        # Check script exists
        if not self.script_path.exists():
            QMessageBox.critical(
                self,
                "Script Not Found",
                f"Cannot find process_audio.sh at:\n{self.script_path}\n\n"
                "Please ensure the script is installed correctly."
            )

    def toggle_output_folder(self, state):
        """Toggle the output folder input enabled state."""
        enabled = state == Qt.CheckState.Checked.value
        self.output_folder_edit.setEnabled(enabled)
        self.browse_output_btn.setEnabled(enabled)
        self.settings.use_custom_output = enabled
        SettingsManager.save(self.settings)

    def browse_output_folder(self):
        """Browse for output folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.settings.output_folder or str(Path.home())
        )
        if folder:
            self.output_folder_edit.setText(folder)
            self.settings.output_folder = folder
            SettingsManager.save(self.settings)

    def browse_files(self):
        """Browse for input files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            self.settings.last_input_folder or str(Path.home()),
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma *.opus);;All Files (*)"
        )
        if files:
            self.settings.last_input_folder = str(Path(files[0]).parent)
            SettingsManager.save(self.settings)
            self.add_files([Path(f) for f in files])

    def browse_folder(self):
        """Browse for folder containing audio files."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Audio Files",
            self.settings.last_input_folder or str(Path.home())
        )
        if folder:
            folder_path = Path(folder)
            self.settings.last_input_folder = folder
            SettingsManager.save(self.settings)

            files = []
            for ext in FileDropListWidget.SUPPORTED_EXTENSIONS:
                files.extend(folder_path.glob(f"*{ext}"))
                files.extend(folder_path.glob(f"*{ext.upper()}"))

            if files:
                self.add_files(files)
            else:
                QMessageBox.information(
                    self,
                    "No Audio Files",
                    "No supported audio files found in the selected folder."
                )

    def add_files(self, files: List[Path]):
        """Add files to the processing list."""
        for file_path in files:
            # Avoid duplicates
            if file_path not in self.files_to_process:
                self.files_to_process.append(file_path)
                item = QListWidgetItem(str(file_path))
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                self.file_list.addItem(item)

        self.update_ui_state()

    def clear_files(self):
        """Clear all files from the list."""
        self.file_list.clear()
        self.files_to_process.clear()
        self.update_ui_state()

    def remove_selected(self):
        """Remove selected files from the list."""
        for item in self.file_list.selectedItems():
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path in self.files_to_process:
                self.files_to_process.remove(file_path)
            self.file_list.takeItem(self.file_list.row(item))
        self.update_ui_state()

    def update_ui_state(self):
        """Update UI elements based on current state."""
        has_files = len(self.files_to_process) > 0
        self.process_btn.setEnabled(has_files and self.worker is None)
        self.status_bar.showMessage(
            f"{len(self.files_to_process)} file(s) ready for processing"
            if has_files else "Ready - Add files to begin"
        )

    def start_processing(self):
        """Start processing files."""
        if not self.files_to_process:
            return

        # Validate output folder if custom is enabled
        output_folder = None
        if self.use_custom_output.isChecked():
            output_folder = Path(self.output_folder_edit.text())
            if not output_folder.exists():
                try:
                    output_folder.mkdir(parents=True)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Cannot create output folder:\n{e}"
                    )
                    return

        # Validate script exists
        if not self.script_path.exists():
            QMessageBox.critical(
                self,
                "Error",
                f"Processing script not found:\n{self.script_path}"
            )
            return

        # Clear log and reset progress
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.files_to_process))

        # Disable UI during processing
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.add_files_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.remove_selected_btn.setEnabled(False)

        # Start worker thread
        self.worker = ProcessingWorker(
            self.files_to_process.copy(),
            output_folder,
            self.script_path
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.file_complete.connect(self.on_file_complete)
        self.worker.all_complete.connect(self.on_all_complete)
        self.worker.log_message.connect(self.on_log_message)
        self.worker.start()

    def cancel_processing(self):
        """Cancel the current processing."""
        if self.worker:
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.status_bar.showMessage("Cancelling...")

    def on_progress(self, current: int, total: int, message: str):
        """Handle progress updates."""
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
        self.status_bar.showMessage(f"Processing {current + 1}/{total}: {message}")

    def on_file_complete(self, filename: str, success: bool, message: str):
        """Handle file completion."""
        status = "✓" if success else "✗"
        self.log_output.append(f"\n{status} {filename}: {message}")

    def on_log_message(self, message: str):
        """Handle log messages."""
        self.log_output.append(message)
        # Auto-scroll to bottom
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def on_all_complete(self, successful: int, failed: int):
        """Handle completion of all processing."""
        self.worker = None

        # Re-enable UI
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.remove_selected_btn.setEnabled(True)

        # Show summary
        total = successful + failed
        self.progress_label.setText(f"Complete: {successful}/{total} successful")
        self.status_bar.showMessage(
            f"Processing complete: {successful} successful, {failed} failed"
        )

        self.log_output.append(f"\n{'='*60}")
        self.log_output.append(f"Processing complete!")
        self.log_output.append(f"  Successful: {successful}")
        self.log_output.append(f"  Failed: {failed}")
        self.log_output.append(f"{'='*60}")

        if failed == 0 and successful > 0:
            QMessageBox.information(
                self,
                "Complete",
                f"Successfully processed {successful} file(s)!"
            )
        elif failed > 0:
            QMessageBox.warning(
                self,
                "Complete with Errors",
                f"Processed {successful} file(s) successfully.\n"
                f"{failed} file(s) failed - check the log for details."
            )

    def closeEvent(self, event):
        """Handle window close."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Processing in Progress",
                "Processing is still running. Cancel and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.cancel()
                self.worker.wait(5000)  # Wait up to 5 seconds
            else:
                event.ignore()
                return

        # Save settings
        SettingsManager.save(self.settings)
        event.accept()


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Prompt Cleanup")
    app.setOrganizationName("VoicePromptCleanup")
    app.setOrganizationDomain("github.com/danielrosehill")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
