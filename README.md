# Daddy Live Stream Player V2.0

A desktop application for accessing Daddy Live streaming resources with an intuitive GUI for browsing live sports channels and scheduled events.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Support the Project
If you like my work, feel free to buy me a coffee! ☕
https://buymeacoffee.com/BluberrySmoothie

## Features

- 🎯 **Browse Live Channels** - Access hundreds of live sports channels
- 📅 **Events Schedule** - View upcoming sporting events by category and time
- 🔍 **Search/Filter** - Quickly find channels and events with built-in search
- 🎬 **Integrated Playback** - Seamless stream playback via Streamlink and MPV/VLC
- 🍪 **Session Management** - Automatic cookie handling for authenticated streams
- 🌐 **Network Monitoring** - Intelligent stream URL detection using browser automation
- 🎨 **Clean Interface** - Modern PyQt6-based GUI

## System Requirements

### Required
- **Python 3.8+**
- **Streamlink** - Stream handling and playback management
- **Selenium & Chrome WebDriver** - For session management and URL extraction
- **Video Player**: Either **MPV** (recommended) or **VLC**

### Platform Support
- Windows 10/11 (primary)
- Linux/macOS (untested but should work)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/BluberrySmoothie/DaddyLivePlayer.git
cd DaddyLivePlayer
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Streamlink
```bash
# Via pip
pip install streamlink

# OR via winget (Windows)
winget install streamlink
```

### 4. Install Video Player

**Option A: MPV (Recommended - lightweight)**
```bash
winget install mpv
```

**Option B: VLC (Alternative)**
```bash
winget install VideoLAN.VLC
```

### 5. Verify Installation
```bash
# Check Streamlink
streamlink --version

# Check MPV
mpv --version

# Check Python packages
pip list | grep -E "PyQt6|selenium|streamlink"
```

## Usage

### GUI Application (Recommended)

Launch the full application with graphical interface:

```bash
python daddylive_gui.py
```

**Features:**
1. **Live Channels Tab** - Browse and search all available channels
2. **Events Schedule Tab** - View upcoming sporting events
3. **Search/Filter** - Type to filter channels or events in real-time
4. **Play/Stop Controls** - Simple playback management

### Standalone Player (Advanced)

If you know the channel ID, you can use the standalone player script directly:

```bash
# Play a specific channel by ID
python PlayTest-streamlink.py <channel_id>

# Examples:
python PlayTest-streamlink.py 32    # Play channel 32
python PlayTest-streamlink.py 20    # Play channel 20
python PlayTest-streamlink.py 349   # Play channel 349
```

**Standalone Player Features:**
- Automatic session cookie extraction
- Network traffic monitoring to find stream URLs
- Supports multiple domain patterns (nfsnew, dokko1new, etc.)
- Automatic MPV/VLC detection with fallback
- Works in headless mode for automation

**Silent Mode (for scripting):**
```bash
python PlayTest-streamlink.py 32 --silent
```

## How It Works

### Session Management
1. Opens the channel webpage using Selenium
2. Extracts session cookies for authentication
3. Passes cookies and URL to Streamlink with proper headers

### Playback
- Streams are handled by Streamlink
- Video playback via MPV (preferred) or VLC
- Automatic header injection (Referer, Origin, User-Agent)
- Cookie-based authentication

## Configuration

### Stream Server Settings
Edit `PlayTest-streamlink.py` to modify default settings:

```python
STREAM_REFERER = "https://truncatedactivitiplay.xyz/"
STREAM_ORIGIN = "https://truncatedactivitiplay.xyz"
BASE_WEBPAGE = "https://dlhd.dad"
```

### Player Selection
The application automatically detects available players in this order:
1. MPV (if found in PATH or common installation directories)
2. VLC (as fallback)

To force a specific player, modify the `find_player()` function in `PlayTest-streamlink.py`.

## Troubleshooting

### "No suitable video player found"
**Solution:** Install MPV or VLC
```bash
winget install mpv
# OR
winget install VideoLAN.VLC
```

### "Streamlink not found in PATH"
**Solution:** Install or reinstall Streamlink
```bash
pip install --upgrade streamlink
```

### "Could not find stream URL"
**Possible causes:**
- Channel is offline or unavailable
- Site structure has changed
- Network connectivity issues
- VPN may be required

**Solutions:**
- Try a different channel
- Check if the website is accessible in a regular browser
- Use a VPN if geo-blocked
- Wait and retry (may be temporary rate limiting)

### "HTTP 418 I'm a teapot" or "HTTP 522" errors
**Possible causes:**
- Server-side anti-bot protection
- Rate limiting
- Server temporarily down
- IP address blocked

**Solutions:**
- Wait a few minutes before retrying
- Use a VPN to change your IP address
- Try different channels (some have less protection)

### Chrome/WebDriver Issues
**Solution:** Update Chrome and reinstall webdriver-manager
```bash
pip install --upgrade webdriver-manager
```

### GUI Crashes or Threading Errors
The latest version includes thread-safe signal handling. If you encounter crashes:
- Make sure you're using the latest code
- Check that PyQt6 is properly installed: `pip install --upgrade PyQt6`

## Dependencies

See `requirements.txt` for complete list:

```
PyQt6>=6.4.0
requests>=2.28.0
selenium>=4.8.0
webdriver-manager>=3.8.0
streamlink>=7.0.0
beautifulsoup4>=4.11.0
python-dateutil>=2.8.0
pytz>=2023.3
```

**External (installed separately):**
- Streamlink
- MPV or VLC media player
- Chrome/Chromium browser (for Selenium)

## Project Structure

```
DaddyLivePlayer/
├── daddylive_gui.py          # Main GUI application
├── PlayTest-streamlink.py    # Standalone stream player
├── stream_player.py          # Stream management threading
├── data_retriever.py         # Channel/event data fetching
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Known Limitations

- **Stream Availability**: Not all channels work at all times (server-side restrictions)
- **Anti-Bot Protection**: Some channels use 418 errors to block automated access
- **Geo-Restrictions**: Some content may require VPN depending on location
- **Cross-Origin Iframes**: Streams in cross-origin iframes may not be detectable
- **Site Changes**: If the source website changes structure, URL detection may fail

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Areas for Improvement
- Better error handling and user feedback
- Support for additional streaming sources
- Playlist/favorites functionality
- Recording capabilities
- Multi-platform testing and optimization

## Legal Disclaimer

This application is provided for educational purposes only. Users are responsible for ensuring their use complies with applicable laws and the terms of service of the streaming sources. The developers do not host, distribute, or promote any copyrighted content.

## Credits

**Developer:** Bluberry Smoothie  
**GitHub:** [github.com/BluberrySmoothie](https://github.com/BluberrySmoothie)

**Built With:**
- PyQt6 - GUI framework
- Streamlink - Stream handling
- Selenium - Browser automation
- MPV/VLC - Media playback

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Consult the Troubleshooting section above

---

**Note:** This application requires an active internet connection and depends on third-party streaming sources that may change or become unavailable at any time.
