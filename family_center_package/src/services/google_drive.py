"""
Google Drive service module for handling file operations and synchronization.
"""

import json
import logging
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image

from src.config import Config
from src.services.complementary_color_service import compute_all_complementary_colors
from src.services.download_queue import DownloadQueue, DownloadTask
from src.utils.error_handling import FamilyCenterError

# Register HEIC support for conversion
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_SUPPORT = True
    logging.info("HEIC support enabled for conversion.")
except ImportError:
    HEIC_SUPPORT = False
    logging.warning("pillow-heif not installed. HEIC files will not be converted.")

# Try to import color processing dependencies
COLOR_ANALYSIS = True
try:
    from colorthief import ColorThief
except ImportError:
    COLOR_ANALYSIS = False
    ColorThief = None

logger = logging.getLogger(__name__)


class GoogleDriveError(FamilyCenterError):
    """Base exception for Google Drive related errors."""

    pass


class GoogleDriveFileError(GoogleDriveError):
    """Exception for file-related errors in Google Drive operations."""

    pass


class GoogleDriveAPIError(GoogleDriveError):
    """Exception for Google Drive API errors."""

    pass


class GoogleDriveService:
    """Service class for Google Drive operations."""

    # If modifying these scopes, delete the file token.json.
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, config: Config, service: Any = None) -> None:
        """Initialize the Google Drive service.

        Args:
            config: Application configuration instance
            service: Optional Google Drive API client (for testing/mocking)

        Raises:
            FileNotFoundError: If service account file is not found
            GoogleDriveError: If service initialization fails
        """
        self.config = config
        self.folder_id = config.get("google_drive.shared_folder_id")
        if service is not None:
            self.service = service
        else:
            self._initialize_service()

        # Initialize download queue with config values
        self.download_queue = DownloadQueue(
            max_workers=config.get("google_drive.sync.max_concurrent_downloads", 3),
            max_retries=config.get("google_drive.sync.retry_attempts", 3),
            retry_delay_seconds=config.get("google_drive.sync.retry_delay_seconds", 5),
        )

        # Initialize file tracking
        self.media_path = config.get(
            "google_drive.local_media_path", "media/remote_drive"
        )
        self.tracking_file = os.path.join(self.media_path, ".file_tracking.json")
        self.file_tracking: dict[str, dict[str, Any]] = self._load_file_tracking()

        # Ensure media directory exists
        os.makedirs(self.media_path, exist_ok=True)

    def _initialize_service(self) -> None:
        """Initialize the Google Drive API service using service account.

        Raises:
            FileNotFoundError: If service account file is not found
            GoogleDriveError: If service initialization fails
        """
        service_account_file = self.config.get("google_drive.service_account_file")

        if not os.path.exists(service_account_file):
            raise FileNotFoundError(
                f"Service account file not found: {service_account_file}"
            )

        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=self.SCOPES
            )
            self.service = build("drive", "v3", credentials=credentials)
            logger.info("Google Drive service initialized successfully")
        except Exception as e:
            raise GoogleDriveError(
                f"Failed to initialize Google Drive service: {str(e)}"
            ) from e

    def _load_file_tracking(self) -> dict[str, dict[str, Any]]:
        """Load the file tracking data from disk.

        Returns:
            Dictionary of file tracking data
        """
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file) as f:
                    tracking_data = json.load(f)
                    # Verify all tracked files still exist
                    valid_tracking = {}
                    for file_id, file_info in tracking_data.items():
                        file_path = file_info.get("path")
                        if file_path and os.path.exists(file_path):
                            valid_tracking[file_id] = file_info
                        else:
                            logger.warning(
                                f"Tracked file no longer exists: {file_path}"
                            )
                    return valid_tracking
            except json.JSONDecodeError:
                logger.warning("Failed to parse file tracking data, starting fresh")
                return {}
        return {}

    def _save_file_tracking(self) -> None:
        """Save the file tracking data to disk."""
        # Create a backup of the current tracking file if it exists
        if os.path.exists(self.tracking_file):
            backup_file = f"{self.tracking_file}.bak"
            try:
                shutil.copy2(self.tracking_file, backup_file)
            except OSError as e:
                logger.error(f"Failed to create tracking file backup: {str(e)}")

        # Save the new tracking data
        os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
        with open(self.tracking_file, "w") as f:
            json.dump(self.file_tracking, f, indent=2)

    def _should_download_file(self, file_id: str, modified_time: str) -> bool:
        """Check if a file should be downloaded based on tracking data.

        Args:
            file_id: ID of the file to check
            modified_time: Last modified time of the file

        Returns:
            True if the file should be downloaded, False otherwise
        """
        if file_id not in self.file_tracking:
            return True

        tracked_time = self.file_tracking[file_id].get("modified_time")
        return tracked_time != modified_time

    def _convert_heic_to_jpeg(self, heic_path: Path) -> Path | None:
        """Convert HEIC file to JPEG for better performance.

        Args:
            heic_path: Path to the HEIC file

        Returns:
            Path to the converted JPEG file, or None if conversion failed
        """
        if not HEIC_SUPPORT:
            logger.warning("HEIC support not available, skipping conversion")
            return None

        try:
            # Open HEIC file
            with Image.open(heic_path) as img:
                # Convert to RGB (HEIC might be in other color spaces)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Create JPEG path
                jpeg_path = heic_path.with_suffix(".jpg")

                # Save as JPEG with good quality
                img.save(jpeg_path, "JPEG", quality=95, optimize=True)

                logger.info(f"Converted {heic_path.name} to {jpeg_path.name}")
                return jpeg_path

        except Exception as e:
            logger.error(f"Failed to convert {heic_path.name} to JPEG: {e}")
            return None

    def download_file(self, file_id: str, destination_path: str) -> bool:
        """Download a file from Google Drive.

        Args:
            file_id: The ID of the file to download
            destination_path: The local path where the file should be saved

        Returns:
            bool: True if download was successful, False otherwise

        Raises:
            GoogleDriveError: If API operations fail
        """
        try:
            # Get file metadata
            file = self.service.files().get(fileId=file_id).execute()
            if not file:
                raise GoogleDriveError(f"File not found: {file_id}")

            # Use modifiedTime if available, otherwise use createdTime
            file_time = file.get("modifiedTime", file.get("createdTime", ""))
            if not file_time:
                # If no timestamp is available, use current time as fallback
                logger.warning(
                    f"No timestamp available for file {file_id}, using current time"
                )
                file_time = datetime.now().isoformat() + "Z"

            # Check if we need to download this file
            if not self._should_download_file(file_id, file_time):
                logger.debug(f"Skipping unchanged file: {file['name']}")
                return False

            def download_callback(task: DownloadTask) -> None:
                """Download callback for handling file downloads."""
                temp_path = None
                try:
                    # Download to temporary file
                    request = self.service.files().get_media(fileId=task.file_id)

                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        downloader = MediaIoBaseDownload(temp_file, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                            logger.debug(f"Download {int(status.progress() * 100)}%")
                        temp_path = temp_file.name

                    # Verify the file was downloaded
                    if not temp_path or not os.path.exists(temp_path):
                        raise GoogleDriveError(f"Failed to download file: {file_id}")

                    # Move to final destination
                    os.rename(temp_path, destination_path)

                    # Set the local file's creation and modification time to today
                    # This ensures all synced files are treated as "new" for date-based prioritization
                    current_time = time.time()
                    os.utime(destination_path, (current_time, current_time))

                    # Convert HEIC files to JPEG for better performance
                    if destination_path.lower().endswith(".heic"):
                        heic_path = Path(destination_path)
                        jpeg_path = self._convert_heic_to_jpeg(heic_path)
                        if jpeg_path:
                            # Update tracking to point to the JPEG file instead
                            if task.file_metadata is None:
                                raise GoogleDriveError(
                                    "Missing file metadata for tracking update."
                                )

                            # Compute complementary color for the JPEG file
                            complementary_color = None
                            if self._should_compute_complementary_color(str(jpeg_path)):
                                try:
                                    complementary_color = self._get_complementary_color(
                                        jpeg_path
                                    )
                                    logger.debug(
                                        f"Computed complementary color for {jpeg_path.name}: {complementary_color}"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to compute complementary color for {jpeg_path.name}: {e}"
                                    )

                            self.file_tracking[file_id] = {
                                "path": str(jpeg_path),
                                "modified_time": task.file_metadata.get(
                                    "modifiedTime",
                                    task.file_metadata.get("createdTime", ""),
                                ),
                                "size": task.file_metadata.get("size", 0),
                                "local_sync_time": datetime.now().isoformat(),
                                "original_heic": destination_path,  # Keep reference to original
                                "complementary_color": complementary_color,  # Store computed color
                            }
                            # Remove the original HEIC file to save space
                            try:
                                os.remove(destination_path)
                                logger.info(
                                    f"Removed original HEIC file: {destination_path}"
                                )
                            except OSError as e:
                                logger.warning(
                                    f"Could not remove original HEIC file: {e}"
                                )
                        else:
                            # Keep original tracking if conversion failed
                            if task.file_metadata is None:
                                raise GoogleDriveError(
                                    "Missing file metadata for tracking update."
                                )

                            # Compute complementary color for the original HEIC file
                            complementary_color = None
                            if self._should_compute_complementary_color(
                                destination_path
                            ):
                                try:
                                    complementary_color = self._get_complementary_color(
                                        Path(destination_path)
                                    )
                                    logger.debug(
                                        f"Computed complementary color for {Path(destination_path).name}: {complementary_color}"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to compute complementary color for {Path(destination_path).name}: {e}"
                                    )

                            self.file_tracking[file_id] = {
                                "path": destination_path,
                                "modified_time": task.file_metadata.get(
                                    "modifiedTime",
                                    task.file_metadata.get("createdTime", ""),
                                ),
                                "size": task.file_metadata.get("size", 0),
                                "local_sync_time": datetime.now().isoformat(),
                                "complementary_color": complementary_color,  # Store computed color
                            }
                    else:
                        # Update file tracking with the latest metadata
                        if task.file_metadata is None:
                            raise GoogleDriveError(
                                "Missing file metadata for tracking update."
                            )

                        # Compute complementary color for image files
                        complementary_color = None
                        if self._should_compute_complementary_color(destination_path):
                            try:
                                complementary_color = self._get_complementary_color(
                                    Path(destination_path)
                                )
                                logger.debug(
                                    f"Computed complementary color for {Path(destination_path).name}: {complementary_color}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to compute complementary color for {Path(destination_path).name}: {e}"
                                )

                        self.file_tracking[file_id] = {
                            "path": destination_path,
                            "modified_time": task.file_metadata.get(
                                "modifiedTime",
                                task.file_metadata.get("createdTime", ""),
                            ),
                            "size": task.file_metadata.get("size", 0),
                            "local_sync_time": datetime.now().isoformat(),
                            "complementary_color": complementary_color,  # Store computed color
                        }
                    self._save_file_tracking()

                except Exception as e:
                    logger.error(f"Error downloading file {file_id}: {str(e)}")
                    # Clean up temp file if it exists
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception as cleanup_error:
                            logger.error(
                                f"Error cleaning up temp file: {str(cleanup_error)}"
                            )
                    raise GoogleDriveError(f"Failed to download file: {str(e)}") from e

            def error_callback(task: DownloadTask) -> None:
                """Error callback for handling download failures."""
                logger.error(
                    f"Download failed for file {task.file_id}: {task.last_error}"
                )
                # Clean up any partial downloads
                if os.path.exists(destination_path):
                    try:
                        os.remove(destination_path)
                    except Exception as e:
                        logger.error(f"Failed to clean up partial download: {str(e)}")

            # Add download task to queue
            self.download_queue.add_task(
                file_id=file_id,
                destination_path=destination_path,
                size_bytes=file.get("size", 0),
                created_time=datetime.fromisoformat(
                    file.get("createdTime", file_time).replace("Z", "+00:00")
                ),
                download_callback=download_callback,
                error_callback=error_callback,
                file_metadata=file,  # Pass the file metadata to the task
            )

            return True

        except Exception as e:
            if isinstance(e, GoogleDriveError):
                raise
            raise GoogleDriveError(f"Failed to access file: {str(e)}") from e

    def _get_file_metadata(self, file_id: str) -> dict[str, Any]:
        """Get metadata for a file."""
        try:
            file = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id,name,mimeType,size,createdTime,modifiedTime",
                )
                .execute()
            )
            if not isinstance(file, dict):
                raise GoogleDriveError("File metadata is not a dictionary.")
            return file
        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"File {file_id} not found") from e
            raise

    def _get_folder_contents(self, folder_id: str) -> list[dict[str, Any]]:
        """Get contents of a folder."""
        try:
            results = (
                self.service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    fields="files(id,name,mimeType,size,createdTime,modifiedTime)",
                    pageSize=1000,
                )
                .execute()
            )
            files = results.get("files", [])
            if not isinstance(files, list):
                raise GoogleDriveError("Folder contents are not a list.")
            return files
        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"Folder {folder_id} not found") from e
            raise GoogleDriveError(f"Failed to get folder contents: {str(e)}") from e

    def list_files(self, folder_id: str) -> list[dict[str, Any]]:
        """List files in a folder."""
        try:
            files = self._get_folder_contents(folder_id)
            return [
                {
                    "id": file["id"],
                    "name": file["name"],
                    "mimeType": file["mimeType"],
                    "size": int(file.get("size", 0)),
                    "createdTime": file["createdTime"],
                    "modifiedTime": file.get("modifiedTime", file["createdTime"]),
                }
                for file in files
            ]
        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"Folder {folder_id} not found") from e
            raise GoogleDriveError(f"Failed to list files: {str(e)}") from e

    def _is_supported_file_type(self, filename: str) -> bool:
        """Check if the file type is supported.

        Args:
            filename: Name of the file to check

        Returns:
            True if the file type is supported, False otherwise
        """
        ext = os.path.splitext(filename)[1].lower()
        supported_types = self.config.get(
            "google_drive.file_types.images", []
        ) + self.config.get("google_drive.file_types.videos", [])
        return ext in supported_types

    def verify_folder_access(self) -> None:
        """Verify that the target folder exists and is accessible in Google Drive.

        Raises:
            GoogleDriveAPIError: If API operations fail or folder is not accessible
        """
        try:
            # Try to list files in the folder instead of searching by name
            # This is more reliable for shared drives and folders
            files = self._get_folder_contents(self.folder_id)
            logger.info(
                f"Successfully accessed folder {self.folder_id}, found {len(files)} files"
            )
            return  # Folder exists and is accessible
        except HttpError as e:
            if e.resp.status == 404:
                raise GoogleDriveAPIError(
                    f"Target folder not found: {self.folder_id}"
                ) from e
            raise GoogleDriveAPIError(
                f"Failed to verify folder access: {str(e)}"
            ) from e
        except Exception as e:
            raise GoogleDriveAPIError(
                f"Failed to verify folder access: {str(e)}"
            ) from e

    def _cleanup_removed_files(self, current_file_ids: set[str]) -> None:
        """Remove files that no longer exist in the shared drive.

        Args:
            current_file_ids: Set of file IDs that currently exist in the shared drive
        """
        # Find files in tracking that no longer exist in the drive
        removed_files = set(self.file_tracking.keys()) - current_file_ids

        for file_id in removed_files:
            file_info = self.file_tracking[file_id]
            file_path = file_info.get("path")

            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(
                        f"Removed file that no longer exists in shared drive: {file_path}"
                    )
                except OSError as e:
                    logger.error(f"Failed to remove file {file_path}: {str(e)}")

            # Remove from tracking
            del self.file_tracking[file_id]

        if removed_files:
            self._save_file_tracking()
            logger.info(
                f"Cleaned up {len(removed_files)} files that no longer exist in shared drive"
            )

    def download_folder(self, destination_path: str) -> None:
        """Download all files from the Google Drive folder.

        Args:
            destination_path: The local path where files should be saved

        Raises:
            GoogleDriveError: If API operations fail
        """
        try:
            # Ensure destination directory exists
            os.makedirs(destination_path, exist_ok=True)

            # List all files in the Google Drive folder
            files = self.list_files(self.folder_id)
            logger.info(f"Found {len(files)} files in Google Drive folder")

            # Track current file IDs for cleanup
            current_file_ids = set()

            # Download each file
            for file in files:
                file_id = file["id"]
                current_file_ids.add(file_id)
                file_path = os.path.join(destination_path, file["name"])

                try:
                    # Try the queue-based download first
                    self.download_file(file_id, file_path)
                    logger.info(f"Queued download for: {file['name']}")
                except Exception as e:
                    logger.warning(f"Queue download failed for {file['name']}: {e}")
                    # If queue download fails, try direct download
                    try:
                        logger.info(f"Trying direct download for: {file['name']}")
                        self.download_file_direct(file_id, file_path)
                    except Exception as direct_error:
                        logger.error(
                            f"Direct download also failed for {file['name']}: {direct_error}"
                        )

            # Clean up files that no longer exist in Google Drive
            self._cleanup_removed_files(current_file_ids)

            # Wait for all downloads to complete
            logger.info("Waiting for downloads to complete...")
            self.download_queue.wait_for_completion()
            logger.info("All downloads completed")

        except Exception as e:
            if isinstance(e, GoogleDriveError):
                raise
            raise GoogleDriveError(f"Failed to download folder: {str(e)}") from e

    def stop(self) -> None:
        """Stop the download queue and clean up resources."""
        # Wait for any pending downloads to complete
        try:
            self.download_queue.stop()
        except Exception as e:
            logger.error(f"Error stopping download queue: {str(e)}")
        # Save tracking data
        self._save_file_tracking()

    def download_file_direct(self, file_id: str, destination_path: str) -> bool:
        """Download a file directly without using the queue system.

        This is a simpler approach for files that have SSL issues with the queue.
        """
        try:
            # Get file metadata
            file = self.service.files().get(fileId=file_id).execute()
            if not file:
                raise GoogleDriveError(f"File not found: {file_id}")

            # Use modifiedTime if available, otherwise use createdTime
            file_time = file.get("modifiedTime", file.get("createdTime", ""))
            if not file_time:
                logger.warning(
                    f"No timestamp available for file {file_id}, using current time"
                )
                file_time = datetime.now().isoformat() + "Z"

            # Check if we need to download this file
            if not self._should_download_file(file_id, file_time):
                logger.debug(f"Skipping unchanged file: {file['name']}")
                return False

            # Download directly to destination
            request = self.service.files().get_media(fileId=file_id)

            with open(destination_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logger.debug(f"Download {int(status.progress() * 100)}%")

            # Set the local file's creation and modification time to today
            current_time = time.time()
            os.utime(destination_path, (current_time, current_time))

            # Convert HEIC files to JPEG for better performance
            if destination_path.lower().endswith(".heic"):
                heic_path = Path(destination_path)
                jpeg_path = self._convert_heic_to_jpeg(heic_path)
                if jpeg_path:
                    # Update tracking to point to the JPEG file instead

                    # Compute complementary color for the JPEG file
                    complementary_color = None
                    if self._should_compute_complementary_color(str(jpeg_path)):
                        try:
                            complementary_color = self._get_complementary_color(
                                jpeg_path
                            )
                            logger.debug(
                                f"Computed complementary color for {jpeg_path.name}: {complementary_color}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to compute complementary color for {jpeg_path.name}: {e}"
                            )

                    self.file_tracking[file_id] = {
                        "path": str(jpeg_path),
                        "modified_time": file_time,
                        "size": file.get("size", 0),
                        "local_sync_time": datetime.now().isoformat(),
                        "original_heic": destination_path,  # Keep reference to original
                        "complementary_color": complementary_color,  # Store computed color
                    }
                    # Remove the original HEIC file to save space
                    try:
                        os.remove(destination_path)
                        logger.info(f"Removed original HEIC file: {destination_path}")
                    except OSError as e:
                        logger.warning(f"Could not remove original HEIC file: {e}")
                else:
                    # Keep original tracking if conversion failed

                    # Compute complementary color for the original HEIC file
                    complementary_color = None
                    if self._should_compute_complementary_color(destination_path):
                        try:
                            complementary_color = self._get_complementary_color(
                                Path(destination_path)
                            )
                            logger.debug(
                                f"Computed complementary color for {Path(destination_path).name}: {complementary_color}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to compute complementary color for {Path(destination_path).name}: {e}"
                            )

                    self.file_tracking[file_id] = {
                        "path": destination_path,
                        "modified_time": file_time,
                        "size": file.get("size", 0),
                        "local_sync_time": datetime.now().isoformat(),
                        "complementary_color": complementary_color,  # Store computed color
                    }
            else:
                # Update file tracking

                # Compute complementary color for image files
                complementary_color = None
                if self._should_compute_complementary_color(destination_path):
                    try:
                        complementary_color = self._get_complementary_color(
                            Path(destination_path)
                        )
                        logger.debug(
                            f"Computed complementary color for {Path(destination_path).name}: {complementary_color}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to compute complementary color for {Path(destination_path).name}: {e}"
                        )

                self.file_tracking[file_id] = {
                    "path": destination_path,
                    "modified_time": file_time,
                    "size": file.get("size", 0),
                    "local_sync_time": datetime.now().isoformat(),
                    "complementary_color": complementary_color,  # Store computed color
                }

            self._save_file_tracking()

            logger.info(f"Successfully downloaded: {file['name']}")
            return True

        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            # Clean up partial download
            if os.path.exists(destination_path):
                try:
                    os.remove(destination_path)
                except Exception as cleanup_error:
                    logger.error(
                        f"Error cleaning up partial download: {str(cleanup_error)}"
                    )
            raise GoogleDriveError(f"Failed to download file: {str(e)}") from e

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

            # Method 1: Simple RGB complement (more vibrant)
            r_comp = 255 - r
            g_comp = 255 - g
            b_comp = 255 - b

            # Method 2: HSV-based complement (more sophisticated)
            # Convert RGB to HSV for color wheel calculations
            r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
            max_val = max(r_norm, g_norm, b_norm)
            min_val = min(r_norm, g_norm, b_norm)
            diff = max_val - min_val

            # Calculate hue
            if diff == 0:
                hue = 0
            elif max_val == r_norm:
                hue = (60 * ((g_norm - b_norm) / diff) + 360) % 360
            elif max_val == g_norm:
                hue = (60 * ((b_norm - r_norm) / diff) + 120) % 360
            else:
                hue = (60 * ((r_norm - g_norm) / diff) + 240) % 360

            # Get complementary hue (180 degrees opposite)
            comp_hue = (hue + 180) % 360

            # Calculate saturation and value
            saturation = 0 if max_val == 0 else diff / max_val
            value = max_val

            # Enhanced color generation with better contrast
            # Boost saturation for more vibrant colors
            enhanced_saturation = min(1.0, saturation * 1.5)

            # Adjust value for better visibility (less aggressive reduction)
            # Use a minimum value to ensure colors aren't too dark
            min_value = 0.4  # Minimum brightness
            max_value = 0.9  # Maximum brightness
            enhanced_value = max(min_value, min(max_value, value * 0.8))

            # Convert HSV back to RGB
            c = enhanced_value * enhanced_saturation
            x = c * (1 - abs((comp_hue / 60) % 2 - 1))
            m = enhanced_value - c

            if 0 <= comp_hue < 60:
                r_hsv, g_hsv, b_hsv = c, x, 0
            elif 60 <= comp_hue < 120:
                r_hsv, g_hsv, b_hsv = x, c, 0
            elif 120 <= comp_hue < 180:
                r_hsv, g_hsv, b_hsv = 0, c, x
            elif 180 <= comp_hue < 240:
                r_hsv, g_hsv, b_hsv = 0, x, c
            elif 240 <= comp_hue < 300:
                r_hsv, g_hsv, b_hsv = x, 0, c
            else:
                r_hsv, g_hsv, b_hsv = c, 0, x

            # Convert to 0-255 range
            r_hsv_final = int((r_hsv + m) * 255)
            g_hsv_final = int((g_hsv + m) * 255)
            b_hsv_final = int((b_hsv + m) * 255)

            # Choose the more vibrant option between RGB complement and HSV complement
            # Calculate colorfulness (distance from gray)
            rgb_colorfulness = (
                abs(r_comp - 127.5) + abs(g_comp - 127.5) + abs(b_comp - 127.5)
            )
            hsv_colorfulness = (
                abs(r_hsv_final - 127.5)
                + abs(g_hsv_final - 127.5)
                + abs(b_hsv_final - 127.5)
            )

            if rgb_colorfulness > hsv_colorfulness:
                r_final, g_final, b_final = r_comp, g_comp, b_comp
            else:
                r_final, g_final, b_final = r_hsv_final, g_hsv_final, b_hsv_final

            # Ensure minimum contrast by checking if the color is too close to the original
            # If too similar, boost the contrast
            color_distance = abs(r_final - r) + abs(g_final - g) + abs(b_final - b)
            if color_distance < 200:  # If colors are too similar
                # Boost the complementary color
                r_final = min(255, max(0, r_final + 50))
                g_final = min(255, max(0, g_final + 50))
                b_final = min(255, max(0, b_final + 50))

            # Return as hex color
            return f"#{r_final:02x}{g_final:02x}{b_final:02x}"

        except Exception as e:
            logger.debug(
                f"Could not extract complementary color from {image_path}: {e}"
            )
            return "#000000"  # Default fallback color

    def _is_image_file(self, file_path: str) -> bool:
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
        return Path(file_path).suffix.lower() in image_extensions

    def _should_compute_complementary_color(self, file_path: str) -> bool:
        """Check if we should compute complementary color for this file.

        Args:
            file_path: Path to the file

        Returns:
            True if we should compute complementary color for this file
        """
        # Only compute for remote media files, not calendar images
        path = Path(file_path)

        # Skip calendar images (they're generated programmatically)
        if "calendar" in str(path).lower():
            return False

        # Only compute for image files
        if not self._is_image_file(file_path):
            return False

        # Only compute for remote media files (not local sync files)
        # Remote files are in the media_path directory
        try:
            media_path = Path(self.media_path)
            if media_path in path.parents:
                return True
        except Exception as e:
            logger.debug(f"Error checking media path for {file_path}: {e}")
            return False

        return False

    def sync_files(self) -> None:
        """Sync files from Google Drive to local storage."""
        try:
            logger.info("Starting Google Drive sync...")

            # Get the list of files from Google Drive
            files = self.list_files(self.folder_id)
            logger.info(f"Found {len(files)} files in Google Drive folder")

            # Download each file
            for file in files:
                file_id = file["id"]
                file_name = file["name"]
                file_path = os.path.join(self.media_path, file_name)

                try:
                    logger.info(f"Downloading {file_name}...")
                    self.download_file_direct(file_id, file_path)
                    logger.info(f"Successfully downloaded: {file_name}")
                except Exception as e:
                    logger.error(f"Failed to download {file_name}: {e}")

            # Compute complementary colors for all images after sync
            logger.info("Computing complementary colors for synced images...")
            compute_all_complementary_colors()

            logger.info("Google Drive sync completed.")

        except Exception as e:
            logger.error(f"Google Drive sync failed: {e}")
            raise GoogleDriveError(f"Sync failed: {e}") from e
