#!/bin/bash

# Family Center Installer
# Universal installer for Raspberry Pi 5, 4, and 3B+
# One-command installation for your Raspberry Pi

set -e

echo "🍓 Family Center Universal Installer"
echo "===================================="
echo ""
echo "🎯 This will install Family Center on your Raspberry Pi"
echo "📱 Supports Pi 5, Pi 4, and Pi 3B+"
echo "⏱️  Estimated time: 15-25 minutes"
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
echo "📦 Step 1/7: Updating system packages..."
sudo apt update -qq && sudo apt upgrade -y -qq
sudo apt autoremove -y -qq

# Step 2: Install dependencies (optimized for Pi 5, compatible with Pi 4/3B+)
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

# Step 3: Check for existing Family Center installation
echo "📁 Step 3/7: Checking for Family Center installation..."
cd /home/pi

if [ -d "family_center" ]; then
    echo "📁 Found existing Family Center installation"
    cd family_center
    
    # Check if it's a git repository
    if [ -d ".git" ]; then
        echo "🔄 Updating existing installation..."
        if git pull -q; then
            echo "✅ Successfully updated Family Center"
        else
            echo "⚠️  Failed to update via git pull"
            echo "   This might be due to authentication issues with the private repository"
            echo "   Please ensure you have proper access to the Family Center repository"
            read -p "Continue with existing files? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "❌ Installation cancelled. Please check your repository access."
                exit 1
            fi
        fi
    else
        echo "📁 Found family_center directory but it's not a git repository"
        echo "   This might be a manual installation"
    fi
else
    echo "📥 Step 3/7: Setting up Family Center repository..."
    echo ""
    echo "🔐 The Family Center repository is private and requires authentication."
    echo "   You have several options:"
    echo ""
    echo "   1. Use SSH key authentication (recommended):"
    echo "      - Ensure your SSH key is added to your GitHub account"
    echo "      - The repository will be cloned via SSH"
    echo ""
    echo "   2. Use HTTPS with personal access token:"
    echo "      - Create a personal access token on GitHub"
    echo "      - Use it when prompted for password"
    echo ""
    echo "   3. Manual setup:"
    echo "      - Clone the repository manually after installation"
    echo "      - Place it in /home/pi/family_center"
    echo ""
    
    read -p "Choose option (1/2/3): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            echo "🔑 Attempting SSH clone..."
            if git clone -q git@github.com:themaddog1068/family_center.git; then
                echo "✅ Successfully cloned Family Center via SSH"
                cd family_center
            else
                echo "❌ SSH clone failed. Please ensure:"
                echo "   - Your SSH key is added to GitHub"
                echo "   - You have access to the Family Center repository"
                echo "   - Your SSH agent is running: ssh-add ~/.ssh/id_rsa"
                exit 1
            fi
            ;;
        2)
            echo "🔑 Attempting HTTPS clone..."
            if git clone -q https://github.com/themaddog1068/family_center.git; then
                echo "✅ Successfully cloned Family Center via HTTPS"
                cd family_center
            else
                echo "❌ HTTPS clone failed. Please ensure:"
                echo "   - You have a valid personal access token"
                echo "   - You have access to the Family Center repository"
                exit 1
            fi
            ;;
        3)
            echo "📁 Creating directory structure for manual setup..."
            mkdir -p family_center
            cd family_center
            echo "✅ Directory created. Please manually clone the repository here."
            echo "   Then run this installer again."
            ;;
        *)
            echo "❌ Invalid option. Installation cancelled."
            exit 1
            ;;
    esac
fi

# Step 4: Verify repository structure
echo "🔍 Step 4/7: Verifying repository structure..."
if [ ! -f "requirements.txt" ] && [ ! -f "src/main.py" ]; then
    echo "⚠️  Warning: Repository structure doesn't match expected Family Center layout"
    echo "   This might be an incomplete or incorrect repository"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled. Please check the repository contents."
        exit 1
    fi
fi

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
echo "🔐 Repository Access Notes:"
echo "   - If you had issues with repository access, ensure you have proper authentication"
echo "   - For SSH: ssh-add ~/.ssh/id_rsa"
echo "   - For HTTPS: Use personal access tokens"
echo ""
echo "📚 Need help? Check the documentation at:"
echo "   https://github.com/themaddog1068/family_center"
echo ""
echo "🎊 Your Raspberry Pi is now a Family Center!"
