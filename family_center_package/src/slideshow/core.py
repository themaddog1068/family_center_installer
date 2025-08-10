"""Core slideshow functionality for the Family Center application."""

import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from PIL import Image

# Register HEIF opener for HEIC support
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

from src.config.config_manager import ConfigManager
from src.core.logging_config import get_logger
from src.services.time_based_weighting import TimeBasedWeightingService

# Try to import video and color processing dependencies
VIDEO_SUPPORT = True
try:
    import cv2
except ImportError:
    VIDEO_SUPPORT = False
    cv2 = None

# Try to import pygame for better video playback
PYGAME_SUPPORT = True
try:
    import pygame as pygame_module
except ImportError:
    PYGAME_SUPPORT = False
    pygame_module = None

COLOR_ANALYSIS = True
try:
    from colorthief import ColorThief
except ImportError:
    COLOR_ANALYSIS = False
    ColorThief = None

# Try to import GUI dependencies, but allow for headless operation
TKINTER_AVAILABLE = True
try:
    import tkinter as tk
    from tkinter import ttk

    from PIL import ImageTk
except ImportError:
    TKINTER_AVAILABLE = False
    tk = cast(Any, None)
    ttk = cast(Any, None)
    ImageTk = cast(Any, None)

logger = get_logger(__name__)


class MediaItem:
    """Represents a media item (image or video) in the slideshow."""

    def __init__(self, file_path: Path, media_type: str):
        self.file_path = file_path
        self.media_type = media_type  # 'image' or 'video'
        self.duration = None  # For videos, this will be set to actual duration
        self.display_duration = None  # For images, this is the slide duration


