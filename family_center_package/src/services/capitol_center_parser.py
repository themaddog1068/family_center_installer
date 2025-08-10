import json
import re
from datetime import datetime, timedelta
from pathlib import Path


class EventInfo:
    def __init__(self, title: str, date: str, venue: str = "", description: str = ""):
        self.title = title
        self.date = date
        self.venue = venue
        self.description = description

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "date": self.date,
            "venue": self.venue,
            "description": self.description,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventInfo):
            return False
        return (
            self.title == other.title
            and self.date == other.date
            and self.venue == other.venue
        )

    def __hash__(self) -> int:
        return hash((self.title, self.date, self.venue))


class CapitolCenterParser:
    def __init__(self) -> None:
        # Tracking file for storing previous events
        self.tracking_file = Path("data/tracking/capitol_center_events_tracking.json")
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)

        # Load previous events
        self.previous_events = self._load_previous_events()

    def _load_previous_events(self) -> set[EventInfo]:
        """Load previously tracked events from file and clean up past events."""
        if not self.tracking_file.exists():
            return set()

        try:
            with open(self.tracking_file) as f:
                data = json.load(f)
                events = set()
                future_events = []

                for event_data in data.get("events", []):
                    event = EventInfo(
                        title=event_data.get("title", ""),
                        date=event_data.get("date", ""),
                        venue=event_data.get("venue", ""),
                        description=event_data.get("description", ""),
                    )

                    # Only keep future events in the tracking
                    if self._is_future_event(event):
                        events.add(event)
                        future_events.append(event_data)
                    # Past events are filtered out

                # If we filtered out past events, update the tracking file
                if len(future_events) != len(data.get("events", [])):
                    print(
                        f"Cleaned up {len(data.get('events', [])) - len(future_events)} past events from Capitol Center tracking file"
                    )
                    self._save_events_dict(future_events)

                return events
        except Exception as e:
            print(f"Error loading previous Capitol Center events: {e}")
            return set()

    def _save_events(self, events: list[EventInfo]) -> None:
        """Save current events to tracking file."""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "events": [event.to_dict() for event in events],
            }
            with open(self.tracking_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving Capitol Center events: {e}")

    def _save_events_dict(self, events: list[dict[str, str]]) -> None:
        """Save events as dict objects to tracking file."""
        try:
            data = {"last_updated": datetime.now().isoformat(), "events": events}
            with open(self.tracking_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving Capitol Center events: {e}")

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        if not date_str or not date_str.strip():
            return datetime.now()

        try:
            # Clean up the date string
            date_str = date_str.strip()

            # Capitol Center date formats: "Jul 18, 7:00pm & Jul 19, 7:00pm", "Jul 20, 7:00pm"
            # Extract the first date from the string
            date_match = re.search(r"(\w{3}\s+\d{1,2})", date_str)
            if date_match:
                date_part = date_match.group(1)

                # Try various date formats
                formats = [
                    "%b %d",  # Jul 18
                    "%B %d",  # July 18
                ]

                for fmt in formats:
                    try:
                        parsed_date = datetime.strptime(date_part, fmt)
                        # Assume current year
                        current_year = datetime.now().year
                        parsed_date = parsed_date.replace(year=current_year)
                        return parsed_date
                    except ValueError:
                        continue

            # If no format matches, return current date
            return datetime.now()
        except Exception:
            return datetime.now()

    def _is_future_event(self, event: EventInfo) -> bool:
        """Check if event is in the future (not past)."""
        try:
            event_date = self._parse_date(event.date)
            # Compare just the date part, not the time
            event_date_only = event_date.date()
            now_date_only = datetime.now().date()
            return event_date_only >= now_date_only
        except Exception:
            return False

    def _is_recent_event(self, event: EventInfo) -> bool:
        """Check if event is from the last 7 days (expanded window for newly announced events)."""
        try:
            event_date = self._parse_date(event.date)
            seven_days_ago = datetime.now() - timedelta(days=7)
            return event_date >= seven_days_ago
        except Exception:
            return False

    def _is_newly_announced(
        self, event: EventInfo, all_current_events: list[EventInfo]
    ) -> bool:
        """Check if this event is newly announced (not in previous tracking)."""
        return event not in self.previous_events

    def parse_content(self, text: str) -> dict[str, list[EventInfo]]:
        """Parse Capitol Center content to extract events."""
        # This method will be called by the web content service
        # The actual parsing will be done in the web content service using HTML selectors
        return {"all_events": [], "new_events": []}

    def create_formatted_content(self, parsed_data: dict[str, list[EventInfo]]) -> dict:
        """Create formatted content for slide generation."""
        content = {
            "source": "Capitol Center for the Arts",
            "type": "theater_events",
            "content": [],
        }

        all_events = parsed_data.get("all_events", [])
        new_events = parsed_data.get("new_events", [])

        # Filter out past events - only show future events
        future_events = [event for event in all_events if self._is_future_event(event)]
        future_new_events = [
            event for event in new_events if self._is_future_event(event)
        ]

        # Priority order for events to show:
        # 1. Newly announced future events (regardless of date)
        # 2. Recent future events (last 7 days)
        # 3. Upcoming future events (next 5 events)

        events_to_show = []

        # First, add newly announced future events
        for event in future_new_events:
            if event not in events_to_show:
                events_to_show.append(event)

        # Then add recent future events that aren't already included
        recent_future_events = [
            event for event in future_events if self._is_recent_event(event)
        ]
        for event in recent_future_events:
            if event not in events_to_show:
                events_to_show.append(event)

        # Finally, add upcoming future events if we don't have enough
        upcoming_future_events = future_events[:5]  # Next 5 future events
        for event in upcoming_future_events:
            if event not in events_to_show and len(events_to_show) < 5:
                events_to_show.append(event)

        # Limit to 5 events total
        events_to_show = events_to_show[:5]

        content_list = content["content"]
        for event in events_to_show:
            if isinstance(content_list, list):
                content_list.append(
                    {
                        "title": event.title,
                        "date": event.date,
                        "venue": event.venue,
                        "description": event.description,
                        "type": "event",
                    }
                )

        return content


def parse_capitol_center_content(text: str) -> dict:
    """Parse Capitol Center content and return formatted data."""
    parser = CapitolCenterParser()
    parsed_data = parser.parse_content(text)
    return parser.create_formatted_content(parsed_data)
