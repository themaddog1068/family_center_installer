#!/bin/bash

# Family Center Installer - Version -5 (Pre-Alpha)
# Self-contained installer with embedded application files
# Universal installer for Raspberry Pi 5, 4, and 3B+

set -e

echo "🍓 Family Center Universal Installer - Version -5 (Pre-Alpha)"
echo "============================================================"
echo ""
echo "🎯 This will install Family Center on your Raspberry Pi"
echo "📱 Supports Pi 5, Pi 4, and Pi 3B+"
echo "⏱️  Estimated time: 10-15 minutes"
echo "🔐 No external repository access required"
echo ""

# Detect Pi model
PI_MODEL=$(cat /proc/cpuinfo | grep -E "(Raspberry Pi|BCM)" | head -1 || echo "Unknown")
echo "🔍 Detected: $PI_MODEL"

# Confirm installation
read -p "🚀 Ready to start installation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "👋 Installation cancelled"
    exit 0
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi"
    echo "   Running on: $(uname -a)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if running as pi user
if [ "$USER" != "pi" ]; then
    echo "⚠️  Warning: This script should be run as the 'pi' user"
    echo "   Current user: $USER"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🔧 Starting automated installation..."
echo ""

# Step 1: Update system
echo "📦 Step 1/6: Updating system packages..."
sudo apt update -qq && sudo apt upgrade -y -qq
sudo apt autoremove -y -qq

# Step 2: Install dependencies (optimized for Pi 5, compatible with Pi 4/3B+)
echo "🔧 Step 2/6: Installing system dependencies..."
sudo apt install -y -qq \
    python3-pip \
    python3-venv \
    python3-full \
    git \
    build-essential \
    libopenjp2-7-dev \
    libtiff5-dev \
    libatlas-base-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    python3-pyqt5 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    gfortran \
    libgtk-3-dev \
    libfreetype6-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libx11-dev \
    libxrandr-dev \
    libxcursor-dev \
    libxinerama-dev \
    libxi-dev \
    libxss-dev \
    libasound2-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    ufw

# Step 3: Create Family Center directory structure
echo "📁 Step 3/6: Setting up Family Center application..."
cd /home/$USER

if [ -d "family_center" ]; then
    echo "📁 Found existing Family Center installation"
    echo "🔄 Backing up existing installation..."
    mv family_center family_center_backup_$(date +%Y%m%d_%H%M%S)
fi

mkdir -p family_center
cd family_center

# Create application structure
echo "📂 Creating application structure..."
mkdir -p src/{config,modules,utils}
mkdir -p media/{remote_drive,web_news,weather,local_media}
mkdir -p downloads logs credentials

# Step 4: Create embedded application files
echo "📝 Step 4/6: Creating application files..."

# Create requirements.txt
cat > requirements.txt << 'EOF'
flask==2.3.3
werkzeug==3.1.3
requests==2.31.0
pillow==10.0.1
opencv-python==4.8.1.78
numpy==1.24.3
google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.108.0
pyyaml==6.0.1
python-dotenv==1.0.0
schedule==1.2.0
beautifulsoup4==4.12.2
lxml==4.9.3
feedparser==6.0.10
EOF

