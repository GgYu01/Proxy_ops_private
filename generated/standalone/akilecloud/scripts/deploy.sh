#!/bin/bash
set -euo pipefail

# ==============================================================================
# Script Name: deploy.sh
# Description: Deploys the service using Podman Quadlet
# ==============================================================================

IS_ROOT=0
if [ "$(id -u)" -eq 0 ]; then
    IS_ROOT=1
fi

if [ "$IS_ROOT" -eq 1 ]; then
    SYSTEMD_DIR="/etc/containers/systemd"
    SYSTEMCTL_CMD="systemctl"
    WANTED_BY_TARGET="multi-user.target"
    echo "ℹ️  Running as ROOT. Using system-wide Quadlet dir: $SYSTEMD_DIR"
else
    SYSTEMD_DIR="$HOME/.config/containers/systemd"
    SYSTEMCTL_CMD="systemctl --user"
    WANTED_BY_TARGET="default.target"
    echo "ℹ️  Running as USER. Using user-scope Quadlet dir: $SYSTEMD_DIR"
fi

if [ -f config.env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./config.env
    set +a
fi

BASE_PORT=${BASE_PORT:-10000}
MEMORY_LIMIT=${MEMORY_LIMIT:-256M}
SING_BOX_IMAGE=${SING_BOX_IMAGE:-ghcr.io/sagernet/sing-box:v1.13.2}
ENABLE_DEPRECATED_SING_BOX_FLAGS=${ENABLE_DEPRECATED_SING_BOX_FLAGS:-true}

if [[ "$MEMORY_LIMIT" =~ ([0-9]+)M ]]; then
    MEM_VAL="${BASH_REMATCH[1]}"
    if [ "$MEM_VAL" -lt 20 ]; then
        echo "⚠️  Memory limit $MEMORY_LIMIT is too low. Bumping to 64M."
        MEMORY_LIMIT="64M"
    fi
fi

if [ ! -f singbox.json ]; then
    echo "⚠️ singbox.json not found. Running generator..."
    python3 scripts/gen_config.py
fi

QUADLET_ENV_LINES=""
FALLBACK_ENV_LINES=""
if [ "$ENABLE_DEPRECATED_SING_BOX_FLAGS" = "true" ]; then
    QUADLET_ENV_LINES=$(cat <<'EOF'
Environment=ENABLE_DEPRECATED_LEGACY_DNS_SERVERS=true
Environment=ENABLE_DEPRECATED_MISSING_DOMAIN_RESOLVER=true
Environment=ENABLE_DEPRECATED_LEGACY_DOMAIN_STRATEGY_OPTIONS=true
EOF
)
    FALLBACK_ENV_LINES=$(cat <<'EOF'
  -e ENABLE_DEPRECATED_LEGACY_DNS_SERVERS=true \
  -e ENABLE_DEPRECATED_MISSING_DOMAIN_RESOLVER=true \
  -e ENABLE_DEPRECATED_LEGACY_DOMAIN_STRATEGY_OPTIONS=true \
EOF
)
fi

mkdir -p "$SYSTEMD_DIR"
rm -f "$SYSTEMD_DIR/remote-proxy.container"

echo ">>> Generating Quadlet file at $SYSTEMD_DIR/remote-proxy.container"
cat > "$SYSTEMD_DIR/remote-proxy.container" <<EOF
[Unit]
Description=Remote Proxy Service (Sing-box)
After=network-online.target

[Container]
Image=${SING_BOX_IMAGE}
ContainerName=remote-proxy
Volume=$(pwd)/singbox.json:/etc/sing-box/config.json:Z
${QUADLET_ENV_LINES}
PublishPort=${BASE_PORT}:${BASE_PORT}
PublishPort=$((${BASE_PORT}+1)):$((${BASE_PORT}+1))
PublishPort=$((${BASE_PORT}+2)):$((${BASE_PORT}+2))
PublishPort=$((${BASE_PORT}+3)):$((${BASE_PORT}+3))
PublishPort=$((${BASE_PORT}+4)):$((${BASE_PORT}+4))
Memory=${MEMORY_LIMIT}
Exec=run -c /etc/sing-box/config.json

[Service]
Restart=always
TimeoutStartSec=900
EOF

echo ">>> Reloading Systemd..."
$SYSTEMCTL_CMD daemon-reload

echo ">>> Verifying Service Generation..."
GENERATED=0
MAX_CHECKS=5
for ((i=1; i<=MAX_CHECKS; i++)); do
    if $SYSTEMCTL_CMD list-unit-files remote-proxy.service | grep -q "remote-proxy.service"; then
        echo "✅ Service detected (Quadlet)."
        GENERATED=1
        break
    fi
    echo "   Waiting for generator... ($i/$MAX_CHECKS)"
    sleep 1
done

if [ "$GENERATED" -eq 0 ]; then
    echo "⚠️  Quadlet generation failed. Falling back to standard Systemd Unit."

    if [ "$IS_ROOT" -eq 1 ]; then
        FALLBACK_DIR="/etc/systemd/system"
    else
        FALLBACK_DIR="$HOME/.config/systemd/user"
        mkdir -p "$FALLBACK_DIR"
    fi

    cat > "$FALLBACK_DIR/remote-proxy.service" <<EOF
[Unit]
Description=Remote Proxy Service (Fallback)
After=network-online.target

[Service]
Restart=always
ExecStart=$(command -v podman) run --name remote-proxy --replace --rm \\
${FALLBACK_ENV_LINES}
  -v $(pwd)/singbox.json:/etc/sing-box/config.json:Z \\
  -p ${BASE_PORT}:${BASE_PORT} \\
  -p $((${BASE_PORT}+1)):$((${BASE_PORT}+1)) \\
  -p $((${BASE_PORT}+2)):$((${BASE_PORT}+2)) \\
  -p $((${BASE_PORT}+3)):$((${BASE_PORT}+3)) \\
  -p $((${BASE_PORT}+4)):$((${BASE_PORT}+4)) \\
  --memory ${MEMORY_LIMIT} \\
  ${SING_BOX_IMAGE} run -c /etc/sing-box/config.json
ExecStop=$(command -v podman) stop remote-proxy

[Install]
WantedBy=${WANTED_BY_TARGET}
EOF

    echo ">>> Reloading Systemd (Fallback)..."
    $SYSTEMCTL_CMD daemon-reload
fi

echo ">>> Starting Service..."
if ! $SYSTEMCTL_CMD enable --now remote-proxy; then
    echo "❌ Failed to enable service. Debugging info:"
    echo "1. Quadlet File Content:"
    cat "$SYSTEMD_DIR/remote-proxy.container"
    echo "2. Generator Logs:"
    journalctl -t podman-system-generator -n 20 --no-pager
    exit 1
fi

sleep 2
$SYSTEMCTL_CMD status remote-proxy --no-pager

echo "✅ Deployment initiated. Check logs with: journalctl -u remote-proxy -f"
if [ "$IS_ROOT" -eq 0 ]; then
    echo "   (User mode logs: journalctl --user -u remote-proxy -f)"
fi
