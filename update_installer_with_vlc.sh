#!/bin/bash

# Family Center Installer Update Script
# Updates the installer package with latest Family Center code including VLC engine

set -e

echo "🔄 Family Center Installer Update Script"
echo "======================================="
echo ""
echo "This script will update the installer package with the latest Family Center code"
echo "including the new VLC slideshow engine improvements"
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
if [ ! -d "family_center_package" ]; then
    print_error "This script must be run from the family_center_installer directory"
    exit 1
fi

# Check if family-center repository exists
FAMILY_CENTER_DIR="../family_center"
if [ ! -d "$FAMILY_CENTER_DIR" ]; then
    print_error "Family Center repository not found at $FAMILY_CENTER_DIR"
    print_error "Please ensure the family_center repository is in the parent directory"
    exit 1
fi

print_status "Found Family Center repository at $FAMILY_CENTER_DIR"

# Create backup of current package
BACKUP_DIR="family_center_package_backup_$(date +%Y%m%d_%H%M%S)"
print_status "Creating backup of current package as $BACKUP_DIR"
cp -r family_center_package "$BACKUP_DIR"

print_success "Backup created successfully"

# Update source code
print_status "Updating source code from Family Center repository..."

# Copy main source files
cp -r "$FAMILY_CENTER_DIR/src/"* family_center_package/src/

# Copy configuration files
cp "$FAMILY_CENTER_DIR/src/config/config.yaml" family_center_package/src/config/
cp "$FAMILY_CENTER_DIR/requirements.txt" family_center_package/

# Copy documentation
cp "$FAMILY_CENTER_DIR/README.md" family_center_package/
cp "$FAMILY_CENTER_DIR/docs/project_notes.md" family_center_package/

# Copy additional files
cp "$FAMILY_CENTER_DIR/pyproject.toml" family_center_package/ 2>/dev/null || print_warning "pyproject.toml not found"
cp "$FAMILY_CENTER_DIR/mypy.ini" family_center_package/ 2>/dev/null || print_warning "mypy.ini not found"
cp "$FAMILY_CENTER_DIR/.isort.cfg" family_center_package/ 2>/dev/null || print_warning ".isort.cfg not found"

print_success "Source code updated successfully"

# Update requirements.txt with VLC dependencies
print_status "Updating requirements.txt with VLC dependencies..."

# Check if python-vlc is already in requirements
if ! grep -q "python-vlc" family_center_package/requirements.txt; then
    echo "python-vlc>=3.0.20000" >> family_center_package/requirements.txt
    print_success "Added python-vlc dependency"
else
    print_status "python-vlc dependency already present"
fi

# Create a version file
echo "v6.6-VLC-$(date +%Y%m%d)" > family_center_package/VERSION

print_success "Version file created"

# Summary
echo ""
print_success "🎉 Family Center Installer Updated Successfully!"
echo ""
print_status "Updated components:"
echo "  ✅ Source code (including VLC engine)"
echo "  ✅ Configuration files"
echo "  ✅ Requirements (with VLC dependencies)"
echo "  ✅ Documentation"
echo ""
print_status "Backup created: $BACKUP_DIR"
print_status "Version: $(cat family_center_package/VERSION)"
echo ""
print_status "Next steps:"
echo "  1. Test the updated installer"
echo "  2. Commit changes to repository"
echo "  3. Update installer scripts if needed"
echo ""
