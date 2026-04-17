from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageDraw, ImageFont
from utils.app_utils import get_font
import logging
from datetime import datetime
import aiohttp
import asyncio
import certifi
import csv
import io
import logging
import json
import os
import ssl
import pytz
import requests
from flask import current_app
import requests
import pandas as pd

logger = logging.getLogger(__name__)

BUS_STOP_URL = "https://datamall2.mytransport.sg/ltaodataservice/BusStops"
BUS_ARRIVAL_URL = "https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival"

CACHE_TTL_HOURS = 7 * 24  # 7 days — station data rarely changes
CACHE_FILE = os.path.join(
    os.path.dirname(__file__), "stations_cache.json"
)



def _create_ssl_context():
    """Create an SSL context using certifi's CA bundle."""
    return ssl.create_default_context(cafile=certifi.where())

def _create_ssl_session():
    """Create an aiohttp session with proper SSL cert verification."""
    connector = aiohttp.TCPConnector(ssl=_create_ssl_context())
    return aiohttp.ClientSession(connector=connector)

def _load_cached_stations():
    """Load station index from cache if fresh enough."""
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        age_hours = (
            (datetime.now().timestamp()
            - os.path.getmtime(CACHE_FILE)) / 3600
        )
        if age_hours > CACHE_TTL_HOURS:
            return None
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        if data:
            logger.info("Loaded station index from cache")
            return data
    except Exception as e:
        logger.warning(f"Could not read station cache: {e}")
    return None

def _save_stations_cache(stations):
    """Write station index to cache file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(stations, f, indent=4)
        logger.info("Saved station index to cache")
    except Exception as e:
        logger.warning(f"Could not write station cache: {e}")


def _fetch_station_index(api_key):
    """Download the MTA stations CSV and build a station index.

    Groups stations by Complex ID so physically connected
    stations (e.g. 59 St-Columbus Circle with 1/A/B/C/D)
    appear as a single entry, while stations that share a
    name but are separate (e.g. the various 125 St stations)
    remain distinct.

    Returns a dict keyed by complex_id:
        {
            "614": {
                "name": "59 St-Columbus Circle",
                "stop_ids": ["A24", "125"],
                "lines": ["1", "A", "B", "C", "D"],
                "north_label": "Uptown",
                "south_label": "Downtown",
            },
            ...
        }
    """
    

    headers = {
        'AccountKey': api_key,
        'accept': 'application/json'
    }

    all_stops = []
    skip = 0

    # Retrive all stations
    while True:
        url = f"{BUS_STOP_URL}?$skip={skip}"

        response = requests.get(url, headers=headers, timeout=15, verify=certifi.where())
        response.raise_for_status()

        data = response.json().get('value', [])
        all_stops.extend(data)

        # If <500 records received, break off from loop
        if len(data) < 500:
            break

        skip += 500

    df = pd.DataFrame(all_stops)
    df = df.set_index("BusStopCode")
    complexes = df['Description'].to_dict()

    return complexes


def _get_station_index(api_key):
    """Return station index, using cache when available."""
    stations = _load_cached_stations()
    if stations:
        return stations
    logger.info("Building station index from LTA Datamall data...")
    stations = _fetch_station_index(api_key)
    if stations:
        _save_stations_cache(stations)
    return stations


class SGBusArrival(BasePlugin):
    """
    Example InkyPi plugin template.

    This plugin demonstrates how to generate a Pillow image and return it
    to InkyPi for display. Plugin authors can use this as a starting point
    for building custom plugins.
    """
    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['api_key'] = {
            "required": True,
            "service": "LTA's DataMall",
            "expected_key": "LTA_DATAMALL_API_KEY"
        }
        template_params['style_settings'] = True

        # Fetch API from env
        device_config = current_app.config.get('DEVICE_CONFIG')
        api_key = device_config.load_env_key("LTA_DATAMALL_API_KEY")

        # try:
        #     stations = _get_station_index(api_key)
        # except Exception as e:
        #     logger.error(f"Failed to preload station index: {e}")
        #     stations = {}

        # template_params['stations_json'] = json.dumps(stations)
        # template_params['api_key'] = api_key


        return template_params

    def generate_image(self, settings, device_config):
        """
        Generate and return a PIL image for display.

        Args:
            settings (dict):
                Values from the plugin's settings page form.
                Example:
                    title = settings.get("title", "Hello World")

            device_config:
                Device configuration. Can be used to load secrets
                or device-level configuration:
                    api_key = device_config.load_env_key("MY_API_KEY")
                    dimensions = device_config.get_resolution()

        Returns:
            PIL.Image.Image:
                The rendered image to be displayed on the device.
        """
        bus_stop_id = settings.get('station_id', 'None')
        bus_list = settings.get('selected_buses', '[]')

        logger.info(f"Bus stop id: {bus_stop_id}")
        logger.info(f"Buses selected: {bus_list}")


        # Example: load a value from plugin settings
        text = settings.get("title") or "Hello World"

        # Target display size, handling display orientation from device config
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]
        width, height = dimensions

        # Create a blank image
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        font_size = width * 0.145
        font = get_font("Jost", font_size)

        # Measure text size
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center text
        x = (width - text_width) // 2
        y = (height - (text_height*2)) // 2

        # Draw text
        draw.text((x, y), text, fill="black", font=font)

        logger.debug("Template plugin rendered image (%dx%d)", width, height)

        return image






