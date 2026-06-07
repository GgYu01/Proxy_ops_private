#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBSCRIPTIONS_DIR="${ROOT_DIR}/generated/subscriptions"
SUBSCRIPTIONS_CONFIG="${ROOT_DIR}/inventory/subscriptions.yaml"
NODES_CONFIG="${ROOT_DIR}/inventory/nodes.yaml"
PYTHON="${PYTHON:-python3}"
if ! command -v "${PYTHON}" >/dev/null 2>&1; then
  PYTHON=python
fi

read_inventory_field() {
  local file="$1"
  local field="$2"
  "${PYTHON}" - "$file" "$field" <<'PY'
import json
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
field = sys.argv[2]
payload = yaml.safe_load(path.read_text(encoding="utf-8"))
if isinstance(payload, dict) and field in payload:
    print(payload[field])
PY
}

read_publish_node_field() {
  local field="$1"
  "${PYTHON}" - "$SUBSCRIPTIONS_CONFIG" "$field" <<'PY'
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
field = sys.argv[2]
payload = yaml.safe_load(path.read_text(encoding="utf-8"))
publish = payload.get("publish") or {}
value = publish.get(field)
if value is None:
    raise SystemExit(f"[ERROR] inventory publish.{field} is required")
print(value)
PY
}

read_node_ssh_field() {
  local node_name="$1"
  local field="$2"
  "${PYTHON}" - "$NODES_CONFIG" "$node_name" "$field" <<'PY'
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
node_name = sys.argv[2]
field = sys.argv[3]
payload = yaml.safe_load(path.read_text(encoding="utf-8"))
for node in payload.get("nodes", []):
    if node.get("name") == node_name:
        value = node.get(field)
        if value is None:
            raise SystemExit(f"[ERROR] node {node_name} missing field {field}")
        print(value)
        raise SystemExit(0)
raise SystemExit(f"[ERROR] unknown node: {node_name}")
PY
}

PUBLISH_NODE="$(read_publish_node_field node)"
DEFAULT_REMOTE_HOST="$(read_node_ssh_field "${PUBLISH_NODE}" host)"
DEFAULT_REMOTE_USER="$(read_node_ssh_field "${PUBLISH_NODE}" ssh_user 2>/dev/null || echo root)"
DEFAULT_REMOTE_PORT="$(read_node_ssh_field "${PUBLISH_NODE}" ssh_port)"

REMOTE_HOST="${REMOTE_HOST:-${DEFAULT_REMOTE_HOST}}"
REMOTE_USER="${REMOTE_USER:-${DEFAULT_REMOTE_USER}}"
REMOTE_PORT="${REMOTE_PORT:-${DEFAULT_REMOTE_PORT}}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:-}"
REMOTE_PUBLIC_ROOT="${REMOTE_PUBLIC_ROOT:-$(read_publish_node_field remote_public_root)}"
REMOTE_PUBLIC_DIR="${REMOTE_PUBLIC_DIR:-$(read_publish_node_field remote_subscriptions_dir)}"
REMOTE_STAGE_DIR="${REMOTE_STAGE_DIR:-${REMOTE_PUBLIC_DIR}.staging}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-$(read_inventory_field "${SUBSCRIPTIONS_CONFIG}" subscription_base_url)}"
PUBLIC_TEST_URL="${PUBLIC_TEST_URL:-$(read_publish_node_field verify_url)}"
PUBLIC_LANDING_URL="${PUBLIC_LANDING_URL:-${PUBLIC_BASE_URL%/subscriptions}/}"
PUBLIC_MIHOMO_URL="${PUBLIC_MIHOMO_URL:-${PUBLIC_BASE_URL%/}/mihomo-universal.yaml}"
SYSTEMD_UNIT="${SYSTEMD_UNIT:-$(read_publish_node_field systemd_unit)}"

if [[ "${REMOTE_HOST}" == "112.28.134.53" ]]; then
  echo "[ERROR] 112.28.134.53 is retired and must not be used as the subscription publish target." >&2
  exit 8
fi

if [[ "${REMOTE_HOST}" == *@* ]]; then
  SSH_TARGET="${REMOTE_HOST}"
else
  SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"
fi

