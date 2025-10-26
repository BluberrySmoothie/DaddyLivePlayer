# data_retriever.py

import requests
import re
import html
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import json
import pytz 
from bs4 import BeautifulSoup 
from dateutil import parser as dparser 
from dateutil import tz as dateutil_tz 

# --- Shared Configuration ---
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
DEFAULT_BASE_URL = 'https://dlhd.dad/' 
FALLBACK_SCHEDULE_URL = 'https://dlhd.dad/' 

class DataRetriever:
    """
    Handles fetching and parsing of both Live Channels and Scheduled Events data.
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': UA, 'Connection': 'Keep-Alive'})
        self.baseurl = DEFAULT_BASE_URL
        self._initialize_base_url()
        self.schedule_url = f'{self.baseurl}/' if urlparse(self.baseurl).netloc else FALLBACK_SCHEDULE_URL

    def _initialize_base_url(self):
        """Fetches the current base URL from GitHub config or uses fallback."""
        try:
            main_url_content = self.session.get(
                'https://raw.githubusercontent.com/thecrewwh/dl_url/refs/heads/main/dl.xml',
                timeout=5
            ).text
            found_iframe_src = re.findall('src = "([^"]*)', main_url_content)
            if found_iframe_src:
                iframe_url = found_iframe_src[0]
                parsed_iframe_url = urlparse(iframe_url)
                self.baseurl = f"{parsed_iframe_url.scheme}://{parsed_iframe_url.netloc}"
            else:
                 pass

        except Exception:
            pass 


    def get_headers(self, referer_override=None):
        """Generate headers for requests."""
        referer = referer_override if referer_override else f'{self.baseurl}/'
        return {
            'User-Agent': UA,
            'Connection': 'Keep-Alive',
            'Referer': referer,
            'Origin': self.baseurl
        }

    # --- Channels Extraction Logic (Updated for 247.txt structure) ---
    def extract_all_streams(self):
        """Extracts all streams' IDs and names from the 24-7-channels page."""
        url = f'{self.baseurl}/24-7-channels.php'
        headers = self.get_headers()

        try:
            resp = self.session.get(url, headers=headers, timeout=10).text

            # Regex updated to find channel ID from watch.php link and name from data-title
            channel_items = re.findall(
                r'href="/watch\.php\?id=(\d+)"[^>]*data-title="([^"]+)"',
                resp,
                re.IGNORECASE | re.DOTALL
            )

            results = []
            seen_ids = set()
            for channel_id_str, name in channel_items:
                try:
                    channel_id = int(channel_id_str)
                    if channel_id in seen_ids:
                        continue 

                    clean_name = re.sub(r'\s+', ' ', html.unescape(name.strip())).strip()

                    results.append({'DLChNo': channel_id, 'DLChName': clean_name})
                    seen_ids.add(channel_id)

                except ValueError:
                    continue
                except Exception:
                     continue

            results.sort(key=lambda x: x['DLChName'])
            return results

        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error fetching streams from {url}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error processing streams data: {e}")

    # --- Events Extraction Logic (Adapted from whatson.py/schedule HTML) ---
    
    @staticmethod
    def _get_local_time(aware_dt):
        """Converts an aware datetime object (in Europe/London) to a local time string."""
        if not isinstance(aware_dt, datetime) or aware_dt.tzinfo is None:
             return "N/A Time"
        try:
            local_tz = dateutil_tz.tzlocal()
            local_dt = aware_dt.astimezone(local_tz)
            # Format as HH:MM AM/PM, removing leading zero from hour if present
            return local_dt.strftime('%I:%M %p').lstrip('0')
        except Exception:
            return "N/A Time"

    @staticmethod
    def _get_schedule_date(soup):
        """Parses the date from the <div class="schedule__dayTitle"> element."""
        tz_london = pytz.timezone("Europe/London")
        try:
            title_element = soup.find('div', class_='schedule__dayTitle')
            if not title_element:
                raise ValueError("Could not find 'schedule__dayTitle' element")

            date_part = title_element.get_text(strip=True).split(" - ")[0].strip()
            # Use dateutil parser
            parsed_date = dparser.parse(date_part, fuzzy=True).date()
            return parsed_date
        except Exception:
            # Fallback to current date in London timezone
            return datetime.now(tz=tz_london).date()


    def fetch_and_extract_events(self):
        """Fetches the HTML schedule and processes it into event rows using BeautifulSoup."""
        headers = self.get_headers(referer_override=self.schedule_url) 

        try:
            response = self.session.get(self.schedule_url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error fetching HTML event data from {self.schedule_url}: {e}")

        soup = BeautifulSoup(response.text, 'html.parser')
        schedule_date = self._get_schedule_date(soup) 
        tz_london = pytz.timezone("Europe/London")

        event_rows = []

        category_blocks = soup.find_all('div', class_='schedule__category')

        for category_block in category_blocks:
            category_header = category_block.find('div', class_='schedule__catHeader')
            category_meta = category_header.find('div', class_='card__meta') if category_header else None
            if not category_meta:
                continue

            category_name = html.unescape(category_meta.get_text(strip=True))

            # Skip TV Show categories
            if "tv show" in category_name.lower():
                continue

            event_blocks = category_block.find_all('div', class_='schedule__event')
            for event_block in event_blocks:
                time_str_elem = event_block.find('span', class_='schedule__time')
                event_title_elem = event_block.find('span', class_='schedule__eventTitle')

                if not time_str_elem or not event_title_elem:
                    continue

                time_utc_str = time_str_elem.get_text(strip=True) # e.g., "15:57" (UK time)
                event_name = html.unescape(event_title_elem.get_text(strip=True))

                try:
                    # Parse time and combine with the schedule date
                    event_time = dparser.parse(time_utc_str).time()
                    naive_dt = datetime.combine(schedule_date, event_time)
                    # Localize to London time zone
                    aware_dt_london = tz_london.localize(naive_dt)
                    time_local_str = self._get_local_time(aware_dt_london)
                except Exception:
                    continue

                # Extract channels with IDs
                channels_data = []
                channels_container = event_block.find('div', class_='schedule__channels')
                if channels_container:
                    channel_links = channels_container.find_all('a')
                    for link in channel_links:
                        channel_name = html.unescape(link.get_text(strip=True))
                        href = link.get('href')
                        channel_id = 'N/A'
                        if href and 'watch.php?id=' in href:
                             try:
                                 # Extract ID from href="/watch.php?id=116"
                                 parsed_link = urlparse(href)
                                 query_params = parse_qs(parsed_link.query)
                                 id_list = query_params.get('id', [])
                                 if id_list:
                                     channel_id = int(id_list[0])
                             except (ValueError, IndexError):
                                 channel_id = 'N/A'
                        if channel_id != 'N/A':
                             channels_data.append({'name': channel_name, 'id': channel_id})


                date_only_str = schedule_date.strftime('%Y-%m-%d')

                # Create event rows, one per channel
                if not channels_data:
                    event_rows.append({
                        'Date': date_only_str,
                        'Time_UTC': time_utc_str,
                        'Time_Local': time_local_str,
                        'Category': category_name,
                        'Event': event_name,
                        'Channel_Name': 'NO CHANNEL LISTED',
                        'Channel_ID': 'N/A'
                    })
                else:
                    for channel in channels_data:
                        event_rows.append({
                            'Date': date_only_str,
                            'Time_UTC': time_utc_str,
                            'Time_Local': time_local_str,
                            'Category': category_name,
                            'Event': event_name,
                            'Channel_Name': channel['name'],
                            'Channel_ID': channel['id']
                        })

        return event_rows