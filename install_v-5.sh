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
cat > src/modules/web_interface.py << 'EOF'

# Create other module stubs
cat > src/modules/photo_manager.py << 'EOF'
"""Photo management for Family Center"""

class PhotoManager:
    def __init__(self, config):
        self.config = config
    
    def load_photos(self):
        """Load photos from Google Drive"""
        pass
    
    def get_next_photo(self):
        """Get next photo for slideshow"""
        pass
EOF

cat > src/modules/weather_service.py << 'EOF'
"""Weather service for Family Center"""

class WeatherService:
    def __init__(self, config):
        self.config = config
    
    def get_current_weather(self):
        """Get current weather information"""
        pass
EOF

cat > src/modules/news_service.py << 'EOF'
"""News service for Family Center"""

class NewsService:
    def __init__(self, config):
        self.config = config
    
    def get_news(self):
        """Get latest news"""
        pass
EOF

cat > src/modules/calendar_service.py << 'EOF'
"""Calendar service for Family Center"""

class CalendarService:
    def __init__(self, config):
        self.config = config
    
    def get_events(self):
        """Get calendar events"""
        pass
EOF

# Create __init__.py files
touch src/__init__.py
touch src/modules/__init__.py
touch src/utils/__init__.py

# Create default config
cat > src/config/config.yaml << 'EOF'
# Family Center Configuration
web:
  host: 0.0.0.0
  port: 8080
  debug: false

google_drive:
  credentials_file: credentials/google_drive_credentials.json
  token_file: credentials/google_drive_token.json
  folder_id: ""

display:
  slideshow_interval: 5
  transition_effect: fade
  fullscreen: true

weather:
  api_key: ""
  location: "London,UK"
  units: metric

news:
  sources: [bbc, reuters]
  update_interval: 30
EOF

# Step 5: Setup Python environment
echo "🐍 Step 5/6: Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Python environment setup complete"

# Step 6: Setup system service
echo "⚙️  Step 6/6: Setting up system service..."

# Create service file with proper escaping
sudo tee /etc/systemd/system/family-center.service > /dev/null << EOF
[Unit]
Description=Family Center Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/family_center
Environment=PATH=/home/$USER/family_center/venv/bin
ExecStart=/home/$USER/family_center/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable family-center.service

# Setup basic firewall
echo "🔒 Configuring security..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8080/tcp
sudo ufw --force enable

# Get IP address
PI_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "🎉 Installation Complete!"
echo "========================"
echo ""
echo "🌐 Your Family Center is ready! Access it at:"
echo "   http://$PI_IP:8080/config"
echo ""
echo "🚀 Quick Start Commands:"
echo "   • Test web UI:     cd /home/$USER/family_center && source venv/bin/activate && python3 src/main.py --web-only"
echo "   • Start service:   sudo systemctl start family-center"
echo "   • Check status:    sudo systemctl status family-center"
echo "   • View logs:       sudo journalctl -u family-center -f"
echo ""
echo "📋 Next Steps:"
echo "1. 🔑 Add Google Drive credentials in the credentials/ folder"
echo "2. ⚙️  Configure settings at http://$PI_IP:8080/config"
echo "3. 🚀 Start the service: sudo systemctl start family-center"
echo ""
echo "🎊 Your Raspberry Pi is now a Family Center!"
echo ""
echo "📝 Version -5 (Pre-Alpha) Features:"
echo "   ✅ Self-contained installation (no external repository needed)"
echo "   ✅ Embedded application files"
echo "   ✅ Simplified setup process"
echo "   ✅ Faster installation time"
echo "   ⚠️  Pre-alpha release - basic framework only" """Enhanced Web interface for Family Center with credential management"""

from flask import Flask, jsonify, render_template_string, request, redirect, url_for, flash
import logging
import os
import json
import yaml
from werkzeug.utils import secure_filename

class WebInterface:
    def __init__(self, config):
        self.config = config
        self.app = Flask(__name__)
        self.app.secret_key = 'family_center_secret_key_2025'
        self.setup_routes()
        self.logger = logging.getLogger(__name__)
        
        # Ensure credentials directory exists
        os.makedirs('credentials', exist_ok=True)
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template_string('''
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
            ''')
        
        @self.app.route('/credentials')
        def credentials_page():
            # Get list of existing credential files
            cred_files = []
            if os.path.exists('credentials'):
                for file in os.listdir('credentials'):
                    if file.endswith('.json'):
                        cred_files.append(file)
            
            return render_template_string('''
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
            ''', cred_files=cred_files, config=self.config.config)
        
        @self.app.route('/upload_credentials', methods=['POST'])
        def upload_credentials():
            if 'credentials_file' not in request.files:
                return 'No file uploaded', 400
            
            file = request.files['credentials_file']
            if file.filename == '':
                return 'No file selected', 400
            
            if file and file.filename.endswith('.json'):
                filename = secure_filename(file.filename)
                filepath = os.path.join('credentials', filename)
                file.save(filepath)
                
                # Try to validate the JSON
                try:
                    with open(filepath, 'r') as f:
                        json.load(f)
                    return redirect('/credentials?success=File uploaded successfully!')
                except json.JSONDecodeError:
                    os.remove(filepath)
                    return 'Invalid JSON file', 400
            
            return 'Invalid file type', 400
        
        @self.app.route('/delete_credential/<filename>')
        def delete_credential(filename):
            filepath = os.path.join('credentials', filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect('/credentials?success=File deleted!')
        
        @self.app.route('/update_config', methods=['POST'])
        def update_config():
            folder_id = request.form.get('folder_id', '')
            credentials_file = request.form.get('credentials_file', '')
            
            # Update config
            self.config.config['google_drive']['folder_id'] = folder_id
            if credentials_file:
                self.config.config['google_drive']['credentials_file'] = credentials_file
            
            # Save config
            self.config.save_config()
            
            return redirect('/credentials?success=Configuration updated!')
        
        @self.app.route('/config')
        def config_page():
            return render_template_string('''
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
            ''', config=self._format_config(self.config.config))
        
        @self.app.route('/api/config', methods=['GET'])
        def api_config():
            return jsonify(self.config.config)
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                'status': 'running',
                'version': '-5 (Pre-Alpha)',
                'installation_type': 'self-contained',
                'services': {
                    'web': 'active',
                    'photos': 'framework-ready',
                    'weather': 'framework-ready',
                    'news': 'framework-ready',
                    'calendar': 'framework-ready'
                },
                'endpoints': {
                    'home': '/',
                    'config': '/config',
                    'credentials': '/credentials',
                    'api_status': '/api/status',
                    'api_config': '/api/config'
                }
            })
    
    def _format_config(self, config):
        """Format configuration for display"""
        try:
            return yaml.dump(config, default_flow_style=False, indent=2)
        except:
            return str(config)
    
    def run(self):
        """Run the web interface"""
        host = self.config.get('web.host', '0.0.0.0')
        port = self.config.get('web.port', 8080)
        debug = self.config.get('web.debug', False)
        
        self.logger.info(f"Starting web interface on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, use_reloader=False)
EOF
