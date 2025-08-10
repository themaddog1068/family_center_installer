"""Enhanced Web interface for Family Center with credential management"""

import json
import logging
import os

import yaml
from flask import Flask, jsonify, redirect, render_template_string, request
from werkzeug.utils import secure_filename


class WebInterface:
    def __init__(self, config):
        self.config = config
        self.app = Flask(__name__)
        self.app.secret_key = "family_center_secret_key_2025"
        self.setup_routes()
        self.logger = logging.getLogger(__name__)

        # Ensure credentials directory exists
        os.makedirs("credentials", exist_ok=True)

    def setup_routes(self):
        """Setup Flask routes"""

        @self.app.route("/")
        def index():
            return render_template_string(
                """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Family Center</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .status { background: #e8f5e8; padding: 20px; border-radius: 5px; border-left: 4px solid #4CAF50; }
                    .warning { background: #fff3cd; padding: 20px; border-radius: 5px; border-left: 4px solid #ffc107; }
                    .nav { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .nav a { margin-right: 20px; color: #007bff; text-decoration: none; }
                    .nav a:hover { text-decoration: underline; }
                    h1 { color: #333; }
                    a { color: #007bff; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                    ul, ol { line-height: 1.6; }
                    .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
                    .btn:hover { background: #0056b3; }
                    .btn-success { background: #28a745; }
                    .btn-success:hover { background: #1e7e34; }
                    .btn-warning { background: #ffc107; color: #212529; }
                    .btn-warning:hover { background: #e0a800; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🍓 Family Center - Version -5 (Pre-Alpha)</h1>

                    <div class="nav">
                        <a href="/">🏠 Home</a>
                        <a href="/config">⚙️ Configuration</a>
                        <a href="/credentials">🔑 Credentials</a>
                        <a href="/api/status">🔍 API Status</a>
                    </div>

                    <div class="status">
                        <h2>✅ Installation Successful!</h2>
                        <p>Your Family Center is running and ready for configuration.</p>
                    </div>

                    <div class="warning">
                        <h3>⚠️ Pre-Alpha Notice</h3>
                        <p>This is a pre-alpha release with basic framework functionality. Full features are still in development.</p>
                    </div>

                    <h3>🚀 Quick Setup:</h3>
                    <ol>
                        <li><a href="/credentials">🔑 Configure Google Drive credentials</a></li>
                        <li><a href="/config">⚙️ Set up your preferences</a></li>
                        <li>🎉 Start using your Family Center!</li>
                    </ol>

                    <h3>🛠️ System Information:</h3>
                    <ul>
                        <li><strong>Version:</strong> -5 (Pre-Alpha)</li>
                        <li><strong>Status:</strong> Running</li>
                        <li><strong>Port:</strong> 8080</li>
                        <li><strong>Installation:</strong> Self-contained</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            )

        @self.app.route("/credentials")
        def credentials_page():
            # Get list of existing credential files
            cred_files = []
            if os.path.exists("credentials"):
                for file in os.listdir("credentials"):
                    if file.endswith(".json"):
                        cred_files.append(file)

            return render_template_string(
                """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Family Center - Credentials</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .nav { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .nav a { margin-right: 20px; color: #007bff; text-decoration: none; }
                    .nav a:hover { text-decoration: underline; }
                    .section { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
                    .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
                    .btn:hover { background: #0056b3; }
                    .btn-success { background: #28a745; }
                    .btn-success:hover { background: #1e7e34; }
                    .file-list { background: #e9ecef; padding: 15px; border-radius: 5px; }
                    .file-item { background: white; padding: 10px; margin: 5px 0; border-radius: 3px; }
                    input[type="file"] { margin: 10px 0; }
                    input[type="text"] { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 3px; }
                    .info { background: #d1ecf1; padding: 15px; border-radius: 5px; border-left: 4px solid #bee5eb; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔑 Family Center Credentials</h1>

                    <div class="nav">
                        <a href="/">🏠 Home</a>
                        <a href="/config">⚙️ Configuration</a>
                        <a href="/credentials">🔑 Credentials</a>
                        <a href="/api/status">🔍 API Status</a>
                    </div>

                    <div class="info">
                        <h3>📋 Google Drive Setup Instructions:</h3>
                        <ol>
                            <li>Go to <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a></li>
                            <li>Create a new project or select existing one</li>
                            <li>Enable Google Drive API</li>
                            <li>Create OAuth 2.0 credentials (Desktop application)</li>
                            <li>Download the JSON credentials file</li>
                            <li>Upload it below</li>
                        </ol>
                    </div>

                    <div class="section">
                        <h3>📤 Upload Credential Files</h3>
                        <form action="/upload_credentials" method="post" enctype="multipart/form-data">
                            <label>Google Drive Credentials (JSON file):</label><br>
                            <input type="file" name="credentials_file" accept=".json" required><br>
                            <button type="submit" class="btn btn-success">📤 Upload Credentials</button>
                        </form>
                    </div>

                    <div class="section">
                        <h3>📁 Current Credential Files:</h3>
                        <div class="file-list">
                            {% if cred_files %}
                                {% for file in cred_files %}
                                <div class="file-item">
                                    📄 {{ file }}
                                    <a href="/delete_credential/{{ file }}" class="btn" style="float: right; background: #dc3545;" onclick="return confirm('Delete this file?')">🗑️</a>
                                </div>
                                {% endfor %}
                            {% else %}
                                <p>No credential files found.</p>
                            {% endif %}
                        </div>
                    </div>

                    <div class="section">
                        <h3>⚙️ Configure Google Drive Settings</h3>
                        <form action="/update_config" method="post">
                            <label>Google Drive Folder ID:</label><br>
                            <input type="text" name="folder_id" placeholder="Enter your Google Drive folder ID" value="{{ config.google_drive.folder_id }}"><br>
                            <small>Get this from your Google Drive folder URL</small><br><br>

                            <label>Credentials File:</label><br>
                            <select name="credentials_file">
                                {% for file in cred_files %}
                                <option value="credentials/{{ file }}" {% if config.google_drive.credentials_file == 'credentials/' + file %}selected{% endif %}>{{ file }}</option>
                                {% endfor %}
                            </select><br><br>

                            <button type="submit" class="btn btn-success">💾 Save Configuration</button>
                        </form>
                    </div>

                    <p><a href="/" class="btn">← Back to Home</a></p>
                </div>
            </body>
            </html>
            """,
                cred_files=cred_files,
                config=self.config.config,
            )

        @self.app.route("/upload_credentials", methods=["POST"])
        def upload_credentials():
            if "credentials_file" not in request.files:
                return "No file uploaded", 400

            file = request.files["credentials_file"]
            if file.filename == "":
                return "No file selected", 400

            if file and file.filename.endswith(".json"):
                filename = secure_filename(file.filename)
                filepath = os.path.join("credentials", filename)
                file.save(filepath)

                # Try to validate the JSON
                try:
                    with open(filepath) as f:
                        json.load(f)
                    return redirect("/credentials?success=File uploaded successfully!")
                except json.JSONDecodeError:
                    os.remove(filepath)
                    return "Invalid JSON file", 400

            return "Invalid file type", 400

        @self.app.route("/delete_credential/<filename>")
        def delete_credential(filename):
            filepath = os.path.join("credentials", filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect("/credentials?success=File deleted!")

        @self.app.route("/update_config", methods=["POST"])
        def update_config():
            folder_id = request.form.get("folder_id", "")
            credentials_file = request.form.get("credentials_file", "")

            # Update config
            self.config.config["google_drive"]["folder_id"] = folder_id
            if credentials_file:
                self.config.config["google_drive"][
                    "credentials_file"
                ] = credentials_file

            # Save config
            self.config.save_config()

            return redirect("/credentials?success=Configuration updated!")

        @self.app.route("/config")
        def config_page():
            return render_template_string(
                """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Family Center Configuration</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .nav { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .nav a { margin-right: 20px; color: #007bff; text-decoration: none; }
                    .nav a:hover { text-decoration: underline; }
                    pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; border: 1px solid #e9ecef; }
                    .info { background: #d1ecf1; padding: 15px; border-radius: 5px; border-left: 4px solid #bee5eb; }
                    a { color: #007bff; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⚙️ Family Center Configuration</h1>

                    <div class="nav">
                        <a href="/">🏠 Home</a>
                        <a href="/config">⚙️ Configuration</a>
                        <a href="/credentials">🔑 Credentials</a>
                        <a href="/api/status">🔍 API Status</a>
                    </div>

                    <div class="info">
                        <p><strong>Note:</strong> This is a pre-alpha version. For easier configuration, use the <a href="/credentials">Credentials page</a>.</p>
                    </div>

                    <h3>Current Configuration:</h3>
                    <pre>{{ config | safe }}</pre>

                    <h3>🔧 Manual Configuration:</h3>
                    <p>For advanced users, you can manually edit the configuration file:</p>
                    <pre><code>/home/benjaminhodson/family_center/src/config/config.yaml</code></pre>

                    <h3>📂 Configuration Directories:</h3>
                    <ul>
                        <li><strong>Credentials:</strong> <code>/home/benjaminhodson/family_center/credentials/</code></li>
                        <li><strong>Media:</strong> <code>/home/benjaminhodson/family_center/media/</code></li>
                        <li><strong>Logs:</strong> <code>/home/benjaminhodson/family_center/logs/</code></li>
                    </ul>

                    <p><a href="/" class="btn">← Back to Home</a></p>
                </div>
            </body>
            </html>
            """,
                config=self._format_config(self.config.config),
            )

        @self.app.route("/api/config", methods=["GET"])
        def api_config():
            return jsonify(self.config.config)

        @self.app.route("/api/status")
        def api_status():
            return jsonify(
                {
                    "status": "running",
                    "version": "-5 (Pre-Alpha)",
                    "installation_type": "self-contained",
                    "services": {
                        "web": "active",
                        "photos": "framework-ready",
                        "weather": "framework-ready",
                        "news": "framework-ready",
                        "calendar": "framework-ready",
                    },
                    "endpoints": {
                        "home": "/",
                        "config": "/config",
                        "credentials": "/credentials",
                        "api_status": "/api/status",
                        "api_config": "/api/config",
                    },
                }
            )

    def _format_config(self, config):
        """Format configuration for display"""
        try:
            return yaml.dump(config, default_flow_style=False, indent=2)
        except:
            return str(config)

    def run(self):
        """Run the web interface"""
        host = self.config.get("web.host", "0.0.0.0")
        port = self.config.get("web.port", 8080)
        debug = self.config.get("web.debug", False)

        self.logger.info(f"Starting web interface on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, use_reloader=False)
