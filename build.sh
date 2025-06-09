#!/bin/bash

# This script builds the application by copying all browsers and then
# explicitly removing the unneeded ones to reduce app size.

# Stop the script if any command fails
set -e

# --- Configuration ---
APP_NAME="markdown2png"
SOURCE_BROWSERS_PATH="$HOME/Library/Caches/ms-playwright"
FINAL_APP_PATH="dist/$APP_NAME.app"

# --- Main Build Logic ---

echo "--- Step 1: Cleaning up previous build artifacts ---"
rm -rf build "$FINAL_APP_PATH" *.spec

echo ""
echo "--- Step 2: Building the core application with PyInstaller ---"
pyinstaller \
    --name "$APP_NAME" \
    --windowed \
    --icon "icon.icns" \
    --hidden-import "playwright._impl._driver" \
    --hidden-import "PIL._tkinter_finder" \
    --noconfirm \
    converter.py

echo "✅ Core application built successfully."

echo ""
echo "--- Step 3: Copying all browsers and cleaning up ---"

if [ ! -d "$SOURCE_BROWSERS_PATH" ]; then
    echo "❌ FATAL: Playwright browser cache not found at '$SOURCE_BROWSERS_PATH'"
    echo "Please run 'playwright install' to download them."
    exit 1
fi

DEST_BROWSER_PATH="$FINAL_APP_PATH/Contents/Frameworks/ms-playwright"
echo "Creating destination directory: $DEST_BROWSER_PATH"
mkdir -p "$DEST_BROWSER_PATH"

echo "Copying all browser cache files (this may be slow)..."
cp -R "$SOURCE_BROWSERS_PATH"/. "$DEST_BROWSER_PATH"

echo "Cleaning up unneeded browser files..."
rm -rf "$DEST_BROWSER_PATH"/webkit-*
rm -rf "$DEST_BROWSER_PATH"/firefox-*
rm -rf "$DEST_BROWSER_PATH"/ffmpeg-*
echo "✅ Cleanup complete."
echo ""
echo "--- Build Complete! ---"
echo "Your standalone application is ready at: $FINAL_APP_PATH"