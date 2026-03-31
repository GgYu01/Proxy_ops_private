#!/bin/bash
# ==============================================================================
# Script Name: show_info.sh
# Description: Reads config.env and outputs client connection links
# ==============================================================================

if [ -f config.env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./config.env
    set +a
fi

# Function to URL encode
urlencode() {
    python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$1"
}

# Defaults
HOST_IP=$(curl -s http://ipinfo.io/ip)
PORT=$((BASE_PORT + 3)) # VLESS port
UUID=${VLESS_UUID}
SNI=${REALITY_SERVER_NAMES%%,*} # Take first SNI
PBK=${REALITY_PUBLIC_KEY}
SID=${REALITY_SHORT_ID}
FLOW="xtls-rprx-vision"
ALIAS="MyRemoteProxy"

echo ""
echo "========================================================"
echo "📝 Client Connection Information"
echo "========================================================"
echo ""
echo "📂 Configuration is saved in: $(pwd)/config.env"
echo ""

if [ -n "$UUID" ] && [ -n "$PBK" ]; then
    # VLESS Reality Link Format
    # vless://uuid@ip:port?security=reality&encryption=none&pbk=...&fp=chrome&type=tcp&flow=vision&sni=...&sid=...#alias
    
    LINK="vless://${UUID}@${HOST_IP}:${PORT}?security=reality&encryption=none&pbk=${PBK}&fp=chrome&type=tcp&flow=${FLOW}&sni=${SNI}&sid=${SID}#$(urlencode "$ALIAS")"
    
    echo "🔗 VLESS + Reality Share Link (Copy to Client):"
    echo "--------------------------------------------------------"
    echo "$LINK"
    echo "--------------------------------------------------------"
else
    echo "⚠️  VLESS keys missing. Could not generate link."
fi

echo ""
echo "ℹ️  To view this info again, run: ./scripts/show_info.sh"
echo "========================================================"
