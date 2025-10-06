# data_retriever.py

import requests
import re
import html
from urllib.parse import urlparse
from datetime import datetime, timezone
import json

# --- Shared Configuration ---
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
DEFAULT_BASE_URL = 'https://daddylivestream.com'

class DataRetriever:
    """
    Handles fetching and parsing of both Live Channels and Scheduled Events data.
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': UA, 'Connection': 'Keep-Alive'})
        self.baseurl = DEFAULT_BASE_URL
        self._initialize_base_url()

    def _initialize_base_url(self):
        """Fetches the current base URL from GitHub config."""
        try:
            # Source URL from app.py/daddylive_api.py
            main_url_content = self.session.get(
                'https://raw.githubusercontent.com/thecrewwh/dl_url/refs/heads/main/dl.xml',
                timeout=5
            ).text
            found_iframe_src = re.findall('src = "([^"]*)', main_url_content)
            if found_iframe_src:
                iframe_url = found_iframe_src[0]
                parsed_iframe_url = urlparse(iframe_url)
                self.baseurl = f"{parsed_iframe_url.scheme}://{parsed_iframe_url.netloc}"
        except Exception as e:
            # Fallback to default
            pass

    def get_headers(self):
        """Generate headers for requests."""
        return {
            'User-Agent': UA,
            'Connection': 'Keep-Alive',
            'Referer': f'{self.baseurl}/',
            'Origin': self.baseurl
        }

    # --- Channels Extraction Logic (from DLLinks.py) ---
    def extract_all_streams(self):
        """Extracts all streams' IDs and names from the 24-7-channels page."""
        url = f'{self.baseurl}/24-7-channels.php'
        headers = self.get_headers()
        
        try:
            resp = self.session.get(url, headers=headers, timeout=10).text
            
            # Regex to find channel ID and name
            channel_items = re.findall(
                r'href="/stream/stream-(\d+)\.php"[^>]*>\s*(?:<[^>]+>)*([^<]+)',
                resp,
                re.DOTALL
            )
            
            results = []
            for channel_id, name in channel_items:
                clean_name = re.sub(r'[\s\n\t]+', ' ', html.unescape(name.strip())).strip()
                
                # Filter for duplicates by ID
                if not any(r['DLChNo'] == int(channel_id) for r in results):
                    results.append({'DLChNo': int(channel_id), 'DLChName': clean_name})
            
            return results
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error fetching streams: {e}")
        except Exception as e:
            raise RuntimeError(f"Error processing streams data: {e}")

    # --- Events Extraction Logic (from Dlevents.py) ---

    @staticmethod
    def _get_local_time(utc_time_str):
        """Simple helper to convert HH:MM UTC string to a more readable local time string."""
        try:
            utc_now = datetime.utcnow()
            event_time_utc = datetime.strptime(utc_time_str, '%H:%M')
            event_time_utc = event_time_utc.replace(year=utc_now.year, month=utc_now.month, day=utc_now.day)
            event_time_utc = event_time_utc.replace(tzinfo=timezone.utc)
            
            local_time = event_time_utc.astimezone()
            return local_time.strftime('%I:%M %p').lstrip('0')
        except Exception:
            return f"{utc_time_str} (UTC)" # Return the UTC time if conversion fails

    def fetch_and_extract_events(self):
        """Fetches the JSON and processes it into event rows."""
        schedule_url = f'{self.baseurl}/schedule/schedule-generated.php'
        headers = self.get_headers()

        try:
            # Fetch the schedule JSON data
            response = self.session.get(schedule_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error fetching JSON data: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Error decoding JSON response: {e}")

        event_rows = []

        for date_full, categories in data.items():
            date_only = date_full.split(' - ')[0].strip()

            for category_name, events in categories.items():
                
                for event_details in events:
                    time_utc = event_details.get('time', 'N/A')
                    time_local = self._get_local_time(time_utc)
                    event_name = html.unescape(event_details.get('event', 'N/A'))
                    
                    # FIX: Handle both list and dict formats for channels
                    channels1 = event_details.get('channels', [])
                    channels2 = event_details.get('channels2', [])
                    
                    # Ensure both are lists before concatenating
                    if not isinstance(channels1, list):
                        channels1 = [channels1] if channels1 else []
                    if not isinstance(channels2, list):
                        channels2 = [channels2] if channels2 else []
                    
                    all_channels = channels1 + channels2
                    
                    if not all_channels:
                        # Event row for 'NO CHANNEL LISTED'
                        event_rows.append({
                            'Date': date_only,
                            'Time_UTC': time_utc,
                            'Time_Local': time_local,
                            'Category': category_name,
                            'Event': event_name,
                            'Channel_Name': 'NO CHANNEL LISTED',
                            'Channel_ID': 'N/A'
                        })
                    else:
                        for channel in all_channels:
                            # Handle if channel is a dict or not properly formatted
                            if isinstance(channel, dict):
                                channel_name = html.unescape(channel.get('channel_name', 'N/A'))
                                channel_id = channel.get('channel_id', 'N/A')
                            else:
                                # Skip malformed channel data
                                continue
                                
                            # Event row for each channel linked to the event
                            event_rows.append({
                                'Date': date_only,
                                'Time_UTC': time_utc,
                                'Time_Local': time_local,
                                'Category': category_name,
                                'Event': event_name,
                                'Channel_Name': channel_name,
                                'Channel_ID': channel_id
                            })
        return event_rows