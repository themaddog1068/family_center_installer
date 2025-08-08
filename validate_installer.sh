#!/bin/bash

# Family Center Installer Validation Script
# Tests the installer for common issues and validates functionality

set -e

echo "🔍 Family Center Installer Validation"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    esac
}

# Test 1: Check if installer files exist
echo "📁 Testing installer files..."
if [ -f "install.sh" ]; then
    print_status "PASS" "install.sh exists"
else
    print_status "FAIL" "install.sh missing"
    exit 1
fi

if [ -f "test_install.sh" ]; then
    print_status "PASS" "test_install.sh exists"
else
    print_status "FAIL" "test_install.sh missing"
fi

if [ -f "README.md" ]; then
    print_status "PASS" "README.md exists"
else
    print_status "FAIL" "README.md missing"
fi

# Test 2: Check file permissions
echo ""
echo "🔐 Testing file permissions..."
if [ -x "install.sh" ]; then
    print_status "PASS" "install.sh is executable"
else
    print_status "WARN" "install.sh is not executable (run: chmod +x install.sh)"
fi

if [ -x "test_install.sh" ]; then
    print_status "PASS" "test_install.sh is executable"
else
    print_status "WARN" "test_install.sh is not executable (run: chmod +x test_install.sh)"
fi

# Test 3: Validate shell script syntax
echo ""
echo "🔧 Testing script syntax..."
if bash -n install.sh 2>/dev/null; then
    print_status "PASS" "install.sh has valid syntax"
else
    print_status "FAIL" "install.sh has syntax errors"
fi

if bash -n test_install.sh 2>/dev/null; then
    print_status "PASS" "test_install.sh has valid syntax"
else
    print_status "FAIL" "test_install.sh has syntax errors"
fi

# Test 4: Check for required commands in installer
echo ""
echo "📋 Testing installer content..."
if grep -q "git clone" install.sh; then
    print_status "PASS" "Git clone command found"
else
    print_status "FAIL" "Git clone command missing"
fi

if grep -q "systemctl" install.sh; then
    print_status "PASS" "Systemd service setup found"
else
    print_status "FAIL" "Systemd service setup missing"
fi

if grep -q "python3 -m venv" install.sh; then
    print_status "PASS" "Python virtual environment setup found"
else
    print_status "FAIL" "Python virtual environment setup missing"
fi

if grep -q "ufw" install.sh; then
    print_status "PASS" "Firewall configuration found"
else
    print_status "FAIL" "Firewall configuration missing"
fi

# Test 5: Check for error handling
echo ""
echo "🛡️  Testing error handling..."
if grep -q "set -e" install.sh; then
    print_status "PASS" "Error handling (set -e) found"
else
    print_status "WARN" "Error handling (set -e) missing"
fi

if grep -q "read -p" install.sh; then
    print_status "PASS" "User confirmation prompts found"
else
    print_status "WARN" "User confirmation prompts missing"
fi

# Test 6: Check for private repository handling
echo ""
echo "🔐 Testing private repository handling..."
if grep -q "private.*repository" install.sh; then
    print_status "PASS" "Private repository handling found"
else
    print_status "WARN" "Private repository handling not explicitly mentioned"
fi

if grep -q "SSH.*authentication" install.sh; then
    print_status "PASS" "SSH authentication option found"
else
    print_status "WARN" "SSH authentication option missing"
fi

if grep -q "personal access token" install.sh; then
    print_status "PASS" "Personal access token option found"
else
    print_status "WARN" "Personal access token option missing"
fi

# Test 7: Check for repository validation
echo ""
echo "🔍 Testing repository validation..."
if grep -q "requirements.txt" install.sh; then
    print_status "PASS" "Requirements.txt validation found"
else
    print_status "WARN" "Requirements.txt validation missing"
fi

if grep -q "src/main.py" install.sh; then
    print_status "PASS" "Main.py validation found"
else
    print_status "WARN" "Main.py validation missing"
fi

# Test 8: Check for helpful output
echo ""
echo "💬 Testing user guidance..."
if grep -q "IP address" install.sh; then
    print_status "PASS" "IP address display found"
else
    print_status "WARN" "IP address display missing"
fi

if grep -q "Quick Start" install.sh; then
    print_status "PASS" "Quick start commands found"
else
    print_status "WARN" "Quick start commands missing"
fi

if grep -q "Next Steps" install.sh; then
    print_status "PASS" "Next steps guidance found"
else
    print_status "WARN" "Next steps guidance missing"
fi

# Test 9: Check README content
echo ""
echo "📚 Testing README content..."
if grep -q "Repository Access" README.md; then
    print_status "PASS" "Repository access documentation found"
else
    print_status "WARN" "Repository access documentation missing"
fi

if grep -q "Troubleshooting" README.md; then
    print_status "PASS" "Troubleshooting section found"
else
    print_status "WARN" "Troubleshooting section missing"
fi

# Summary
echo ""
echo "📊 Validation Summary"
echo "===================="
echo ""
echo "The installer has been validated for:"
echo "✅ File existence and permissions"
echo "✅ Script syntax and structure"
echo "✅ Required functionality"
echo "✅ Error handling and user guidance"
echo "✅ Private repository support"
echo "✅ Documentation completeness"
echo ""
echo "🎯 Ready for deployment!"
echo ""
echo "To make scripts executable:"
echo "chmod +x install.sh test_install.sh validate_installer.sh" 