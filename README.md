# Family Center Slideshow Installer

A streamlined installer for the Family Center slideshow application that displays family media and calendar events.

## Features

- **Media Slideshow**: Displays photos and videos from Google Drive
- **Calendar Integration**: Shows upcoming events from Google Calendar
- **Weather Display**: Current weather information
- **Web Content**: News and other web content
- **Fullscreen Display**: Optimized for digital picture frames
- **Web Configuration Interface**: Easy setup and configuration via web browser

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Web Configuration Interface

**This is the recommended way to set up the application:**

```bash
./setup.sh
```

Or manually:
```bash
python start_web_ui.py
```

Then open your web browser to: **http://localhost:8080**

The web interface will help you:
- Upload Google Drive service account credentials
- Configure Google Drive folder settings
- Set up calendar integration
- Configure weather settings
- Adjust slideshow parameters
- Test connections

### 3. Alternative: Manual Configuration

If you prefer manual setup:

1. Copy your Google service account JSON file to `credentials/service-account.json`
2. Edit `config/config.yaml` to customize settings
3. Run the application: `python src/main.py`

## Web Configuration Interface

The web configuration interface is the easiest way to set up the application. It provides:

### Google Drive Setup
- **Upload Credentials**: Drag and drop your service account JSON file
- **Test Connection**: Verify your Google Drive access
- **Configure Folder**: Set the shared folder ID and sync settings

### Calendar Configuration
- **Calendar ID**: Set your Google Calendar ID
- **Sync Settings**: Configure sync intervals and event limits
- **Display Options**: Customize calendar appearance

### Weather Setup
- **API Key**: Enter your OpenWeatherMap API key
- **Location**: Set your location for weather data
- **Display Options**: Configure weather display settings

### Slideshow Settings
- **Timing**: Adjust image and video display durations
- **Transitions**: Configure transition effects
- **Display**: Set resolution and fullscreen options

### Web Content
- **News Sources**: Add RSS feeds and web content
- **Content Selection**: Choose what content to display
- **Scheduling**: Set content rotation schedules

## Available Scripts

- `./install.sh` - Install dependencies and set up environment
- `./setup.sh` - Start web configuration interface
- `./run.sh` - Run the slideshow application

## Command Line Options

- `--video-only`: Show only video files
- `--pi-sim`: Simulate Raspberry Pi environment
- `--skip-sync`: Skip Google Drive sync
- `--skip-calendar`: Skip calendar sync
- `--skip-weather`: Skip weather sync
- `--web-config`: Start web configuration interface

## Directory Structure

```
family_center_installer/
├── src/                    # Application source code
│   ├── slideshow/         # Slideshow engine
│   ├── services/          # External service integrations
│   ├── core/              # Core application logic
│   ├── config/            # Configuration management
│   └── utils/             # Utility functions
├── config/                # Configuration files
├── credentials/           # API credentials
├── media/                 # Downloaded media files
├── logs/                  # Application logs
├── install.sh            # Installation script
├── setup.sh              # Web configuration setup
├── run.sh                # Run script
├── start_web_ui.py       # Web configuration interface
└── requirements.txt       # Python dependencies
```

## Configuration

The main configuration file is `config/config.yaml`. However, it's recommended to use the web configuration interface for easier setup.

Key configuration sections:
- **google_drive**: Google Drive sync settings
- **google_calendar**: Calendar integration settings
- **display**: Screen resolution and display options
- **slideshow**: Slideshow timing and behavior
- **weather**: Weather service configuration

## Troubleshooting

1. **Missing credentials**: Use the web interface to upload your service account file
2. **Permission errors**: Check file permissions for media and logs directories
3. **Display issues**: Verify display resolution settings in the web interface
4. **Sync problems**: Test connections using the web interface
5. **Web interface not starting**: Check if port 8080 is available

## Support

For issues and questions, please refer to the main Family Center repository documentation.
