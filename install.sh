#!/bin/bash
# Raspberry Pi Zero installation script for Lyrics Display

set -e

echo "==================================="
echo "Lyrics Display - Pi Zero Installer"
echo "==================================="
echo

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    echo "Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# Update system
echo "[1/6] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "[2/6] Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0

# Create virtual environment
echo "[3/6] Setting up Python virtual environment..."
cd "$(dirname "$0")"
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "[4/6] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for .env file
echo "[5/6] Checking configuration..."
if [ ! -f .env ]; then
    echo ""
    echo "WARNING: No .env file found!"
    echo "Copy env.example to .env and add your ACRCloud credentials:"
    echo "  cp env.example .env"
    echo "  nano .env"
    echo ""
fi

# Install systemd service
echo "[6/6] Installing systemd service..."
SERVICE_FILE="/etc/systemd/system/lyrics.service"
INSTALL_DIR="$(pwd)"
USER="$(whoami)"

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Lyrics Display
After=network.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/venv/bin/python -m src.main
WorkingDirectory=${INSTALL_DIR}
User=${USER}
Restart=always
RestartSec=5
Environment=DISPLAY=:0
Environment=SDL_VIDEODRIVER=kmsdrm

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lyrics.service

echo ""
echo "==================================="
echo "Installation complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Copy env.example to .env and add your ACRCloud credentials"
echo "  2. Test the application: ./venv/bin/python -m src.main --windowed"
echo "  3. Start the service: sudo systemctl start lyrics"
echo "  4. View logs: journalctl -u lyrics -f"
echo ""
echo "For auto-start on boot, the service is already enabled."
echo ""

