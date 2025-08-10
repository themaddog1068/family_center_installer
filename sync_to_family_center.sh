#!/bin/bash

# Family Center Integration Script
# This script extracts all improvements from the installer and applies them to the family-center repository

set -e

echo "🔄 Family Center Integration Script"
echo "=================================="
echo ""
echo "This script will sync all improvements from the installer to the family-center repository"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "install_v-5.sh" ]; then
    print_error "This script must be run from the family_center_installer directory"
    exit 1
fi

# Check if family-center repository exists
FAMILY_CENTER_DIR="../family_center"
if [ ! -d "$FAMILY_CENTER_DIR" ]; then
    print_warning "Family Center repository not found at $FAMILY_CENTER_DIR"
    read -p "Would you like to clone it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cloning Family Center repository..."
        git clone https://github.com/themaddog1068/family_center.git "$FAMILY_CENTER_DIR"
        if [ $? -ne 0 ]; then
            print_error "Failed to clone repository. Please check your access permissions."
            exit 1
        fi
    else
        print_error "Cannot proceed without Family Center repository"
        exit 1
    fi
fi

print_status "Found Family Center repository at $FAMILY_CENTER_DIR"

# Create backup of current family-center
BACKUP_DIR="../family_center_backup_$(date +%Y%m%d_%H%M%S)"
print_status "Creating backup of current Family Center at $BACKUP_DIR"
cp -r "$FAMILY_CENTER_DIR" "$BACKUP_DIR" 2>/dev/null || print_warning "Some files could not be backed up (this is normal for missing credential files)"

# Extract application files from installer
print_status "Extracting application files from installer..."

# Store absolute paths
SCRIPT_DIR="$(pwd)"
FAMILY_CENTER_DIR_ABS="$(cd "$FAMILY_CENTER_DIR" && pwd)"

# Create temporary directory for extraction
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Extract the embedded Python files from install_v-5.sh
print_status "Extracting Python application files..."

# Store the path to the installer
INSTALLER_PATH="$SCRIPT_DIR/install_v-5.sh"

# Extract main.py
sed -n '/^cat > src\/main.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > main.py

# Extract config.yaml
sed -n '/^cat > src\/config\/config.yaml/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > config.yaml

# Extract requirements.txt
sed -n '/^cat > requirements.txt/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > requirements.txt

# Extract web_interface.py
sed -n '/^cat > src\/modules\/web_interface.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > web_interface.py

# Extract photo_manager.py
sed -n '/^cat > src\/modules\/photo_manager.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > photo_manager.py

# Extract weather_manager.py
sed -n '/^cat > src\/modules\/weather_manager.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > weather_manager.py

# Extract news_manager.py
sed -n '/^cat > src\/modules\/news_manager.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > news_manager.py

# Extract calendar_manager.py
sed -n '/^cat > src\/modules\/calendar_manager.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > calendar_manager.py

# Extract config_manager.py
sed -n '/^cat > src\/modules\/config_manager.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > config_manager.py

# Extract __init__.py files
sed -n '/^cat > src\/__init__.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > __init__.py
sed -n '/^cat > src\/modules\/__init__.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > modules_init.py
sed -n '/^cat > src\/config\/__init__.py/,/^EOF$/p' "$INSTALLER_PATH" | sed '1d;$d' > config_init.py

print_success "Extracted all application files"

# Now apply the files to the family-center repository
print_status "Applying files to Family Center repository..."

cd "$FAMILY_CENTER_DIR_ABS"

# Create directory structure
mkdir -p src/modules src/config credentials media logs

# Copy the extracted files
cp "$TEMP_DIR/main.py" src/
cp "$TEMP_DIR/config.yaml" src/config/
cp "$TEMP_DIR/requirements.txt" ./
cp "$TEMP_DIR/web_interface.py" src/modules/
cp "$TEMP_DIR/photo_manager.py" src/modules/
cp "$TEMP_DIR/weather_manager.py" src/modules/
cp "$TEMP_DIR/news_manager.py" src/modules/
cp "$TEMP_DIR/calendar_manager.py" src/modules/
cp "$TEMP_DIR/config_manager.py" src/modules/
cp "$TEMP_DIR/__init__.py" src/
cp "$TEMP_DIR/modules_init.py" src/modules/__init__.py
cp "$TEMP_DIR/config_init.py" src/config/__init__.py

print_success "Applied all application files"

# Create enhanced README for the family-center repository
print_status "Creating enhanced README..."

cat > README.md << 'EOF'
# 🍓 Family Center

A comprehensive family management system for Raspberry Pi with photo synchronization, weather updates, news feeds, and calendar integration.

## 🚀 Features

- **Photo Management**: Automatic Google Drive photo synchronization
- **Weather Updates**: Real-time weather information
- **News Feeds**: Customizable news aggregation
- **Calendar Integration**: Google Calendar synchronization
- **Web Interface**: User-friendly web-based configuration
- **Credential Management**: Secure credential upload and management

## 📋 Requirements

- Raspberry Pi (Pi 5, Pi 4, or Pi 3B+)
- Python 3.11+
- Google Cloud Platform account
- Google Drive API enabled
- OAuth 2.0 credentials

## 🛠️ Installation

### Quick Install (Recommended)
```bash
curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install_v-5.sh | bash
```

### Manual Installation
1. Clone this repository
2. Install Python dependencies: `pip install -r requirements.txt`
3. Configure Google Drive credentials
4. Run: `python src/main.py`

## 🔧 Configuration

### Web Interface
Access the web interface at `http://your-pi-ip:8080`

