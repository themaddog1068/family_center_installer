"""
VLC-based slideshow engine for Family Center application.

This module provides a VLC-powered slideshow engine that maintains all core tenets:
- Read-only Google Drive integration
- Weighted media selection
- Time-based content prioritization
- Mixed media support (images and videos)
- Raspberry Pi optimization
- Smooth transitions
"""

import logging
import random
import tempfile
import time
from pathlib import Path

import vlc

from src.config.config_manager import ConfigManager
from src.services.time_based_weighting import TimeBasedWeightingService

logger = logging.getLogger(__name__)


class MediaItem:
    """Represents a media item with metadata for slideshow display."""

    def __init__(
        self,
        path: Path,
        media_type: str,
        duration: int = 8,
        weight: float = 1.0,
        source: str = "unknown",
    ):
        self.path = path
        self.media_type = media_type  # 'image' or 'video'
        self.duration = duration
        self.weight = weight
        self.source = source
        self.is_video = self._is_video_file()

    def _is_video_file(self) -> bool:
        """Determine if this is a video file based on extension."""
        video_extensions = {".mp4", ".avi", ".mov", ".wmv", ".mkv", ".webm", ".flv"}
        return self.path.suffix.lower() in video_extensions

    def __str__(self) -> str:
        return f"MediaItem({self.path.name}, type={self.media_type}, duration={self.duration}s, weight={self.weight})"


