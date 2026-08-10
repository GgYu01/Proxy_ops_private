#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/dual_egress_common.sh"

ROOT_DIR="$(standalone_node_root_dir)"
PUBLIC_REPO_DIR="$(cd "${ROOT_DIR}/../remote_proxy" && pwd -P)"
DEFAULT_NODE="vmrack1"

usage() {
  cat <<'EOF'
Usage: apply_vmrack_dual_egress.sh [--node vmrack1] [--dry-run]

Applies WireGuard + dual-egress sing-box on the node:
  public VLESS  -> host public IP
  Hy2 + qqpw VLESS + qqpw SOCKS5 -> wg0 bind (residential NAT)

Requires real WIREGUARD_PRIVATE_KEY / WIREGUARD_PEER_PUBLIC_KEY in secrets.
Optional live env:
  REMOTE_PROXY_SSH_PASSWORD_<NODE>
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
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[ERROR] missing ${ENV_FILE}" >&2
  exit 1
fi

if ! grep -Eq '^ENABLE_DUAL_EGRESS=true$' "${ENV_FILE}"; then
  echo "[ERROR] ${ENV_FILE} must set ENABLE_DUAL_EGRESS=true" >&2
  exit 1
fi

REMOTE_DIR="${REMOTE_PROXY_REMOTE_DIR:-/root/remote_proxy}"
WG_IFACE="$(grep -E '^WIREGUARD_INTERFACE=' "${ENV_FILE}" | cut -d= -f2-)"
HY2_CERT="$(grep -E '^HYSTERIA2_TLS_CERT_PATH=' "${ENV_FILE}" | cut -d= -f2-)"
HY2_KEY="$(grep -E '^HYSTERIA2_TLS_KEY_PATH=' "${ENV_FILE}" | cut -d= -f2-)"
HY2_SNI="$(grep -E '^HYSTERIA2_SNI=' "${ENV_FILE}" | cut -d= -f2-)"

BUNDLE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/dual-egress-${NODE}.XXXXXX")"
cleanup() { rm -rf "${BUNDLE_DIR}"; }
trap cleanup EXIT

echo "[INFO] Applying dual egress to ${NODE}"
echo "[INFO] Expected remote actions:"
printf '  - %s\n' \
  "install wireguard-tools if missing" \
  "install /etc/wireguard/${WG_IFACE}.conf and systemctl enable --now wg-quick@${WG_IFACE}" \
  "ensure Hy2 TLS cert at ${HY2_CERT}" \
  "sync ${REMOTE_DIR} and run scripts/deploy.sh (sing-box dual egress)"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote apply executed (secrets/WG key validation deferred until live apply)."
  exit 0
fi

IFS=$'\t' read -r HOST SSH_PORT SSH_USER < <(standalone_node_resolve_ssh_target "${ROOT_DIR}" "${NODE}")
SSH_TARGET="${SSH_USER}@${HOST}"
SSH_OPTS=(
  -p "${SSH_PORT}"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o ConnectTimeout=15
)
SCP_OPTS=(
  -P "${SSH_PORT}"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o ConnectTimeout=15
)

standalone_node_prepare_bundle "${ROOT_DIR}" "${PUBLIC_REPO_DIR}" "${NODE}" "${BUNDLE_DIR}"
dual_egress_render_wg_conf "${ENV_FILE}" > "${BUNDLE_DIR}/wg0.conf"

echo "[INFO] Bundle prepared at ${BUNDLE_DIR} for ${HOST}"

SSH_PASSWORD="$(standalone_node_optional_ssh_password "${NODE}")"
REMOTE_STAGE="/tmp/dual-egress-${NODE}-$$"
standalone_node_ssh "${SSH_PASSWORD}" "${SSH_OPTS[@]}" "${SSH_TARGET}" "rm -rf '${REMOTE_STAGE}' && mkdir -p '${REMOTE_STAGE}'"
if [[ -n "${SSH_PASSWORD}" ]]; then
  SSHPASS="${SSH_PASSWORD}" sshpass -e scp "${SCP_OPTS[@]}" -r "${BUNDLE_DIR}/." "${SSH_TARGET}:${REMOTE_STAGE}/"
else
  scp "${SCP_OPTS[@]}" -r "${BUNDLE_DIR}/." "${SSH_TARGET}:${REMOTE_STAGE}/"
fi

CERT_SCRIPT="$(dual_egress_ensure_hy2_certs_remote "${HY2_CERT}" "${HY2_KEY}" "${HY2_SNI}")"
standalone_node_ssh "${SSH_PASSWORD}" "${SSH_OPTS[@]}" "${SSH_TARGET}" bash -s <<EOF
set -euo pipefail
REMOTE_STAGE='${REMOTE_STAGE}'
REMOTE_DIR='${REMOTE_DIR}'
WG_IFACE='${WG_IFACE}'
${CERT_SCRIPT}
if ! command -v wg >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y wireguard wireguard-tools
  else
    echo '[ERROR] wireguard-tools missing and apt-get unavailable' >&2
    exit 1
  fi
fi
install -m 600 "\${REMOTE_STAGE}/wg0.conf" "/etc/wireguard/\${WG_IFACE}.conf"
systemctl enable --now "wg-quick@\${WG_IFACE}"
wg show "\${WG_IFACE}" >/dev/null
mkdir -p "\${REMOTE_DIR}"
# Prefer rsync when present; otherwise fall back to tar extract (busybox/minimal hosts).
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "\${REMOTE_STAGE}/" "\${REMOTE_DIR}/"
else
  find "\${REMOTE_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  tar -C "\${REMOTE_STAGE}" -cf - . | tar -C "\${REMOTE_DIR}" -xf -
fi
cd "\${REMOTE_DIR}"
chmod +x install.sh scripts/*.sh scripts/lib/*.sh 2>/dev/null || true
# Root deploy reads /etc/remote_proxy/singbox.env (copy-if-missing). Force-sync
# the dual-egress config.env so ENABLE_DUAL_EGRESS and related keys take effect.
mkdir -p /etc/remote_proxy
cp -f "\${REMOTE_DIR}/config.env" /etc/remote_proxy/singbox.env
chmod 600 /etc/remote_proxy/singbox.env
# Dual-egress proxy path always uses sing-box even if cliproxy-plus is also present.
systemctl reset-failed remote-proxy 2>/dev/null || true
REMOTE_PROXY_SINGBOX_ENV_FILE=/etc/remote_proxy/singbox.env \
REMOTE_PROXY_SERVICE=singbox ./scripts/deploy.sh
# Give systemd/podman a moment before listener checks.
sleep 2
systemctl is-active remote-proxy >/dev/null
rm -rf "\${REMOTE_STAGE}"
echo '[OK] dual egress apply complete'
EOF

echo "[OK] Applied dual egress on ${NODE}"
