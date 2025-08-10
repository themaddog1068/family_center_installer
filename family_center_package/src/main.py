"""
Main entry point for the Family Center application.

This application syncs media from Google Drive, generates calendar images,
and displays a slideshow of family media and calendar events.
"""

import argparse
import logging
import os
import shutil
import signal
import sys
import time
from types import FrameType

from src.config import Config
from src.config.config_manager import ConfigManager
from src.services.calendar_visualizer import CalendarVisualizer
from src.services.complementary_color_service import compute_all_complementary_colors
from src.services.google_calendar import GoogleCalendarService
from src.services.google_drive import GoogleDriveService
from src.services.scheduler import SchedulerService
from src.services.weather_service import WeatherService
from src.services.web_config_ui import create_web_config_ui
from src.services.web_content_service import create_web_content_service
from src.slideshow import PygameSlideshowEngine

# Global flag for shutdown
shutdown_requested = False
slideshow_engine_global = None
web_config_ui_global = None


def signal_handler(signum: int, frame: FrameType | None) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested, slideshow_engine_global, web_config_ui_global
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True

    # Stop the slideshow engine if it exists
    if slideshow_engine_global:
        logger.info("Stopping slideshow engine from signal handler...")
        slideshow_engine_global.handle_shutdown_signal()

    # Stop the web configuration interface if it exists
    if web_config_ui_global:
        logger.info("Stopping web configuration interface from signal handler...")
        web_config_ui_global.stop()


def initialize_config() -> Config:
    """Initialize and return the application configuration."""
    return Config()