class WeightedMediaManager:
    """Manages weighted media selection and playlist generation."""

    def __init__(self, config: ConfigManager) -> None:
        logger.info("Initializing WeightedMediaManager...")
        self.config = config
        self.media_types = {
            "calendar": {"weight": 0.25, "folder": "media/Calendar"},
            "weather": {"weight": 0.25, "folder": "media/Weather"},
            "drive_media": {"weight": 0.3, "folder": "media/remote_drive"},
            "local_media": {"weight": 0.1, "folder": "media/local"},
            "web_news": {"weight": 0.1, "folder": "media/web_news"},
        }
        logger.info("Creating TimeBasedWeightingService...")
        self.time_weighting_service = TimeBasedWeightingService(config)
        # Set default slide duration from config
        vlc_config = config.get("slideshow", {}).get("vlc_engine", {})
        self.slide_duration = vlc_config.get("image_duration", 12)
        logger.info("WeightedMediaManager initialized successfully")

    def discover_all_media(self) -> dict[str, list[MediaItem]]:
        """Discover all media files organized by source."""
        logger.info("Starting media discovery...")
        media_by_source = {}

        for source_name, source_config in self.media_types.items():
            logger.info(f"Discovering media for source: {source_name}")
            folder_path = Path(str(source_config["folder"]))
            logger.info(f"Checking folder: {folder_path}")

            if not folder_path.exists():
                logger.warning(f"Media folder does not exist: {folder_path}")
                continue

            media_files = []
            supported_formats = {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".webp",
                ".heic",
                ".heif",
                ".mp4",
                ".avi",
                ".mov",
                ".wmv",
                ".mkv",
                ".webm",
                ".flv",
            }

            logger.info(f"Scanning files in {folder_path}...")
            file_count = 0
            for file_path in folder_path.rglob("*"):
                file_count += 1
                if file_count % 10 == 0:  # Log every 10 files
                    logger.debug(f"Scanned {file_count} files in {source_name}")

                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in supported_formats
                ):
                    logger.debug(f"Found supported file: {file_path.name}")

                    # Get time-based weights
                    logger.debug(f"Getting weights for {source_name}")
                    current_weights = (
                        self.time_weighting_service.get_current_hour_weights()
                    )
                    source_weight = current_weights.get(
                        source_name, float(source_config["weight"])
                    )

                    # Determine duration based on media type
                    if file_path.suffix.lower() in {
                        ".mp4",
                        ".avi",
                        ".mov",
                        ".wmv",
                        ".mkv",
                        ".webm",
                        ".flv",
                    }:
                        logger.debug(f"Processing video: {file_path.name}")
                        duration = self._get_video_duration(file_path)
                        media_type = "video"
                    else:
                        logger.debug(f"Processing image: {file_path.name}")
                        duration = self.slide_duration  # 12 seconds for images
                        media_type = "image"

                    media_item = MediaItem(
                        path=file_path,
                        media_type=media_type,
                        duration=duration,
                        weight=float(source_weight),
                        source=source_name,
                    )
                    media_files.append(media_item)

            logger.info(
                f"Completed scan of {source_name}: {file_count} total files, {len(media_files)} supported"
            )

            if media_files:
                media_by_source[source_name] = media_files
                logger.info(f"Discovered {len(media_files)} files in {source_name}")
            else:
                logger.warning(f"No media files found for {source_name}")

        total_files = sum(len(files) for files in media_by_source.values())
        logger.info(
            f"Media discovery complete. Found {total_files} total files across {len(media_by_source)} sources"
        )
        return media_by_source

    def _get_video_duration(self, video_path: Path) -> int:
        """Get video duration in seconds using VLC."""
        logger.debug(f"Getting video duration for: {video_path}")
        try:
            logger.debug("Creating VLC instance for duration check")
            instance = vlc.Instance("--no-xlib --no-audio")
            logger.debug(f"Creating media object for: {video_path}")
            media = instance.media_new(str(video_path))
            logger.debug(f"Parsing media: {video_path}")
            media.parse()
            logger.debug(f"Getting duration for: {video_path}")
            duration_ms = media.get_duration()
            duration_sec = max(12, duration_ms // 1000)  # Minimum 12 seconds for videos
            logger.debug(f"Video duration for {video_path}: {duration_sec} seconds")
            logger.debug("Releasing VLC instance")
            instance.release()
            return duration_sec
        except Exception as e:
            logger.warning(f"Could not get duration for {video_path}: {e}")
            return 12

    def build_weighted_playlist(self) -> list[MediaItem]:
        """Build a weighted playlist with proper distribution."""
        media_by_source = self.discover_all_media()

        if not media_by_source:
            logger.warning("No media files found in any source")
            return []

        # Create weighted pool
        weighted_pool = []

        for _source_name, media_files in media_by_source.items():
            for media_item in media_files:
                # Add multiple copies based on weight
                copies = max(1, int(media_item.weight * 10))
                for _ in range(copies):
                    weighted_pool.append(media_item)

        # Shuffle the pool
        random.shuffle(weighted_pool)

        logger.info(f"Created weighted playlist with {len(weighted_pool)} items")
        return weighted_pool


class VLCSlideshowEngine:
    """VLC-based slideshow engine with weighted media support."""

    def __init__(self, config: ConfigManager) -> None:
        logger.info("Initializing VLCSlideshowEngine...")
        self.config = config
        self.running = False
        self.vlc_instance = None
        self.player = None
        logger.info("Creating WeightedMediaManager...")
        self.media_manager = WeightedMediaManager(config)
        self.current_playlist: list[MediaItem] = []
        self.current_index = 0
        self.playlist_file: Path | None = None

        logger.info("Loading configuration...")
        try:
            # Configuration - using ConfigManager API
            display_config = config.get("display")
            logger.info(f"Display config: {display_config}")
            resolution_config = display_config.get("resolution", {})
            logger.info(f"Resolution config: {resolution_config}")
            self.screen_width = resolution_config.get("width", 1920)
            self.screen_height = resolution_config.get("height", 1080)
            logger.info(f"Screen dimensions: {self.screen_width}x{self.screen_height}")

            slideshow_config = config.get("slideshow")
            transitions_config = slideshow_config.get("transitions", {})
            self.transition_duration = transitions_config.get("duration", 2.0)
            self.slide_duration = slideshow_config.get("slide_duration_seconds", 8)

            # Pass slide duration to media manager
            self.media_manager.slide_duration = self.slide_duration
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            import traceback

            logger.error(f"Configuration error traceback: {traceback.format_exc()}")
            raise

        logger.info("Setting up VLC options...")

        # Get VLC configuration
        vlc_config = config.get("slideshow", {}).get("vlc_engine", {})
        
        # VLC options - cross-platform compatible with network prevention
        self.vlc_options = [
            "--no-audio",  # Disable audio for slideshow
            f"--image-duration={vlc_config.get('image_duration', 12)}",  # Image display duration from config
            "--no-playlist-tree",  # Disable playlist tree (prevents network calls)
            "--no-random",  # Disable random (we handle this manually)
            "--no-loop",  # Disable loop (we handle this manually)
            f"--width={self.screen_width}",
            f"--height={self.screen_height}",
            "--quiet",  # Reduce verbose output
        ]
        
        # Add metadata hiding options based on config
        if vlc_config.get("hide_titles", True):
            self.vlc_options.extend(["--no-video-title-show", "--no-media-title"])
        if vlc_config.get("hide_filenames", True):
            self.vlc_options.extend(["--no-filename", "--no-media-info"])
        if vlc_config.get("hide_metadata", True):
            self.vlc_options.extend([
                "--no-osd", "--no-overlay", "--no-stats",
                "--no-media-description", "--no-media-artist", "--no-media-album",
                "--no-media-genre", "--no-media-copyright", "--no-media-language",
                "--no-media-rating", "--no-media-date", "--no-media-track",
                "--no-media-disc", "--no-media-url", "--no-media-nowplaying",
                "--no-media-metadata"
            ])
        
        # Add network prevention options based on config
        if vlc_config.get("network_prevention", True):
            self.vlc_options.extend([
                "--no-sub-autodetect-file", "--no-sub-autodetect-path",
                "--no-lua", "--no-http-reconnect", "--no-rtsp-tcp",
                "--no-udp", "--no-tcp", "--no-ipv6", "--no-ipv4",
                "--no-crashdump", "--no-snapshot-preview", "--no-snapshot-sequential",
                "--no-snapshot-path", "--no-snapshot-format", "--no-snapshot-ratio",
                "--no-snapshot-width", "--no-snapshot-height"
            ])
        
        # Add transition options based on config
        fade_duration = vlc_config.get("fade_duration", 2.0)
        fade_alpha = vlc_config.get("fade_alpha", 0.8)
        enable_fade_in = vlc_config.get("enable_fade_in", True)
        enable_fade_out = vlc_config.get("enable_fade_out", True)
        
        self.vlc_options.extend([
            f"--image-fade-duration={fade_duration}",
            f"--image-fade-alpha={fade_alpha}",
            f"--image-fade-out={1 if enable_fade_out else 0}",
            f"--image-fade-in={1 if enable_fade_in else 0}"
        ])

        # Add Pi-specific options only if on Raspberry Pi
        import platform

        if platform.machine().startswith("arm"):
            self.vlc_options.extend(
                [
                    "--hwdec=mmal",  # Pi hardware acceleration
                    "--vout=mmal_vout",  # Pi video output
                    "--fullscreen",  # Fullscreen on Pi
                ]
            )
        else:
            # macOS/development options - create proper display window
            self.vlc_options.extend(
                [
                    "--quiet",  # Reduce verbose output
                    "--no-video-title-show",  # Don't show video title
                    "--no-osd",  # No on-screen display
                ]
            )

    def _create_vlc_instance(self) -> vlc.Instance:
        """Create VLC instance optimized for Pi."""
        try:
            instance = vlc.Instance(" ".join(self.vlc_options))
            logger.info("VLC instance created successfully")
            return instance
        except Exception as e:
            logger.error(f"Failed to create VLC instance: {e}")
            # Fallback to basic options
            return vlc.Instance("--no-xlib --no-audio --fullscreen")

    def start(self) -> None:
        """Start the VLC slideshow."""
        logger.info("Starting VLC slideshow engine...")

        try:
            logger.info("Step 1: Creating VLC instance...")
            # Initialize VLC
            self.vlc_instance = self._create_vlc_instance()
            logger.info("VLC instance created successfully")

            logger.info("Step 2: Creating media player...")
            self.player = self.vlc_instance.media_player_new()
            logger.info("Media player created successfully")

            logger.info("Step 3: Building weighted playlist...")
            # Build weighted playlist
            self.current_playlist = self.media_manager.build_weighted_playlist()
            logger.info(f"Playlist built with {len(self.current_playlist)} items")

            if not self.current_playlist:
                logger.error("No media files found for slideshow")
                return

            logger.info("Step 4: Creating playlist file...")
            # Create playlist file
            self.playlist_file = self._create_playlist_file()
            logger.info(f"Playlist file created: {self.playlist_file}")

            logger.info("Step 5: Starting playback...")
            # Start playback
            self._start_playback()
            logger.info("Playback started successfully")

            self.running = True
            logger.info("VLC slideshow started successfully")

        except Exception as e:
            logger.error(f"Failed to start VLC slideshow: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            self.stop()

    def _create_playlist_file(self) -> Path:
        """Create a VLC playlist file from the weighted media list."""
        try:
            # Create temporary playlist file
            playlist_content = []

            # Add M3U header
            playlist_content.append("#EXTM3U")

            for media_item in self.current_playlist:
                # Add extended info line for each media item
                duration = media_item.duration if media_item.duration else 12
                playlist_content.append(f"#EXTINF:{duration},{media_item.path.name}")

                # Add media file to playlist
                playlist_content.append(str(media_item.path.absolute()))

            # Write playlist file
            playlist_file = (
                Path(tempfile.gettempdir())
                / f"family_center_playlist_{int(time.time())}.m3u"
            )
            playlist_content_text = "\n".join(playlist_content)
            playlist_file.write_text(playlist_content_text, encoding="utf-8")

            logger.info(f"Created playlist file: {playlist_file}")
            logger.info(f"Playlist contains {len(playlist_content)} items")
            logger.info(
                f"First few items: {playlist_content[:3] if playlist_content else 'None'}"
            )
            logger.info(f"Playlist content preview: {playlist_content_text[:200]}...")

            # Debug: Print the full playlist content
            logger.info("=== FULL PLAYLIST CONTENT ===")
            for i, line in enumerate(playlist_content):
                logger.info(f"Line {i}: {line}")
            logger.info("=== END PLAYLIST CONTENT ===")
            return playlist_file

        except Exception as e:
            logger.error(f"Failed to create playlist file: {e}")
            raise

    def _start_playback(self) -> None:
        """Start VLC playback with the playlist."""
        try:
            if not self.playlist_file or not self.playlist_file.exists():
                logger.error("Playlist file not found")
                return

            # Try direct file playback first (more reliable than playlist)
            logger.info("Attempting direct file playback...")
            first_media_item = (
                self.current_playlist[0] if self.current_playlist else None
            )
            if first_media_item and self.vlc_instance and self.player:
                logger.info(f"Playing first file directly: {first_media_item.path}")
                media = self.vlc_instance.media_new(
                    str(first_media_item.path.absolute())
                )
                self.player.set_media(media)

                # Start playback
                logger.info("Starting VLC player...")
                result = self.player.play()
                logger.info(f"VLC play() result: {result}")

                # Check player state
                time.sleep(1)  # Give VLC time to start
                state = self.player.get_state()
                logger.info(f"VLC player state: {state}")

                # Set display options based on platform
                import platform

                if platform.machine().startswith("arm"):
                    try:
                        logger.info("Setting VLC to fullscreen on Pi...")
                        if self.player:
                            self.player.set_fullscreen(True)
                        logger.info("Fullscreen set successfully")
                    except Exception as e:
                        logger.warning(f"Could not set fullscreen: {e}")
                else:
                    try:
                        logger.info("Setting VLC window size for macOS...")
                        # Set window size for macOS development
                        if self.player:
                            self.player.set_hwnd(0)  # Use default window
                        logger.info("VLC window configured for macOS")
                    except Exception as e:
                        logger.warning(f"Could not configure VLC window: {e}")

                logger.info("VLC playback started successfully")

                # Start manual playlist loop
                self._start_playlist_loop()
            else:
                logger.error("No media items found for playback")

        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            import traceback

            logger.error(f"Playback error traceback: {traceback.format_exc()}")
            raise

    def _start_playlist_loop(self) -> None:
        """Start manual playlist loop for cycling through media items."""
        logger.info("Starting manual playlist loop...")

        def playlist_worker():
            current_index = 0
            while self.running and current_index < len(self.current_playlist):
                try:
                    media_item = self.current_playlist[current_index]
                    logger.info(
                        f"Playing item {current_index + 1}/{len(self.current_playlist)}: {media_item.path.name}"
                    )

                    # Load and play the media item
                    if self.vlc_instance and self.player:
                        media = self.vlc_instance.media_new(
                            str(media_item.path.absolute())
                        )
                        self.player.set_media(media)
                        self.player.play()

                    # Wait for the duration of this item plus transition time
                    duration = media_item.duration if media_item.duration else 12
                    vlc_config = self.config.get("slideshow", {}).get("vlc_engine", {})
                    transition_time = vlc_config.get("fade_duration", 2.0)  # Transition time from config
                    total_duration = duration + transition_time

                    logger.info(
                        f"Playing {media_item.path.name} for {duration}s + {transition_time}s transition"
                    )

                    # Wait for main duration
                    time.sleep(duration)

                    # Smooth transition - fade out effect
                    logger.info("Starting transition to next slide...")
                    time.sleep(transition_time)

                    # Move to next item
                    current_index = (current_index + 1) % len(self.current_playlist)

                except Exception as e:
                    logger.error(f"Error in playlist loop: {e}")
                    time.sleep(1)
                    current_index = (current_index + 1) % len(self.current_playlist)

        # Start playlist loop in a separate thread
        import threading

        self.playlist_thread = threading.Thread(target=playlist_worker, daemon=True)
        self.playlist_thread.start()
        logger.info("Playlist loop thread started")

    def stop(self) -> None:
        """Stop the VLC slideshow."""
        logger.info("Stopping VLC slideshow...")
        self.running = False

        # Wait for playlist thread to finish
        if hasattr(self, "playlist_thread") and self.playlist_thread:
            logger.info("Waiting for playlist thread to finish...")
            self.playlist_thread.join(timeout=2)
            logger.info("Playlist thread finished")

        if self.player:
            try:
                self.player.stop()
                self.player.release()
            except Exception as e:
                logger.error(f"Error stopping VLC player: {e}")
            finally:
                self.player = None

        if self.vlc_instance:
            try:
                self.vlc_instance.release()
            except Exception as e:
                logger.error(f"Error releasing VLC instance: {e}")
            finally:
                self.vlc_instance = None

        # Clean up playlist file
        if self.playlist_file and self.playlist_file.exists():
            try:
                self.playlist_file.unlink()
                logger.info("Cleaned up playlist file")
            except Exception as e:
                logger.error(f"Error cleaning up playlist file: {e}")

    def handle_shutdown_signal(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received shutdown signal {signum}")
        self.stop()

    def is_running(self) -> bool:
        """Check if the slideshow is currently running."""
        return self.running and self.player is not None

    def get_current_media(self) -> MediaItem | None:
        """Get the currently playing media item."""
        if self.current_playlist and 0 <= self.current_index < len(
            self.current_playlist
        ):
            return self.current_playlist[self.current_index]
        return None

    def get_playlist_info(self) -> dict[str, any]:
        """Get information about the current playlist."""
        return {
            "total_items": len(self.current_playlist),
            "current_index": self.current_index,
            "is_running": self.is_running(),
            "sources": list(self.media_manager.media_types.keys()),
            "media_by_type": {
                "images": len(
                    [m for m in self.current_playlist if m.media_type == "image"]
                ),
                "videos": len(
                    [m for m in self.current_playlist if m.media_type == "video"]
                ),
            },
        }
