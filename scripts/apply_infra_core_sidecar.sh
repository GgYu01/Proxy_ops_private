#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${ROOT_DIR}/generated/infra-core/vless-sidecar/config.json"
REMOTE_HOST="${REMOTE_HOST:-112.28.134.53}"
REMOTE_USER="${REMOTE_USER:-gaoyx}"
REMOTE_PORT="${REMOTE_PORT:-52117}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:-666666}"
REMOTE_SERVICE_DIR="${REMOTE_SERVICE_DIR:-/mnt/hdo/infra-core/services/proxied/vless-sidecar}"
REMOTE_HOST_CONFIG_PATH="${REMOTE_HOST_CONFIG_PATH:-${REMOTE_SERVICE_DIR}/config.json}"
REMOTE_APPLY_SCRIPT="${REMOTE_APPLY_SCRIPT:-${REMOTE_SERVICE_DIR}/apply_runtime_routing.sh}"
REMOTE_CONTAINER_NAME="${REMOTE_CONTAINER_NAME:-infra_vless_sidecar}"
SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"

usage() {
  cat <<'EOF'
Usage: apply_infra_core_sidecar.sh [--dry-run] [--full-restart]
EOF
}

DRY_RUN=0
FULL_RESTART=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --full-restart)
      FULL_RESTART=1
      shift
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "[ERROR] Missing generated config: ${CONFIG_PATH}"
  exit 2
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

echo "[INFO] Infra-core target: Ubuntu.online"
echo "[INFO] Generated config: ${CONFIG_PATH}"
echo "[INFO] Default path: hot reload"
echo "[INFO] Remote host: ${SSH_TARGET}:${REMOTE_PORT}"
echo "[INFO] Remote config path: ${REMOTE_HOST_CONFIG_PATH}"
echo "[INFO] Hot reload sequence:"
printf '  - %s\n' "upload generated config.json" "sing-box check" "apply_runtime_routing.sh" "verify StartedAt and RestartCount unchanged"
echo "[INFO] Full restart fallback:"
printf '  - %s\n' "docker compose up -d vless-sidecar" "recreate only if container-shape changes"

if [[ "${FULL_RESTART}" -eq 1 ]]; then
  echo "[INFO] Mode override: full restart requested"
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote changes applied."
  exit 0
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
remote_tmp_path="${REMOTE_HOST_CONFIG_PATH}.codex.tmp"

echo "[INFO] Uploading generated config to ${SSH_TARGET}"
run_scp "${CONFIG_PATH}" "${SSH_TARGET}:${remote_tmp_path}"

echo "[INFO] Applying hot reload on remote sidecar"
run_ssh "set -euo pipefail;
backup_path='${REMOTE_HOST_CONFIG_PATH}.bak.${timestamp}';
cp -a '${REMOTE_HOST_CONFIG_PATH}' \"\${backup_path}\";
mv '${remote_tmp_path}' '${REMOTE_HOST_CONFIG_PATH}';
HOST_CONFIG_PATH='${REMOTE_HOST_CONFIG_PATH}' bash '${REMOTE_APPLY_SCRIPT}';
echo \"[INFO] Backup path: \${backup_path}\""

echo "[INFO] Remote post-check"
run_ssh "set -euo pipefail;
docker inspect '${REMOTE_CONTAINER_NAME}' --format 'StartedAt={{.State.StartedAt}} RestartCount={{.RestartCount}} Health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}';
python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path('${REMOTE_HOST_CONFIG_PATH}').read_text(encoding='utf-8'))
print('outbounds=' + ','.join(item.get('tag', '') for item in cfg.get('outbounds', [])))
print('final=' + str(cfg.get('route', {}).get('final')))
PY"

echo "[INFO] Infra-core sidecar config applied successfully."
