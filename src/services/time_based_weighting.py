"""Time-based weighting service for slideshow content prioritization."""

import random
from datetime import datetime, time
from typing import Any

from src.config.config_manager import ConfigManager
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class WeightingEntry:
    """Represents a single weighting entry in the collection."""

    def __init__(
        self,
        day: str,
        time_str: str,
        weights: dict[str, float],
        description: str = "",
    ):
        self.day = day.lower()
        self.time = self._parse_time(time_str)
        self.weights = weights
        self.description = description

    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object."""
        try:
            hour, minute = map(int, time_str.split(":"))
            return time(hour, minute)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid time format '{time_str}': {e}")
            return time(0, 0)  # Default to midnight

    def __repr__(self) -> str:
        return f"WeightingEntry(day='{self.day}', time={self.time}, description='{self.description}')"


class TimeBasedWeightingService:
    """Service for managing time-based content weighting in slideshows."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize the time-based weighting service.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.config = config_manager.config
        self.weighting_config = (
            self.config.get("slideshow", {})
            .get("weighted_media", {})
            .get("time_based_weighting", {})
        )
        self.enabled = self.weighting_config.get("enabled", False)
        self.debug_mode = self.weighting_config.get("debug_mode", False)

        # New collection-based weighting
        self.weighting_collection = self._load_weighting_collection()

        # Legacy support
        self.day_of_week_enabled = self.weighting_config.get(
            "day_of_week_enabled", False
        )
        self.daily_time_ranges = self.weighting_config.get("daily_time_ranges", {})
        self.daily_weights = self.weighting_config.get("daily_weights", {})  # Legacy
        self.hourly_weights = self.weighting_config.get("hourly_weights", {})

        if self.enabled:
            if self.weighting_collection:
                logger.info(
                    f"Time-based weighting service initialized with {len(self.weighting_collection)} collection entries"
                )
            else:
                self._validate_hourly_weights()
                logger.info(
                    "Time-based weighting service initialized with legacy hourly weights"
                )
        else:
            logger.info("Time-based weighting service disabled")

    def _load_weighting_collection(self) -> list[WeightingEntry]:
        """Load weighting collection from configuration."""
        collection_data = self.weighting_config.get("weighting_collection", [])
        entries = []

        for entry_data in collection_data:
            try:
                entry = WeightingEntry(
                    day=entry_data.get("day", ""),
                    time_str=entry_data.get("time", "00:00"),
                    weights=entry_data.get("weights", {}),
                    description=entry_data.get("description", ""),
                )
                entries.append(entry)
            except Exception as e:
                logger.error(f"Failed to load weighting entry {entry_data}: {e}")

        # Sort entries by day and time for efficient lookup
        entries.sort(key=lambda x: (self._day_to_number(x.day), x.time))
        return entries

    def _day_to_number(self, day: str) -> int:
        """Convert day name to number (0=Monday, 6=Sunday)."""
        day_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        return day_map.get(day.lower(), 0)

    def _number_to_day(self, day_num: int) -> str:
        """Convert day number to name."""
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        return day_names[day_num] if 0 <= day_num <= 6 else "monday"

    def get_current_hour_weights(self) -> dict[str, float]:
        """Get weights for the current hour based on collection or legacy system.

        Returns:
            Dictionary of content type weights
        """
        if not self.enabled:
            return self._get_default_weights()

        # Use collection-based weighting if available
        if self.weighting_collection:
            return self._get_collection_weights()

        # Fall back to legacy system
        return self._get_legacy_weights()

    def _get_collection_weights(self) -> dict[str, float]:
        """Get weights from the collection-based system."""
        now = datetime.now()
        current_day = self._number_to_day(now.weekday())
        current_time = now.time()

        # Find the most recent entry that applies to current day/time
        applicable_entry = self._find_applicable_entry(current_day, current_time)

        if applicable_entry:
            if self.debug_mode:
                logger.info(
                    f"Collection weighting: {current_day} {current_time.strftime('%H:%M')} -> "
                    f"{applicable_entry.description} (weights: {applicable_entry.weights})"
                )
            return applicable_entry.weights

        # Fall back to default weights if no applicable entry found
        logger.warning(
            f"No applicable weighting entry found for {current_day} {current_time}"
        )
        return self._get_default_weights()

    def _find_applicable_entry(
        self, current_day: str, current_time: time
    ) -> WeightingEntry | None:
        """Find the most recent applicable weighting entry."""
        current_day_num = self._day_to_number(current_day)

        # First, look for entries on the same day that are before or at current time
        same_day_entries = [
            entry
            for entry in self.weighting_collection
            if self._day_to_number(entry.day) == current_day_num
            and entry.time <= current_time
        ]

        if same_day_entries:
            # Return the most recent entry for today
            return max(same_day_entries, key=lambda x: x.time)

        # If no entries for today, look for the most recent entry from previous days
        # Start from yesterday and work backwards
        for days_back in range(1, 8):  # Check up to a week back
            check_day_num = (current_day_num - days_back) % 7
            self._number_to_day(check_day_num)

            day_entries = [
                entry
                for entry in self.weighting_collection
                if self._day_to_number(entry.day) == check_day_num
            ]

            if day_entries:
                # Return the latest entry from this day
                return max(day_entries, key=lambda x: x.time)

        return None

    def _get_legacy_weights(self) -> dict[str, float]:
        """Get weights using the legacy time range system."""
        now = datetime.now()
        current_hour = now.hour
        current_weekday = now.weekday()  # 0=Monday, 6=Sunday

        if self.day_of_week_enabled and self.daily_time_ranges:
            # Use day-of-week time ranges
            day_ranges = self.daily_time_ranges.get(str(current_weekday), [])
            current_weights: dict[str, float] = {}

            # Find the time range that covers the current hour
            for time_range in day_ranges:
                start_hour = time_range.get("start_hour", 0)
                end_hour = time_range.get("end_hour", 24)

                # Handle ranges that span midnight (e.g., 18-24 becomes 18-24)
                if start_hour <= current_hour < end_hour:
                    current_weights = time_range.get("weights", {})
                    range_name = time_range.get(
                        "name", f"Range {start_hour}-{end_hour}"
                    )

                    if self.debug_mode:
                        day_names = [
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday",
                        ]
                        logger.info(
                            f"Current day: {day_names[current_weekday]}, hour: {current_hour}, "
                            f"time range: {range_name}, weights: {current_weights}"
                        )
                    break

            if current_weights:
                return current_weights

        # Fall back to hourly weights if no day-specific ranges found
        if self.hourly_weights:
            hour_weights = self.hourly_weights.get(str(current_hour), {})
            if hour_weights:
                if self.debug_mode:
                    logger.info(
                        f"Using hourly weights for hour {current_hour}: {hour_weights}"
                    )
                return dict(hour_weights)  # Type cast to ensure proper return type

        # Final fallback to default weights
        logger.warning(f"No weights found for hour {current_hour}, using defaults")
        return self._get_default_weights()

    def _get_default_weights(self) -> dict[str, float]:
        """Get default weights when time-based weighting is disabled.

        Returns:
            Default weights for content types
        """
        return {"media": 0.6, "calendar": 0.2, "weather": 0.1, "web_news": 0.1}

    def select_content_type(self) -> str:
        """Select a content type based on current time weights.

        Returns:
            Selected content type (media, calendar, weather, web_news)
        """
        weights = self.get_current_hour_weights()

        if not weights:
            logger.warning("No weights available, using default selection")
            return "media"

        # Create weighted random selection
        content_types = list(weights.keys())
        weight_values = list(weights.values())

        selected = random.choices(  # nosec B311
            content_types, weights=weight_values, k=1
        )[0]

        if self.debug_mode:
            logger.info(f"Selected content type: {selected} (weights: {weights})")

        return selected

    def get_weighted_media_sources(
        self, all_sources: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Get media sources with adjusted weights based on current time.

        Args:
            all_sources: List of all available media sources

        Returns:
            List of media sources with time-adjusted weights
        """
        if not self.enabled:
            return all_sources

        current_weights = self.get_current_hour_weights()
        weighted_sources = []

        for source in all_sources:
            source_name = source.get("name", "").lower()
            source_copy = source.copy()

            # Map source names to content types
            content_type = self._map_source_to_content_type(source_name)

            # Apply time-based weight adjustment
            if content_type in current_weights:
                base_weight = source_copy.get("weight", 1.0)
                time_weight = current_weights[content_type]
                adjusted_weight = base_weight * time_weight
                source_copy["weight"] = adjusted_weight

                if self.debug_mode:
                    logger.info(
                        f"Source '{source_name}' ({content_type}): "
                        f"base_weight={base_weight}, time_weight={time_weight}, "
                        f"adjusted_weight={adjusted_weight}"
                    )

            weighted_sources.append(source_copy)

        return weighted_sources

    def _map_source_to_content_type(self, source_name: str) -> str:
        """Map source name to content type for weighting."""
        source_name_lower = source_name.lower()

        if any(
            keyword in source_name_lower
            for keyword in ["photo", "family", "media", "drive"]
        ):
            return "media"
        elif any(keyword in source_name_lower for keyword in ["calendar", "event"]):
            return "calendar"
        elif any(keyword in source_name_lower for keyword in ["weather", "forecast"]):
            return "weather"
        elif any(
            keyword in source_name_lower for keyword in ["web", "news", "content"]
        ):
            return "web_news"
        else:
            # Default mapping based on common patterns
            return "media"

    def get_weighting_summary(self) -> dict[str, Any]:
        """Get a summary of current weighting status.

        Returns:
            Dictionary with weighting information
        """
        now = datetime.now()
        current_weights = self.get_current_hour_weights()

        return {
            "enabled": self.enabled,
            "current_hour": now.hour,
            "current_day": now.strftime("%A"),
            "current_weights": current_weights,
            "using_collection": bool(self.weighting_collection),
            "collection_size": len(self.weighting_collection)
            if self.weighting_collection
            else 0,
            "debug_mode": self.debug_mode,
        }

    def validate_configuration(self) -> list[str]:
        """Validate the weighting configuration.

        Returns:
            List of validation error messages
        """
        errors: list[str] = []

        if not self.enabled:
            return errors

        # Validate collection-based weighting if used
        if self.weighting_collection:
            errors.extend(self._validate_collection())
        else:
            # Validate legacy system
            errors.extend(self._validate_legacy_system())

        return errors

    def _validate_collection(self) -> list[str]:
        """Validate the weighting collection."""
        errors = []

        for i, entry in enumerate(self.weighting_collection):
            # Validate weights sum to 1.0
            total_weight = sum(entry.weights.values())
            if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
                errors.append(
                    f"Entry {i+1} ({entry.day} {entry.time}): weights sum to {total_weight}, should be 1.0"
                )

            # Validate day names
            if entry.day not in [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]:
                errors.append(f"Entry {i+1}: invalid day '{entry.day}'")

            # Validate content types
            valid_types = {"media", "calendar", "weather", "web_news"}
            invalid_types = set(entry.weights.keys()) - valid_types
            if invalid_types:
                errors.append(f"Entry {i+1}: invalid content types {invalid_types}")

        return errors

    def _validate_legacy_system(self) -> list[str]:
        """Validate the legacy weighting system."""
        errors = []

        # Validate hourly weights
        if self.hourly_weights:
            for hour, weights in self.hourly_weights.items():
                total_weight = sum(weights.values())
                if abs(total_weight - 1.0) > 0.01:
                    errors.append(
                        f"Hour {hour}: weights sum to {total_weight}, should be 1.0"
                    )

        # Validate daily time ranges
        if self.daily_time_ranges:
            for day, ranges in self.daily_time_ranges.items():
                for i, time_range in enumerate(ranges):
                    weights = time_range.get("weights", {})
                    total_weight = sum(weights.values())
                    if abs(total_weight - 1.0) > 0.01:
                        errors.append(
                            f"Day {day}, range {i+1}: weights sum to {total_weight}, should be 1.0"
                        )

        return errors

    def _validate_hourly_weights(self) -> None:
        """Validate that hourly weights sum to 1.0 for each hour."""
        if not self.hourly_weights:
            return

        for hour, weights in self.hourly_weights.items():
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(
                    f"Weights for hour {hour} sum to {total_weight}, should be 1.0"
                )
