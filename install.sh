#!/bin/bash

# Family Center Slideshow Installer
# This script sets up the environment and installs dependencies

set -e

echo "🚀 Family Center Slideshow Installer"
echo "====================================="

# Check if Python 3.8+ is installed
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p media/remote_drive
mkdir -p media/Calendar
mkdir -p media/Weather
mkdir -p logs
mkdir -p credentials

# Set permissions
echo "🔐 Setting permissions..."
chmod 755 media logs credentials

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Copy your Google service account JSON to credentials/service-account.json"
echo "2. Edit config/config.yaml to configure your settings"
echo "3. Run: source venv/bin/activate && python src/main.py"
echo ""
echo "For more information, see README.md"
