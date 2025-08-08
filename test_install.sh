#!/bin/bash

# Simple test installer to bypass caching issues
echo "🍓 Family Center Test Installer"
echo "==============================="
echo ""
echo "🎯 Testing installation on your Raspberry Pi 5"
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

echo ""
echo "🔧 Starting installation..."
echo ""

# Step 1: Update system
echo "📦 Step 1/6: Updating system packages..."
sudo apt update -qq && sudo apt upgrade -y -qq
sudo apt autoremove -y -qq

# Step 2: Install dependencies
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

# Step 3: Clone repository
echo "📥 Step 3/6: Downloading Family Center..."
cd /home/pi
if [ -d "family_center" ]; then
    echo "📁 Updating existing installation..."
    cd family_center
    git pull -q
else
    git clone -q https://github.com/themaddog1068/family_center.git
    cd family_center
fi

# Step 4: Setup Python environment
echo "🐍 Step 4/6: Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Step 5: Create directories and configuration
echo "📁 Step 5/6: Setting up directories and configuration..."
mkdir -p media/remote_drive media/web_news media/weather media/local_media
mkdir -p downloads logs credentials

if [ ! -f "src/config/config.yaml" ]; then
    if [ -f "src/config/config.yaml.example" ]; then
        cp src/config/config.yaml.example src/config/config.yaml
        echo "✅ Configuration file created from example"
    fi
fi

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
echo "📚 Need help? Check the documentation at:"
echo "   https://github.com/themaddog1068/family_center"
echo ""
echo "🎊 Your Raspberry Pi is now a Family Center!"
