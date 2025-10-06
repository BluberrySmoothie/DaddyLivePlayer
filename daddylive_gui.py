# daddylive_gui.py - COMPLETE FIXED VERSION

import sys
import re

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QMessageBox, QSizePolicy, QSpacerItem, QCompleter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize

# Import the logic modules
from data_retriever import DataRetriever
from stream_player import StreamPlayer

class DataWorker(QThread):
    """Worker thread to fetch data without freezing the GUI."""
    channels_ready = pyqtSignal(list)
    events_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            retriever = DataRetriever()
            
            # Fetch Channels
            channels = retriever.extract_all_streams()
            self.channels_ready.emit(channels)

            # Fetch Events
            events = retriever.fetch_and_extract_events()
            self.events_ready.emit(events)

        except (ConnectionError, RuntimeError) as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"An unexpected error occurred: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daddy Live Stream Player")
        self.setGeometry(100, 100, 700, 450)
        
        # State variables
        self.current_stream_player = None
        self.channel_data = []
        self.event_data = []
        
        # Flag to track if stop was user-initiated
        self.user_stopped = False

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Setup Tabs
        self.channels_tab = self.setup_channels_tab()
        self.events_tab = self.setup_events_tab()
        self.about_tab = self.setup_about_tab()
        
        self.tab_widget.addTab(self.channels_tab, "Live Channels")
        self.tab_widget.addTab(self.events_tab, "Events Schedule")
        self.tab_widget.addTab(self.about_tab, "About")

        # Initial data load
        self.load_data()

    def load_data(self):
        """Initial or refresh data load, running in a worker thread."""
        self.data_worker = DataWorker()
        self.data_worker.channels_ready.connect(self.update_channels_list)
        self.data_worker.events_ready.connect(self.update_events_list)
        self.data_worker.error.connect(self.handle_data_error)
        
        # Disable buttons while loading
        self.channels_refresh_btn.setEnabled(False)
        self.events_refresh_btn.setEnabled(False)
        self.channels_play_btn.setEnabled(False)
        self.events_play_btn.setEnabled(False)
        
        self.channels_status_lbl.setText("Status: Downloading channel list...")
        self.events_status_lbl.setText("Status: Downloading events list...")
        
        self.data_worker.start()

    def handle_data_error(self, message):
        """Displays error and closes the app if data retrieval fails."""
        QMessageBox.critical(
            self, 
            "Data Retrieval Error",
            f"Error - Unable to update list. Please retry with a VPN.\n\nDetails: {message}"
        )
        QApplication.instance().quit()

    def update_channels_list(self, channels):
        """Updates the channels ComboBox with retrieved data."""
        self.channel_data = channels
        self.channels_combo.clear()
        
        if channels:
            items = [f"{c['DLChName']} ({c['DLChNo']})" for c in channels]
            self.channels_combo.addItems(items)
            self.channels_play_btn.setEnabled(True)
            self.channels_status_lbl.setText(f"Status: {len(channels)} channels loaded.")
        else:
            self.channels_combo.addItem("No channels found.")
            self.channels_play_btn.setEnabled(False)
            self.channels_status_lbl.setText("Status: No channels found.")
            
        self.channels_refresh_btn.setEnabled(True)

    def update_events_list(self, events):
        """Updates the events ComboBox with retrieved data."""
        self.event_data = events
        self.events_combo.clear()
        
        if events:
            # Filter out entries with 'N/A' or 'NO CHANNEL LISTED' for playback
            self.playable_events = [e for e in events if e.get('Channel_ID', 'N/A') != 'N/A' and e['Channel_Name'] != 'NO CHANNEL LISTED']
            
            # Sort by Category first, then by Time_UTC
            self.playable_events.sort(key=lambda e: (e['Category'], e['Time_UTC']))
            
            # Display format: "Category | Time_Local | Event - Channel_Name (Channel_ID)"
            items = [
                f"{e['Category']} | {e['Time_Local']} | {e['Event']} - {e['Channel_Name']} ({e['Channel_ID']})"
                for e in self.playable_events
            ]
            self.events_combo.addItems(items)
            self.events_play_btn.setEnabled(True)
            self.events_status_lbl.setText(f"Status: {len(events)} events loaded (including non-playable entries).")
        else:
            self.events_combo.addItem("No events found.")
            self.events_play_btn.setEnabled(False)
            self.events_status_lbl.setText("Status: No events found.")
            
        self.events_refresh_btn.setEnabled(True)

    def setup_channels_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.channels_combo = QComboBox()
        self.channels_combo.setMinimumHeight(30)
        self.channels_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.channels_combo.setEditable(True)
        self.channels_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.channels_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.channels_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        layout.addWidget(QLabel("Select Live Channel (type to filter):"))
        layout.addWidget(self.channels_combo)
        
        button_layout = QHBoxLayout()
        self.channels_refresh_btn = QPushButton("Refresh list")
        self.channels_refresh_btn.clicked.connect(self.load_data)
        
        self.channels_play_btn = QPushButton("▶️ Play Channel")
        self.channels_play_btn.setMinimumSize(QSize(100, 40))
        self.channels_play_btn.clicked.connect(self.play_channels_stream)
        
        button_layout.addWidget(self.channels_refresh_btn)
        button_layout.addWidget(self.channels_play_btn)
        layout.addLayout(button_layout)

        self.channels_status_lbl = QLabel("Status: Awaiting list download...")
        layout.addWidget(self.channels_status_lbl)
        
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        return tab

    def setup_events_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.events_combo = QComboBox()
        self.events_combo.setMinimumHeight(30)
        self.events_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.events_combo.setEditable(True)
        self.events_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.events_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.events_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        layout.addWidget(QLabel("Select Scheduled Event (type to filter):"))
        layout.addWidget(self.events_combo)
        
        button_layout = QHBoxLayout()
        self.events_refresh_btn = QPushButton("Refresh list")
        self.events_refresh_btn.clicked.connect(self.load_data)
        
        self.events_play_btn = QPushButton("▶️ Play Event")
        self.events_play_btn.setMinimumSize(QSize(100, 40))
        self.events_play_btn.clicked.connect(self.play_events_stream)
        
        button_layout.addWidget(self.events_refresh_btn)
        button_layout.addWidget(self.events_play_btn)
        layout.addLayout(button_layout)

        self.events_status_lbl = QLabel("Status: Awaiting list download...")
        layout.addWidget(self.events_status_lbl)
        
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        return tab

    def setup_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        about_text = QLabel(
            "<h1>Daddy Live Player V1.0</h1>"
            "<p>A desktop client for accessing Daddy Live streaming resources. "
            "This application provides an intuitive interface for browsing live channels "
            "and scheduled sporting events.</p>"
            
            "<h2>System Requirements</h2>"
            "<p><b>Required:</b> FFplay (part of FFmpeg) must be installed and available in your system PATH.</p>"
            
            "<h2>Features</h2>"
            "<ul>"
            "<li>Browse and play live sports channels</li>"
            "<li>View scheduled events by category and time</li>"
            "<li>Search/filter channels and events</li>"
            "<li>Integrated stream playback with session management</li>"
            "</ul>"
            
            "<h2>Developer</h2>"
            "<p>Developed by Bluberry Smoothie<br>"
            "<a href='https://github.com/BluberrySmoothie'>github.com/BluberrySmoothie</a></p>"
            
            "<h2>Technologies</h2>"
            "<p>Built with PyQt6, Selenium, and FFmpeg</p>"
        )
        
        about_text.setOpenExternalLinks(True)
        about_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(about_text)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        return tab

    def play_channels_stream(self):
        """Starts playback for the selected channel."""
        selected_index = self.channels_combo.currentIndex()
        if selected_index < 0 or not self.channel_data:
             QMessageBox.warning(self, "Playback Error", "Please select a channel first, or refresh the list.")
             return
             
        try:
            channel_id = self.channel_data[selected_index]['DLChNo']
            channel_name = self.channel_data[selected_index]['DLChName']
            self.start_playback(channel_id, channel_name)
        except Exception as e:
            QMessageBox.critical(self, "Playback Error", f"An error occurred during channel ID retrieval: {e}")

    def play_events_stream(self):
        """Starts playback for the selected event's channel."""
        selected_text = self.events_combo.currentText()
        if not selected_text or "No events found" in selected_text:
             QMessageBox.warning(self, "Playback Error", "Please select a valid event first.")
             return
             
        try:
            # Extract Channel_ID which is inside the last parentheses
            match = re.search(r'\((\d+)\)$', selected_text)
            if not match:
                QMessageBox.warning(self, "Playback Error", "Selected event has no discernible Channel ID. Select a different event.")
                return

            channel_id = int(match.group(1))
            # Extract event name - it's after the second pipe and before the dash
            parts = selected_text.split(' | ')
            if len(parts) >= 3:
                event_name = parts[2].split(' - ')[0].strip()
            else:
                event_name = "Selected Event"

            self.start_playback(channel_id, f"Event: {event_name}")

        except Exception as e:
            QMessageBox.critical(self, "Playback Error", f"Failed to extract Channel ID from event: {e}")

    def start_playback(self, channel_id, stream_name):
        """Manages starting a new StreamPlayer thread."""
        if self.current_stream_player and self.current_stream_player.is_alive():
            reply = QMessageBox.question(
                self, 
                "Stream Already Playing", 
                "A stream is currently playing. Do you want to stop the current stream and start the new one?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.user_stopped = True
                self.current_stream_player.stop()
                self.current_stream_player.join(timeout=1)
            else:
                return

        try:
            self.user_stopped = False
            self.current_stream_player = StreamPlayer(
                channel_id=channel_id,
                start_callback=lambda: self.playback_started(stream_name),
                stop_callback=self.playback_stopped,
                error_callback=self.playback_error
            )
            self.current_stream_player.start()
            self.update_ui_for_playback_state(True, stream_name)
        except Exception as e:
            self.playback_error(f"Failed to launch playback thread: {e}")

    def playback_started(self, stream_name):
        """Callback when the StreamPlayer successfully launches ffplay."""
        pass

    def playback_stopped(self):
        """Callback when the StreamPlayer thread terminates normally."""
        self.current_stream_player = None
        self.update_ui_for_playback_state(False)
        
        # Only show message if user didn't manually stop it
        if not self.user_stopped:
            # Use QTimer to show message in the main thread
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.show_stream_ended_message)
    
    def show_stream_ended_message(self):
        """Show the stream ended message - called from main thread."""
        QMessageBox.information(
            self,
            "Stream Ended",
            "Stream has been terminated.\n\n"
            "Possible reasons:\n"
            "• You closed the ffplay window\n"
            "• Stream went offline/unavailable\n"
            "• Network connection issue"
        )

    def playback_error(self, message):
        """Callback when the StreamPlayer thread encounters an error."""
        QMessageBox.critical(
            self, 
            "Playback Failed", 
            f"Failed to play stream. Ensure FFplay is installed and in your PATH, and all required Python packages are installed.\n\nDetails: {message}"
        )
        self.current_stream_player = None
        self.update_ui_for_playback_state(False)

    def update_ui_for_playback_state(self, is_playing, stream_name=None):
        """Updates UI elements based on the playback state."""
        try: 
            self.channels_play_btn.clicked.disconnect()
        except TypeError: 
            pass
        try: 
            self.events_play_btn.clicked.disconnect()
        except TypeError: 
            pass
        
        if is_playing:
            self.channels_play_btn.setText("🔴 STOP Stream")
            self.events_play_btn.setText("🔴 STOP Stream")
            self.channels_play_btn.clicked.connect(self.stop_current_stream)
            self.events_play_btn.clicked.connect(self.stop_current_stream)
            self.statusBar().showMessage(f"Streaming: {stream_name} | Close ffplay window or click STOP")
        else:
            self.channels_play_btn.setText("▶️ Play Channel")
            self.events_play_btn.setText("▶️ Play Event")
            self.channels_play_btn.clicked.connect(self.play_channels_stream)
            self.events_play_btn.clicked.connect(self.play_events_stream)
            self.statusBar().showMessage("Ready.")

    def stop_current_stream(self):
        """Handler for the STOP button."""
        if self.current_stream_player and self.current_stream_player.is_alive():
            self.user_stopped = True
            self.current_stream_player.stop() 
            self.current_stream_player.join(timeout=3)
        self.playback_stopped()

    def closeEvent(self, event):
        """Ensures the stream is stopped before closing the application."""
        if self.current_stream_player and self.current_stream_player.is_alive():
            self.user_stopped = True
            self.current_stream_player.stop()
            self.current_stream_player.join(timeout=5)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())