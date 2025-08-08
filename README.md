# Family Center Installer

🍓 **One-command installation for Family Center on Raspberry Pi 5, 4, and 3B+**

## 📦 Available Versions

- **Version 4** - Full installer with private repository access
- **Version -5 (Pre-Alpha)** - Self-contained installer with embedded application files

## 🚀 Quick Install

### Version 4 (Full Installer)
For a fresh Raspberry Pi with the latest Raspberry Pi OS:

```bash
curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install.sh | bash
```

### Version -5 (Pre-Alpha - Self-Contained)
For a self-contained installation with embedded application files:

```bash
curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install_v-5.sh | bash
```

**Note: Version -5 is a pre-alpha release with basic framework functionality.**

## 🔐 Repository Access

**Important**: The Family Center repository is private and requires authentication. The installer will guide you through the setup process with three options:

1. **SSH Key Authentication** (Recommended)
   - Add your SSH key to your GitHub account
   - The installer will clone via SSH automatically

2. **HTTPS with Personal Access Token**
   - Create a personal access token on GitHub
   - Use it when prompted for password

3. **Manual Setup**
   - Clone the repository manually after installation
   - Place it in `/home/pi/family_center`

## What gets installed?

- ✅ **Family Center Application** - Digital photo frame and home dashboard
- ✅ **All system dependencies** - Optimized for your Pi model
- ✅ **Python environment** - Isolated virtual environment with all packages
- ✅ **System service** - Auto-start on boot
- ✅ **Web configuration** - Easy setup via browser at `http://YOUR_PI_IP:8080/config`
- ✅ **Security** - Basic firewall configuration
- ✅ **Error handling** - Robust installation with fallback options

## Supported Devices

- **Raspberry Pi 5** (recommended) - Fastest performance, Wi-Fi 6
- **Raspberry Pi 4** - Excellent performance for all features  
- **Raspberry Pi 3B+** - Good performance for basic slideshow

## Requirements

- Fresh installation of **Raspberry Pi OS** (Bookworm or newer)
- Internet connection (Wi-Fi or Ethernet)
- MicroSD card (16GB+ recommended)
- Display connected via HDMI
- **GitHub access** to the private Family Center repository

## What is Family Center?

Family Center transforms your Raspberry Pi into a beautiful digital photo frame and family dashboard that displays:

- 📸 **Photos from Google Drive** - Automatically synced family photos
- 📅 **Calendar events** - Upcoming family activities and appointments  
- 🌤️ **Weather information** - Local weather and forecasts
- 📰 **News and web content** - Customizable content feeds
- 🎬 **Videos** - Family videos and memories

## Installation Process

The installer now includes 7 steps with improved error handling:

1. **System Updates** - Updates all packages
2. **Dependencies** - Installs required system libraries
3. **Repository Setup** - Handles private repository access
4. **Structure Verification** - Validates repository contents
5. **Python Environment** - Creates virtual environment
6. **Configuration** - Sets up directories and config files
7. **System Service** - Configures auto-start service

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

### Repository Access Issues
```bash
# Check SSH key setup
ssh -T git@github.com

# Add SSH key to agent
ssh-add ~/.ssh/id_rsa

# Test repository access
git ls-remote git@github.com:themaddog1068/family_center.git
```

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

### Manual Repository Setup
If the installer can't access the repository, you can set it up manually:

```bash
# Create directory
mkdir -p /home/pi/family_center
cd /home/pi/family_center

# Clone manually (replace with your preferred method)
git clone git@github.com:themaddog1068/family_center.git .

# Then run the installer again
cd /home/pi/family_center_installer
./install.sh
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
- Private repository access is handled securely

## Recent Improvements

- ✅ **Private repository support** - Handles authentication gracefully
- ✅ **Better error handling** - Provides clear guidance for issues
- ✅ **Repository validation** - Checks for correct file structure
- ✅ **Fallback options** - Multiple ways to handle repository access
- ✅ **Improved user experience** - Clear prompts and status messages

---

**Made with ❤️ for families who want to stay connected through shared memories**
