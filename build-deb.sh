#!/bin/bash
#
# Build and install script for Voice Prompt Cleanup Debian package
#
# This script builds the .deb package from the source and installs it.
# Run from the project root directory.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get version from changelog
VERSION=$(head -1 debian/changelog | sed -n 's/.*(\([^)]*\)).*/\1/p')
PACKAGE_NAME="voice-prompt-cleanup"

echo "Voice Prompt Cleanup - Build & Install"
echo "======================================="
echo "Version: ${VERSION}"
echo ""

# Check for required tools
if ! command -v dpkg-deb &> /dev/null; then
    echo "Error: dpkg-deb not found. Install with: sudo apt install dpkg-dev"
    exit 1
fi

# Clean previous build
rm -rf build/
mkdir -p build/${PACKAGE_NAME}_${VERSION}

BUILD_DIR="build/${PACKAGE_NAME}_${VERSION}"

# Create directory structure
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/${PACKAGE_NAME}"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps"

# Copy files
cp process_audio.sh "${BUILD_DIR}/usr/share/${PACKAGE_NAME}/"
cp voice_prompt_cleanup_gui.py "${BUILD_DIR}/usr/share/${PACKAGE_NAME}/"
cp debian/voice-prompt-cleanup.sh "${BUILD_DIR}/usr/bin/voice-prompt-cleanup"
cp debian/voice-prompt-cleanup.desktop "${BUILD_DIR}/usr/share/applications/"
cp debian/voice-prompt-cleanup.svg "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/"

# Set permissions
chmod 755 "${BUILD_DIR}/usr/share/${PACKAGE_NAME}/process_audio.sh"
chmod 755 "${BUILD_DIR}/usr/share/${PACKAGE_NAME}/voice_prompt_cleanup_gui.py"
chmod 755 "${BUILD_DIR}/usr/bin/voice-prompt-cleanup"

# Create control file
cat > "${BUILD_DIR}/DEBIAN/control" << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: sound
Priority: optional
Architecture: all
Depends: python3, python3-pyqt6, ffmpeg
Maintainer: Daniel Rosehill <public@danielrosehill.com>
Homepage: https://github.com/danielrosehill/Voice-Prompt-Cleanup-Script
Description: Audio preprocessing GUI for speech-to-text workflows
 Voice Prompt Cleanup is a GUI application that processes audio files
 to optimize them for speech-to-text (STT) workflows. It applies:
 .
  - Mono conversion and downsampling to 16kHz
  - Speech EQ (80Hz-8kHz bandpass filter)
  - Gentle compression for even dynamics
  - Silence truncation
  - Audio normalization
  - MP3 encoding
 .
 Features include batch processing, drag-and-drop support, and
 persistent output folder settings.
EOF

# Create postinst script (update icon cache)
cat > "${BUILD_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e
if [ -x /usr/bin/update-icon-caches ]; then
    update-icon-caches /usr/share/icons/hicolor || true
fi
if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database /usr/share/applications || true
fi
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

# Build the package
echo ""
echo "Building package..."
dpkg-deb --build --root-owner-group "${BUILD_DIR}"

# Package is already created in build/ directory by dpkg-deb
DEB_FILE="build/${PACKAGE_NAME}_${VERSION}.deb"

echo ""
echo "Build complete: ${DEB_FILE}"
echo ""

# Install the package
echo "Installing package..."
sudo apt install "./${DEB_FILE}"

echo ""
echo "======================================="
echo "Installation complete!"
echo ""
echo "Launch from:"
echo "  - Application menu: Voice Prompt Cleanup"
echo "  - Terminal: voice-prompt-cleanup"
