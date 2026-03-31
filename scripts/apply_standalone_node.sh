#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLIC_REPO_DIR="${ROOT_DIR}/../remote_proxy"

usage() {
  cat <<'EOF'
Usage: apply_standalone_node.sh [--dry-run] --node <dedirock|akilecloud>
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

if [[ "${NODE}" == "lisahost" ]]; then
  echo "[ERROR] lisahost is frozen and must not be changed."
  exit 2
fi

ENV_PATH="${ROOT_DIR}/secrets/nodes/${NODE}.env"
if [[ ! -f "${ENV_PATH}" ]]; then
  echo "[ERROR] Missing node env: ${ENV_PATH}"
  exit 3
fi

HOST="$(python3 - <<'PY' "${ROOT_DIR}" "${NODE}"
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
node_name = sys.argv[2]
inventory = json.loads((root / "inventory" / "nodes.yaml").read_text(encoding="utf-8"))
node = next(item for item in inventory["nodes"] if item["name"] == node_name)
print(node["host"])
PY
)"

BUNDLE_DIR="${ROOT_DIR}/generated/standalone/${NODE}"
mkdir -p "${BUNDLE_DIR}/scripts"
cp "${ENV_PATH}" "${BUNDLE_DIR}/config.env"
(cd "${BUNDLE_DIR}" && python3 "${PUBLIC_REPO_DIR}/scripts/gen_config.py" >/dev/null)
cp "${PUBLIC_REPO_DIR}/install.sh" "${BUNDLE_DIR}/install.sh"
cp "${PUBLIC_REPO_DIR}/config.env.example" "${BUNDLE_DIR}/config.env.example"
cp "${PUBLIC_REPO_DIR}"/scripts/*.sh "${BUNDLE_DIR}/scripts/"
cp "${PUBLIC_REPO_DIR}/scripts/gen_config.py" "${BUNDLE_DIR}/scripts/gen_config.py"

echo "[INFO] Target node: ${NODE}"
echo "[INFO] Target host: ${HOST}"
echo "[INFO] Bundle dir: ${BUNDLE_DIR}"
echo "[INFO] Files to upload:"
printf '  - %s\n' "${BUNDLE_DIR}/config.env" "${BUNDLE_DIR}/singbox.json" "${BUNDLE_DIR}/install.sh"
echo "[INFO] Remote backup targets:"
printf '  - %s\n' "/root/remote_proxy/config.env" "/root/remote_proxy/singbox.json" "/etc/systemd/system/remote-proxy.service"
echo "[INFO] Verification commands:"
printf '  - %s\n' "systemctl is-active remote-proxy" "podman ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'" "ss -ltnp | grep 1000"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote changes applied."
  exit 0
fi

echo "[ERROR] Live apply not implemented yet in this revision."
exit 4
