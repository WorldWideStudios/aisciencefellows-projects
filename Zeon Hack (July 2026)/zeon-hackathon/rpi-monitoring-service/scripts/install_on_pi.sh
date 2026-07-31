#!/usr/bin/env bash
set -euo pipefail

SERVICE_USER="${SERVICE_USER:-hack}"
SERVICE_DIR="/home/${SERVICE_USER}/rpi-monitoring-service"
SERVICE_FILE="/etc/systemd/system/rpi-monitoring-service.service"

cd "$SERVICE_DIR"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if ! command -v rpicam-still >/dev/null 2>&1 && ! command -v libcamera-still >/dev/null 2>&1; then
  echo "Warning: rpicam-still/libcamera-still was not found. Install Raspberry Pi camera apps before using /camera/image." >&2
fi

sudo usermod -aG dialout,video,render "$SERVICE_USER"
sudo cp systemd/rpi-monitoring-service.service "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable rpi-monitoring-service
sudo systemctl restart rpi-monitoring-service
sudo systemctl --no-pager --full status rpi-monitoring-service
