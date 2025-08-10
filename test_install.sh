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
echo "📦 Step 1/7: Updating system packages..."
sudo apt update -qq && sudo apt upgrade -y -qq
sudo apt autoremove -y -qq

# Step 2: Install dependencies
echo "🔧 Step 2/7: Installing system dependencies..."
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

# Step 3: Download and extract Family Center package
echo "📦 Step 3/7: Downloading Family Center package..."
cd /home/pi

# Configuration
FAMILY_CENTER_DIR="/home/pi/family_center"
PACKAGE_URL="https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/family_center_complete_v12.zip"
BACKUP_DIR="/home/pi/family_center_backup_$(date +%Y%m%d_%H%M%S)"

# Create backup if existing installation exists
if [[ -d "$FAMILY_CENTER_DIR" ]]; then
    echo "📁 Found existing Family Center installation"
    echo "🔄 Creating backup at $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    cp -r "$FAMILY_CENTER_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
    echo "✅ Backup created successfully"
    
    # Remove existing installation
    echo "🗑️  Removing existing installation..."
    rm -rf "$FAMILY_CENTER_DIR"
fi

# Create new installation directory
echo "📁 Creating installation directory..."
mkdir -p "$FAMILY_CENTER_DIR"
cd "$FAMILY_CENTER_DIR"

# Download and extract package
echo "📥 Downloading Family Center package..."
if curl -L -o family_center_complete_v6.zip "$PACKAGE_URL"; then
    echo "✅ Package downloaded successfully"
    echo "📦 Extracting package..."
    unzip -q family_center_complete_v6.zip
    rm family_center_complete_v6.zip
    
    # Move package contents to the correct location
    echo "📁 Moving package contents..."
    if [ -d "family_center_package" ]; then
        mv family_center_package/* .
        mv family_center_package/.* . 2>/dev/null || true
        rmdir family_center_package
    fi
    
    echo "✅ Package extracted and moved successfully"
else
    echo "❌ Failed to download package"
    echo "   Please check your internet connection and try again"
    exit 1
fi

# Step 4: Verify package structure
echo "🔍 Step 4/7: Verifying package structure..."
if [ ! -f "requirements.txt" ] || [ ! -f "src/main.py" ]; then
    echo "❌ Error: Package structure doesn't match expected Family Center layout"
    echo "   This might be an incomplete or corrupted package"
    echo "   Please try downloading the package again"
    exit 1
fi
echo "✅ Package structure verified successfully"

# Step 5: Setup Python environment
echo "🐍 Step 5/7: Setting up Python environment..."
if [ -f "requirements.txt" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    echo "✅ Python environment setup complete"
else
    echo "⚠️  No requirements.txt found. Creating basic Python environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    echo "✅ Basic Python environment created"
fi

# Step 6: Create directories and configuration
echo "📁 Step 6/7: Setting up directories and configuration..."
mkdir -p media/remote_drive media/web_news media/weather media/local_media
mkdir -p downloads logs credentials

# Handle configuration file
if [ -f "src/config/config.yaml.example" ]; then
    if [ ! -f "src/config/config.yaml" ]; then
        cp src/config/config.yaml.example src/config/config.yaml
        echo "✅ Configuration file created from example"
    else
        echo "✅ Configuration file already exists"
    fi
else
    echo "⚠️  No config.yaml.example found. You may need to create config.yaml manually."
fi

# Step 7: Setup system service
echo "⚙️  Step 7/7: Setting up system service..."
sudo tee /etc/systemd/system/family-center.service > /dev/null << SERVICEEOF
[Unit]
Description=Family Center Application
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/family_center
Environment=PATH=/home/pi/family_center/venv/bin
Environment=PYTHONPATH=/home/pi/family_center
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
echo "📦 Package Installation Notes:"
echo "   - Family Center was installed from a self-contained package"
echo "   - No external repository access required"
echo "   - All application files are included in the package"
echo ""
echo "📚 Need help? Check the documentation at:"
echo "   https://github.com/themaddog1068/family_center"
echo ""
echo "🎊 Your Raspberry Pi is now a Family Center!"
