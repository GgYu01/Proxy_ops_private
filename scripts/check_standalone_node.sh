#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/standalone_node_common.sh"

ROOT_DIR="$(standalone_node_root_dir)"

usage() {
  cat <<'EOF'
Usage: check_standalone_node.sh --node <node-name> [--dry-run]

Required live env:
  REMOTE_PROXY_SSH_PASSWORD_<NODE>

Optional env:
  REMOTE_PROXY_SSH_USER
  REMOTE_PROXY_REMOTE_DIR
EOF
}

DRY_RUN=0
NODE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --node)
      NODE="${2:-}"
      shift 2
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${NODE}" ]]; then
  usage >&2
  exit 1
fi

IFS=$'\t' read -r HOST SSH_PORT SSH_USER < <(standalone_node_resolve_ssh_target "${ROOT_DIR}" "${NODE}")
RUNTIME_SERVICE="$(standalone_node_runtime_service "${ROOT_DIR}" "${NODE}")"
SYSTEMD_SERVICE="$(standalone_node_systemd_service_name "${RUNTIME_SERVICE}")"
VERIFY_COMMAND="$(standalone_node_verify_command "${RUNTIME_SERVICE}")"
REMOTE_DIR="${REMOTE_PROXY_REMOTE_DIR:-/root/remote_proxy}"
SSH_TARGET="${SSH_USER}@${HOST}"
SSH_OPTS=(
  -p "${SSH_PORT}"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o ConnectTimeout=15
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
)

echo "[INFO] Checking node ${NODE} (${HOST})"
echo "[INFO] SSH target: ${SSH_TARGET}:${SSH_PORT}"
echo "[INFO] Expected checks:"
printf '  - %s\n' \
  "cd ${REMOTE_DIR} && ${VERIFY_COMMAND}" \
  "systemctl is-active ${SYSTEMD_SERVICE}" \
  "systemctl cat ${SYSTEMD_SERVICE}" \
  "podman ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep ${SYSTEMD_SERVICE}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote checks executed."
  exit 0
fi

SSH_PASSWORD="$(standalone_node_require_ssh_password "${NODE}")"
SSHPASS="${SSH_PASSWORD}" sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" \
  "cd '${REMOTE_DIR}' && ${VERIFY_COMMAND} && systemctl is-active ${SYSTEMD_SERVICE} && systemctl cat ${SYSTEMD_SERVICE} && podman ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep ${SYSTEMD_SERVICE}"