- **Home**: System status and quick links
- **Credentials**: Upload and manage Google Drive credentials
- **Configuration**: View and edit system settings
- **API Status**: Check service status

### Manual Configuration
Edit `src/config/config.yaml` for advanced settings.

## 📁 Directory Structure

```
family_center/
├── src/
│   ├── main.py              # Main application entry point
│   ├── modules/
│   │   ├── web_interface.py # Web interface and credential management
│   │   ├── photo_manager.py # Google Drive photo synchronization
│   │   ├── weather_manager.py # Weather data management
│   │   ├── news_manager.py  # News feed management
│   │   ├── calendar_manager.py # Calendar integration
│   │   └── config_manager.py # Configuration management
│   └── config/
│       └── config.yaml      # Configuration file
├── credentials/             # Google Drive credentials
├── media/                   # Local media storage
├── logs/                    # Application logs
└── requirements.txt         # Python dependencies
```

## 🔑 Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the JSON credentials file
6. Upload via the web interface or place in `credentials/` directory

## 🚀 Quick Start

1. Run the installer: `curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install_v-5.sh | bash`
2. Access web interface: `http://your-pi-ip:8080`
3. Upload Google Drive credentials
4. Configure your settings
5. Start using Family Center!

## 🔧 Management Commands

```bash
# Start the service
sudo systemctl start family-center

# Stop the service
sudo systemctl stop family-center

# Check status
sudo systemctl status family-center

# View logs
sudo journalctl -u family-center -f

# Restart service
sudo systemctl restart family-center
```

## 📝 Version History

### Version -5 (Pre-Alpha)
- Self-contained installer
- Enhanced web interface with credential management
- Improved error handling and user experience
- Complete application framework

## 🤝 Contributing

This is a pre-alpha release. Contributions are welcome!

## 📄 License

This project is licensed under the MIT License.
EOF

print_success "Created enhanced README"

# Create systemd service file
print_status "Creating systemd service file..."

cat > family-center.service << 'EOF'
[Unit]
Description=Family Center Application
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/family_center
Environment=PYTHONPATH=/home/pi/family_center/src
ExecStart=/home/pi/family_center/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_success "Created systemd service file"

# Create installation script for the family-center repository
print_status "Creating installation script..."

cat > install.sh << 'EOF'
#!/bin/bash

# Family Center Installation Script
# This script installs Family Center from the source repository

set -e

echo "🍓 Family Center Installation Script"
echo "==================================="
echo ""
echo "This will install Family Center from the source repository"
echo ""

# Check if running as pi user
if [ "$USER" != "pi" ]; then
    echo "⚠️  Warning: This script should be run as the 'pi' user"
    echo "   Current user: $USER"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled"
        exit 1
    fi
fi

echo ""
echo "🔧 Starting installation..."
echo ""

# Step 1: Update system
echo "📦 Step 1/5: Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Step 2: Install Python dependencies
echo "🐍 Step 2/5: Installing Python dependencies..."
sudo apt install -y python3 python3-pip python3-venv git

# Step 3: Create virtual environment
echo "🔧 Step 3/5: Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Setup systemd service
echo "⚙️  Step 4/5: Setting up systemd service..."
sudo cp family-center.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable family-center.service

# Step 5: Configure firewall
echo "🛡️  Step 5/5: Configuring firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8080/tcp
sudo ufw --force enable

echo ""
echo "✅ Installation complete!"
echo ""
echo "🎉 Family Center has been installed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Start the service: sudo systemctl start family-center"
echo "   2. Access web interface: http://$(hostname -I | awk '{print $1}'):8080"
echo "   3. Upload Google Drive credentials via the web interface"
echo "   4. Configure your settings"
echo ""
echo "🔧 Management commands:"
echo "   - Check status: sudo systemctl status family-center"
echo "   - View logs: sudo journalctl -u family-center -f"
echo "   - Restart: sudo systemctl restart family-center"
echo ""
EOF

chmod +x install.sh

print_success "Created installation script"

# Create .gitignore
print_status "Creating .gitignore..."

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/

# Credentials (security)
credentials/*.json
*.key
*.pem

# Logs
logs/
*.log

# Media
media/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
EOF

print_success "Created .gitignore"

# Clean up temporary directory
rm -rf "$TEMP_DIR"

# Check git status
print_status "Checking git status..."
cd "$FAMILY_CENTER_DIR"

if git status --porcelain | grep -q .; then
    print_status "Changes detected. Would you like to commit them?"
    read -p "Commit changes to family-center repository? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "Sync improvements from installer

- Enhanced web interface with credential management
- Improved error handling and user experience
- Complete application framework
- Systemd service configuration
- Installation script
- Enhanced documentation
- Proper directory structure
- Security improvements"
        
        print_success "Changes committed to family-center repository"
        
        read -p "Push changes to remote repository? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push origin main
            print_success "Changes pushed to remote repository"
        fi
    fi
else
    print_warning "No changes detected in family-center repository"
fi

echo ""
print_success "Integration complete!"
echo ""
echo "📋 Summary:"
echo "   ✅ Extracted all application files from installer"
echo "   ✅ Applied files to family-center repository"
echo "   ✅ Created enhanced README"
echo "   ✅ Created systemd service file"
echo "   ✅ Created installation script"
echo "   ✅ Created .gitignore"
echo "   ✅ Backup created at: $BACKUP_DIR"
echo ""
echo "🎯 Next steps:"
echo "   1. Review the changes in the family-center repository"
echo "   2. Test the installation process"
echo "   3. Update any additional documentation as needed"
echo "" 