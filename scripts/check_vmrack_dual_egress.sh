#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/dual_egress_common.sh"

ROOT_DIR="$(standalone_node_root_dir)"
DEFAULT_NODE="vmrack1"

usage() {
  cat <<'EOF'
Usage: check_vmrack_dual_egress.sh [--node vmrack1] [--dry-run]

Checks WireGuard iface, sing-box dual-egress listeners, and route tags.
EOF
}

DRY_RUN=0
NODE="${DEFAULT_NODE}"

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
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
done

ENV_FILE="${ROOT_DIR}/secrets/nodes/${NODE}.env"
WG_IFACE="$(grep -E '^WIREGUARD_INTERFACE=' "${ENV_FILE}" | cut -d= -f2-)"
WG_BIND="$(grep -E '^WG_BIND_ADDRESS=' "${ENV_FILE}" | cut -d= -f2-)"
BASE_PORT="$(dual_egress_node_field "${ROOT_DIR}" "${NODE}" "base_port")"
PUBLIC_PORT=$((BASE_PORT + 3))
HY2_PORT=$((BASE_PORT + 5))
QQPW_PORT=$((BASE_PORT + 6))
QQPW_SOCKS_PORT=$((BASE_PORT + 7))

IFS=$'\t' read -r HOST SSH_PORT SSH_USER < <(standalone_node_resolve_ssh_target "${ROOT_DIR}" "${NODE}")
SSH_TARGET="${SSH_USER}@${HOST}"
SSH_OPTS=(
  -p "${SSH_PORT}"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o ConnectTimeout=15
)
REMOTE_DIR="${REMOTE_PROXY_REMOTE_DIR:-/root/remote_proxy}"

echo "[INFO] Checking dual egress on ${NODE} (${HOST})"
printf '  - wg show %s\n' "${WG_IFACE}"
printf '  - listeners %s/%s/%s/%s\n' "${PUBLIC_PORT}" "${HY2_PORT}" "${QQPW_PORT}" "${QQPW_SOCKS_PORT}"
printf '  - sing-box config contains direct-wg bind %s\n' "${WG_BIND}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote checks executed."
  exit 0
fi

SSH_PASSWORD="$(standalone_node_optional_ssh_password "${NODE}")"
standalone_node_ssh "${SSH_PASSWORD}" "${SSH_OPTS[@]}" "${SSH_TARGET}" bash -s <<EOF
set -euo pipefail
WG_IFACE='${WG_IFACE}'
WG_BIND='${WG_BIND}'
PUBLIC_PORT='${PUBLIC_PORT}'
HY2_PORT='${HY2_PORT}'
QQPW_PORT='${QQPW_PORT}'
QQPW_SOCKS_PORT='${QQPW_SOCKS_PORT}'
REMOTE_DIR='${REMOTE_DIR}'
wg show "\${WG_IFACE}" >/dev/null
ss -lntu | grep -E ":(\${PUBLIC_PORT}|\${HY2_PORT}|\${QQPW_PORT}|\${QQPW_SOCKS_PORT})\\b" >/dev/null
CONFIG="\${REMOTE_DIR}/singbox.json"
if [[ ! -f "\${CONFIG}" ]]; then
  CONFIG=/var/lib/remote_proxy/singbox/config.json
fi
# Prefer runtime rendered config for dual-egress assertions.
if [[ -f /var/lib/remote_proxy/singbox/config.json ]]; then
  CONFIG=/var/lib/remote_proxy/singbox/config.json
fi
grep -q 'direct-wg' "\${CONFIG}"
grep -q "\${WG_BIND}" "\${CONFIG}"
grep -q 'hysteria2-in' "\${CONFIG}"
grep -q 'vless-qqpw-in' "\${CONFIG}"
grep -q 'socks-qqpw-in' "\${CONFIG}"
systemctl is-active remote-proxy >/dev/null || systemctl --user is-active remote-proxy >/dev/null
echo '[OK] dual egress remote checks passed'
EOF
