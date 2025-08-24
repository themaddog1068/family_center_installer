"""
Example module for the Python project template.

This module demonstrates basic structure and can be replaced with your actual implementation.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from src.utils.errors import ErrorSeverity, FamilyCenterError


class ExampleClass:
    """Example class demonstrating basic structure."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the example class.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._initialized = True

    def process_data(self, data: str) -> str:
        """
        Process some data.

        Args:
            data: Input data to process

        Returns:
            str: Processed data

        Raises:
            ValueError: If data is empty
        """
        if not data.strip():
            raise ValueError("Data cannot be empty")

        try:
            # Example processing logic
            processed = data.upper()
            return f"Processed: {processed}"
        except Exception as e:
            print(f"Error processing data: {e}")
            return f"Error: {str(e)}"

    def get_status(self) -> dict[str, Any]:
        """Get the current status of the instance.

        Returns:
            Dict containing status information
        """
        return {
            "initialized": self._initialized,
            "config_keys": list(self.config.keys()),
            "ready": True,
        }


class DisplayError(FamilyCenterError):
    """Raised when there is an error with the display."""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> None:
        """Initialize the error.

        Args:
            message: Error message
            severity: Error severity
        """
        super().__init__(message, severity)


class DisplayState(str, Enum):
    """Display state enum."""

    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class DisplayType(str, Enum):
    """Display type enum."""

    DIGITAL = "digital"
    PHYSICAL = "physical"


class EventType(str, Enum):
    """Event type enum."""

    PRESENTATION = "presentation"
    MEETING = "meeting"
    BREAK = "break"
    OTHER = "other"


class Event:
    """Event class for display events."""

    def __init__(
        self,
        id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        type: EventType = EventType.OTHER,
    ) -> None:
        """Initialize the event.

        Args:
            id: Event ID
            title: Event title
            start_time: Event start time
            end_time: Event end time
            type: Event type
        """
        self.id = id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.type = type


class TimeSlot:
    """Time slot class for display scheduling."""

    def __init__(self, start_time: datetime, end_time: datetime) -> None:
        """Initialize the time slot.

        Args:
            start_time: Slot start time
            end_time: Slot end time
        """
        self.start_time = start_time
        self.end_time = end_time


class Display:
    """Class for handling display and formatting of output."""

    def __init__(
        self,
        id: str,
        name: str,
        type: DisplayType,
        location: str,
    ) -> None:
        """Initialize the display.

        Args:
            id: Display ID
            name: Display name
            type: Display type
            location: Display location
        """
        self.id = id
        self.name = name
        self.type = type
        self.location = location
        self.state = DisplayState.OFFLINE
        self.error_message: str | None = None
        self.events: list[Event] = []
        self.time_slots: list[TimeSlot] = []

    def turn_on(self) -> None:
        """Turn on the display."""
        if self.state == DisplayState.ONLINE:
            raise DisplayError("Display is already on")
        self.state = DisplayState.ONLINE
        self.error_message = None

    def turn_off(self) -> None:
        """Turn off the display."""
        self.state = DisplayState.OFFLINE
        self.error_message = None

    def set_error(self, message: str) -> None:
        """Set display error state.

        Args:
            message: Error message
        """
        self.state = DisplayState.ERROR
        self.error_message = message

    def clear_error(self) -> None:
        """Clear display error state."""
        self.state = DisplayState.OFFLINE
        self.error_message = None

    def add_event(self, event: Event) -> None:
        """Add an event to the display.

        Args:
            event: Event to add
        """
        self.events.append(event)

    def remove_event(self, event_id: str) -> None:
        """Remove an event from the display.

        Args:
            event_id: ID of event to remove
        """
        self.events = [e for e in self.events if e.id != event_id]

    def add_time_slot(self, time_slot: TimeSlot) -> None:
        """Add a time slot to the display.

        Args:
            time_slot: Time slot to add
        """
        self.time_slots.append(time_slot)

    def remove_time_slot(self, time_slot: TimeSlot) -> None:
        """Remove a time slot from the display.

        Args:
            time_slot: Time slot to remove
        """
        self.time_slots.remove(time_slot)


class DisplayManager:
    """Class for managing multiple displays."""

    def __init__(self) -> None:
        """Initialize the display manager."""
        self.displays: dict[str, Display] = {}

    def add_display(self, display: Display) -> None:
        """Add a display to the manager.

        Args:
            display: Display to add
        """
        self.displays[display.id] = display

    def remove_display(self, display_id: str) -> None:
        """Remove a display from the manager.

        Args:
            display_id: ID of display to remove
        """
        if display_id not in self.displays:
            raise DisplayError(f"Display {display_id} not found")
        del self.displays[display_id]

    def get_display(self, display_id: str) -> Display:
        """Get a display by ID.

        Args:
            display_id: ID of display to get

        Returns:
            Display instance

        Raises:
            DisplayError: If display not found
        """
        if display_id not in self.displays:
            raise DisplayError(f"Display {display_id} not found")
        return self.displays[display_id]

    def clear_displays(self) -> None:
        """Clear all displays."""
        self.displays.clear()

    def format_output(self, data: Any) -> str:
        """Format the output data.

        Args:
            data: The data to format.

        Returns:
            str: The formatted output.
        """
        return str(data)

    def display_error(self, error: Exception) -> None:
        """Display an error message.

        Args:
            error: The error to display.
        """
        print(f"Error: {str(error)}")

    def display_success(self, message: str) -> None:
        """Display a success message.

        Args:
            message: The message to display.
        """
        print(f"Success: {message}")

    def display_info(self, message: str) -> None:
        """Display an info message.

        Args:
            message: The message to display.
        """
        print(f"Info: {message}")

    def display_warning(self, message: str) -> None:
        """Display a warning message.

        Args:
            message: The message to display.
        """
        print(f"Warning: {message}")

    def display_debug(self, message: str) -> None:
        """Display a debug message.

        Args:
            message: The message to display.
        """
        print(f"Debug: {message}")

    def display_table(
        self, data: list[dict[str, Any]], headers: list[str] | None = None
    ) -> None:
        """Display data in a table format.

        Args:
            data: The data to display.
            headers: Optional list of headers for the table.
        """
        if not data:
            print("No data to display")
            return

        if headers is None:
            headers = list(data[0].keys())

        # Calculate column widths
        col_widths = {header: len(str(header)) for header in headers}
        for row in data:
            for header in headers:
                col_widths[header] = max(
                    col_widths[header], len(str(row.get(header, "")))
                )

        # Print headers
        header_str = " | ".join(f"{header:{col_widths[header]}}" for header in headers)
        print(header_str)
        print("-" * len(header_str))

        # Print rows
        for row in data:
            row_str = " | ".join(
                f"{str(row.get(header, '')):{col_widths[header]}}" for header in headers
            )
            print(row_str)

    def status(self) -> str:
        """Get the current status of the display.

        Returns:
            str: The current status.
        """
        return "Display is ready."

    def update(self, data: Any) -> None:
        """Update the display with new data.

        Args:
            data: The data to update the display with.
        """
        print(f"Updating display with: {data}")

    def clear(self) -> None:
        """Clear the display."""
        print("Display cleared.")

    def error(self, error: Exception) -> None:
        """Handle and display an error.

        Args:
            error: The error to handle and display.
        """
        print(f"Error: {str(error)}")
