"""
Pygame-based slideshow engine for the Family Center application.

This provides a more integrated solution with native video playback,
smooth transitions, and better performance than the tkinter version.
"""

import logging
import os
import random
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pygame
from PIL import Image

# Register HEIC support
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    logging.info("HEIC support enabled via pillow-heif.")
except ImportError:
    logging.warning("pillow-heif not installed. HEIC images will not be supported.")

from src.config.config_manager import ConfigManager
from src.core.logging_config import get_logger

# Try to import color processing dependencies
COLOR_ANALYSIS = True
try:
    from colorthief import ColorThief
except ImportError:
    COLOR_ANALYSIS = False
    ColorThief = None

logger = get_logger(__name__)


class MediaItem:
    """Represents a media item (image or video) in the slideshow."""

    def __init__(self, file_path: Path, media_type: str):
        self.file_path = file_path
        self.media_type = media_type  # 'image' or 'video'
        self.duration = None  # For videos, this will be set to actual duration
        self.display_duration = None  # For images, this is the slide duration


class PygameSlideshowEngine:
    """Pygame-based slideshow engine for displaying media files."""

    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        video_only: bool = False,
        pi_sim: bool = False,
    ) -> None:
        """Initialize the pygame slideshow engine.

        Args:
            config_manager: Configuration manager instance
            video_only: Show only video files in the slideshow
            pi_sim: Simulate Raspberry Pi environment
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.config
        self.video_only = video_only
        self.pi_sim = pi_sim

        # Load slideshow configuration
        self.slideshow_config = self.config.get("slideshow", {})
        self.display_config = self.config.get("display", {})

        # Initialize display properties
        self.screen_width = self.display_config.get("resolution", {}).get("width", 1280)
        self.screen_height = self.display_config.get("resolution", {}).get(
            "height", 800
        )
        self.fullscreen = self.display_config.get("fullscreen", True)
        self.background_color = self.display_config.get("background_color", "#000000")

        # Initialize slideshow properties
        self.media_directory = Path(
            self.slideshow_config.get("media_directory", "media")
        )
        self.shuffle_enabled = self.slideshow_config.get("shuffle_enabled", True)
        self.slide_duration = self.slideshow_config.get("slide_duration_seconds", 5)
        logger.info(f"Slide duration configured: {self.slide_duration} seconds")

        self.supported_image_formats = set(
            self.slideshow_config.get(
                "supported_image_formats",
                [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif"],
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
        self.crossfade_duration = self.transition_duration  # Add crossfade_duration
        self.ease_type = self.transitions_config.get("ease_type", "linear")

        # Sprint 3: Video settings
        self.video_enabled = self.video_config.get("enabled", True)
        self.video_autoplay = self.video_config.get("autoplay", True)
        self.video_loop = self.video_config.get("loop_videos", False)
        self.video_mute = self.video_config.get("mute_audio", True)

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
        self.fallback_color = self.background_config.get("fallback_color", "#000000")
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

        # Initialize state
        self.media_items: list[MediaItem] = []
        self.current_index = 0
        self.running = False
        self.transition_in_progress = False

        # Initialize pygame components
        self.screen: pygame.Surface | None = None
        self.clock: pygame.time.Clock | None = None
        self.current_surface: pygame.Surface | None = None
        self.next_surface: pygame.Surface | None = None
        self.video_playing = False
        self.video_surface: pygame.Surface | None = None
        self.video_thread: threading.Thread | None = None
        self.video_stop_event: threading.Event | None = None
        self.video_process = None  # Add video_process attribute

        # Image cache for preloaded images
        self.image_cache: dict[str, pygame.Surface] = {}
        # Cache for complementary colors
        self.complementary_color_cache: dict[str, str] = {}

        # Initialize pygame
        self._init_pygame()

    def _init_pygame(self) -> None:
        """Initialize pygame for slideshow display."""
        try:
            pygame.init()

            # Set display flags
            flags = pygame.FULLSCREEN if self.fullscreen else 0

            # Create the display
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height), flags
            )
            pygame.display.set_caption("Family Center Slideshow")

            # Initialize clock for timing
            self.clock = pygame.time.Clock()

            # Initialize mixer for audio
            if not self.video_mute:
                pygame.mixer.init()

            logger.info(
                f"Pygame initialized: {self.screen_width}x{self.screen_height}, fullscreen={self.fullscreen}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize pygame: {e}")
            raise

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
            for source in self.weighted_sources:
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
                        # Skip temp folder for weather files
                        if name == "Weather" and "temp" in str(file_path):
                            continue

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

    def load_and_resize_image(self, image_path: Path) -> pygame.Surface | None:
        """Load and resize an image to fit the screen.

        Args:
            image_path: Path to the image file

        Returns:
            Pygame surface with the resized image, or None if loading failed
        """
        # Check cache first
        cache_key = str(image_path)
        if cache_key in self.image_cache:
            logger.debug(f"Using cached image: {image_path}")
            return self.image_cache[cache_key]

        try:
            # Load image with PIL
            with Image.open(image_path) as pil_image:
                # Convert to RGB if necessary
                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")

                # Resize to fit screen
                resized_pil = self._resize_image_to_fit(pil_image)

                # Convert to pygame surface
                size = resized_pil.size
                data = resized_pil.tobytes()

                pygame_image = pygame.image.fromstring(data, size, "RGB")

                # Cache the result
                self.image_cache[cache_key] = pygame_image

                return pygame_image

        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            return None

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
            # Original behavior: fill screen by cropping
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

    def _is_video_file(self, file_path: Path) -> bool:
        """Check if a file is a video file.

        Args:
            file_path: Path to check

        Returns:
            True if the file is a video file
        """
        return file_path.suffix.lower() in self.supported_video_formats

    def _get_video_thumbnail(self, video_path: Path) -> pygame.Surface | None:
        """Extract a thumbnail from a video file.

        Args:
            video_path: Path to the video file

        Returns:
            Pygame surface with video thumbnail or None if failed
        """
        try:
            # For now, create a simple video indicator
            # In a full implementation, you'd extract an actual frame
            surface = pygame.Surface((self.screen_width, self.screen_height))
            surface.fill((0, 0, 0))  # Black background

            # Create text indicator
            font = pygame.font.Font(None, 48)
            text = font.render(f"VIDEO: {video_path.name}", True, (255, 255, 255))
            text_rect = text.get_rect(
                center=(self.screen_width // 2, self.screen_height // 2)
            )
            surface.blit(text, text_rect)

            return surface

        except Exception as e:
            logger.error(f"Failed to create video thumbnail for {video_path}: {e}")
            return None

    def display_current_slide(self) -> None:
        logger.debug(
            f"[TRACE] Enter display_current_slide for index {self.current_index}"
        )
        if not self.media_items:
            return

        current_item = self.media_items[self.current_index]
        logger.info(
            f"Displaying slide {self.current_index + 1}/{len(self.media_items)}: {current_item.file_path.name}"
        )

        if current_item.media_type == "video":
            self._play_video_file(current_item.file_path)
        else:
            self._display_image_file(current_item.file_path)
        logger.debug(
            f"[TRACE] Exit display_current_slide for index {self.current_index}"
        )

    def _display_image_file(self, image_path: Path) -> None:
        logger.debug(f"[TRACE] Enter _display_image_file for {image_path}")
        # Load and resize image
        surface = self.load_and_resize_image(image_path)
        if not surface:
            logger.error(f"Failed to load image: {image_path}")
            # Instead of getting stuck, advance to next slide
            logger.info("Advancing to next slide due to failed image load")
            self.next_slide()
            if self.media_items:
                self.display_current_slide()
            return

        # Display immediately without transitions
        self._display_on_screen(surface)
        logger.debug(f"[TRACE] Exit _display_image_file for {image_path}")

    def _play_video_file(self, video_path: Path) -> None:
        """Play video file using opencv for frame extraction in pygame."""
        logger.info(f"Playing video with opencv: {video_path}")

        try:
            import cv2

            # Open video file
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                self._fallback_to_thumbnail(video_path)
                return

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_duration = frame_count / fps if fps > 0 else self.slide_duration

            logger.info(
                f"Video: {fps} fps, {frame_count} frames, {video_duration:.2f}s duration"
            )

            # Use slide duration for consistent timing
            display_duration = self.slide_duration

            # Show video frames for the slide duration
            start_time = pygame.time.get_ticks()
            frame_index = 0

            while cap.isOpened() and self.running:
                current_time = pygame.time.get_ticks()
                if current_time - start_time >= display_duration * 1000:
                    break

                # Calculate which frame to show based on elapsed time
                elapsed_time = (current_time - start_time) / 1000.0
                target_frame = int(elapsed_time * fps) if fps > 0 else frame_index

                # Ensure we don't go beyond the video length
                if target_frame >= frame_count:
                    break

                # Read the target frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = cap.read()
                if not ret:
                    break

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Resize frame to fit screen
                frame_pil = Image.fromarray(frame_rgb)
                frame_pil = self._resize_image_to_fit(frame_pil)

                # Convert to pygame surface
                frame_string = frame_pil.tobytes()
                frame_surface = pygame.image.fromstring(
                    frame_string, frame_pil.size, "RGB"
                )

                # Create background surface
                background_surface = pygame.Surface(
                    (self.screen_width, self.screen_height)
                )
                background_surface.fill((0, 0, 0))  # Black background

                # Center the frame on the background
                frame_rect = frame_surface.get_rect(
                    center=(self.screen_width // 2, self.screen_height // 2)
                )
                background_surface.blit(frame_surface, frame_rect)

                # Display frame
                if self.screen is not None:
                    self.screen.blit(background_surface, (0, 0))
                    pygame.display.flip()

                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False
                        elif event.key == pygame.K_RIGHT:
                            break  # Skip to next slide
                        elif event.key == pygame.K_LEFT:
                            break  # Skip to previous slide

                # Simple frame rate control
                pygame.time.wait(33)  # ~30 fps
                frame_index += 1

            # Clean up
            cap.release()

        except ImportError:
            logger.warning("opencv-python not available, using thumbnail")
            self._fallback_to_thumbnail(video_path)
        except Exception as e:
            logger.error(f"Error playing video {video_path}: {e}")
            self._fallback_to_thumbnail(video_path)

    def _fallback_to_thumbnail(self, video_path: Path) -> None:
        """Fallback to showing video thumbnail when video playback fails."""
        logger.info(f"Using thumbnail fallback for video: {video_path}")
        thumbnail_surface = self._get_video_thumbnail(video_path)
        if thumbnail_surface:
            self.current_surface = thumbnail_surface
            self._display_on_screen(thumbnail_surface)
            self.video_playing = True

    def _get_complementary_color(self, image_path: Path) -> str:
        """Extract complementary color from an image for background.

        Args:
            image_path: Path to the image file

        Returns:
            Hex color string for complementary background
        """
        if not COLOR_ANALYSIS or ColorThief is None:
            return str(self.fallback_color)

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
            return str(self.fallback_color)

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color string to RGB tuple.

        Args:
            hex_color: Hex color string (e.g., "#FF0000")

        Returns:
            RGB tuple (r, g, b)
        """
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return rgb[0], rgb[1], rgb[2]

    def _apply_transition(self, new_surface: pygame.Surface) -> None:
        """Apply transition effect when changing slides.

        Args:
            new_surface: New surface to transition to
        """
        if self.transitions_enabled and self.current_surface is not None:
            self._crossfade_transition(new_surface)
        else:
            # No transition or first slide - display immediately
            self._display_on_screen(new_surface)

    def _crossfade_transition(self, new_surface: pygame.Surface) -> None:
        """Apply crossfade transition effect.

        Args:
            new_surface: New surface to transition to
        """
        try:
            # Store the current surface for the transition
            old_surface = self.current_surface

            # Create a smooth crossfade effect
            steps = 30  # More steps for smoother transition
            step_duration = int(
                (self.transition_duration * 1000) / steps
            )  # Duration per step

            # Create blended surface
            blended_surface = pygame.Surface((self.screen_width, self.screen_height))

            # Calculate alpha for the new surface (0.0 to 1.0)
            alpha = 0.0
            alpha_step = 1.0 / steps

            for _step in range(steps):
                if not self.running:
                    break

                # Clear blended surface
                blended_surface.fill((0, 0, 0))

                if old_surface is not None:
                    # Show old surface with decreasing alpha
                    old_surface.set_alpha(int(255 * (1 - alpha)))
                    blended_surface.blit(old_surface, (0, 0))

                # Show new surface with increasing alpha
                new_surface.set_alpha(int(255 * alpha))
                blended_surface.blit(new_surface, (0, 0))

                # Display blended surface
                self._display_on_screen(blended_surface)

                # Wait for step duration
                pygame.time.wait(step_duration)

                # Update alpha
                alpha += alpha_step

            # Set final surface
            self.current_surface = new_surface

        except Exception as e:
            logger.error(f"Error during crossfade transition: {e}")
            # Fallback to direct display
            self._display_on_screen(new_surface)
            self.current_surface = new_surface

    def _get_complementary_color_for_display(self, image_path: Path) -> str:
        """Get the complementary color for display, using cache only - never compute at runtime."""
        # Normalize path for lookup
        norm_path = str(image_path.resolve()).lower()

        # Try multiple lookup strategies
        color = None

        # Strategy 1: Direct match
        color = self.complementary_color_cache.get(norm_path)

        # Strategy 2: Basename match (for legacy or mismatched paths)
        if not color:
            for k, v in self.complementary_color_cache.items():
                if Path(k).name.lower() == image_path.name.lower():
                    color = v
                    break

        # Strategy 3: Basename without extension match (for HEIC vs JPG mismatches)
        if not color:
            base_name = image_path.stem.lower()  # filename without extension
            for k, v in self.complementary_color_cache.items():
                if Path(k).stem.lower() == base_name:
                    color = v
                    logger.debug(
                        f"Found color for {image_path.name} via basename match: {color}"
                    )
                    break

        # Strategy 4: If no cached color found, use fallback (never compute at runtime)
        if not color or color == "#000000":
            logger.debug(
                f"No cached complementary color found for {image_path.name}, using fallback background"
            )
            color = self.background_color

        return color or self.background_color

    def _display_on_screen(self, surface: pygame.Surface) -> None:
        logger.debug(f"[TRACE] Enter _display_on_screen for index {self.current_index}")
        try:
            # Use improved complementary color lookup
            image_path = self.media_items[self.current_index].file_path
            background_color = self._get_complementary_color_for_display(image_path)

            # Create background surface
            background_surface = pygame.Surface((self.screen_width, self.screen_height))
            background_surface.fill(self._hex_to_rgb(background_color))

            # Add matted frame effect if enabled
            mat_config = self.slideshow_config.get("mat_frame", {})
            mat_enabled = mat_config.get("enabled", True)

            if mat_enabled and surface is not None:
                # Create matted frame effect
                matted_surface = self._create_matted_frame(surface, mat_config)

                # Center the matted image on the background
                image_rect = matted_surface.get_rect(
                    center=(self.screen_width // 2, self.screen_height // 2)
                )
                background_surface.blit(matted_surface, image_rect)
            elif surface is not None:
                # No mat effect - center the original image
                image_rect = surface.get_rect(
                    center=(self.screen_width // 2, self.screen_height // 2)
                )
                background_surface.blit(surface, image_rect)

            # Display the final surface
            screen = self.screen
            if screen is not None:
                screen.blit(background_surface, (0, 0))
                pygame.display.flip()
            # Store current surface
            self.current_surface = background_surface
        except Exception as e:
            logger.error(f"Error displaying surface on screen: {e}")
            # Fallback to direct display
            screen = self.screen
            if screen is not None and surface is not None:
                screen.blit(surface, (0, 0))
                pygame.display.flip()
                self.current_surface = surface
        logger.debug(f"[TRACE] Exit _display_on_screen for index {self.current_index}")

    def _create_matted_frame(
        self, image_surface: pygame.Surface, mat_config: dict
    ) -> pygame.Surface:
        """Create a matted frame effect around the image.

        Args:
            image_surface: Original image surface
            mat_config: Configuration for the mat effect

        Returns:
            New surface with matted frame effect
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
        img_width, img_height = image_surface.get_size()

        # Calculate matted frame dimensions
        matted_width = img_width + (mat_width * 2)
        matted_height = img_height + (mat_width * 2)

        # Determine mat color based on configuration
        if mat_color_setting == "complementary_dark":
            # Get complementary color for the current image
            image_path = self.media_items[self.current_index].file_path
            complementary_color = self._get_complementary_color_for_display(image_path)

            # Create darker version of complementary color
            dark_factor = mat_config.get("complementary_dark_factor", 0.6)
            if complementary_color and isinstance(complementary_color, str):
                mat_color = self._darken_color(complementary_color, dark_factor)
            else:
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
        matted_surface = pygame.Surface((matted_width, matted_height))
        matted_surface.fill(self._hex_to_rgb(str(mat_color)))

        # Add border if specified
        if border_width > 0:
            # Create border surface
            border_surface = pygame.Surface(
                (img_width + (border_width * 2), img_height + (border_width * 2))
            )
            border_surface.fill(self._hex_to_rgb(str(border_color)))

            # Place image on border surface
            border_surface.blit(image_surface, (border_width, border_width))

            # Place bordered image on mat surface
            matted_surface.blit(
                border_surface, (mat_width - border_width, mat_width - border_width)
            )
        else:
            # Place image directly on mat surface
            matted_surface.blit(image_surface, (mat_width, mat_width))

        return matted_surface

    def _darken_color(self, hex_color: str, factor: float) -> str:
        """Create a darker version of a hex color.

        Args:
            hex_color: Original hex color string
            factor: Darkening factor (0.0 = black, 1.0 = original color)

        Returns:
            Darkened hex color string
        """
        # Convert hex to RGB
        r, g, b = self._hex_to_rgb(hex_color)

        # Apply darkening factor
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def next_slide(self) -> None:
        """Advance to the next slide."""
        if self.media_items:
            self.current_index = (self.current_index + 1) % len(self.media_items)

    def previous_slide(self) -> None:
        """Go to the previous slide."""
        if self.media_items:
            self.current_index = (self.current_index - 1) % len(self.media_items)

    def _show_loading_screen(self, total: int, loaded: int) -> None:
        """Display a loading screen with a progress bar."""
        if not self.screen:
            return
        self.screen.fill((30, 30, 30))
        font = pygame.font.SysFont(None, 60)
        text = font.render("Loading images...", True, (200, 200, 200))
        self.screen.blit(
            text,
            (
                self.screen_width // 2 - text.get_width() // 2,
                self.screen_height // 2 - 80,
            ),
        )
        # Draw progress bar
        bar_width = self.screen_width // 2
        bar_height = 40
        bar_x = self.screen_width // 2 - bar_width // 2
        bar_y = self.screen_height // 2
        pygame.draw.rect(
            self.screen, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height)
        )
        if total > 0:
            fill_width = int(bar_width * (loaded / total))
            pygame.draw.rect(
                self.screen, (100, 200, 100), (bar_x, bar_y, fill_width, bar_height)
            )
        pygame.display.flip()

    def _load_cached_complementary_colors(self) -> None:
        """Load complementary colors from file tracking cache."""
        try:
            # Load file tracking data
            tracking_file = Path("media/remote_drive/.file_tracking.json")
            if tracking_file.exists():
                import json

                with open(tracking_file) as f:
                    tracking_data = json.load(f)

                # Extract complementary colors for image files
                for file_info in tracking_data.values():
                    file_path = file_info.get("path")
                    complementary_color = file_info.get("complementary_color")

                    if file_path and complementary_color:
                        # Convert to absolute path if needed
                        if not Path(file_path).is_absolute():
                            file_path = str(
                                Path("media/remote_drive") / Path(file_path).name
                            )

                        self.complementary_color_cache[file_path] = complementary_color
                        logger.debug(
                            f"Loaded cached complementary color for {file_path}: {complementary_color}"
                        )

                logger.info(
                    f"Loaded {len(self.complementary_color_cache)} cached complementary colors"
                )
            else:
                logger.debug(
                    "No file tracking cache found, will compute colors at runtime"
                )
        except Exception as e:
            logger.warning(f"Failed to load cached complementary colors: {e}")

    def preload_images(self, num_to_preload: int = 4) -> None:
        """Preload and process the first N images, showing a progress bar and using cached complementary colors."""
        if not self.media_items:
            return

        # Load cached complementary colors first
        self._load_cached_complementary_colors()

        # Remove the 6-second buffer since colors are now cached
        logger.info("Preloading images...")

        # Now preload the actual images (no complementary color computation needed)
        loaded = 0
        for i in range(min(num_to_preload, len(self.media_items))):
            self._show_loading_screen(num_to_preload, loaded)
            item = self.media_items[i]
            if item.media_type == "image":
                # Load and cache the image only
                surface = self.load_and_resize_image(item.file_path)
                if surface:
                    self.image_cache[str(item.file_path)] = surface
                    logger.debug(f"Preloaded image: {item.file_path.name}")
            loaded += 1
            self._show_loading_screen(num_to_preload, loaded)

        # Small pause to show full bar
        pygame.time.wait(200)

    def start(self) -> None:
        """Start the pygame slideshow."""
        logger.info("Starting pygame slideshow engine")

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

        # Preload first 4 images with progress bar
        self._init_pygame()
        self.preload_images(num_to_preload=4)

        # Display the first slide
        if self.media_items:
            self.display_current_slide()

        # Start slideshow loop
        self.running = True
        self.slideshow_loop()

    def slideshow_loop(self) -> None:
        """Main slideshow loop."""
        if not self.clock:
            return

        last_slide_time = pygame.time.get_ticks()
        max_slide_time = self.slide_duration * 1000 + 1000  # Reduce buffer to 1 second

        while self.running:
            # Check for shutdown signal more frequently
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.info("Received pygame QUIT event")
                    self.running = False
                    break
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        logger.info("Received ESC key, stopping slideshow")
                        self.running = False
                        break
                    elif event.key == pygame.K_RIGHT:
                        self.next_slide()
                        self.display_current_slide()
                        last_slide_time = pygame.time.get_ticks()
                    elif event.key == pygame.K_LEFT:
                        self.previous_slide()
                        self.display_current_slide()
                        last_slide_time = pygame.time.get_ticks()

            # Exit early if running flag was set to False
            if not self.running:
                logger.info("Slideshow loop exiting due to running flag")
                break

            # Check if it's time to advance to next slide
            current_time = pygame.time.get_ticks()
            time_since_last_slide = current_time - last_slide_time

            # Force advance if stuck too long (reduced timeout)
            if time_since_last_slide >= max_slide_time:
                logger.warning(
                    f"Force advancing slide after {time_since_last_slide/1000:.1f} seconds"
                )
                self.next_slide()
                self.display_current_slide()
                last_slide_time = current_time
            elif time_since_last_slide >= self.slide_duration * 1000:
                logger.info("Advancing to next slide")
                self.next_slide()
                self.display_current_slide()
                last_slide_time = current_time

            # Cap the frame rate and check for shutdown more frequently
            self.clock.tick(60)

            # Small sleep to allow other processes to run and check shutdown signals
            pygame.time.wait(10)

        logger.info("Slideshow loop completed")
        self.stop()

    def stop(self) -> None:
        """Stop the slideshow."""
        logger.info("Stopping pygame slideshow engine")
        self.running = False

        # Stop any playing video
        self.video_playing = False
        if self.video_stop_event:
            self.video_stop_event.set()

        # Quit pygame
        try:
            pygame.quit()
            logger.info("Pygame quit successfully")
        except Exception as e:
            logger.warning(f"Error during pygame quit: {e}")

    def handle_shutdown_signal(self) -> None:
        """Handle external shutdown signals."""
        logger.info("Received shutdown signal, stopping slideshow")
        self.running = False


def main() -> None:
    """Main entry point for running the pygame slideshow."""
    try:
        engine = PygameSlideshowEngine()
        engine.start()
    except KeyboardInterrupt:
        logger.info("Slideshow interrupted by user")
    except Exception as e:
        logger.error(f"Slideshow failed: {e}")
        raise


if __name__ == "__main__":
    main()
