"""
Calendar visualization service for generating calendar images.
"""

import logging
import os
from datetime import date, datetime, timedelta
from typing import Any

import pytz
from PIL import Image, ImageDraw, ImageFont

from src.utils.error_handling import ErrorSeverity, FamilyCenterError, handle_error

logger = logging.getLogger(__name__)


class CalendarVisualizerError(FamilyCenterError):
    """Raised when there is an error with calendar visualization."""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> None:
        """Initialize the error.

        Args:
            message: Error message
            severity: Error severity
        """
        super().__init__(message, severity)


class CalendarVisualizer:
    """Calendar visualizer for generating calendar views."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the calendar visualizer with configuration."""
        self.config = config
        self.calendar_config = config.get("google_calendar", {})
        self.views_config = self.calendar_config.get("views", {})
        self.width = self.calendar_config.get("width", 1920)
        self.height = self.calendar_config.get("height", 1080)
        self.timezone = self.calendar_config.get("timezone", "America/New_York")
        self.title = self.calendar_config.get("title", "Test Calendar")
        self.fonts = self._initialize_fonts()
        self.colors = self._initialize_colors()
        # Type annotations for instance variables used in multi-day event tracking
        self._occupied_positions: dict[int, set[tuple[int, int]]]
        self._row_heights: dict[int, dict[int, int]]

    def _initialize_fonts(self) -> dict[str, Any]:
        """Initialize fonts with sizes from config."""
        # Get the absolute path to the media/fonts directory
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "media",
            "fonts",
            "roboto",
            "static",
        )

        def _load_font(font_path: str, size: int) -> Any:
            """Load font with fallback to default font."""
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
                else:
                    # Fallback to default font
                    return ImageFont.load_default()
            except OSError:
                # Fallback to default font if loading fails
                return ImageFont.load_default()

        return {
            "title": _load_font(os.path.join(base_path, "Roboto-Bold.ttf"), 60),
            "header": _load_font(os.path.join(base_path, "Roboto-Bold.ttf"), 40),
            "day": _load_font(os.path.join(base_path, "Roboto-Bold.ttf"), 50),
            "time": _load_font(os.path.join(base_path, "Roboto-Regular.ttf"), 34),
            "event": _load_font(os.path.join(base_path, "Roboto-Regular.ttf"), 35),
            "all_day": _load_font(os.path.join(base_path, "Roboto-Regular.ttf"), 35),
        }

    def _initialize_colors(self) -> dict[str, tuple[int, int, int]]:
        """Initialize colors from config or use defaults."""
        # Get colors from config
        config_colors = self.calendar_config.get("colors", {})

        def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
            """Convert hex color string to RGB tuple."""
            hex_color = hex_color.lstrip("#")
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            return rgb[0], rgb[1], rgb[2]

        # Default colors
        default_colors = {
            "background": (255, 255, 255),
            "text": (0, 0, 0),
            "header": (0, 0, 0),
            "border": (200, 200, 200),
        }

        # Override with config colors if provided
        colors = default_colors.copy()
        for color_key, color_value in config_colors.items():
            if isinstance(color_value, str) and color_value.startswith("#"):
                try:
                    colors[color_key] = _hex_to_rgb(color_value)
                except (ValueError, IndexError):
                    # If hex conversion fails, keep default
                    logger.warning(
                        f"Invalid hex color '{color_value}' for '{color_key}', using default"
                    )
            elif isinstance(color_value, list | tuple) and len(color_value) == 3:
                # Already in RGB format
                colors[color_key] = tuple(color_value)

        return colors

    def _create_base_image(
        self, is_weekly: bool = True
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Create base image with title."""
        image = Image.new("RGB", (self.width, self.height), self.colors["background"])
        draw = ImageDraw.Draw(image)

        # Draw title
        title = self.calendar_config.get("calendar_title", "Calendar Events")
        if is_weekly:
            title = self.views_config.get("weekly", {}).get("title", "This Week")

        draw.text(
            (self.width // 2, 50),
            title,
            font=self.fonts["title"],
            fill=self.colors["text"],
            anchor="mm",
        )

        return image, draw

    def _format_time(self, dt: datetime) -> str:
        """Format time for display."""
        return dt.strftime("%I:%M %p").lstrip("0")

    def _is_event_on_day(self, event: dict[str, Any], date: date) -> bool:
        """Check if event occurs on given date."""
        start = event["start"].get("dateTime")
        if start:
            start_dt = datetime.fromisoformat(start)
            # Convert to local timezone if it has timezone info
            if start_dt.tzinfo is not None:
                start_dt = start_dt.astimezone(pytz.timezone(self.timezone))
            start_date = start_dt.date()
            return start_date == date
        else:
            start_date = datetime.fromisoformat(event["start"]["date"]).date()
            end_date = datetime.fromisoformat(event["end"]["date"]).date()
            return start_date <= date < end_date

    def _wrap_text(self, text: str, max_width: int, font: Any) -> list[str]:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line: list[str] = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def _format_date(self, dt: datetime) -> str:
        """Format date as string."""
        return dt.strftime("%Y-%m-%d, %b, %A")

    def _draw_event(
        self,
        draw: ImageDraw.ImageDraw,
        event: dict[str, Any],
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Draw an event on the image."""
        # Placeholder implementation
        draw.rectangle([x, y, x + width, y + height], outline="black", width=2)
        draw.text(
            (x + 10, y + 10),
            event.get("summary", ""),
            fill="black",
            font=self.fonts["event"],
        )

    def _get_text_width(self, text: str, font: Any) -> int:
        """Get the width of text in pixels."""
        return int(font.getlength(text))

    def _adjust_font_size(
        self,
        text: str,
        max_width: int,
        max_height: int,
        initial_size: int = 40,
        min_size: int = 20,
    ) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
        """Adjust font size to fit text within bounds."""
        font_size = initial_size
        while font_size >= min_size:
            try:
                font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype(
                    os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "media",
                        "fonts",
                        "roboto",
                        "static",
                        "Roboto-Regular.ttf",
                    ),
                    font_size,
                )
            except OSError:
                # Fallback to default font if loading fails
                font = ImageFont.load_default()

            wrapped_lines = self._wrap_text(text, max_width, font)
            total_height = sum(
                font.getbbox(line)[3] - font.getbbox(line)[1] for line in wrapped_lines
            )
            line_spacing = font_size * 0.2
            total_height += line_spacing * (len(wrapped_lines) - 1)
            if total_height <= max_height:
                return font, wrapped_lines
            font_size -= 2

        # Return minimum size font
        try:
            min_font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "media",
                    "fonts",
                    "roboto",
                    "static",
                    "Roboto-Regular.ttf",
                ),
                min_size,
            )
        except OSError:
            # Fallback to default font if loading fails
            min_font = ImageFont.load_default()

        return min_font, self._wrap_text(text, max_width, min_font)

    def _adjust_font_size_wrapped(
        self,
        text: str,
        max_width: int,
        max_height: int,
        initial_size: int = 80,
        min_size: int = 16,
        max_lines: int = 4,
    ) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
        """Adjust font size for wrapped text."""
        font_size = initial_size
        while font_size >= min_size:
            try:
                font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype(
                    os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "media",
                        "fonts",
                        "roboto",
                        "static",
                        "Roboto-Regular.ttf",
                    ),
                    font_size,
                )
            except OSError:
                # Fallback to default font if loading fails
                font = ImageFont.load_default()

            wrapped_lines = self._wrap_text(text, max_width, font)
            total_height = sum(
                font.getbbox(line)[3] - font.getbbox(line)[1] for line in wrapped_lines
            )
            line_spacing = font_size * 0.2
            total_height += line_spacing * (len(wrapped_lines) - 1)
            if len(wrapped_lines) <= max_lines and total_height <= max_height:
                return font, wrapped_lines
            font_size -= 2

        # Return minimum size font
        try:
            min_font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "media",
                    "fonts",
                    "roboto",
                    "static",
                    "Roboto-Regular.ttf",
                ),
                min_size,
            )
        except OSError:
            # Fallback to default font if loading fails
            min_font = ImageFont.load_default()

        return min_font, self._wrap_text(text, max_width, min_font)

    @handle_error(severity=ErrorSeverity.ERROR)
    def generate_weekly_view(self, events: list[dict[str, Any]]) -> Image.Image | None:
        """Generate weekly calendar view with full column layout and enhanced detail.

        MILESTONE: Enhanced Weekly View - December 2024
        - Full column per day with dates and day names at top
        - Multi-day event support with smart stacking
        - Enhanced detail with more vertical space
        - Same logic as 28-day sliding calendar

        CHECKPOINT: Workable Weekly Display - December 2024
        - Perfect spacing between date numbers and events
        - Centered day names above columns
        - Left-justified date numbers in column boxes
        - Month display at top left/right for context
        - No overlap between elements
        - Professional, readable layout
        """
        if not self.views_config.get("weekly", {}).get("enabled", True):
            return None

        # Initialize occupied positions tracking for multi-day event stacking
        self._occupied_positions = {0: set(), 1: set(), 2: set()}

        image, draw = self._create_base_image(True)

        # Calculate dimensions for 7-day week
        day_width = self.width // 7
        day_height = (self.height - 200) // 1  # Full height for one week
        start_y = 150

        # Get current date and Monday of the week
        current_date = datetime.now(pytz.timezone(self.timezone)).date()
        days_since_monday = current_date.weekday()  # Monday is 0, Sunday is 6
        monday_of_week = current_date - timedelta(days=days_since_monday)

        # Draw day headers with day names and dates
        header_y = start_y - 40  # Position above the main content
        for i in range(7):
            x = i * day_width
            date = monday_of_week + timedelta(days=i)

            # Day name (Mon, Tue, etc.) - centered above the column
            day_name = date.strftime("%a")[:3]  # First 3 letters
            day_x = x + day_width // 2  # Center in column
            draw.text(
                (day_x, header_y),
                day_name,
                font=self.fonts["header"],
                fill=self.colors["header"],
                anchor="mm",  # Center the text
            )

            # Date number - left-justified at top of the column box
            date_str = date.strftime("%d")
            draw.text(
                (x + 10, start_y + 10),  # 10px from top and left of box
                date_str,
                font=self.fonts["day"],
                fill=self.colors["text"],
            )

        # Add month display at the top
        start_month = monday_of_week.strftime("%B")  # Just month name, no year
        end_date = monday_of_week + timedelta(days=6)  # Sunday
        end_month = end_date.strftime("%B")  # Just month name, no year

        # Draw starting month on the left
        draw.text(
            (20, 15),  # 15px from top edge
            start_month,
            font=self.fonts["title"],  # Use title font for prominence
            fill=self.colors["text"],
        )

        # If crossing months, draw ending month on the right
        if start_month != end_month:
            # Calculate text width to position it on the right
            bbox = self.fonts["title"].getbbox(end_month)
            text_width = bbox[2] - bbox[0]
            right_x = self.width - text_width - 20  # 20px from right edge

            draw.text(
                (right_x, 15),  # 15px from top edge
                end_month,
                font=self.fonts["title"],
                fill=self.colors["text"],
            )

        # Draw grid lines to separate days into columns
        grid_color = (100, 100, 100)  # Gray color for grid lines

        # Draw vertical lines
        for i in range(8):  # 8 lines for 7 columns
            x = i * day_width
            draw.line(
                [(x, start_y), (x, start_y + day_height)], fill=grid_color, width=2
            )

        # Draw horizontal line at the top
        draw.line([(0, start_y), (self.width, start_y)], fill=grid_color, width=2)

        # Draw multi-day events first (so they appear behind single-day events)
        multi_day_events = [
            event for event in events if self._is_multi_day_event(event)
        ]
        for event in multi_day_events:
            self._draw_multi_day_event_weekly(
                draw, event, monday_of_week, day_width, day_height, start_y + 40
            )  # Shift down by 40px

        # Draw single-day events
        single_day_events = [
            event for event in events if not self._is_multi_day_event(event)
        ]

        for i in range(7):
            x = i * day_width
            y = start_y

            # Draw events for this day
            date = monday_of_week + timedelta(days=i)
            day_events = [
                event
                for event in single_day_events
                if self._is_event_on_day(event, date)
            ]

            # Sort events by time
            day_events.sort(
                key=lambda x: (
                    x["start"].get(
                        "dateTime", "9999-12-31"
                    ),  # Put all-day events at the end
                    x["summary"],
                )
            )

            # Limit events per day (more for weekly view)
            max_events = self.views_config.get("weekly", {}).get(
                "max_events_per_day", 8
            )
            day_events = day_events[:max_events]

            # Calculate available space for events
            available_width = day_width - 20  # 10px padding on each side
            day_height - 20  # Space for padding

            # Find the maximum y-offset+height of any multi-day event bar that overlaps this cell
            max_bar_bottom = 0
            if (
                hasattr(self, "_row_heights")
                and 0 in self._row_heights
                and hasattr(self, "_occupied_positions")
            ):
                for bar_col, level in self._occupied_positions.get(0, set()):
                    if bar_col == i:
                        bar_height = self._row_heights[0].get(level, 0)
                        # Compute y-offset for this bar
                        y_offset = 50  # base offset for multi-day bars
                        for prev_level in range(level):
                            y_offset += self._row_heights[0].get(prev_level, 0) + 5
                        bar_bottom = y_offset + bar_height
                        if bar_bottom > max_bar_bottom:
                            max_bar_bottom = bar_bottom

            # Add a small gap below the bar
            single_day_y_offset = (
                y + 50 + max_bar_bottom + (10 if max_bar_bottom > 0 else 50)
            )  # Start 50px down to clear date numbers

            # Draw each event
            event_y = single_day_y_offset
            for event in day_events:
                start_str = event["start"].get("dateTime")
                if start_str:
                    if not self.views_config.get("weekly", {}).get("show_time", True):
                        continue
                    start = datetime.fromisoformat(start_str)
                    event_time = self._format_time(start)
                else:
                    if not self.views_config.get("weekly", {}).get(
                        "show_all_day", True
                    ):
                        continue
                    event_time = "All Day"

                # Draw time within the day column
                draw.text(
                    (x + 10, event_y),  # 10px from left edge of day column
                    event_time,
                    font=self.fonts["time"],
                    fill=self.colors["text"],
                )
                event_y += (
                    self.fonts["time"].getbbox("Ay")[3] + 5
                )  # Move down for title

                # Draw event title with wrapping - position within the day column
                title = event["summary"]
                available_width = day_width - 20  # Leave some padding

                # Adjust font size and wrap text
                title_font, wrapped_title_lines = self._adjust_font_size_wrapped(
                    title,
                    available_width,
                    100,  # Max height for title
                    initial_size=32,
                    min_size=16,
                    max_lines=2,
                )

                # Draw wrapped title - position within the day column
                title_y = event_y + 5  # Start 5px from time
                line_height = title_font.getbbox("Ay")[3] + 4

                for line in wrapped_title_lines:
                    draw.text(
                        (x + 10, title_y),  # 10px from left edge of day column
                        line,
                        font=title_font,
                        fill=self.colors["text"],
                    )
                    title_y += line_height

                # Calculate total height used by this event
                time_height = self.fonts["time"].getbbox("Ay")[3]
                title_height = len(wrapped_title_lines) * line_height
                event_total_height = (
                    time_height + title_height + 15
                )  # Padding for weekly view

                # Move to next event position with proper spacing
                event_y += event_total_height + 8  # More spacing between events

        return image

    @handle_error(severity=ErrorSeverity.ERROR)
    def generate_sliding_30_days(
        self, events: list[dict[str, Any]]
    ) -> Image.Image | None:
        """Generate sliding 21-day view (3 weeks x 7 days).

        MILESTONE: 28-Day Sliding Calendar - December 2024
        - Dynamic height calculation for multi-day events
        - Smart stacking to prevent overlap
        - Single-day events positioned below multi-day bars
        - Proper date handling and timezone fixes
        """
        if not self.views_config.get("sliding_30_days", {}).get("enabled", True):
            return None

        # Initialize occupied positions tracking for multi-day event stacking
        self._occupied_positions = {0: set(), 1: set(), 2: set()}

        image, draw = self._create_base_image(False)

        # 21 days: 3 rows x 7 columns
        num_days = 21
        num_cols = 7
        num_rows = 3
        day_width = self.width // num_cols
        day_height = (self.height - 100) // num_rows
        start_y = 150

        # Get font size configuration
        self.views_config.get("sliding_30_days", {}).get("single_event_font_size", 80)
        self.views_config.get("sliding_30_days", {}).get("multi_event_font_size", 40)

        # Draw day headers centered above the grid
        header_y = start_y - 30  # Position above the grid
        for i, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            x = i * day_width + day_width // 2  # Center in column
            draw.text(
                (x, header_y),
                day,
                font=self.fonts["header"],
                fill=self.colors["header"],
                anchor="mm",  # Center the text
            )

        # Add month display at the top
        current_date = datetime.now(pytz.timezone(self.timezone)).date()

        # Calculate Monday of the current week
        days_since_monday = current_date.weekday()  # Monday is 0, Sunday is 6
        monday_of_week = current_date - timedelta(days=days_since_monday)

        start_month = monday_of_week.strftime("%B")  # Just month name, no year
        end_date = monday_of_week + timedelta(days=20)  # 21 days - 1 (0-indexed)
        end_month = end_date.strftime("%B")  # Just month name, no year

        # Draw starting month on the left
        draw.text(
            (20, 15),  # 15px from top edge
            start_month,
            font=self.fonts["title"],  # Use title font for prominence
            fill=self.colors["text"],
        )

        # If crossing months, draw ending month on the right
        if start_month != end_month:
            # Calculate text width to position it on the right
            bbox = self.fonts["title"].getbbox(end_month)
            text_width = bbox[2] - bbox[0]
            right_x = self.width - text_width - 20  # 20px from right edge

            draw.text(
                (right_x, 15),  # 15px from top edge
                end_month,
                font=self.fonts["title"],
                fill=self.colors["text"],
            )

        # Draw grid lines to separate days into boxes
        grid_color = (100, 100, 100)  # Gray color for grid lines

        # Draw vertical lines
        for i in range(num_cols + 1):
            x = i * day_width
            draw.line(
                [(x, start_y), (x, start_y + num_rows * day_height)],
                fill=grid_color,
                width=2,
            )

        # Draw horizontal lines
        for i in range(num_rows + 1):
            y = start_y + i * day_height
            draw.line([(0, y), (self.width, y)], fill=grid_color, width=2)

        # Draw multi-day events first (so they appear behind single-day events)
        multi_day_events = [
            event for event in events if self._is_multi_day_event(event)
        ]
        for event in multi_day_events:
            self._draw_multi_day_event(
                draw,
                event,
                current_date,
                end_date,
                monday_of_week,
                day_width,
                day_height,
                start_y,
            )

        # Draw single-day events
        single_day_events = [
            event for event in events if not self._is_multi_day_event(event)
        ]

        for i in range(num_days):
            row = i // num_cols
            col = i % num_cols
            x = col * day_width
            y = start_y + (row * day_height)

            # Draw date number in the top-left of each cell
            date = monday_of_week + timedelta(days=i)  # Start from Monday of the week
            draw.text(
                (x + 10, y + 10),  # 10px from top-left of cell
                date.strftime("%d"),  # Just the day number
                font=self.fonts["day"],
                fill=self.colors["text"],
            )

            # Draw events for this day
            day_events = [
                event
                for event in single_day_events
                if self._is_event_on_day(event, date)
            ]

            # Sort events by time
            day_events.sort(
                key=lambda x: (
                    x["start"].get(
                        "dateTime", "9999-12-31"
                    ),  # Put all-day events at the end
                    x["summary"],
                )
            )

            # Limit events per day
            max_events = self.views_config.get("sliding_30_days", {}).get(
                "max_events_per_day", 3
            )
            day_events = day_events[:max_events]

            # Calculate available space for events
            available_width = day_width - 20  # 10px padding on each side
            day_height - 60  # Space for date and padding

            # Find the maximum y-offset+height of any multi-day event bar that overlaps this cell
            max_bar_bottom = 0
            if (
                hasattr(self, "_row_heights")
                and row in self._row_heights
                and hasattr(self, "_occupied_positions")
            ):
                for bar_col, level in self._occupied_positions.get(row, set()):
                    if bar_col == col:
                        bar_height = self._row_heights[row].get(level, 0)
                        # Compute y-offset for this bar
                        y_offset = 50  # base offset for multi-day bars
                        for prev_level in range(level):
                            y_offset += self._row_heights[row].get(prev_level, 0) + 5
                        bar_bottom = y_offset + bar_height
                        if bar_bottom > max_bar_bottom:
                            max_bar_bottom = bar_bottom
            # Add a small gap below the bar
            single_day_y_offset = (
                y + 50 + max_bar_bottom + (10 if max_bar_bottom > 0 else 50)
            )  # Reduced from 80 to 50

            # Draw each event
            event_y = single_day_y_offset
            for event in day_events:
                start_str = event["start"].get("dateTime")
                if start_str:
                    if not self.views_config.get("sliding_30_days", {}).get(
                        "show_time", True
                    ):
                        continue
                    start = datetime.fromisoformat(start_str)
                    event_time = self._format_time(start)
                else:
                    if not self.views_config.get("sliding_30_days", {}).get(
                        "show_all_day", True
                    ):
                        continue
                    event_time = "All Day"

                # Draw time and title on the same line to save space
                title = event["summary"]
                available_width = day_width - 20  # Leave some padding

                # Adjust font size and wrap text
                title_font, wrapped_title_lines = self._adjust_font_size_wrapped(
                    title,
                    available_width,
                    day_height - 20,  # Leave some padding
                    initial_size=32,
                    min_size=16,
                    max_lines=3,
                )

                # Draw time and title together
                time_width = (
                    self.fonts["time"].getbbox(event_time)[2]
                    - self.fonts["time"].getbbox(event_time)[0]
                )
                draw.text(
                    (x + 10, event_y),  # 10px from left edge of cell
                    event_time,
                    font=self.fonts["time"],
                    fill=self.colors["text"],
                )

                # Draw title starting after time with a small gap
                title_x = x + 10 + time_width + 5  # 5px gap after time
                title_y = event_y
                line_height = title_font.getbbox("Ay")[3] + 2

                for line in wrapped_title_lines:
                    draw.text(
                        (title_x, title_y),  # Start after time
                        line,
                        font=title_font,
                        fill=self.colors["text"],
                    )
                    title_y += line_height

                # Calculate total height used by this event
                time_height = self.fonts["time"].getbbox("Ay")[3]
                title_height = len(wrapped_title_lines) * line_height
                event_total_height = (
                    max(time_height, title_height) + 5
                )  # Reduced padding

                # Move to next event position
                event_y += event_total_height + 3  # Reduced spacing between events

        return image

    @handle_error(severity=ErrorSeverity.ERROR)
    def generate_upcoming_events(
        self, events: list[dict[str, Any]]
    ) -> Image.Image | None:
        """Generate enhanced upcoming events view with categories and details.

        MILESTONE: Enhanced Upcoming Events - December 2024 ✅ COMPLETED
        - Date display for each event
        - Event categorization (Today, Tomorrow, This Week, etc.)
        - Enhanced formatting with better spacing and layout
        - Visual hierarchy with different styling
        - Event details including duration and location
        - Fixed "All Day" overlap issues with proper spacing
        - Screen fitting logic to prevent overflow
        - Improved visual hierarchy with indented events under categories
        - Increased padding below category headers for better readability
        """
        if not self.views_config.get("upcoming", {}).get("enabled", True):
            return None

        image, draw = self._create_base_image(False)

        # Get current date and time
        current_date = datetime.now(pytz.timezone(self.timezone)).date()
        datetime.now(pytz.timezone(self.timezone))

        # Sort events by start time
        events.sort(key=lambda x: x["start"].get("dateTime", "9999-12-31"))

        # Filter and categorize events
        categorized_events: dict[str, list[dict[str, Any]]] = {
            "Today": [],
            "Tomorrow": [],
            "This Week": [],
            "Next Week": [],
            "Later": [],
        }

        for event in events:
            start_str = event["start"].get("dateTime")
            if start_str:
                if not self.views_config.get("upcoming", {}).get("show_time", True):
                    continue
                start = datetime.fromisoformat(start_str)
                event_date = start.date()
            else:
                if not self.views_config.get("upcoming", {}).get("show_all_day", True):
                    continue
                event_date = datetime.fromisoformat(event["start"]["date"]).date()

            # Skip past events
            if event_date < current_date:
                continue

            # Categorize event
            days_diff = (event_date - current_date).days
            if days_diff == 0:
                categorized_events["Today"].append(event)
            elif days_diff == 1:
                categorized_events["Tomorrow"].append(event)
            elif days_diff <= 7:
                categorized_events["This Week"].append(event)
            elif days_diff <= 14:
                categorized_events["Next Week"].append(event)
            else:
                categorized_events["Later"].append(event)

        # Draw title
        title = "Upcoming Events"
        draw.text(
            (50, 50),
            title,
            font=self.fonts["title"],
            fill=self.colors["header"],
        )

        # Draw events by category
        y = 150
        max_events_per_category = self.views_config.get("upcoming", {}).get(
            "max_events_per_category", 5
        )

        for category, category_events in categorized_events.items():
            if not category_events:
                continue

            # Limit events per category
            category_events = category_events[:max_events_per_category]

            # Check if we have enough space for this category
            category_header_height = 40
            estimated_event_height = 60  # Rough estimate per event
            total_category_height = category_header_height + (
                len(category_events) * estimated_event_height
            )

            # If this category would exceed screen height, skip it
            if (
                y + total_category_height > self.height - 100
            ):  # Leave 100px margin at bottom
                break

            # Draw category header
            draw.text(
                (50, y),
                category,
                font=self.fonts["header"],
                fill=self.colors["header"],
            )
            y += 60  # Increased from 40 to 60 for more padding below headers

            # Draw events in this category
            for event in category_events:
                start_str = event["start"].get("dateTime")
                end_str = event["end"].get("dateTime")

                if start_str:
                    start = datetime.fromisoformat(start_str)
                    event_date = start.date()
                    event_time = self._format_time(start)

                    # Calculate duration
                    if end_str:
                        end = datetime.fromisoformat(end_str)
                        duration = end - start
                        if duration.total_seconds() > 0:
                            hours = int(duration.total_seconds() // 3600)
                            int((duration.total_seconds() % 3600) // 60)
                            if hours > 0:
                                pass
                            else:
                                pass
                        else:
                            pass
                    else:
                        pass
                else:
                    event_date = datetime.fromisoformat(event["start"]["date"]).date()
                    event_time = "All Day"

                # Check if this event would fit on screen
                estimated_event_height = 80  # Conservative estimate
                if (
                    y + estimated_event_height > self.height - 100
                ):  # Leave 100px margin at bottom
                    break

                # Draw date and time on the same line (indented under category)
                draw.text(
                    (80, y),  # Indented from 50 to 80
                    event_date.strftime("%a, %b %d"),
                    font=self.fonts["time"],
                    fill=self.colors["text"],
                )
                # Time column (including "All Day") - also indented
                draw.text(
                    (280, y),  # Indented from 250 to 280
                    event_time,
                    font=self.fonts["time"],
                    fill=self.colors["text"],
                )

                # Draw event title (indented)
                title = event["summary"]
                title_x = 430  # Indented from 400 to 430
                available_width = self.width - (title_x + 150)
                title_font, wrapped_title_lines = self._adjust_font_size_wrapped(
                    title,
                    available_width,
                    100,
                    initial_size=32,
                    min_size=16,
                    max_lines=2,
                )
                title_y = y
                line_height = title_font.getbbox("Ay")[3] + 4
                for line in wrapped_title_lines:
                    draw.text(
                        (title_x, title_y),
                        line,
                        font=title_font,
                        fill=self.colors["text"],
                    )
                    title_y += line_height

                # Calculate actual height used by this event
                time_height = self.fonts["time"].getbbox("Ay")[3]
                title_height = len(wrapped_title_lines) * line_height
                event_total_height = max(time_height, title_height) + 10
                y += event_total_height + 5

            # Add space between categories
            y += 20

        return image

    def _is_multi_day_event(self, event: dict[str, Any]) -> bool:
        """Check if an event spans multiple days."""
        start = event["start"]
        end = event["end"]

        # Handle all-day events
        if "date" in start and "date" in end:
            start_date = datetime.fromisoformat(start["date"]).date()
            end_date = datetime.fromisoformat(end["date"]).date()
            return start_date != end_date

        # Handle timed events
        if "dateTime" in start and "dateTime" in end:
            start_dt = datetime.fromisoformat(start["dateTime"])
            end_dt = datetime.fromisoformat(end["dateTime"])
            start_date = start_dt.date()
            end_date = end_dt.date()
            return start_date != end_date

        return False

    def _get_event_date_range(self, event: dict[str, Any]) -> tuple[date, date]:
        """Get the start and end dates for an event."""
        start = event["start"]
        end = event["end"]

        if "date" in start and "date" in end:
            start_date = datetime.fromisoformat(start["date"]).date()
            end_date = datetime.fromisoformat(end["date"]).date()
        else:
            # Handle timezone conversion for datetime events
            start_dt = datetime.fromisoformat(start["dateTime"])
            end_dt = datetime.fromisoformat(end["dateTime"])

            # Convert to local timezone if they have timezone info
            if start_dt.tzinfo is not None:
                start_dt = start_dt.astimezone(pytz.timezone(self.timezone))
            if end_dt.tzinfo is not None:
                end_dt = end_dt.astimezone(pytz.timezone(self.timezone))

            start_date = start_dt.date()
            end_date = end_dt.date()

        return start_date, end_date

    def _calculate_event_height(
        self, title: str, available_width: int, min_height: int = 30
    ) -> tuple[int, Any, list[str]]:
        """Calculate the required height for an event based on its text content."""
        title_font = self.fonts["event"]

        # Wrap text to fit within available width
        wrapped_lines = self._wrap_text(title, available_width, title_font)

        # Check if text fits in minimum height, if not, reduce font size
        max_lines = 3  # Allow up to 3 lines for better text display
        if len(wrapped_lines) > max_lines:
            # Try with smaller font
            smaller_font = ImageFont.truetype(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "media",
                    "fonts",
                    "roboto",
                    "static",
                    "Roboto-Regular.ttf",
                ),
                20,  # Smaller font size
            )
            wrapped_lines = self._wrap_text(title, available_width, smaller_font)
            title_font = smaller_font

        # Limit to maximum lines
        wrapped_lines = wrapped_lines[:max_lines]

        # Calculate required height
        if wrapped_lines:
            line_height = int(title_font.getbbox("Ay")[3]) + 2
            text_height = len(wrapped_lines) * line_height
            # Add padding (10px top + 10px bottom)
            required_height = text_height + 20
        else:
            required_height = min_height

        # Ensure minimum height
        final_height = max(required_height, min_height)

        return final_height, title_font, wrapped_lines

    def _draw_multi_day_event(
        self,
        draw: ImageDraw.ImageDraw,
        event: dict[str, Any],
        start_date: date,
        end_date: date,
        monday_of_week: date,
        day_width: int,
        day_height: int,
        start_y: int,
    ) -> None:
        """Draw a multi-day event spanning multiple days with smart stacking."""
        event_start, event_end = self._get_event_date_range(event)

        # Calculate which days in our 21-day view this event spans
        view_start = monday_of_week
        view_end = monday_of_week + timedelta(days=20)

        # Find the intersection of the event with our view
        display_start = max(event_start, view_start)
        display_end = min(event_end, view_end)

        if display_start > display_end:
            return  # Event is outside our view

        # Calculate positions for the event box
        start_offset = (display_start - view_start).days
        end_offset = (display_end - view_start).days

        # Check if event crosses week boundaries
        start_row = start_offset // 7
        end_row = end_offset // 7

        # Initialize tracking systems for multi-day events
        if not hasattr(self, "_occupied_positions"):
            self._occupied_positions = {0: set(), 1: set(), 2: set()}
        if not hasattr(self, "_row_heights"):
            self._row_heights = {}

        if start_row == end_row:
            # Event is within one week, draw as single bar
            start_col = start_offset % 7
            end_col = end_offset % 7

            # Calculate available width for title
            available_width = (
                end_col - start_col + 1
            ) * day_width - 40  # Padding for vertical lines

            # Calculate required height based on text content
            title = event["summary"]
            line_height, title_font, wrapped_lines = self._calculate_event_height(
                title, available_width
            )

            # Find the best vertical position for this event
            vertical_level, y_offset = self._find_best_vertical_position(
                start_row, start_col, end_col, line_height
            )

            x_start = start_col * day_width
            x_end = end_col * day_width + day_width  # Cover only the actual days
            y_start = start_y + start_row * day_height + 50 + y_offset
            y_end = y_start + line_height

            # Mark this position as occupied
            for col in range(start_col, end_col + 1):
                self._occupied_positions[start_row].add((col, vertical_level))

            # Draw light grey background bar
            draw.rectangle(
                [x_start, y_start, x_end, y_end],
                fill=(240, 240, 240),
                outline=(200, 200, 200),
                width=1,
            )

            # Draw vertical lines at start and end (heavier)
            draw.line(
                [(x_start, y_start), (x_start, y_end)], fill=(80, 80, 80), width=6
            )
            draw.line([(x_end, y_start), (x_end, y_end)], fill=(80, 80, 80), width=6)

            # Draw event title centered in the bar
            if wrapped_lines:
                # Center the text vertically in the bar
                text_height = len(wrapped_lines) * title_font.getbbox("Ay")[3]
                title_y = y_start + (line_height - text_height) // 2

                for line in wrapped_lines:
                    # Center the line horizontally
                    line_width = (
                        title_font.getbbox(line)[2] - title_font.getbbox(line)[0]
                    )
                    line_x = x_start + (x_end - x_start - line_width) // 2

                    draw.text(
                        (line_x, title_y),
                        line,
                        font=title_font,
                        fill=self.colors["text"],
                    )
                    title_y += title_font.getbbox("Ay")[3] + 2
        else:
            # Event crosses week boundaries, draw separate bars for each week
            for row in range(start_row, end_row + 1):
                week_start_col = 0 if row > start_row else start_offset % 7
                week_end_col = 6 if row < end_row else end_offset % 7

                # Calculate available width for title
                available_width = (week_end_col - week_start_col + 1) * day_width - 40

                # Calculate required height based on text content
                title = event["summary"]
                line_height, title_font, wrapped_lines = self._calculate_event_height(
                    title, available_width
                )

                # Find the best vertical position for this week's bar
                vertical_level, y_offset = self._find_best_vertical_position(
                    row, week_start_col, week_end_col, line_height
                )

                x_start = week_start_col * day_width
                x_end = (
                    week_end_col * day_width + day_width
                )  # Cover only the actual days
                y_start = start_y + row * day_height + 50 + y_offset
                y_end = y_start + line_height

                # Mark this position as occupied
                for col in range(week_start_col, week_end_col + 1):
                    self._occupied_positions[row].add((col, vertical_level))

                # Draw light grey background bar
                draw.rectangle(
                    [x_start, y_start, x_end, y_end],
                    fill=(240, 240, 240),
                    outline=(200, 200, 200),
                    width=1,
                )

                # Draw vertical lines at start and end (heavier)
                draw.line(
                    [(x_start, y_start), (x_start, y_end)], fill=(80, 80, 80), width=6
                )
                draw.line(
                    [(x_end, y_start), (x_end, y_end)], fill=(80, 80, 80), width=6
                )

                # Draw event title in each week's box, centered
                if wrapped_lines:
                    # Center the text vertically in the bar
                    text_height = len(wrapped_lines) * title_font.getbbox("Ay")[3]
                    title_y = y_start + (line_height - text_height) // 2

                    for line in wrapped_lines:
                        # Center the line horizontally
                        line_width = (
                            title_font.getbbox(line)[2] - title_font.getbbox(line)[0]
                        )
                        line_x = x_start + (x_end - x_start - line_width) // 2

                        draw.text(
                            (line_x, title_y),
                            line,
                            font=title_font,
                            fill=self.colors["text"],
                        )
                        title_y += title_font.getbbox("Ay")[3] + 2

    def _find_best_vertical_position(
        self, row: int, start_col: int, end_col: int, event_height: int
    ) -> tuple[int, int]:
        """Find the best vertical position for a multi-day event to avoid overlaps.
        Returns (vertical_level, y_offset) where y_offset is the cumulative height of previous levels.
        """
        # Check if this row has any occupied positions
        if row not in self._occupied_positions:
            self._occupied_positions[row] = set()

        # Track heights used by each level in this row
        if not hasattr(self, "_row_heights"):
            self._row_heights = {}
        if row not in self._row_heights:
            self._row_heights[row] = {}

        # Check each vertical level (0 = top, 1 = middle, 2 = bottom)
        for level in range(5):  # Support up to 5 levels for better stacking
            # Check if this level is free for all columns in our range
            is_free = True
            for col in range(start_col, end_col + 1):
                if (col, level) in self._occupied_positions[row]:
                    is_free = False
                    break

            if is_free:
                # Calculate y_offset based on heights of previous levels
                y_offset = 0
                for prev_level in range(level):
                    if prev_level in self._row_heights[row]:
                        y_offset += (
                            self._row_heights[row][prev_level] + 5
                        )  # 5px gap between levels

                # Store the height for this level
                self._row_heights[row][level] = event_height

                return level, y_offset

        # If all levels are occupied, use the top level (will overlap but at least it's visible)
        y_offset = 0
        if 0 in self._row_heights[row]:
            y_offset = self._row_heights[row][0] + 5
        self._row_heights[row][0] = event_height
        return 0, y_offset

    def _get_multi_day_event_height_for_row(self, row: int) -> int:
        """Calculate the maximum height used by multi-day events in a specific row."""
        if not hasattr(self, "_row_heights") or row not in self._row_heights:
            return 0

        if not self._row_heights[row]:
            return 0

        # Calculate total height: base height (50px) + sum of all level heights + gaps
        total_height = 50  # Base height
        for _level, height in self._row_heights[row].items():
            total_height += height + 5  # Add height + 5px gap

        return total_height

    def _draw_multi_day_event_weekly(
        self,
        draw: ImageDraw.ImageDraw,
        event: dict[str, Any],
        monday_of_week: date,
        day_width: int,
        day_height: int,
        start_y: int,
    ) -> None:
        """Draw a multi-day event in the weekly view with smart stacking."""
        event_start, event_end = self._get_event_date_range(event)

        # Calculate which days in our week this event spans
        view_start = monday_of_week
        view_end = monday_of_week + timedelta(days=6)  # Sunday

        # Find the intersection of the event with our view
        display_start = max(event_start, view_start)
        display_end = min(event_end, view_end)

        if display_start > display_end:
            return  # Event is outside our view

        # Calculate positions for the event box
        start_offset = (display_start - view_start).days
        end_offset = (display_end - view_start).days

        # Initialize tracking systems for multi-day events
        if not hasattr(self, "_occupied_positions"):
            self._occupied_positions = {0: set(), 1: set(), 2: set()}
        if not hasattr(self, "_row_heights"):
            self._row_heights = {}
        if 0 not in self._row_heights:
            self._row_heights[0] = {}

        # Calculate available width for title
        available_width = (
            end_offset - start_offset + 1
        ) * day_width - 40  # Padding for vertical lines

        # Calculate required height based on text content
        title = event["summary"]
        line_height, title_font, wrapped_lines = self._calculate_event_height(
            title, available_width
        )

        # Find the best vertical position for this event
        vertical_level, y_offset = self._find_best_vertical_position(
            0, start_offset, end_offset, line_height
        )

        x_start = start_offset * day_width
        x_end = end_offset * day_width + day_width  # Cover only the actual days
        y_start = start_y + 50 + y_offset  # Use adjusted start_y
        y_end = y_start + line_height

        # Mark this position as occupied
        for col in range(start_offset, end_offset + 1):
            self._occupied_positions[0].add((col, vertical_level))

        # Draw light grey background bar
        draw.rectangle(
            [x_start, y_start, x_end, y_end],
            fill=(240, 240, 240),
            outline=(200, 200, 200),
            width=1,
        )

        # Draw vertical lines at start and end (heavier)
        draw.line([(x_start, y_start), (x_start, y_end)], fill=(80, 80, 80), width=6)
        draw.line([(x_end, y_start), (x_end, y_end)], fill=(80, 80, 80), width=6)

        # Draw event title centered in the bar
        if wrapped_lines:
            # Center the text vertically in the bar
            text_height = len(wrapped_lines) * title_font.getbbox("Ay")[3]
            title_y = y_start + (line_height - text_height) // 2

            for line in wrapped_lines:
                # Center the line horizontally
                line_width = title_font.getbbox(line)[2] - title_font.getbbox(line)[0]
                line_x = x_start + (x_end - x_start - line_width) // 2

                draw.text(
                    (line_x, title_y),
                    line,
                    font=title_font,
                    fill=self.colors["text"],
                )
                title_y += title_font.getbbox("Ay")[3] + 2
