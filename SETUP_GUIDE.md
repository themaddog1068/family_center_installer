# Family Center Setup Guide

This guide helps you set up authentication for the private Family Center repository.

## 🔑 SSH Key Authentication (Recommended)

### Step 1: Generate SSH Key
```bash
# Generate a new SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Or use RSA (if ed25519 is not supported)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### Step 2: Add SSH Key to SSH Agent
```bash
# Start the SSH agent
eval "$(ssh-agent -s)"

# Add your SSH key
ssh-add ~/.ssh/id_ed25519
# or for RSA: ssh-add ~/.ssh/id_rsa
```

### Step 3: Add SSH Key to GitHub
1. Copy your public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   # or for RSA: cat ~/.ssh/id_rsa.pub
   ```

2. Go to GitHub Settings → SSH and GPG keys → New SSH key
3. Paste your public key and save

### Step 4: Test SSH Connection
```bash
ssh -T git@github.com
```

You should see: "Hi username! You've successfully authenticated..."

## 🔐 Personal Access Token Authentication

### Step 1: Create Personal Access Token
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (Full control of private repositories)
   - `read:org` (if needed for organization repos)
4. Copy the token (you won't see it again!)

### Step 2: Use Token During Installation
When the installer prompts for password, use your personal access token instead of your GitHub password.

## 🚀 Running the Installer

### Option 1: One-command Install
```bash
curl -sSL https://raw.githubusercontent.com/themaddog1068/family_center_installer/main/install.sh | bash
```

### Option 2: Manual Install
```bash
# Clone the installer
git clone https://github.com/themaddog1068/family_center_installer.git
cd family_center_installer

# Run the installer
chmod +x install.sh
./install.sh
```

## 🔧 Troubleshooting

### SSH Issues
```bash
# Check SSH agent
ssh-add -l

# Test GitHub connection
ssh -T git@github.com

# Check SSH key permissions
ls -la ~/.ssh/
# Keys should be 600, public keys should be 644
```

### Token Issues
- Ensure token has `repo` scope
- Token expires after 90 days (classic) or set expiration
- Use token as password, not username

### Repository Access Issues
```bash
# Test repository access
git ls-remote git@github.com:themaddog1068/family_center.git

# Or with HTTPS
git ls-remote https://github.com/themaddog1068/family_center.git
```

### Manual Repository Setup
If authentication fails, you can set up manually:

```bash
# Create directory
mkdir -p /home/pi/family_center
cd /home/pi/family_center

# Clone with your preferred method
git clone git@github.com:themaddog1068/family_center.git .
# or
git clone https://github.com/themaddog1068/family_center.git .

# Then run installer again
cd /home/pi/family_center_installer
./install.sh
```

## 📋 Pre-Installation Checklist

- [ ] Raspberry Pi OS installed and updated
- [ ] Internet connection working
- [ ] SSH key added to GitHub (or personal access token ready)
- [ ] Access to Family Center repository confirmed
- [ ] Display connected via HDMI
- [ ] MicroSD card has sufficient space (16GB+ recommended)

## 🎯 Post-Installation

After successful installation:

1. **Access web interface**: `http://YOUR_PI_IP:8080/config`
2. **Add Google Drive credentials** to `/home/pi/family_center/credentials/`
3. **Configure settings** through the web interface
4. **Start the service**: `sudo systemctl start family-center`

## 🆘 Need Help?

- Check the main README.md for troubleshooting
- Verify your GitHub access permissions
- Ensure your Raspberry Pi meets the requirements
- Check system logs: `sudo journalctl -u family-center -f` 