#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage: check_standalone_node.sh --node <lisahost|dedirock|akilecloud> [--dry-run]
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

HOST="$(python3 - <<'PY' "${ROOT_DIR}" "${NODE}"
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
node_name = sys.argv[2]
inventory = json.loads((root / "inventory" / "nodes.yaml").read_text(encoding="utf-8"))
node = next(item for item in inventory["nodes"] if item["name"] == node_name)
print(node["host"])
PY
)"

echo "[INFO] Checking node ${NODE} (${HOST})"
echo "[INFO] Expected checks:"
printf '  - %s\n' "systemctl is-active remote-proxy" "systemctl cat remote-proxy" "podman ps" "ss -ltnp"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote checks executed."
  exit 0
fi

echo "[ERROR] Live check not implemented yet in this revision."
exit 4
