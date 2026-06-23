#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBSCRIPTIONS_DIR="${ROOT_DIR}/generated/subscriptions"
PUBLISH_CONFIG_DIR="${ROOT_DIR}/generated/publish/sea-bgp"
SUBSCRIPTIONS_CONFIG="${ROOT_DIR}/inventory/subscriptions.yaml"
NODES_CONFIG="${ROOT_DIR}/inventory/nodes.yaml"
WORKSPACE_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
DEFAULT_WINDOWS_VENV_PYTHON="${WORKSPACE_ROOT}/.venv/Scripts/python.exe"
if [[ -z "${PYTHON:-}" && -x "${DEFAULT_WINDOWS_VENV_PYTHON}" ]]; then
  PYTHON="${DEFAULT_WINDOWS_VENV_PYTHON}"
else
  PYTHON="${PYTHON:-python3}"
fi
if ! command -v "${PYTHON}" >/dev/null 2>&1 && [[ ! -x "${PYTHON}" ]]; then
  PYTHON=python
fi
DEFAULT_WINDOWS_MIHOMO_BIN="/c/Tools/mihomo/mihomo-windows-amd64.exe"
if [[ -z "${MIHOMO_BIN:-}" && -x "${DEFAULT_WINDOWS_MIHOMO_BIN}" ]]; then
  export MIHOMO_BIN="${DEFAULT_WINDOWS_MIHOMO_BIN}"
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
REMOTE_CONFIG_DIR="${REMOTE_CONFIG_DIR:-$(read_publish_node_field remote_config_dir)}"
REMOTE_CONFIG_STAGE_DIR="${REMOTE_CONFIG_STAGE_DIR:-${REMOTE_CONFIG_DIR}.staging}"
REMOTE_CONTAINER_CONFIG="${REMOTE_CONTAINER_CONFIG:-$(read_publish_node_field remote_container_config)}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-$(read_inventory_field "${SUBSCRIPTIONS_CONFIG}" subscription_base_url)}"
PUBLIC_TEST_URL="${PUBLIC_TEST_URL:-$(read_publish_node_field verify_url)}"
PUBLIC_LANDING_URL="${PUBLIC_LANDING_URL:-${PUBLIC_BASE_URL%/subscriptions}/}"
PUBLIC_MIHOMO_URL="${PUBLIC_MIHOMO_URL:-${PUBLIC_BASE_URL%/}/mihomo-universal.yaml}"
SSH_BIN="${SSH_BIN:-ssh}"
SSHPASS_BIN="${SSHPASS_BIN:-sshpass}"
SUBSCRIPTION_CONTAINER_NAME="${SUBSCRIPTION_CONTAINER_NAME:-gg-proxy-subscriptions}"
SUBSCRIPTION_CONTAINER_CONFIG_FILE="${SUBSCRIPTION_CONTAINER_CONFIG_FILE:-${PUBLISH_CONFIG_DIR}/${SUBSCRIPTION_CONTAINER_NAME}.container}"
SUBSCRIPTION_PUBLISH_MANIFEST="${SUBSCRIPTION_PUBLISH_MANIFEST:-${PUBLISH_CONFIG_DIR}/subscription-publish-manifest.json}"
SUBSCRIPTION_HOST="$("${PYTHON}" - "${PUBLIC_BASE_URL}" <<'PY'
import sys
from urllib.parse import urlparse

host = urlparse(sys.argv[1]).hostname
if not host:
    raise SystemExit("[ERROR] subscription_base_url must include a hostname")
print(host)
PY
)"

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

SKIP_LOCAL_AVAILABILITY_PROBE="${SEA_SUBSCRIPTION_SKIP_LOCAL_PROBE:-0}"

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
    command -v "${SSHPASS_BIN}" >/dev/null 2>&1 || {
      echo "[ERROR] REMOTE_PASSWORD was provided but sshpass is not installed: ${SSHPASS_BIN}" >&2
      exit 10
    }
    SSHPASS="${REMOTE_PASSWORD}" "${SSHPASS_BIN}" -e "${SSH_BIN}" \
      -o StrictHostKeyChecking=no \
      -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no \
      -p "${REMOTE_PORT}" \
      "${SSH_TARGET}" \
      "$@"
  else
    "${SSH_BIN}" -p "${REMOTE_PORT}" "${SSH_TARGET}" "$@"
  fi
}

echo "[INFO] Publish target: ${SSH_TARGET}:${REMOTE_PORT}"
echo "[INFO] Publish node: ${PUBLISH_NODE}"
echo "[INFO] Remote public root: ${REMOTE_PUBLIC_ROOT}"
echo "[INFO] Remote subscriptions dir: ${REMOTE_PUBLIC_DIR}"
echo "[INFO] Remote config dir: ${REMOTE_CONFIG_DIR}"
echo "[INFO] Remote container config: ${REMOTE_CONTAINER_CONFIG}"
echo "[INFO] Public landing URL: ${PUBLIC_LANDING_URL}"
echo "[INFO] Public base URL: ${PUBLIC_BASE_URL}"
echo "[INFO] Subscription container unit: ${SUBSCRIPTION_CONTAINER_NAME}"
if [[ -f "${SUBSCRIPTION_CONTAINER_CONFIG_FILE}" ]]; then
  echo "[INFO] Subscription container image: $(sed -n 's/^Image=//p' "${SUBSCRIPTION_CONTAINER_CONFIG_FILE}" | head -n 1)"
  echo "[INFO] Subscription container command: $(sed -n 's/^Exec=//p' "${SUBSCRIPTION_CONTAINER_CONFIG_FILE}" | head -n 1)"
