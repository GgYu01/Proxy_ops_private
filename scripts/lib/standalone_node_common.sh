#!/usr/bin/env bash
set -euo pipefail

standalone_node_root_dir() {
  if [[ -n "${PROXY_OPS_PRIVATE_ROOT_OVERRIDE:-}" ]]; then
    printf '%s\n' "${PROXY_OPS_PRIVATE_ROOT_OVERRIDE}"
    return 0
  fi
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
  printf '%s\n' "${script_dir}"
}

standalone_node_public_repo_dir() {
  local root_dir="$1"
  if [[ -n "${REMOTE_PROXY_PUBLIC_REPO_DIR:-}" ]]; then
    printf '%s\n' "${REMOTE_PROXY_PUBLIC_REPO_DIR}"
    return 0
  fi
  printf '%s\n' "${root_dir}/../remote_proxy"
}

standalone_node_password_env_name() {
  local node_name="$1"
  local upper_name
  upper_name="$(printf '%s' "${node_name}" | tr '[:lower:]-' '[:upper:]_')"
  printf 'REMOTE_PROXY_SSH_PASSWORD_%s\n' "${upper_name}"
}

standalone_node_inventory_field() {
  local root_dir="$1"
  local node_name="$2"
  local field_name="$3"
  python3 - <<'PY' "${root_dir}" "${node_name}" "${field_name}"
from pathlib import Path
import sys
import yaml

root = Path(sys.argv[1])
node_name = sys.argv[2]
field_name = sys.argv[3]
payload = yaml.safe_load((root / "inventory" / "nodes.yaml").read_text(encoding="utf-8")) or {}
nodes = payload.get("nodes", [])
node = next((item for item in nodes if item.get("name") == node_name), None)
if node is None:
    raise SystemExit(f"Unknown node: {node_name}")
value = node.get(field_name, "")
if value is None:
    value = ""
print(value)
PY
}

standalone_node_resolve_ssh_target() {
  local root_dir="$1"
  local node_name="$2"
  local host
  local ssh_port
  local ssh_user
  host="$(standalone_node_inventory_field "${root_dir}" "${node_name}" "host")"
  ssh_port="$(standalone_node_inventory_field "${root_dir}" "${node_name}" "ssh_port")"
  ssh_user="$(standalone_node_inventory_field "${root_dir}" "${node_name}" "ssh_user")"
  if [[ -z "${ssh_user}" ]]; then
    ssh_user="${REMOTE_PROXY_SSH_USER:-root}"
  fi
  printf '%s\t%s\t%s\n' "${host}" "${ssh_port}" "${ssh_user}"
}

standalone_node_runtime_service() {
  local root_dir="$1"
  local node_name="$2"
  standalone_node_inventory_field "${root_dir}" "${node_name}" "runtime_service"
}

standalone_node_proxy_domain() {
  local root_dir="$1"
  local node_name="$2"
  standalone_node_inventory_field "${root_dir}" "${node_name}" "proxy_domain"
}

standalone_node_set_env_value() {
  local env_file="$1"
  local key="$2"
  local value="$3"
  local tmp_file

  tmp_file="$(mktemp "${env_file}.XXXXXX")"
  awk -v key="$key" -v value="$value" '
    BEGIN { replaced = 0 }
    $0 ~ "^" key "=" {
      print key "=" value
      replaced = 1
      next
    }
    { print }
    END {
      if (replaced == 0) {
        print key "=" value
      }
    }
  ' "$env_file" > "$tmp_file"
  mv "$tmp_file" "$env_file"
}

standalone_node_systemd_service_name() {
  local runtime_service="$1"
  case "${runtime_service}" in
    cliproxy-plus)
      printf 'cliproxy-plus\n'
      ;;
    singbox)
      printf 'remote-proxy\n'
      ;;
    *)
      echo "[ERROR] Unsupported runtime service: ${runtime_service}" >&2
      return 1
      ;;
  esac
}

standalone_node_install_command() {
  local runtime_service="$1"
  printf './install.sh %s\n' "${runtime_service}"
}

standalone_node_verify_command() {
  local runtime_service="$1"
  case "${runtime_service}" in
    cliproxy-plus)
      printf './scripts/service.sh cliproxy-plus verify\n'
      ;;
    singbox)
      printf './scripts/verify.sh\n'
      ;;
    *)
      echo "[ERROR] Unsupported runtime service: ${runtime_service}" >&2
      return 1
      ;;
  esac
}

standalone_node_require_ssh_password() {
  local node_name="$1"
  local env_name="${REMOTE_PROXY_SSH_PASSWORD_ENV:-}"
  if [[ -z "${env_name}" ]]; then
    env_name="$(standalone_node_password_env_name "${node_name}")"
  fi
  local password="${!env_name:-}"
  if [[ -z "${password}" ]]; then
    echo "[ERROR] Missing SSH password env: ${env_name}" >&2
    return 1
  fi
  printf '%s\n' "${password}"
}

standalone_node_prepare_bundle() {
  local root_dir="$1"
  local public_repo_dir="$2"
  local node_name="$3"
  local bundle_dir="$4"
  local env_path="${root_dir}/secrets/nodes/${node_name}.env"

  if [[ ! -f "${env_path}" ]]; then
    echo "[ERROR] Missing node env: ${env_path}" >&2
    return 1
  fi
  if [[ ! -d "${public_repo_dir}" ]]; then
    echo "[ERROR] Missing public baseline repo: ${public_repo_dir}" >&2
    return 1
  fi

  rm -rf "${bundle_dir}"
  mkdir -p "${bundle_dir}"
  cp "${env_path}" "${bundle_dir}/config.env"
  local proxy_domain
  proxy_domain="$(standalone_node_proxy_domain "${root_dir}" "${node_name}")"
  if [[ -n "${proxy_domain}" ]]; then
    standalone_node_set_env_value "${bundle_dir}/config.env" "PROXY_PUBLIC_HOST" "${proxy_domain}"
  fi
  cp "${public_repo_dir}/install.sh" "${bundle_dir}/install.sh"
  cp "${public_repo_dir}/config.env.example" "${bundle_dir}/config.env.example"
  mkdir -p "${bundle_dir}/config"
  cp "${public_repo_dir}/config/cliproxy-plus.env" "${bundle_dir}/config/cliproxy-plus.env"
  cp "${public_repo_dir}/config/cliproxy-plus.env.example" "${bundle_dir}/config/cliproxy-plus.env.example"
  cp -R "${public_repo_dir}/scripts" "${bundle_dir}/scripts"

  (
    cd "${bundle_dir}"
    python3 scripts/gen_config.py >/dev/null
  )
}
