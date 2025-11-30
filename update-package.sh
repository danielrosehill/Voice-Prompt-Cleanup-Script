#!/bin/bash
#
# Update script for Voice Prompt Cleanup
#
# This script pulls the latest changes from the repository,
# rebuilds the Debian package, and installs it.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PACKAGE_NAME="voice-prompt-cleanup"

echo "Voice Prompt Cleanup - Update Script"
echo "====================================="
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "Error: Not a git repository. Please run from the project root."
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "Warning: You have uncommitted changes."
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Fetch and pull latest changes
echo "Fetching latest changes..."
git fetch origin

# Get current and remote commit hashes
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")

if [ -z "$REMOTE" ]; then
    echo "No upstream branch configured. Proceeding with local build."
elif [ "$LOCAL" = "$REMOTE" ]; then
    echo "Already up to date."
    read -p "Rebuild anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    echo "Updates available. Pulling..."
    git pull
fi

echo ""
echo "Building package..."
echo ""

# Run the build script
bash ./build-deb.sh

# Get the built package path
VERSION=$(head -1 debian/changelog | sed -n 's/.*(\([^)]*\)).*/\1/p')
DEB_FILE="build/${PACKAGE_NAME}_${VERSION}.deb"

if [ ! -f "$DEB_FILE" ]; then
    echo "Error: Built package not found at $DEB_FILE"
    exit 1
fi

echo ""
echo "Installing package..."
echo ""

# Install the package
sudo apt install "./$DEB_FILE"

echo ""
echo "====================================="
echo "Update complete!"
echo ""
echo "Installed version: ${VERSION}"
echo ""
echo "You can launch the application from:"
echo "  - Application menu: Voice Prompt Cleanup"
echo "  - Terminal: voice-prompt-cleanup"
