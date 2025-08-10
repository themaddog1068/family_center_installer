"""
Weather Service for Family Center Application.

This module provides weather data fetching, forecast image generation,
and radar image downloading capabilities for the slideshow system.
"""

import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

from src.config.config_manager import ConfigManager
from src.utils.error_handling import handle_error

logger = logging.getLogger(__name__)


class WeatherData(BaseModel):
    """Weather data model for current conditions."""

    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: float = Field(..., description="Feels like temperature in Celsius")
    humidity: int = Field(..., description="Humidity percentage")
    pressure: int = Field(..., description="Pressure in hPa")
    wind_speed: float = Field(..., description="Wind speed in m/s")
    wind_direction: int = Field(..., description="Wind direction in degrees")
    description: str = Field(..., description="Weather description")
    icon: str = Field(..., description="Weather icon code")
    visibility: int = Field(..., description="Visibility in meters")
    sunrise: datetime = Field(..., description="Sunrise time")
    sunset: datetime = Field(..., description="Sunset time")


class WeatherAlert(BaseModel):
    """Weather alert model for warnings, watches, and advisories."""

    event: str = Field(..., description="Alert event name (e.g., 'Flood Warning')")
    description: str = Field(..., description="Alert description")
    severity: str = Field(..., description="Alert severity (warning, watch, advisory)")
    start_time: datetime = Field(..., description="Alert start time")
    end_time: datetime = Field(..., description="Alert end time")
    tags: list[str] = Field(default_factory=list, description="Alert tags")


class ForecastData(BaseModel):
    """Forecast data model for future weather."""

    date: datetime = Field(..., description="Forecast date")
    temperature_min: float = Field(..., description="Minimum temperature")
    temperature_max: float = Field(..., description="Maximum temperature")
    humidity: int = Field(..., description="Humidity percentage")
    description: str = Field(..., description="Weather description")
    icon: str = Field(..., description="Weather icon code")
    precipitation_probability: float = Field(
        ..., description="Precipitation probability"
    )
    alerts: list[WeatherAlert] = Field(
        default_factory=list, description="Weather alerts for this day"
    )


