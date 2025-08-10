"""Time-based weighting service for slideshow content prioritization."""

import random
from datetime import datetime
from typing import Any

from src.config.config_manager import ConfigManager
from src.core.logging_config import get_logger

logger = get_logger(__name__)


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
        self.day_of_week_enabled = self.weighting_config.get(
            "day_of_week_enabled", False
        )
        self.daily_time_ranges = self.weighting_config.get("daily_time_ranges", {})
        self.daily_weights = self.weighting_config.get("daily_weights", {})  # Legacy
        self.hourly_weights = self.weighting_config.get("hourly_weights", {})

        if self.enabled:
            self._validate_hourly_weights()
            logger.info("Time-based weighting service initialized and enabled")
        else:
            logger.info("Time-based weighting service disabled")

    def _validate_hourly_weights(self) -> None:
        """Validate that hourly weights total 100% for each hour."""
        for hour, weights in self.hourly_weights.items():
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
                logger.warning(
                    f"Hour {hour} weights total {total_weight:.3f}, should total 1.0"
                )

    def get_current_hour_weights(self) -> dict[str, float]:
        """Get the content type weights for the current hour and day.

        Returns:
            Dictionary mapping content types to their weights for the current hour
        """
        if not self.enabled:
            return self._get_default_weights()

        current_datetime = datetime.now()
        current_hour = current_datetime.hour
        current_weekday = current_datetime.weekday()  # 0=Monday, 6=Sunday

        if self.day_of_week_enabled and self.daily_time_ranges:
            # Use day-of-week time ranges
            day_ranges = self.daily_time_ranges.get(current_weekday, [])
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

            # If no range found, use default weights
            if not current_weights:
                current_weights = self._get_default_weights()
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
                    logger.warning(
                        f"No time range found for {day_names[current_weekday]} {current_hour}:00, "
                        f"using default weights: {current_weights}"
                    )

            weights = current_weights

        elif self.day_of_week_enabled and self.daily_weights:
            # Legacy: Use day-of-week specific weights
            day_weights = self.daily_weights.get(current_weekday, {})
            legacy_weights: dict[str, float] = day_weights.get(current_hour, {})

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
                    f"Current day: {day_names[current_weekday]}, hour: {current_hour}, weights: {legacy_weights}"
                )

            weights = legacy_weights
        else:
            # Fall back to legacy hourly weights
            hourly_weights: dict[str, float] = self.hourly_weights.get(current_hour, {})

            if self.debug_mode:
                logger.info(f"Current hour: {current_hour}, weights: {hourly_weights}")

            weights = hourly_weights

        return weights

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
        """Map a source name to a content type.

        Args:
            source_name: Name of the media source

        Returns:
            Content type (media, calendar, weather, web_news)
        """
        source_name_lower = source_name.lower()

        if any(keyword in source_name_lower for keyword in ["calendar", "event"]):
            content_type = "calendar"
        elif any(keyword in source_name_lower for keyword in ["weather", "forecast"]):
            content_type = "weather"
        elif any(keyword in source_name_lower for keyword in ["news", "web"]):
            content_type = "web_news"
        else:
            content_type = "media"

        if self.debug_mode:
            logger.info(
                f"Mapping source '{source_name}' to content type '{content_type}'"
            )

        return content_type

    def get_weighting_summary(self) -> dict[str, Any]:
        """Get a summary of current weighting configuration.

        Returns:
            Dictionary with weighting summary information
        """
        current_datetime = datetime.now()
        current_hour = current_datetime.hour
        current_weekday = current_datetime.weekday()
        current_weights = self.get_current_hour_weights()

        day_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        current_day_name = day_names[current_weekday]

        summary = {
            "enabled": self.enabled,
            "debug_mode": self.debug_mode,
            "day_of_week_enabled": self.day_of_week_enabled,
            "current_day": current_day_name,
            "current_weekday": current_weekday,
            "current_hour": current_hour,
            "current_weights": current_weights,
            "total_weight": sum(current_weights.values()) if current_weights else 0.0,
        }

        if self.day_of_week_enabled:
            if self.daily_time_ranges:
                summary["daily_time_ranges_configured"] = len(self.daily_time_ranges)
                # Add current time range info
                day_ranges = self.daily_time_ranges.get(current_weekday, [])
                for time_range in day_ranges:
                    start_hour = time_range.get("start_hour", 0)
                    end_hour = time_range.get("end_hour", 24)
                    if start_hour <= current_hour < end_hour:
                        summary["current_time_range"] = time_range.get(
                            "name", f"Range {start_hour}-{end_hour}"
                        )
                        break
            else:
                summary["daily_weights_configured"] = len(self.daily_weights)
        else:
            summary["hourly_weights_configured"] = len(self.hourly_weights)

        return summary

    def validate_configuration(self) -> list[str]:
        """Validate the time-based weighting configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        if not self.enabled:
            return errors

        if self.day_of_week_enabled and self.daily_time_ranges:
            # Validate day-of-week time ranges configuration
            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            required_types = {"media", "calendar", "weather", "web_news"}

            # Check if all 7 days are configured
            missing_days = set(range(7)) - set(self.daily_time_ranges.keys())
            if missing_days:
                missing_day_names = [day_names[day] for day in missing_days]
                errors.append(
                    f"Missing daily time ranges for days: {missing_day_names}"
                )

            # Check each day's time ranges
            for day, day_ranges in self.daily_time_ranges.items():
                day_name = day_names[day]

                # Check that time ranges cover all 24 hours
                covered_hours: set[int] = set()
                for time_range in day_ranges:
                    start_hour = time_range.get("start_hour", 0)
                    end_hour = time_range.get("end_hour", 24)
                    covered_hours.update(range(start_hour, end_hour))

                missing_hours = set(range(24)) - covered_hours
                if missing_hours:
                    errors.append(
                        f"{day_name} missing time ranges for hours: {sorted(missing_hours)}"
                    )

                # Check that each time range's weights total 1.0
                for time_range in day_ranges:
                    weights = time_range.get("weights", {})
                    total_weight = sum(weights.values())
                    range_name = time_range.get(
                        "name",
                        f"Range {time_range.get('start_hour', 0)}-{time_range.get('end_hour', 24)}",
                    )

                    if abs(total_weight - 1.0) > 0.01:
                        errors.append(
                            f"{day_name} {range_name} weights total {total_weight:.3f}, should total 1.0"
                        )

                # Check for required content types
                for time_range in day_ranges:
                    weights = time_range.get("weights", {})
                    missing_types = required_types - set(weights.keys())
                    if missing_types:
                        range_name = time_range.get(
                            "name",
                            f"Range {time_range.get('start_hour', 0)}-{time_range.get('end_hour', 24)}",
                        )
                        errors.append(
                            f"{day_name} {range_name} missing content types: {missing_types}"
                        )

        elif self.day_of_week_enabled and self.daily_weights:
            # Validate legacy day-of-week configuration
            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            required_types = {"media", "calendar", "weather", "web_news"}

            # Check if all 7 days are configured
            missing_days = set(range(7)) - set(self.daily_weights.keys())
            if missing_days:
                missing_day_names = [day_names[day] for day in missing_days]
                errors.append(f"Missing daily weights for days: {missing_day_names}")

            # Check each day's hourly weights
            for day, day_weights in self.daily_weights.items():
                day_name = day_names[day]

                # Check that each hour's weights total 1.0
                for hour, weights in day_weights.items():
                    total_weight = sum(weights.values())
                    if abs(total_weight - 1.0) > 0.01:
                        errors.append(
                            f"{day_name} {hour}:00 weights total {total_weight:.3f}, should total 1.0"
                        )

                # Check for required content types
                for hour, weights in day_weights.items():
                    missing_types = required_types - set(weights.keys())
                    if missing_types:
                        errors.append(
                            f"{day_name} {hour}:00 missing content types: {missing_types}"
                        )
        else:
            # Validate legacy hourly configuration
            # Check if all 24 hours are configured
            missing_hours = set(range(24)) - set(self.hourly_weights.keys())
            if missing_hours:
                errors.append(
                    f"Missing hourly weights for hours: {sorted(missing_hours)}"
                )

            # Check that each hour's weights total 1.0
            for hour, weights in self.hourly_weights.items():
                total_weight = sum(weights.values())
                if abs(total_weight - 1.0) > 0.01:
                    errors.append(
                        f"Hour {hour} weights total {total_weight:.3f}, should total 1.0"
                    )

            # Check for required content types
            required_types = {"media", "calendar", "weather", "web_news"}
            for hour, weights in self.hourly_weights.items():
                missing_types = required_types - set(weights.keys())
                if missing_types:
                    errors.append(f"Hour {hour} missing content types: {missing_types}")

        return errors
