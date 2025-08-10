#!/bin/bash

# Family Center Installer - Version -5 (Pre-Alpha)
# Enhanced version with package download approach

set -e

echo "🏠 Family Center Installer - Version -5 (Pre-Alpha)"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FAMILY_CENTER_DIR="$HOME/family_center"
PACKAGE_URL="https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/family_center_enhanced_v5_full.zip"
BACKUP_DIR="$HOME/family_center_backup_$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}📋 Step 1/6: Checking system requirements...${NC}"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   exit 1
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip3 not found, installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

echo -e "${GREEN}✅ pip3 found${NC}"

echo -e "${BLUE}📋 Step 2/6: Installing system dependencies...${NC}"

# Update package list
sudo apt-get update

# Install required packages
sudo apt-get install -y \
    python3-venv \
    python3-pip \
    unzip \
    curl \
    wget

echo -e "${GREEN}✅ System dependencies installed${NC}"

echo -e "${BLUE}📋 Step 3/6: Setting up Family Center application...${NC}"

# Check if Family Center is already installed
if [[ -d "$FAMILY_CENTER_DIR" ]]; then
    echo -e "${YELLOW}📁 Found existing Family Center installation${NC}"
    echo -e "${YELLOW}🔄 Backing up existing installation...${NC}"
    
    # Create backup
    mkdir -p "$BACKUP_DIR"
    cp -r "$FAMILY_CENTER_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
    echo -e "${GREEN}✅ Backup created at: $BACKUP_DIR${NC}"
    
    # Remove existing installation
    rm -rf "$FAMILY_CENTER_DIR"
fi

# Create application directory
echo -e "${BLUE}📂 Creating application structure...${NC}"
mkdir -p "$FAMILY_CENTER_DIR"
cd "$FAMILY_CENTER_DIR"

echo -e "${BLUE}📝 Step 4/6: Downloading enhanced Family Center package...${NC}"

# Download the enhanced package
echo -e "${YELLOW}📥 Downloading Family Center enhanced package (full version)...${NC}"
if curl -L -o family_center_enhanced_v5_full.zip "$PACKAGE_URL"; then
    echo -e "${GREEN}✅ Package downloaded successfully${NC}"
else
    echo -e "${RED}❌ Failed to download package${NC}"
    exit 1
fi

# Extract the package
echo -e "${YELLOW}📦 Extracting package...${NC}"
unzip -q family_center_enhanced_v5_full.zip
rm family_center_enhanced_v5_full.zip

echo -e "${GREEN}✅ Package extracted successfully${NC}"

echo -e "${BLUE}📝 Step 5/6: Setting up Python environment...${NC}"

# Create virtual environment
echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Python environment setup complete${NC}"

echo -e "${BLUE}📝 Step 6/6: Creating system service...${NC}"

# Create systemd service file
sudo tee /etc/systemd/system/family-center.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Family Center Application
After=network.target

[Service]
Type=simple
User=benjaminhodson
WorkingDirectory=/home/benjaminhodson/family_center
Environment=PATH=/home/benjaminhodson/family_center/venv/bin
ExecStart=/home/benjaminhodson/family_center/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Replace username in service file
sudo sed -i "s/benjaminhodson/$USER/g" /etc/systemd/system/family-center.service

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable family-center.service

echo -e "${GREEN}✅ System service created and enabled${NC}"

# Configure firewall
echo -e "${YELLOW}🔥 Configuring firewall...${NC}"
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8080/tcp
sudo ufw --force enable

echo -e "${GREEN}✅ Firewall configured${NC}"

# Start the service
echo -e "${YELLOW}🚀 Starting Family Center service...${NC}"
sudo systemctl start family-center.service

# Wait a moment for service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet family-center.service; then
    echo -e "${GREEN}✅ Family Center service is running${NC}"
else
    echo -e "${RED}❌ Family Center service failed to start${NC}"
    sudo systemctl status family-center.service
    exit 1
fi

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}🎉 Family Center installation completed successfully!${NC}"
echo ""
echo -e "${BLUE}📱 Access your Family Center at:${NC}"
echo -e "${GREEN}   http://$IP_ADDRESS:8080${NC}"
echo ""
echo -e "${BLUE}🔧 Service Management:${NC}"
echo -e "${YELLOW}   Check status:  sudo systemctl status family-center.service${NC}"
echo -e "${YELLOW}   Stop service:   sudo systemctl stop family-center.service${NC}"
echo -e "${YELLOW}   Start service:  sudo systemctl start family-center.service${NC}"
echo -e "${YELLOW}   View logs:      sudo journalctl -u family-center.service -f${NC}"
echo ""
echo -e "${BLUE}📁 Application Directory:${NC}"
echo -e "${GREEN}   $FAMILY_CENTER_DIR${NC}"
echo ""
echo -e "${BLUE}🔑 Next Steps:${NC}"
echo -e "${YELLOW}   1. Open http://$IP_ADDRESS:8080 in your browser${NC}"
echo -e "${YELLOW}   2. Configure your slideshow settings${NC}"
echo -e "${YELLOW}   3. Add Google Drive credentials${NC}"
echo -e "${YELLOW}   4. Set up your media folders${NC}"
echo ""
echo -e "${GREEN}✨ Enjoy your enhanced Family Center!${NC}"
