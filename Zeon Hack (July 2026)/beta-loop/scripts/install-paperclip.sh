#!/usr/bin/env bash
# Install gxl-paperclip from the official GXL wheel (not on PyPI).
# Usage: bash scripts/install-paperclip.sh
set -euo pipefail

VERSION="${PAPERCLIP_VERSION:-0.7.11}"
WHEEL_URL="https://paperclip.gxl.ai/paperclip.whl"
TMP="/tmp/gxl_paperclip-${VERSION}-py3-none-any.whl"
trap 'rm -f "$TMP"' EXIT

curl -fsSL "$WHEEL_URL" -o "$TMP"
python3 -m pip install "$TMP"

echo "Installed gxl-paperclip ${VERSION}"
