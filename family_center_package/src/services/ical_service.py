"""
iCal service module for handling calendar operations and synchronization.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, cast

import pytz
import requests
from icalendar import Calendar

from src.config import Config
from src.utils.error_handling import ErrorSeverity, FamilyCenterError, handle_error

logger = logging.getLogger(__name__)


class ICalError(FamilyCenterError):
    """Raised when there is an error with iCal operations."""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> None:
        """Initialize the error.

        Args:
            message: Error message
            severity: Error severity
        """
        super().__init__(message, severity)


class ICalService:
    """Service class for iCal operations."""

    def __init__(self, config: Config) -> None:
        """Initialize the iCal service.

        Args:
            config: Application configuration instance
        """
        self.config = config
        self.ical_url = config.get("google_calendar.ical_url")
        self.timezone = config.get("google_calendar.timezone")
        self.tz = pytz.timezone(self.timezone)

    def _convert_to_timezone(self, dt: datetime | date) -> datetime:
        """Convert datetime to configured timezone."""
        if isinstance(dt, date) and not isinstance(dt, datetime):
            # For all-day events, just convert to datetime at midnight in local timezone
            # Don't apply timezone conversion for all-day events
            return datetime.combine(dt, datetime.min.time()).replace(tzinfo=self.tz)

        if dt.tzinfo is None:
            # Assume naive datetime is in UTC
            dt = dt.replace(tzinfo=pytz.UTC)

        return dt.astimezone(self.tz)

    def _format_event_time(self, dt: datetime, is_all_day: bool) -> dict[str, str]:
        """Format event time for API response."""
        if is_all_day:
            return {"date": dt.strftime("%Y-%m-%d")}
        return {"dateTime": dt.isoformat(), "timeZone": self.timezone}

    @handle_error(severity=ErrorSeverity.ERROR)
    def list_events(
        self,
        max_results: int | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """List events from the iCal feed."""
        try:
            # Fetch iCal feed
            response = requests.get(self.ical_url, timeout=30)
            response.raise_for_status()

            # Parse iCal feed
            cal = Calendar.from_ical(response.text)

            # Convert events to dictionary format
            events = []
            for event in cal.walk("VEVENT"):
                # Get event start and end times
                start = event.get("dtstart").dt
                end = event.get("dtend").dt

                # Determine if this is an all-day event
                import datetime as dtmod

                is_all_day = isinstance(start, dtmod.date) and not isinstance(
                    start, dtmod.datetime
                )

                # Convert to datetime if needed
                start = self._convert_to_timezone(start)
                end = self._convert_to_timezone(end)

                # For all-day events, iCal uses exclusive end dates
                # Convert to inclusive end dates by subtracting one day
                if is_all_day:
                    end = end - timedelta(days=1)

                # Apply time filters
                if time_min and start < time_min:
                    continue
                if time_max and end > time_max:
                    continue

                # Convert to dictionary format matching Google Calendar API
                event_dict: dict[str, str | dict[str, str] | bool] = {
                    "id": str(event.get("uid")),
                    "summary": str(event.get("summary", "")),
                    "start": self._format_event_time(start, is_all_day),
                    "end": self._format_event_time(end, is_all_day),
                    "description": str(event.get("description", "")),
                    "location": str(event.get("location", "")),
                }

                # Add all-day event flag
                if is_all_day:
                    event_dict["allDay"] = True

                events.append(event_dict)

                # Apply max results limit
                if max_results and len(events) >= max_results:
                    break

            # Sort events by start time, with all-day events after regular events
            def sort_key(event: dict[str, Any]) -> tuple[int, str]:
                start = event["start"]
                if "dateTime" in start:
                    return (0, start["dateTime"])  # Regular events first
                return (1, start["date"])  # All-day events second

            events.sort(key=sort_key)

            return cast(list[dict[str, Any]], events)

        except requests.RequestException as e:
            raise ICalError(f"Failed to fetch iCal feed: {str(e)}") from e
        except Exception as e:
            raise ICalError(f"Failed to parse iCal feed: {str(e)}") from e
