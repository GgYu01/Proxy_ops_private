#!/bin/bash
set -euo pipefail

# ==============================================================================
# Script Name: verify.sh
# Description: Verifies the deployment by checking ports and connectivity
# ==============================================================================

# Load config
if [ -f config.env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./config.env
    set +a
fi

BASE_PORT=${BASE_PORT:-10000}
RETRIES=10
DELAY=3
TARGET_URL="http://ipinfo.io/ip"

log_info() { echo -e "INFO: $1"; }
log_warn() { echo -e "⚠️  WARN: $1"; }
log_err()  { echo -e "❌ ERROR: $1"; }
log_pass() { echo -e "✅ PASS: $1"; }

check_port() {
    local port=$1
    local name=$2
    log_info "Checking $name port ($port)..."
    if command -v ss &> /dev/null; then
        if ss -tulpn | grep -q ":$port "; then
            log_pass "Port $port ($name) is listening."
            return 0
        fi
    else
        # Fallback to lsof or netstat if ss is missing
        if netstat -tulpn 2>/dev/null | grep -q ":$port "; then
             log_pass "Port $port ($name) is listening."
             return 0
        fi
    fi
    log_warn "Port $port ($name) not found (Might be containerized/mapped, checking curl...)"
    return 1
}

test_proxy() {
    local proto=$1
    local port=$2
    local name=$3
    local user=$PROXY_USER
    local pass=$PROXY_PASS
    
    local proxy_url=""
    local display_target=""
    if [ "$proto" == "http" ]; then
        proxy_url="http://${user}:${pass}@127.0.0.1:${port}"
        display_target="http://<redacted>@127.0.0.1:${port}"
    elif [ "$proto" == "socks5" ]; then
        proxy_url="socks5://${user}:${pass}@127.0.0.1:${port}"
        display_target="socks5://<redacted>@127.0.0.1:${port}"
    fi

    log_info "Testing $name connectivity via $display_target..."

    local count=1
    while [ $count -le $RETRIES ]; do
        if response=$(curl -s --max-time 5 -x "$proxy_url" "$TARGET_URL"); then
            log_pass "$name connectivity verified! (Response: $response)"
            return 0
        else
            log_warn "Attempt $count/$RETRIES failed for $name. Retrying in ${DELAY}s..."
            sleep $DELAY
            ((count++))
        fi
    done

    log_err "$name failed after $RETRIES attempts."
    return 1
}

main() {
    echo "🔍 Starting Verification..."
    
    # 1. Port Checks (Basic Listener Check)
    # Note: In rootless podman, these might be bound by 'slirp4netns' or 'rootlesskit', 
    # seeing them on host might require checking the container status or mapped ports.
    
    check_port "$BASE_PORT" "SOCKS5" || true
    check_port "$(($BASE_PORT + 1))" "HTTP" || true
    check_port "$(($BASE_PORT + 2))" "Shadowsocks" || true
    check_port "$(($BASE_PORT + 3))" "VLESS" || true
    check_port "$(($BASE_PORT + 4))" "Trojan" || true

    # 2. Functional Checks (Only SOCKS5 and HTTP are easily curl-able)
    test_proxy "socks5" "$BASE_PORT" "SOCKS5"
    test_proxy "http" "$(($BASE_PORT + 1))" "HTTP"

    echo "========================================"
    echo "✅ Verification Completed Successfully."
    echo "========================================"
}

main
