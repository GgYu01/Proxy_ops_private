#!/bin/bash
set -euo pipefail

# ==============================================================================
# Script Name: install.sh
# Description: One-click installation script
# ==============================================================================

echo "🚀 Starting Remote Proxy Installation..."

# 0. Config Check
if [ ! -f config.env ]; then
    echo "ℹ️  config.env not found. Creating from default..."
    cp config.env.example config.env
    echo "⚠️  Created config.env. You may want to edit it before proceeding."
    echo "   Press Enter to continue with defaults, or Ctrl+C to stop and edit."
    read -r
fi

# 1. Environment Setup
echo "🔧 Step 1: Setting up Environment..."
chmod +x scripts/*.sh
./scripts/setup_env.sh

# 2. Generate Config
echo "⚙️  Step 2: Generating Configuration..."
./scripts/gen_keys.sh
python3 scripts/gen_config.py

# 3. Deploy
echo "🚀 Step 3: Deploying Service..."
./scripts/deploy.sh

# 4. Show Info
./scripts/show_info.sh

echo "🎉 Installation Complete!"
echo "--------------------------------------------------------"
if [ "$(id -u)" -eq 0 ]; then
    echo "Check service status: systemctl status remote-proxy"
    echo "View logs:            journalctl -u remote-proxy -f"
else
    echo "Check service status: systemctl --user status remote-proxy"
    echo "View logs:            journalctl --user -u remote-proxy -f"
fi
echo "========================================================"
