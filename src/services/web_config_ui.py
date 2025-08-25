"""
Web Configuration UI for Sprint 6.

This module provides a web interface for configuring web content targets,
including a visual region selector for choosing webpage sections to capture.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_from_directory,
    url_for,
)
from flask_cors import CORS

from src.config.config_manager import ConfigManager
from src.services.web_content_service import WebContentService, WebContentTarget

logger = logging.getLogger(__name__)


class WebConfigUI:
    """Web-based configuration interface for web content targets."""

    def __init__(
        self, config_manager: ConfigManager, web_content_service: WebContentService
    ):
        self.config_manager = config_manager
        self.web_content_service = web_content_service
        self.app = Flask(__name__)
        CORS(self.app)

        # Setup routes
        self._setup_routes()

        logger.info("WebConfigUI initialized")

    def _setup_routes(self) -> None:
        """Setup Flask routes."""

        @self.app.route("/page-selector")
        def page_selector() -> str:
            """Visual page selector interface."""
            return self._render_page_selector()

        @self.app.route("/api/targets", methods=["GET"])
        def get_targets() -> Any:
            """Get all web content targets."""
            targets = []
            for target in self.web_content_service.targets:
                targets.append(
                    {
                        "name": target.name,
                        "url": target.url,
                        "selector": target.selector,
                        "enabled": target.enabled,
                        "weight": target.weight,
                    }
                )
            return jsonify(targets)

        @self.app.route("/api/targets", methods=["POST"])
        def add_target() -> Any:
            """Add a new web content target."""
            data = request.get_json()

            target = WebContentTarget(
                name=data.get("name", "New Target"),
                url=data.get("url", ""),
                selector=data.get("selector", "body"),
                enabled=data.get("enabled", True),
                weight=float(data.get("weight", 1.0)),
            )

            # Add to service
            self.web_content_service.targets.append(target)

            # Save to config
            self._save_targets_to_config()

            return jsonify({"success": True, "message": "Target added successfully"})

        @self.app.route("/api/targets/<name>", methods=["DELETE"])
        def delete_target(name: str) -> Any:
            """Delete a web content target."""
            target = self.web_content_service.get_target_by_name(name)
            if not target:
                return jsonify({"success": False, "message": "Target not found"}), 404

            # Clean up screenshots for this target
            self._cleanup_old_screenshots(target.name)

            # Remove from service
            self.web_content_service.targets.remove(target)

            # Save to config
            self._save_targets_to_config()

            return jsonify({"success": True, "message": "Target deleted successfully"})

        @self.app.route("/api/targets/<name>", methods=["PUT"])
        def update_target(name: str) -> Any:
            """Update an existing web content target."""
            target = self.web_content_service.get_target_by_name(name)
            if not target:
                return jsonify({"success": False, "message": "Target not found"}), 404

            data = request.get_json()
            old_name = target.name
            new_name = data.get("name", target.name)

            # Update target properties
            target.name = new_name
            target.url = data.get("url", target.url)
            target.selector = data.get("selector", target.selector)
            target.enabled = data.get("enabled", target.enabled)
            target.weight = float(data.get("weight", target.weight))

            # Clean up old screenshots if name changed
            if old_name != new_name:
                self._cleanup_old_screenshots(old_name)

            # Save to config
            self._save_targets_to_config()

            return jsonify({"success": True, "message": "Target updated successfully"})

        @self.app.route("/api/preview/<name>", methods=["POST"])
        def preview_target(name: str) -> Any:
            """Capture a quick preview of a target."""
            logger.info(f"Preview request received for target: {name}")

            target = self.web_content_service.get_target_by_name(name)
            if not target:
                logger.error(f"Target not found: {name}")
                return jsonify({"success": False, "message": "Target not found"}), 404

            logger.info(
                f"Found target: {target.name}, URL: {target.url}, Selector: {target.selector}"
            )

            try:
                # Ensure the service is started
                if not self.web_content_service.browser:
                    logger.info("Starting web content service for preview...")
                    asyncio.run(self.web_content_service.start())

                # Use a simple approach without threading
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    logger.info("Capturing screenshot...")
                    result = loop.run_until_complete(
                        self.web_content_service.capture_screenshot(target)
                    )
                    if result:
                        logger.info(f"Preview captured successfully: {result}")
                        return jsonify(
                            {
                                "success": True,
                                "message": "Preview captured successfully",
                                "filename": result.name,
                            }
                        )
                    else:
                        logger.error("Screenshot capture returned None")
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "message": "Failed to capture preview",
                                }
                            ),
                            500,
                        )
                finally:
                    loop.close()

            except Exception as e:
                logger.error(f"Preview capture failed: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/api/preview", methods=["POST"])
        def preview_new_target() -> Any:
            """Capture a preview for a new target configuration."""
            data = request.get_json()

            # Create a temporary target
            temp_target = WebContentTarget(
                name=data.get("name", "Preview"),
                url=data.get("url", ""),
                selector=data.get("selector", "body"),
                enabled=True,
                weight=1.0,
            )

            try:
                # Ensure the service is started
                if not self.web_content_service.browser:
                    asyncio.run(self.web_content_service.start())

                # Use a simple approach without threading
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.web_content_service.capture_screenshot(temp_target)
                    )
                    if result:
                        return jsonify(
                            {
                                "success": True,
                                "message": "Preview captured successfully",
                                "filename": result.name,
                            }
                        )
                    else:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "message": "Failed to capture preview",
                                }
                            ),
                            500,
                        )
                finally:
                    loop.close()

            except Exception as e:
                logger.error(f"Preview capture failed: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/api/screenshots", methods=["GET"])
        def get_screenshots() -> Any:
            """Get list of available screenshots."""
            screenshots = self.web_content_service.get_available_screenshots()
            return jsonify(
                {
                    "screenshots": [
                        {
                            "name": f.name,
                            "path": str(f),
                            "size": f.stat().st_size,
                            "modified": datetime.fromtimestamp(
                                f.stat().st_mtime
                            ).isoformat(),
                        }
                        for f in screenshots
                    ]
                }
            )

        @self.app.route("/screenshots/<path:filename>")
        def serve_screenshot(filename: str) -> Any:
            """Serve screenshot files."""
            logger.info(f"Serving screenshot: {filename}")
            logger.info(f"Output folder: {self.web_content_service.output_folder}")
            logger.info(
                f"Full path: {self.web_content_service.output_folder / filename}"
            )
            logger.info(
                f"File exists: {(self.web_content_service.output_folder / filename).exists()}"
            )

            if not (self.web_content_service.output_folder / filename).exists():
                logger.error(f"Screenshot file not found: {filename}")
                return "File not found", 404

            # Use absolute path to ensure Flask can find the files
            import os

            absolute_path = os.path.abspath(str(self.web_content_service.output_folder))
            logger.info(f"Absolute path: {absolute_path}")

            return send_from_directory(absolute_path, filename)

        @self.app.route("/api/test-browser", methods=["POST"])
        def test_browser() -> Any:
            """Test if the browser is working properly."""
            try:
                # Ensure the service is started
                if not self.web_content_service.browser:
                    asyncio.run(self.web_content_service.start())

                return jsonify(
                    {
                        "success": True,
                        "message": "Browser is ready",
                        "browser_status": "running"
                        if self.web_content_service.browser
                        else "not_started",
                    }
                )
            except Exception as e:
                logger.error(f"Browser test failed: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/api/analyze-page", methods=["POST"])
        def analyze_page() -> Any:
            """Analyze a webpage using different strategies based on site type."""
            data = request.get_json()
            url = data.get("url", "")

            if not url:
                return jsonify({"success": False, "message": "URL is required"}), 400

            try:
                # Use the modular analysis system
                sections = self._analyze_page_modular(url)
                logger.info(
                    f"Modular analysis completed, found {len(sections)} sections"
                )
                return jsonify({"success": True, "sections": sections})

            except Exception as e:
                logger.error(f"Failed to analyze page: {e}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Failed to analyze page: {str(e)}",
                        }
                    ),
                    500,
                )

        @self.app.route("/api/config", methods=["GET"])
        def get_config() -> Any:
            """Get the full configuration as JSON."""
            return jsonify(self.config_manager.to_dict())

        @self.app.route("/api/config", methods=["PUT"])
        def update_config() -> Any:
            """Update the full configuration from JSON."""
            try:
                new_config = request.get_json()
                self.config_manager.set_config(new_config)
                self.config_manager.save_config()
                self.config_manager.reload()  # Ensure reload after save
                return jsonify(
                    {"success": True, "message": "Config updated and reloaded."}
                )
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 400

        @self.app.route("/api/config/validate-weighting", methods=["GET"])
        def validate_weighting() -> Any:
            """Validate the time-based weighting configuration."""
            try:
                from src.services.time_based_weighting import TimeBasedWeightingService

                service = TimeBasedWeightingService(self.config_manager)
                errors = service.validate_configuration()
                return jsonify({"valid": len(errors) == 0, "errors": errors})
            except Exception as e:
                return jsonify({"valid": False, "errors": [str(e)]}), 400

        @self.app.route("/api/google-drive/upload-credentials", methods=["POST"])
        def upload_google_drive_credentials() -> Any:
            """Upload Google Drive service account credentials."""
            try:
                if "credentials" not in request.files:
                    return (
                        jsonify({"success": False, "message": "No file uploaded"}),
                        400,
                    )

                file = request.files["credentials"]
                if file.filename == "":
                    return (
                        jsonify({"success": False, "message": "No file selected"}),
                        400,
                    )

                if not file.filename.endswith(".json"):
                    return (
                        jsonify(
                            {"success": False, "message": "File must be a JSON file"}
                        ),
                        400,
                    )

                # Create credentials directory if it doesn't exist
                import os

                credentials_dir = "credentials"
                os.makedirs(credentials_dir, exist_ok=True)

                # Save the credentials file
                credentials_path = os.path.join(credentials_dir, "service-account.json")
                file.save(credentials_path)

                # Update the config to point to the new credentials file
                config = self.config_manager.to_dict()
                if "google_drive" not in config:
                    config["google_drive"] = {}
                config["google_drive"]["service_account_file"] = credentials_path
                self.config_manager.set_config(config)
                self.config_manager.save_config()

                logger.info(f"Google Drive credentials uploaded to {credentials_path}")
                return jsonify(
                    {
                        "success": True,
                        "message": "Credentials uploaded successfully",
                        "credentials_path": credentials_path,
                    }
                )

            except Exception as e:
                logger.error(f"Failed to upload credentials: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        @self.app.route("/api/google-drive/test-connection", methods=["POST"])
        def test_google_drive_connection() -> Any:
            """Test Google Drive connection with current credentials."""
            try:
                data = request.get_json()
                folder_id = data.get("folder_id", "")

                if not folder_id:
                    return (
                        jsonify({"success": False, "message": "Folder ID is required"}),
                        400,
                    )

                # Import and test Google Drive service
                from src.services.google_drive import GoogleDriveService

                # Use the current config from the config manager
                config = self.config_manager.get_config()
                google_drive_service = GoogleDriveService(config)

                # Test the connection by listing files
                files = google_drive_service.list_files(folder_id)

                logger.info(
                    f"Google Drive connection test successful, found {len(files)} files"
                )
                return jsonify(
                    {
                        "success": True,
                        "message": "Connection successful",
                        "file_count": len(files),
                    }
                )

            except Exception as e:
                logger.error(f"Google Drive connection test failed: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        DASHBOARD_TEMPLATE = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Family Center Config Dashboard</title>
            <style>
                body { font-family: sans-serif; margin: 2em; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 2em; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .section { margin-bottom: 2em; padding: 1em; border: 1px solid #ddd; border-radius: 4px; }
                .section h3 { margin-top: 0; color: #333; border-bottom: 2px solid #007cba; padding-bottom: 0.5em; }
                .form-group { margin-bottom: 1em; }
                .form-group label { display: block; font-weight: bold; margin-bottom: 0.5em; }
                .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 0.5em; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
                .form-row { display: flex; gap: 1em; }
                .form-row .form-group { flex: 1; }
                .btn { padding: 0.5em 1em; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
                .btn-primary { background: #007cba; color: white; }
                .btn-secondary { background: #6c757d; color: white; }
                .btn-danger { background: #dc3545; color: white; }
                .btn-success { background: #28a745; color: white; }
                .list-item { border: 1px solid #ddd; padding: 1em; margin-bottom: 1em; border-radius: 4px; background: #f9f9f9; }
                .list-item .form-row { margin-bottom: 0.5em; }
                .weighting-table { width: 100%; border-collapse: collapse; margin-top: 1em; }
                .weighting-table th, .weighting-table td { border: 1px solid #ddd; padding: 0.5em; text-align: center; }
                .weighting-table th { background: #f8f9fa; font-weight: bold; }
                .success { color: #28a745; background: #d4edda; padding: 0.5em; border-radius: 4px; margin: 1em 0; }
                .error { color: #dc3545; background: #f8d7da; padding: 0.5em; border-radius: 4px; margin: 1em 0; }
                .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 2em; }
                .tab { padding: 1em; cursor: pointer; border: 1px solid transparent; border-bottom: none; }
                .tab.active { background: white; border-color: #ddd; border-radius: 4px 4px 0 0; }
                .tab-content { display: none; }
                .tab-content.active { display: block; }
                .help-text { font-size: 12px; color: #666; margin-top: 0.25em; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Family Center Config Dashboard</h1>
                <div id="message"></div>

                <div class="tabs">
                    <div class="tab active" onclick="showTab('google-drive')">Google Drive</div>
                    <div class="tab" onclick="showTab('local-media')">Local Media</div>
                    <div class="tab" onclick="showTab('calendar')">Calendar</div>
                    <div class="tab" onclick="showTab('weather')">Weather</div>
                    <div class="tab" onclick="showTab('slideshow')">Slideshow</div>
                    <div class="tab" onclick="showTab('web-content')">Web Content</div>
                    <div class="tab" onclick="showTab('weighting')">Time Weighting</div>
                </div>

                <!-- Google Drive Section -->
                <div id="google-drive" class="tab-content active">
                    <div class="section">
                        <h3>Google Drive Configuration</h3>

                        <!-- Credentials Upload Section -->
                        <div class="form-group">
                            <label>Google Drive Service Account Credentials</label>
                            <input type="file" id="google_drive_credentials_file" accept=".json" onchange="handleCredentialsUpload(event)">
                            <div class="help-text">Upload your Google Drive service account JSON credentials file</div>
                            <div id="credentials-status" style="margin-top: 10px;"></div>
                        </div>

                        <div class="form-group">
                            <label>Current Credentials Path</label>
                            <input type="text" id="google_drive_credentials_path" placeholder="credentials/service-account.json" readonly>
                            <div class="help-text">Path to the current credentials file</div>
                        </div>

                        <div class="form-group">
                            <button type="button" class="btn btn-primary" onclick="testGoogleDriveConnection()">Test Google Drive Connection</button>
                            <div id="connection-test-result" style="margin-top: 10px;"></div>
                        </div>

                        <hr style="margin: 20px 0;">

                        <div class="form-group">
                            <label>Shared Folder ID</label>
                            <input type="text" id="google_drive_shared_folder_id" placeholder="Enter Google Drive folder ID">
                            <div class="help-text">The ID of the Google Drive folder to sync</div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Local Media Path</label>
                                <input type="text" id="google_drive_local_media_path" placeholder="media/remote_drive">
                            </div>
                            <div class="form-group">
                                <label>Sync Interval (minutes)</label>
                                <input type="number" id="google_drive_sync_interval_minutes" min="1" max="1440">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Auto Sync on Startup</label>
                            <select id="google_drive_auto_sync_on_startup">
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Local Media Network Access Section -->
                <div id="local-media" class="tab-content">
                    <div class="section">
                        <h3>Local Media Network Access</h3>
                        <div class="form-group">
                            <label>Network Sharing Enabled</label>
                            <select id="local_media_network_enabled">
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                            </select>
                            <div class="help-text">Enable network access to media folders</div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>HTTP Port</label>
                                <input type="number" id="local_media_http_port" min="1024" max="65535" value="8081">
                                <div class="help-text">Port for web-based file browser</div>
                            </div>
                            <div class="form-group">
                                <label>SMB/CIFS Share Name</label>
                                <input type="text" id="local_media_smb_share" placeholder="family_center_media">
                                <div class="help-text">Windows/Mac network share name</div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Media Folders to Share</label>
                            <div id="media-folders-list">
                                <div class="list-item">
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label>Folder Path</label>
                                            <input type="text" value="media/remote_drive" readonly>
                                        </div>
                                        <div class="form-group">
                                            <label>Access URL</label>
                                            <input type="text" value="http://localhost:8081/remote_drive" readonly>
                                        </div>
                                    </div>
                                    <div class="help-text">Google Drive synced media</div>
                                </div>
                                <div class="list-item">
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label>Folder Path</label>
                                            <input type="text" value="media/web_news" readonly>
                                        </div>
                                        <div class="form-group">
                                            <label>Access URL</label>
                                            <input type="text" value="http://localhost:8081/web_news" readonly>
                                        </div>
                                    </div>
                                    <div class="help-text">Web content screenshots</div>
                                </div>
                                <div class="list-item">
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label>Folder Path</label>
                                            <input type="text" value="media/Weather" readonly>
                                        </div>
                                        <div class="form-group">
                                            <label>Access URL</label>
                                            <input type="text" value="http://localhost:8081/Weather" readonly>
                                        </div>
                                    </div>
                                    <div class="help-text">Weather images and forecasts</div>
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Network Access Instructions</label>
                            <div style="background: #f8f9fa; padding: 1em; border-radius: 4px; font-size: 14px;">
                                <p><strong>Web Browser Access:</strong></p>
                                <ul>
                                    <li>From any device on your network: <code>http://[RASPBERRY_PI_IP]:8081</code></li>
                                    <li>Browse folders and download files directly</li>
                                </ul>
                                <p><strong>Windows/Mac Network Share:</strong></p>
                                <ul>
                                    <li>Windows: <code>\\[RASPBERRY_PI_IP]\family_center_media</code></li>
                                    <li>Mac: <code>smb://[RASPBERRY_PI_IP]/family_center_media</code></li>
                                </ul>
                                <p><strong>SSH/SFTP Access:</strong></p>
                                <ul>
                                    <li>SFTP: <code>sftp://[RASPBERRY_PI_IP]/home/pi/family_center/media</code></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Calendar Section -->
                <div id="calendar" class="tab-content">
                    <div class="section">
                        <h3>Calendar Configuration</h3>
                        <div class="form-group">
                            <label>Calendar ID</label>
                            <input type="text" id="google_calendar_calendar_id" placeholder="deckhousefamilycenter@gmail.com">
                        </div>
                        <div class="form-group">
                            <label>iCal URL</label>
                            <input type="text" id="google_calendar_ical_url" placeholder="https://calendar.google.com/calendar/ical/...">
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Timezone</label>
                                <select id="google_calendar_timezone">
                                    <option value="America/New_York">Eastern Time</option>
                                    <option value="America/Chicago">Central Time</option>
                                    <option value="America/Denver">Mountain Time</option>
                                    <option value="America/Los_Angeles">Pacific Time</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Sync Interval (minutes)</label>
                                <input type="number" id="google_calendar_sync_interval_minutes" min="1" max="1440">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Use iCal</label>
                            <select id="google_calendar_use_ical">
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Weather Section -->
                <div id="weather" class="tab-content">
                    <div class="section">
                        <h3>Weather Configuration</h3>
                        <div class="form-group">
                            <label>API Key</label>
                            <input type="text" id="weather_api_key" placeholder="Enter OpenWeatherMap API key">
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>ZIP Code</label>
                                <input type="text" id="weather_zip_code" placeholder="03110">
                            </div>
                            <div class="form-group">
                                <label>Units</label>
                                <select id="weather_units">
                                    <option value="imperial">Fahrenheit</option>
                                    <option value="metric">Celsius</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Sync Interval (minutes)</label>
                                <input type="number" id="weather_sync_interval_minutes" min="1" max="1440">
                            </div>
                            <div class="form-group">
                                <label>Download Radar</label>
                                <select id="weather_download_radar">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Slideshow Section -->
                <div id="slideshow" class="tab-content">
                    <div class="section">
                        <h3>Slideshow Configuration</h3>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Slide Duration (seconds)</label>
                                <input type="number" id="slideshow_slide_duration_seconds" min="1" max="60">
                            </div>
                            <div class="form-group">
                                <label>Shuffle Enabled</label>
                                <select id="slideshow_shuffle_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Transitions Enabled</label>
                                <select id="slideshow_transitions_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Transition Type</label>
                                <select id="slideshow_transition_type">
                                    <option value="crossfade">Crossfade</option>
                                    <option value="fade">Fade</option>
                                    <option value="none">None</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Transition Duration (seconds)</label>
                                <input type="number" id="slideshow_transition_duration" min="0.1" max="5" step="0.1">
                            </div>
                            <div class="form-group">
                                <label>Ease Type</label>
                                <select id="slideshow_ease_type">
                                    <option value="linear">Linear</option>
                                    <option value="ease_in">Ease In</option>
                                    <option value="ease_out">Ease Out</option>
                                    <option value="ease_in_out">Ease In/Out</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Video Playback Enabled</label>
                            <select id="slideshow_video_enabled">
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                            </select>
                        </div>


                    </div>
                </div>

                <!-- Web Content Section -->
                <div id="web-content" class="tab-content">
                    <div class="section">
                        <h3>Web Content Configuration</h3>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Service Enabled</label>
                                <select id="web_content_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                                <div class="help-text">Enable web content screenshot capture</div>
                            </div>
                            <div class="form-group">
                                <label>Auto Sync on Startup</label>
                                <select id="web_content_auto_sync_on_startup">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Sync Interval (minutes)</label>
                                <input type="number" id="web_content_sync_interval_minutes" min="1" max="1440">
                            </div>
                            <div class="form-group">
                                <label>Output Folder</label>
                                <input type="text" id="web_content_output_folder" placeholder="media/web_news">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Image Width</label>
                                <input type="number" id="web_content_image_width" min="800" max="3840">
                            </div>
                            <div class="form-group">
                                <label>Image Height</label>
                                <input type="number" id="web_content_image_height" min="600" max="2160">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Cleanup Old Files</label>
                                <select id="web_content_cleanup_old_files">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Max File Age (hours)</label>
                                <input type="number" id="web_content_max_file_age_hours" min="1" max="168">
                            </div>
                        </div>
                    </div>

                    <div class="section">
                        <h3>Web Content Targets</h3>
                        <div class="help-text">Note: Many targets use specialized parsers and don't rely on CSS selectors. The selector field is only used for basic screenshot capture.</div>
                        <div id="web-content-targets"></div>
                        <button class="btn btn-secondary" onclick="addWebTarget()">Add Target</button>
                    </div>
                </div>

                <!-- Time Weighting Section -->
                <div id="weighting" class="tab-content">
                    <div class="section">
                        <h3>Time-Based Weighting</h3>
                        <div class="form-group">
                            <label>Time Weighting Enabled</label>
                            <select id="weighting_enabled">
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Day of Week Enabled</label>
                            <select id="weighting_day_of_week_enabled">
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                            </select>
                        </div>
                        <div id="weighting-validation" style="margin: 1em 0;"></div>
                        <div id="weighting-table-container">
                            <h4>Current Weighting</h4>
                            <div id="weighting-table"></div>
                        </div>
                    </div>
                </div>

                <div style="margin-top: 2em; text-align: center;">
                    <button class="btn btn-success" onclick="saveConfig()">Save All Changes</button>
                    <button class="btn btn-secondary" onclick="loadConfig()">Reload Config</button>
                </div>
            </div>

            <script>
            let currentConfig = {};

            function showTab(tabName) {
                // Hide all tab contents
                document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));

                // Show selected tab
                document.getElementById(tabName).classList.add('active');
                event.target.classList.add('active');
            }

            function loadConfig() {
                fetch('/api/config').then(r => r.json()).then(cfg => {
                    currentConfig = cfg;
                    populateForm(cfg);
                    renderWeightingTable(cfg);
                    renderWebTargets(cfg);
                });
            }

            function populateForm(cfg) {
                // Google Drive
                if (cfg.google_drive) {
                    document.getElementById('google_drive_shared_folder_id').value = cfg.google_drive.shared_folder_id || '';
                    document.getElementById('google_drive_local_media_path').value = cfg.google_drive.local_media_path || '';
                    document.getElementById('google_drive_sync_interval_minutes').value = cfg.google_drive.sync_interval_minutes || 30;
                    document.getElementById('google_drive_auto_sync_on_startup').value = cfg.google_drive.auto_sync_on_startup || false;
                    document.getElementById('google_drive_credentials_path').value = cfg.google_drive.service_account_file || 'credentials/service-account.json';
                }

                // Calendar
                if (cfg.google_calendar) {
                    document.getElementById('google_calendar_calendar_id').value = cfg.google_calendar.calendar_id || '';
                    document.getElementById('google_calendar_ical_url').value = cfg.google_calendar.ical_url || '';
                    document.getElementById('google_calendar_timezone').value = cfg.google_calendar.timezone || 'America/New_York';
                    document.getElementById('google_calendar_sync_interval_minutes').value = cfg.google_calendar.sync_interval_minutes || 60;
                    document.getElementById('google_calendar_use_ical').value = cfg.google_calendar.use_ical || true;
                }

                // Weather
                if (cfg.weather) {
                    document.getElementById('weather_api_key').value = cfg.weather.api_key || '';
                    document.getElementById('weather_zip_code').value = cfg.weather.zip_code || '';
                    document.getElementById('weather_units').value = cfg.weather.units || 'imperial';
                    document.getElementById('weather_sync_interval_minutes').value = cfg.weather.sync_interval_minutes || 60;
                    document.getElementById('weather_download_radar').value = cfg.weather.download_radar || true;
                }

                // Slideshow
                if (cfg.slideshow) {
                    document.getElementById('slideshow_slide_duration_seconds').value = cfg.slideshow.slide_duration_seconds || 5;
                    document.getElementById('slideshow_shuffle_enabled').value = cfg.slideshow.shuffle_enabled || false;
                    document.getElementById('slideshow_transitions_enabled').value = cfg.slideshow.transitions?.enabled || false;
                    document.getElementById('slideshow_transition_type').value = cfg.slideshow.transitions?.type || 'crossfade';
                    document.getElementById('slideshow_transition_duration').value = cfg.slideshow.transitions?.duration_seconds || 0.3;
                    document.getElementById('slideshow_ease_type').value = cfg.slideshow.transitions?.ease_type || 'linear';
                    document.getElementById('slideshow_video_enabled').value = cfg.slideshow.video_playback?.enabled || false;
                }



                // Weighting
                if (cfg.slideshow?.weighted_media?.time_based_weighting) {
                    document.getElementById('weighting_enabled').value = cfg.slideshow.weighted_media.time_based_weighting.enabled || false;
                    document.getElementById('weighting_day_of_week_enabled').value = cfg.slideshow.weighted_media.time_based_weighting.day_of_week_enabled || false;
                }

                // Web Content
                if (cfg.web_content) {
                    document.getElementById('web_content_enabled').value = cfg.web_content.enabled || false;
                    document.getElementById('web_content_auto_sync_on_startup').value = cfg.web_content.auto_sync_on_startup || false;
                    document.getElementById('web_content_sync_interval_minutes').value = cfg.web_content.sync_interval_minutes || 30;
                    document.getElementById('web_content_output_folder').value = cfg.web_content.output_folder || 'media/web_news';
                    document.getElementById('web_content_image_width').value = cfg.web_content.image_width || 1920;
                    document.getElementById('web_content_image_height').value = cfg.web_content.image_height || 1080;
                    document.getElementById('web_content_cleanup_old_files').value = cfg.web_content.cleanup_old_files || true;
                    document.getElementById('web_content_max_file_age_hours').value = cfg.web_content.max_file_age_hours || 24;
                }
            }

            function renderWebTargets(cfg) {
                const container = document.getElementById('web-content-targets');
                container.innerHTML = '';

                if (cfg.web_content?.targets) {
                    cfg.web_content.targets.forEach((target, index) => {
                        const div = document.createElement('div');
                        div.className = 'list-item';
                        div.innerHTML = `
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Name</label>
                                    <input type="text" value="${target.name}" onchange="updateWebTarget(${index}, 'name', this.value)">
                                </div>
                                <div class="form-group">
                                    <label>URL</label>
                                    <input type="text" value="${target.url}" onchange="updateWebTarget(${index}, 'url', this.value)">
                                </div>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Selector</label>
                                    <input type="text" value="${target.selector}" onchange="updateWebTarget(${index}, 'selector', this.value)">
                                    <div class="help-text">CSS selector for screenshot capture (not used by specialized parsers)</div>
                                </div>
                                <div class="form-group">
                                    <label>Enabled</label>
                                    <select onchange="updateWebTarget(${index}, 'enabled', this.value === 'true')">
                                        <option value="true" ${target.enabled ? 'selected' : ''}>Yes</option>
                                        <option value="false" ${!target.enabled ? 'selected' : ''}>No</option>
                                    </select>
                                </div>
                            </div>
                            <button class="btn btn-danger" onclick="removeWebTarget(${index})">Remove</button>
                        `;
                        container.appendChild(div);
                    });
                }
            }

            function updateWebTarget(index, field, value) {
                if (!currentConfig.web_content) currentConfig.web_content = {};
                if (!currentConfig.web_content.targets) currentConfig.web_content.targets = [];
                if (!currentConfig.web_content.targets[index]) currentConfig.web_content.targets[index] = {};
                currentConfig.web_content.targets[index][field] = value;
            }

            function addWebTarget() {
                if (!currentConfig.web_content) currentConfig.web_content = {};
                if (!currentConfig.web_content.targets) currentConfig.web_content.targets = [];
                currentConfig.web_content.targets.push({
                    name: 'New Target',
                    url: 'https://example.com',
                    selector: 'body',
                    enabled: true
                });
                renderWebTargets(currentConfig);
            }

            function removeWebTarget(index) {
                if (currentConfig.web_content?.targets) {
                    currentConfig.web_content.targets.splice(index, 1);
                    renderWebTargets(currentConfig);
                }
            }

            function renderWeightingTable(cfg) {
                let html = '';
                try {
                    let tbw = cfg.slideshow?.weighted_media?.time_based_weighting;
                    if (tbw?.day_of_week_enabled && tbw.daily_time_ranges) {
                        html += '<table class="weighting-table"><tr><th>Day</th><th>Range</th><th>Media</th><th>Calendar</th><th>Weather</th><th>Web News</th></tr>';
                        let days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
                        for (let d=0; d<7; ++d) {
                            let ranges = tbw.daily_time_ranges[d];
                            for (let r of ranges) {
                                html += `<tr><td>${days[d]}</td><td>${r.name}</td><td>${r.weights.media}</td><td>${r.weights.calendar}</td><td>${r.weights.weather}</td><td>${r.weights.web_news}</td></tr>`;
                            }
                        }
                        html += '</table>';
                    } else if (tbw?.hourly_weights) {
                        html += '<table class="weighting-table"><tr><th>Hour</th><th>Media</th><th>Calendar</th><th>Weather</th><th>Web News</th></tr>';
                        for (let h=0; h<24; ++h) {
                            let w = tbw.hourly_weights[h];
                            html += `<tr><td>${h}</td><td>${w.media}</td><td>${w.calendar}</td><td>${w.weather}</td><td>${w.web_news}</td></tr>`;
                        }
                        html += '</table>';
                    } else {
                        html = '<i>No time-based weighting config found.</i>';
                    }
                } catch (e) {
                    html = '<i>Error rendering weighting table.</i>';
                }
                document.getElementById('weighting-table').innerHTML = html;

                // Validate weighting configuration
                validateWeighting();
            }

            function validateWeighting() {
                fetch('/api/config/validate-weighting').then(r => r.json()).then(result => {
                    const container = document.getElementById('weighting-validation');
                    if (result.valid) {
                        container.innerHTML = '<div class="success">✅ Time weighting configuration is valid!</div>';
                    } else {
                        let errorHtml = '<div class="error"><strong>❌ Time weighting validation errors:</strong><ul>';
                        result.errors.forEach(error => {
                            errorHtml += `<li>${error}</li>`;
                        });
                        errorHtml += '</ul></div>';
                        container.innerHTML = errorHtml;
                    }
                }).catch(err => {
                    document.getElementById('weighting-validation').innerHTML =
                        '<div class="error">❌ Error validating weighting: ' + err + '</div>';
                });
            }

            function saveConfig() {
                // Update currentConfig from form values
                if (!currentConfig.google_drive) currentConfig.google_drive = {};
                if (!currentConfig.google_calendar) currentConfig.google_calendar = {};
                if (!currentConfig.weather) currentConfig.weather = {};
                if (!currentConfig.slideshow) currentConfig.slideshow = {};
                if (!currentConfig.slideshow.transitions) currentConfig.slideshow.transitions = {};
                if (!currentConfig.slideshow.video_playback) currentConfig.slideshow.video_playback = {};
                if (!currentConfig.slideshow.weighted_media) currentConfig.slideshow.weighted_media = {};
                if (!currentConfig.slideshow.weighted_media.time_based_weighting) currentConfig.slideshow.weighted_media.time_based_weighting = {};


                // Google Drive
                currentConfig.google_drive.shared_folder_id = document.getElementById('google_drive_shared_folder_id').value;
                currentConfig.google_drive.local_media_path = document.getElementById('google_drive_local_media_path').value;
                currentConfig.google_drive.sync_interval_minutes = parseInt(document.getElementById('google_drive_sync_interval_minutes').value);
                currentConfig.google_drive.auto_sync_on_startup = document.getElementById('google_drive_auto_sync_on_startup').value === 'true';

                // Calendar
                currentConfig.google_calendar.calendar_id = document.getElementById('google_calendar_calendar_id').value;
                currentConfig.google_calendar.ical_url = document.getElementById('google_calendar_ical_url').value;
                currentConfig.google_calendar.timezone = document.getElementById('google_calendar_timezone').value;
                currentConfig.google_calendar.sync_interval_minutes = parseInt(document.getElementById('google_calendar_sync_interval_minutes').value);
                currentConfig.google_calendar.use_ical = document.getElementById('google_calendar_use_ical').value === 'true';

                // Weather
                currentConfig.weather.api_key = document.getElementById('weather_api_key').value;
                currentConfig.weather.zip_code = document.getElementById('weather_zip_code').value;
                currentConfig.weather.units = document.getElementById('weather_units').value;
                currentConfig.weather.sync_interval_minutes = parseInt(document.getElementById('weather_sync_interval_minutes').value);
                currentConfig.weather.download_radar = document.getElementById('weather_download_radar').value === 'true';

                // Slideshow
                currentConfig.slideshow.slide_duration_seconds = parseInt(document.getElementById('slideshow_slide_duration_seconds').value);
                currentConfig.slideshow.shuffle_enabled = document.getElementById('slideshow_shuffle_enabled').value === 'true';
                currentConfig.slideshow.transitions.enabled = document.getElementById('slideshow_transitions_enabled').value === 'true';
                currentConfig.slideshow.transitions.type = document.getElementById('slideshow_transition_type').value;
                currentConfig.slideshow.transitions.duration_seconds = parseFloat(document.getElementById('slideshow_transition_duration').value);
                currentConfig.slideshow.transitions.ease_type = document.getElementById('slideshow_ease_type').value;
                currentConfig.slideshow.video_playback.enabled = document.getElementById('slideshow_video_enabled').value === 'true';

                // Weighting
                currentConfig.slideshow.weighted_media.time_based_weighting.enabled = document.getElementById('weighting_enabled').value === 'true';
                currentConfig.slideshow.weighted_media.time_based_weighting.day_of_week_enabled = document.getElementById('weighting_day_of_week_enabled').value === 'true';



                // Web Content
                if (!currentConfig.web_content) currentConfig.web_content = {};
                currentConfig.web_content.enabled = document.getElementById('web_content_enabled').value === 'true';
                currentConfig.web_content.auto_sync_on_startup = document.getElementById('web_content_auto_sync_on_startup').value === 'true';
                currentConfig.web_content.sync_interval_minutes = parseInt(document.getElementById('web_content_sync_interval_minutes').value);
                currentConfig.web_content.output_folder = document.getElementById('web_content_output_folder').value;
                currentConfig.web_content.image_width = parseInt(document.getElementById('web_content_image_width').value);
                currentConfig.web_content.image_height = parseInt(document.getElementById('web_content_image_height').value);
                currentConfig.web_content.cleanup_old_files = document.getElementById('web_content_cleanup_old_files').value === 'true';
                currentConfig.web_content.max_file_age_hours = parseInt(document.getElementById('web_content_max_file_age_hours').value);

                // Save to server
                fetch('/api/config', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentConfig)
                }).then(r => r.json()).then(resp => {
                    const msg = document.getElementById('message');
                    if (resp.success) {
                        msg.innerHTML = '<div class="success">Config saved and reloaded successfully!</div>';
                        renderWeightingTable(currentConfig);
                    } else {
                        msg.innerHTML = '<div class="error">Error: ' + resp.message + '</div>';
                    }
                }).catch(err => {
                    document.getElementById('message').innerHTML = '<div class="error">Error: ' + err + '</div>';
                });
            }

            // Google Drive Credentials Functions
            function handleCredentialsUpload(event) {
                const file = event.target.files[0];
                if (!file) return;

                const formData = new FormData();
                formData.append('credentials', file);

                const statusDiv = document.getElementById('credentials-status');
                statusDiv.innerHTML = '<div class="loading">Uploading credentials...</div>';

                fetch('/api/google-drive/upload-credentials', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        statusDiv.innerHTML = '<div class="success">✅ Credentials uploaded successfully!</div>';
                        document.getElementById('google_drive_credentials_path').value = result.credentials_path;
                    } else {
                        statusDiv.innerHTML = '<div class="error">❌ Upload failed: ' + result.message + '</div>';
                    }
                })
                .catch(error => {
                    statusDiv.innerHTML = '<div class="error">❌ Upload error: ' + error.message + '</div>';
                });
            }

            function testGoogleDriveConnection() {
                const resultDiv = document.getElementById('connection-test-result');
                resultDiv.innerHTML = '<div class="loading">Testing Google Drive connection...</div>';

                fetch('/api/google-drive/test-connection', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        folder_id: document.getElementById('google_drive_shared_folder_id').value
                    })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        resultDiv.innerHTML = '<div class="success">✅ Connection successful! Found ' + result.file_count + ' files in the folder.</div>';
                    } else {
                        resultDiv.innerHTML = '<div class="error">❌ Connection failed: ' + result.message + '</div>';
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = '<div class="error">❌ Test error: ' + error.message + '</div>';
                });
            }

            // Load config on page load
            loadConfig();
            </script>
        </body>
        </html>
        """

        @self.app.route("/config")
        def config_dashboard() -> Response:
            return render_template_string(DASHBOARD_TEMPLATE)

        @self.app.route("/")
        def root_redirect() -> Response:
            return redirect(url_for("config_dashboard"))

    def _render_config_page(self) -> str:
        """Render the main configuration page HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Content Configuration</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], input[type="url"], input[type="number"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background-color: #0056b3;
        }
        button.danger {
            background-color: #dc3545;
        }
        button.danger:hover {
            background-color: #c82333;
        }
        .target-list {
            margin-top: 20px;
        }
        .target-item {
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 10px;
            background-color: #f9f9f9;
        }
        .target-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .target-name {
            font-weight: bold;
            font-size: 18px;
        }
        .target-url {
            color: #666;
            font-size: 14px;
        }
        .target-actions {
            display: flex;
            gap: 10px;
        }
        .edit-form {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
            border: 1px solid #dee2e6;
        }
        .edit-form input, .edit-form select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            margin-bottom: 10px;
        }
        .edit-form .form-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        .edit-form .form-row > div {
            flex: 1;
        }
        .preview-container {
            margin-top: 10px;
            text-align: center;
        }
        .preview-image {
            max-width: 100%;
            max-height: 300px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-top: 10px;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .loading-spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .loading-steps {
            text-align: left;
            max-width: 300px;
            margin: 0 auto;
        }
        .loading-step {
            margin: 8px 0;
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #dee2e6;
        }
        .loading-step.active {
            border-left-color: #007bff;
            background-color: #e3f2fd;
        }
        .loading-step.completed {
            border-left-color: #28a745;
            background-color: #d4edda;
        }
        .analyzing-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #007bff;
            color: white;
            padding: 10px 15px;
            border-radius: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            display: none;
        }
        .analyzing-indicator .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff;
            border-top: 2px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }
        .button-group {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }
        .button-small {
            padding: 5px 10px;
            font-size: 12px;
        }
        .status {
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .status.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .selector-help {
            background-color: #e9ecef;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
        }
        .selector-help h3 {
            margin-top: 0;
        }
        .selector-examples {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
        }
        .selector-examples code {
            display: block;
            margin: 5px 0;
            padding: 5px;
            background-color: #e9ecef;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Web Content Configuration</h1>

        <div id="status"></div>

        <!-- Add New Target Section -->
        <div class="section">
            <h2>Add New Web Content Target</h2>

            <div style="margin-bottom: 20px; padding: 15px; background-color: #e3f2fd; border-radius: 4px; border-left: 4px solid #2196f3;">
                <strong>💡 Visual Page Selector:</strong>
                <a href="/page-selector" style="color: #1976d2; text-decoration: none; font-weight: bold;">
                    Click here to visually select webpage sections →
                </a>
                <br>
                <small>Use the visual selector to browse a webpage and click on sections you want to capture automatically.</small>
            </div>

            <form id="addTargetForm">
                <div class="form-group">
                    <label for="targetName">Target Name:</label>
                    <input type="text" id="targetName" name="name" required placeholder="e.g., Movie Theater Now Showing">
                </div>
                <div class="form-group">
                    <label for="targetUrl">URL:</label>
                    <input type="url" id="targetUrl" name="url" required placeholder="https://example.com">
                </div>
                <div class="form-group">
                    <label for="targetSelector">CSS Selector:</label>
                    <input type="text" id="targetSelector" name="selector" placeholder=".main-content, #content, body">
                    <small>Leave empty to capture entire page</small>
                </div>
                <div class="form-group">
                    <label for="targetWeight">Weight (0.1 - 2.0):</label>
                    <input type="number" id="targetWeight" name="weight" min="0.1" max="2.0" step="0.1" value="1.0">
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="targetEnabled" name="enabled" checked>
                        Enabled
                    </label>
                </div>
                <button type="submit">Add Target</button>
            </form>

            <!-- CSS Selector Help -->
            <div class="selector-help">
                <h3>CSS Selector Help</h3>
                <p>Use CSS selectors to target specific parts of a webpage. Here are some common examples:</p>
                <div class="selector-examples">
                    <code>.main-content</code> - Selects elements with class "main-content"
                    <code>#content</code> - Selects element with id "content"
                    <code>.movie-list</code> - Selects elements with class "movie-list"
                    <code>.now-showing</code> - Selects elements with class "now-showing"
                    <code>body</code> - Selects the entire page body
                </div>
                <p><strong>Tip:</strong> Use your browser's developer tools (F12) to inspect elements and find the right selector.</p>
            </div>
        </div>

        <!-- Existing Targets Section -->
        <div class="section">
            <h2>Existing Targets</h2>
            <button onclick="loadTargets()">Refresh Targets</button>
            <div id="targetList" class="target-list">
                <!-- Targets will be loaded here -->
            </div>
        </div>

        <!-- Screenshots Section -->
        <div class="section">
            <h2>Available Screenshots</h2>
            <button onclick="loadScreenshots()">Refresh Screenshots</button>
            <div id="screenshotsList">
                <!-- Screenshots will be loaded here -->
            </div>
        </div>
    </div>

    <script>
        // Load targets on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadTargets();
            loadScreenshots();
            checkForSelectedSections();

            // Add event delegation for buttons
            document.addEventListener('click', function(e) {
                if (e.target.classList.contains('preview-btn')) {
                    const targetName = e.target.getAttribute('data-target');
                    console.log('Preview button clicked via event delegation:', targetName);
                    previewTarget(targetName);
                } else if (e.target.classList.contains('edit-btn')) {
                    const targetName = e.target.getAttribute('data-target');
                    editTarget(targetName);
                } else if (e.target.classList.contains('delete-btn')) {
                    const targetName = e.target.getAttribute('data-target');
                    deleteTarget(targetName);
                }
            });
        });

        // Add target form submission
        document.getElementById('addTargetForm').addEventListener('submit', function(e) {
            e.preventDefault();
            addTarget();
        });

        function showStatus(message, type = 'success') {
            const statusDiv = document.getElementById('status');
            statusDiv.className = `status ${type}`;
            statusDiv.textContent = message;
            setTimeout(() => {
                statusDiv.textContent = '';
                statusDiv.className = '';
            }, 5000);
        }

        async function loadTargets() {
            try {
                const response = await fetch('/api/targets');
                const targets = await response.json();
                displayTargets(targets);
            } catch (error) {
                showStatus('Failed to load targets: ' + error.message, 'error');
            }
        }

        function displayTargets(targets) {
            const targetList = document.getElementById('targetList');
            targetList.innerHTML = '';

            if (targets.length === 0) {
                targetList.innerHTML = '<p>No targets configured yet. Add your first target above!</p>';
                return;
            }

            targets.forEach(target => {
                const targetDiv = document.createElement('div');
                targetDiv.className = 'target-item';
                targetDiv.innerHTML = `
                    <div class="target-header">
                        <div>
                            <div class="target-name">${target.name}</div>
                            <div class="target-url">${target.url}</div>
                        </div>
                        <div class="target-actions">
                            <div class="button-group">
                                <button class="button-small edit-btn" data-target="${target.name}">Edit</button>
                                <button class="button-small preview-btn" data-target="${target.name}">Preview</button>
                                <button class="danger button-small delete-btn" data-target="${target.name}">Delete</button>
                            </div>
                        </div>
                    </div>
                    <div>Selector: <code>${target.selector}</code></div>
                    <div>Weight: ${target.weight} | Enabled: ${target.enabled ? 'Yes' : 'No'}</div>
                    <div id="edit-form-${target.name.replace(/[^a-zA-Z0-9]/g, '_')}" class="edit-form" style="display: none;">
                        <h4>Edit Target</h4>
                        <div class="form-row">
                            <div>
                                <label>Name:</label>
                                <input type="text" id="edit-name-${target.name.replace(/[^a-zA-Z0-9]/g, '_')}" value="${target.name}">
                            </div>
                            <div>
                                <label>Weight:</label>
                                <input type="number" id="edit-weight-${target.name.replace(/[^a-zA-Z0-9]/g, '_')}" value="${target.weight}" min="0.1" max="2.0" step="0.1">
                            </div>
                        </div>
                        <div>
                            <label>URL:</label>
                            <input type="url" id="edit-url-${target.name.replace(/[^a-zA-Z0-9]/g, '_')}" value="${target.url}">
                        </div>
                        <div>
                            <label>Selector:</label>
                            <input type="text" id="edit-selector-${target.name.replace(/[^a-zA-Z0-9]/g, '_')}" value="${target.selector}">
                        </div>
                        <div>
                            <label>
                                <input type="checkbox" id="edit-enabled-${target.name.replace(/[^a-zA-Z0-9]/g, '_')}" ${target.enabled ? 'checked' : ''}>
                                Enabled
                            </label>
                        </div>
                        <div class="button-group">
                            <button onclick="saveTarget('${target.name}')">Save</button>
                            <button onclick="cancelEdit('${target.name}')">Cancel</button>
                            <button onclick="previewEditedTarget('${target.name}')">Preview</button>
                        </div>
                    </div>
                    <div id="preview-${target.name.replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_')}" class="preview-container" style="display: none;">
                        <div class="loading">Capturing preview...</div>
                    </div>
                `;
                targetList.appendChild(targetDiv);
            });
        }

        function editTarget(name) {
            const editForm = document.getElementById(`edit-form-${name.replace(/[^a-zA-Z0-9]/g, '_')}`);
            editForm.style.display = editForm.style.display === 'none' ? 'block' : 'none';
        }

        function cancelEdit(name) {
            const editForm = document.getElementById(`edit-form-${name.replace(/[^a-zA-Z0-9]/g, '_')}`);
            editForm.style.display = 'none';
            loadTargets(); // Reload to reset form values
        }

        async function saveTarget(originalName) {
            const safeName = originalName.replace(/[^a-zA-Z0-9]/g, '_');
            const data = {
                name: document.getElementById(`edit-name-${safeName}`).value,
                url: document.getElementById(`edit-url-${safeName}`).value,
                selector: document.getElementById(`edit-selector-${safeName}`).value,
                weight: parseFloat(document.getElementById(`edit-weight-${safeName}`).value),
                enabled: document.getElementById(`edit-enabled-${safeName}`).checked
            };

            try {
                const response = await fetch(`/api/targets/${encodeURIComponent(originalName)}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (result.success) {
                    showStatus('Target updated successfully');
                    loadTargets();
                } else {
                    showStatus('Failed to update target: ' + result.message, 'error');
                }
            } catch (error) {
                showStatus('Failed to update target: ' + error.message, 'error');
            }
        }

        async function previewTarget(name) {
            console.log('Preview button clicked for:', name);

            // Create a safe ID for the preview container
            const safeId = name.replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_');
            console.log('Safe ID:', safeId);

            const previewContainer = document.getElementById(`preview-${safeId}`);
            console.log('Preview container:', previewContainer);

            if (!previewContainer) {
                console.error('Preview container not found for:', name, 'Safe ID:', safeId);
                // Try to find it by looking at all preview containers
                const allContainers = document.querySelectorAll('[id^="preview-"]');
                console.log('All preview containers:', Array.from(allContainers).map(c => c.id));
                return;
            }

            previewContainer.style.display = 'block';
            previewContainer.innerHTML = '<div class="loading">Capturing preview...</div>';

            try {
                console.log('Sending preview request to:', `/api/preview/${encodeURIComponent(name)}`);
                const response = await fetch(`/api/preview/${encodeURIComponent(name)}`, {
                    method: 'POST'
                });

                console.log('Preview response status:', response.status);
                const result = await response.json();
                console.log('Preview result:', result);

                if (result.success) {
                    previewContainer.innerHTML = `
                        <div>Preview captured successfully!</div>
                        <img src="/screenshots/${result.filename}" alt="Preview" class="preview-image">
                        <div><small>Filename: ${result.filename}</small></div>
                    `;
                } else {
                    previewContainer.innerHTML = `<div class="error">Failed to capture preview: ${result.message}</div>`;
                }
            } catch (error) {
                console.error('Preview error:', error);
                previewContainer.innerHTML = `<div class="error">Failed to capture preview: ${error.message}</div>`;
            }
        }

        async function previewEditedTarget(originalName) {
            const safeName = originalName.replace(/[^a-zA-Z0-9]/g, '_');
            const data = {
                name: document.getElementById(`edit-name-${safeName}`).value,
                url: document.getElementById(`edit-url-${safeName}`).value,
                selector: document.getElementById(`edit-selector-${safeName}`).value,
                weight: parseFloat(document.getElementById(`edit-weight-${safeName}`).value),
                enabled: document.getElementById(`edit-enabled-${safeName}`).checked
            };

            const previewContainer = document.getElementById(`preview-${originalName.replace(/[^a-zA-Z0-9]/g, '_')}`);
            previewContainer.style.display = 'block';
            previewContainer.innerHTML = '<div class="loading">Capturing preview with new settings...</div>';

            try {
                const response = await fetch('/api/preview', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (result.success) {
                    previewContainer.innerHTML = `
                        <div>Preview captured successfully!</div>
                        <img src="/screenshots/${result.filename}" alt="Preview" class="preview-image">
                        <div><small>Filename: ${result.filename}</small></div>
                    `;
                } else {
                    previewContainer.innerHTML = `<div class="error">Failed to capture preview: ${result.message}</div>`;
                }
            } catch (error) {
                previewContainer.innerHTML = `<div class="error">Failed to capture preview: ${error.message}</div>`;
            }
        }

        async function loadScreenshots() {
            try {
                const response = await fetch('/api/screenshots');
                const data = await response.json();
                displayScreenshots(data.screenshots);
            } catch (error) {
                showStatus('Failed to load screenshots: ' + error.message, 'error');
            }
        }

        function displayScreenshots(screenshots) {
            const screenshotsList = document.getElementById('screenshotsList');
            screenshotsList.innerHTML = '';

            if (screenshots.length === 0) {
                screenshotsList.innerHTML = '<p>No screenshots available yet. Add targets and run the sync to capture screenshots.</p>';
                return;
            }

            screenshots.forEach(screenshot => {
                const screenshotDiv = document.createElement('div');
                screenshotDiv.className = 'target-item';
                screenshotDiv.innerHTML = `
                    <div class="target-header">
                        <div>
                            <div class="target-name">${screenshot.name}</div>
                            <div class="target-url">Size: ${(screenshot.size / 1024).toFixed(1)} KB | Modified: ${screenshot.modified}</div>
                        </div>
                    </div>
                    <img src="/screenshots/${screenshot.name}" alt="Screenshot" class="preview-image">
                `;
                screenshotsList.appendChild(screenshotDiv);
            });
        }

        async function addTarget() {
            const formData = new FormData(document.getElementById('addTargetForm'));
            const data = {
                name: formData.get('name'),
                url: formData.get('url'),
                selector: formData.get('selector') || 'body',
                weight: parseFloat(formData.get('weight')),
                enabled: formData.get('enabled') === 'on'
            };

            try {
                const response = await fetch('/api/targets', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (result.success) {
                    showStatus('Target added successfully');
                    document.getElementById('addTargetForm').reset();
                    loadTargets();
                } else {
                    showStatus('Failed to add target: ' + result.message, 'error');
                }
            } catch (error) {
                showStatus('Failed to add target: ' + error.message, 'error');
            }
        }

        async function deleteTarget(name) {
            if (!confirm(`Are you sure you want to delete "${name}"?`)) {
                return;
            }

            try {
                const response = await fetch(`/api/targets/${encodeURIComponent(name)}`, {
                    method: 'DELETE'
                });

                const result = await response.json();
                if (result.success) {
                    showStatus('Target deleted successfully');
                    loadTargets();
                } else {
                    showStatus('Failed to delete target: ' + result.message, 'error');
                }
            } catch (error) {
                showStatus('Failed to delete target: ' + error.message, 'error');
            }
        }

        // Handle selected sections from visual page selector
        async function checkForSelectedSections() {
            const selectedData = sessionStorage.getItem('selectedSections');
            if (selectedData) {
                try {
                    const data = JSON.parse(selectedData);
                    const url = data.url;
                    const sections = data.sections;

                    // Clear the stored data
                    sessionStorage.removeItem('selectedSections');

                    // Show success message
                    showStatus(`Auto-adding ${sections.length} sections from ${url}...`, 'success');

                    // Auto-add all selected sections
                    let addedCount = 0;
                    for (const section of sections) {
                        try {
                            const response = await fetch('/api/targets', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    name: section.name,
                                    url: url,
                                    selector: section.selector,
                                    weight: 1.0,
                                    enabled: true
                                })
                            });

                            const result = await response.json();
                            if (result.success) {
                                addedCount++;
                            } else {
                                console.warn(`Failed to add section "${section.name}": ${result.message}`);
                            }
                        } catch (error) {
                            console.error(`Error adding section "${section.name}":`, error);
                        }
                    }

                    // Reload targets to show the new ones
                    await loadTargets();

                    if (addedCount > 0) {
                        showStatus(`Successfully added ${addedCount} of ${sections.length} sections from ${url}`, 'success');
                    } else {
                        showStatus('Failed to add any sections. Please add them manually.', 'error');
                    }

                } catch (error) {
                    console.error('Error processing selected sections:', error);
                    showStatus('Error processing selected sections: ' + error.message, 'error');
                }
            }
        }

        function displaySections(sections) {
            const container = document.getElementById('sectionsList');

            if (!sections || sections.length === 0) {
                container.innerHTML = '<div class="error">No headers found on this page. Try a different website or check if the page loaded correctly.</div>';
                return;
            }

            container.innerHTML = '<h3>Page Headers & Content Sections (click to select):</h3>';

            sections.forEach((section, index) => {
                const div = document.createElement('div');
                div.className = 'section-item';
                div.onclick = () => toggleSection(index);

                // Create checkbox
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'section-checkbox';
                checkbox.checked = selectedSections.includes(index);
                checkbox.onclick = (e) => {
                    e.stopPropagation(); // Prevent triggering the div click
                    toggleSection(index);
                };

                div.innerHTML = `
                    <div class="section-name">${section.name}</div>
                    <div class="section-header" style="font-size: 12px; color: #007bff; margin: 5px 0;">
                        <strong>Header:</strong> ${section.header}
                    </div>
                    <div class="section-selector">${section.selector}</div>
                    <div class="section-preview">${section.preview || 'No preview available'}</div>
                `;

                div.appendChild(checkbox);
                container.appendChild(div);
            });

            showStatus(`Found ${sections.length} common sections! You can customize the CSS selectors after adding them.`, 'success');
        }

        function toggleSection(index) {
            const checkbox = document.querySelectorAll('.section-checkbox')[index];
            const sectionItem = document.querySelectorAll('.section-item')[index];

            if (selectedSections.includes(index)) {
                selectedSections = selectedSections.filter(i => i !== index);
                sectionItem.classList.remove('selected');
                checkbox.checked = false;
            } else {
                selectedSections.push(index);
                sectionItem.classList.add('selected');
                checkbox.checked = true;
            }

            updateSelectedCount();
        }

        function updateSelectedCount() {
            const count = selectedSections.length;
            const btn = document.getElementById('addSelectedBtn');
            if (count > 0) {
                btn.textContent = `Add ${count} Selected Section${count > 1 ? 's' : ''}`;
                btn.disabled = false;
            } else {
                btn.textContent = 'Add Selected Sections';
                btn.disabled = true;
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }

        function hideError() {
            document.getElementById('errorMessage').style.display = 'none';
        }
    </script>
</body>
</html>
        """

    def _save_targets_to_config(self) -> None:
        """Save targets back to configuration file."""
        try:
            # Get the current config
            config = self.config_manager.to_dict()

            # Convert targets to config format
            targets_config = []
            for target in self.web_content_service.targets:
                targets_config.append(
                    {
                        "name": target.name,
                        "url": target.url,
                        "selector": target.selector,
                        "enabled": target.enabled,
                        "weight": target.weight,
                    }
                )

            # Update config
            if "web_content" not in config:
                config["web_content"] = {}

            config["web_content"]["targets"] = targets_config

            # Save config by writing to file
            import yaml

            with open(self.config_manager.config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)

            logger.info("Web content targets saved to configuration")

        except Exception as e:
            logger.error(f"Failed to save targets to config: {e}")

    def start(self, host: str = "localhost", port: int = 8080) -> None:
        """Start the web configuration interface."""
        logger.info(f"Starting web configuration interface on http://{host}:{port}")
        self.app.run(host=host, port=port, debug=False)

    def stop(self) -> None:
        """Stop the web configuration interface."""
        logger.info("Stopping web configuration interface")

        # Stop the web content service browser
        if self.web_content_service.browser:
            asyncio.run(self.web_content_service.stop())  # type: ignore[unreachable]

    def _cleanup_old_screenshots(self, old_name: str) -> None:
        """Clean up old screenshots when a target is renamed or deleted."""
        try:
            screenshots = self.web_content_service.get_available_screenshots()
            old_name_lower = old_name.lower().replace(" ", "_")

            for screenshot in screenshots:
                screenshot_name_lower = screenshot.name.lower()
                # Check if screenshot belongs to the old target name
                if (
                    old_name_lower in screenshot_name_lower
                    or old_name.lower().replace(" ", "") in screenshot_name_lower
                ):
                    try:
                        screenshot.unlink()
                        logger.info(f"Cleaned up old screenshot: {screenshot.name}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete screenshot {screenshot.name}: {e}"
                        )
        except Exception as e:
            logger.error(f"Error during screenshot cleanup: {e}")

    def _render_page_selector(self) -> str:
        """Render the visual page selector HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visual Page Selector</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .url-input {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            align-items: center;
        }
        .url-input input {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .url-input button {
            padding: 12px 24px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .url-input button:hover {
            background-color: #0056b3;
        }
        .page-viewer {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
            height: 600px;
        }
        .iframe-container {
            border: 2px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }
        .page-iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        .selector-panel {
            border: 2px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            background-color: #f9f9f9;
            overflow-y: auto;
        }
        .section-item {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
        }
        .section-item:hover {
            border-color: #007bff;
            background-color: #f8f9fa;
        }
        .section-item.selected {
            border-color: #28a745;
            background-color: #d4edda;
        }
        .section-item::before {
            content: '';
            position: absolute;
            top: -5px;
            left: -5px;
            width: 20px;
            height: 20px;
            border: 2px solid #007bff;
            border-radius: 50%;
            background: white;
            z-index: 1;
        }
        .section-item.selected::before {
            background: #28a745;
            border-color: #28a745;
        }
        .section-item.selected::after {
            content: '✓';
            position: absolute;
            top: -2px;
            left: 2px;
            color: white;
            font-weight: bold;
            z-index: 2;
        }
        .section-checkbox {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        .section-name {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .section-selector {
            font-family: monospace;
            background: #f8f9fa;
            padding: 5px;
            border-radius: 3px;
            font-size: 12px;
            color: #666;
            margin: 5px 0;
        }
        .section-preview {
            color: #666;
            font-size: 14px;
            line-height: 1.4;
            max-height: 60px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .controls {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }
        .controls button {
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-primary {
            background-color: #28a745;
            color: white;
        }
        .btn-primary:hover {
            background-color: #218838;
        }
        .btn-secondary {
            background-color: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background-color: #5a6268;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .loading-spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .loading-steps {
            text-align: left;
            max-width: 300px;
            margin: 0 auto;
        }
        .loading-step {
            margin: 8px 0;
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #dee2e6;
        }
        .loading-step.active {
            border-left-color: #007bff;
            background-color: #e3f2fd;
        }
        .loading-step.completed {
            border-left-color: #28a745;
            background-color: #d4edda;
        }
        .analyzing-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #007bff;
            color: white;
            padding: 10px 15px;
            border-radius: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            display: none;
        }
        .analyzing-indicator .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff;
            border-top: 2px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }
        .error {
            color: #dc3545;
            padding: 10px;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #007bff;
            text-decoration: none;
        }
        .back-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Back to Configuration</a>
        <h1>Visual Page Selector</h1>
        <p style="color: #666; margin-bottom: 20px;">
            Enter a webpage URL to get content sections optimized for the site type.
            The system will automatically detect the site type and provide relevant sections.
        </p>

        <div class="url-input">
            <input type="url" id="pageUrl" placeholder="Enter webpage URL (e.g., https://redrivertheatres.org)" />
            <button onclick="analyzePage()" id="analyzeBtn">Analyze Page</button>
        </div>

        <div id="strategyInfo" style="display: none; margin: 15px 0; padding: 10px; background-color: #e3f2fd; border-radius: 4px; border-left: 4px solid #2196f3;">
            <strong>🎯 Detected Strategy:</strong> <span id="strategyName"></span>
            <br>
            <small id="strategyDescription"></small>
        </div>

        <div id="manualStrategy" style="margin: 15px 0;">
            <label for="strategySelect"><strong>Or choose strategy manually:</strong></label>
            <select id="strategySelect" onchange="changeStrategy()">
                <option value="auto">Auto-detect (recommended)</option>
                <option value="theater">🎬 Theater/Cinema</option>
                <option value="news">📰 News/Media</option>
                <option value="ecommerce">🛍️ E-commerce</option>
                <option value="generic">📄 Generic</option>
            </select>
        </div>

        <div id="errorMessage" class="error" style="display: none;"></div>

        <!-- Fixed analyzing indicator -->
        <div id="analyzingIndicator" class="analyzing-indicator">
            <span class="spinner"></span>
            Analyzing page...
        </div>

        <div class="page-viewer">
            <div class="iframe-container">
                <iframe id="pageFrame" class="page-iframe" src="about:blank"></iframe>
            </div>

            <div class="selector-panel">
                <div id="loadingMessage" class="loading" style="display: none;">
                    <div class="loading-spinner"></div>
                    <h3>Analyzing Page Structure</h3>
                    <div class="loading-steps">
                        <div class="loading-step" id="step1">
                            <strong>Step 1:</strong> Loading webpage...
                        </div>
                        <div class="loading-step" id="step2">
                            <strong>Step 2:</strong> Detecting content sections...
                        </div>
                        <div class="loading-step" id="step3">
                            <strong>Step 3:</strong> Analyzing page structure...
                        </div>
                        <div class="loading-step" id="step4">
                            <strong>Step 4:</strong> Generating selectors...
                        </div>
                    </div>
                    <p><small>This may take up to 45 seconds for complex websites</small></p>
                </div>

                <div id="sectionsList"></div>

                <div class="controls">
                    <button class="btn-primary" onclick="addSelectedSections()">Add Selected Sections</button>
                    <button class="btn-secondary" onclick="window.location.href='/'">Back to Configuration</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedSections = [];
        let analysisTimeout;

        function analyzePage() {
            const url = document.getElementById('pageUrl').value.trim();
            if (!url) {
                showError('Please enter a URL');
                return;
            }

            // Disable the analyze button
            const analyzeBtn = document.getElementById('analyzeBtn');
            analyzeBtn.disabled = true;
            analyzeBtn.textContent = 'Analyzing...';

            // Load the page in the iframe
            document.getElementById('pageFrame').src = url;

            // Show loading message and start progress
            document.getElementById('loadingMessage').style.display = 'block';
            document.getElementById('sectionsList').innerHTML = '';
            hideError();

            // Show fixed analyzing indicator
            document.getElementById('analyzingIndicator').style.display = 'block';

            // Start progress steps
            startProgressSteps();

            // Set a timeout to show the fixed indicator if analysis takes too long
            analysisTimeout = setTimeout(() => {
                document.getElementById('analyzingIndicator').style.display = 'block';
            }, 5000);

            // Analyze the page
            fetch('/api/analyze-page', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            })
            .then(response => response.json())
            .then(data => {
                clearTimeout(analysisTimeout);
                document.getElementById('loadingMessage').style.display = 'none';
                document.getElementById('analyzingIndicator').style.display = 'none';

                // Re-enable the analyze button
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = 'Analyze Page';

                if (data.success) {
                    displaySections(data.sections);
                } else {
                    showError(data.message || 'Failed to analyze page');
                }
            })
            .catch(error => {
                clearTimeout(analysisTimeout);
                document.getElementById('loadingMessage').style.display = 'none';
                document.getElementById('analyzingIndicator').style.display = 'none';

                // Re-enable the analyze button
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = 'Analyze Page';

                showError('Error analyzing page: ' + error.message);
            });
        }

        function startProgressSteps() {
            const steps = ['step1', 'step2', 'step3', 'step4'];
            let currentStep = 0;

            // Reset all steps
            steps.forEach(stepId => {
                const step = document.getElementById(stepId);
                step.className = 'loading-step';
            });

            // Start with first step
            if (steps[currentStep]) {
                document.getElementById(steps[currentStep]).className = 'loading-step active';
            }

            // Progress through steps
            const stepInterval = setInterval(() => {
                // Mark current step as completed
                if (steps[currentStep]) {
                    document.getElementById(steps[currentStep]).className = 'loading-step completed';
                }

                currentStep++;

                // Activate next step
                if (steps[currentStep]) {
                    document.getElementById(steps[currentStep]).className = 'loading-step active';
                } else {
                    // All steps done, stop the interval
                    clearInterval(stepInterval);
                }
            }, 2000); // Change step every 2 seconds

            // Store interval ID to clear it if needed
            window.progressInterval = stepInterval;
        }

        function displaySections(sections) {
            const container = document.getElementById('sectionsList');

            if (!sections || sections.length === 0) {
                container.innerHTML = '<div class="error">No headers found on this page. Try a different website or check if the page loaded correctly.</div>';
                return;
            }

            container.innerHTML = '<h3>Page Headers & Content Sections (click to select):</h3>';

            sections.forEach((section, index) => {
                const div = document.createElement('div');
                div.className = 'section-item';
                div.onclick = () => toggleSection(index);

                // Create checkbox
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'section-checkbox';
                checkbox.checked = selectedSections.includes(index);
                checkbox.onclick = (e) => {
                    e.stopPropagation(); // Prevent triggering the div click
                    toggleSection(index);
                };

                div.innerHTML = `
                    <div class="section-name">${section.name}</div>
                    <div class="section-header" style="font-size: 12px; color: #007bff; margin: 5px 0;">
                        <strong>Header:</strong> ${section.header}
                    </div>
                    <div class="section-selector">${section.selector}</div>
                    <div class="section-preview">${section.preview || 'No preview available'}</div>
                `;

                div.appendChild(checkbox);
                container.appendChild(div);
            });

            showStatus(`Found ${sections.length} common sections! You can customize the CSS selectors after adding them.`, 'success');
        }

        function toggleSection(index) {
            const checkbox = document.querySelectorAll('.section-checkbox')[index];
            const sectionItem = document.querySelectorAll('.section-item')[index];

            if (selectedSections.includes(index)) {
                selectedSections = selectedSections.filter(i => i !== index);
                sectionItem.classList.remove('selected');
                checkbox.checked = false;
            } else {
                selectedSections.push(index);
                sectionItem.classList.add('selected');
                checkbox.checked = true;
            }

            updateSelectedCount();
        }

        function updateSelectedCount() {
            const count = selectedSections.length;
            const btn = document.getElementById('addSelectedBtn');
            if (count > 0) {
                btn.textContent = `Add ${count} Selected Section${count > 1 ? 's' : ''}`;
                btn.disabled = false;
            } else {
                btn.textContent = 'Add Selected Sections';
                btn.disabled = true;
            }
        }

        function addSelectedSections() {
            if (selectedSections.length === 0) {
                showError('Please select at least one section');
                return;
            }

            // Redirect back to main config with selected sections
            const url = document.getElementById('pageUrl').value;
            const sections = selectedSections.map(index => {
                const item = document.querySelectorAll('.section-item')[index];
                return {
                    name: item.querySelector('.section-name').textContent,
                    selector: item.querySelector('.section-selector').textContent
                };
            });

            // Store in sessionStorage for the main page to use
            sessionStorage.setItem('selectedSections', JSON.stringify({
                url: url,
                sections: sections
            }));

            window.location.href = '/';
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }

        function hideError() {
            document.getElementById('errorMessage').style.display = 'none';
        }

        // Handle Enter key in URL input
        document.getElementById('pageUrl').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                analyzePage();
            }
        });
    </script>
</body>
</html>
        """

    def _analyze_page_modular(self, url: str) -> list[dict[str, str]]:
        """Analyze a webpage using different strategies based on site type."""
        try:
            # First, try to detect the site type
            site_type = self._detect_site_type(url)
            logger.info(f"Detected site type: {site_type}")

            # Use appropriate analysis strategy
            if site_type == "theater":
                return self._get_theater_sections()
            elif site_type == "news":
                return self._get_news_sections()
            elif site_type == "ecommerce":
                return self._get_ecommerce_sections()
            else:
                return self._get_generic_sections()

        except Exception as e:
            logger.error(f"Modular analysis failed: {e}")
            return self._get_generic_sections()

    def _detect_site_type(self, url: str) -> str:
        """Detect the type of website based on URL and domain."""
        url_lower = url.lower()

        # Theater/Cinema detection
        theater_keywords = [
            "theater",
            "theatre",
            "cinema",
            "movie",
            "film",
            "red river",
        ]
        if any(keyword in url_lower for keyword in theater_keywords):
            return "theater"

        # News site detection
        news_keywords = ["news", "times", "post", "tribune", "herald", "journal"]
        if any(keyword in url_lower for keyword in news_keywords):
            return "news"

        # E-commerce detection
        ecommerce_keywords = ["shop", "store", "buy", "amazon", "ebay", "etsy"]
        if any(keyword in url_lower for keyword in ecommerce_keywords):
            return "ecommerce"

        return "generic"

    def _get_theater_sections(self) -> list[dict[str, str]]:
        """Get sections optimized for theater/cinema websites."""
        return [
            {
                "name": "🎬 Now Playing Section",
                "header": "Now Playing",
                "selector": "#content, #primary, .maincontent",
                "preview": "Currently showing movies and their details",
                "tag": "section",
                "index": "0",
                "strategy": "theater",
            },
            {
                "name": "🎬 Coming Soon Section",
                "header": "Coming Up",
                "selector": "#content, #primary, .maincontent",
                "preview": "Upcoming movies and release dates",
                "tag": "section",
                "index": "1",
                "strategy": "theater",
            },
            {
                "name": "🏛️ Main Content Area",
                "header": "Main Content",
                "selector": "main, #content, #primary, .maincontent",
                "preview": "Main page content including movies, shows, and information",
                "tag": "main",
                "index": "2",
                "strategy": "theater",
            },
            {
                "name": "🧭 Navigation Menu",
                "header": "Navigation",
                "selector": "nav, .menu, .main-navigation",
                "preview": "Site navigation and menu items",
                "tag": "nav",
                "index": "3",
                "strategy": "theater",
            },
            {
                "name": "🛍️ Merchandise Section",
                "header": "Merchandise",
                "selector": "#content, #primary, .maincontent",
                "preview": "Theater merchandise and gift items",
                "tag": "section",
                "index": "4",
                "strategy": "theater",
            },
            {
                "name": "📰 News/Updates",
                "header": "News",
                "selector": '.news, .updates, .announcements, [class*="news"]',
                "preview": "Latest news and announcements",
                "tag": "section",
                "index": "5",
                "strategy": "theater",
            },
        ]

    def _get_news_sections(self) -> list[dict[str, str]]:
        """Get sections optimized for news websites."""
        return [
            {
                "name": "📰 Breaking News",
                "header": "Breaking News",
                "selector": '.breaking-news, .urgent, [class*="breaking"]',
                "preview": "Latest breaking news and urgent updates",
                "tag": "section",
                "index": "0",
                "strategy": "news",
            },
            {
                "name": "📰 Main Headlines",
                "header": "Headlines",
                "selector": ".headlines, .main-news, .featured",
                "preview": "Main news headlines and featured stories",
                "tag": "section",
                "index": "1",
                "strategy": "news",
            },
            {
                "name": "📰 Article Content",
                "header": "Articles",
                "selector": "article, .article, .story, .post",
                "preview": "Individual news articles and stories",
                "tag": "article",
                "index": "2",
                "strategy": "news",
            },
            {
                "name": "🧭 Navigation",
                "header": "Navigation",
                "selector": "nav, .menu, .navigation",
                "preview": "Site navigation and menu items",
                "tag": "nav",
                "index": "3",
                "strategy": "news",
            },
            {
                "name": "📰 Sidebar Content",
                "header": "Sidebar",
                "selector": "aside, .sidebar, .widget",
                "preview": "Sidebar content and widgets",
                "tag": "aside",
                "index": "4",
                "strategy": "news",
            },
        ]

    def _get_ecommerce_sections(self) -> list[dict[str, str]]:
        """Get sections optimized for e-commerce websites."""
        return [
            {
                "name": "🛍️ Featured Products",
                "header": "Featured",
                "selector": ".featured, .hero, .banner",
                "preview": "Featured products and promotional content",
                "tag": "section",
                "index": "0",
                "strategy": "ecommerce",
            },
            {
                "name": "🛍️ Product Grid",
                "header": "Products",
                "selector": ".products, .grid, .catalog",
                "preview": "Product listings and catalog",
                "tag": "section",
                "index": "1",
                "strategy": "ecommerce",
            },
            {
                "name": "🛍️ Categories",
                "header": "Categories",
                "selector": ".categories, .departments, .menu",
                "preview": "Product categories and departments",
                "tag": "section",
                "index": "2",
                "strategy": "ecommerce",
            },
            {
                "name": "🧭 Navigation",
                "header": "Navigation",
                "selector": "nav, .menu, .navigation",
                "preview": "Site navigation and menu items",
                "tag": "nav",
                "index": "3",
                "strategy": "ecommerce",
            },
            {
                "name": "📰 News/Updates",
                "header": "News",
                "selector": ".news, .updates, .blog",
                "preview": "Latest news and updates",
                "tag": "section",
                "index": "4",
                "strategy": "ecommerce",
            },
        ]

    def _get_generic_sections(self) -> list[dict[str, str]]:
        """Get generic sections for any website."""
        return [
            {
                "name": "📄 Main Content Area",
                "header": "Main Content",
                "selector": "main, .main, .content, .container",
                "preview": "Main page content and information",
                "tag": "main",
                "index": "0",
                "strategy": "generic",
            },
            {
                "name": "🧭 Navigation Menu",
                "header": "Navigation",
                "selector": "nav, .nav, .menu, .navigation",
                "preview": "Site navigation and menu items",
                "tag": "nav",
                "index": "1",
                "strategy": "generic",
            },
            {
                "name": "📰 News/Updates",
                "header": "News",
                "selector": ".news, .updates, .announcements",
                "preview": "Latest news and announcements",
                "tag": "section",
                "index": "2",
                "strategy": "generic",
            },
            {
                "name": "📋 Sidebar Content",
                "header": "Sidebar",
                "selector": "aside, .sidebar, .widget",
                "preview": "Sidebar content and widgets",
                "tag": "aside",
                "index": "3",
                "strategy": "generic",
            },
            {
                "name": "ℹ️ About/Info",
                "header": "About",
                "selector": ".about, .info, .description",
                "preview": "About section and general information",
                "tag": "section",
                "index": "4",
                "strategy": "generic",
            },
        ]


def create_web_config_ui(
    config_manager: ConfigManager, web_content_service: WebContentService
) -> "WebConfigUI":
    """Create and return a WebConfigUI instance."""
    return WebConfigUI(config_manager, web_content_service)
