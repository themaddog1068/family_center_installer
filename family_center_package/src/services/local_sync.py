"""
Local folder synchronization service module.
"""

import logging
import os
import shutil
from pathlib import Path

from src.config import Config
from src.utils.error_handling import FamilyCenterError

logger = logging.getLogger(__name__)


class LocalSyncError(FamilyCenterError):
    """Base exception for local sync related errors."""

    pass


class LocalSyncService:
    """Service class for local folder synchronization."""

    def __init__(self, config: Config) -> None:
        """Initialize the local sync service.

        Args:
            config: Application configuration instance
        """
        self.config = config
        self.media_path = config.get("local_media_path", "media")
        self.supported_formats = config.get(
            "supported_formats", ["jpg", "jpeg", "png", "gif", "mp4"]
        )
        self._ensure_media_directory()

    def _ensure_media_directory(self) -> None:
        """Ensure the media directory exists."""
        os.makedirs(self.media_path, exist_ok=True)

    def _is_supported_file_type(self, filename: str) -> bool:
        """Check if the file type is supported.

        Args:
            filename: Name of the file to check

        Returns:
            True if the file type is supported, False otherwise
        """
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        return ext in self.supported_formats

    def sync_folder(self, source_dir: str, dest_dir: str) -> None:
        """Sync files from source directory to destination directory."""
        source_path = Path(source_dir)
        dest_path = Path(dest_dir)

        if not source_path.exists():
            raise LocalSyncError(f"Source directory does not exist: {source_dir}")

        # Ensure destination directory exists
        dest_path.mkdir(parents=True, exist_ok=True)

        # Get list of files in source and destination
        source_files = {
            f.relative_to(source_path): f
            for f in source_path.rglob("*")
            if f.is_file() and self._is_supported_file_type(str(f))
        }
        dest_files = {
            f.relative_to(dest_path): f
            for f in dest_path.rglob("*")
            if f.is_file() and self._is_supported_file_type(str(f))
        }

        # Remove files that don't exist in source
        for rel_path in set(dest_files.keys()) - set(source_files.keys()):
            file_path = dest_files[rel_path]
            try:
                file_path.unlink()
                logger.info(f"Removed {file_path}")
            except OSError as e:
                logger.warning(f"Failed to remove {file_path}: {e}")

        # Copy or update files
        for rel_path, source_file in source_files.items():
            dest_file = dest_path / rel_path
            try:
                # Ensure parent directory exists
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                # Copy if file doesn't exist or is different
                if (
                    not dest_file.exists()
                    or source_file.stat().st_mtime > dest_file.stat().st_mtime
                ):
                    shutil.copy2(source_file, dest_file)
                    logger.info(f"Copied {source_file} to {dest_file}")
            except OSError as e:
                logger.warning(f"Failed to copy {source_file}: {e}")

        logger.info(f"Successfully synced folder {source_dir} to {dest_dir}")

    def get_sync_status(self, source_path: str, dest_path: str) -> dict[str, list[str]]:
        """Get status of files that need to be synced.

        Args:
            source_path: Path to the source folder
            dest_path: Path to the destination folder

        Returns:
            Dictionary with lists of files to be added, updated, or removed

        Raises:
            LocalSyncError: If status check fails
        """
        try:
            source = Path(source_path)
            dest = Path(dest_path)
            if not source.exists() or not dest.exists():
                return {"to_add": [], "to_update": [], "to_remove": []}
            source_files = {
                f.name: f.stat().st_mtime
                for f in source.glob("**/*")
                if f.is_file() and self._is_supported_file_type(str(f))
            }
            dest_files = {
                f.name: f.stat().st_mtime for f in dest.glob("**/*") if f.is_file()
            }
            to_add = [name for name in source_files if name not in dest_files]
            to_update = [
                name
                for name in source_files
                if name in dest_files and source_files[name] > dest_files[name]
            ]
            to_remove = [name for name in dest_files if name not in source_files]
            return {"to_add": to_add, "to_update": to_update, "to_remove": to_remove}

        except Exception as e:
            if isinstance(e, LocalSyncError):
                raise
            raise LocalSyncError(f"Failed to get sync status: {str(e)}") from e