usage() {
  cat <<'EOF'
Usage: publish_subscriptions_to_sea_host.sh [--dry-run]

Publish generated subscriptions to the LisaHost SEA BGP temporary host.
Defaults are read from inventory/subscriptions.yaml publish metadata and us_sea_bgp_01.
EOF
}

DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "${SUBSCRIPTIONS_DIR}" ]]; then
  echo "[ERROR] Missing generated subscriptions directory: ${SUBSCRIPTIONS_DIR}"
  exit 2
fi

legacy_mihomo_profiles=(
  "${SUBSCRIPTIONS_DIR}/mihomo-windows.yaml"
  "${SUBSCRIPTIONS_DIR}/mihomo-macos.yaml"
  "${SUBSCRIPTIONS_DIR}/mihomo-linux.yaml"
)
for legacy_profile in "${legacy_mihomo_profiles[@]}"; do
  if [[ -e "${legacy_profile}" ]]; then
    echo "[ERROR] Refusing to publish legacy per-platform mihomo profile: ${legacy_profile}" >&2
    echo "[ERROR] Regenerate subscriptions so only mihomo-universal.yaml is published." >&2
    exit 11
  fi
done

run_ssh() {
  if [[ -n "${REMOTE_PASSWORD}" ]]; then
    command -v sshpass >/dev/null 2>&1 || {
      echo "[ERROR] REMOTE_PASSWORD was provided but sshpass is not installed." >&2
      exit 10
    }
    SSHPASS="${REMOTE_PASSWORD}" sshpass -e ssh \
      -o StrictHostKeyChecking=no \
      -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no \
      -p "${REMOTE_PORT}" \
      "${SSH_TARGET}" \
      "$@"
  else
    ssh -p "${REMOTE_PORT}" "${SSH_TARGET}" "$@"
  fi
}

echo "[INFO] Publish target: ${SSH_TARGET}:${REMOTE_PORT}"
echo "[INFO] Publish node: ${PUBLISH_NODE}"
echo "[INFO] Remote public root: ${REMOTE_PUBLIC_ROOT}"
echo "[INFO] Remote subscriptions dir: ${REMOTE_PUBLIC_DIR}"
echo "[INFO] Public landing URL: ${PUBLIC_LANDING_URL}"
echo "[INFO] Public base URL: ${PUBLIC_BASE_URL}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[INFO] Planned files:"
  find "${SUBSCRIPTIONS_DIR}" -maxdepth 1 -type f | sed 's#^#  - #'
  echo "[DRY-RUN] No remote changes applied."
  exit 0
fi

run_ssh "mkdir -p '${REMOTE_PUBLIC_ROOT}' && rm -rf '${REMOTE_STAGE_DIR}' && mkdir -p '${REMOTE_STAGE_DIR}'"
tar czf - -C "${SUBSCRIPTIONS_DIR}" . | run_ssh "tar xzf - -C '${REMOTE_STAGE_DIR}'"
run_ssh "\
  rm -rf '${REMOTE_PUBLIC_DIR}.previous' && \
  if [ -d '${REMOTE_PUBLIC_DIR}' ]; then mv '${REMOTE_PUBLIC_DIR}' '${REMOTE_PUBLIC_DIR}.previous'; fi && \
  mv '${REMOTE_STAGE_DIR}' '${REMOTE_PUBLIC_DIR}' && \
  cp '${REMOTE_PUBLIC_DIR}/index.html' '${REMOTE_PUBLIC_ROOT}/index.html'"
if run_ssh "systemctl is-active '${SYSTEMD_UNIT}' >/dev/null 2>&1"; then
  run_ssh "systemctl reload-or-restart '${SYSTEMD_UNIT}'" || true
fi

echo "[INFO] Verifying published subscription endpoint"
for attempt in $(seq 1 10); do
  if curl -fsS --max-time 15 "${PUBLIC_TEST_URL}" >/dev/null && \
     curl -fsS --max-time 15 "${PUBLIC_MIHOMO_URL}" | grep -Eq 'PROCESS-NAME,wps\.exe|DOMAIN-SUFFIX,wps\.cn'; then
    echo "[INFO] Subscription endpoint is ready on attempt ${attempt}."
    echo "[INFO] Subscription publish completed successfully."
    exit 0
  fi
  sleep 2
done

echo "[ERROR] Subscription endpoint did not become ready: ${PUBLIC_TEST_URL}"
exit 4
