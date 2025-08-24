#!/bin/bash

# Family Center Slideshow Runner
# This script activates the virtual environment and runs the slideshow

echo "🎬 Starting Family Center Slideshow..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if main.py exists
if [ ! -f "src/main.py" ]; then
    echo "❌ main.py not found. Please ensure the application is properly installed."
    exit 1
fi

# Run the application
echo "🚀 Starting slideshow..."
python src/main.py "$@"
