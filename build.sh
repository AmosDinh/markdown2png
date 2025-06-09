#!/bin/bash

# This script builds the application using a two-step process:
# 1. Run PyInstaller to build the core app, INTENTIONALLY without the
#    browser files to avoid the `codesign` error.
# 2. Manually copy the browser files into the finished .app bundle.

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
# We build WITHOUT the browser data to prevent the codesign error.
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
echo "--- Step 3: Manually copying Playwright browser files ---"

# Verify that the source browser cache exists
if [ ! -d "$SOURCE_BROWSERS_PATH" ]; then
    echo "❌ FATAL: Playwright browser cache not found at '$SOURCE_BROWSERS_PATH'"
    echo "Please run 'playwright install chromium' to download them."
    exit 1
fi

# Define the destination within the .app bundle's MacOS directory
# This MUST match the path constructed in converter.py (sys._MEIPASS)
DEST_BROWSER_PATH="$FINAL_APP_PATH/Contents/MacOS/ms-playwright"

echo "Creating destination directory: $DEST_BROWSER_PATH"
mkdir -p "$DEST_BROWSER_PATH"

# Copy only the Chromium browser directory into the app
cp -R "$SOURCE_BROWSERS_PATH"/chromium-* "$DEST_BROWSER_PATH"

echo "✅ Browser files copied successfully."
echo ""
echo "--- Build Complete! ---"
echo "Your standalone application is ready at: $FINAL_APP_PATH"