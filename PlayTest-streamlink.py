# PlayTest-streamlink.py (WITH SESSION COOKIE EXTRACTION + MULTI-DOMAIN TRIES)

import subprocess
import sys
import os
import platform
import shutil
import time
import urllib.request
from urllib.error import URLError, HTTPError

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
# If you want to try different name tokens (used both in hostname and path),
# add them here in preferred order.
DOMAIN_CANDIDATES = ["nfs", "dokko1", "zeko", "ddy6", "wind"]

# If you want to force a specific stream server, set STREAM_SERVER_DOMAIN (full scheme+host).
# If None, the script will try DOMAIN_CANDIDATES first and then fall back to this value.
STREAM_SERVER_DOMAIN = None  # e.g. "https://dokko1new.newkso.ru" or None to rely on candidates
STREAM_REFERER = "https://truncatedactivitiplay.xyz/"
STREAM_ORIGIN = "https://truncatedactivitiplay.xyz"
BASE_WEBPAGE = "https://dlhd.dad"
# ---------------------

def find_player():
    """Find mpv or fallback to VLC if mpv is not available."""
    if shutil.which("mpv"):
        return "mpv"
    common_mpv_paths = [
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\Program Files (x86)\mpv\mpv.exe",
        os.path.expanduser(r"~\AppData\Local\mpv\mpv.exe"),
    ]
    for path in common_mpv_paths:
        if os.path.exists(path):
            return path
    if shutil.which("vlc"):
        print("Warning: mpv not found, falling back to VLC")
        return "vlc"
    common_vlc_paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ]
    for path in common_vlc_paths:
        if os.path.exists(path):
            print(f"Warning: mpv not found, falling back to VLC at {path}")
            return path
    return None

def get_session_cookies(channel_id):
    """Use Selenium to visit the webpage and extract session cookies."""
    print(f"Opening webpage to establish session for channel {channel_id}...")
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = f"{BASE_WEBPAGE}/watch.php?id={channel_id}"
        print(f"Visiting: {url}")
        driver.get(url)

        # small wait to let cookies be set
        time.sleep(3)

        cookies = driver.get_cookies()
        driver.quit()

        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

        print(f"Extracted {len(cookies)} cookies")
        return cookie_string

    except Exception as e:
        print(f"Warning: Could not extract cookies: {e}")
        print("Continuing without cookies...")
        return None

def probe_url(url, headers=None, timeout=5):
    """
    Do a quick HEAD (or GET fallback) to check if the URL is reachable.
    Returns True if HTTP status is 200 (or 206 for partial content), False otherwise.
    """
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, method="HEAD", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            # Accept 200 (OK) and 206 (partial content for HLS)
            if code in (200, 206):
                return True
            else:
                print(f"Probe returned status {code} for {url}")
                return False
    except HTTPError as e:
        print(f"HTTPError probing {url}: {e.code}")
        return False
    except URLError as e:
        print(f"URLError probing {url}: {e.reason}")
        return False
    except Exception as e:
        print(f"Error probing {url}: {e}")
        return False

def build_and_select_stream_url(channel_id):
    """
    Try DOMAIN_CANDIDATES in order and probe each constructed m3u8 URL.
    If none succeed and STREAM_SERVER_DOMAIN is set, try the configured fallback.
    Returns the chosen STREAM_URL (string).
    """
    headers = {
        "Referer": STREAM_REFERER,
        "Origin": STREAM_ORIGIN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    }

    for name in DOMAIN_CANDIDATES:
        # hostname uses the name with 'new' appended as per examples: e.g. dokko1 -> dokko1new.newkso.ru
        host = f"https://{name}new.newkso.ru"
        path_segment = name  # examples show path uses the raw name (without 'new')
        stream_url = f"{host}/{path_segment}/premium{channel_id}/mono.m3u8"
        print(f"Probing {stream_url} ...")
        if probe_url(stream_url, headers=headers, timeout=4):
            print(f"Selected: {stream_url}")
            return stream_url

    # If nothing from candidates worked, try the configured STREAM_SERVER_DOMAIN if provided
    if STREAM_SERVER_DOMAIN:
        # try to detect path portion by using last path segment from example (fallback to 'dokko1')
        # Here we try to mimic the previous hardcoded path; adjust if you want different behavior.
        fallback_name = "dokko1"
        stream_url = f"{STREAM_SERVER_DOMAIN}/{fallback_name}/premium{channel_id}/mono.m3u8"
        print(f"No candidate responded. Probing fallback: {stream_url}")
        if probe_url(stream_url, headers=headers, timeout=4):
            print(f"Selected fallback: {stream_url}")
            return stream_url

    # If nothing responds, return the first candidate URL (for debugging), or construct a "best guess"
    guessed = f"https://{DOMAIN_CANDIDATES[0]}new.newkso.ru/{DOMAIN_CANDIDATES[0]}/premium{channel_id}/mono.m3u8"
    print("No candidate validated. Returning guessed URL for attempt:", guessed)
    return guessed

def start_integrated_stream(channel_id):
    """Starts the stream using Streamlink CLI with session cookies."""
    player = find_player()
    if not player:
        print("\nERROR: No suitable video player found!")
        print("Please install mpv (recommended):")
        print("  winget install mpv.mpv")
        print("\nOr VLC will work as fallback:")
        print("  winget install VideoLAN.VLC")
        return 1

    # Get session cookies by visiting the webpage first
    cookies = get_session_cookies(channel_id)

    # Build/select the STREAM_URL by probing candidate domains
    STREAM_URL = build_and_select_stream_url(channel_id)

    print(f"\nStarting Streamlink for Channel ID: {channel_id}")
    print(f"Player: {player}")
    print(f"Stream URL: {STREAM_URL}")

    # Construct Streamlink command
    streamlink_cmd = [
        "streamlink",
        "--player", player,
        "--http-header", f"Referer={STREAM_REFERER}",
        "--http-header", f"Origin={STREAM_ORIGIN}",
        "--http-header", "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    ]

    # Add cookies if we got them
    if cookies:
        streamlink_cmd.extend(["--http-cookie", cookies])

    # Add URL and quality
    streamlink_cmd.extend([
        f"hlsvariant://{STREAM_URL}",
        "best"
    ])

    try:
        print("Launching Streamlink...")
        streamlink_process = subprocess.Popen(
            streamlink_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            universal_newlines=True,
            bufsize=1
        )

        for line in streamlink_process.stdout:
            print(line.rstrip())

        returncode = streamlink_process.wait()
        print(f"Streamlink exited with code: {returncode}")

        return returncode

    except FileNotFoundError:
        print("\nERROR: Streamlink not found in PATH")
        print("Install with: pip install streamlink")
        print("Or download from: https://github.com/streamlink/streamlink/releases")
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    channel_id_to_play = 32
    is_silent = False

    # Parse command line arguments
    for arg in sys.argv[1:]:
        if arg == '--silent':
            is_silent = True
        else:
            try:
                channel_id_to_play = int(arg)
            except ValueError:
                print(f"Warning: Invalid channel ID '{arg}'. Using default {channel_id_to_play}.")

    # Redirect output if silent mode
    if is_silent:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    exit_code = start_integrated_stream(channel_id_to_play)
    sys.exit(exit_code)
