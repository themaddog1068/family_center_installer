# Family Center Slideshow Setup Guide

This guide will help you set up and run the Family Center slideshow application.

## Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account with APIs enabled
- Google Drive folder with family media
- Google Calendar (optional)
- Web browser (for configuration)

## Step 1: Install the Application

1. **Clone or download** this repository
2. **Navigate** to the project directory:
   ```bash
   cd family_center_installer
   ```
3. **Run the installer**:
   ```bash
   ./install.sh
   ```

The installer will:
- Check Python version
- Create a virtual environment
- Install all dependencies
- Create necessary directories

## Step 2: Start Web Configuration Interface

**This is the recommended way to configure the application:**

```bash
python start_web_ui.py
```

Then open your web browser to: **http://localhost:8080**

The web interface provides an easy way to:
- Upload Google Drive credentials
- Configure all settings
- Test connections
- Validate configuration

## Step 3: Configure Google APIs

### Google Drive Setup

1. **Create a Google Cloud Project** (if you don't have one)
2. **Enable the Google Drive API**
3. **Create a Service Account**:
   - Go to Google Cloud Console > IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Give it a name like "family-center-drive"
   - Grant "Editor" role
   - Create and download the JSON key file

4. **Share your Google Drive folder**:
   - Open your family media folder in Google Drive
   - Right-click > Share
   - Add the service account email (from the JSON file)
   - Give "Editor" permissions

5. **Upload credentials via web interface**:
   - In the web interface, go to the "Google Drive" tab
   - Click "Choose File" and select your service account JSON
   - Click "Upload Credentials"
   - Test the connection

### Google Calendar Setup (Optional)

1. **Enable the Google Calendar API**
2. **Configure via web interface**:
   - Go to the "Calendar" tab in the web interface
   - Enter your calendar ID
   - Configure sync settings
   - Test the connection

## Step 4: Configure Application Settings

Use the web interface to configure all settings:

### Google Drive Configuration
- **Shared Folder ID**: Enter the ID from your Google Drive folder URL
- **Local Media Path**: Set where files will be downloaded (default: `media/remote_drive`)
- **Sync Interval**: How often to check for new files (default: 30 minutes)
- **Auto Sync on Startup**: Whether to sync when the app starts

### Calendar Configuration
- **Calendar ID**: Your Google Calendar ID
- **Sync Interval**: How often to update calendar events
- **Event Limits**: Maximum events to display
- **Display Options**: Font sizes, colors, layout

### Weather Configuration
- **API Key**: Your OpenWeatherMap API key
- **Location**: City name or coordinates
- **Units**: Metric or Imperial
- **Update Interval**: How often to refresh weather data

### Slideshow Configuration
- **Image Duration**: How long to show each image (seconds)
- **Video Duration**: How long to show each video (seconds)
- **Transition Duration**: Time for transitions between items
- **Display Resolution**: Screen resolution settings
- **Fullscreen Mode**: Enable/disable fullscreen

### Web Content Configuration
- **News Sources**: Add RSS feeds and web content
- **Content Selection**: Choose what to display
- **Scheduling**: Set content rotation schedules

## Step 5: Test and Validate

Use the web interface to test all connections:

1. **Test Google Drive**: Verify folder access and file listing
2. **Test Calendar**: Check calendar access and event retrieval
3. **Test Weather**: Verify weather API connection
4. **Validate Configuration**: Check for any configuration errors

## Step 6: Run the Application

### Quick Start
```bash
./run.sh
```

### Manual Start
```bash
source venv/bin/activate
python src/main.py
```

### Command Line Options

- `--video-only`: Show only video files
- `--pi-sim`: Simulate Raspberry Pi environment
- `--skip-sync`: Skip Google Drive sync
- `--skip-calendar`: Skip calendar sync
- `--skip-weather`: Skip weather sync
- `--web-config`: Start web configuration interface

## Step 7: First Run

On first run, the application will:

1. **Sync media** from Google Drive to `media/remote_drive/`
2. **Generate calendar images** (if enabled) to `media/Calendar/`
3. **Download weather data** (if enabled) to `media/Weather/`
4. **Start the slideshow** in fullscreen mode

## Troubleshooting

### Common Issues

1. **"No module named 'src'"**
   - Make sure you're in the project directory
   - Activate the virtual environment: `source venv/bin/activate`

2. **"Service account file not found"**
   - Use the web interface to upload your credentials
   - Check that the file was uploaded to `credentials/service-account.json`

3. **"Permission denied" on Google Drive**
   - Ensure the service account email has access to your shared folder
   - Check folder sharing settings in Google Drive
   - Test the connection in the web interface

4. **Display issues**
   - Verify resolution settings in the web interface
   - Try running with `--pi-sim` for Raspberry Pi compatibility

5. **Sync problems**
   - Check network connectivity
   - Verify API quotas in Google Cloud Console
   - Test connections using the web interface
   - Check logs in `logs/family_center.log`

6. **Web interface not starting**
   - Check if port 8080 is available
   - Try a different port: `python start_web_ui.py --port 8081`

### Logs

Application logs are stored in:
- `logs/family_center.log` - Main application log
- `logs/` - Other service-specific logs

### Getting Help

1. Use the web interface to test connections and validate settings
2. Check the logs for error messages
3. Test with `--skip-sync` to isolate sync issues
4. Refer to the main Family Center repository for detailed documentation

## Advanced Configuration

### Manual Configuration (Alternative)

If you prefer to edit configuration files directly:

1. **Edit `config/config.yaml`** to modify settings
2. **Restart the application** to apply changes
3. **Use the web interface** to validate configuration

### Custom Display Settings

```yaml
display:
  background_color: '#000000'
  fullscreen: true
  resolution:
    width: 1920
    height: 1080
```

### Slideshow Timing

```yaml
slideshow:
  image_duration: 5
  video_duration: 30
  transition_duration: 1
```

### Sync Intervals

```yaml
google_drive:
  sync_interval_minutes: 30

google_calendar:
  sync_interval_minutes: 60
```

## Next Steps

Once the application is running:

1. **Customize the slideshow** by adjusting timing and display settings
2. **Add more media sources** by configuring additional Google Drive folders
3. **Integrate with smart home** systems for automated startup
4. **Set up as a service** for automatic startup on boot

For more advanced features and customization options, refer to the main Family Center repository documentation.
