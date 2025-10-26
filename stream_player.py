# stream_player.py (FIXED Streamlink Version)

import subprocess
import threading
import sys
import os
import time

class StreamPlayer(threading.Thread):
    """
    Manages stream playback in a separate thread by calling PlayTest-streamlink.py
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
        """Stops the playback process (Streamlink and associated player)."""
        self._stop_event.set()
        
        if self.process and self.process.poll() is None:
            try:
                # Try graceful termination first
                self.process.terminate()
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                try:
                    self.process.kill()
                    self.process.wait(timeout=2)
                except Exception:
                    pass
            except Exception:
                pass

    def run(self):
        """The main execution loop for the thread."""
        error_occurred = False
        error_message = ""
        
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            player_script = os.path.join(script_dir, 'PlayTest-streamlink.py')
            
            # Verify script exists
            if not os.path.exists(player_script):
                error_occurred = True
                error_message = f"Script not found: {player_script}"
                return

            cmd = [sys.executable, player_script, str(self.channel_id), '--silent']

            # Launch the process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                universal_newlines=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )

            # Give it a moment to start
            time.sleep(2)
            
            # Check if it failed immediately
            if self.process.poll() is not None:
                stdout_out, stderr_out = self.process.communicate()
                error_msg = stderr_out.strip() if stderr_out else stdout_out.strip()
                
                error_occurred = True
                error_message = (
                    f"Streamlink failed to start (exit code {self.process.returncode})\n\n"
                    f"Make sure Streamlink is installed:\n"
                    f"  pip install streamlink\n\n"
                    f"Details: {error_msg[:300] if error_msg else 'No output'}"
                )
                return
            
            # Notify that playback started successfully
            if self.start_callback:
                self.start_callback()
            
            # Monitor the process
            while not self._stop_event.is_set():
                returncode = self.process.poll()
                if returncode is not None:
                    # Process ended
                    break
                time.sleep(0.5)
            
        except FileNotFoundError:
            error_occurred = True
            error_message = "Python interpreter not found. This shouldn't happen!"
        except Exception as e:
            error_occurred = True
            error_message = f"Playback error: {e}"
        finally:
            self.cleanup()
            
            # Call callbacks after cleanup
            if error_occurred and self.error_callback:
                self.error_callback(error_message)
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