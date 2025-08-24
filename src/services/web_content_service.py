"""
Web Content Aggregation Service for Sprint 6.

This service captures screenshots of configured web pages and stores them
for inclusion in the slideshow with time-of-day weighting.
"""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import Page, async_playwright

from src.config.config_manager import ConfigManager
from src.utils.error_handling import handle_error

logger = logging.getLogger(__name__)


class WebContentTarget:
    """Represents a web content target for screenshot capture."""

    def __init__(
        self,
        name: str,
        url: str,
        selector: str,
        enabled: bool = True,
        weight: float = 1.0,
    ):
        self.name = name
        self.url = url
        self.selector = selector
        self.enabled = enabled
        self.weight = weight

    def __repr__(self) -> str:
        return f"WebContentTarget(name='{self.name}', url='{self.url}', selector='{self.selector}')"


class WebContentService:
    """Service for capturing and managing web content screenshots."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.to_dict()
        self.web_config = self.config.get("web_content", {})

        # Initialize paths
        self.output_folder = Path(
            self.web_config.get("output_folder", "media/web_news")
        )
        self.output_folder.mkdir(parents=True, exist_ok=True)

        # Browser settings
        self.browser_config = self.web_config.get("browser", {})
        self.headless = self.browser_config.get("headless", True)
        self.timeout = (
            self.browser_config.get("timeout_seconds", 30) * 1000
        )  # Convert to milliseconds
        self.user_agent = self.browser_config.get(
            "user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        # Image settings
        self.image_width = self.web_config.get("image_width", 1920)
        self.image_height = self.web_config.get("image_height", 1080)

        # Sync settings
        self.sync_interval = self.web_config.get("sync_interval_minutes", 30)
        self.auto_sync_on_startup = self.web_config.get("auto_sync_on_startup", True)

        # Cleanup settings
        self.should_cleanup_old_files = self.web_config.get("cleanup_old_files", True)
        self.max_file_age_hours = self.web_config.get("max_file_age_hours", 24)

        # Initialize targets
        self.targets = self._load_targets()

        # Browser instance
        self.browser = None
        self.playwright = None

        logger.info(f"WebContentService initialized with {len(self.targets)} targets")

    def _load_targets(self) -> list[WebContentTarget]:
        """Load web content targets from configuration."""
        targets = []
        targets_config = self.web_config.get("targets", [])

        for target_config in targets_config:
            target = WebContentTarget(
                name=target_config.get("name", "Unknown"),
                url=target_config.get("url", ""),
                selector=target_config.get("selector", "body"),
                enabled=target_config.get("enabled", True),
                weight=target_config.get("weight", 1.0),
            )
            if target.enabled:
                targets.append(target)

        return targets

    async def start(self) -> None:
        """Start the web content service."""
        if self.web_config.get("enabled", False) is False:
            logger.info("Web content service is disabled in config")
            self.playwright = None
            self.browser = None
            return
        try:
            logger.info("Starting web content service")
            logger.info("Starting Playwright...")
            self.playwright = await async_playwright().start()
            logger.info("Playwright started successfully")
            logger.info("Launching browser...")
            if self.playwright is None:
                raise RuntimeError("Failed to start Playwright")
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )
            logger.info("Browser launched successfully")
            logger.info("Web content service started successfully")
        except ImportError:
            logger.error(
                "Playwright not installed. Please install with: pip install playwright && playwright install"
            )
            self.playwright = None
            self.browser = None
        except Exception as e:
            logger.error(f"Failed to start web content service: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            self.playwright = None
            self.browser = None

    async def stop(self) -> None:
        """Stop the web content service."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        logger.info("Web content service stopped")

    def sanitize_filename(self, name: str) -> str:
        """Sanitize a string to be safe for filenames (ASCII only, replace non-alphanum with _)."""
        # Remove non-ASCII characters
        name_ascii = name.encode("ascii", "ignore").decode("ascii")
        # Replace non-alphanumeric characters with underscores
        result = re.sub(r"[^a-zA-Z0-9]+", "_", name_ascii).strip("_").lower()
        return result

    @handle_error()
    async def create_text_slide_images(self, content: dict) -> list[Path]:
        """Create image slides from extracted text content."""
        try:
            logger.info(f"Creating text slides for {content.get('source', 'Unknown')}")

            # Clean up old slides for this content type before creating new ones
            if content.get("source") == "Red River Theater":
                await self._cleanup_old_red_river_slides()
            elif content.get("source") == "The Music Hall":
                await self._cleanup_old_music_hall_slides()
            elif content.get("source") == "Capitol Center for the Arts":
                await self._cleanup_old_capitol_center_slides()
            elif content.get("source") == "WMUR News":
                await self._cleanup_old_wmur_slides()
            elif content.get("source") == "Bank of New Hampshire Pavilion":
                await self._cleanup_old_bank_nh_pavilion_slides()

            slide_paths: list[Path] = []
            content_items = content.get("content", [])
            if not content_items:
                logger.warning("No content items to create slides from")
                return slide_paths

            # Group content by section if its theater content
            if content.get("type") == "theater_movies":
                sections: dict[str, list[dict]] = {}
                for item in content_items:
                    section = item.get("section", "Unknown")
                    if section not in sections:
                        sections[section] = []
                    sections[section].append(item)

                # Create slides for each section
                for section_name, items in sections.items():
                    slide_path = await self._create_theater_slide(section_name, items)
                    if slide_path:
                        slide_paths.append(slide_path)
            elif content.get("type") == "theater_events":
                # Create events slides - handle both upcoming and newly announced
                source = content.get("source", "Theater Events")

                if source == "Bank of New Hampshire Pavilion":
                    # Create separate slides for upcoming and newly announced events
                    upcoming_slide = await self._create_upcoming_events_slide(content)
                    if upcoming_slide:
                        slide_paths.append(upcoming_slide)

                    newly_announced_slide = (
                        await self._create_newly_announced_events_slide(content)
                    )
                    if newly_announced_slide:
                        slide_paths.append(newly_announced_slide)
                else:
                    # Create single events slide for other venues
                    slide_path = await self._create_events_slide(content)
                    if slide_path:
                        slide_paths.append(slide_path)
            elif content.get("type") == "news_headlines":
                # Create news headlines slide
                slide_path = await self._create_news_slide(content)
                if slide_path:
                    slide_paths.append(slide_path)
            else:
                # Create generic text slide
                slide_path = await self._create_generic_text_slide(content)
                if slide_path:
                    slide_paths.append(slide_path)

            logger.info(f"Created {len(slide_paths)} text slides")
            return slide_paths

        except Exception as e:
            logger.error(f"Failed to create text slides: {e}")
            return []

    async def _create_theater_slide(
        self, section_name: str, movies: list[dict]
    ) -> Path | None:
        """Create a slide for theater movies section with centered, large, title-cased titles."""
        try:
            # Create image
            img = Image.new("RGB", (self.image_width, self.image_height), color="black")
            draw = ImageDraw.Draw(img)

            # Try to load a font, fall back to default if not available
            try:
                title_font = ImageFont.truetype("Arial.ttf", 80)
                movie_font = ImageFont.truetype("Arial.ttf", 64)
            except OSError:
                title_font = ImageFont.load_default()
                movie_font = ImageFont.load_default()

            # Draw section title
            title = f"Red River Theater - {section_name}"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.image_width - title_width) // 2
            draw.text((title_x, 80), title, fill="white", font=title_font)

            # Draw movie titles, centered, with more spacing and lower start
            y_position = 250  # Start lower on the page
            spacing = 90  # More vertical spacing
            for movie in movies:
                movie_title = movie.get("title", "Unknown Title").title()
                movie_bbox = draw.textbbox((0, 0), movie_title, font=movie_font)
                movie_width = movie_bbox[2] - movie_bbox[0]
                movie_x = (self.image_width - movie_width) // 2
                draw.text(
                    (movie_x, y_position), movie_title, fill="yellow", font=movie_font
                )
                y_position += spacing
                if y_position > self.image_height - 100:
                    break

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_section = self.sanitize_filename(section_name)
            filename = f"red_river_{safe_section}_{timestamp}.png"
            slide_path = self.output_folder / filename
            img.save(slide_path)
            logger.info(f"Created theater slide: {slide_path}")
            return slide_path
        except Exception as e:
            logger.error(f"Failed to create theater slide: {e}")
            return None

    async def _create_events_slide(self, content: dict) -> Path | None:
        """Create a slide for theater events with event titles, dates, and venues."""
        try:
            # Create image
            img = Image.new("RGB", (self.image_width, self.image_height), color="black")
            draw = ImageDraw.Draw(img)

            # Try to load a font, fall back to default if not available
            try:
                title_font = ImageFont.truetype("Arial.ttf", 70)
                event_font = ImageFont.truetype("Arial.ttf", 50)
                date_font = ImageFont.truetype("Arial.ttf", 35)
                venue_font = ImageFont.truetype("Arial.ttf", 30)
            except OSError:
                title_font = ImageFont.load_default()
                event_font = ImageFont.load_default()
                date_font = ImageFont.load_default()
                venue_font = ImageFont.load_default()

            # Draw title based on source
            source = content.get("source", "Theater Events")
            title = f"{source} - Upcoming Events"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.image_width - title_width) // 2
            draw.text((title_x, 80), title, fill="white", font=title_font)

            # Draw events
            y_position = 200
            spacing = 80
            for event in content.get("content", [])[:5]:  # Limit to 5 events
                event_title = event.get("title", "Unknown Event").title()
                event_date = event.get("date", "")
                event_venue = event.get("venue", "")

                # Draw event title
                event_bbox = draw.textbbox((0, 0), event_title, font=event_font)
                event_width = event_bbox[2] - event_bbox[0]
                event_x = (self.image_width - event_width) // 2
                draw.text(
                    (event_x, y_position), event_title, fill="yellow", font=event_font
                )

                # Draw date if available
                if event_date:
                    date_bbox = draw.textbbox((0, 0), event_date, font=date_font)
                    date_width = date_bbox[2] - date_bbox[0]
                    date_x = (self.image_width - date_width) // 2
                    draw.text(
                        (date_x, y_position + 60),
                        event_date,
                        fill="lightblue",
                        font=date_font,
                    )
                    y_position += 50

                # Draw venue if available
                if event_venue:
                    venue_bbox = draw.textbbox((0, 0), event_venue, font=venue_font)
                    venue_width = venue_bbox[2] - venue_bbox[0]
                    venue_x = (self.image_width - venue_width) // 2
                    draw.text(
                        (venue_x, y_position + 45),
                        event_venue,
                        fill="orange",
                        font=venue_font,
                    )
                    y_position += spacing + 20
                else:
                    y_position += spacing

                if y_position > self.image_height - 100:
                    break

            # Save image with appropriate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if source == "The Music Hall":
                filename = f"music_hall_events_{timestamp}.png"
            elif source == "Capitol Center for the Arts":
                filename = f"capitol_center_events_{timestamp}.png"
            else:
                filename = f"theater_events_{timestamp}.png"

            slide_path = self.output_folder / filename
            img.save(slide_path)
            logger.info(f"Created events slide: {slide_path}")
            return slide_path
        except Exception as e:
            logger.error(f"Failed to create events slide: {e}")
            return None

    async def _create_upcoming_events_slide(self, content: dict) -> Path | None:
        """Create a slide for upcoming Bank NH Pavilion events."""
        try:
            # Create image
            img = Image.new("RGB", (self.image_width, self.image_height), color="black")
            draw = ImageDraw.Draw(img)

            # Try to load a font, fall back to default if not available
            try:
                title_font = ImageFont.truetype("Arial.ttf", 70)
                event_font = ImageFont.truetype("Arial.ttf", 50)
                date_font = ImageFont.truetype("Arial.ttf", 35)
                desc_font = ImageFont.truetype("Arial.ttf", 25)
            except OSError:
                title_font = ImageFont.load_default()
                event_font = ImageFont.load_default()
                date_font = ImageFont.load_default()
                desc_font = ImageFont.load_default()

            # Draw title
            title = "Bank NH Pavilion - Upcoming Events"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.image_width - title_width) // 2
            draw.text((title_x, 60), title, fill="white", font=title_font)

            # Draw events
            y_position = 180
            spacing = 140  # Increased spacing between events
            for event in content.get("content", [])[:4]:  # Limit to 4 events
                event_title = event.get("title", "Unknown Event").title()
                event_date = event.get("date", "")
                event_description = event.get("description", "")

                # Draw event title
                event_bbox = draw.textbbox((0, 0), event_title, font=event_font)
                event_width = event_bbox[2] - event_bbox[0]
                event_x = (self.image_width - event_width) // 2
                draw.text(
                    (event_x, y_position), event_title, fill="yellow", font=event_font
                )

                # Draw date if available
                if event_date:
                    date_bbox = draw.textbbox((0, 0), event_date, font=date_font)
                    date_width = date_bbox[2] - date_bbox[0]
                    date_x = (self.image_width - date_width) // 2
                    draw.text(
                        (date_x, y_position + 60),
                        event_date,
                        fill="lightblue",
                        font=date_font,
                    )
                    y_position += 50

                # Draw description if available
                if event_description:
                    # Wrap description text if too long
                    max_width = self.image_width - 100
                    words = event_description.split()
                    lines = []
                    current_line = ""

                    for word in words:
                        test_line = current_line + " " + word if current_line else word
                        bbox = draw.textbbox((0, 0), test_line, font=desc_font)
                        if bbox[2] - bbox[0] <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word

                    if current_line:
                        lines.append(current_line)

                    # Draw description lines
                    for line in lines[:2]:  # Limit to 2 lines
                        desc_bbox = draw.textbbox((0, 0), line, font=desc_font)
                        desc_width = desc_bbox[2] - desc_bbox[0]
                        desc_x = (self.image_width - desc_width) // 2
                        draw.text(
                            (desc_x, y_position + 45),
                            line,
                            fill="orange",
                            font=desc_font,
                        )
                        y_position += 35

                y_position += spacing

                if y_position > self.image_height - 100:
                    break

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bank_nh_pavilion_upcoming_{timestamp}.png"
            slide_path = self.output_folder / filename
            img.save(slide_path)
            logger.info(f"Created upcoming events slide: {slide_path}")
            return slide_path
        except Exception as e:
            logger.error(f"Failed to create upcoming events slide: {e}")
            return None

    async def _create_newly_announced_events_slide(self, content: dict) -> Path | None:
        """Create a slide for newly announced Bank NH Pavilion events."""
        try:
            # For now, let's create a slide showing the first few events as "newly announced"
            # This is a simplified approach - in production, you'd want proper tracking
            all_events = content.get("content", [])

            # Take the first 2-3 events as "newly announced" for demonstration
            newly_announced = all_events[:3] if all_events else []

            # If no events, don't create a slide
            if not newly_announced:
                logger.info("No events found, skipping newly announced slide")
                return None

            logger.info(
                f"Creating newly announced slide with {len(newly_announced)} events"
            )

            # Create image
            img = Image.new("RGB", (self.image_width, self.image_height), color="black")
            draw = ImageDraw.Draw(img)

            # Try to load a font, fall back to default if not available
            try:
                title_font = ImageFont.truetype("Arial.ttf", 70)
                event_font = ImageFont.truetype("Arial.ttf", 50)
                date_font = ImageFont.truetype("Arial.ttf", 35)
                desc_font = ImageFont.truetype("Arial.ttf", 25)
            except OSError:
                title_font = ImageFont.load_default()
                event_font = ImageFont.load_default()
                date_font = ImageFont.load_default()
                desc_font = ImageFont.load_default()

            # Draw title
            title = "Bank NH Pavilion - Newly Announced!"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.image_width - title_width) // 2
            draw.text((title_x, 60), title, fill="white", font=title_font)

            # Draw newly announced events
            y_position = 180
            spacing = 140  # Increased spacing between events
            for event in newly_announced[:4]:  # Limit to 4 events
                event_title = event.get("title", "Unknown Event").title()
                event_date = event.get("date", "")
                event_description = event.get("description", "")

                # Draw event title
                event_bbox = draw.textbbox((0, 0), event_title, font=event_font)
                event_width = event_bbox[2] - event_bbox[0]
                event_x = (self.image_width - event_width) // 2
                draw.text(
                    (event_x, y_position), event_title, fill="yellow", font=event_font
                )

                # Draw date if available
                if event_date:
                    date_bbox = draw.textbbox((0, 0), event_date, font=date_font)
                    date_width = date_bbox[2] - date_bbox[0]
                    date_x = (self.image_width - date_width) // 2
                    draw.text(
                        (date_x, y_position + 60),
                        event_date,
                        fill="lightblue",
                        font=date_font,
                    )
                    y_position += 50

                # Draw description if available
                if event_description:
                    # Wrap description text if too long
                    max_width = self.image_width - 100
                    words = event_description.split()
                    lines = []
                    current_line = ""

                    for word in words:
                        test_line = current_line + " " + word if current_line else word
                        bbox = draw.textbbox((0, 0), test_line, font=desc_font)
                        if bbox[2] - bbox[0] <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word

                    if current_line:
                        lines.append(current_line)

                    # Draw description lines
                    for line in lines[:2]:  # Limit to 2 lines
                        desc_bbox = draw.textbbox((0, 0), line, font=desc_font)
                        desc_width = desc_bbox[2] - desc_bbox[0]
                        desc_x = (self.image_width - desc_width) // 2
                        draw.text(
                            (desc_x, y_position + 45),
                            line,
                            fill="orange",
                            font=desc_font,
                        )
                        y_position += 35

                y_position += spacing

                if y_position > self.image_height - 100:
                    break

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bank_nh_pavilion_newly_announced_{timestamp}.png"
            slide_path = self.output_folder / filename
            img.save(slide_path)
            logger.info(f"Created newly announced events slide: {slide_path}")
            return slide_path
        except Exception as e:
            logger.error(f"Failed to create newly announced events slide: {e}")
            return None

    async def _create_news_slide(self, content: dict) -> Path | None:
        """Create a slide for WMUR news headlines."""
        try:
            # Create image
            img = Image.new("RGB", (self.image_width, self.image_height), color="black")
            draw = ImageDraw.Draw(img)

            # Try to load a font, fall back to default if not available
            try:
                title_font = ImageFont.truetype("Arial.ttf", 70)
                headline_font = ImageFont.truetype("Arial.ttf", 45)
                category_font = ImageFont.truetype("Arial.ttf", 30)
            except OSError:
                title_font = ImageFont.load_default()
                headline_font = ImageFont.load_default()
                category_font = ImageFont.load_default()

            # Draw title
            title = "WMUR News - Latest Headlines"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.image_width - title_width) // 2
            draw.text((title_x, 80), title, fill="white", font=title_font)

            # Draw headlines
            y_position = 180
            spacing = 70
            for news_item in content.get("content", [])[:5]:  # Limit to 5 headlines
                headline = news_item.get("title", "Unknown Headline").title()
                category = news_item.get("category", "")

                # Draw category if available
                if category:
                    category_bbox = draw.textbbox((0, 0), category, font=category_font)
                    category_width = category_bbox[2] - category_bbox[0]
                    category_x = (self.image_width - category_width) // 2
                    draw.text(
                        (category_x, y_position),
                        category,
                        fill="orange",
                        font=category_font,
                    )
                    y_position += 50

                # Draw headline
                headline_bbox = draw.textbbox((0, 0), headline, font=headline_font)
                headline_width = headline_bbox[2] - headline_bbox[0]
                headline_x = (self.image_width - headline_width) // 2
                draw.text(
                    (headline_x, y_position),
                    headline,
                    fill="lightgreen",
                    font=headline_font,
                )
                y_position += spacing

                if y_position > self.image_height - 100:
                    break

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wmur_news_{timestamp}.png"
            slide_path = self.output_folder / filename
            img.save(slide_path)
            logger.info(f"Created news slide: {slide_path}")
            return slide_path
        except Exception as e:
            logger.error(f"Failed to create news slide: {e}")
            return None

    async def _create_generic_text_slide(self, content: dict) -> Path | None:
        """Create a generic text slide."""
        try:
            # Create image
            img = Image.new("RGB", (self.image_width, self.image_height), color="black")
            draw = ImageDraw.Draw(img)

            # Try to load a font
            try:
                title_font = ImageFont.truetype("Arial.ttf", 50)
                text_font = ImageFont.truetype("Arial.ttf", 30)
            except OSError:
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()

            # Draw title
            title = content.get("source", "web_content")
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.image_width - title_width) // 2
            draw.text((title_x, 50), title, fill="white", font=title_font)

            # Draw content
            y_position = 150
            for item in content.get("content", []):
                text = item.get("title", "") + ": " + item.get("text", "")
                draw.text(
                    (100, y_position), text[:100], fill="lightgray", font=text_font
                )
                y_position += 50

                if y_position > self.image_height - 100:
                    break

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_source = self.sanitize_filename(content.get("source", "web_content"))
            filename = f"{safe_source}_slide_{timestamp}.png"
            slide_path = self.output_folder / filename

            img.save(slide_path)
            logger.info(f"Created generic slide: {slide_path}")
            return slide_path

        except Exception as e:
            logger.error(f"Failed to create generic slide: {e}")
            return None

    @handle_error()
    async def extract_text_content(self, target: WebContentTarget) -> dict | None:
        """
        Extract and parse text content from a web page.

        Args:
            target: The web content target to extract from

        Returns:
            Dictionary containing parsed content or None if extraction failed
        """
        try:
            logger.info(f"Extracting text content from {target.name}")

            # Create a fresh browser instance for each extraction
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )

            page = await browser.new_page()

            # Set viewport size
            await page.set_viewport_size(
                {"width": self.image_width, "height": self.image_height}
            )

            # Set user agent
            await page.set_extra_http_headers({"User-Agent": self.user_agent})

            # Navigate to the URL
            await page.goto(target.url, wait_until="domcontentloaded", timeout=15000)
            # Wait a bit more for content to load
            await page.wait_for_timeout(3000)

            # Handle popups and overlays
            await self._handle_popups_and_overlays(page)

            # Parse content based on target type
            if "redrivertheatres" in target.url.lower():
                # Use specialized Red River Theater parser with HTML structure

                # Extract movie titles using the correct HTML selectors
                movie_data = await page.evaluate(
                    """
                    () => {
                        const movies = [];

                        // Look for movie titles in podsfilmtitle elements
                        const titleElements = document.querySelectorAll('.podsfilmtitle');
                        titleElements.forEach(el => {
                            const text = el.textContent.trim();
                            if (text && text.length > 3) {
                                // Determine if it's "Now Playing" or "Coming Up" based on position
                                // We'll use a simple heuristic: first 3 are "Now Playing", rest are "Coming Up"
                                movies.push({
                                    title: text,
                                    section: movies.length < 3 ? 'Now Playing' : 'Coming Up'
                                });
                            }
                        });

                        return movies;
                    }
                """
                )

                # Create structured content for the parser
                content: dict[str, str | list[dict[str, str]]] = {
                    "source": "Red River Theater",
                    "type": "theater_movies",
                    "content": [],
                }

                for movie in movie_data:
                    content_list = content["content"]
                    if isinstance(content_list, list):
                        content_list.append(
                            {
                                "title": movie["title"],
                                "section": movie["section"],
                                "type": "movie",
                            }
                        )

                await page.close()
                await browser.close()
                await playwright.stop()

                return content
            elif "themusichall" in target.url.lower():
                # Use specialized Music Hall parser with HTML structure
                music_hall_content: dict[
                    str, str | list[dict[str, str]]
                ] | None = await self._extract_music_hall_events(page)

                await page.close()
                await browser.close()
                await playwright.stop()

                if music_hall_content is None:
                    return {"error": "Failed to extract Music Hall events"}

                return music_hall_content
            elif "ccanh" in target.url.lower():
                # Use specialized Capitol Center parser with HTML structure
                capitol_content: dict[
                    str, str | list[dict[str, str]]
                ] | None = await self._extract_capitol_center_events(page)

                await page.close()
                await browser.close()
                await playwright.stop()

                if capitol_content is None:
                    return {"error": "Failed to extract Capitol Center events"}

                return capitol_content
            elif "wmur" in target.url.lower():
                # Use specialized WMUR news parser
                from src.services.wmur_parser import parse_wmur_content

                # Extract text content for parsing
                all_text = await page.evaluate(
                    """
                    () => {
                        // Get text from specific content areas, excluding CSS and scripts
                        const contentSelectors = [
                            '.elementor-container',
                            '.main-content',
                            '.content-area',
                            'main',
                            'article'
                        ];

                        let content = '';
                        for (const selector of contentSelectors) {
                            const elements = document.querySelectorAll(selector);
                            for (const element of elements) {
                                // Skip elements that are likely CSS or scripts
                                if (element.tagName === 'STYLE' || element.tagName === 'SCRIPT') {
                                    continue;
                                }
                                const text = element.textContent || element.innerText;
                                if (text && text.trim().length > 50) {  // Only significant content
                                    content += text + '\\n';
                                }
                            }
                        }

                        // If no content found, fall back to body text but filter out CSS
                        if (!content.trim()) {
                            const bodyText = document.body.textContent || document.body.innerText;
                            // Remove CSS-like content
                            const lines = bodyText.split('\\n');
                            const filteredLines = lines.filter(line => {
                                const trimmed = line.trim();
                                return trimmed &&
                                       !trimmed.startsWith('{') &&
                                       !trimmed.startsWith('}') &&
                                       !trimmed.includes('font-family:') &&
                                       !trimmed.includes('color:') &&
                                       !trimmed.includes('background:') &&
                                       !trimmed.includes('var ') &&
                                       !trimmed.includes('function(') &&
                                       trimmed.length > 3;
                            });
                            content = filteredLines.join('\\n');
                        }

                        return content;
                    }
                """
                )

                await page.close()
                await browser.close()
                await playwright.stop()

                return parse_wmur_content(all_text)
            elif "banknhpavilion" in target.url.lower():
                # Use specialized Bank NH Pavilion parser with HTML structure
                bank_nh_content: dict[
                    str, str | list[dict[str, str]]
                ] | None = await self._extract_bank_nh_pavilion_events(page)

                await page.close()
                await browser.close()
                await playwright.stop()

                if bank_nh_content is None:
                    return {"error": "Failed to extract Bank NH Pavilion events"}

                return bank_nh_content
            else:
                # Generic content extraction
                # Extract text content for parsing
                all_text = await page.evaluate(
                    """
                    () => {
                        // Get text from specific content areas, excluding CSS and scripts
                        const contentSelectors = [
                            '.elementor-container',
                            '.main-content',
                            '.content-area',
                            'main',
                            'article'
                        ];

                        let content = '';
                        for (const selector of contentSelectors) {
                            const elements = document.querySelectorAll(selector);
                            for (const element of elements) {
                                // Skip elements that are likely CSS or scripts
                                if (element.tagName === 'STYLE' || element.tagName === 'SCRIPT') {
                                    continue;
                                }
                                const text = element.textContent || element.innerText;
                                if (text && text.trim().length > 50) {  // Only significant content
                                    content += text + '\\n';
                                }
                            }
                        }

                        // If no content found, fall back to body text but filter out CSS
                        if (!content.trim()) {
                            const bodyText = document.body.textContent || document.body.innerText;
                            // Remove CSS-like content
                            const lines = bodyText.split('\\n');
                            const filteredLines = lines.filter(line => {
                                const trimmed = line.trim();
                                return trimmed &&
                                       !trimmed.startsWith('{') &&
                                       !trimmed.startsWith('}') &&
                                       !trimmed.includes('font-family:') &&
                                       !trimmed.includes('color:') &&
                                       !trimmed.includes('background:') &&
                                       !trimmed.includes('var ') &&
                                       !trimmed.includes('function(') &&
                                       trimmed.length > 3;
                            });
                            content = filteredLines.join('\\n');
                        }

                        return content;
                    }
                """
                )

                await page.close()
                await browser.close()
                await playwright.stop()

                return {
                    "source": target.name,
                    "type": "generic_content",
                    "content": [
                        {"title": target.name, "text": all_text, "type": "text"}
                    ],
                }

        except Exception as e:
            logger.error(f"Failed to extract text content from {target.name}: {e}")
            return None

    async def _handle_popups_and_overlays(self, page: Page) -> None:
        """Handle popups and overlays that might interfere with content extraction."""
        try:
            # Common popup selectors
            popup_selectors = [
                ".popup",
                ".modal",
                ".overlay",
                ".cookie-banner",
                ".newsletter-popup",
                ".ad-popup",
                '[class*="popup"]',
                '[class*="modal"]',
                '[class*="overlay"]',
            ]

            for selector in popup_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        try:
                            await element.evaluate("el => el.style.display = 'none'")
                            logger.debug(f"Hidden popup: {selector}")
                        except Exception as e:
                            logger.debug(f"Failed to hide popup {selector}: {e}")
                except Exception as e:
                    logger.debug(f"Failed to handle popup element: {e}")
        except Exception as e:
            logger.debug(f"Popup handling error: {e}")

    @handle_error()
    async def capture_screenshot(self, target: WebContentTarget) -> Path | None:
        """Capture a screenshot of the specified web target."""
        try:
            logger.info(f"Starting screenshot capture for {target.name}")

            # Create a fresh browser instance for each screenshot to avoid conflicts
            logger.info("Creating fresh browser instance...")
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )
            logger.info("Fresh browser instance created successfully")

            # Create a new page
            logger.info("Creating new browser page...")
            try:
                # Add a timeout for page creation
                import asyncio

                page = await asyncio.wait_for(browser.new_page(), timeout=10.0)
                logger.info("Browser page created successfully")
            except asyncio.TimeoutError:
                logger.error("Timeout creating browser page")
                await browser.close()
                await playwright.stop()
                return None
            except Exception as e:
                logger.error(f"Failed to create browser page: {e}")
                await browser.close()
                await playwright.stop()
                return None

            # Set viewport size
            logger.info(
                f"Setting viewport size: {self.image_width}x{self.image_height}"
            )
            await page.set_viewport_size(
                {"width": self.image_width, "height": self.image_height}
            )

            # Set user agent
            logger.info(f"Setting user agent: {self.user_agent}")
            await page.set_extra_http_headers({"User-Agent": self.user_agent})

            # Navigate to the URL
            logger.info(f"Navigating to {target.url}")
            await page.goto(target.url, timeout=self.timeout)
            logger.info("Navigation completed")

            # Wait for the page to load
            logger.info("Waiting for page to load...")
            await page.wait_for_load_state("networkidle", timeout=self.timeout)
            logger.info("Page load completed")

            # Try to find the selector (handle multiple selectors separated by commas)
            selectors = [s.strip() for s in target.selector.split(",")]
            element = None

            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    element = await page.wait_for_selector(selector, timeout=10000)
                    if element:
                        logger.info(f"Found element with selector: {selector}")
                        break
                except Exception as e:
                    logger.warning(
                        f"Selector '{selector}' not found for {target.name}: {e}"
                    )
                    continue

            # Use sanitized name for filename
            safe_name = self.sanitize_filename(target.name)
            screenshot_path = (
                self.output_folder
                / f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            if element:
                await element.screenshot(path=str(screenshot_path))
                logger.info(f"Screenshot captured for {target.name}: {screenshot_path}")
                logger.info("Closing browser page...")
                await page.close()
                logger.info("Closing browser...")
                await browser.close()
                logger.info("Stopping Playwright...")
                await playwright.stop()
                logger.info("Screenshot capture completed successfully")
                return screenshot_path
            else:
                logger.warning(
                    f"No selectors found for {target.name}. Selectors tried: {selectors}"
                )
                logger.info(
                    "No specific element found, capturing full page screenshot..."
                )
                logger.info(f"Saving screenshot to: {screenshot_path}")
                await page.screenshot(path=str(screenshot_path))
                logger.info(
                    f"Full page screenshot captured for {target.name}: {screenshot_path}"
                )
                logger.info("Closing browser page...")
                await page.close()
                logger.info("Closing browser...")
                await browser.close()
                logger.info("Stopping Playwright...")
                await playwright.stop()
                logger.info("Screenshot capture completed successfully")
                return screenshot_path

        except Exception as e:
            logger.error(f"Failed to capture screenshot for {target.name}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Clean up browser resources on error
            try:
                if "page" in locals():
                    await page.close()
                if "browser" in locals():
                    await browser.close()
                if "playwright" in locals():
                    await playwright.stop()
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")
            return None

    @handle_error()
    async def sync_all_targets(self) -> list[Path]:
        """Process all enabled targets using appropriate method (screenshots or text extraction)."""
        if not self.web_config.get("enabled", False):
            logger.info("Web content service is disabled")
            return []

        logger.info(f"Starting web content sync for {len(self.targets)} targets")

        # Clean up ALL existing slides before starting new sync
        await self._cleanup_all_existing_slides()

        captured_files = []

        for target in self.targets:
            if target.enabled:
                # Check if this target should use text extraction (has a parser)
                if self._should_use_text_extraction(target):
                    logger.info(f"Using text extraction for {target.name}")
                    content = await self.extract_text_content(target)
                    if content:
                        slide_paths = await self.create_text_slide_images(content)
                        captured_files.extend(slide_paths)
                else:
                    logger.info(f"Using screenshot capture for {target.name}")
                    screenshot_path = await self.capture_screenshot(target)
                    if screenshot_path:
                        captured_files.append(screenshot_path)

        # Cleanup old files (this is now redundant but kept for safety)
        if self.should_cleanup_old_files:
            await self.cleanup_old_files()

        logger.info(f"Web content sync completed. Created {len(captured_files)} files")
        return captured_files

    def _should_use_text_extraction(self, target: WebContentTarget) -> bool:
        """Determine if a target should use text extraction instead of screenshot capture."""
        url_lower = target.url.lower()

        # Targets that have specialized parsers
        parser_targets = [
            "redrivertheatres.org",  # Red River Theater parser
            "themusichall.org",  # Music Hall parser
            "ccanh.com",  # Capitol Center parser
            "banknhpavilion.com",  # Bank NH Pavilion parser
        ]

        return any(parser_url in url_lower for parser_url in parser_targets)

    async def _cleanup_all_existing_slides(self) -> None:
        """Remove ALL existing slides before starting a new sync to prevent duplicates."""
        try:
            deleted_count = 0
            # Only remove PNG files (slides), not JSON tracking files
            for file_path in self.output_folder.glob("*.png"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted existing slide: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete existing slide {file_path}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} existing slides before sync")
            else:
                logger.info("No existing slides to clean up")
        except Exception as e:
            logger.error(f"Error cleaning up existing slides: {e}")

    async def cleanup_old_files(self) -> None:
        """Remove old screenshot files based on max_file_age_hours."""
        if not self.should_cleanup_old_files:
            return

        cutoff_time = datetime.now() - timedelta(hours=self.max_file_age_hours)
        deleted_count = 0

        # Only remove PNG files (slides), not JSON tracking files
        for file_path in self.output_folder.glob("*.png"):
            if file_path.stat().st_mtime < cutoff_time.timestamp():
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old screenshot: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete old screenshot {file_path}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old screenshot files")

    async def _cleanup_old_red_river_slides(self) -> None:
        """Remove old Red River Theater slides before creating new ones."""
        try:
            deleted_count = 0
            # Only remove PNG files (slides), not JSON tracking files
            for file_path in self.output_folder.glob("red_river_*.png"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old Red River slide: {file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete old Red River slide {file_path}: {e}"
                    )

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old Red River Theater slides")
        except Exception as e:
            logger.error(f"Error cleaning up old Red River slides: {e}")

    async def _cleanup_old_music_hall_slides(self) -> None:
        """Remove old Music Hall slides before creating new ones."""
        try:
            deleted_count = 0
            # Only remove PNG files (slides), not JSON tracking files
            for file_path in self.output_folder.glob("music_hall_*.png"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old Music Hall slide: {file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete old Music Hall slide {file_path}: {e}"
                    )

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old Music Hall slides")
        except Exception as e:
            logger.error(f"Error cleaning up old Music Hall slides: {e}")

    async def _cleanup_old_capitol_center_slides(self) -> None:
        """Remove old Capitol Center slides before creating new ones."""
        try:
            deleted_count = 0
            # Only remove PNG files (slides), not JSON tracking files
            for file_path in self.output_folder.glob("capitol_center_*.png"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old Capitol Center slide: {file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete old Capitol Center slide {file_path}: {e}"
                    )

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old Capitol Center slides")
        except Exception as e:
            logger.error(f"Error cleaning up old Capitol Center slides: {e}")

    async def _cleanup_old_wmur_slides(self) -> None:
        """Remove old WMUR news slides before creating new ones."""
        try:
            deleted_count = 0
            # Only remove PNG files (slides), not JSON tracking files
            for file_path in self.output_folder.glob("wmur_*.png"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old WMUR slide: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete old WMUR slide {file_path}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old WMUR slides")
        except Exception as e:
            logger.error(f"Error cleaning up old WMUR slides: {e}")

    async def _cleanup_old_bank_nh_pavilion_slides(self) -> None:
        """Remove old Bank NH Pavilion slides before creating new ones."""
        try:
            deleted_count = 0
            # Only remove PNG files (slides), not JSON tracking files
            for file_path in self.output_folder.glob("bank_nh_pavilion_*.png"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old Bank NH Pavilion slide: {file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete old Bank NH Pavilion slide {file_path}: {e}"
                    )

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old Bank NH Pavilion slides")
        except Exception as e:
            logger.error(f"Error cleaning up old Bank NH Pavilion slides: {e}")

    def get_available_screenshots(self) -> list[Path]:
        """Get list of available screenshot files."""
        if not self.output_folder.exists():
            return []

        return list(self.output_folder.glob("*.png"))

    def get_target_by_name(self, name: str) -> WebContentTarget | None:
        """Get a target by name."""
        for target in self.targets:
            if target.name == name:
                return target
        return None

    def is_enabled(self) -> bool:
        """Check if the web content service is enabled."""
        return bool(self.web_config.get("enabled", False))

    async def _extract_music_hall_events(
        self, page: Page
    ) -> dict[str, str | list[dict[str, str]]] | None:
        """Extract and process Music Hall events."""
        from src.services.music_hall_parser import EventInfo as MusicHallEventInfo
        from src.services.music_hall_parser import MusicHallParser

        # Extract events using HTML selectors
        events_data = await page.evaluate(
            """
            () => {
                const events = [];

                // Look for event titles in performance__title elements
                const titleElements = document.querySelectorAll('.performance__title');
                titleElements.forEach(el => {
                    const title = el.textContent.trim();
                    if (title && title.length > 3) {
                        let date = '';

                        // Find the calendar day that contains this event
                        const calendarDay = el.closest('.day');
                        if (calendarDay) {
                            // Get the day number from the calendar
                            const dayLabel = calendarDay.querySelector('.day__labels');
                            if (dayLabel) {
                                const dayText = dayLabel.textContent.trim();
                                // Extract just the day number
                                const dayMatch = dayText.match(/(\\d{1,2})/);
                                if (dayMatch) {
                                    const day = dayMatch[1];

                                    // Get the current month/year from the calendar navigation
                                    const monthNav = document.querySelector('.navigation__month-current');
                                    if (monthNav) {
                                        const monthText = monthNav.textContent.trim();
                                        // Extract month and year
                                        const monthMatch = monthText.match(/([A-Za-z]+)\\s+(\\d{4})/);
                                        if (monthMatch) {
                                            const month = monthMatch[1];
                                            const year = monthMatch[2];
                                            date = `${month} ${day}, ${year}`;
                                        } else {
                                            // Fallback: just use day
                                            date = day;
                                        }
                                    } else {
                                        // Fallback: just use day
                                        date = day;
                                    }
                                }
                            }
                        }

                        // If no date found from calendar, try to find it in the event title or nearby text
                        if (!date) {
                            const parentSection = el.closest('section');
                            if (parentSection) {
                                const sectionText = parentSection.textContent;

                                // Try multiple date patterns to catch different formats
                                const datePatterns = [
                                    // Full date formats: "Thursday, July 17, 2025"
                                    /([A-Za-z]+,\\s+[A-Za-z]+\\s+\\d{1,2},\\s+\\d{4})/,
                                    // Date without year: "Thursday, July 17"
                                    /([A-Za-z]+,\\s+[A-Za-z]+\\s+\\d{1,2})/,
                                    // Date without comma: "Thursday July 17"
                                    /([A-Za-z]+\\s+[A-Za-z]+\\s+\\d{1,2})/,
                                    // Numeric formats: "7/17/2025", "7/17"
                                    /(\\d{1,2}\\/\\d{1,2}\\/\\d{4})/,
                                    /(\\d{1,2}\\/\\d{1,2})/,
                                    // Month day format: "July 17"
                                    /([A-Za-z]+\\s+\\d{1,2})/
                                ];

                                for (const pattern of datePatterns) {
                                    const dateMatch = sectionText.match(pattern);
                                    if (dateMatch) {
                                        date = dateMatch[1].trim();
                                        break;
                                    }
                                }
                            }
                        }

                        events.push({
                            title: title,
                            date: date
                        });
                    }
                });

                return events;
            }
        """
        )

        # Process events with tracking logic
        parser = MusicHallParser()

        current_events = []
        for event_data in events_data:
            event = MusicHallEventInfo(
                title=event_data["title"], date=event_data["date"]
            )
            current_events.append(event)

        # Remove duplicates
        unique_events = list({event.title: event for event in current_events}.values())

        # Filter out past events first
        future_events = [
            event for event in unique_events if parser._is_future_event(event)
        ]

        # Sort by date (earliest first)
        future_events.sort(key=lambda x: parser._parse_date(x.date))

        # Limit to next 5 upcoming events
        upcoming_events = future_events[:5]

        # Find new events (not in previous events)
        new_events = []
        for event in upcoming_events:
            if event not in parser.previous_events:
                new_events.append(event)

        # Save current events for next comparison
        parser._save_events(upcoming_events)

        # Use the improved parser logic to prioritize newly announced events
        parsed_data = {"all_events": upcoming_events, "new_events": new_events}

        return parser.create_formatted_content(parsed_data)

    async def _extract_bank_nh_pavilion_events(
        self, page: Page
    ) -> dict[str, str | list[dict[str, str]]] | None:
        """Extract and process Bank NH Pavilion events."""
        from src.services.bank_nh_pavilion_parser import BankNHPavilionParser
        from src.services.bank_nh_pavilion_parser import EventInfo as BankNHEventInfo

        # Extract events using HTML selectors
        events_data = await page.evaluate(
            """
            () => {
                const events = [];

                // Look for event titles in showBox elements
                const showBoxes = document.querySelectorAll('.showBox');
                showBoxes.forEach(box => {
                    const titleElement = box.querySelector('.title');
                    const dateElement = box.querySelector('.showDate');

                    if (titleElement) {
                        const title = titleElement.textContent.trim();
                        let date = '';
                        let description = '';

                        // Get date from showDate element
                        if (dateElement) {
                            date = dateElement.textContent.trim();
                        }

                        // Build description from supporting artists and tour info
                        const smallElements = box.querySelectorAll('.small');
                        const smallerElements = box.querySelectorAll('.smaller');
                        const microElements = box.querySelectorAll('.micro');

                        const descriptionParts = [];

                        // Add supporting artists
                        smallElements.forEach(el => {
                            const text = el.textContent.trim();
                            if (text && text !== 'LIVE NATION PRESENTS') {
                                descriptionParts.push(text);
                            }
                        });

                        smallerElements.forEach(el => {
                            const text = el.textContent.trim();
                            if (text) {
                                descriptionParts.push(text);
                            }
                        });

                        // Add tour info
                        microElements.forEach(el => {
                            const text = el.textContent.trim();
                            if (text && text !== 'LIVE NATION PRESENTS') {
                                descriptionParts.push(text);
                            }
                        });

                        description = descriptionParts.join(' • ');

                        if (title && title.length > 3) {
                            events.push({
                                title: title,
                                date: date,
                                description: description
                            });
                        }
                    }
                });

                return events;
            }
        """
        )

        # Process events with tracking logic
        parser = BankNHPavilionParser()

        current_events = []
        for event_data in events_data:
            event = BankNHEventInfo(
                title=event_data["title"],
                date=event_data["date"],
                description=event_data["description"],
            )
            current_events.append(event)

        # Remove duplicates
        unique_events = list({event.title: event for event in current_events}.values())

        # Filter out past events first
        future_events = [
            event for event in unique_events if parser._is_future_event(event)
        ]

        # Sort by date (earliest first)
        future_events.sort(key=lambda x: parser._parse_date(x.date))

        # Limit to next 5 upcoming events
        upcoming_events = future_events[:5]

        # Find new events (not in previous events)
        new_events = []
        for event in upcoming_events:
            if event not in parser.previous_events:
                new_events.append(event)

        # Save current events for next comparison
        parser._save_events(upcoming_events)

        # Use the improved parser logic to prioritize newly announced events
        parsed_data = {"all_events": upcoming_events, "new_events": new_events}

        return parser.create_formatted_content(parsed_data)

    async def _extract_capitol_center_events(
        self, page: Page
    ) -> dict[str, str | list[dict[str, str]]] | None:
        """Extract and process Capitol Center events."""
        from src.services.capitol_center_parser import CapitolCenterParser
        from src.services.capitol_center_parser import EventInfo as CapitolEventInfo

        # Extract events using HTML selectors
        events_data = await page.evaluate(
            """
            () => {
                const events = [];

                // Look for event titles in h3 elements
                const titleElements = document.querySelectorAll('h3');
                titleElements.forEach(el => {
                    const title = el.textContent.trim();
                    if (title && title.length > 5) {
                        let date = '';
                        let venue = '';

                        // Find the parent container to get date and venue info
                        const parent = el.closest('div, section, article');
                        if (parent) {
                            const parentText = parent.textContent.trim();

                            // Look for date in div.date elements
                            const dateElement = parent.querySelector('.date');
                            if (dateElement) {
                                date = dateElement.textContent.trim();
                            } else {
                                // Fallback: look for date patterns in parent text
                                const datePatterns = [
                                    /\\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2}\\b/gi,
                                    /\\b\\d{1,2}\\/\\d{1,2}\\/\\d{4}\\b/g,
                                    /\\b\\d{1,2}\\/\\d{1,2}\\b/g
                                ];

                                for (const pattern of datePatterns) {
                                    const match = parentText.match(pattern);
                                    if (match) {
                                        date = match[0];
                                        break;
                                    }
                                }
                            }

                            // Look for venue information
                            const venuePatterns = [
                                /\\b(Chubb|BNH|Theatre|Stage|Concord)\\b/gi,
                                /\\b(Chubb Theatre|Bank of NH Stage)\\b/gi
                            ];

                            for (const pattern of venuePatterns) {
                                const match = parentText.match(pattern);
                                if (match) {
                                    venue = match[0];
                                    break;
                                }
                            }
                        }

                        events.push({
                            title: title,
                            date: date,
                            venue: venue
                        });
                    }
                });

                return events;
            }
        """
        )

        # Process events with tracking logic
        parser = CapitolCenterParser()

        current_events = []
        for event_data in events_data:
            event = CapitolEventInfo(
                title=event_data["title"],
                date=event_data["date"],
                venue=event_data["venue"],
            )
            current_events.append(event)

        # Remove duplicates
        unique_events = list({event.title: event for event in current_events}.values())

        # Filter out past events first
        future_events = [
            event for event in unique_events if parser._is_future_event(event)
        ]

        # Sort by date (earliest first)
        future_events.sort(key=lambda x: parser._parse_date(x.date))

        # Limit to next 5 upcoming events
        upcoming_events = future_events[:5]

        # Find new events (not in previous events)
        new_events = []
        for event in upcoming_events:
            if event not in parser.previous_events:
                new_events.append(event)

        # Save current events for next comparison
        parser._save_events(upcoming_events)

        # Use the improved parser logic to prioritize newly announced events
        parsed_data = {"all_events": upcoming_events, "new_events": new_events}

        return parser.create_formatted_content(parsed_data)


# Convenience function for creating the service
def create_web_content_service(config_manager: ConfigManager) -> WebContentService:
    """Create and return a WebContentService instance."""
    return WebContentService(config_manager)
