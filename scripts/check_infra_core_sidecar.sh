#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-112.28.134.53}"
REMOTE_USER="${REMOTE_USER:-gaoyx}"
REMOTE_PORT="${REMOTE_PORT:-52117}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:-666666}"
REMOTE_SERVICE_DIR="${REMOTE_SERVICE_DIR:-/mnt/hdo/infra-core/services/proxied/vless-sidecar}"
REMOTE_HOST_CONFIG_PATH="${REMOTE_HOST_CONFIG_PATH:-${REMOTE_SERVICE_DIR}/config.json}"
REMOTE_CONTAINER_NAME="${REMOTE_CONTAINER_NAME:-infra_vless_sidecar}"
SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"

usage() {
  cat <<'EOF'
Usage: check_infra_core_sidecar.sh [--dry-run]
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

echo "[INFO] Infra-core sidecar checks:"
printf '  - %s\n' "docker inspect infra_vless_sidecar" "mounted config path" "rendered outbounds contain proxy_failover" "selector default matches priority policy"
echo "[INFO] Remote host: ${SSH_TARGET}:${REMOTE_PORT}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote checks executed."
  exit 0
fi

run_ssh "set -euo pipefail;
docker inspect '${REMOTE_CONTAINER_NAME}' --format 'StartedAt={{.State.StartedAt}} RestartCount={{.RestartCount}} Health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}';
python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path('${REMOTE_HOST_CONFIG_PATH}').read_text(encoding='utf-8'))
outbounds = [item.get('tag', '') for item in cfg.get('outbounds', [])]
print('outbounds=' + ','.join(outbounds))
print('final=' + str(cfg.get('route', {}).get('final')))
selector = next((item for item in cfg.get('outbounds', []) if item.get('tag') == 'proxy_failover'), None)
if selector is None:
    raise SystemExit('proxy_failover outbound missing')
print('selector_default=' + str(selector.get('default')))
print('selector_members=' + ','.join(selector.get('outbounds', [])))
if selector.get('default') != 'proxy_lisahost':
    raise SystemExit('proxy_failover default is not proxy_lisahost')
if selector.get('outbounds') != ['proxy_lisahost', 'proxy_akilecloud', 'proxy_dedirock']:
    raise SystemExit('proxy_failover priority order drifted')
if cfg.get('route', {}).get('final') != 'direct':
    raise SystemExit('route.final drifted from direct')
PY"

echo "[INFO] Infra-core sidecar checks passed."
