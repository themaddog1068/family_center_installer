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
cd /home/pi

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
cat > requirements.txt << 'REQEOF'
flask==2.3.3
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
REQEOF

# Create main.py
cat > src/main.py << 'MAINEOF'
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
MAINEOF

# Create config manager
cat > src/utils/config_manager.py << 'CONFIGEOF'
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
CONFIGEOF

# Create web interface
cat > src/modules/web_interface.py << 'WEBEOF'
"""Web interface for Family Center"""

from flask import Flask, render_template, request, jsonify
import logging

class WebInterface:
    def __init__(self, config):
        self.config = config
        self.app = Flask(__name__)
        self.setup_routes()
        self.logger = logging.getLogger(__name__)
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/config')
        def config_page():
            return render_template('config.html', config=self.config.config)
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def api_config():
            if request.method == 'POST':
                data = request.json
                # Update config logic here
                return jsonify({'status': 'success'})
            return jsonify(self.config.config)
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                'status': 'running',
                'version': '5.0',
                'services': {
                    'photos': 'ready',
                    'weather': 'ready',
                    'news': 'ready',
                    'calendar': 'ready'
                }
            })
    
    def run(self):
        """Run the web interface"""
        host = self.config.get('web.host', '0.0.0.0')
        port = self.config.get('web.port', 8080)
        debug = self.config.get('web.debug', False)
        
        self.logger.info(f"Starting web interface on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)
WEBEOF

# Create other module stubs
cat > src/modules/photo_manager.py << 'PHOTOEOF'
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
PHOTOEOF

cat > src/modules/weather_service.py << 'WEATHEREOF'
"""Weather service for Family Center"""

class WeatherService:
    def __init__(self, config):
        self.config = config
    
    def get_current_weather(self):
        """Get current weather information"""
        pass
WEATHEREOF

cat > src/modules/news_service.py << 'NEWSEOF'
"""News service for Family Center"""

class NewsService:
    def __init__(self, config):
        self.config = config
    
    def get_news(self):
        """Get latest news"""
        pass
NEWSEOF

cat > src/modules/calendar_service.py << 'CALEOF'
"""Calendar service for Family Center"""

class CalendarService:
    def __init__(self, config):
        self.config = config
    
    def get_events(self):
        """Get calendar events"""
        pass
CALEOF

# Create __init__.py files
touch src/__init__.py
touch src/modules/__init__.py
touch src/utils/__init__.py

# Create default config
cat > src/config/config.yaml << 'YAMLEOF'
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
YAMLEOF

# Step 5: Setup Python environment
echo "🐍 Step 5/6: Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Python environment setup complete"

# Step 6: Setup system service
echo "⚙️  Step 6/6: Setting up system service..."
sudo tee /etc/systemd/system/family-center.service > /dev/null << SERVICEEOF
[Unit]
Description=Family Center Application
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/family_center
Environment=PATH=/home/pi/family_center/venv/bin
ExecStart=/home/pi/family_center/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable family-center

# Setup basic firewall
echo "🔒 Configuring security..."
sudo ufw default deny incoming -q
sudo ufw default allow outgoing -q
sudo ufw allow ssh -q
sudo ufw allow 8080 -q
sudo ufw --force enable -q

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
echo "   • Test web UI:     cd /home/pi/family_center && source venv/bin/activate && python3 src/main.py --web-only"
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
echo "   ⚠️  Pre-alpha release - basic framework only" 