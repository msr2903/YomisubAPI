#!/usr/bin/env bash
# update_jmdict.sh - Download the latest JMdict English dictionary
#
# Usage: ./scripts/update_jmdict.sh

set -e

DATA_DIR="${1:-data}"
mkdir -p "$DATA_DIR"

echo "🔍 Fetching latest jmdict-simplified release..."

# Get the latest release download URL
DOWNLOAD_URL=$(curl -sL "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
for asset in data.get('assets', []):
    if 'jmdict-eng-' in asset['name'] and asset['name'].endswith('.json.tgz'):
        if 'common' not in asset['name'] and 'examples' not in asset['name']:
            print(asset['browser_download_url'])
            break
")

if [ -z "$DOWNLOAD_URL" ]; then
    echo "❌ Could not find download URL"
    exit 1
fi

VERSION=$(echo "$DOWNLOAD_URL" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
echo "📦 Found version: $VERSION"
echo "📥 Downloading from: $DOWNLOAD_URL"

# Download and extract
TEMP_FILE=$(mktemp)
curl -L "$DOWNLOAD_URL" -o "$TEMP_FILE"

echo "📂 Extracting to $DATA_DIR..."
tar -xzf "$TEMP_FILE" -C "$DATA_DIR"

# Rename to standard name
JSON_FILE=$(ls "$DATA_DIR"/jmdict-eng-*.json 2>/dev/null | head -1)
if [ -n "$JSON_FILE" ]; then
    mv "$JSON_FILE" "$DATA_DIR/jmdict-eng.json"
fi

# Cleanup
rm -f "$TEMP_FILE"

echo "✅ JMdict updated to version $VERSION"
echo "   Location: $DATA_DIR/jmdict-eng.json"
echo "   Entries: $(python3 -c "import json; print(len(json.load(open('$DATA_DIR/jmdict-eng.json'))['words']))")"
