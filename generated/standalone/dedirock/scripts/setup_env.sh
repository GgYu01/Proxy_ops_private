#!/bin/bash
set -euo pipefail

# ==============================================================================
# Script Name: setup_env.sh
# Description: Prepares the environment (Update, Podman, Swap)
# ==============================================================================

# Load config if exists
if [ -f config.env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./config.env
    set +a
fi

SWAP_SIZE=${SWAP_SIZE_GB:-2}
if [ "$(id -u)" -eq 0 ]; then
    SUDO_CMD=""
else
    SUDO_CMD="sudo"
fi

echo ">>> [1/3] Updating System Packages..."
# Check for apt (Debian/Ubuntu)
if command -v apt-get &> /dev/null; then
    ${SUDO_CMD} apt-get update -q
    ${SUDO_CMD} apt-get upgrade -yq
    ${SUDO_CMD} apt-get install -yq curl jq python3 podman uidmap slirp4netns systemd-container
elif command -v yum &> /dev/null; then
    ${SUDO_CMD} yum update -y
    ${SUDO_CMD} yum install -y curl jq python3 podman
else
    echo "⚠️  Unsupported package manager. Please ensure Podman is installed manually."
fi

echo ">>> [2/3] Configuring Swap..."
chmod +x scripts/manage_swap.sh
${SUDO_CMD} ./scripts/manage_swap.sh --size "$SWAP_SIZE"

echo ">>> [3/3] Verifying Podman..."
podman info > /dev/null
echo "✅ Environment Setup Complete."
