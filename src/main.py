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
from src.services.google_calendar import GoogleCalendarService
from src.services.google_drive import GoogleDriveService
from src.services.scheduler import SchedulerService
from src.services.weather_service import WeatherService
from src.services.web_config_ui import create_web_config_ui
from src.slideshow.pygame_slideshow import PygameSlideshowEngine

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
    print("🔍 DEBUG: main() function called")
    global shutdown_requested, slideshow_engine_global, web_config_ui_global

    # Set up signal handlers for graceful shutdown
    print("🔍 DEBUG: Setting up signal handlers...")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print("🔍 DEBUG: Signal handlers set up")

    # Parse command line arguments
    print("🔍 DEBUG: Creating argument parser...")
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
    print("🔍 DEBUG: Parsing arguments...")
    args = parser.parse_args()
    print("🔍 DEBUG: Arguments parsed successfully")

    scheduler_service = None
    web_config_ui = None
    logger = None
    slideshow_engine = None
    print("🔍 DEBUG: Variables initialized")

    try:
        print("🔍 DEBUG: Starting main application...")

        # Initialize logging first
        logger = logging.getLogger(__name__)
        logger.info("=== MAIN APPLICATION STARTUP ===")
        logger.info("Step 1: Initializing logging...")
        print("🔍 DEBUG: Step 1 - Logging initialized")

        # Initialize configuration
        logger.info("Step 2: Initializing configuration...")
        print("🔍 DEBUG: Step 2 - Starting configuration initialization...")
        config = initialize_config()
        print("🔍 DEBUG: Step 2a - Config initialized")
        config_manager = ConfigManager()
        print("🔍 DEBUG: Step 2b - ConfigManager initialized")
        logger.info("✅ Configuration initialized successfully")

        logger.info("Step 3: Starting Family Center application...")
        print("🔍 DEBUG: Step 3 - Family Center application starting...")

        # Initialize services
        print("🔍 DEBUG: Step 4 - Starting Google Drive service initialization...")
        logger.info("Step 4: Initializing Google Drive service...")
        google_drive_service = GoogleDriveService(config)
        print("🔍 DEBUG: Step 4a - Google Drive service created")
        logger.info("✅ Google Drive service initialized")

        print("🔍 DEBUG: Step 5 - Starting Google Calendar service initialization...")
        logger.info("Step 5: Initializing Google Calendar service...")
        google_calendar_service = GoogleCalendarService(config)
        print("🔍 DEBUG: Step 5a - Google Calendar service created")
        logger.info("✅ Google Calendar service initialized")

        print("🔍 DEBUG: Step 6 - Starting Weather service initialization...")
        logger.info("Step 6: Initializing Weather service...")
        weather_service = WeatherService(ConfigManager())
        print("🔍 DEBUG: Step 6a - Weather service created")
        logger.info("✅ Weather service initialized")

        print("🔍 DEBUG: Step 7 - Starting Scheduler service initialization...")
        logger.info("Step 7: Initializing Scheduler service...")
        scheduler_service = SchedulerService(config)
        print("🔍 DEBUG: Step 7a - Scheduler service created")
        logger.info("✅ Scheduler service initialized")

        # Initialize web content service (Sprint 6)
        print("🔍 DEBUG: Step 8 - Starting web content service initialization...")
        logger.info("Step 8: Initializing web content service...")
        from src.services.web_content_service import create_web_content_service

        web_content_service = create_web_content_service(config_manager)
        print("🔍 DEBUG: Step 8a - Web content service created")
        logger.info("✅ Web content service initialized")

        # Start web configuration interface if requested
        print("🔍 DEBUG: Step 9 - Checking web config interface...")
        if args.web_config:
            logger.info("Step 9: Starting web configuration interface...")
            print("🔍 DEBUG: Step 9a - Creating web config UI...")
            web_config_ui = create_web_config_ui(config_manager, web_content_service)
            web_config_ui_global = web_config_ui

            # Start web config UI in a separate thread
            import threading

            print("🔍 DEBUG: Step 9b - Starting web config thread...")
            web_config_thread = threading.Thread(
                target=web_config_ui.start,
                kwargs={"host": "localhost", "port": args.web_config_port},
                daemon=True,
            )
            web_config_thread.start()
            print("🔍 DEBUG: Step 9c - Web config thread started")
            logger.info(
                f"✅ Web configuration interface started on http://localhost:{args.web_config_port}"
            )
        else:
            logger.info("Step 9: Skipping web configuration interface")
            print("🔍 DEBUG: Step 9a - Web config interface skipped")

        # Compute complementary colors for all images at startup - TEMPORARILY DISABLED
        print("🔍 DEBUG: Step 10 - Skipping complementary colors...")
        logger.info(
            "Step 10: Skipping complementary colors computation (temporarily disabled for debugging)"
        )
        print("🔍 DEBUG: Step 10a - Complementary colors skipped")
        logger.info("✅ Complementary colors computation skipped")

        # Handle sync operations
        print("🔍 DEBUG: Step 11 - Checking sync operations...")
        if not args.skip_sync:
            logger.info("Step 11: Starting Google Drive sync...")
            print("🔍 DEBUG: Step 11a - Starting Google Drive sync...")
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

            logger.info("✅ Google Drive sync completed.")
            print("🔍 DEBUG: Step 11b - Google Drive sync completed")
        else:
            logger.info(
                "Step 11: Skipping Google Drive sync - using existing local files"
            )
            print("🔍 DEBUG: Step 11a - Google Drive sync skipped")

        # Calendar sync
        print("🔍 DEBUG: Step 12 - Checking calendar sync...")
        if not args.skip_calendar:
            logger.info("Step 12: Starting calendar sync...")
            print("🔍 DEBUG: Step 12a - Starting calendar sync...")
            calendar_visualizer = CalendarVisualizer(config.to_dict())
            print("🔍 DEBUG: Step 12b - Calendar visualizer created")
            scheduler_service.set_google_calendar_service(google_calendar_service)
            print("🔍 DEBUG: Step 12c - Google calendar service set")
            scheduler_service.set_calendar_visualizer(calendar_visualizer)
            print("🔍 DEBUG: Step 12d - Calendar visualizer set")
            scheduler_service._sync_calendar_images()
            print("🔍 DEBUG: Step 12e - Calendar images synced")
            logger.info("✅ Calendar sync completed.")
        else:
            logger.info(
                "Step 12: Skipping calendar sync - using existing calendar images"
            )
            print("🔍 DEBUG: Step 12a - Calendar sync skipped")

        # Weather sync
        print("🔍 DEBUG: Step 13 - Checking weather sync...")
        if not args.skip_weather:
            logger.info("Step 13: Starting weather sync...")
            print("🔍 DEBUG: Step 13a - Starting weather sync...")
            scheduler_service.set_weather_service(weather_service)
            print("🔍 DEBUG: Step 13b - Weather service set")
            scheduler_service._sync_weather_data()
            print("🔍 DEBUG: Step 13c - Weather data synced")
            logger.info("✅ Weather sync completed.")
        else:
            logger.info(
                "Step 13: Skipping weather sync - using existing weather images"
            )
            print("🔍 DEBUG: Step 13a - Weather sync skipped")

        # Start scheduler service for periodic syncs
        print("🔍 DEBUG: Step 14 - Starting scheduler service...")
        logger.info("Step 14: Starting scheduler service for periodic syncs...")
        scheduler_service.start()
        print("🔍 DEBUG: Step 14a - Scheduler service started")
        logger.info("✅ Scheduler service started for periodic syncs")

        # Initialize and start slideshow - using Pygame for all platforms
        print("🔍 DEBUG: Step 15 - Initializing Pygame slideshow engine...")
        logger.info("Step 15: Initializing Pygame slideshow engine...")
        slideshow_engine = PygameSlideshowEngine(
            config_manager=config_manager,
        )
        print("🔍 DEBUG: Step 15a - Pygame slideshow engine created")
        logger.info("✅ Pygame slideshow engine initialized")

        # Set global reference for signal handler
        slideshow_engine_global = slideshow_engine
        print("🔍 DEBUG: Step 15b - Global reference set")

        print("🔍 DEBUG: Step 16 - Starting slideshow...")
        logger.info("Step 16: Starting slideshow...")
        slideshow_engine.start()
        print("🔍 DEBUG: Step 16a - Slideshow started")
        logger.info("✅ Slideshow started successfully")

        logger.info("🎉 Application started successfully")
        logger.info("Running slideshow - press ESC to exit")
        print("🔍 DEBUG: Application startup completed successfully!")

        # Keep the application running and check for shutdown signals
        print("🔍 DEBUG: Step 17 - Entering main application loop...")
        logger.info("Step 17: Entering main application loop...")
        try:
            loop_count = 0
            print("🔍 DEBUG: Step 17a - Main loop starting...")
            while not shutdown_requested:
                time.sleep(0.1)  # Check more frequently for shutdown signal
                loop_count += 1

                if loop_count % 100 == 0:  # Log every 10 seconds
                    logger.info(f"Main loop running... (iteration {loop_count})")
                    print(f"🔍 DEBUG: Main loop iteration {loop_count}")

                # Also check if slideshow has stopped
                if slideshow_engine and not getattr(slideshow_engine, "running", False):
                    logger.info("Slideshow stopped, exiting main loop")
                    print("🔍 DEBUG: Slideshow stopped, exiting main loop")
                    break

        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            print("🔍 DEBUG: Application interrupted by user")

    except Exception as e:
        print(f"🔍 DEBUG: Application failed with exception: {e}")
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