# Create main.py
cat > src/main.py << 'EOF'
#!/usr/bin/env python3
"""
Family Center - Digital Photo Frame and Family Dashboard
Version 5.0 - Self-contained installer version
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.web_interface import WebInterface
from modules.photo_manager import PhotoManager
from modules.weather_service import WeatherService
from modules.news_service import NewsService
from modules.calendar_service import CalendarService
from utils.config_manager import ConfigManager

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/family_center.log'),
            logging.StreamHandler()
        ]
    )

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='Family Center Application')
    parser.add_argument('--web-only', action='store_true', help='Run web interface only')
    parser.add_argument('--config', default='src/config/config.yaml', help='Configuration file path')
    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = ConfigManager(args.config)
        
        if args.web_only:
            logger.info("Starting Family Center in web-only mode")
            web_interface = WebInterface(config)
            web_interface.run()
        else:
            logger.info("Starting Family Center full application")
            # Initialize services
            photo_manager = PhotoManager(config)
            weather_service = WeatherService(config)
            news_service = NewsService(config)
            calendar_service = CalendarService(config)
            web_interface = WebInterface(config)
            
            # Start web interface
            web_interface.run()
            
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

# Create config manager
cat > src/utils/config_manager.py << 'EOF'
"""Configuration management for Family Center"""

import yaml
import os
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            return self.get_default_config()
    
    def get_default_config(self):
        """Get default configuration"""
        return {
            'web': {
                'host': '0.0.0.0',
                'port': 8080,
                'debug': False
            },
            'google_drive': {
                'credentials_file': 'credentials/google_drive_credentials.json',
                'token_file': 'credentials/google_drive_token.json',
                'folder_id': ''
            },
            'display': {
                'slideshow_interval': 5,
                'transition_effect': 'fade',
                'fullscreen': True
            },
            'weather': {
                'api_key': '',
                'location': 'London,UK',
                'units': 'metric'
            },
            'news': {
                'sources': ['bbc', 'reuters'],
                'update_interval': 30
            }
        }
    
    def save_config(self):
        """Save configuration to file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def get(self, key, default=None):
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
EOF

# Create enhanced web interface with full configuration management
# Create enhanced web interface with full configuration management
# Create enhanced web interface with full slideshow configuration
cat > src/modules/web_interface.py << 'EOF'
"""Enhanced Web interface for Family Center with full slideshow configuration - Simplified Version"""

import json
import logging
import os
import yaml
from flask import Flask, jsonify, redirect, render_template_string, request
from werkzeug.utils import secure_filename

# Import our simplified services
from config_manager import ConfigManager
from simple_web_content_service import WebContentService, WebContentTarget

