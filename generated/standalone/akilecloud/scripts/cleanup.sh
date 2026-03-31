#!/bin/bash
# ==============================================================================
# Script Name: cleanup.sh
# Description: Removes existing service and configuration to ensure a clean slate
# ==============================================================================

echo "🧹 Starting Cleanup..."

IS_ROOT=0
if [ "$(id -u)" -eq 0 ]; then
    IS_ROOT=1
fi

if [ "$IS_ROOT" -eq 1 ]; then
    SYSTEMD_DIR="/etc/containers/systemd"
    SYSTEMCTL_CMD="systemctl"
else
    SYSTEMD_DIR="$HOME/.config/containers/systemd"
    SYSTEMCTL_CMD="systemctl --user"
fi

# 1. Stop and Disable Service
if $SYSTEMCTL_CMD is-active --quiet remote-proxy; then
    echo "   Stopping remote-proxy service..."
    $SYSTEMCTL_CMD stop remote-proxy
fi

if $SYSTEMCTL_CMD is-enabled --quiet remote-proxy; then
    echo "   Disabling remote-proxy service..."
    $SYSTEMCTL_CMD disable remote-proxy
fi

# 2. Remove Quadlet File
if [ -f "$SYSTEMD_DIR/remote-proxy.container" ]; then
    echo "   Removing Quadlet file: $SYSTEMD_DIR/remote-proxy.container"
    rm -f "$SYSTEMD_DIR/remote-proxy.container"
fi

# 3. Reload Daemon (to clear generated service)
echo "   Reloading systemd..."
$SYSTEMCTL_CMD daemon-reload
$SYSTEMCTL_CMD reset-failed

echo "✅ Cleanup Complete."
