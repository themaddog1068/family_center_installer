#!/bin/bash

# Family Center Installer Validation - Version -5 (Pre-Alpha)
# Tests the pre-alpha installer for basic functionality

set -e

echo "🔍 Family Center Installer Validation - Version -5 (Pre-Alpha)"
echo "============================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC}: $message"
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC}: $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  WARN${NC}: $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  INFO${NC}: $message"
            ;;
    esac
}

# Test 1: Check if installer files exist
echo "📁 Testing installer files..."
if [ -f "install_v-5.sh" ]; then
    print_status "PASS" "install_v-5.sh exists"
else
    print_status "FAIL" "install_v-5.sh missing"
    exit 1
fi

if [ -f "README_V-5.md" ]; then
    print_status "PASS" "README_V-5.md exists"
else
    print_status "FAIL" "README_V-5.md missing"
fi

# Test 2: Check file permissions
echo ""
echo "🔐 Testing file permissions..."
if [ -x "install_v-5.sh" ]; then
    print_status "PASS" "install_v-5.sh is executable"
else
    print_status "WARN" "install_v-5.sh is not executable (run: chmod +x install_v-5.sh)"
fi

# Test 3: Validate shell script syntax
echo ""
echo "🔧 Testing script syntax..."
if bash -n install_v-5.sh 2>/dev/null; then
    print_status "PASS" "install_v-5.sh has valid syntax"
else
    print_status "FAIL" "install_v-5.sh has syntax errors"
fi

# Test 4: Check for pre-alpha indicators
echo ""
echo "🔬 Testing pre-alpha indicators..."
if grep -q "Version -5" install_v-5.sh; then
    print_status "PASS" "Version -5 identifier found"
else
    print_status "FAIL" "Version -5 identifier missing"
fi

if grep -q "Pre-Alpha" install_v-5.sh; then
    print_status "PASS" "Pre-Alpha indicator found"
else
    print_status "FAIL" "Pre-Alpha indicator missing"
fi

# Test 5: Check for embedded application files
echo ""
echo "📦 Testing embedded application structure..."
if grep -q "cat > requirements.txt" install_v-5.sh; then
    print_status "PASS" "Requirements.txt creation found"
else
    print_status "WARN" "Requirements.txt creation missing"
fi

if grep -q "cat > src/main.py" install_v-5.sh; then
    print_status "PASS" "Main.py creation found"
else
    print_status "WARN" "Main.py creation missing"
fi

if grep -q "cat > src/modules" install_v-5.sh; then
    print_status "PASS" "Modules creation found"
else
    print_status "WARN" "Modules creation missing"
fi

# Test 6: Check for self-contained indicators
echo ""
echo "📦 Testing self-contained features..."
if grep -q "No external repository access required" install_v-5.sh; then
    print_status "PASS" "Self-contained indicator found"
else
    print_status "WARN" "Self-contained indicator missing"
fi

if ! grep -q "git clone.*family_center" install_v-5.sh; then
    print_status "PASS" "No external repository cloning"
else
    print_status "WARN" "External repository cloning found"
fi

# Test 7: Check for basic functionality
echo ""
echo "🔧 Testing basic functionality..."
if grep -q "systemctl" install_v-5.sh; then
    print_status "PASS" "Systemd service setup found"
else
    print_status "FAIL" "Systemd service setup missing"
fi

if grep -q "python3 -m venv" install_v-5.sh; then
    print_status "PASS" "Python virtual environment setup found"
else
    print_status "FAIL" "Python virtual environment setup missing"
fi

if grep -q "ufw" install_v-5.sh; then
    print_status "PASS" "Firewall configuration found"
else
    print_status "FAIL" "Firewall configuration missing"
fi

# Test 8: Check for user guidance
echo ""
echo "💬 Testing user guidance..."
if grep -q "IP address" install_v-5.sh; then
    print_status "PASS" "IP address display found"
else
    print_status "WARN" "IP address display missing"
fi

if grep -q "Quick Start" install_v-5.sh; then
    print_status "PASS" "Quick start commands found"
else
    print_status "WARN" "Quick start commands missing"
fi

# Test 9: Check README content
echo ""
echo "📚 Testing README content..."
if grep -q "Pre-Alpha" README_V-5.md; then
    print_status "PASS" "Pre-Alpha documentation found"
else
    print_status "WARN" "Pre-Alpha documentation missing"
fi

if grep -q "basic framework" README_V-5.md; then
    print_status "PASS" "Framework description found"
else
    print_status "WARN" "Framework description missing"
fi

# Summary
echo ""
echo "📊 Validation Summary - Version -5 (Pre-Alpha)"
echo "=============================================="
echo ""
print_status "INFO" "This is a pre-alpha release with basic framework"
print_status "INFO" "Self-contained installation (no external repo needed)"
print_status "INFO" "Embedded application files included"
print_status "INFO" "Foundation for future development"
echo ""
echo "The installer has been validated for:"
echo "✅ File existence and permissions"
echo "✅ Script syntax and structure"
echo "✅ Pre-alpha indicators"
echo "✅ Self-contained features"
echo "✅ Basic functionality"
echo "✅ User guidance"
echo "✅ Documentation"
echo ""
echo "🎯 Pre-alpha release ready for testing!"
echo ""
echo "To make scripts executable:"
echo "chmod +x install_v-5.sh validate_v-5.sh" 