else
  echo "[INFO] Subscription container config pending generation: ${SUBSCRIPTION_CONTAINER_CONFIG_FILE}"
fi
echo "[INFO] Subscription container mount: ${REMOTE_PUBLIC_ROOT}:/www:ro,Z"
echo "[INFO] Subscription public endpoint: HTTPS 443 via Traefik"
echo "[INFO] Subscription Traefik rule: Host(\`${SUBSCRIPTION_HOST}\`)"
echo "[INFO] Git-tracked publish config: ${SUBSCRIPTION_CONTAINER_CONFIG_FILE}"
echo "[INFO] Git-tracked publish manifest: ${SUBSCRIPTION_PUBLISH_MANIFEST}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[INFO] Planned files:"
  find "${SUBSCRIPTIONS_DIR}" -maxdepth 1 -type f | sed 's#^#  - #'
  if [[ -d "${PUBLISH_CONFIG_DIR}" ]]; then
    find "${PUBLISH_CONFIG_DIR}" -maxdepth 1 -type f | sed 's#^#  - #'
  fi
  echo "[DRY-RUN] No remote changes applied."
  exit 0
fi

if [[ "${SKIP_LOCAL_AVAILABILITY_PROBE}" == "1" ]]; then
  echo "[INFO] Regenerating subscription artifacts from existing availability ledger"
  SKIP_AVAILABILITY_PROBE=1 "${PYTHON}" "${ROOT_DIR}/scripts/reconcile_subscription_node_availability.py" --report
  SKIP_AVAILABILITY_PROBE=1 "${PYTHON}" "${ROOT_DIR}/scripts/render_artifacts.py"
else
  echo "[INFO] Regenerating subscription artifacts with availability probe"
  "${PYTHON}" "${ROOT_DIR}/scripts/reconcile_subscription_node_availability.py" --probe --report
  "${PYTHON}" "${ROOT_DIR}/scripts/render_artifacts.py"
fi

if [[ ! -f "${SUBSCRIPTION_CONTAINER_CONFIG_FILE}" || ! -f "${SUBSCRIPTION_PUBLISH_MANIFEST}" ]]; then
  echo "[ERROR] Missing generated publish config. Run scripts/render_artifacts.py first." >&2
  exit 12
fi

run_ssh "mkdir -p '${REMOTE_PUBLIC_ROOT}' && rm -rf '${REMOTE_STAGE_DIR}' && mkdir -p '${REMOTE_STAGE_DIR}'"
tar czf - -C "${SUBSCRIPTIONS_DIR}" . | run_ssh "tar xzf - -C '${REMOTE_STAGE_DIR}'"
run_ssh "\
  rm -rf '${REMOTE_PUBLIC_DIR}.previous' && \
  if [ -d '${REMOTE_PUBLIC_DIR}' ]; then mv '${REMOTE_PUBLIC_DIR}' '${REMOTE_PUBLIC_DIR}.previous'; fi && \
  mv '${REMOTE_STAGE_DIR}' '${REMOTE_PUBLIC_DIR}' && \
  cp '${REMOTE_PUBLIC_DIR}/index.html' '${REMOTE_PUBLIC_ROOT}/index.html'"
run_ssh "mkdir -p '${REMOTE_CONFIG_DIR}' && rm -rf '${REMOTE_CONFIG_STAGE_DIR}' && mkdir -p '${REMOTE_CONFIG_STAGE_DIR}'"
tar czf - -C "${PUBLISH_CONFIG_DIR}" . | run_ssh "tar xzf - -C '${REMOTE_CONFIG_STAGE_DIR}'"
run_ssh "\
  rm -rf '${REMOTE_CONFIG_DIR}.previous' && \
  if [ -d '${REMOTE_CONFIG_DIR}' ]; then mv '${REMOTE_CONFIG_DIR}' '${REMOTE_CONFIG_DIR}.previous'; fi && \
  mv '${REMOTE_CONFIG_STAGE_DIR}' '${REMOTE_CONFIG_DIR}'"
run_ssh "install -d -m 0755 /etc/containers/systemd && install -m 0644 '${REMOTE_CONFIG_DIR}/${SUBSCRIPTION_CONTAINER_NAME}.container' '${REMOTE_CONTAINER_CONFIG}' && \
systemctl daemon-reload
systemctl enable '${SUBSCRIPTION_CONTAINER_NAME}.service' >/dev/null 2>&1 || true
systemctl restart '${SUBSCRIPTION_CONTAINER_NAME}.service'"

echo "[INFO] Verifying published subscription endpoint"
MIHOMO_VERIFY_FILE="$(mktemp)"
cleanup_verify_file() {
  rm -f "${MIHOMO_VERIFY_FILE}"
}
trap cleanup_verify_file EXIT
for attempt in $(seq 1 10); do
  if curl -fsS --max-time 15 "${PUBLIC_TEST_URL}" >/dev/null && \
     curl -fsS --max-time 15 "${PUBLIC_MIHOMO_URL}" -o "${MIHOMO_VERIFY_FILE}" && \
     grep -Eq 'PROCESS-NAME,wps\.exe|DOMAIN-SUFFIX,wps\.cn' "${MIHOMO_VERIFY_FILE}"; then
    echo "[INFO] Subscription endpoint is ready on attempt ${attempt}."
    echo "[INFO] Subscription publish completed successfully."
    exit 0
  fi
  sleep 2
done

echo "[ERROR] Subscription endpoint did not become ready: ${PUBLIC_TEST_URL}"
exit 4
