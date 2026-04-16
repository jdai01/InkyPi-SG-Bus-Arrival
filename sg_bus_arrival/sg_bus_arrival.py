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

logger = logging.getLogger(__name__)


class SGBusArrival(BasePlugin):
    """
    Example InkyPi plugin template.

    This plugin demonstrates how to generate a Pillow image and return it
    to InkyPi for display. Plugin authors can use this as a starting point
    for building custom plugins.
    """
    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)

        self.__isInitialised = True
        self.__api_key = None

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['api_key'] = {
            "required": True,
            "service": "LTA's DataMall",
            "expected_key": "LTA_DATAMALL_API_KEY"
        }
        template_params['style_settings'] = True
        template_params['isInitialised'] = self.__isInitialised
        template_params['api_key'] = self.__api_key

        try:
            device_config = current_app.config.get('DEVICE_CONFIG')
            logger.info(current_app.config.__str__)

        except:
            logger.info("== No device_config found. ==")
            

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

        if self.__isInitialised:
            self.__api_key = device_config.load_env_key("LTA_DATAMALL_API_KEY")
            self.__isInitialised = False


        



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
