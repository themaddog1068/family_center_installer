#!/bin/bash

# Family Center Setup Script
# This script starts the web configuration interface for easy setup

echo "🌐 Family Center Setup"
echo "====================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if start_web_ui.py exists
if [ ! -f "start_web_ui.py" ]; then
    echo "❌ start_web_ui.py not found. Please ensure the application is properly installed."
    exit 1
fi

echo ""
echo "🚀 Starting Web Configuration Interface..."
echo "📱 Open your web browser to: http://localhost:8080"
echo ""
echo "The web interface will help you:"
echo "  • Upload Google Drive credentials"
echo "  • Configure Google Drive folder settings"
echo "  • Set up calendar integration"
echo "  • Configure weather settings"
echo "  • Adjust slideshow parameters"
echo "  • Test all connections"
echo ""
echo "Press Ctrl+C to stop the web interface"
echo ""

# Start the web configuration interface
python start_web_ui.py
