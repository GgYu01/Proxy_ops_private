#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/standalone_node_common.sh"

ROOT_DIR="$(standalone_node_root_dir)"
PUBLIC_REPO_DIR="$(standalone_node_public_repo_dir "${ROOT_DIR}")"

usage() {
  cat <<'EOF'
Usage: apply_standalone_node.sh [--dry-run] --node <node-name>

Optional live env:
  REMOTE_PROXY_SSH_PASSWORD_<NODE>
  If absent, the script uses the existing SSH key/agent configuration.

Optional env:
  REMOTE_PROXY_SSH_USER
  REMOTE_PROXY_REMOTE_DIR
  REMOTE_PROXY_BACKUP_DIR
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
INSTALL_COMMAND="$(standalone_node_install_command "${RUNTIME_SERVICE}")"
VERIFY_COMMAND="$(standalone_node_verify_command "${RUNTIME_SERVICE}")"

BUNDLE_DIR="${ROOT_DIR}/generated/standalone/${NODE}"
standalone_node_prepare_bundle "${ROOT_DIR}" "${PUBLIC_REPO_DIR}" "${NODE}" "${BUNDLE_DIR}"

REMOTE_DIR="${REMOTE_PROXY_REMOTE_DIR:-/root/remote_proxy}"
REMOTE_BACKUP_DIR="${REMOTE_PROXY_BACKUP_DIR:-/root/remote_proxy_backups}"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
SSH_TARGET="${SSH_USER}@${HOST}"
SSH_OPTS=(
  -p "${SSH_PORT}"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o ConnectTimeout=15
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
)

echo "[INFO] Target node: ${NODE}"
echo "[INFO] Target host: ${HOST}"
echo "[INFO] SSH target: ${SSH_TARGET}:${SSH_PORT}"
echo "[INFO] Bundle dir: ${BUNDLE_DIR}"
echo "[INFO] Files to upload:"
printf '  - %s\n' \
  "${BUNDLE_DIR}/config.env" \
  "${BUNDLE_DIR}/config/cliproxy-plus.env" \
  "${BUNDLE_DIR}/config/cliproxy-plus.env.example" \
  "${BUNDLE_DIR}/singbox.json" \
  "${BUNDLE_DIR}/install.sh" \
  "${BUNDLE_DIR}/scripts/lib/runtime_compat.sh"
echo "[INFO] Remote backup targets:"
printf '  - %s\n' \
  "${REMOTE_DIR}" \
  "${REMOTE_BACKUP_DIR}/${NODE}/${TIMESTAMP}" \
  "/etc/remote_proxy" \
  "/var/lib/remote_proxy" \
  "/etc/systemd/system/${SYSTEMD_SERVICE}.service" \
  "/etc/containers/systemd/${SYSTEMD_SERVICE}.container"
echo "[INFO] Verification commands:"
printf '  - %s\n' \
  "${VERIFY_COMMAND}" \
  "systemctl is-active ${SYSTEMD_SERVICE}" \
  "systemctl cat ${SYSTEMD_SERVICE}" \
  "podman ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep ${SYSTEMD_SERVICE}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote changes applied."
  exit 0
fi

SSH_PASSWORD="$(standalone_node_optional_ssh_password "${NODE}")"

run_ssh() {
  standalone_node_ssh "${SSH_PASSWORD}" "${SSH_OPTS[@]}" "${SSH_TARGET}" "$@"
}

remote_runtime_ready() {
  run_ssh "command -v curl >/dev/null && command -v jq >/dev/null && command -v podman >/dev/null && command -v systemctl >/dev/null && python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'" >/dev/null 2>&1
}

echo "[INFO] Creating remote backup and preparing remote workdir..."
run_ssh "mkdir -p '${REMOTE_BACKUP_DIR}/${NODE}/${TIMESTAMP}' && if [ -d '${REMOTE_DIR}' ]; then cp -a '${REMOTE_DIR}' '${REMOTE_BACKUP_DIR}/${NODE}/${TIMESTAMP}/remote_proxy_workdir'; fi && if [ -d '/etc/remote_proxy' ]; then cp -a '/etc/remote_proxy' '${REMOTE_BACKUP_DIR}/${NODE}/${TIMESTAMP}/etc_remote_proxy'; fi && if [ -d '/var/lib/remote_proxy' ]; then cp -a '/var/lib/remote_proxy' '${REMOTE_BACKUP_DIR}/${NODE}/${TIMESTAMP}/var_lib_remote_proxy'; fi && if [ -f '/etc/systemd/system/${SYSTEMD_SERVICE}.service' ]; then cp -a '/etc/systemd/system/${SYSTEMD_SERVICE}.service' '${REMOTE_BACKUP_DIR}/${NODE}/${TIMESTAMP}/${SYSTEMD_SERVICE}.service'; fi && if [ -f '/etc/containers/systemd/${SYSTEMD_SERVICE}.container' ]; then cp -a '/etc/containers/systemd/${SYSTEMD_SERVICE}.container' '${REMOTE_BACKUP_DIR}/${NODE}/${TIMESTAMP}/${SYSTEMD_SERVICE}.container'; fi && rm -rf '${REMOTE_DIR}' && mkdir -p '${REMOTE_DIR}'"

echo "[INFO] Uploading bundle..."
tar -C "${BUNDLE_DIR}" -czf - . | standalone_node_ssh "${SSH_PASSWORD}" "${SSH_OPTS[@]}" "${SSH_TARGET}" "tar -xzf - -C '${REMOTE_DIR}'"

echo "[INFO] Running remote install..."
INSTALL_ENV_PREFIX=""
if remote_runtime_ready; then
  echo "[INFO] Remote runtime already satisfies curl/jq/podman/python3 prerequisites; skipping package refresh/install."
  INSTALL_ENV_PREFIX="SETUP_ENV_SKIP_PACKAGE_REFRESH=true SETUP_ENV_SKIP_PACKAGE_INSTALL=true"
fi
run_ssh "cd '${REMOTE_DIR}' && chmod +x install.sh scripts/*.sh scripts/lib/*.sh scripts/services/cliproxy_plus/*.sh && ${INSTALL_ENV_PREFIX} ${INSTALL_COMMAND}"

echo "[INFO] Running remote verification..."
run_ssh "cd '${REMOTE_DIR}' && ${VERIFY_COMMAND} && systemctl is-active ${SYSTEMD_SERVICE} >/dev/null && systemctl cat ${SYSTEMD_SERVICE} >/dev/null && podman ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep ${SYSTEMD_SERVICE}"

echo "[OK] Live apply completed for ${NODE}."
echo "[OK] Rollback backup: ${REMOTE_BACKUP_DIR}/${NODE}/${TIMESTAMP}"
