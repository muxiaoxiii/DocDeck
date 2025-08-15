#!/usr/bin/env bash
set -euo pipefail

APP_NAME="DocDeck"
ICON_PNG="icon/docdeck.png"
ICON_ICNS="icon/docdeck.icns"
DMG_PATH="dist/DocDeck-macOS.dmg"
ENTRY="main.py"

# Prepare icon.icns
if [[ ! -f "$ICON_ICNS" ]]; then
	mkdir -p icon.iconset
	sips -z 16 16     "$ICON_PNG" --out icon.iconset/icon_16x16.png
	sips -z 32 32     "$ICON_PNG" --out icon.iconset/icon_32x32.png
	sips -z 128 128   "$ICON_PNG" --out icon.iconset/icon_128x128.png
	sips -z 256 256   "$ICON_PNG" --out icon.iconset/icon_256x256.png
	iconutil -c icns icon.iconset -o "$ICON_ICNS"
	rm -rf icon.iconset
fi

# Clean
rm -rf build dist "$APP_NAME.spec"

# Build app bundle
pyinstaller \
	--noconfirm --clean --windowed \
	--name "$APP_NAME" \
	--icon "$ICON_ICNS" \
	"$ENTRY"

# Create DMG
mkdir -p dist
if ! command -v create-dmg >/dev/null 2>&1; then
	pip install create-dmg >/dev/null 2>&1 || true
fi
create-dmg \
	--overwrite \
	--volname "$APP_NAME" \
	--window-size 600 400 \
	--icon-size 128 \
	--icon "$APP_NAME.app" 175 120 \
	--hide-extension "$APP_NAME.app" \
	--app-drop-link 425 120 \
	"$DMG_PATH" \
	"dist/$APP_NAME/"

echo "DMG built at: $DMG_PATH"