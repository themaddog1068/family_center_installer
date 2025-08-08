# Family Center Installer - Version -5 (Pre-Alpha)

🍓 **Self-contained installer with embedded application files**

## 🚀 What's New in Version -5

Version -5 is a **pre-alpha release** that eliminates the need for external repository access by embedding the necessary Family Center application files directly into the installer. This is a foundational framework that provides the basic structure for the Family Center application.

### ✨ Key Benefits

- ✅ **No external repository access required**
- ✅ **Faster installation** (10-15 minutes vs 15-25 minutes)
- ✅ **More reliable** - no authentication issues
- ✅ **Self-contained** - everything needed is included
- ✅ **Simplified setup** - fewer steps and dependencies
- ✅ **Better user experience** - works out of the box

## 🚀 Quick Install

For a fresh Raspberry Pi with the latest Raspberry Pi OS:

```bash
curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install_v-5.sh | bash
```

**⚠️ Note: This is a pre-alpha release. The application provides a basic framework and web interface, but full functionality is still in development.**

## 📦 What's Included

Version -5 includes a **basic Family Center application framework** with:

- 🐍 **Python Application Structure**
  - Main application entry point (`src/main.py`)
  - Modular architecture (`src/modules/`)
  - Configuration management (`src/utils/`)
  - Web interface framework

- 📋 **Dependencies**
  - Flask web framework
  - OpenCV for image processing
  - Google API clients
  - Weather and news services
  - All required Python packages

- ⚙️ **Configuration**
  - Default configuration files
  - Web interface setup
  - Service configuration

- 🔧 **System Integration**
  - Systemd service setup
  - Firewall configuration
  - Auto-start on boot

## 🏗️ Application Architecture

```
family_center/
├── src/
│   ├── main.py              # Main application entry point
│   ├── config/
│   │   └── config.yaml      # Configuration file
│   ├── modules/
│   │   ├── web_interface.py # Web UI and API
│   │   ├── photo_manager.py # Google Drive photo sync
│   │   ├── weather_service.py # Weather information
│   │   ├── news_service.py  # News feeds
│   │   └── calendar_service.py # Calendar integration
│   └── utils/
│       └── config_manager.py # Configuration management
├── media/                   # Media directories
├── credentials/             # Google Drive credentials
├── logs/                    # Application logs
├── venv/                    # Python virtual environment
└── requirements.txt         # Python dependencies
```

## 🔧 Installation Process

Version -5 uses a streamlined 6-step process:

1. **System Updates** - Updates all packages
2. **Dependencies** - Installs required system libraries
3. **Application Setup** - Creates directory structure and embedded files
4. **File Creation** - Generates all necessary application files
5. **Python Environment** - Sets up virtual environment and dependencies
6. **System Service** - Configures auto-start service

## 🌐 Web Interface

After installation, access the web interface at:
```
http://YOUR_PI_IP:8080/config
```

The web interface provides:
- 📊 **Status Dashboard** - System status and service health
- ⚙️ **Configuration Panel** - Easy settings management
- 📸 **Photo Management** - Google Drive integration setup
- 🌤️ **Weather Configuration** - Location and API key setup
- 📰 **News Sources** - Customizable news feeds
- 📅 **Calendar Setup** - Event integration

## 🚀 Quick Start

1. **Run the installer**:
   ```bash
   curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install_v5.sh | bash
   ```

2. **Access web interface**:
   ```bash
   http://YOUR_PI_IP:8080/config
   ```

3. **Add Google Drive credentials** to `/home/pi/family_center/credentials/`

4. **Configure settings** through the web interface

5. **Start the service**:
   ```bash
   sudo systemctl start family-center
   ```

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

# Test web interface only
cd /home/pi/family_center
source venv/bin/activate
python3 src/main.py --web-only
```

## 🆚 Version Comparison

| Feature | Version 4 | Version -5 (Pre-Alpha) |
|---------|-----------|----------------------|
| External Repository | Required | Not needed |
| Installation Time | 15-25 min | 10-15 min |
| Authentication | SSH/Token required | None |
| Reliability | Depends on repo access | High |
| Setup Complexity | Medium | Low |
| User Experience | Good | Basic Framework |
| Functionality | Full | Basic |

## 🔄 Updating

To update to a newer version:

```bash
# Download and run the latest installer
curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install_v-5.sh | bash
```

The installer will automatically backup your existing installation.

## 🛠️ Development

Version -5 is designed to be easily extensible and serves as a foundation for future development:

- **Add new modules** in `src/modules/`
- **Modify configuration** in `src/config/config.yaml`
- **Update dependencies** in `requirements.txt`
- **Enhance web interface** in `src/modules/web_interface.py`

## 🆘 Troubleshooting

### Web Interface Not Accessible
```bash
# Check service status
sudo systemctl status family-center

# Check if port is listening
sudo netstat -tlnp | grep 8080

# Check firewall
sudo ufw status
```

### Service Won't Start
```bash
# Check logs
sudo journalctl -u family-center -f

# Test manually
cd /home/pi/family_center
source venv/bin/activate
python3 src/main.py --web-only
```

### Configuration Issues
```bash
# Check config file
cat /home/pi/family_center/src/config/config.yaml

# Reset to defaults
cp /home/pi/family_center/src/config/config.yaml.example /home/pi/family_center/src/config/config.yaml
```

## 📋 Requirements

- **Raspberry Pi OS** (Bookworm or newer)
- **Internet connection** (Wi-Fi or Ethernet)
- **MicroSD card** (16GB+ recommended)
- **Display** connected via HDMI

## 🎯 Supported Devices

- **Raspberry Pi 5** (recommended) - Fastest performance
- **Raspberry Pi 4** - Excellent performance
- **Raspberry Pi 3B+** - Good performance

---

**Version -5 (Pre-Alpha) - Foundation for Family Center** 🚀

*Self-contained framework for future development* 