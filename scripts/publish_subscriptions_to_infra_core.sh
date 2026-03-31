#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBSCRIPTIONS_DIR="${ROOT_DIR}/generated/subscriptions"
TEMPLATE_COMPOSE_PATH="${ROOT_DIR}/templates/infra_core_proxy_subscriptions/docker-compose.yml"
REMOTE_HOST="${REMOTE_HOST:-112.28.134.53}"
REMOTE_USER="${REMOTE_USER:-gaoyx}"
REMOTE_PORT="${REMOTE_PORT:-52117}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:-666666}"
REMOTE_SERVICE_DIR="${REMOTE_SERVICE_DIR:-/mnt/hdo/infra-core/services/proxy-subscriptions}"
REMOTE_PUBLIC_DIR="${REMOTE_PUBLIC_DIR:-${REMOTE_SERVICE_DIR}/public/subscriptions}"
REMOTE_COMPOSE_PATH="${REMOTE_COMPOSE_PATH:-${REMOTE_SERVICE_DIR}/docker-compose.yml}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions}"
PUBLIC_TEST_URL="${PUBLIC_TEST_URL:-${PUBLIC_BASE_URL}/v2ray_nodes.txt}"
SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"

usage() {
  cat <<'EOF'
Usage: publish_subscriptions_to_infra_core.sh [--dry-run]
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

if [[ ! -f "${TEMPLATE_COMPOSE_PATH}" ]]; then
  echo "[ERROR] Missing compose template: ${TEMPLATE_COMPOSE_PATH}"
  exit 3
fi

run_ssh() {
  SSHPASS="${REMOTE_PASSWORD}" sshpass -e ssh \
    -o StrictHostKeyChecking=no \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -p "${REMOTE_PORT}" \
    "${SSH_TARGET}" \
    "$@"
}

run_scp() {
  SSHPASS="${REMOTE_PASSWORD}" sshpass -e scp \
    -o StrictHostKeyChecking=no \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -P "${REMOTE_PORT}" \
    "$@"
}

echo "[INFO] Publish target: ${SSH_TARGET}:${REMOTE_PORT}"
echo "[INFO] Remote service dir: ${REMOTE_SERVICE_DIR}"
echo "[INFO] Public base URL: ${PUBLIC_BASE_URL}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[INFO] Planned files:"
  find "${SUBSCRIPTIONS_DIR}" -maxdepth 1 -type f | sed 's#^#  - #'
  echo "[DRY-RUN] No remote changes applied."
  exit 0
fi

run_ssh "mkdir -p '${REMOTE_PUBLIC_DIR}'"
run_scp "${TEMPLATE_COMPOSE_PATH}" "${SSH_TARGET}:${REMOTE_COMPOSE_PATH}"
tar czf - -C "${SUBSCRIPTIONS_DIR}" . | run_ssh "mkdir -p '${REMOTE_PUBLIC_DIR}' && tar xzf - -C '${REMOTE_PUBLIC_DIR}'"
run_ssh "cd '${REMOTE_SERVICE_DIR}' && docker compose up -d"

echo "[INFO] Verifying published subscription endpoint"
for attempt in $(seq 1 10); do
  if curl -skf --max-time 15 "${PUBLIC_TEST_URL}" >/dev/null; then
    echo "[INFO] Subscription endpoint is ready on attempt ${attempt}."
    echo "[INFO] Subscription publish completed successfully."
    exit 0
  fi
  sleep 2
done

echo "[ERROR] Subscription endpoint did not become ready: ${PUBLIC_TEST_URL}"
exit 4
