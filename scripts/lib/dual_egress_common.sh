#!/usr/bin/env bash
# Shared helpers for vmrack1 WireGuard + dual-egress sing-box apply/check.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/standalone_node_common.sh"

dual_egress_python() {
  standalone_node_python
}

dual_egress_node_field() {
  local root_dir="$1"
  local node_name="$2"
  local expression="$3"
  "$(dual_egress_python)" - "$root_dir" "$node_name" "$expression" <<'PY'
import sys
from pathlib import Path

import yaml

root = Path(sys.argv[1])
node_name = sys.argv[2]
expression = sys.argv[3]
payload = yaml.safe_load((root / "inventory" / "nodes.yaml").read_text(encoding="utf-8"))
node = next(item for item in payload["nodes"] if item["name"] == node_name)
current = node
for part in expression.split("."):
    if part.endswith("]"):
        key, _, index = part[:-1].partition("[")
        current = current[key][int(index)]
    else:
        current = current[part]
if current is None:
    raise SystemExit(1)
print(current)
PY
}

dual_egress_require_secret() {
  local env_file="$1"
  local key="$2"
  local value
  value="$(grep -E "^${key}=" "${env_file}" | head -n1 | cut -d= -f2- || true)"
  if [[ -z "${value}" || "${value}" == PLACEHOLDER* || "${value}" == placeholder ]]; then
    echo "[ERROR] ${env_file}: ${key} must be set to a real value (not placeholder)" >&2
    return 1
  fi
  printf '%s\n' "${value}"
}

dual_egress_render_wg_conf() {
  local env_file="$1"
  local iface address peer_endpoint peer_allowed_ips keepalive private_key peer_public_key
  local listen_port table post_up post_down
  iface="$(grep -E '^WIREGUARD_INTERFACE=' "${env_file}" | cut -d= -f2-)"
  address="$(grep -E '^WIREGUARD_ADDRESS=' "${env_file}" | cut -d= -f2-)"
  peer_endpoint="$(grep -E '^WIREGUARD_PEER_ENDPOINT=' "${env_file}" | cut -d= -f2- || true)"
  peer_allowed_ips="$(grep -E '^WIREGUARD_PEER_ALLOWED_IPS=' "${env_file}" | cut -d= -f2-)"
  keepalive="$(grep -E '^WIREGUARD_PERSISTENT_KEEPALIVE=' "${env_file}" | cut -d= -f2- || true)"
  listen_port="$(grep -E '^WIREGUARD_LISTEN_PORT=' "${env_file}" | cut -d= -f2- || true)"
  table="$(grep -E '^WIREGUARD_TABLE=' "${env_file}" | cut -d= -f2- || true)"
  post_up="$(grep -E '^WIREGUARD_POST_UP=' "${env_file}" | cut -d= -f2- || true)"
  post_down="$(grep -E '^WIREGUARD_POST_DOWN=' "${env_file}" | cut -d= -f2- || true)"
  private_key="$(dual_egress_require_secret "${env_file}" WIREGUARD_PRIVATE_KEY)"
  peer_public_key="$(dual_egress_require_secret "${env_file}" WIREGUARD_PEER_PUBLIC_KEY)"
  {
    echo "[Interface]"
    echo "Address = ${address}"
    if [[ -n "${table}" ]]; then
      echo "Table = ${table}"
    fi
    if [[ -n "${post_up}" ]]; then
      echo "PostUp = ${post_up}"
    fi
    if [[ -n "${post_down}" ]]; then
      echo "PostDown = ${post_down}"
    fi
    if [[ -n "${listen_port}" ]]; then
      echo "ListenPort = ${listen_port}"
    fi
    echo "PrivateKey = ${private_key}"
    echo
    echo "[Peer]"
    echo "PublicKey = ${peer_public_key}"
    echo "AllowedIPs = ${peer_allowed_ips}"
    if [[ -n "${peer_endpoint}" ]]; then
      echo "Endpoint = ${peer_endpoint}"
    fi
    if [[ -n "${keepalive}" ]]; then
      echo "PersistentKeepalive = ${keepalive}"
    fi
  }
}

dual_egress_ensure_hy2_certs_remote() {
  local cert_path="$1"
  local key_path="$2"
  local sni="$3"
  cat <<EOF
set -euo pipefail
cert_path='${cert_path}'
key_path='${key_path}'
sni='${sni}'
mkdir -p "\$(dirname "\$cert_path")" "\$(dirname "\$key_path")"
if [[ ! -f "\$cert_path" || ! -f "\$key_path" ]]; then
  openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \\
    -keyout "\$key_path" -out "\$cert_path" \\
    -subj "/CN=\${sni}" >/dev/null 2>&1
  chmod 600 "\$key_path"
  chmod 644 "\$cert_path"
fi
EOF
}
