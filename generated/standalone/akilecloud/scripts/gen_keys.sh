#!/bin/bash
set -euo pipefail

# ==============================================================================
# Script Name: gen_keys.sh
# Description: Generates X25519 keys for Reality using the sing-box container
# ==============================================================================

CONFIG_FILE="config.env"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ config.env not found. Create it from config.env.example first."
    exit 1
fi

upsert_env_key() {
    local key="$1"
    local value="$2"
    local tmp_file

    tmp_file=$(mktemp)
    awk -F= -v target_key="$key" -v target_value="$value" '
        BEGIN { updated = 0 }
        $1 == target_key {
            if (!updated) {
                print target_key "=" target_value
                updated = 1
            }
            next
        }
        { print }
        END {
            if (!updated) {
                print target_key "=" target_value
            }
        }
    ' "$CONFIG_FILE" > "$tmp_file"
    mv "$tmp_file" "$CONFIG_FILE"
}

get_env_value() {
    awk -F= -v target_key="$1" '
        $1 == target_key { value = substr($0, index($0, "=") + 1) }
        END { print value }
    ' "$CONFIG_FILE"
}

generate_uuid() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen
        return 0
    fi

    if [ -r /proc/sys/kernel/random/uuid ]; then
        cat /proc/sys/kernel/random/uuid
        return 0
    fi

    python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
}

current_private_key="$(get_env_value REALITY_PRIVATE_KEY)"
current_public_key="$(get_env_value REALITY_PUBLIC_KEY)"
current_short_id="$(get_env_value REALITY_SHORT_ID)"
sing_box_image="$(get_env_value SING_BOX_IMAGE)"
sing_box_image="${sing_box_image:-ghcr.io/sagernet/sing-box:v1.13.2}"

if [ -n "$current_private_key" ] && [ -n "$current_public_key" ] && [ -n "$current_short_id" ]; then
    echo "ℹ️  Reality keys already present."
else
    echo "🔑 Generating Reality Keypair..."

    CONTAINER_CMD="podman"
    if ! command -v podman >/dev/null 2>&1; then
        CONTAINER_CMD="docker"
    fi

    OUTPUT=$($CONTAINER_CMD run --rm "$sing_box_image" generate reality-keypair)
    PRIV_KEY=$(echo "$OUTPUT" | grep "PrivateKey" | awk '{print $2}')
    PUB_KEY=$(echo "$OUTPUT" | grep "PublicKey" | awk '{print $2}')
    SHORT_ID=$(openssl rand -hex 8)

    if [ -z "$PRIV_KEY" ] || [ -z "$PUB_KEY" ]; then
        echo "❌ Failed to generate keys. Output: $OUTPUT"
        exit 1
    fi

    upsert_env_key "REALITY_PRIVATE_KEY" "$PRIV_KEY"
    upsert_env_key "REALITY_PUBLIC_KEY" "$PUB_KEY"
    upsert_env_key "REALITY_SHORT_ID" "$SHORT_ID"
    echo "💾 Saved Reality keys to $CONFIG_FILE"
fi

CURRENT_UUID="$(get_env_value VLESS_UUID)"
if [ -z "$CURRENT_UUID" ]; then
    echo "🔑 Generating new VLESS_UUID..."
    NEW_UUID="$(generate_uuid)"
    upsert_env_key "VLESS_UUID" "$NEW_UUID"
    echo "   UUID: $NEW_UUID"
else
    echo "ℹ️  VLESS_UUID already set."
fi
