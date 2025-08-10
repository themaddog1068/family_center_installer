"""Scheduler service for periodic media syncing."""
import logging
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.config import Config
from src.services.calendar_visualizer import CalendarVisualizer
from src.services.google_calendar import GoogleCalendarService
from src.services.google_drive import GoogleDriveService
from src.services.local_sync import LocalSyncService
from src.services.weather_service import WeatherService
from src.services.web_content_service import WebContentService
from src.utils.error_handling import handle_error

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduling periodic media syncs."""

    def __init__(self, config: Config) -> None:
        """Initialize the scheduler service.

        Args:
            config: Application configuration
        """
        self.config = config
        self.google_drive_service: GoogleDriveService | None = None
        self.local_sync_service: LocalSyncService | None = None
        self.google_calendar_service: GoogleCalendarService | None = None
        self.calendar_visualizer: CalendarVisualizer | None = None
        self.weather_service: WeatherService | None = None
        self.web_content_service: WebContentService | None = None
        self.sync_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.last_sync: dict[str, datetime] = {}
        self.running = False

    def start(self) -> None:
        """Start the scheduler service."""
        if self.sync_thread and self.sync_thread.is_alive():
            logger.warning("Scheduler is already running")
            return

        self.stop_event.clear()
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        self.running = True
        logger.info("Scheduler service started")

    def stop(self) -> None:
        """Stop the scheduler service."""
        if not self.sync_thread or not self.sync_thread.is_alive():
            logger.warning("Scheduler is not running")
            return

        self.stop_event.set()
        self.sync_thread.join()
        self.running = False
        logger.info("Scheduler service stopped")

    @handle_error()
    def _sync_loop(self) -> None:
        """Main sync loop that runs periodically."""
        while not self.stop_event.is_set():
            try:
                self._perform_sync()
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")

            # Sleep until next sync or stop event
            for _ in range(60):  # Check every minute
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    @handle_error()
    def _perform_sync(self) -> None:
        """Perform sync operations for all configured sources."""
        current_time = datetime.now()

        # Sync Google Drive if configured
        if self.google_drive_service:
            drive_interval = self.config.get("google_drive.sync_interval_minutes", 30)
            last_drive_sync = self.last_sync.get("google_drive")
            drive_path = self.config.get(
                "google_drive.local_media_path", "media/remote_drive"
            )
            logger.debug(
                f"Google Drive sync: interval={drive_interval}, last_sync={last_drive_sync}, path={drive_path}"
            )
            if (
                not last_drive_sync
                or (current_time - last_drive_sync).total_seconds()
                >= drive_interval * 60
            ):
                try:
                    logger.info("Starting Google Drive sync")
                    self.google_drive_service.download_folder(drive_path)
                    self.last_sync["google_drive"] = current_time
                    logger.info("Google Drive sync completed")
                except Exception as e:
                    logger.error(f"Error during Google Drive sync: {e}")
                    # Do not update last_sync on error

        # Sync Google Calendar if configured
        if self.google_calendar_service and self.calendar_visualizer:
            calendar_interval = self.config.get(
                "google_calendar.sync_interval_minutes", 60
            )
            last_calendar_sync = self.last_sync.get("google_calendar")
            logger.debug(
                f"Google Calendar sync: interval={calendar_interval}, last_sync={last_calendar_sync}"
            )
            if (
                not last_calendar_sync
                or (current_time - last_calendar_sync).total_seconds()
                >= calendar_interval * 60
            ):
                try:
                    logger.info("Starting Google Calendar sync")
                    self._sync_calendar_images()
                    self.last_sync["google_calendar"] = current_time
                    logger.info("Google Calendar sync completed")
                except Exception as e:
                    logger.error(f"Error during Google Calendar sync: {e}")
                    # Do not update last_sync on error

        # Sync Weather if configured
        if self.weather_service:
            weather_interval = self.config.get("weather.sync_interval_minutes", 60)
            last_weather_sync = self.last_sync.get("weather")
            logger.debug(
                f"Weather sync: interval={weather_interval}, last_sync={last_weather_sync}"
            )
            if (
                not last_weather_sync
                or (current_time - last_weather_sync).total_seconds()
                >= weather_interval * 60
            ):
                try:
                    logger.info("Starting weather sync")
                    self._sync_weather_data()
                    self.last_sync["weather"] = current_time
                    logger.info("Weather sync completed")
                except Exception as e:
                    logger.error(f"Error during weather sync: {e}")
                    # Do not update last_sync on error

        # Sync Web Content if configured (Sprint 6)
        if self.web_content_service and self.web_content_service.is_enabled():
            web_interval = self.config.get("web_content.sync_interval_minutes", 30)
            last_web_sync = self.last_sync.get("web_content")
            logger.debug(
                f"Web content sync: interval={web_interval}, last_sync={last_web_sync}"
            )
            if (
                not last_web_sync
                or (current_time - last_web_sync).total_seconds() >= web_interval * 60
            ):
                try:
                    logger.info("Starting web content sync")
                    import asyncio

                    captured_files = asyncio.run(
                        self.web_content_service.sync_all_targets()
                    )
                    self.last_sync["web_content"] = current_time
                    logger.info(
                        f"Web content sync completed. Captured {len(captured_files)} screenshots"
                    )
                except Exception as e:
                    logger.error(f"Error during web content sync: {e}")
                    # Do not update last_sync on error

        # Sync local folders if configured
        if self.local_sync_service:
            local_sources = self.config.get("local_sync.sources", [])
            logger.debug(f"Local sync sources: {local_sources}")
            for source in local_sources:
                source_id = source.get("id", "default")
                sync_interval = source.get("sync_interval_minutes", 30)
                last_sync_key = f"local_{source_id}"
                last_sync_time = self.last_sync.get(last_sync_key)
                logger.debug(
                    f"Local sync: id={source_id}, interval={sync_interval}, last_sync={last_sync_time}, path={source.get('path')}, dest={source.get('destination')}"
                )
                if (
                    not last_sync_time
                    or (current_time - last_sync_time).total_seconds()
                    >= sync_interval * 60
                ):
                    try:
                        logger.info(f"Starting local sync for source: {source_id}")
                        self.local_sync_service.sync_folder(
                            source.get("path"), source.get("destination")
                        )
                        self.last_sync[last_sync_key] = current_time
                        logger.info(f"Local sync completed for source: {source_id}")
                    except Exception as e:
                        logger.error(
                            f"Error during local sync for source {source_id}: {e}"
                        )
                        # Do not update last_sync on error

    @handle_error()
    def _sync_calendar_images(self) -> None:
        """Sync calendar events and generate images."""
        if not self.google_calendar_service or not self.calendar_visualizer:
            logger.warning("Calendar services not initialized")
            return

        # Get calendar configuration
        calendar_config = self.config.get("google_calendar", {})
        output_folder = Path(
            calendar_config.get("image_output_folder", "media/Calendar")
        )

        # Clean up existing calendar folder before sync
        if output_folder.exists():
            logger.info(f"Cleaning existing calendar folder: {output_folder}")
            shutil.rmtree(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        # Fetch calendar events
        events = self.google_calendar_service.list_events()
        logger.info(f"Fetched {len(events)} calendar events")

        # Generate calendar images based on configuration
        views_config = calendar_config.get("views", {})

        # Generate weekly view
        if views_config.get("weekly", {}).get("enabled", True):
            weekly_image = self.calendar_visualizer.generate_weekly_view(events)
            if weekly_image:
                weekly_path = output_folder / "weekly_view.png"
                weekly_image.save(weekly_path)
                logger.info(f"Weekly calendar view saved to {weekly_path}")

        # Generate sliding 30 days view
        if views_config.get("sliding_30_days", {}).get("enabled", True):
            sliding_image = self.calendar_visualizer.generate_sliding_30_days(events)
            if sliding_image:
                sliding_path = output_folder / "sliding_30_days.png"
                sliding_image.save(sliding_path)
                logger.info(f"Sliding 30 days view saved to {sliding_path}")

        # Generate upcoming events view
        if views_config.get("upcoming", {}).get("enabled", True):
            upcoming_image = self.calendar_visualizer.generate_upcoming_events(events)
            if upcoming_image:
                upcoming_path = output_folder / "upcoming_events.png"
                upcoming_image.save(upcoming_path)
                logger.info(f"Upcoming events view saved to {upcoming_path}")

    @handle_error()
    def _sync_weather_data(self) -> None:
        """Sync weather data and generate images."""
        if not self.weather_service:
            logger.warning("Weather service not initialized")
            return

        # Get weather configuration
        weather_config = self.config.get("weather", {})
        Path(weather_config.get("output_folder", "media/Weather"))

        # Clean up old files if configured
        if weather_config.get("cleanup_old_files", True):
            max_age_hours = weather_config.get("max_file_age_hours", 24)
            self.weather_service.cleanup_old_files(max_age_hours)

        # Sync weather data and generate images
        generated_files = self.weather_service.sync_weather_data()
        logger.info(f"Weather sync generated {len(generated_files)} files")

    def set_google_drive_service(self, service: GoogleDriveService) -> None:
        """Set the Google Drive service.

        Args:
            service: Google Drive service instance
        """
        self.google_drive_service = service
        logger.info("Google Drive service set in scheduler")

    def set_local_sync_service(self, service: LocalSyncService) -> None:
        """Set the local sync service.

        Args:
            service: Local sync service instance
        """
        self.local_sync_service = service
        logger.info("Local sync service set in scheduler")

    def set_google_calendar_service(self, service: GoogleCalendarService) -> None:
        """Set the Google Calendar service.

        Args:
            service: Google Calendar service instance
        """
        self.google_calendar_service = service
        logger.info("Google Calendar service set in scheduler")

    def set_calendar_visualizer(self, visualizer: CalendarVisualizer) -> None:
        """Set the calendar visualizer.

        Args:
            visualizer: Calendar visualizer instance
        """
        self.calendar_visualizer = visualizer
        logger.info("Calendar visualizer set in scheduler")

    def set_weather_service(self, service: WeatherService) -> None:
        """Set the weather service.

        Args:
            service: Weather service instance
        """
        self.weather_service = service
        logger.info("Weather service set in scheduler")

    def set_web_content_service(self, service: WebContentService) -> None:
        """Set the web content service.

        Args:
            service: Web content service instance
        """
        self.web_content_service = service
        logger.info("Web content service set in scheduler")

    def get_sync_status(self) -> dict[str, Any]:
        """Get the current sync status for all services.

        Returns:
            Dictionary containing sync status for each service
        """
        status: dict[str, Any] = {
            "is_running": {"value": self.running},
            "last_sync": {},
        }

        # Google Drive status
        if self.google_drive_service:
            last_sync = self.last_sync.get("google_drive")
            status["last_sync"]["google_drive"] = last_sync
            status["google_drive"] = {
                "enabled": True,
                "last_sync": last_sync.isoformat() if last_sync else None,
                "next_sync": (
                    last_sync
                    + timedelta(
                        minutes=self.config.get(
                            "google_drive.sync_interval_minutes", 30
                        )
                    )
                ).isoformat()
                if last_sync
                else None,
            }
        else:
            status["last_sync"]["google_drive"] = None
            status["google_drive"] = {"enabled": False}

        # Google Calendar status
        if self.google_calendar_service and self.calendar_visualizer:
            last_sync = self.last_sync.get("google_calendar")
            status["last_sync"]["google_calendar"] = last_sync
            status["google_calendar"] = {
                "enabled": True,
                "last_sync": last_sync.isoformat() if last_sync else None,
                "next_sync": (
                    last_sync
                    + timedelta(
                        minutes=self.config.get(
                            "google_calendar.sync_interval_minutes", 60
                        )
                    )
                ).isoformat()
                if last_sync
                else None,
            }
        else:
            status["last_sync"]["google_calendar"] = None
            status["google_calendar"] = {"enabled": False}

        # Weather status
        if self.weather_service:
            last_sync = self.last_sync.get("weather")
            status["last_sync"]["weather"] = last_sync
            status["weather"] = {
                "enabled": True,
                "last_sync": last_sync.isoformat() if last_sync else None,
                "next_sync": (
                    last_sync
                    + timedelta(
                        minutes=self.config.get("weather.sync_interval_minutes", 60)
                    )
                ).isoformat()
                if last_sync
                else None,
            }
        else:
            status["last_sync"]["weather"] = None
            status["weather"] = {"enabled": False}

        # Web Content status (Sprint 6)
        if self.web_content_service and self.web_content_service.is_enabled():
            last_sync = self.last_sync.get("web_content")
            status["last_sync"]["web_content"] = last_sync
            status["web_content"] = {
                "enabled": True,
                "last_sync": last_sync.isoformat() if last_sync else None,
                "next_sync": (
                    last_sync
                    + timedelta(
                        minutes=self.config.get("web_content.sync_interval_minutes", 30)
                    )
                ).isoformat()
                if last_sync
                else None,
                "targets": len(self.web_content_service.targets),
            }
        else:
            status["last_sync"]["web_content"] = None
            status["web_content"] = {"enabled": False}

        # Local sync status
        if self.local_sync_service:
            local_sources = self.config.get("local_sync.sources", [])
            status["local_sync"] = {
                "enabled": True,
                "sources": len(local_sources),
                "last_syncs": {},
            }
            for source in local_sources:
                source_id = source.get("id", "default")
                last_sync_key = f"local_{source_id}"
                last_sync = self.last_sync.get(last_sync_key)
                status["last_sync"][f"local_{source_id}"] = last_sync
                status["local_sync"]["last_syncs"][source_id] = {
                    "last_sync": last_sync.isoformat() if last_sync else None,
                    "next_sync": (
                        last_sync
                        + timedelta(minutes=source.get("sync_interval_minutes", 30))
                    ).isoformat()
                    if last_sync
                    else None,
                }
        else:
            status["local_sync"] = {"enabled": False}

        return status