class WeatherService:
    """Weather service for fetching and processing weather data."""

    def __init__(self, config: ConfigManager) -> None:
        """Initialize the weather service.

        Args:
            config: Configuration manager instance
        """
        self.config = config

        # Get weather config with defaults if not present
        try:
            self.weather_config = config.get("weather")
        except KeyError:
            # Create default weather config if not present
            self.weather_config = {
                "api_key": "",
                "zip_code": "",
                "country_code": "US",
                "units": "metric",
                "language": "en",
                "output_folder": "media/Weather",
                "image_width": 1920,
                "image_height": 1080,
                "download_radar": True,
                "radar_animation_frames": 6,
                "radar_animation_duration": 2000,
            }

        self.api_key = self.weather_config.get("api_key", "")
        self.zip_code = self.weather_config.get("zip_code", "")
        self.country_code = self.weather_config.get("country_code", "US")
        self.units = self.weather_config.get("units", "metric")
        self.language = self.weather_config.get("language", "en")

        # Output configuration
        self.output_folder = Path(
            self.weather_config.get("output_folder", "media/Weather")
        )
        self.temp_folder = Path("media/temp/weather")  # For intermediate files
        self.image_width = self.weather_config.get("image_width", 1920)
        self.image_height = self.weather_config.get("image_height", 1080)

        # Radar configuration
        self.radar_enabled = self.weather_config.get("download_radar", True)
        self.radar_animation_frames = self.weather_config.get(
            "radar_animation_frames", 6
        )
        self.radar_animation_duration = self.weather_config.get(
            "radar_animation_duration", 2000
        )  # ms

        # Pressure trend tracking
        self.pressure_history: list[tuple[datetime, int]] = []
        self.max_pressure_history = 10  # Keep last 10 readings

        # Create output directories
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.temp_folder.mkdir(parents=True, exist_ok=True)

        # API endpoints
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.current_url = f"{self.base_url}/weather"
        self.forecast_url = f"{self.base_url}/forecast"

        # Font configuration
        self.font_size_large = 48
        self.font_size_medium = 36
        self.font_size_small = 24
        self.font_size_tiny = 18

        # Colors
        self.colors = {
            "background": (240, 248, 255),  # AliceBlue
            "text": (25, 25, 112),  # MidnightBlue
            "accent": (70, 130, 180),  # SteelBlue
            "highlight": (255, 140, 0),  # DarkOrange
            "success": (34, 139, 34),  # ForestGreen
            "warning": (255, 69, 0),  # RedOrange
            "border": (200, 200, 200),  # LightGray
        }

        logger.info(
            f"Weather service initialized for {self.zip_code}, {self.country_code}"
        )

    @handle_error()
    def fetch_current_weather(self) -> WeatherData | None:
        """Fetch current weather data from OpenWeatherMap API.

        Returns:
            WeatherData object with current weather information, or None if failed
        """
        if not self.api_key or not self.zip_code:
            logger.error("Weather API key or ZIP code not configured")
            return None

        params = {
            "zip": f"{self.zip_code},{self.country_code}",
            "appid": self.api_key,
            "units": self.units,
            "lang": self.language,
        }

        try:
            response = requests.get(self.current_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            weather_data = WeatherData(
                temperature=data["main"]["temp"],
                feels_like=data["main"]["feels_like"],
                humidity=data["main"]["humidity"],
                pressure=data["main"]["pressure"],
                wind_speed=data["wind"]["speed"],
                wind_direction=data["wind"]["deg"],
                description=data["weather"][0]["description"],
                icon=data["weather"][0]["icon"],
                visibility=data.get("visibility", 10000),
                sunrise=datetime.fromtimestamp(data["sys"]["sunrise"]),
                sunset=datetime.fromtimestamp(data["sys"]["sunset"]),
            )

            logger.info(
                f"Current weather fetched: {weather_data.temperature}°C, {weather_data.description}"
            )
            return weather_data

        except requests.RequestException as e:
            logger.error(f"Failed to fetch current weather: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse weather data: {e}")
            return None

    @handle_error()
    def fetch_weather_alerts(self) -> list[WeatherAlert]:
        """Fetch weather alerts from OpenWeatherMap API.

        Returns:
            List of WeatherAlert objects
        """
        if not self.api_key or not self.zip_code:
            logger.error("Weather API key or ZIP code not configured")
            return []

        # OpenWeatherMap doesn't provide alerts in the free tier
        # For now, we'll return an empty list
        # In a production system, you might use NOAA's weather alerts API
        logger.info("Weather alerts not available in free OpenWeatherMap tier")
        return []

    @handle_error()
    def fetch_forecast(self, days: int = 5) -> list[ForecastData]:
        """Fetch weather forecast data from OpenWeatherMap API.

        Args:
            days: Number of days to forecast (max 5 for free API)

        Returns:
            List of ForecastData objects
        """
        if not self.api_key or not self.zip_code:
            logger.error("Weather API key or ZIP code not configured")
            return []

        params = {
            "zip": f"{self.zip_code},{self.country_code}",
            "appid": self.api_key,
            "units": self.units,
            "lang": self.language,
            "cnt": min(days * 8, 40),  # 8 forecasts per day, max 40 for free API
        }

        try:
            response = requests.get(self.forecast_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            forecasts = []
            daily_data: dict[str, dict[str, list[Any]]] = {}

            # Group forecasts by day
            for item in data["list"]:
                date_str = datetime.fromtimestamp(item["dt"]).date().isoformat()
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        "temps": [],
                        "humidity": [],
                        "descriptions": [],
                        "icons": [],
                        "pop": [],
                    }

                daily_data[date_str]["temps"].append(item["main"]["temp"])
                daily_data[date_str]["humidity"].append(item["main"]["humidity"])
                daily_data[date_str]["descriptions"].append(
                    item["weather"][0]["description"]
                )
                daily_data[date_str]["icons"].append(item["weather"][0]["icon"])
                daily_data[date_str]["pop"].append(
                    item.get("pop", 0) * 100
                )  # Convert to percentage

            # Create daily forecasts
            sorted_dates = sorted(daily_data.keys())
            for date_str in sorted_dates[:days]:
                day_data = daily_data[date_str]
                date_obj = datetime.fromisoformat(date_str).date()

                # Get most common description and icon for the day
                most_common_desc = max(
                    set(day_data["descriptions"]), key=day_data["descriptions"].count
                )
                most_common_icon = max(
                    set(day_data["icons"]), key=day_data["icons"].count
                )

                # Calculate average precipitation probability
                avg_pop = sum(day_data["pop"]) / len(day_data["pop"])

                # Get alerts for this day (empty for now since free API doesn't support alerts)
                day_alerts: list[WeatherAlert] = []

                forecast = ForecastData(
                    date=datetime.combine(date_obj, datetime.min.time()),
                    temperature_min=min(day_data["temps"]),
                    temperature_max=max(day_data["temps"]),
                    humidity=int(sum(day_data["humidity"]) / len(day_data["humidity"])),
                    description=most_common_desc,
                    icon=most_common_icon,
                    precipitation_probability=avg_pop,
                    alerts=day_alerts,
                )
                forecasts.append(forecast)

            logger.info(f"Forecast fetched: {len(forecasts)} days")
            return forecasts

        except requests.RequestException as e:
            logger.error(f"Failed to fetch forecast: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse forecast data: {e}")
            return []

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Get font with specified size.

        Args:
            size: Font size in pixels

        Returns:
            PIL font object
        """
        try:
            # Try to use a system font
            return ImageFont.truetype("/System/Library/Fonts/Arial.ttf", size)
        except OSError:
            try:
                # Fallback to default font
                return ImageFont.load_default()
            except Exception:
                # Last resort - create a basic font
                return ImageFont.load_default()

    def _draw_text_with_background(
        self,
        draw: Any,  # ImageDraw.Draw type is complex, use Any for now
        text: str,
        position: tuple[int, int],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        text_color: tuple[int, int, int],
        bg_color: tuple[int, int, int] | None = None,
        padding: int = 5,
    ) -> None:
        """Draw text with optional background.

        Args:
            draw: PIL ImageDraw object
            text: Text to draw
            position: (x, y) position
            font: PIL font object
            text_color: RGB text color
            bg_color: RGB background color (optional)
            padding: Background padding in pixels
        """
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x, y = position

        # Draw background if specified
        if bg_color:
            bg_rect = [
                x - padding,
                y - padding,
                x + text_width + padding,
                y + text_height + padding,
            ]
            draw.rectangle(bg_rect, fill=bg_color)

        # Draw text
        draw.text((x, y), text, font=font, fill=text_color)

    @handle_error()
    def download_radar_frames(self) -> list[Path]:
        """Download multiple radar frames for animation.

        Returns:
            List of paths to downloaded radar frame images
        """
        if not self.radar_enabled:
            logger.info("Radar downloads disabled")
            return []

        frame_paths = []

        try:
            # Use NOAA KBOX (Boston/Taunton, MA) local radar images for a zoomed-in New England view
            # These provide a much more focused area: eastern MA, southern NH, northern RI/CT
            radar_urls = [
                "https://radar.weather.gov/ridge/standard/KBOX_0.gif",  # most recent
                "https://radar.weather.gov/ridge/standard/KBOX_2.gif",
                "https://radar.weather.gov/ridge/standard/KBOX_4.gif",
                "https://radar.weather.gov/ridge/standard/KBOX_6.gif",
                "https://radar.weather.gov/ridge/standard/KBOX_8.gif",
            ]

            # For now, we'll use static radar images since animated GIFs require more complex processing
            # In a full implementation, you'd download multiple time-stamped frames
            for i, url in enumerate(radar_urls[: self.radar_animation_frames]):
                try:
                    response = requests.get(url, timeout=15)
                    response.raise_for_status()

                    # Save radar frame
                    frame_path = self.temp_folder / f"radar_frame_{i:02d}.png"
                    with open(frame_path, "wb") as f:
                        f.write(response.content)

                    frame_paths.append(frame_path)
                    logger.info(f"Radar frame {i+1} downloaded: {frame_path}")

                except requests.RequestException as e:
                    logger.warning(f"Failed to download radar frame {i+1}: {e}")
                    continue

            return frame_paths

        except Exception as e:
            logger.error(f"Failed to download radar frames: {e}")
            return frame_paths

    @handle_error()
    def create_radar_animation(self, frame_paths: list[Path]) -> Path | None:
        """Create animated GIF from radar frames.

        Args:
            frame_paths: List of paths to radar frame images

        Returns:
            Path to animated GIF, or None if failed
        """
        if not frame_paths:
            logger.warning("No radar frames to animate")
            return None

        try:
            # Load all frames
            frames = []
            for frame_path in frame_paths:
                if frame_path.exists():
                    frame = Image.open(frame_path)
                    # Resize to larger size for better quality when scaled up
                    # Target size for 3/4 of 1920x1080 slide: approximately 1400x900
                    frame = frame.resize((1400, 900), Image.Resampling.LANCZOS)
                    frames.append(frame)

            if not frames:
                logger.warning("No valid radar frames found")
                return None

            # Create animated GIF
            output_path = self.temp_folder / "radar_animation.gif"

            # If we have multiple frames, create animation
            if len(frames) > 1:
                frames[0].save(
                    output_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=self.radar_animation_duration,
                    loop=0,
                    optimize=True,
                )
            else:
                # Single frame - create a simple animation by duplicating and slightly modifying
                base_frame = frames[0]
                animated_frames = [base_frame]

                # Create slight variations for animation
                for _i in range(3):
                    # Create a slightly modified version (add a subtle overlay)
                    modified_frame = base_frame.copy()
                    overlay = Image.new(
                        "RGBA", base_frame.size, (0, 0, 255, 20)
                    )  # Subtle blue overlay
                    modified_frame = Image.alpha_composite(
                        modified_frame.convert("RGBA"), overlay
                    ).convert("RGB")
                    animated_frames.append(modified_frame)

                # Save as animated GIF
                animated_frames[0].save(
                    output_path,
                    save_all=True,
                    append_images=animated_frames[1:],
                    duration=1000,  # 1 second per frame
                    loop=0,
                    optimize=True,
                )

            logger.info(f"Radar animation created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create radar animation: {e}")
            return None

    def generate_current_weather_image(self, weather_data: WeatherData) -> Path | None:
        """Generate an image showing current weather conditions with radar.

        Args:
            weather_data: Current weather data

        Returns:
            Path to generated image file, or None if failed
        """
        try:
            # Create image
            image = Image.new(
                "RGB", (self.image_width, self.image_height), self.colors["background"]
            )
            draw = ImageDraw.Draw(image)

            # Get fonts - increase sizes for better readability
            title_font = self._get_font(self.font_size_large + 8)  # 56px
            main_font = self._get_font(self.font_size_medium + 6)  # 42px
            detail_font = self._get_font(self.font_size_small + 4)  # 28px
            self._get_font(self.font_size_tiny + 2)  # 20px

            # Calculate layout dimensions
            # Left side (weather info): 1/4 of width
            # Right side (radar): 3/4 of width
            left_width = self.image_width // 4
            radar_width = self.image_width - left_width

            # Title spans full width
            title = "Current Weather"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.image_width - title_width) // 2
            self._draw_text_with_background(
                draw,
                title,
                (title_x, 50),
                title_font,
                self.colors["text"],
                self.colors["border"],
            )

            # Layout - Redesigned with proper grid system
            left_x = 50
            y_start = 150

            # Define layout constants
            icon_column_width = 60  # Fixed width for icon column
            text_column_start = (
                left_x + icon_column_width + 20
            )  # Text starts after icon column + padding
            line_height = 70  # Consistent line height for all rows

            # TOP SECTION: Weather Icon + Temperature
            # Weather icon (centered above temperature number)
            temp_x = text_column_start
            temp_y = y_start + 20
            temp_text = f"{weather_data.temperature:.1f}{'°F' if self.units == 'imperial' else '°C'}"

            # Calculate center position above temperature text
            temp_bbox = draw.textbbox((0, 0), temp_text, font=main_font)
            temp_width = temp_bbox[2] - temp_bbox[0]
            icon_x = int(
                temp_x + (temp_width // 2) - 40
            )  # Center 80px icon above temperature text
            icon_y = y_start - 60  # Keep the same height
            self._draw_weather_icon(draw, weather_data.icon, (icon_x, icon_y), 80)

            # Main temp (below weather icon)
            self._draw_text_with_background(
                draw, temp_text, (temp_x, temp_y), main_font, self.colors["highlight"]
            )

            # Thermometer graphic (to the LEFT of temp text)
            thermo_x = temp_x - 50  # Position to the left of temperature text
            thermo_y = temp_y - 10
            self._draw_thermometer(
                draw, weather_data.temperature, (thermo_x, thermo_y), (30, 80)
            )

            # Weather description (below temperature, to the right of weather icon)
            desc_x = text_column_start
            desc_y = y_start + 100
            desc_text = weather_data.description.title()
            self._draw_text_with_background(
                draw, desc_text, (desc_x, desc_y), detail_font, self.colors["text"]
            )

            # DETAILS SECTION: Organized grid with icons and text
            details_start_y = y_start + 180
            icon_size = 45

            if self.units == "imperial":
                feels_like_text = f"Feels like: {weather_data.feels_like:.1f}°F"
                wind_text = f"Wind: {weather_data.wind_speed:.1f} mph"
                visibility_text = f"Visibility: {weather_data.visibility // 1609} mi"
            else:
                feels_like_text = f"Feels like: {weather_data.feels_like:.1f}°C"
                wind_text = f"Wind: {weather_data.wind_speed:.1f} m/s"
                visibility_text = f"Visibility: {weather_data.visibility // 1000} km"

            details = [
                ("Feels like", feels_like_text, weather_data.feels_like),
                ("Humidity", f"{weather_data.humidity}%", weather_data.humidity),
                ("Pressure", f"{weather_data.pressure} hPa", weather_data.pressure),
                ("Wind", wind_text, weather_data.wind_speed),
                ("Visibility", visibility_text, weather_data.visibility),
            ]

            for i, (label, text, value) in enumerate(details):
                y_pos = details_start_y + i * line_height

                # Icon position (left column, centered)
                icon_x = left_x + (icon_column_width - icon_size) // 2
                icon_y = y_pos - 5

                # Draw icon based on detail type
                if "Feels like" in label:
                    # Small thermometer for feels like
                    self._draw_thermometer(draw, value, (icon_x, icon_y), (30, 50))
                elif "Humidity" in label:
                    # Humidity droplet
                    self._draw_humidity_icon(
                        draw, int(value), (icon_x, icon_y), icon_size
                    )
                elif "Pressure" in label:
                    # Pressure barometer
                    self._draw_pressure_icon(
                        draw, int(value), (icon_x, icon_y), icon_size
                    )
                elif "Wind" in label:
                    # Wind direction and speed
                    self._draw_wind_icon(
                        draw,
                        value,
                        weather_data.wind_direction,
                        (icon_x, icon_y),
                        icon_size,
                    )
                elif "Visibility" in label:
                    # Visibility mountains
                    self._draw_visibility_icon(
                        draw, int(value), (icon_x, icon_y), icon_size
                    )

                # Text position (right column)
                if "Pressure" in label:
                    # Add trend information to pressure text
                    trend_text = self.get_pressure_trend_text(int(value))
                    self.get_pressure_trend_color(int(value))
                    pressure_text = f"{text} ({trend_text})"

                    # Draw pressure value with trend
                    self._draw_text_with_background(
                        draw,
                        pressure_text,
                        (text_column_start, y_pos),
                        detail_font,
                        self.colors["text"],
                    )
                else:
                    self._draw_text_with_background(
                        draw,
                        text,
                        (text_column_start, y_pos),
                        detail_font,
                        self.colors["text"],
                    )

            # SUNRISE/SUNSET SECTION: Icons + Text in same grid
            sunrise_sunset_start_y = details_start_y + 5 * line_height + 20
            sunrise_y = sunrise_sunset_start_y
            sunset_y = sunrise_sunset_start_y + line_height

            # Sunrise icon and text
            sunrise_icon_x = left_x + (icon_column_width - 35) // 2
            sunrise_icon_y = sunrise_y - 5
            draw.ellipse(
                [
                    sunrise_icon_x,
                    sunrise_icon_y,
                    sunrise_icon_x + 35,
                    sunrise_icon_y + 35,
                ],
                fill=(255, 255, 0),
                outline=(255, 165, 0),
                width=2,
            )

            sunrise_text = f"Sunrise: {weather_data.sunrise.strftime('%H:%M')}"
            self._draw_text_with_background(
                draw,
                sunrise_text,
                (text_column_start, sunrise_y),
                detail_font,
                self.colors["accent"],
            )

            # Sunset icon and text
            sunset_icon_x = left_x + (icon_column_width - 35) // 2
            sunset_icon_y = sunset_y - 5
            draw.ellipse(
                [sunset_icon_x, sunset_icon_y, sunset_icon_x + 35, sunset_icon_y + 35],
                fill=(200, 200, 200),
                outline=(100, 100, 100),
                width=2,
            )

            sunset_text = f"Sunset: {weather_data.sunset.strftime('%H:%M')}"
            self._draw_text_with_background(
                draw,
                sunset_text,
                (text_column_start, sunset_y),
                detail_font,
                self.colors["accent"],
            )

            # RIGHT SIDE - Large Radar Section (3/4 width, full height)
            # Calculate equal margins for radar positioning
            radar_margin = 50  # Equal margin on all sides
            radar_x = (
                left_width + radar_margin
            )  # Start after left section with equal margin
            radar_y = 120  # Start below title

            # Calculate radar dimensions to fit the right section with equal margins
            radar_section_width = radar_width - (
                radar_margin * 2
            )  # Equal left/right margins
            radar_section_height = (
                self.image_height - radar_y - radar_margin
            )  # Equal top/bottom margins

            # Try to add radar image
            radar_path = self.output_folder / "radar_animation.gif"
            if radar_path.exists():
                try:
                    radar_img = Image.open(radar_path)

                    # Resize radar to fit the large section while maintaining aspect ratio
                    radar_img = radar_img.resize(
                        (radar_section_width, radar_section_height),
                        Image.Resampling.LANCZOS,
                    )

                    # Paste radar image (no title)
                    image.paste(radar_img, (radar_x, radar_y))

                    # Add radar border
                    border_rect = [
                        radar_x - 3,
                        radar_y - 3,
                        radar_x + radar_section_width + 3,
                        radar_y + radar_section_height + 3,
                    ]
                    draw.rectangle(border_rect, outline=self.colors["border"], width=3)

                    # Add location label on radar
                    location_font = self._get_font(self.font_size_small)
                    location_text = "Boston/New England Radar - Last 8 Min"
                    self._draw_text_with_background(
                        draw,
                        location_text,
                        (radar_x + 20, radar_y + 20),
                        location_font,
                        (255, 255, 255),
                        (0, 0, 0),
                    )

                    logger.info(
                        f"Large radar image added: {radar_section_width}x{radar_section_height}"
                    )

                except Exception as e:
                    logger.warning(f"Failed to add radar to weather slide: {e}")
            else:
                # Add placeholder if no radar available
                placeholder_text = "Radar Unavailable"
                placeholder_bbox = draw.textbbox(
                    (0, 0), placeholder_text, font=main_font
                )
                placeholder_width = placeholder_bbox[2] - placeholder_bbox[0]
                placeholder_x = radar_x + (radar_section_width - placeholder_width) // 2
                placeholder_y = radar_y + (radar_section_height // 2)
                self._draw_text_with_background(
                    draw,
                    placeholder_text,
                    (placeholder_x, placeholder_y),
                    main_font,
                    self.colors["text"],
                )

            # Save image
            output_path = self.output_folder / "current_weather.png"
            image.save(output_path, "PNG")
            logger.info(f"Current weather image generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate current weather image: {e}")
            return None

    def generate_forecast_image(self, forecasts: list[ForecastData]) -> Path | None:
        """Generate an enhanced image showing weather forecast with visual improvements.

        Args:
            forecasts: List of forecast data

        Returns:
            Path to generated image file, or None if failed
        """
        try:
            # Create image
            image = Image.new(
                "RGB", (self.image_width, self.image_height), self.colors["background"]
            )
            draw = ImageDraw.Draw(image)

            # Get fonts
            title_font = self._get_font(self.font_size_large)
            day_font = self._get_font(self.font_size_medium)
            self._get_font(self.font_size_small * 2)  # Double the temperature font size
            detail_font = self._get_font(
                self.font_size_tiny * 2
            )  # Double the detail font size
            small_font = self._get_font(
                self.font_size_tiny
            )  # Keep small font for footer
            # New: Large value font for temps and percentages
            large_value_font = self._get_font(int(self.font_size_tiny * 3))

            # Title
            title = "5-Day Forecast"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.image_width - title_width) // 2
            self._draw_text_with_background(
                draw, title, (title_x, 30), title_font, self.colors["text"]
            )

            # Calculate layout
            num_days = len(forecasts)
            day_width = (self.image_width - 200) // num_days
            start_x = 100
            start_y = 120

            # Day column background colors (alternating)
            column_colors = [
                (240, 248, 255),  # AliceBlue
                (245, 245, 245),  # LightGray
                (240, 248, 255),  # AliceBlue
                (245, 245, 245),  # LightGray
                (240, 248, 255),  # AliceBlue
            ]

            # Get current date for highlighting today
            today = datetime.now().date()

            for i, forecast in enumerate(forecasts):
                x = start_x + i * day_width
                column_center_x = x + day_width // 2  # Center of the column

                # Day column background
                column_color = column_colors[i % len(column_colors)]
                is_today = forecast.date.date() == today

                # Highlight today with a border
                if is_today:
                    # Draw border around today's column
                    border_color = (255, 140, 0)  # DarkOrange
                    draw.rectangle(
                        [x - 5, start_y - 5, x + day_width + 5, start_y + 820],
                        outline=border_color,
                        width=3,
                    )

                # Draw column background
                draw.rectangle(
                    [x, start_y, x + day_width, start_y + 820],
                    fill=column_color,
                    outline=(200, 200, 200),
                    width=1,
                )

                # Day name (bold, large) - centered
                day_name = forecast.date.strftime("%a")
                day_bbox = draw.textbbox((0, 0), day_name, font=day_font)
                day_width_text = day_bbox[2] - day_bbox[0]
                day_x = column_center_x - day_width_text // 2
                self._draw_text_with_background(
                    draw, day_name, (day_x, start_y + 20), day_font, self.colors["text"]
                )

                # Date - centered
                date_text = forecast.date.strftime("%m/%d")
                date_bbox = draw.textbbox((0, 0), date_text, font=detail_font)
                date_width_text = date_bbox[2] - date_bbox[0]
                date_x = column_center_x - date_width_text // 2
                self._draw_text_with_background(
                    draw,
                    date_text,
                    (date_x, start_y + 80),
                    detail_font,
                    self.colors["accent"],
                )

                # Use a single font size for all items below the date
                unified_font = detail_font

                # Large weather icon with background - centered
                icon_size = 60
                icon_x = column_center_x - icon_size // 2
                icon_y = start_y + 120
                circle_center = (icon_x + icon_size // 2, icon_y + icon_size // 2)
                circle_radius = 35
                draw.ellipse(
                    [
                        circle_center[0] - circle_radius,
                        circle_center[1] - circle_radius,
                        circle_center[0] + circle_radius,
                        circle_center[1] + circle_radius,
                    ],
                    fill=(255, 255, 255),
                    outline=(200, 200, 200),
                    width=2,
                )
                self._draw_weather_icon(
                    draw, forecast.icon, (icon_x, icon_y), icon_size
                )

                # Max temperature label - centered
                max_label = "Max"
                max_label_bbox = draw.textbbox((0, 0), max_label, font=unified_font)
                max_label_width = max_label_bbox[2] - max_label_bbox[0]
                max_label_x = column_center_x - max_label_width // 2
                self._draw_text_with_background(
                    draw,
                    max_label,
                    (max_label_x, start_y + 200),
                    unified_font,
                    self.colors["text"],
                )

                # High temperature (big, colored) - centered, use large_value_font
                if self.units == "imperial":
                    high_text = f"{forecast.temperature_max:.0f}°F"
                else:
                    high_text = f"{forecast.temperature_max:.0f}°C"
                high_bbox = draw.textbbox((0, 0), high_text, font=large_value_font)
                high_width_text = high_bbox[2] - high_bbox[0]
                high_x = column_center_x - high_width_text // 2
                self._draw_text_with_background(
                    draw,
                    high_text,
                    (high_x, start_y + 230),
                    large_value_font,
                    self.colors["highlight"],
                )

                # Min temperature label - centered
                min_label = "Min"
                min_label_bbox = draw.textbbox((0, 0), min_label, font=unified_font)
                min_label_width = min_label_bbox[2] - min_label_bbox[0]
                min_label_x = column_center_x - min_label_width // 2
                self._draw_text_with_background(
                    draw,
                    min_label,
                    (min_label_x, start_y + 300),
                    unified_font,
                    self.colors["text"],
                )

                # Low temperature (smaller, blue) - centered, use large_value_font
                if self.units == "imperial":
                    low_text = f"{forecast.temperature_min:.0f}°F"
                else:
                    low_text = f"{forecast.temperature_min:.0f}°C"
                low_bbox = draw.textbbox((0, 0), low_text, font=large_value_font)
                low_width_text = low_bbox[2] - low_bbox[0]
                low_x = column_center_x - low_width_text // 2
                self._draw_text_with_background(
                    draw,
                    low_text,
                    (low_x, start_y + 330),
                    large_value_font,
                    (70, 130, 180),
                )

                # Precipitation probability with raindrop icon - centered, use large_value_font for %
                if forecast.precipitation_probability > 0:
                    raindrop_size = 15
                    pop_text = f"{forecast.precipitation_probability:.0f}%"
                    pop_bbox = draw.textbbox((0, 0), pop_text, font=large_value_font)
                    pop_width_text = pop_bbox[2] - pop_bbox[0]

                    # Calculate total width of icon + text + spacing
                    total_width = raindrop_size + 5 + pop_width_text
                    start_x_pos = column_center_x - total_width // 2

                    raindrop_x = start_x_pos
                    raindrop_y = start_y + 400
                    self._draw_raindrop_icon(
                        draw, (raindrop_x, raindrop_y), raindrop_size
                    )

                    pop_x = start_x_pos + raindrop_size + 5
                    self._draw_text_with_background(
                        draw,
                        pop_text,
                        (pop_x, raindrop_y),
                        large_value_font,
                        self.colors["warning"],
                    )

                # Humidity with droplet icon - centered, use large_value_font for %
                droplet_size = 15
                humidity_text = f"{forecast.humidity}%"
                humidity_bbox = draw.textbbox(
                    (0, 0), humidity_text, font=large_value_font
                )
                humidity_width_text = humidity_bbox[2] - humidity_bbox[0]

                # Calculate total width of icon + text + spacing
                total_width = droplet_size + 5 + humidity_width_text
                start_x_pos = column_center_x - total_width // 2

                droplet_x = start_x_pos
                droplet_y = start_y + 450
                self._draw_humidity_droplet_icon(
                    draw, (droplet_x, droplet_y), droplet_size
                )

                humidity_x = start_x_pos + droplet_size + 5
                self._draw_text_with_background(
                    draw,
                    humidity_text,
                    (humidity_x, droplet_y),
                    large_value_font,
                    self.colors["accent"],
                )

                # Weather description (smaller, italic-like) - centered and wrapped to five lines if needed
                desc_text = forecast.description.title()
                # Split into five lines if too long
                max_line_length = 8
                if len(desc_text) > max_line_length:
                    # Try to split at spaces near fifths
                    words = desc_text.split()
                    if len(words) > 4:
                        fifth = len(words) // 5
                        line1 = " ".join(words[:fifth])
                        line2 = " ".join(words[fifth : 2 * fifth])
                        line3 = " ".join(words[2 * fifth : 3 * fifth])
                        line4 = " ".join(words[3 * fifth : 4 * fifth])
                        line5 = " ".join(words[4 * fifth :])
                    elif len(words) > 3:
                        quarter = len(words) // 4
                        line1 = " ".join(words[:quarter])
                        line2 = " ".join(words[quarter : 2 * quarter])
                        line3 = " ".join(words[2 * quarter : 3 * quarter])
                        line4 = " ".join(words[3 * quarter :])
                        line5 = ""
                    elif len(words) > 2:
                        third = len(words) // 3
                        line1 = " ".join(words[:third])
                        line2 = " ".join(words[third : 2 * third])
                        line3 = " ".join(words[2 * third :])
                        line4 = ""
                        line5 = ""
                    elif len(words) > 1:
                        mid = len(words) // 2
                        line1 = " ".join(words[:mid])
                        line2 = " ".join(words[mid:])
                        line3 = ""
                        line4 = ""
                        line5 = ""
                    else:
                        line1 = desc_text[:max_line_length]
                        line2 = desc_text[max_line_length : 2 * max_line_length]
                        line3 = desc_text[2 * max_line_length : 3 * max_line_length]
                        line4 = desc_text[3 * max_line_length : 4 * max_line_length]
                        line5 = desc_text[4 * max_line_length :]
                else:
                    line1 = desc_text
                    line2 = ""
                    line3 = ""
                    line4 = ""
                    line5 = ""
                # Draw all five lines, centered
                for idx, line in enumerate([line1, line2, line3, line4, line5]):
                    if line:
                        line_bbox = draw.textbbox((0, 0), line, font=unified_font)
                        line_width = line_bbox[2] - line_bbox[0]
                        line_x = column_center_x - line_width // 2
                        self._draw_text_with_background(
                            draw,
                            line,
                            (line_x, start_y + 570 + idx * 36),
                            unified_font,
                            self.colors["text"],
                        )

            # Footer with update time
            footer_text = f"Last updated: {datetime.now().strftime('%m/%d %H:%M')}"
            footer_bbox = draw.textbbox((0, 0), footer_text, font=small_font)
            footer_width = footer_bbox[2] - footer_bbox[0]
            footer_x = (self.image_width - footer_width) // 2
            self._draw_text_with_background(
                draw,
                footer_text,
                (footer_x, self.image_height - 60),
                small_font,
                self.colors["accent"],
            )

            # Save image
            output_path = self.output_folder / "forecast.png"
            image.save(output_path, "PNG")
            logger.info(f"Enhanced forecast image generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate forecast image: {e}")
            return None

    @handle_error()
    def download_radar_image(self) -> Path | None:
        """Download weather radar image.

        Returns:
            Path to downloaded radar image, or None if failed
        """
        if not self.api_key:
            logger.error("Weather API key not configured")
            return None

        try:
            # OpenWeatherMap radar URL (this is a placeholder - actual radar requires different API)
            # For now, we'll use a static radar image or weather map
            radar_url = f"https://tile.openweathermap.org/map/precipitation_new/1/1/1.png?appid={self.api_key}"

            response = requests.get(radar_url, timeout=10)
            response.raise_for_status()

            # Save radar image
            output_path = self.output_folder / "radar.png"
            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Radar image downloaded: {output_path}")
            return output_path

        except requests.RequestException as e:
            logger.error(f"Failed to download radar image: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to save radar image: {e}")
            return None

    def sync_weather_data(self) -> list[Path]:
        """Sync all weather data and generate images.

        Returns:
            List of paths to generated weather images (only current_weather.gif and forecast.png)
        """
        generated_files = []

        try:
            # Download radar frames and create animation first (stored in temp folder)
            if self.radar_enabled:
                radar_frames = self.download_radar_frames()
                if radar_frames:
                    self.create_radar_animation(radar_frames)
                    # Don't include radar_animation in slideshow - it's in temp folder

            # Create simple weather animation for slideshow (stored in temp folder)
            self.create_simple_weather_animation()
            # Don't include weather_animation in slideshow - it's in temp folder

            # Fetch current weather
            current_weather = self.fetch_current_weather()
            if current_weather:
                # Generate animated GIF with RainViewer radar
                current_gif = self.generate_current_weather_gif_with_radar(
                    current_weather, num_frames=6
                )
                if current_gif:
                    generated_files.append(current_gif)

            # Fetch forecast
            forecasts = self.fetch_forecast(5)
            if forecasts:
                forecast_image = self.generate_forecast_image(forecasts)
                if forecast_image:
                    generated_files.append(forecast_image)

            logger.info(
                f"Weather sync completed: {len(generated_files)} files generated"
            )
            return generated_files

        except Exception as e:
            logger.error(f"Weather sync failed: {e}")
            return generated_files

    def cleanup_old_files(self, max_age_hours: int = 24) -> None:
        """Clean up old weather files.

        Args:
            max_age_hours: Maximum age of files in hours before deletion
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            # Clean up main output folder
            for file_path in self.output_folder.glob("*.png"):
                if file_path.stat().st_mtime < cutoff_time.timestamp():
                    file_path.unlink()
                    logger.info(f"Deleted old weather file: {file_path}")

            # Clean up temp folder
            for file_path in self.temp_folder.glob("*"):
                if file_path.stat().st_mtime < cutoff_time.timestamp():
                    file_path.unlink()
                    logger.info(f"Deleted old temp weather file: {file_path}")

        except Exception as e:
            logger.error(f"Failed to cleanup old weather files: {e}")

    @handle_error()
    def create_simple_weather_animation(self) -> Path | None:
        """Create a simple animated weather pattern for slideshow.

        Returns:
            Path to animated GIF, or None if failed
        """
        try:
            # Create a simple animated weather pattern
            frames = []
            frame_size = (400, 300)

            # Create different weather patterns
            patterns = [
                self._create_cloud_pattern,
                self._create_sun_pattern,
                self._create_rain_pattern,
                self._create_snow_pattern,
            ]

            for pattern_func in patterns:
                frame = pattern_func(frame_size)
                frames.append(frame)

            # Create animated GIF
            output_path = self.temp_folder / "weather_animation.gif"

            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=1500,  # 1.5 seconds per frame
                loop=0,
                optimize=True,
            )

            logger.info(f"Weather animation created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create weather animation: {e}")
            return None

    def _create_cloud_pattern(self, size: tuple[int, int]) -> Image.Image:
        """Create a cloud pattern frame."""
        image = Image.new("RGB", size, (135, 206, 235))  # Sky blue
        draw = ImageDraw.Draw(image)

        # Draw clouds
        cloud_color = (255, 255, 255)
        for i in range(3):
            x = 50 + i * 120
            y = 100 + (i % 2) * 20
            # Simple cloud shape
            draw.ellipse([x, y, x + 80, y + 60], fill=cloud_color)
            draw.ellipse([x + 20, y - 20, x + 100, y + 40], fill=cloud_color)
            draw.ellipse([x + 40, y + 20, x + 120, y + 80], fill=cloud_color)

        return image

    def _create_sun_pattern(self, size: tuple[int, int]) -> Image.Image:
        """Create a sun pattern frame."""
        image = Image.new("RGB", size, (135, 206, 235))  # Sky blue
        draw = ImageDraw.Draw(image)

        # Draw sun
        sun_center = (size[0] // 2, size[1] // 3)
        sun_radius = 40
        draw.ellipse(
            [
                sun_center[0] - sun_radius,
                sun_center[1] - sun_radius,
                sun_center[0] + sun_radius,
                sun_center[1] + sun_radius,
            ],
            fill=(255, 255, 0),
        )  # Yellow sun

        # Draw sun rays
        ray_length = 20
        for angle in range(0, 360, 45):
            rad = angle * 3.14159 / 180
            start_x = sun_center[0] + int(sun_radius * 1.2 * math.cos(rad))
            start_y = sun_center[1] + int(sun_radius * 1.2 * math.sin(rad))
            end_x = start_x + int(ray_length * math.cos(rad))
            end_y = start_y + int(ray_length * math.sin(rad))
            draw.line([start_x, start_y, end_x, end_y], fill=(255, 255, 0), width=3)

        return image

    def _create_rain_pattern(self, size: tuple[int, int]) -> Image.Image:
        """Create a rain pattern frame."""
        image = Image.new("RGB", size, (105, 105, 105))  # Dark gray
        draw = ImageDraw.Draw(image)

        # Draw clouds
        cloud_color = (169, 169, 169)
        draw.ellipse([50, 50, 350, 120], fill=cloud_color)

        # Draw rain drops
        rain_color = (0, 191, 255)  # Deep sky blue
        for i in range(20):
            x = 50 + (i * 15) % 300
            y = 130 + (i * 10) % 150
            draw.line([x, y, x + 2, y + 8], fill=rain_color, width=2)

        return image

    def _create_snow_pattern(self, size: tuple[int, int]) -> Image.Image:
        """Create a snow pattern frame."""
        image = Image.new("RGB", size, (240, 248, 255))  # Alice blue
        draw = ImageDraw.Draw(image)

        # Draw clouds
        cloud_color = (220, 220, 220)
        draw.ellipse([50, 50, 350, 120], fill=cloud_color)

        # Draw snowflakes
        snow_color = (255, 255, 255)
        for i in range(15):
            x = 50 + (i * 20) % 300
            y = 130 + (i * 15) % 150
            # Simple snowflake
            draw.line([x, y, x, y + 6], fill=snow_color, width=2)
            draw.line([x - 3, y + 3, x + 3, y + 3], fill=snow_color, width=2)

        return image

    @handle_error()
    def generate_current_weather_gif_with_radar(
        self, weather_data: WeatherData, num_frames: int = 6
    ) -> Path | None:
        """Generate an animated GIF showing current weather with animated radar.
        Args:
            weather_data: Current weather data
            num_frames: Number of radar frames to use (default: 6, ~last hour)
        Returns:
            Path to generated GIF file, or None if failed
        """
        import io

        import requests
        from PIL import Image

        try:
            # Use NOAA KBOX (Boston/Taunton, MA) local radar images for a zoomed-in New England view
            # These provide a much more focused area: eastern MA, southern NH, northern RI/CT
            radar_urls = [
                "https://radar.weather.gov/ridge/standard/KBOX_0.gif",  # most recent
                "https://radar.weather.gov/ridge/standard/KBOX_2.gif",
                "https://radar.weather.gov/ridge/standard/KBOX_4.gif",
                "https://radar.weather.gov/ridge/standard/KBOX_6.gif",
                "https://radar.weather.gov/ridge/standard/KBOX_8.gif",
            ]

            # Download NOAA radar images (these already have map backgrounds)
            radar_imgs = []
            for i, url in enumerate(radar_urls[:num_frames]):
                try:
                    response = requests.get(url, timeout=15)
                    if response.status_code == 200:
                        radar_img = Image.open(io.BytesIO(response.content)).convert(
                            "RGB"
                        )
                        radar_imgs.append(radar_img)
                        logger.info(f"NOAA radar frame {i+1} downloaded successfully")
                    else:
                        logger.warning(
                            f"Failed to download NOAA radar frame {i+1}: status {response.status_code}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to download NOAA radar frame {i+1}: {e}")
                    continue

            if not radar_imgs:
                logger.error("No NOAA radar frames downloaded")
                return None

            # For each radar frame, generate a weather slide with that radar
            frames = []
            for radar_img in radar_imgs:
                # Create base image
                image = Image.new(
                    "RGB",
                    (self.image_width, self.image_height),
                    self.colors["background"],
                )
                draw = ImageDraw.Draw(image)

                # Get fonts (use larger sizes)
                title_font = self._get_font(self.font_size_large + 8)
                main_font = self._get_font(self.font_size_medium + 6)
                detail_font = self._get_font(self.font_size_small + 4)

                # Layout - Redesigned with proper grid system
                left_x = 50
                y_start = 150

                # Define layout constants
                icon_column_width = 60  # Fixed width for icon column
                text_column_start = (
                    left_x + icon_column_width + 20
                )  # Text starts after icon column + padding
                line_height = 70  # Consistent line height for all rows

                # TOP SECTION: Weather Icon + Temperature
                # Weather icon (centered above temperature number)
                temp_x = text_column_start
                temp_y = y_start + 20
                temp_text = f"{weather_data.temperature:.1f}{'°F' if self.units == 'imperial' else '°C'}"

                # Calculate center position above temperature text
                temp_bbox = draw.textbbox((0, 0), temp_text, font=main_font)
                temp_width = temp_bbox[2] - temp_bbox[0]
                icon_x = int(
                    temp_x + (temp_width // 2) - 40
                )  # Center 80px icon above temperature text
                icon_y = y_start - 60  # Keep the same height
                self._draw_weather_icon(draw, weather_data.icon, (icon_x, icon_y), 80)

                # Main temp (below weather icon)
                self._draw_text_with_background(
                    draw,
                    temp_text,
                    (temp_x, temp_y),
                    main_font,
                    self.colors["highlight"],
                )

                # Thermometer graphic (to the LEFT of temp text)
                thermo_x = temp_x - 50  # Position to the left of temperature text
                thermo_y = temp_y - 10
                self._draw_thermometer(
                    draw, weather_data.temperature, (thermo_x, thermo_y), (30, 80)
                )

                # Weather description (below temperature, to the right of weather icon)
                desc_x = text_column_start
                desc_y = y_start + 100
                desc_text = weather_data.description.title()
                self._draw_text_with_background(
                    draw, desc_text, (desc_x, desc_y), detail_font, self.colors["text"]
                )

                # DETAILS SECTION: Organized grid with icons and text
                details_start_y = y_start + 180
                icon_size = 45

                if self.units == "imperial":
                    feels_like_text = f"Feels like: {weather_data.feels_like:.1f}°F"
                    wind_text = f"Wind: {weather_data.wind_speed:.1f} mph"
                    visibility_text = (
                        f"Visibility: {weather_data.visibility // 1609} mi"
                    )
                else:
                    feels_like_text = f"Feels like: {weather_data.feels_like:.1f}°C"
                    wind_text = f"Wind: {weather_data.wind_speed:.1f} m/s"
                    visibility_text = (
                        f"Visibility: {weather_data.visibility // 1000} km"
                    )

                details = [
                    ("Feels like", feels_like_text, weather_data.feels_like),
                    ("Humidity", f"{weather_data.humidity}%", weather_data.humidity),
                    ("Pressure", f"{weather_data.pressure} hPa", weather_data.pressure),
                    ("Wind", wind_text, weather_data.wind_speed),
                    ("Visibility", visibility_text, weather_data.visibility),
                ]

                for i, (label, text, value) in enumerate(details):
                    y_pos = details_start_y + i * line_height

                    # Icon position (left column, centered)
                    icon_x = left_x + (icon_column_width - icon_size) // 2
                    icon_y = y_pos - 5

                    # Draw icon based on detail type
                    if "Feels like" in label:
                        # Small thermometer for feels like
                        self._draw_thermometer(draw, value, (icon_x, icon_y), (30, 50))
                    elif "Humidity" in label:
                        # Humidity droplet
                        self._draw_humidity_icon(
                            draw, int(value), (icon_x, icon_y), icon_size
                        )
                    elif "Pressure" in label:
                        # Pressure barometer
                        self._draw_pressure_icon(
                            draw, int(value), (icon_x, icon_y), icon_size
                        )
                    elif "Wind" in label:
                        # Wind direction and speed
                        self._draw_wind_icon(
                            draw,
                            value,
                            weather_data.wind_direction,
                            (icon_x, icon_y),
                            icon_size,
                        )
                    elif "Visibility" in label:
                        # Visibility mountains
                        self._draw_visibility_icon(
                            draw, int(value), (icon_x, icon_y), icon_size
                        )

                    # Text position (right column)
                    if "Pressure" in label:
                        # Add trend information to pressure text
                        trend_text = self.get_pressure_trend_text(int(value))
                        self.get_pressure_trend_color(int(value))
                        pressure_text = f"{text} ({trend_text})"

                        # Draw pressure value with trend
                        self._draw_text_with_background(
                            draw,
                            pressure_text,
                            (text_column_start, y_pos),
                            detail_font,
                            self.colors["text"],
                        )
                    else:
                        self._draw_text_with_background(
                            draw,
                            text,
                            (text_column_start, y_pos),
                            detail_font,
                            self.colors["text"],
                        )

                # SUNRISE/SUNSET SECTION: Icons + Text in same grid
                sunrise_sunset_start_y = details_start_y + 5 * line_height + 20
                sunrise_y = sunrise_sunset_start_y
                sunset_y = sunrise_sunset_start_y + line_height

                # Sunrise icon and text
                sunrise_icon_x = left_x + (icon_column_width - 35) // 2
                sunrise_icon_y = sunrise_y - 5
                draw.ellipse(
                    [
                        sunrise_icon_x,
                        sunrise_icon_y,
                        sunrise_icon_x + 35,
                        sunrise_icon_y + 35,
                    ],
                    fill=(255, 255, 0),
                    outline=(255, 165, 0),
                    width=2,
                )

                sunrise_text = f"Sunrise: {weather_data.sunrise.strftime('%H:%M')}"
                self._draw_text_with_background(
                    draw,
                    sunrise_text,
                    (text_column_start, sunrise_y),
                    detail_font,
                    self.colors["accent"],
                )

                # Sunset icon and text
                sunset_icon_x = left_x + (icon_column_width - 35) // 2
                sunset_icon_y = sunset_y - 5
                draw.ellipse(
                    [
                        sunset_icon_x,
                        sunset_icon_y,
                        sunset_icon_x + 35,
                        sunset_icon_y + 35,
                    ],
                    fill=(200, 200, 200),
                    outline=(100, 100, 100),
                    width=2,
                )

                sunset_text = f"Sunset: {weather_data.sunset.strftime('%H:%M')}"
                self._draw_text_with_background(
                    draw,
                    sunset_text,
                    (text_column_start, sunset_y),
                    detail_font,
                    self.colors["accent"],
                )

                # Radar section (right 3/4) - NOAA images already have map backgrounds
                left_width = self.image_width // 4
                radar_width = self.image_width - left_width
                radar_margin = 50
                radar_x = left_width + radar_margin
                radar_y = 120
                radar_section_width = radar_width - (radar_margin * 2)
                radar_section_height = self.image_height - radar_y - radar_margin

                # Resize NOAA radar image to fit radar section
                radar_resized = radar_img.resize(
                    (radar_section_width, radar_section_height),
                    Image.Resampling.LANCZOS,
                )

                # Paste the NOAA radar image (which already includes map background)
                image.paste(radar_resized, (radar_x, radar_y))

                # Add border around radar section
                border_rect = [
                    radar_x - 3,
                    radar_y - 3,
                    radar_x + radar_section_width + 3,
                    radar_y + radar_section_height + 3,
                ]
                draw.rectangle(border_rect, outline=self.colors["border"], width=3)

                # Add location label on radar
                location_font = self._get_font(self.font_size_small)
                location_text = "Boston/New England Radar - Last 8 Min"
                self._draw_text_with_background(
                    draw,
                    location_text,
                    (radar_x + 20, radar_y + 20),
                    location_font,
                    (255, 255, 255),
                    (0, 0, 0),
                )

                # Title (top)
                title = "Current Weather"
                title_font = self._get_font(self.font_size_large + 8)
                title_bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = (self.image_width - title_width) // 2
                self._draw_text_with_background(
                    draw, title, (title_x, 50), title_font, self.colors["text"]
                )

                frames.append(image)

            # Save as animated GIF
            output_path = self.output_folder / "current_weather.gif"
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=400,  # ms per frame
                loop=0,
                optimize=True,
            )
            logger.info(
                f"Animated current weather GIF with NOAA radar (includes map background) generated: {output_path}"
            )
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate animated current weather GIF: {e}")
            return None

    def _draw_weather_icon(
        self, draw: Any, icon_code: str, position: tuple[int, int], size: int = 60
    ) -> None:
        """Draw a weather icon based on the OpenWeatherMap icon code."""
        x, y = position

        # Weather icon mapping
        icon_map = {
            # Clear sky
            "01d": "☀️",
            "01n": "🌙",
            # Few clouds
            "02d": "⛅",
            "02n": "☁️",
            # Scattered clouds
            "03d": "☁️",
            "03n": "☁️",
            # Broken clouds
            "04d": "☁️",
            "04n": "☁️",
            # Shower rain
            "09d": "🌧️",
            "09n": "🌧️",
            # Rain
            "10d": "🌦️",
            "10n": "🌧️",
            # Thunderstorm
            "11d": "⛈️",
            "11n": "⛈️",
            # Snow
            "13d": "🌨️",
            "13n": "🌨️",
            # Mist/Fog
            "50d": "🌫️",
            "50n": "🌫️",
        }

        # Get icon or use default
        icon_map.get(icon_code, "🌤️")

        # For now, we'll draw simple shapes since emoji rendering can be complex
        # Draw a simple weather icon based on the code
        if "01" in icon_code:  # Clear sky
            # Draw sun
            draw.ellipse(
                [x, y, x + size, y + size],
                fill=(255, 255, 0),
                outline=(255, 165, 0),
                width=2,
            )
            # Draw sun rays
            for angle in range(0, 360, 45):
                rad = angle * 3.14159 / 180
                start_x = x + size // 2 + int(size // 3 * math.cos(rad))
                start_y = y + size // 2 + int(size // 3 * math.sin(rad))
                end_x = start_x + int(size // 6 * math.cos(rad))
                end_y = start_y + int(size // 6 * math.sin(rad))
                draw.line([start_x, start_y, end_x, end_y], fill=(255, 165, 0), width=3)
        elif "02" in icon_code:  # Few clouds
            # Draw sun with clouds
            draw.ellipse(
                [x + size // 4, y + size // 4, x + 3 * size // 4, y + 3 * size // 4],
                fill=(255, 255, 0),
            )
            draw.ellipse(
                [x, y + size // 3, x + 2 * size // 3, y + size], fill=(200, 200, 200)
            )
        elif "03" in icon_code or "04" in icon_code:  # Clouds
            # Draw multiple clouds
            draw.ellipse(
                [x, y + size // 4, x + 2 * size // 3, y + 3 * size // 4],
                fill=(200, 200, 200),
            )
            draw.ellipse(
                [x + size // 3, y, x + size, y + 2 * size // 3], fill=(180, 180, 180)
            )
        elif "09" in icon_code or "10" in icon_code:  # Rain
            # Draw cloud with rain
            draw.ellipse([x, y, x + 2 * size // 3, y + size // 2], fill=(150, 150, 150))
            for i in range(5):
                rain_x = x + size // 6 + i * size // 6
                rain_y = y + size // 2
                draw.line(
                    [rain_x, rain_y, rain_x - 2, rain_y + size // 3],
                    fill=(0, 191, 255),
                    width=2,
                )
        elif "11" in icon_code:  # Thunderstorm
            # Draw cloud with lightning
            draw.ellipse([x, y, x + 2 * size // 3, y + size // 2], fill=(100, 100, 100))
            # Lightning bolt
            lightning_points = [
                x + size // 2,
                y + size // 3,
                x + size // 3,
                y + size // 2,
                x + size // 2,
                y + size,
            ]
            draw.polygon(lightning_points, fill=(255, 255, 0))
        elif "13" in icon_code:  # Snow
            # Draw cloud with snow
            draw.ellipse([x, y, x + 2 * size // 3, y + size // 2], fill=(220, 220, 220))
            for i in range(6):
                snow_x = x + size // 6 + i * size // 6
                snow_y = y + size // 2
                # Snowflake
                draw.line(
                    [snow_x, snow_y, snow_x, snow_y + size // 4],
                    fill=(255, 255, 255),
                    width=2,
                )
                draw.line(
                    [snow_x - 2, snow_y + size // 8, snow_x + 2, snow_y + size // 8],
                    fill=(255, 255, 255),
                    width=2,
                )
        elif "50" in icon_code:  # Mist/Fog
            # Draw fog
            for i in range(3):
                fog_y = y + size // 4 + i * size // 6
                draw.ellipse(
                    [x, fog_y, x + size, fog_y + size // 8], fill=(200, 200, 200, 100)
                )
        else:
            # Default: simple sun
            draw.ellipse([x, y, x + size, y + size], fill=(255, 255, 0))

    def _draw_thermometer(
        self,
        draw: Any,
        temperature: float,
        position: tuple[int, int],
        size: tuple[int, int] = (40, 120),
    ) -> None:
        """Draw a thermometer graphic."""
        x, y = position
        width, height = size

        # Thermometer bulb
        bulb_radius = width // 2
        bulb_center = (x + width // 2, y + height - bulb_radius)
        draw.ellipse(
            [
                bulb_center[0] - bulb_radius,
                bulb_center[1] - bulb_radius,
                bulb_center[0] + bulb_radius,
                bulb_center[1] + bulb_radius,
            ],
            fill=(255, 0, 0),
            outline=(100, 0, 0),
            width=2,
        )

        # Thermometer tube
        tube_width = width // 4
        tube_x = x + (width - tube_width) // 2
        tube_y = y
        tube_height = height - bulb_radius
        draw.rectangle(
            [tube_x, tube_y, tube_x + tube_width, tube_y + tube_height],
            fill=(255, 255, 255),
            outline=(100, 100, 100),
            width=2,
        )

        # Temperature scale (simplified)
        # Map temperature to fill height (assuming -20 to 120 F range)
        temp_min, temp_max = -20, 120
        if self.units == "metric":
            temp_min, temp_max = -30, 50

        temp_ratio = max(0, min(1, (temperature - temp_min) / (temp_max - temp_min)))
        fill_height = int(tube_height * temp_ratio)

        # Fill with red
        fill_y = tube_y + tube_height - fill_height
        draw.rectangle(
            [tube_x, fill_y, tube_x + tube_width, tube_y + tube_height],
            fill=(255, 0, 0),
        )

    def _draw_wind_icon(
        self,
        draw: Any,
        wind_speed: float,
        wind_direction: int,
        position: tuple[int, int],
        size: int = 50,
    ) -> None:
        """Draw a wind icon with direction and speed."""
        x, y = position

        # Wind direction arrow
        center_x, center_y = x + size // 2, y + size // 2
        arrow_length = size // 3

        # Convert wind direction to radians (meteorological direction)
        angle_rad = math.radians(270 - wind_direction)  # Convert to screen coordinates

        # Arrow head
        arrow_end_x = center_x + int(arrow_length * math.cos(angle_rad))
        arrow_end_y = center_y + int(arrow_length * math.sin(angle_rad))

        # Draw arrow
        draw.line(
            [center_x, center_y, arrow_end_x, arrow_end_y],
            fill=(100, 100, 100),
            width=3,
        )

        # Arrow head
        head_size = 8
        head_angle1 = angle_rad + math.pi * 0.8
        head_angle2 = angle_rad - math.pi * 0.8

        head1_x = arrow_end_x + int(head_size * math.cos(head_angle1))
        head1_y = arrow_end_y + int(head_size * math.sin(head_angle1))
        head2_x = arrow_end_x + int(head_size * math.cos(head_angle2))
        head2_y = arrow_end_y + int(head_size * math.sin(head_angle2))

        draw.line(
            [arrow_end_x, arrow_end_y, head1_x, head1_y], fill=(100, 100, 100), width=2
        )
        draw.line(
            [arrow_end_x, arrow_end_y, head2_x, head2_y], fill=(100, 100, 100), width=2
        )

        # Wind speed indicator (number of lines)
        speed_lines = min(5, max(1, int(wind_speed / 5)))  # 1 line per 5 m/s
        for i in range(speed_lines):
            line_x = x + 10 + i * 8
            line_y = y + size - 15
            draw.line(
                [line_x, line_y, line_x + 6, line_y], fill=(150, 150, 150), width=2
            )

    def _draw_humidity_icon(
        self, draw: Any, humidity: int, position: tuple[int, int], size: int = 50
    ) -> None:
        """Draw a humidity icon."""
        x, y = position

        # Draw a droplet shape
        droplet_points = [
            (x + size // 2, y),  # Top point
            (x + size // 4, y + size // 3),  # Left curve
            (x + size // 2, y + size),  # Bottom point
            (x + 3 * size // 4, y + size // 3),  # Right curve
        ]

        # Fill based on humidity level
        if humidity > 80:
            fill_color = (0, 100, 200)  # Dark blue for high humidity
        elif humidity > 60:
            fill_color = (0, 150, 255)  # Medium blue
        elif humidity > 40:
            fill_color = (100, 200, 255)  # Light blue
        else:
            fill_color = (200, 220, 255)  # Very light blue for low humidity

        draw.polygon(droplet_points, fill=fill_color, outline=(0, 50, 100), width=2)

        # Add shine effect
        shine_points = [
            (x + size // 2 - 3, y + size // 4),
            (x + size // 2 - 1, y + size // 6),
            (x + size // 2 + 1, y + size // 4),
        ]
        draw.polygon(shine_points, fill=(255, 255, 255))

    def _draw_pressure_icon(
        self, draw: Any, pressure: int, position: tuple[int, int], size: int = 50
    ) -> None:
        """Draw a pressure/barometer icon with trend indicator."""
        x, y = position

        # Get pressure trend without adding to history
        if len(self.pressure_history) < 1:
            trend = "steady"
        else:
            last_pressure = self.pressure_history[-1][1]
            change = pressure - last_pressure
            if change > 1:
                trend = "rising"
            elif change < -1:
                trend = "falling"
            else:
                trend = "steady"

        # Draw a barometer dial
        center_x, center_y = x + size // 2, y + size // 2
        radius = size // 2 - 5

        # Draw dial circle
        draw.ellipse(
            [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ],
            fill=(240, 240, 240),
            outline=(100, 100, 100),
            width=2,
        )

        # Draw pressure needle
        # Normal pressure is around 1013 hPa, map to angle
        pressure_angle = (pressure - 950) / (
            1050 - 950
        ) * 180 - 90  # Map to -90 to 90 degrees
        pressure_angle = max(-90, min(90, pressure_angle))
        angle_rad = math.radians(pressure_angle)

        needle_end_x = center_x + int(radius * 0.8 * math.cos(angle_rad))
        needle_end_y = center_y + int(radius * 0.8 * math.sin(angle_rad))

        draw.line(
            [center_x, center_y, needle_end_x, needle_end_y], fill=(255, 0, 0), width=3
        )

        # Draw center dot
        draw.ellipse(
            [center_x - 3, center_y - 3, center_x + 3, center_y + 3],
            fill=(100, 100, 100),
        )

        # Draw trend indicator
        if trend == "rising":
            # Up arrow (green)
            arrow_color = (0, 150, 0)
            arrow_points = [
                (x + size - 15, y + 10),  # Top point
                (x + size - 20, y + 15),  # Left point
                (x + size - 18, y + 15),  # Left inner
                (x + size - 18, y + 20),  # Left bottom
                (x + size - 12, y + 20),  # Right bottom
                (x + size - 12, y + 15),  # Right inner
                (x + size - 10, y + 15),  # Right point
            ]
        elif trend == "falling":
            # Down arrow (red)
            arrow_color = (200, 0, 0)
            arrow_points = [
                (x + size - 15, y + 20),  # Bottom point
                (x + size - 20, y + 15),  # Left point
                (x + size - 18, y + 15),  # Left inner
                (x + size - 18, y + 10),  # Left top
                (x + size - 12, y + 10),  # Right top
                (x + size - 12, y + 15),  # Right inner
                (x + size - 10, y + 15),  # Right point
            ]
        else:
            # Steady (no arrow, just a small dot)
            arrow_color = (100, 100, 100)
            arrow_points = None

        if arrow_points:
            draw.polygon(arrow_points, fill=arrow_color, outline=(50, 50, 50), width=1)
        else:
            # Draw steady indicator (small circle)
            steady_x, steady_y = x + size - 15, y + 15
            draw.ellipse(
                [steady_x - 3, steady_y - 3, steady_x + 3, steady_y + 3],
                fill=arrow_color,
                outline=(50, 50, 50),
                width=1,
            )

    def _draw_visibility_icon(
        self, draw: Any, visibility: int, position: tuple[int, int], size: int = 50
    ) -> None:
        """Draw a visibility icon."""
        x, y = position

        # Draw mountains/horizon
        mountain_points = [
            (x, y + size),  # Bottom left
            (x + size // 4, y + size // 2),  # First peak
            (x + size // 2, y + size // 3),  # Second peak
            (x + 3 * size // 4, y + size // 2),  # Third peak
            (x + size, y + size),  # Bottom right
        ]

        # Fill based on visibility
        if visibility > 10000:  # > 10km
            fill_color = (100, 150, 100)  # Clear green
        elif visibility > 5000:  # 5-10km
            fill_color = (150, 200, 150)  # Medium green
        elif visibility > 1000:  # 1-5km
            fill_color = (200, 220, 200)  # Light green
        else:
            fill_color = (220, 220, 220)  # Gray for poor visibility

        draw.polygon(mountain_points, fill=fill_color, outline=(50, 100, 50), width=2)

        # Draw sun/moon above mountains
        sun_x, sun_y = x + size // 2, y + size // 4
        sun_radius = size // 8
        draw.ellipse(
            [
                sun_x - sun_radius,
                sun_y - sun_radius,
                sun_x + sun_radius,
                sun_y + sun_radius,
            ],
            fill=(255, 255, 0),
            outline=(255, 165, 0),
            width=1,
        )

    def _get_pressure_trend(self, current_pressure: int) -> str:
        """Determine pressure trend based on historical data.

        Args:
            current_pressure: Current pressure reading

        Returns:
            Trend string: "rising", "falling", or "steady"
        """
        # Add current reading to history
        self.pressure_history.append((datetime.now(), current_pressure))

        # Keep only recent history
        if len(self.pressure_history) > self.max_pressure_history:
            self.pressure_history = self.pressure_history[-self.max_pressure_history :]

        # Need at least 2 readings to determine trend
        if len(self.pressure_history) < 2:
            return "steady"

        # Calculate trend over last few readings
        recent_readings = self.pressure_history[-3:]  # Last 3 readings
        pressures = [reading[1] for reading in recent_readings]

        # Calculate average change
        if len(pressures) >= 2:
            changes = [
                pressures[i] - pressures[i - 1] for i in range(1, len(pressures))
            ]
            avg_change = sum(changes) / len(changes)

            # Determine trend based on average change
            if avg_change > 1:  # Rising more than 1 hPa on average
                return "rising"
            elif avg_change < -1:  # Falling more than 1 hPa on average
                return "falling"
            else:
                return "steady"

        return "steady"

    def get_pressure_trend_text(self, current_pressure: int) -> str:
        """Get pressure trend as human-readable text.

        Args:
            current_pressure: Current pressure reading

        Returns:
            Trend text: "Rising", "Falling", or "Steady"
        """
        # Calculate trend without adding current pressure to history
        if len(self.pressure_history) < 1:
            return "Steady"

        # Get the last pressure reading from history
        last_pressure = self.pressure_history[-1][1]

        # Calculate change from last reading to current
        change = current_pressure - last_pressure

        if change > 1:  # Rising more than 1 hPa
            return "Rising"
        elif change < -1:  # Falling more than 1 hPa
            return "Falling"
        else:
            return "Steady"

    def get_pressure_trend_color(self, current_pressure: int) -> tuple[int, int, int]:
        """Get color for pressure trend display.

        Args:
            current_pressure: Current pressure reading

        Returns:
            RGB color tuple
        """
        # Calculate trend without adding current pressure to history
        if len(self.pressure_history) < 1:
            return (100, 100, 100)  # Gray for steady

        # Get the last pressure reading from history
        last_pressure = self.pressure_history[-1][1]

        # Calculate change from last reading to current
        change = current_pressure - last_pressure

        if change > 1:  # Rising more than 1 hPa
            return (0, 150, 0)  # Green
        elif change < -1:  # Falling more than 1 hPa
            return (200, 0, 0)  # Red
        else:
            return (100, 100, 100)  # Gray

    def _draw_raindrop_icon(
        self, draw: Any, position: tuple[int, int], size: int = 15
    ) -> None:
        """Draw a simple raindrop icon.

        Args:
            draw: ImageDraw object
            position: (x, y) position for the icon
            size: Size of the icon
        """
        x, y = position

        # Draw raindrop shape (simple triangle with rounded bottom)
        points = [
            (x + size // 2, y),  # Top point
            (x, y + size),  # Bottom left
            (x + size, y + size),  # Bottom right
        ]

        # Fill raindrop
        draw.polygon(points, fill=(100, 150, 255))  # Light blue

        # Add a small circle at the bottom for rounded effect
        draw.ellipse(
            [
                x + size // 4,
                y + size - size // 4,
                x + 3 * size // 4,
                y + size + size // 4,
            ],
            fill=(100, 150, 255),
        )

    def _draw_humidity_droplet_icon(
        self, draw: Any, position: tuple[int, int], size: int = 15
    ) -> None:
        """Draw a simple humidity droplet icon.

        Args:
            draw: ImageDraw object
            position: (x, y) position for the icon
            size: Size of the icon
        """
        x, y = position

        # Draw droplet shape (teardrop)
        # Create a teardrop using an ellipse and a triangle

        # Main droplet body (ellipse)
        draw.ellipse([x, y, x + size, y + size], fill=(150, 200, 255))  # Light blue

        # Add a small highlight
        highlight_size = size // 3
        draw.ellipse(
            [
                x + size // 4,
                y + size // 4,
                x + size // 4 + highlight_size,
                y + size // 4 + highlight_size,
            ],
            fill=(200, 220, 255),
        )  # Lighter blue for highlight