def main() -> None:
    """Main entry point for the Family Center application."""
    global shutdown_requested, slideshow_engine_global, web_config_ui_global

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Family Center Slideshow Application")
    parser.add_argument(
        "-vo",
        "--video-only",
        action="store_true",
        help="Show only video files in the slideshow",
    )
    parser.add_argument(
        "--pi-sim",
        action="store_true",
        help="Simulate Raspberry Pi environment (use Pi-compatible video players)",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip Google Drive sync and use existing local files",
    )
    parser.add_argument(
        "--skip-calendar",
        action="store_true",
        help="Skip calendar sync and use existing calendar images",
    )
    parser.add_argument(
        "--skip-weather",
        action="store_true",
        help="Skip weather sync and use existing weather images",
    )
    parser.add_argument(
        "--web-config",
        action="store_true",
        help="Start web configuration interface for web content targets",
    )
    parser.add_argument(
        "--web-config-port",
        type=int,
        default=8080,
        help="Port for web configuration interface (default: 8080)",
    )
    args = parser.parse_args()

    slideshow_engine = None
    scheduler_service = None
    web_content_service = None
    web_config_ui = None
    logger = None

    try:
        # Initialize logging first
        logger = logging.getLogger(__name__)

        # Initialize configuration
        config = initialize_config()
        config_manager = ConfigManager()

        logger.info("Starting Family Center application...")

        # Initialize services
        google_drive_service = GoogleDriveService(config)
        google_calendar_service = GoogleCalendarService(config)
        weather_service = WeatherService(ConfigManager())
        scheduler_service = SchedulerService(config)

        # Initialize web content service (Sprint 6)
        web_content_service = create_web_content_service(config_manager)
        if web_content_service.is_enabled():
            logger.info("Web content service enabled")
            # Start web content service
            import asyncio

            asyncio.run(web_content_service.start())

            # Add web content sync to scheduler
            scheduler_service.set_web_content_service(web_content_service)
        else:
            logger.info("Web content service disabled")

        # Start web configuration interface if requested
        if args.web_config:
            logger.info("Starting web configuration interface...")
            web_config_ui = create_web_config_ui(config_manager, web_content_service)
            web_config_ui_global = web_config_ui

            # Start web config UI in a separate thread
            import threading

            web_config_thread = threading.Thread(
                target=web_config_ui.start,
                kwargs={"host": "localhost", "port": args.web_config_port},
                daemon=True,
            )
            web_config_thread.start()
            logger.info(
                f"Web configuration interface started on http://localhost:{args.web_config_port}"
            )

        # Compute complementary colors for all images at startup
        logger.info("Computing complementary colors for all images...")
        compute_all_complementary_colors()

        # Handle sync operations
        if not args.skip_sync:
            logger.info("Starting Google Drive sync...")
            # Use the existing sync logic from the original main function
            media_path = config.get(
                "google_drive.local_media_path", "media/remote_drive"
            )

            # Clean up existing media directory for fresh sync
            if os.path.exists(media_path):
                logger.info(f"Cleaning existing media directory: {media_path}")
                shutil.rmtree(media_path)
            os.makedirs(media_path, exist_ok=True)

            logger.info(f"Syncing Google Drive media to {media_path}...")
            files = google_drive_service.list_files(google_drive_service.folder_id)
            logger.info(f"Found {len(files)} files in Google Drive folder")

            for file in files:
                file_id = file["id"]
                file_path = os.path.join(media_path, file["name"])
                try:
                    logger.info(f"Downloading {file['name']}...")
                    google_drive_service.download_file_direct(file_id, file_path)
                    logger.info(f"Successfully downloaded: {file['name']}")
                except Exception as e:
                    logger.error(f"Failed to download {file['name']}: {e}")

            logger.info("Google Drive sync completed.")
        else:
            logger.info("Skipping Google Drive sync - using existing local files")

        # Calendar sync
        if not args.skip_calendar:
            logger.info("Starting calendar sync...")
            calendar_visualizer = CalendarVisualizer(config.to_dict())
            scheduler_service.set_google_calendar_service(google_calendar_service)
            scheduler_service.set_calendar_visualizer(calendar_visualizer)
            scheduler_service._sync_calendar_images()
            logger.info("Calendar sync completed.")
        else:
            logger.info("Skipping calendar sync - using existing calendar images")

        # Weather sync
        if not args.skip_weather:
            logger.info("Starting weather sync...")
            scheduler_service.set_weather_service(weather_service)
            scheduler_service._sync_weather_data()
            logger.info("Weather sync completed.")
        else:
            logger.info("Skipping weather sync - using existing weather images")

        # Start scheduler service for periodic syncs
        scheduler_service.start()
        logger.info("Scheduler service started for periodic syncs")

        # Initialize and start slideshow
        slideshow_engine = PygameSlideshowEngine(
            config_manager=ConfigManager(),
            video_only=args.video_only,
            pi_sim=args.pi_sim,
        )

        # Set global reference for signal handler
        slideshow_engine_global = slideshow_engine

        logger.info("Starting slideshow...")
        slideshow_engine.start()

        logger.info("Application started successfully")
        logger.info("Running slideshow - press ESC to exit")

        # Keep the application running and check for shutdown signals
        try:
            while not shutdown_requested:
                time.sleep(0.1)  # Check more frequently for shutdown signal

                # Also check if slideshow has stopped
                if slideshow_engine and not getattr(slideshow_engine, "running", False):
                    logger.info("Slideshow stopped, exiting main loop")
                    break

        except KeyboardInterrupt:
            logger.info("Application interrupted by user")

    except Exception as e:
        if logger:
            logger.error(f"Application failed to start: {e}")
            logger.error(f"Unexpected error: {e}")
        else:
            print(f"Application failed to start: {e}")
            print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if logger:
            logger.info("Starting application cleanup...")

        if slideshow_engine:
            if logger:
                logger.info("Stopping slideshow engine...")
            slideshow_engine.stop()

        if scheduler_service:
            if logger:
                logger.info("Stopping scheduler service...")
            scheduler_service.stop()

        # Clear global reference
        slideshow_engine_global = None
        web_config_ui_global = None

        if logger:
            logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()
