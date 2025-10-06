# stream_player.py - Fixed buffering issue

import subprocess
import threading
import sys
import os
import time

class StreamPlayer(threading.Thread):
    """
    Manages the stream playback in a separate thread by calling PlayTest-headless.py
    """

    def __init__(self, channel_id, start_callback=None, stop_callback=None, error_callback=None):
        super().__init__()
        self.daemon = False
        
        try:
            self.channel_id = int(channel_id)
        except ValueError:
            raise ValueError("Channel ID must be a valid integer.")
            
        self.process = None
        self._stop_event = threading.Event()
        
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.error_callback = error_callback

    def stop(self):
        """Stops the playback process."""
        self._stop_event.set()
        
        # Terminate the subprocess
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

    def run(self):
        """The main execution loop for the thread."""
        
        try:
            # Find the path to PlayTest-headless.py (should be in same directory)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            playtest_script = os.path.join(script_dir, "PlayTest-headless.py")
            
            # Check if the script exists
            if not os.path.exists(playtest_script):
                if self.error_callback:
                    self.error_callback(f"PlayTest-headless.py not found at: {playtest_script}")
                return
            
            # Build the command to run PlayTest-headless.py with the channel ID
            cmd = [sys.executable, playtest_script, str(self.channel_id)]
            
            # Start the subprocess with all output suppressed
            # Use DEVNULL for stdin, stdout, and stderr
            # On Windows, use CREATE_NO_WINDOW flag to hide console window
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                startupinfo=startupinfo
            )
            
            # Give it a moment to start
            time.sleep(0.5)
            
            # Check if it failed immediately
            initial_check = self.process.poll()
            if initial_check is not None and initial_check != 0:
                if self.error_callback:
                    self.error_callback(
                        f"Failed to start stream for channel {self.channel_id}.\n\n"
                        f"The stream may be unavailable or offline.\n"
                        f"Try a different channel."
                    )
                return
            
            # Signal successful start
            if self.start_callback:
                self.start_callback()
            
            # Monitor the process - just wait for it to complete
            while not self._stop_event.is_set():
                returncode = self.process.poll()
                if returncode is not None:
                    # Process ended naturally (user closed ffplay window)
                    break
                time.sleep(0.5)
            
        except Exception as e:
            if self.error_callback:
                self.error_callback(f"Playback error: {e}")
        finally:
            self.cleanup()
            if self.stop_callback:
                self.stop_callback()

    def cleanup(self):
        """Centralized cleanup method."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass