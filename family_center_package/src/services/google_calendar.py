"""
Google Calendar service module for handling calendar operations and synchronization.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, cast

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from src.config import Config
from src.services.ical_service import ICalService
from src.utils.error_handling import ErrorSeverity, FamilyCenterError, handle_error

logger = logging.getLogger(__name__)


class GoogleCalendarError(FamilyCenterError):
    """Raised when there is an error with Google Calendar."""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> None:
        """Initialize the error.

        Args:
            message: Error message
            severity: Error severity
        """
        super().__init__(message, severity)


class GoogleCalendarService:
    """Service class for Google Calendar operations."""

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, config: Config) -> None:
        """Initialize the Google Calendar service.

        Args:
            config: Application configuration instance
        """
        self.config = config
        self.use_ical = config.get("google_calendar.use_ical", False)

        if self.use_ical:
            self.ical_service = ICalService(config)
        else:
            self.service: Resource = None
            self.calendar_id = config.get("google_calendar.calendar_id")
            self._initialize_service()

    @handle_error(severity=ErrorSeverity.ERROR)
    def _initialize_service(self) -> None:
        """Initialize the Google Calendar API service using service account."""
        service_account_file = self.config.get("google_calendar.credentials_path")

        if not os.path.exists(service_account_file):
            raise FileNotFoundError(
                f"Service account file not found: {service_account_file}"
            )

        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=self.SCOPES
        )

        self.service = build("calendar", "v3", credentials=credentials)
        logger.info("Google Calendar service initialized successfully")

    @handle_error(severity=ErrorSeverity.ERROR)
    def list_events(
        self,
        max_results: int | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """List events from the calendar.

        Args:
            max_results: Maximum number of events to return
            time_min: Start time for events
            time_max: End time for events

        Returns:
            List of event metadata dictionaries
        """
        if self.use_ical:
            return cast(
                list[dict[str, Any]],
                self.ical_service.list_events(
                    max_results=max_results,
                    time_min=time_min,
                    time_max=time_max,
                ),
            )

        if time_min is None:
            time_min = datetime.utcnow()
        if time_max is None:
            time_max = time_min + timedelta(days=7)

        events_result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min.isoformat() + "Z",
                timeMax=time_max.isoformat() + "Z",
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        return cast(list[dict[str, Any]], events)


@handle_error()
def get_calendar_service(credentials: Credentials) -> Resource:
    """Get Google Calendar service.

    Args:
        credentials: Google API credentials.

    Returns:
        Google Calendar service instance.

    Raises:
        GoogleCalendarError: If service creation fails.
    """
    try:
        return build("calendar", "v3", credentials=credentials)
    except Exception as e:
        raise GoogleCalendarError(f"Failed to create Calendar service: {str(e)}") from e


@handle_error()
def list_events(
    service: Resource,
    calendar_id: str = "primary",
    time_min: datetime | None = None,
    time_max: datetime | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """List events from Google Calendar.

    Args:
        service: Google Calendar service instance.
        calendar_id: Calendar ID to list events from.
        time_min: Start time for events.
        time_max: End time for events.
        max_results: Maximum number of events to return.

    Returns:
        List of event dictionaries.

    Raises:
        GoogleCalendarError: If listing events fails.
    """
    try:
        if time_min is None:
            time_min = datetime.utcnow()
        if time_max is None:
            time_max = time_min + timedelta(days=7)

        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat() + "Z",
                timeMax=time_max.isoformat() + "Z",
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return cast(list[dict[str, Any]], events_result.get("items", []))
    except HttpError as error:
        logger.error(f"Failed to list events: {error}")
        raise GoogleCalendarError(f"Failed to list events: {str(error)}") from error


@handle_error()
def create_event(
    service: Resource,
    calendar_id: str,
    event: dict[str, Any],
) -> dict[str, Any]:
    """Create a new event in Google Calendar.

    Args:
        service: Google Calendar service instance.
        calendar_id: Calendar ID to create event in.
        event: Event details.

    Returns:
        Created event dictionary.

    Raises:
        GoogleCalendarError: If event creation fails.
    """
    try:
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        return event
    except HttpError as error:
        logger.error(f"Failed to create event: {error}")
        raise GoogleCalendarError(f"Failed to create event: {str(error)}") from error


@handle_error()
def update_event(
    service: Resource,
    calendar_id: str,
    event_id: str,
    event: dict[str, Any],
) -> dict[str, Any]:
    """Update an existing event in Google Calendar.

    Args:
        service: Google Calendar service instance.
        calendar_id: Calendar ID containing the event.
        event_id: ID of the event to update.
        event: Updated event details.

    Returns:
        Updated event dictionary.

    Raises:
        GoogleCalendarError: If event update fails.
    """
    try:
        event = (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event)
            .execute()
        )
        return event
    except HttpError as error:
        logger.error(f"Failed to update event: {error}")
        raise GoogleCalendarError(f"Failed to update event: {str(error)}") from error


@handle_error()
def delete_event(
    service: Resource,
    calendar_id: str,
    event_id: str,
) -> None:
    """Delete an event from Google Calendar.

    Args:
        service: Google Calendar service instance.
        calendar_id: Calendar ID containing the event.
        event_id: ID of the event to delete.

    Raises:
        GoogleCalendarError: If event deletion fails.
    """
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as error:
        logger.error(f"Failed to delete event: {error}")
        raise GoogleCalendarError(f"Failed to delete event: {str(error)}") from error
