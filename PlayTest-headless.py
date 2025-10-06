import subprocess
import shlex
import time
import os
import tempfile
import shutil
import sys

# Import Selenium components
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    
    # Suppress webdriver_manager logs
    import logging
    logging.getLogger('WDM').setLevel(logging.NOTSET)
    os.environ['WDM_LOG'] = '0'
except ImportError:
    print("FATAL ERROR: Selenium or webdriver-manager is not installed.")
    print("Please run: pip install selenium webdriver-manager")
    sys.exit(1)

# --- Configuration ---
# Full, standard headers to be passed to ffplay (using the version without quotes for ffplay compatibility)
FFPLAY_HEADERS = {
    "Origin": "https://jxokplay.xyz",
    "Referer": "https://jxokplay.xyz/",
    "sec-ch-ua": "Google Chrome;v=141, Not?A_Brand;v=8, Chromium;v=141",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
}
# ---------------------

def start_integrated_stream(channel_id):
    """Starts the headless browser, launches ffplay, and manages the session."""
    
    # Build URLs based on channel ID
    STREAM_URL = f"https://nfsnew.newkso.ru/nfs/premium{channel_id}/mono.m3u8"
    STREAM_PAGE_URL = f"https://dlhd.dad/watch.php?id={channel_id}"
    
    # 1. Setup Temporary Directory
    temp_dir = tempfile.mkdtemp()

    driver = None
    ffplay_process = None
    
    try:
        # 2. Configure and Start Headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless=new") 
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")  # Suppress most Chrome logs
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_argument(f"user-data-dir={temp_dir}") 
        chrome_options.add_argument(f"user-agent={FFPLAY_HEADERS['User-Agent']}")
        
        # Suppress Chrome DevTools and error messages
        service = Service(ChromeDriverManager().install(), log_path=os.devnull)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 3. Establish Session Token
        driver.get(STREAM_PAGE_URL)
        time.sleep(3) # Give time for JavaScript to run and token to activate

        # 4. Prepare and Launch ffplay
        header_str = "".join(f"{k}: {v}\r\n" for k, v in FFPLAY_HEADERS.items())
        
        # Build the ffplay command list
        ffplay_cmd = ["ffplay", "-loglevel", "quiet", "-headers", header_str, STREAM_URL]
        
        # Launch ffplay as a non-blocking subprocess with suppressed output
        ffplay_process = subprocess.Popen(
            ffplay_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        
        # 5. Session Management Loop
        while ffplay_process.poll() is None:
            # Check if ffplay is still running (non-blocking)
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    except Exception:
        pass
        
    finally:
        # 6. Cleanup
        # Terminate ffplay if it's still running
        if ffplay_process and ffplay_process.poll() is None:
            ffplay_process.terminate()
            
        # Close the Selenium browser
        if driver:
            driver.quit()
        
        # Remove the temporary directory
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass

if __name__ == "__main__":
    # Suppress all print output when run from GUI
    if len(sys.argv) > 1 and '--silent' not in sys.argv:
        # Parse command line argument for channel ID
        try:
            channel_id = int(sys.argv[1])
        except ValueError:
            # Only print errors if not in silent mode
            sys.exit(1)
    else:
        # Default channel ID if none provided (for backward compatibility)
        channel_id = 32
    
    start_integrated_stream(channel_id)