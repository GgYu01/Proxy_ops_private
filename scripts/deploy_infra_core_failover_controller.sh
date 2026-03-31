#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_SCRIPT="${ROOT_DIR}/scripts/reconcile_infra_core_failover.py"
LOCAL_POLICY="${ROOT_DIR}/generated/infra-core/vless-sidecar/failover_policy.json"
REMOTE_HOST="${REMOTE_HOST:-112.28.134.53}"
REMOTE_USER="${REMOTE_USER:-gaoyx}"
REMOTE_PORT="${REMOTE_PORT:-52117}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:-666666}"
REMOTE_DIR="${REMOTE_DIR:-/mnt/hdo/infra-core/services/proxied/vless-sidecar}"
REMOTE_SCRIPT="${REMOTE_DIR}/reconcile_failover.py"
REMOTE_POLICY="${REMOTE_DIR}/failover_policy.json"
CRON_MARKER="# infra-core-vless-failover"
CRON_LINE="* * * * * /usr/bin/python3 ${REMOTE_SCRIPT} >> ${REMOTE_DIR}/failover.log 2>&1 ${CRON_MARKER}"
SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"

usage() {
  cat <<'EOF'
Usage: deploy_infra_core_failover_controller.sh [--dry-run]
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

echo "[INFO] Deploying failover controller to ${SSH_TARGET}:${REMOTE_PORT}"
echo "[INFO] Remote script path: ${REMOTE_SCRIPT}"
echo "[INFO] Remote policy path: ${REMOTE_POLICY}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[INFO] Planned cron line: ${CRON_LINE}"
  echo "[DRY-RUN] No remote changes applied."
  exit 0
fi

if [[ ! -f "${LOCAL_POLICY}" ]]; then
  echo "[ERROR] Missing generated failover policy: ${LOCAL_POLICY}"
  exit 2
fi

run_scp "${LOCAL_SCRIPT}" "${SSH_TARGET}:${REMOTE_SCRIPT}"
run_scp "${LOCAL_POLICY}" "${SSH_TARGET}:${REMOTE_POLICY}"
run_ssh "chmod +x '${REMOTE_SCRIPT}'"
run_ssh "tmp_file=\$(mktemp); crontab -l 2>/dev/null | grep -v '${CRON_MARKER}' > \"\${tmp_file}\" || true; printf '%s\n' '${CRON_LINE}' >> \"\${tmp_file}\"; crontab \"\${tmp_file}\"; rm -f \"\${tmp_file}\""
run_ssh "/usr/bin/python3 '${REMOTE_SCRIPT}'"

echo "[INFO] Failover controller deployed and executed once."