class WebInterface:
    def __init__(self, config):
        self.config = config
        self.app = Flask(__name__)
        self.app.secret_key = "family_center_secret_key_2025"
        
        # Initialize simplified services
        self.config_manager = ConfigManager("src/config/config.yaml")
        self.web_content_service = WebContentService()
        
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
                <title>Family Center - Enhanced Configuration</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
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
                    .config-section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    .form-group { margin: 15px 0; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                    .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
                    .tab { padding: 10px 20px; cursor: pointer; border: 1px solid transparent; border-bottom: none; background: #f8f9fa; }
                    .tab.active { background: white; border-color: #ddd; border-bottom: 1px solid white; margin-bottom: -1px; }
                    .tab-content { display: none; }
                    .tab-content.active { display: block; }
                    .credential-file { background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; border: 1px solid #ddd; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🏠 Family Center - Enhanced Configuration</h1>
                    
                    <div class="nav">
                        <a href="/">🏠 Home</a>
                        <a href="/config">⚙️ Full Configuration</a>
                        <a href="/credentials">🔑 Credentials</a>
                        <a href="/api/status">🔍 API Status</a>
                    </div>

                    <div class="status">
                        <h2>✅ Family Center is Running Successfully!</h2>
                        <p>Welcome to the enhanced Family Center configuration interface. This version includes comprehensive slideshow settings, folder configurations, and transition controls.</p>
                    </div>

                    <div class="config-section">
                        <h2>🎯 Quick Access</h2>
                        <ul>
                            <li><a href="/config">⚙️ <strong>Full Configuration Panel</strong> - Slideshow settings, transitions, timing, and more</a></li>
                            <li><a href="/credentials">🔑 Configure Google Drive credentials</a></li>
                            <li><a href="/api/status">🔍 Check system status</a></li>
                        </ul>
                    </div>

                    <div class="config-section">
                        <h2>📁 Credentials Status</h2>
                        <div class="credential-file">
                            <strong>Credentials Directory:</strong> <code>/home/{{ user }}/family_center/credentials/</code>
                        </div>
                        {% if cred_files %}
                            <div class="status">
                                <h3>✅ Found {{ cred_files|length }} credential file(s):</h3>
                                <ul>
                                {% for file in cred_files %}
                                    <li>{{ file }}</li>
                                {% endfor %}
                                </ul>
                            </div>
                        {% else %}
                            <div class="warning">
                                <h3>⚠️ No credential files found</h3>
                                <p>Please add Google Drive credentials to the credentials directory to enable photo synchronization.</p>
                                <a href="/credentials" class="btn">Configure Credentials</a>
                            </div>
                        {% endif %}
                    </div>

                    <div class="config-section">
                        <h2>🎨 What's New in Enhanced Version</h2>
                        <ul>
                            <li><strong>Slideshow Configuration:</strong> Control slide duration, shuffle, and transitions</li>
                            <li><strong>Transition Effects:</strong> Choose from crossfade, slide, zoom, and more</li>
                            <li><strong>Timing Controls:</strong> Set transition duration and easing</li>
                            <li><strong>Video Playback:</strong> Enable/disable video support</li>
                            <li><strong>Time-based Weighting:</strong> Advanced media selection algorithms</li>
                            <li><strong>Folder Management:</strong> Configure multiple media sources</li>
                        </ul>
                    </div>
                </div>

                <script>
                    function showTab(tabName) {
                        // Hide all tab contents
                        var tabContents = document.getElementsByClassName('tab-content');
                        for (var i = 0; i < tabContents.length; i++) {
                            tabContents[i].classList.remove('active');
                        }
                        
                        // Remove active class from all tabs
                        var tabs = document.getElementsByClassName('tab');
                        for (var i = 0; i < tabs.length; i++) {
                            tabs[i].classList.remove('active');
                        }
                        
                        // Show selected tab content and mark tab as active
                        document.getElementById(tabName).classList.add('active');
                        event.target.classList.add('active');
                    }
                </script>
            </body>
            </html>
            """, user=os.getenv('USER', 'unknown'), cred_files=self.get_credential_files())

        @self.app.route("/config")
        def config_page():
            return render_template_string(
                """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Family Center - Full Configuration</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .nav { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .nav a { margin-right: 20px; color: #007bff; text-decoration: none; }
                    .nav a:hover { text-decoration: underline; }
                    .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
                    .tab { padding: 10px 20px; cursor: pointer; border: 1px solid transparent; border-bottom: none; background: #f8f9fa; }
                    .tab.active { background: white; border-color: #ddd; border-bottom: 1px solid white; margin-bottom: -1px; }
                    .tab-content { display: none; padding: 20px; border: 1px solid #ddd; border-top: none; }
                    .tab-content.active { display: block; }
                    .form-group { margin: 15px 0; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                    .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
                    .btn:hover { background: #0056b3; }
                    .btn-success { background: #28a745; }
                    .btn-success:hover { background: #1e7e34; }
                    .status { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0; }
                    .error { background: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0; }
                    .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    h1, h2, h3 { color: #333; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⚙️ Family Center - Full Configuration</h1>
                    
                    <div class="nav">
                        <a href="/">🏠 Home</a>
                        <a href="/config">⚙️ Full Configuration</a>
                        <a href="/credentials">🔑 Credentials</a>
                        <a href="/api/status">🔍 API Status</a>
                    </div>

                    <div class="tabs">
                        <div class="tab active" onclick="showTab('slideshow')">🎨 Slideshow</div>
                        <div class="tab" onclick="showTab('folders')">📁 Folders</div>
                        <div class="tab" onclick="showTab('credentials')">🔑 Credentials</div>
                        <div class="tab" onclick="showTab('system')">⚙️ System</div>
                    </div>

                    <!-- Slideshow Section -->
                    <div id="slideshow" class="tab-content active">
                        <h2>🎨 Slideshow Configuration</h2>
                        
                        <div class="section">
                            <h3>⏱️ Timing Settings</h3>
                            <div class="form-group">
                                <label>Slide Duration (seconds)</label>
                                <input type="number" id="slideshow_slide_duration_seconds" min="1" max="60" value="5">
                                <small>How long each slide is displayed</small>
                            </div>
                        </div>

                        <div class="section">
                            <h3>🔄 Playback Options</h3>
                            <div class="form-group">
                                <label>Shuffle Enabled</label>
                                <select id="slideshow_shuffle_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                                <small>Randomize the order of slides</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Video Playback Enabled</label>
                                <select id="slideshow_video_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                                <small>Include video files in slideshow</small>
                            </div>
                        </div>

                        <div class="section">
                            <h3>✨ Transition Effects</h3>
                            <div class="form-group">
                                <label>Transitions Enabled</label>
                                <select id="slideshow_transitions_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                                <small>Enable smooth transitions between slides</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Transition Type</label>
                                <select id="slideshow_transition_type">
                                    <option value="crossfade">Crossfade</option>
                                    <option value="slide">Slide</option>
                                    <option value="zoom">Zoom</option>
                                    <option value="fade">Fade</option>
                                    <option value="none">None</option>
                                </select>
                                <small>Visual effect for transitions</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Transition Duration (seconds)</label>
                                <input type="number" id="slideshow_transition_duration" min="0.1" max="5" step="0.1" value="0.3">
                                <small>How long transitions take</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Ease Type</label>
                                <select id="slideshow_ease_type">
                                    <option value="linear">Linear</option>
                                    <option value="ease-in">Ease In</option>
                                    <option value="ease-out">Ease Out</option>
                                    <option value="ease-in-out">Ease In Out</option>
                                </select>
                                <small>Animation easing function</small>
                            </div>
                        </div>

                        <div class="section">
                            <h3>⚖️ Advanced Weighting</h3>
                            <div class="form-group">
                                <label>Time-based Weighting Enabled</label>
                                <select id="weighting_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                                <small>Weight media based on time of day</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Day of Week Weighting</label>
                                <select id="weighting_day_of_week_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                                <small>Weight media based on day of week</small>
                            </div>
                        </div>

                        <button class="btn btn-success" onclick="saveConfig()">💾 Save Slideshow Settings</button>
                    </div>

                    <!-- Folders Section -->
                    <div id="folders" class="tab-content">
                        <h2>📁 Folder Configuration</h2>
                        
                        <div class="section">
                            <h3>📂 Media Folders</h3>
                            <div class="form-group">
                                <label>Google Drive Folder ID</label>
                                <input type="text" id="google_drive_folder_id" placeholder="Enter your Google Drive folder ID">
                                <small>Get this from your Google Drive folder URL</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Local Media Path</label>
                                <input type="text" id="local_media_path" value="/home/{{ user }}/family_center/media">
                                <small>Local directory for media files</small>
                            </div>
                        </div>

                        <div class="section">
                            <h3>🔄 Sync Settings</h3>
                            <div class="form-group">
                                <label>Auto Sync Enabled</label>
                                <select id="auto_sync_enabled">
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                                <small>Automatically sync from Google Drive</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Sync Interval (minutes)</label>
                                <input type="number" id="sync_interval" min="1" max="1440" value="30">
                                <small>How often to check for new files</small>
                            </div>
                        </div>

                        <button class="btn btn-success" onclick="saveConfig()">💾 Save Folder Settings</button>
                    </div>

                    <!-- Credentials Section -->
                    <div id="credentials" class="tab-content">
                        <h2>🔑 Credentials Management</h2>
                        
                        <div class="section">
                            <h3>📁 Current Credentials</h3>
                            <div id="credentials-list">
                                {% if cred_files %}
                                    <div class="status">
                                        <h4>✅ Found {{ cred_files|length }} credential file(s):</h4>
                                        <ul>
                                        {% for file in cred_files %}
                                            <li>{{ file }}</li>
                                        {% endfor %}
                                        </ul>
                                    </div>
                                {% else %}
                                    <div class="error">
                                        <h4>⚠️ No credential files found</h4>
                                        <p>Please add Google Drive credentials to: <code>/home/{{ user }}/family_center/credentials/</code></p>
                                    </div>
                                {% endif %}
                            </div>
                        </div>

                        <div class="section">
                            <h3>📤 Upload New Credentials</h3>
                            <form action="/upload_credentials" method="post" enctype="multipart/form-data">
                                <div class="form-group">
                                    <label>Select Credential File</label>
                                    <input type="file" name="credentials" accept=".json">
                                    <small>Upload your Google Drive service account JSON file</small>
                                </div>
                                <button type="submit" class="btn btn-success">📤 Upload Credentials</button>
                            </form>
                        </div>

                        <div class="section">
                            <h3>ℹ️ How to Get Credentials</h3>
                            <ol>
                                <li>Go to <a href="https://console.cloud.google.com" target="_blank">Google Cloud Console</a></li>
                                <li>Create a new project or select existing one</li>
                                <li>Enable Google Drive API</li>
                                <li>Create a Service Account</li>
                                <li>Download the JSON key file</li>
                                <li>Upload it here or place it in the credentials directory</li>
                            </ol>
                        </div>
                    </div>

                    <!-- System Section -->
                    <div id="system" class="tab-content">
                        <h2>⚙️ System Configuration</h2>
                        
                        <div class="section">
                            <h3>🌐 Web Interface</h3>
                            <div class="form-group">
                                <label>Host</label>
                                <input type="text" id="web_host" value="0.0.0.0">
                                <small>Web interface host address</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Port</label>
                                <input type="number" id="web_port" min="1" max="65535" value="8080">
                                <small>Web interface port</small>
                            </div>
                            
                            <div class="form-group">
                                <label>Debug Mode</label>
                                <select id="web_debug">
                                    <option value="false">No</option>
                                    <option value="true">Yes</option>
                                </select>
                                <small>Enable debug mode for development</small>
                            </div>
                        </div>

                        <div class="section">
                            <h3>📊 Current Configuration</h3>
                            <pre id="current-config">{{ config_dump }}</pre>
                        </div>

                        <button class="btn btn-success" onclick="saveConfig()">💾 Save System Settings</button>
                        <button class="btn" onclick="loadConfig()">🔄 Reload Configuration</button>
                    </div>

                    <div id="save-status"></div>
                </div>

                <script>
                    // Load current configuration
                    function loadConfig() {
                        fetch('/api/config')
                            .then(response => response.json())
                            .then(config => {
                                // Populate form fields with current config
                                populateForm(config);
                                document.getElementById('current-config').textContent = JSON.stringify(config, null, 2);
                            })
                            .catch(error => {
                                console.error('Error loading config:', error);
                                showStatus('Error loading configuration', 'error');
                            });
                    }

                    function populateForm(config) {
                        // Slideshow settings
                        if (config.slideshow) {
                            document.getElementById('slideshow_slide_duration_seconds').value = config.slideshow.slide_duration_seconds || 5;
                            document.getElementById('slideshow_shuffle_enabled').value = config.slideshow.shuffle_enabled || false;
                            document.getElementById('slideshow_transitions_enabled').value = config.slideshow.transitions?.enabled || false;
                            document.getElementById('slideshow_transition_type').value = config.slideshow.transitions?.type || 'crossfade';
                            document.getElementById('slideshow_transition_duration').value = config.slideshow.transitions?.duration_seconds || 0.3;
                            document.getElementById('slideshow_ease_type').value = config.slideshow.transitions?.ease_type || 'linear';
                            document.getElementById('slideshow_video_enabled').value = config.slideshow.video_playback?.enabled || false;
                        }
                        
                        if (config.slideshow?.weighted_media?.time_based_weighting) {
                            document.getElementById('weighting_enabled').value = config.slideshow.weighted_media.time_based_weighting.enabled || false;
                            document.getElementById('weighting_day_of_week_enabled').value = config.slideshow.weighted_media.time_based_weighting.day_of_week_enabled || false;
                        }

                        // Folder settings
                        if (config.google_drive) {
                            document.getElementById('google_drive_folder_id').value = config.google_drive.folder_id || '';
                        }
                        
                        if (config.sync) {
                            document.getElementById('auto_sync_enabled').value = config.sync.auto_sync_enabled || false;
                            document.getElementById('sync_interval').value = config.sync.interval_minutes || 30;
                        }

                        // System
                        if (config.web) {
                            document.getElementById('web_host').value = config.web.host || '0.0.0.0';
                            document.getElementById('web_port').value = config.web.port || 8080;
                            document.getElementById('web_debug').value = config.web.debug || false;
                        }
                    }

                    function saveConfig() {
                        // Collect form data
                        let currentConfig = {};
                        
                        // Slideshow
                        if (!currentConfig.slideshow) currentConfig.slideshow = {};
                        if (!currentConfig.slideshow.transitions) currentConfig.slideshow.transitions = {};
                        if (!currentConfig.slideshow.video_playback) currentConfig.slideshow.video_playback = {};
                        if (!currentConfig.slideshow.weighted_media) currentConfig.slideshow.weighted_media = {};
                        if (!currentConfig.slideshow.weighted_media.time_based_weighting) currentConfig.slideshow.weighted_media.time_based_weighting = {};
                        
                        // Slideshow
                        currentConfig.slideshow.slide_duration_seconds = parseInt(document.getElementById('slideshow_slide_duration_seconds').value);
                        currentConfig.slideshow.shuffle_enabled = document.getElementById('slideshow_shuffle_enabled').value === 'true';
                        currentConfig.slideshow.transitions.enabled = document.getElementById('slideshow_transitions_enabled').value === 'true';
                        currentConfig.slideshow.transitions.type = document.getElementById('slideshow_transition_type').value;
                        currentConfig.slideshow.transitions.duration_seconds = parseFloat(document.getElementById('slideshow_transition_duration').value);
                        currentConfig.slideshow.transitions.ease_type = document.getElementById('slideshow_ease_type').value;
                        currentConfig.slideshow.video_playback.enabled = document.getElementById('slideshow_video_enabled').value === 'true';
                        currentConfig.slideshow.weighted_media.time_based_weighting.enabled = document.getElementById('weighting_enabled').value === 'true';
                        currentConfig.slideshow.weighted_media.time_based_weighting.day_of_week_enabled = document.getElementById('weighting_day_of_week_enabled').value === 'true';

                        // Folders
                        if (!currentConfig.google_drive) currentConfig.google_drive = {};
                        currentConfig.google_drive.folder_id = document.getElementById('google_drive_folder_id').value;
                        
                        if (!currentConfig.sync) currentConfig.sync = {};
                        currentConfig.sync.auto_sync_enabled = document.getElementById('auto_sync_enabled').value === 'true';
                        currentConfig.sync.interval_minutes = parseInt(document.getElementById('sync_interval').value);

                        // System
                        if (!currentConfig.web) currentConfig.web = {};
                        currentConfig.web.host = document.getElementById('web_host').value;
                        currentConfig.web.port = parseInt(document.getElementById('web_port').value);
                        currentConfig.web.debug = document.getElementById('web_debug').value === 'true';

                        // Send to server
                        fetch('/api/update_config', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(currentConfig)
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                showStatus('Configuration saved successfully!', 'success');
                                loadConfig(); // Reload to show updated config
                            } else {
                                showStatus('Error saving configuration: ' + data.message, 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showStatus('Error saving configuration', 'error');
                        });
                    }

                    function showStatus(message, type) {
                        const statusDiv = document.getElementById('save-status');
                        statusDiv.innerHTML = '<div class="' + type + '">' + message + '</div>';
                        setTimeout(() => {
                            statusDiv.innerHTML = '';
                        }, 5000);
                    }

                    function showTab(tabName) {
                        // Hide all tab contents
                        var tabContents = document.getElementsByClassName('tab-content');
                        for (var i = 0; i < tabContents.length; i++) {
                            tabContents[i].classList.remove('active');
                        }
                        
                        // Remove active class from all tabs
                        var tabs = document.getElementsByClassName('tab');
                        for (var i = 0; i < tabs.length; i++) {
                            tabs[i].classList.remove('active');
                        }
                        
                        // Show selected tab content and mark tab as active
                        document.getElementById(tabName).classList.add('active');
                        event.target.classList.add('active');
                    }

                    // Load configuration on page load
                    document.addEventListener('DOMContentLoaded', function() {
                        loadConfig();
                    });
                </script>
            </body>
            </html>
            """, config_dump=json.dumps(self.config, indent=2), user=os.getenv('USER', 'unknown'), cred_files=self.get_credential_files())

        @self.app.route("/credentials")
        def credentials_page():
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
                    .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    .form-group { margin: 15px 0; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                    .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
                    .btn:hover { background: #0056b3; }
                    .btn-success { background: #28a745; }
                    .btn-success:hover { background: #1e7e34; }
                    .status { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0; }
                    .warning { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
                    .error { background: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0; }
                    .credential-file { background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; border: 1px solid #ddd; }
                    h1, h2, h3 { color: #333; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔑 Family Center - Credentials Management</h1>
                    
                    <div class="nav">
                        <a href="/">🏠 Home</a>
                        <a href="/config">⚙️ Full Configuration</a>
                        <a href="/credentials">🔑 Credentials</a>
                        <a href="/api/status">🔍 API Status</a>
                    </div>

                    <div class="section">
                        <h2>📁 Current Credentials</h2>
                        <div class="credential-file">
                            <strong>Credentials Directory:</strong> <code>/home/{{ user }}/family_center/credentials/</code>
                        </div>
                        {% if cred_files %}
                            <div class="status">
                                <h3>✅ Found {{ cred_files|length }} credential file(s):</h3>
                                <ul>
                                {% for file in cred_files %}
                                    <li>{{ file }}</li>
                                {% endfor %}
                                </ul>
                            </div>
                        {% else %}
                            <div class="warning">
                                <h3>⚠️ No credential files found</h3>
                                <p>Please add Google Drive credentials to enable photo synchronization.</p>
                            </div>
                        {% endif %}
                    </div>

                    <div class="section">
                        <h2>📤 Upload New Credentials</h2>
                        <form action="/upload_credentials" method="post" enctype="multipart/form-data">
                            <div class="form-group">
                                <label>Select Credential File</label>
                                <input type="file" name="credentials" accept=".json" required>
                                <small>Upload your Google Drive service account JSON file</small>
                            </div>
                            <button type="submit" class="btn btn-success">📤 Upload Credentials</button>
                        </form>
                    </div>

                    <div class="section">
                        <h2>ℹ️ How to Get Google Drive Credentials</h2>
                        <ol>
                            <li>Go to <a href="https://console.cloud.google.com" target="_blank">Google Cloud Console</a></li>
                            <li>Create a new project or select existing one</li>
                            <li>Enable Google Drive API</li>
                            <li>Create a Service Account</li>
                            <li>Download the JSON key file</li>
                            <li>Upload it here or place it in the credentials directory</li>
                        </ol>
                    </div>

                    <div class="section">
                        <h2>🔧 Manual Setup</h2>
                        <p>Alternatively, you can manually copy credential files to the credentials directory:</p>
                        <pre><code>scp your-credentials.json {{ user }}@your-pi-ip:/home/{{ user }}/family_center/credentials/</code></pre>
                    </div>
                </div>
            </body>
            </html>
            """, user=os.getenv('USER', 'unknown'), cred_files=self.get_credential_files())

        @self.app.route("/api/status")
        def api_status():
            return jsonify({
                'status': 'running',
                'service': 'Family Center',
                'version': 'v-5-pre-alpha-enhanced',
                'features': [
                    'Enhanced slideshow configuration',
                    'Transition effects',
                    'Time-based weighting',
                    'Video playback support',
                    'Folder management',
                    'Credential management'
                ]
            })

        @self.app.route("/api/config")
        def api_config():
            return jsonify(self.config)

        @self.app.route("/api/update_config", methods=["POST"])
        def api_update_config():
            try:
                data = request.get_json()
                # Update config with new data
                self.config.update(data)
                return jsonify({"success": True, "message": "Configuration updated"})
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 400

        @self.app.route("/upload_credentials", methods=["POST"])
        def upload_credentials():
            if 'credentials' not in request.files:
                return jsonify({"success": False, "message": "No file uploaded"}), 400
            
            file = request.files['credentials']
            if file.filename == '':
                return jsonify({"success": False, "message": "No file selected"}), 400
            
            if file and file.filename.endswith('.json'):
                filename = secure_filename(file.filename)
                file.save(os.path.join('credentials', filename))
                return jsonify({"success": True, "message": f"Credentials uploaded: {filename}"})
            else:
                return jsonify({"success": False, "message": "Invalid file type. Please upload a JSON file."}), 400

    def get_credential_files(self):
        """Get list of credential files"""
        cred_dir = os.path.join(os.path.expanduser('~'), 'family_center', 'credentials')
        if os.path.exists(cred_dir):
            return [f for f in os.listdir(cred_dir) if f.endswith('.json')]
        return []

    def run(self):
        """Run the web interface"""
        host = self.config.get("web.host", "0.0.0.0")
        port = self.config.get("web.port", 8080)
        debug = self.config.get("web.debug", False)

        self.logger.info(f"Starting enhanced web interface on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, use_reloader=False)
EOF

# Create config manager
cat > config_manager.py << 'EOF'
"""Configuration manager for the Family Center application."""

import os
from typing import Any

import yaml


class ConfigManager:
    """Manages application configuration loading and validation."""

    def __init__(self, config_path: str = "src/config/config.yaml"):
        """Initialize the configuration manager.

        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            self._validate_config()
        except FileNotFoundError as err:
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            ) from err
        except yaml.YAMLError as err:
            raise ValueError(f"Error parsing YAML configuration: {str(err)}") from err

    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        required_sections = ["google_drive", "slideshow", "display", "logging"]
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")

        # Validate media paths
        media_path = self.config["google_drive"]["local_media_path"]
        if not os.path.exists(media_path):
            os.makedirs(media_path, exist_ok=True)

    def get(self, section: str, key: str | None = None) -> Any:
        """Get configuration value.

        Args:
            section: Configuration section name
            key: Optional key within the section

        Returns:
            Configuration value or section
        """
        if section not in self.config:
            raise KeyError(f"Configuration section not found: {section}")

        if key is None:
            return self.config[section]

        if key not in self.config[section]:
            raise KeyError(f"Configuration key not found: {section}.{key}")

        return self.config[section][key]

    def reload(self) -> None:
        """Reload configuration from file."""
        self.load_config()

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary.

        Returns:
            The configuration as a dictionary.
        """
        return self.config

    def save_config(self) -> None:
        """Save the current configuration to the YAML file."""
        import yaml

        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.config, f, sort_keys=False, allow_unicode=True)

    def set_config(self, new_config: dict[str, Any]) -> None:
        """Replace the current config dict and validate it."""
        self.config = new_config
        self._validate_config()
EOF

# Create simplified web content service
cat > simple_web_content_service.py << 'EOF'
"""Simplified Web Content Service for Family Center Installer"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class WebContentTarget:
    """Represents a web content target for screenshot capture."""

    def __init__(
        self,
        name: str,
        url: str,
        selector: str = "body",
        enabled: bool = True,
        weight: float = 1.0,
    ):
        self.name = name
        self.url = url
        self.selector = selector
        self.enabled = enabled
        self.weight = weight


class WebContentService:
    """Simplified web content service for the installer."""

    def __init__(self):
        self.targets: List[WebContentTarget] = []
        self.browser = None
        logger.info("Simplified WebContentService initialized")

    def get_target_by_name(self, name: str) -> Optional[WebContentTarget]:
        """Get a target by name."""
        for target in self.targets:
            if target.name == name:
                return target
        return None

    def add_target(self, target: WebContentTarget) -> None:
        """Add a new target."""
        self.targets.append(target)

    def remove_target(self, target: WebContentTarget) -> None:
        """Remove a target."""
        if target in self.targets:
            self.targets.remove(target)

    def cleanup_old_screenshots(self, target_name: str) -> None:
        """Clean up old screenshots for a target (simplified)."""
        logger.info(f"Would cleanup screenshots for {target_name}")

    def save_targets_to_config(self) -> None:
        """Save targets to configuration (simplified)."""
        logger.info("Would save targets to configuration")
EOF
