# Configuration Module

This module handles the configuration management for the Family Center application.

## Structure

- `config.yaml`: Main configuration file in YAML format
- `config_manager.py`: Configuration manager class for loading and validating config

## Configuration Sections

### Google Drive
- `credentials_path`: Path to Google Drive API credentials
- `token_path`: Path to store OAuth token
- `folder_name`: Name of the Google Drive folder to sync
- `local_media_path`: Local path to store synced media
- `sync_interval_minutes`: How often to sync (in minutes)
- `auto_sync_on_startup`: Whether to sync when app starts

### Slideshow
- `media_directory`: Directory containing media files
- `shuffle_enabled`: Whether to shuffle media
- `slide_duration_seconds`: How long to show each slide
- `supported_image_formats`: List of supported image formats
- `supported_video_formats`: List of supported video formats
- `weighted_media`: Configuration for weighted media selection

### Display
- `resolution`: Screen resolution settings
- `fullscreen`: Whether to run in fullscreen mode
- `background_color`: Background color for display

### Logging
- `level`: Logging level (INFO, DEBUG, etc.)
- `enable_file_logging`: Whether to log to file
- `log_file`: Path to log file
- `max_log_files`: Maximum number of log files to keep
- `max_log_size_mb`: Maximum size of each log file

## Usage

```python
from src.config.config_manager import ConfigManager

# Initialize config manager
config = ConfigManager()

# Get entire section
google_drive_config = config.get('google_drive')

# Get specific value
sync_interval = config.get('google_drive', 'sync_interval_minutes')
```

## Validation

The configuration manager validates:
1. Required sections are present
2. Media directories exist (creates if missing)
3. YAML syntax is valid

## Error Handling

The configuration manager raises:
- `FileNotFoundError`: If config file is missing
- `ValueError`: If YAML is invalid or required sections are missing
- `KeyError`: If requested section or key doesn't exist