class SlideshowEngine:
    """Main slideshow engine for displaying media files."""

    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        headless: bool = False,
        video_only: bool = False,
        pi_sim: bool = False,
    ) -> None:
        """Initialize the slideshow engine.

        Args:
            config_manager: Configuration manager instance
            headless: Run in headless mode (no GUI display)
            video_only: Show only video files in the slideshow
            pi_sim: Simulate Raspberry Pi environment
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.config
        self.headless = headless or not TKINTER_AVAILABLE
        self.video_only = video_only
        self.pi_sim = pi_sim

        if not self.headless and not TKINTER_AVAILABLE:
            logger.warning("tkinter not available, running in headless mode")
            self.headless = True

        # Load slideshow configuration
        self.slideshow_config = self.config.get("slideshow", {})
        self.display_config = self.config.get("display", {})

        # Initialize display properties
        self.screen_width = self.display_config.get("resolution", {}).get("width", 1000)
        self.screen_height = self.display_config.get("resolution", {}).get(
            "height", 700
        )
        self.fullscreen = self.display_config.get("fullscreen", False)
        self.background_color: str = self.display_config.get(
            "background_color", "#000000"
        )

        # Initialize slideshow properties
        self.media_directory = Path(
            self.slideshow_config.get("media_directory", "media")
        )
        self.shuffle_enabled = self.slideshow_config.get("shuffle_enabled", True)
        self.slide_duration = self.slideshow_config.get("slide_duration_seconds", 10)
        logger.info(f"Slide duration configured: {self.slide_duration} seconds")
        self.supported_image_formats = set(
            self.slideshow_config.get(
                "supported_image_formats",
                [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            )
        )
        self.supported_video_formats = set(
            self.slideshow_config.get(
                "supported_video_formats", [".mp4", ".avi", ".mov", ".wmv", ".mkv"]
            )
        )

        # Sprint 3: Enhanced configuration options
        self.transitions_config = self.slideshow_config.get("transitions", {})
        self.video_config = self.slideshow_config.get("video_playback", {})
        self.date_prioritization_config = self.slideshow_config.get(
            "date_prioritization", {}
        )
        self.background_config = self.slideshow_config.get("background", {})
        self.weighted_media_config = self.slideshow_config.get("weighted_media", {})

        # Sprint 3: Transition settings
        self.transitions_enabled = self.transitions_config.get("enabled", True)
        self.transition_type = self.transitions_config.get("type", "crossfade")
        self.transition_duration = self.transitions_config.get("duration_seconds", 1.0)
        self.ease_type = self.transitions_config.get("ease_type", "linear")

        # Sprint 3: Video settings
        self.video_enabled = self.video_config.get("enabled", True) and (
            VIDEO_SUPPORT or PYGAME_SUPPORT
        )
        self.video_autoplay = self.video_config.get("autoplay", True)
        self.video_loop = self.video_config.get("loop_videos", False)
        self.video_mute = self.video_config.get("mute_audio", True)  # Read from config

        # Sprint 3: Date prioritization settings
        self.date_prioritization_enabled = self.date_prioritization_config.get(
            "enabled", True
        )
        self.newer_bias = self.date_prioritization_config.get("newer_bias", 0.7)
        self.days_considered_new = self.date_prioritization_config.get(
            "days_considered_new", 30
        )
        self.creation_date_weight = self.date_prioritization_config.get(
            "creation_date_weight", 0.3
        )

        # Sprint 3: Background settings
        self.use_complementary_colors = self.background_config.get(
            "use_complementary_colors", True
        )
        self.fallback_color: str = self.background_config.get(
            "fallback_color", "#000000"
        )
        self.brightness_adjustment = self.background_config.get(
            "brightness_adjustment", 0.3
        )

        # Sprint 3: Weighted media settings
        self.weighted_media_enabled = bool(
            self.weighted_media_config.get("sources", [])
        )
        self.weighted_sources = self.weighted_media_config.get("sources", [])
        self.playlist_size = self.weighted_media_config.get("playlist_size", 20)
        self.reshuffle_interval = self.weighted_media_config.get(
            "reshuffle_interval", 10
        )
        self.strict_weights = self.weighted_media_config.get("strict_weights", True)

        # Sprint 7: Initialize time-based weighting service
        self.time_weighting_service = TimeBasedWeightingService(self.config_manager)

        # Initialize state
        self.media_items: list[MediaItem] = []
        self.current_index = 0
        self.running = False
        self.transition_in_progress = False

        # Initialize UI components (only if not headless)
        self.root: Any = None
        self.canvas: Any = None
        self.current_image: Any = None
        self.current_pil_image: Image.Image | None = (
            None  # Store PIL image for transitions
        )
        self.next_image: Any = None  # For transitions
        self._temp_photo: Any = None  # For transition blending

        # Pygame video playback components
        self.pygame_screen: Any = None
        self.video_playing = False
        self.video_duration = 10  # Default video duration in seconds
        self.video_process: Any = None
        self.video_thread: Any = None
        self.video_path: Path | None = None
        self.video_stop_event: Any = None  # Threading event for stopping video

        if not VIDEO_SUPPORT and not PYGAME_SUPPORT and self.video_enabled:
            logger.warning(
                "Video support not available (opencv-python or pygame not installed)"
            )
            self.video_enabled = False

        if not COLOR_ANALYSIS and self.use_complementary_colors:
            logger.warning("Color analysis not available (colorthief not installed)")
            self.use_complementary_colors = False

        # Initialize pygame if available
        self._init_pygame()

    def _init_pygame(self) -> None:
        """Initialize pygame for video playback."""
        global pygame_module
        if PYGAME_SUPPORT and pygame_module is not None:
            try:
                # Only initialize mixer, not the full pygame display
                pygame_module.mixer.init()
                logger.info("Pygame mixer initialized successfully for audio playback")
            except Exception as e:
                logger.warning(f"Failed to initialize pygame mixer: {e}")
                pygame_module = None

    def discover_media_files(self) -> list[Path]:
        """Discover all supported media files in the media directory.

        Returns:
            List of media file paths
        """
        logger.info(f"Discovering media files in {self.media_directory}")
        media_files: list[Path] = []

        # Use weighted media sources if enabled
        if self.weighted_media_enabled and self.weighted_sources:
            logger.info("Using weighted media sources for file discovery")

            # Sprint 7: Apply time-based weighting to sources
            weighted_sources = self.time_weighting_service.get_weighted_media_sources(
                self.weighted_sources
            )

            # Log time-based weighting summary
            weighting_summary = self.time_weighting_service.get_weighting_summary()
            if weighting_summary["enabled"]:
                logger.info(
                    f"Time-based weighting active - Hour: {weighting_summary['current_hour']}, "
                    f"Weights: {weighting_summary['current_weights']}"
                )

            for source in weighted_sources:
                if not source.get("enabled", True):
                    continue

                folder_path = Path(source.get("folder", "media"))
                weight = source.get("weight", 1.0)
                name = source.get("name", "unknown")

                logger.info(
                    f"Discovering files in {name} ({folder_path}) with weight {weight}"
                )

                if not folder_path.exists():
                    logger.warning(f"Media directory does not exist: {folder_path}")
                    continue

                # Recursively find all supported media files in this source
                source_files = []
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file():
                        suffix = file_path.suffix.lower()
                        if suffix in self.supported_image_formats:
                            source_files.append(file_path)
                            logger.debug(f"Found image in {name}: {file_path}")
                        elif (
                            suffix in self.supported_video_formats
                            and self.video_enabled
                        ):
                            source_files.append(file_path)
                            logger.debug(f"Found video in {name}: {file_path}")

                # Apply weight to files from this source
                weighted_count = int(len(source_files) * weight)

                # Ensure at least one file is included if files are available
                if len(source_files) > 0 and weighted_count == 0:
                    weighted_count = 1
                    logger.debug(
                        f"Ensuring at least one file from {name} (weight {weight} would result in 0 files)"
                    )

                # Ensure we don't lose all files due to very small weights
                if len(source_files) > 0 and weighted_count < len(source_files) * 0.1:
                    weighted_count = max(1, int(len(source_files) * 0.1))
                    logger.debug(
                        f"Adjusting {name} from {int(len(source_files) * weight)} to {weighted_count} files "
                        f"(weight {weight} was too small)"
                    )

                if self.strict_weights and weighted_count < len(source_files):
                    # Randomly sample files based on weight
                    source_files = random.sample(
                        source_files, weighted_count
                    )  # nosec B311

                media_files.extend(source_files)
                logger.info(f"Added {len(source_files)} files from {name}")
        else:
            # Use traditional single directory approach
            if not self.media_directory.exists():
                logger.warning(
                    f"Media directory does not exist: {self.media_directory}"
                )
                return media_files

            # Recursively find all supported media files
            for file_path in self.media_directory.rglob("*"):
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    if suffix in self.supported_image_formats:
                        media_files.append(file_path)
                        logger.debug(f"Found image: {file_path}")
                    elif suffix in self.supported_video_formats and self.video_enabled:
                        # Sprint 3: Include video files when video support is enabled
                        media_files.append(file_path)
                        logger.debug(f"Found video: {file_path}")

        logger.info(f"Discovered {len(media_files)} supported media files")

        # Filter for video-only if requested
        if self.video_only:
            len(media_files)
            # Instead of filtering to only videos, prioritize videos but include all media
            video_files = [
                f
                for f in media_files
                if f.suffix.lower() in self.supported_video_formats
            ]
            other_files = [
                f
                for f in media_files
                if f.suffix.lower() in self.supported_image_formats
            ]

            # Put videos first, then other files
            media_files = video_files + other_files
            logger.info(
                f"Video-only mode: prioritized {len(video_files)} videos, included {len(other_files)} other files (total: {len(media_files)})"
            )

            if len(media_files) == 0:
                logger.warning(
                    "No media files found. Please ensure media files are available in the media directory."
                )
                return []

        # Sprint 3: Apply date-based prioritization to media files
        if self.date_prioritization_enabled:
            media_files = self._apply_date_prioritization(media_files)

        return media_files

    def _apply_date_prioritization(self, media_files: list[Path]) -> list[Path]:
        """Apply date-based prioritization to media files.

        Args:
            media_files: List of media file paths

        Returns:
            Reordered list with newer files having higher priority
        """
        # Check if date prioritization is disabled
        if not self.date_prioritization_enabled:
            logger.debug("Date prioritization is disabled")
            return media_files

        logger.info("Applying date-based prioritization to media files")

        try:
            current_time = datetime.now()
            cutoff_date = current_time - timedelta(days=self.days_considered_new)

            # Categorize files by age
            new_files = []
            old_files = []

            for file_path in media_files:
                try:
                    # Try to get Google Drive metadata first (for remote_drive files)
                    file_mtime = None
                    if "remote_drive" in str(file_path):
                        # For Google Drive files, try to get metadata from tracking
                        try:
                            from src.config import Config
                            from src.services.google_drive import GoogleDriveService

                            config = Config()
                            drive_service = GoogleDriveService(config)

                            # Look for file in tracking data by path
                            for (
                                _file_id,
                                tracking_info,
                            ) in drive_service.file_tracking.items():
                                if tracking_info.get("path") == str(file_path):
                                    modified_time_str = tracking_info.get(
                                        "modified_time"
                                    )
                                    if modified_time_str:
                                        # Parse Google Drive timestamp
                                        file_mtime = datetime.fromisoformat(
                                            modified_time_str.replace("Z", "+00:00")
                                        )
                                        break
                        except Exception as e:
                            logger.debug(
                                f"Could not get Google Drive metadata for {file_path}: {e}"
                            )

                    # Fall back to local file modification time
                    if file_mtime is None:
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

                    if file_mtime >= cutoff_date:
                        new_files.append(file_path)
                    else:
                        old_files.append(file_path)
                except (OSError, ValueError) as e:
                    logger.debug(
                        f"Could not get modification time for {file_path}: {e}"
                    )
                    old_files.append(
                        file_path
                    )  # Default to old if we can't determine age

            logger.info(
                f"Categorized {len(new_files)} new files, {len(old_files)} older files"
            )

            # Create weighted playlist
            weighted_files = []

            # Add newer files with higher frequency based on newer_bias
            new_file_count = int(len(media_files) * self.newer_bias)
            for _ in range(new_file_count):
                if new_files:
                    weighted_files.append(random.choice(new_files))  # nosec B311
                elif old_files:
                    weighted_files.append(random.choice(old_files))  # nosec B311

            # Fill remaining slots with older files
            remaining_slots = len(media_files) - len(weighted_files)
            for _ in range(remaining_slots):
                if old_files:
                    weighted_files.append(random.choice(old_files))  # nosec B311
                elif new_files:
                    weighted_files.append(random.choice(new_files))  # nosec B311

            return weighted_files

        except Exception as e:
            logger.error(f"Error applying date prioritization: {e}")
            return media_files  # Return original list if prioritization fails

    def shuffle_playlist(self) -> None:
        """Shuffle the media files playlist if shuffle is enabled."""
        if self.shuffle_enabled and self.media_items:
            logger.info("Shuffling media playlist")
            random.shuffle(self.media_items)  # nosec B311
            self.current_index = 0

    def load_and_resize_image(self, image_path: Path) -> Image.Image | None:
        """Load and resize an image while preserving aspect ratio.

        Args:
            image_path: Path to the image file

        Returns:
            Resized PIL Image or None if loading failed
        """
        try:
            logger.debug(f"Loading image: {image_path}")
            image = Image.open(image_path)

            # Convert to RGB if necessary (for compatibility)
            if image.mode in ("RGBA", "P"):
                background = Image.new("RGB", image.size, (0, 0, 0))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(
                    image, mask=image.split()[-1] if image.mode == "RGBA" else None
                )
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Use the new _resize_image_to_fit method for consistent scaling behavior
            resized_image = self._resize_image_to_fit(image)

            logger.debug(f"Resized image from {image.size} to {resized_image.size}")

            return resized_image

        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            return None

    def create_canvas_image(self, pil_image: Image.Image) -> Any:
        """Create a canvas-ready image with background padding.

        Args:
            pil_image: PIL Image to prepare for canvas

        Returns:
            ImageTk.PhotoImage ready for display (GUI mode) or PIL Image (headless mode)
        """
        # This method is kept for backward compatibility
        # New code should use _create_canvas_image_with_color
        return self._create_canvas_image_with_color(pil_image, self.background_color)

    def _create_canvas_image_with_color(
        self, pil_image: Image.Image, bg_color: str
    ) -> Any:
        """Create a canvas image with a colored background.

        Args:
            pil_image: PIL Image to display
            bg_color: Background color as hex string

        Returns:
            Canvas image object
        """
        if self.headless or not TKINTER_AVAILABLE:
            return pil_image

        # Create a new image with the background color
        bg_image = Image.new("RGB", (self.screen_width, self.screen_height), bg_color)

        # Resize the original image to fit the screen
        resized_image = self._resize_image_to_fit(pil_image)

        # Calculate position to center the image
        x_offset = (self.screen_width - resized_image.width) // 2
        y_offset = (self.screen_height - resized_image.height) // 2

        # Paste the resized image onto the background
        bg_image.paste(resized_image, (x_offset, y_offset))

        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(bg_image)

        return photo

    def setup_window(self) -> None:
        """Set up the tkinter window for the slideshow."""
        if self.headless:
            logger.info("Running in headless mode - no GUI window")
            return

        if not TKINTER_AVAILABLE or tk is None:
            raise RuntimeError("tkinter not available for GUI mode")

        self.root = tk.Tk()
        self.root.title("Family Center Slideshow")
        self.root.configure(bg=self.background_color)

        # Configure window size and fullscreen
        if self.fullscreen:
            self.root.attributes("-fullscreen", True)
            # Get actual screen dimensions when in fullscreen
            self.root.update_idletasks()
            self.screen_width = self.root.winfo_screenwidth()
            self.screen_height = self.root.winfo_screenheight()
        else:
            self.root.geometry(f"{self.screen_width}x{self.screen_height}")

        # Create canvas for image display
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            bg=self.background_color,
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind escape key to exit
        self.root.bind("<Escape>", lambda e: self.stop())
        self.root.bind("<q>", lambda e: self.stop())

        logger.info(
            f"Window setup complete: {self.screen_width}x{self.screen_height}, fullscreen={self.fullscreen}"
        )

    def display_current_slide(self) -> None:
        """Display the current slide in the slideshow."""
        if not self.media_items:
            return

        current_item = self.media_items[self.current_index]
        logger.info(
            f"Displaying slide {self.current_index + 1}/{len(self.media_items)}: {current_item.file_path.name}"
        )

        try:
            if current_item.media_type == "video":
                # Handle video files
                self._play_video_file(current_item.file_path)
            else:
                # Handle image files
                pil_image = self.load_and_resize_image(current_item.file_path)
                if pil_image is None:
                    # Skip to next image if current one failed to load
                    self.next_slide()
                    return

                # Use enhanced display with complementary colors
                self._display_image_content(pil_image, current_item.file_path)

        except Exception as e:
            logger.error(f"Failed to display slide {current_item.file_path}: {e}")
            self.next_slide()

    def next_slide(self) -> None:
        """Advance to the next slide."""
        if not self.media_items:
            return

        self.current_index = (self.current_index + 1) % len(self.media_items)

        # If we've completed a full cycle and shuffle is enabled, reshuffle
        if self.current_index == 0 and self.shuffle_enabled:
            self.shuffle_playlist()

    def previous_slide(self) -> None:
        """Go back to the previous slide."""
        if not self.media_items:
            return

        self.current_index = (self.current_index - 1) % len(self.media_items)

    def slideshow_loop(self) -> None:
        """Main slideshow loop that advances slides automatically."""
        if self.running and self.media_items:
            # Display the current slide
            self.display_current_slide()

            # Get current media item
            current_item = self.media_items[self.current_index]

            # Handle timing based on media type
            if current_item.media_type == "video":
                # Videos are handled by pygame - they play to completion
                # The _on_video_complete method will handle advancing
                logger.info("Video playing - will advance when complete")
            else:
                # Images use timed duration
                logger.info(f"Image slide duration: {self.slide_duration} seconds")

                # Schedule next slide after the slide duration
            if not self.headless and self.root:
                delay_ms = int(self.slide_duration * 1000)
                logger.info(
                    f"Scheduling next slide in {delay_ms}ms ({self.slide_duration}s)"
                )
                self.root.after(delay_ms, self._advance_slide)
            elif self.headless:
                # In headless mode, use time.sleep for demo purposes
                # In production, this would be handled differently
                time.sleep(self.slide_duration)
                if self.running:
                    self._advance_slide()

    def _advance_slide(self) -> None:
        """Advance to the next slide and continue the slideshow loop."""
        if self.running and self.media_items:
            logger.info("Advancing to next slide")
            self.next_slide()
            self.slideshow_loop()

    def start(self) -> None:
        """Start the slideshow."""
        logger.info(f"Starting slideshow engine (headless={self.headless})")

        # Discover media files
        media_files = self.discover_media_files()
        if not media_files:
            if self.video_only:
                logger.error(
                    "No video files found for video-only mode. Please ensure video files are available in the media directory."
                )
                logger.info(
                    "You can add video files to media/remote_drive/ or media/local_drive/ directories."
                )
            else:
                logger.error("No media files found. Cannot start slideshow.")
                logger.info(
                    "Please ensure media files are available in the media directory."
                )
            return

        # Create media item objects
        self.media_items = [
            MediaItem(
                file_path,
                "image"
                if file_path.suffix.lower() in self.supported_image_formats
                else "video",
            )
            for file_path in media_files
        ]

        # Shuffle if enabled
        self.shuffle_playlist()

        # Setup window (only if not headless)
        self.setup_window()

        # Start slideshow loop
        self.running = True

        if self.headless:
            logger.info("Starting headless slideshow loop")
            # For headless mode, just demonstrate functionality
            # In a real implementation, this might save images or serve them via web interface
            try:
                for _ in range(
                    min(3, len(self.media_items))
                ):  # Just show first 3 slides in demo
                    if self.running:
                        self.display_current_slide()
                        time.sleep(1)  # Short delay for demo
                        self.next_slide()
            except KeyboardInterrupt:
                logger.info("Headless slideshow interrupted by user")
                self.stop()
        else:
            self.slideshow_loop()

            # Start tkinter main loop
            if self.root:
                logger.info("Starting tkinter main loop")
                try:
                    self.root.mainloop()
                except KeyboardInterrupt:
                    logger.info("Slideshow interrupted by user")
                    self.stop()

    def stop(self) -> None:
        """Stop the slideshow."""
        logger.info("Stopping slideshow engine")
        self.running = False

        # Stop any playing video
        self._stop_video()

        if not self.headless and self.root:
            self.root.quit()
            self.root.destroy()

    def _get_complementary_color(self, image_path: Path) -> str:
        """Extract complementary color from an image for background.

        Args:
            image_path: Path to the image file

        Returns:
            Hex color string for complementary background
        """
        if not COLOR_ANALYSIS or ColorThief is None:
            return self.fallback_color

        try:
            # Get dominant color from image
            color_thief = ColorThief(str(image_path))
            dominant_color = color_thief.get_color(quality=1)

            # Calculate complementary color (opposite on color wheel)
            r, g, b = dominant_color

            # Convert RGB to HSV for color wheel calculations
            r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
            max_val = max(r_norm, g_norm, b_norm)
            min_val = min(r_norm, g_norm, b_norm)
            diff = max_val - min_val

            # Calculate hue
            if diff == 0:
                hue = 0
            elif max_val == r_norm:
                hue = (60 * ((g_norm - b_norm) / diff) + 360) % 360
            elif max_val == g_norm:
                hue = (60 * ((b_norm - r_norm) / diff) + 120) % 360
            else:
                hue = (60 * ((r_norm - g_norm) / diff) + 240) % 360

            # Get complementary hue (180 degrees opposite)
            comp_hue = (hue + 180) % 360

            # Calculate saturation and value
            saturation = 0 if max_val == 0 else diff / max_val
            value = max_val

            # Adjust brightness
            value = max(0.1, min(1.0, value * (1.0 - self.brightness_adjustment)))

            # Convert HSV back to RGB
            c = value * saturation
            x = c * (1 - abs((comp_hue / 60) % 2 - 1))
            m = value - c

            if 0 <= comp_hue < 60:
                r_comp, g_comp, b_comp = c, x, 0
            elif 60 <= comp_hue < 120:
                r_comp, g_comp, b_comp = x, c, 0
            elif 120 <= comp_hue < 180:
                r_comp, g_comp, b_comp = 0, c, x
            elif 180 <= comp_hue < 240:
                r_comp, g_comp, b_comp = 0, x, c
            elif 240 <= comp_hue < 300:
                r_comp, g_comp, b_comp = x, 0, c
            else:
                r_comp, g_comp, b_comp = c, 0, x

            # Convert to 0-255 range
            r_final = int((r_comp + m) * 255)
            g_final = int((g_comp + m) * 255)
            b_final = int((b_comp + m) * 255)

            # Return as hex color
            return f"#{r_final:02x}{g_final:02x}{b_final:02x}"

        except Exception as e:
            logger.debug(
                f"Could not extract complementary color from {image_path}: {e}"
            )
            return self.fallback_color

    def _is_video_file(self, file_path: Path) -> bool:
        """Check if a file is a video file.

        Args:
            file_path: Path to check

        Returns:
            True if the file is a video file
        """
        return file_path.suffix.lower() in self.supported_video_formats

    def _get_video_thumbnail(self, video_path: Path) -> Image.Image | None:
        """Extract a thumbnail from a video file.

        Args:
            video_path: Path to the video file

        Returns:
            PIL Image thumbnail or None if extraction failed
        """
        if not VIDEO_SUPPORT or cv2 is None:
            return None

        try:
            # Open video file
            cap = cv2.VideoCapture(str(video_path))

            if not cap.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                return None

            # Get total frame count and seek to middle frame
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            middle_frame = total_frames // 2

            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)

            # Read frame
            ret, frame = cap.read()
            cap.release()

            if not ret:
                logger.error(f"Could not read frame from video: {video_path}")
                return None

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to PIL Image
            return Image.fromarray(frame_rgb)

        except Exception as e:
            logger.error(f"Error extracting thumbnail from video {video_path}: {e}")
            return None

    def _play_video_file(self, video_path: Path) -> None:
        """Play video file using pygame for integrated playback."""
        logger.info(f"Playing video with pygame: {video_path}")

        # Try to set stop event if it exists
        if hasattr(self, "video_stop_event") and self.video_stop_event:
            try:
                self.video_stop_event.set()
            except Exception as e:
                logger.debug(f"Error setting stop event: {e}")

        # Check if pygame is available for video playback
        if PYGAME_SUPPORT and pygame_module is not None:
            logger.info("Using pygame for video playback")
            self._play_with_pygame(video_path)
        else:
            logger.warning("Pygame not available, using thumbnail fallback")
            self._fallback_to_thumbnail(video_path)

    def _fallback_to_thumbnail(self, video_path: Path) -> None:
        """Fallback to showing video thumbnail when native player is not available."""
        thumbnail = self._get_video_thumbnail(video_path)
        if thumbnail:
            self._display_image_content(thumbnail, video_path)
            # Use slide duration for thumbnail display
            if self.root and self.running:
                self.root.after(
                    int(self.slide_duration * 1000), self._on_video_complete
                )
        else:
            self.next_slide()

    def _stop_video(self) -> None:
        """Stop any currently playing video."""
        if self.video_playing and pygame_module is not None:
            try:
                pygame_module.mixer.music.stop()
                self.video_playing = False
            except Exception as e:
                logger.debug(f"Error stopping video: {e}")

        # Stop native video player process if running
        if hasattr(self, "video_process") and self.video_process is not None:
            try:
                import subprocess  # nosec B404

                # Try graceful termination first
                self.video_process.terminate()

                # Wait a bit for graceful shutdown
                try:
                    self.video_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.video_process.kill()
                    self.video_process.wait()

                self.video_process = None
                logger.info("Native video player process stopped")
            except Exception as e:
                logger.debug(f"Error stopping video process: {e}")

        # Clean up pygame screen if needed
        if self.pygame_screen and pygame_module is not None:
            try:
                pygame_module.quit()
                self.pygame_screen = None
            except Exception as e:
                logger.debug(f"Error cleaning up pygame: {e}")

    def _on_video_complete(self) -> None:
        """Called when video playback completes."""
        logger.info("Video playback completed")
        self._stop_video()
        self.next_slide()
        self.slideshow_loop()

    def _resize_image_to_fit(self, pil_image: Image.Image) -> Image.Image:
        """Resize image to fit within the screen while maintaining aspect ratio.

        Args:
            pil_image: PIL Image to resize

        Returns:
            Resized PIL Image that fits within the screen without cropping
        """
        # Calculate aspect ratios
        img_width, img_height = pil_image.size
        screen_ratio = self.screen_width / self.screen_height
        img_ratio = img_width / img_height

        # Determine scaling approach based on configuration
        scaling_mode = self.slideshow_config.get("scaling_mode", "fit_within")

        if scaling_mode == "fill_screen":
            # Fill screen by cropping
            if img_ratio > screen_ratio:
                # Image is wider than screen - fit to height and crop width
                new_height = self.screen_height
                new_width = int(self.screen_height * img_ratio)
            else:
                # Image is taller than screen - fit to width and crop height
                new_width = self.screen_width
                new_height = int(self.screen_width / img_ratio)

            # Resize image to fill screen
            resized_image = pil_image.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )

            # Crop to exact screen dimensions if needed
            if new_width > self.screen_width or new_height > self.screen_height:
                left = (
                    (new_width - self.screen_width) // 2
                    if new_width > self.screen_width
                    else 0
                )
                top = (
                    (new_height - self.screen_height) // 2
                    if new_height > self.screen_height
                    else 0
                )
                right = left + self.screen_width
                bottom = top + self.screen_height
                resized_image = resized_image.crop((left, top, right, bottom))
        else:
            # Default behavior: fit within screen without cropping
            if img_ratio > screen_ratio:
                # Image is wider than screen - fit to width
                new_width = self.screen_width
                new_height = int(self.screen_width / img_ratio)
            else:
                # Image is taller than screen - fit to height
                new_height = self.screen_height
                new_width = int(self.screen_height * img_ratio)

            # Resize image to fit within screen
            resized_image = pil_image.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )

        return resized_image

    def _display_image_content(self, pil_image: Image.Image, source_path: Path) -> None:
        """Display image content with appropriate background.

        Args:
            pil_image: PIL Image to display
            source_path: Original file path for color analysis
        """
        # Store PIL image for transitions
        self.current_pil_image = pil_image.copy()

        # Determine background color
        if self.use_complementary_colors and not self._is_video_file(source_path):
            background_color = self._get_complementary_color(source_path)
        else:
            background_color = self.background_color

        # Add matted frame effect if enabled
        mat_config = self.slideshow_config.get("mat_frame", {})
        mat_enabled = mat_config.get("enabled", True)

        if mat_enabled:
            # Create matted frame effect
            matted_image = self._create_matted_frame(pil_image, mat_config)
            # Create canvas image with calculated background
            canvas_image = self._create_canvas_image_with_color(
                matted_image, background_color
            )
        else:
            # Create canvas image with calculated background (no mat effect)
            canvas_image = self._create_canvas_image_with_color(
                pil_image, background_color
            )

        if not self.headless and self.canvas and tk is not None:
            # Apply transition if enabled
            if self.transitions_enabled and not self.transition_in_progress:
                self._apply_transition(canvas_image)
            else:
                self._display_on_canvas(canvas_image)
        else:
            self.current_image = canvas_image

    def _create_matted_frame(
        self, pil_image: Image.Image, mat_config: dict
    ) -> Image.Image:
        """Create a matted frame effect around the image.

        Args:
            pil_image: PIL Image to add mat frame to
            mat_config: Configuration for the mat effect

        Returns:
            PIL Image with matted frame effect
        """
        # Get mat configuration
        mat_width = mat_config.get("width", 80)  # Width of mat border in pixels
        mat_color_setting = mat_config.get("color", "white")  # Color setting
        show_border = mat_config.get("show_border", True)  # Whether to show border
        border_width = (
            mat_config.get("border_width", 4) if show_border else 0
        )  # Border width
        border_color = mat_config.get("border_color", "#000000")  # Border color

        # Get image dimensions
        img_width, img_height = pil_image.size

        # Calculate matted frame dimensions
        matted_width = img_width + (mat_width * 2)
        matted_height = img_height + (mat_width * 2)

        # If mat_width is 0 but border_width > 0, ensure border is still added
        if mat_width == 0 and border_width > 0:
            matted_width = img_width + (border_width * 2)
            matted_height = img_height + (border_width * 2)

        # Determine mat color based on configuration
        if mat_color_setting == "complementary_dark":
            # Get complementary color for the current image
            # For core engine, we'll use a fallback since we don't have the same color cache
            mat_color = mat_config.get("fallback_mat_color", "#FFFFFF")
        elif mat_color_setting.startswith("#"):
            # Direct hex color
            mat_color = mat_color_setting
        else:
            # Named color or fallback
            color_map = {
                "white": "#FFFFFF",
                "black": "#000000",
                "cream": "#F5F5DC",
                "beige": "#F5F5DC",
                "gray": "#808080",
            }
            mat_color = color_map.get(
                mat_color_setting.lower(),
                mat_config.get("fallback_mat_color", "#FFFFFF"),
            )

        # Create matted surface
        matted_image = Image.new("RGB", (matted_width, matted_height), mat_color)

        # Add border if specified
        if border_width > 0:
            # Create inner border image
            border_width_total = img_width + (border_width * 2)
            border_height_total = img_height + (border_width * 2)
            border_image = Image.new(
                "RGB", (border_width_total, border_height_total), border_color
            )

            # Place image on border image
            border_image.paste(pil_image, (border_width, border_width))

            # Place bordered image on mat image
            matted_image.paste(
                border_image,
                (
                    (matted_width - border_width_total) // 2,
                    (matted_height - border_height_total) // 2,
                ),
            )
        else:
            # Place image directly on mat image
            matted_image.paste(
                pil_image,
                ((matted_width - img_width) // 2, (matted_height - img_height) // 2),
            )

        return matted_image

    def _apply_transition(self, new_image: Any) -> None:
        """Apply transition effect when changing slides.

        Args:
            new_image: New image to transition to
        """
        if self.transition_type == "crossfade":
            self._crossfade_transition(new_image)
        else:
            # No transition or unsupported type - display immediately
            self._display_on_canvas(new_image)

    def _crossfade_transition(self, new_image: Any) -> None:
        """Apply crossfade transition effect.

        Args:
            new_image: New image to transition to
        """
        if self.headless or not self.canvas or tk is None:
            # Just display the new image in headless mode
            self.current_image = new_image
            return

        self.transition_in_progress = True

        try:
            # Store the current image for the transition
            old_image = self.current_image

            # Create a smooth crossfade effect
            steps = 20  # Number of steps for the transition
            step_duration = int(
                (self.transition_duration * 1000) / steps
            )  # Duration per step

            def fade_step(step: int) -> None:
                if not self.running or step >= steps:
                    # Transition complete
                    self.current_image = new_image
                    self.transition_in_progress = False
                    return

                # Calculate alpha for the new image (0.0 to 1.0)
                alpha = step / steps

                # Clear canvas
                self.canvas.delete("all")

                # Simple crossfade: gradually show the new image
                # For now, use a basic approach that works reliably
                if alpha < 0.5:
                    # Show old image
                    if old_image:
                        self.canvas.create_image(
                            self.screen_width // 2,
                            self.screen_height // 2,
                            image=old_image,
                            anchor=tk.CENTER,
                        )
                else:
                    # Show new image
                    self.canvas.create_image(
                        self.screen_width // 2,
                        self.screen_height // 2,
                        image=new_image,
                        anchor=tk.CENTER,
                    )

                # Schedule next step
                if self.root and self.running:
                    self.root.after(step_duration, lambda: fade_step(step + 1))

            # Start the fade transition
            fade_step(0)

        except Exception as e:
            logger.error(f"Error during crossfade transition: {e}")
            # Fallback to direct display
            self._display_on_canvas(new_image)
            self.transition_in_progress = False

    def _display_on_canvas(self, image: Any) -> None:
        """Display image directly on canvas without transition.

        Args:
            image: Image to display
        """
        if self.headless or not self.canvas or tk is None:
            self.current_image = image
            return

        try:
            # Clear canvas and display new image
            self.canvas.delete("all")
            self.canvas.create_image(
                self.screen_width // 2,
                self.screen_height // 2,
                image=image,
                anchor=tk.CENTER,
            )
            self.current_image = image

        except Exception as e:
            logger.error(f"Error displaying image on canvas: {e}")

    def _play_with_pygame(self, video_path: Path) -> None:
        """Play video using pygame for integrated display."""

        try:
            # Initialize pygame display if not already done
            if not self.pygame_screen and pygame_module is not None:
                pygame_module.init()
                # Create a hidden pygame screen for video processing
                self.pygame_screen = pygame_module.display.set_mode(
                    (1, 1), pygame_module.HIDDEN
                )

            # Get video duration (estimate based on file size for now)
            # In a full implementation, you'd use a proper video library
            duration = self.slide_duration  # Use slide duration for consistent timing

            logger.info(f"Starting pygame video playback for {duration} seconds")

            # For now, show a video indicator and use slide duration
            # In a full implementation, you'd decode and display actual video frames
            self.video_playing = True

            # Create a video indicator image
            indicator_text = f"VIDEO: {video_path.name}"
            if pygame_module is not None:
                # Create a simple video indicator surface
                font = pygame_module.font.Font(None, 36)
                text_surface = font.render(indicator_text, True, (255, 255, 255))
                text_rect = text_surface.get_rect(
                    center=(self.screen_width // 2, self.screen_height // 2)
                )

                # Create background surface
                video_surface = pygame_module.Surface(
                    (self.screen_width, self.screen_height)
                )
                video_surface.fill((0, 0, 0))  # Black background
                video_surface.blit(text_surface, text_rect)

                # Convert pygame surface to PIL image for tkinter display
                video_string = pygame_module.image.tostring(video_surface, "RGB")
                video_image = Image.frombytes(
                    "RGB", (self.screen_width, self.screen_height), video_string
                )

                # Display the video indicator
                self._display_image_content(video_image, video_path)

            # Schedule video completion after slide duration
            if self.root and self.running:
                self.root.after(
                    int(self.slide_duration * 1000), self._on_video_complete
                )

            logger.info(
                f"Pygame video playback started for {self.slide_duration} seconds"
            )

        except Exception as e:
            logger.error(f"Failed to start pygame video: {e}")
            self._fallback_to_thumbnail(video_path)


def main() -> None:
    """Main entry point for running the slideshow."""
    try:
        # Use headless mode if tkinter is not available
        headless = not TKINTER_AVAILABLE
        engine = SlideshowEngine(headless=headless)
        engine.start()
    except KeyboardInterrupt:
        logger.info("Slideshow interrupted by user")
    except Exception as e:
        logger.error(f"Slideshow failed: {e}")
        raise


if __name__ == "__main__":
    main()
