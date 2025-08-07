# Family Center Installer

🍓 **One-command installation for Family Center on Raspberry Pi 5, 4, and 3B+**

## 🚀 Quick Install

For a fresh Raspberry Pi with the latest Raspberry Pi OS:

```bash
curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install.sh | bash
```

## What gets installed?

- ✅ **Family Center Application** - Digital photo frame and home dashboard
- ✅ **All system dependencies** - Optimized for your Pi model
- ✅ **Python environment** - Isolated virtual environment with all packages
- ✅ **System service** - Auto-start on boot
- ✅ **Web configuration** - Easy setup via browser at `http://YOUR_PI_IP:8080/config`
- ✅ **Security** - Basic firewall configuration

## Supported Devices

- **Raspberry Pi 5** (recommended) - Fastest performance, Wi-Fi 6
- **Raspberry Pi 4** - Excellent performance for all features  
- **Raspberry Pi 3B+** - Good performance for basic slideshow

## Requirements

- Fresh installation of **Raspberry Pi OS** (Bookworm or newer)
- Internet connection (Wi-Fi or Ethernet)
- MicroSD card (16GB+ recommended)
- Display connected via HDMI

## What is Family Center?

Family Center transforms your Raspberry Pi into a beautiful digital photo frame and family dashboard that displays:

- 📸 **Photos from Google Drive** - Automatically synced family photos
- 📅 **Calendar events** - Upcoming family activities and appointments  
- 🌤️ **Weather information** - Local weather and forecasts
- 📰 **News and web content** - Customizable content feeds
- 🎬 **Videos** - Family videos and memories

## After Installation

1. **Access web config**: `http://YOUR_PI_IP:8080/config`
2. **Add Google Drive credentials** to sync your photos
3. **Configure your preferences** through the web interface
4. **Start the slideshow**: `sudo systemctl start family-center`

## Manual Installation

If you prefer to install manually or want to see what the script does:

```bash
# Clone this repository
git clone https://github.com/themaddog1068/family_center_installer.git
cd family_center_installer

# Run the installer
chmod +x install.sh
./install.sh
```

## Troubleshooting

### Installation Issues
```bash
# Check system logs
sudo journalctl -u family-center -f

# Restart the service
sudo systemctl restart family-center

# Check service status
sudo systemctl status family-center
```

### Web Interface Not Accessible
```bash
# Check if service is running
sudo netstat -tlnp | grep 8080

# Check firewall
sudo ufw status

# Get your Pi's IP address
hostname -I
```

## Support

- **Documentation**: Full setup guide in the main repository
- **Issues**: Report problems via GitHub issues
- **Updates**: `cd /home/pi/family_center && git pull && sudo systemctl restart family-center`

## Security Notes

- The installer sets up a basic firewall with UFW
- Only necessary ports are opened (SSH: 22, Web UI: 8080)
- Application runs as the `pi` user (not root)
- Regular system updates are recommended

---

**Made with ❤️ for families who want to stay connected through shared memories**
