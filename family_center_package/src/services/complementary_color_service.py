#!/usr/bin/env python3
"""
Complementary Color Service

This service computes and caches complementary colors for all images
in the media directories. It should be called at startup and after
Google Drive sync operations.
"""

import json
import logging
from pathlib import Path
from typing import Any

# Try to import color processing dependencies
COLOR_ANALYSIS = True
try:
    from colorthief import ColorThief
except ImportError:
    COLOR_ANALYSIS = False
    ColorThief = None

logger = logging.getLogger(__name__)


class ComplementaryColorService:
    """Service for computing and caching complementary colors for images."""

    def __init__(self, media_base_path: str = "media"):
        """Initialize the complementary color service.

        Args:
            media_base_path: Base path for media directories
        """
        self.media_base_path = Path(media_base_path)
        self.remote_drive_path = self.media_base_path / "remote_drive"
        self.local_drive_path = self.media_base_path / "local_drive"
        self.tracking_file = self.remote_drive_path / ".file_tracking.json"

    def _is_image_file(self, file_path: Path) -> bool:
        """Check if a file is an image file.

        Args:
            file_path: Path to check

        Returns:
            True if the file is an image file
        """
        image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".heic",
            ".heif",
        }
        return file_path.suffix.lower() in image_extensions

    def _should_compute_complementary_color(self, file_path: Path) -> bool:
        """Check if we should compute complementary color for this file.

        Args:
            file_path: Path to the file

        Returns:
            True if we should compute complementary color for this file
        """
        # Only compute for remote and local media files, not calendar images
        file_str = str(file_path)
        return (
            self._is_image_file(file_path)
            and "calendar" not in file_str
            and (
                self.remote_drive_path in file_path.parents
                or self.local_drive_path in file_path.parents
            )
        )

    def _get_complementary_color(self, image_path: Path) -> str:
        """Extract complementary color from an image for background.

        Args:
            image_path: Path to the image file

        Returns:
            Hex color string for complementary background
        """
        if not COLOR_ANALYSIS or ColorThief is None:
            return "#000000"  # Default fallback color

        try:
            # Get dominant color from image
            color_thief = ColorThief(str(image_path))
            dominant_color = color_thief.get_color(quality=1)

            # Calculate complementary color (opposite on color wheel)
            r, g, b = dominant_color

            # Method 1: Simple RGB complement
            r_comp1 = 255 - r
            g_comp1 = 255 - g
            b_comp1 = 255 - b

            # Method 2: HSV complement (more accurate color theory)
            # Convert to HSV
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            diff = max_val - min_val

            if diff == 0:
                # Grayscale - use a warm color
                r_comp2, g_comp2, b_comp2 = 200, 150, 100
            else:
                # Calculate hue
                if max_val == r:
                    hue = (60 * ((g - b) / diff) + 360) % 360
                elif max_val == g:
                    hue = (60 * ((b - r) / diff) + 120) % 360
                else:
                    hue = (60 * ((r - g) / diff) + 240) % 360

                # Complementary hue (opposite on color wheel)
                comp_hue = (hue + 180) % 360

                # Convert back to RGB
                c = max_val / 255
                x = c * (1 - abs((comp_hue / 60) % 2 - 1))
                m = (max_val - c * 255) / 255

                if 0 <= comp_hue < 60:
                    r_comp2, g_comp2, b_comp2 = c, x, 0
                elif 60 <= comp_hue < 120:
                    r_comp2, g_comp2, b_comp2 = x, c, 0
                elif 120 <= comp_hue < 180:
                    r_comp2, g_comp2, b_comp2 = 0, c, x
                elif 180 <= comp_hue < 240:
                    r_comp2, g_comp2, b_comp2 = 0, x, c
                elif 240 <= comp_hue < 300:
                    r_comp2, g_comp2, b_comp2 = x, 0, c
                else:
                    r_comp2, g_comp2, b_comp2 = c, 0, x

                # Convert to 0-255 range
                r_comp2 = int((r_comp2 + m) * 255)
                g_comp2 = int((g_comp2 + m) * 255)
                b_comp2 = int((b_comp2 + m) * 255)

            # Combine both methods for better results
            r_final = (r_comp1 + r_comp2) // 2
            g_final = (g_comp1 + g_comp2) // 2
            b_final = (b_comp1 + b_comp2) // 2

            # Ensure minimum brightness and boost saturation
            brightness = (r_final + g_final + b_final) / 3
            if brightness < 50:
                # Boost brightness while maintaining color
                boost = 50 / brightness if brightness > 0 else 1.5
                r_final = min(255, int(r_final * boost))
                g_final = min(255, int(g_final * boost))
                b_final = min(255, int(b_final * boost))

            # Return as hex color
            return f"#{r_final:02x}{g_final:02x}{b_final:02x}"

        except Exception as e:
            logger.debug(
                f"Could not extract complementary color from {image_path}: {e}"
            )
            return "#000000"  # Default fallback color

    def _load_tracking_data(self) -> dict[str, Any]:
        """Load the file tracking data.

        Returns:
            Dictionary containing file tracking data
        """
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file) as f:
                    return dict[str, Any](json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load file tracking data: {e}")
        return {}

    def _save_tracking_data(self, tracking_data: dict[str, Any]) -> None:
        """Save the file tracking data.

        Args:
            tracking_data: Dictionary containing file tracking data
        """
        try:
            # Create backup
            if self.tracking_file.exists():
                backup_file = self.tracking_file.with_suffix(".json.bak")
                with open(self.tracking_file) as src, open(backup_file, "w") as dst:
                    dst.write(src.read())
                logger.info(f"Created backup: {backup_file}")

            # Save updated data
            with open(self.tracking_file, "w") as f:
                json.dump(tracking_data, f, indent=2)
            logger.info(f"Updated file tracking data: {self.tracking_file}")

        except Exception as e:
            logger.error(f"Failed to save file tracking data: {e}")

    def _discover_image_files(self) -> list[Path]:
        """Discover all image files in media directories.

        Returns:
            List of image file paths
        """
        image_files = []

        # Check remote drive
        if self.remote_drive_path.exists():
            for file_path in self.remote_drive_path.iterdir():
                if file_path.is_file() and self._should_compute_complementary_color(
                    file_path
                ):
                    image_files.append(file_path)

        # Check local drive
        if self.local_drive_path.exists():
            for file_path in self.local_drive_path.iterdir():
                if file_path.is_file() and self._should_compute_complementary_color(
                    file_path
                ):
                    image_files.append(file_path)

        return image_files

    def compute_complementary_colors(self) -> None:
        """Compute and cache complementary colors for all images in media directories."""
        logger.info("Starting complementary color computation for all images...")

        # Load existing tracking data
        tracking_data = self._load_tracking_data()

        # Discover all image files
        image_files = self._discover_image_files()
        logger.info(f"Found {len(image_files)} image files to process")

        # Track changes
        updated_count = 0
        total_images = 0

        # Process each image file
        for image_path in image_files:
            total_images += 1

            # Find the tracking entry for this file
            file_id = None
            for fid, file_info in tracking_data.items():
                if file_info.get("path") == str(image_path):
                    file_id = fid
                    break

            # If not in tracking, create a new entry
            if file_id is None:
                file_id = f"local_file_{total_images}"
                tracking_data[file_id] = {
                    "path": str(image_path),
                    "modified_time": "",
                    "size": 0,
                    "local_sync_time": "2025-06-28T00:00:00.000000",
                }

            # Check if we need to compute the color
            existing_color = tracking_data[file_id].get("complementary_color")
            if existing_color and existing_color != "#000000":
                logger.debug(
                    f"Complementary color already exists for {image_path.name}: {existing_color}"
                )
                continue

            # Compute the color
            try:
                complementary_color = self._get_complementary_color(image_path)
                tracking_data[file_id]["complementary_color"] = complementary_color
                updated_count += 1
                logger.info(
                    f"Computed complementary color for {image_path.name}: {complementary_color}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to compute complementary color for {image_path.name}: {e}"
                )
                tracking_data[file_id]["complementary_color"] = "#000000"

        # Save updated tracking data
        if updated_count > 0:
            self._save_tracking_data(tracking_data)
            logger.info(f"Updated {updated_count} files with complementary colors")
        else:
            logger.info("No new complementary colors to compute")

        # Summary
        images_with_colors = sum(
            1
            for file_info in tracking_data.values()
            if file_info.get("complementary_color")
            and file_info.get("complementary_color") != "#000000"
        )
        logger.info(
            f"Summary: {images_with_colors}/{total_images} images have complementary colors"
        )


def compute_all_complementary_colors(media_base_path: str = "media") -> None:
    """Convenience function to compute complementary colors for all images.

    Args:
        media_base_path: Base path for media directories
    """
    service = ComplementaryColorService(media_base_path)
    service.compute_complementary_colors()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Run the service
    compute_all_complementary_colors()
