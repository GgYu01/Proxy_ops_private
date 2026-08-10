#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
WORKSPACE_ROOT="$(cd "${ROOT_DIR}/../.." && pwd -P)"
DEFAULT_WINDOWS_VENV_PYTHON="${WORKSPACE_ROOT}/.venv/Scripts/python.exe"
if [[ -z "${PYTHON:-}" && -x "${DEFAULT_WINDOWS_VENV_PYTHON}" ]]; then
  PYTHON="${DEFAULT_WINDOWS_VENV_PYTHON}"
else
  PYTHON="${PYTHON:-python3}"
fi
if ! command -v "${PYTHON}" >/dev/null 2>&1 && [[ ! -x "${PYTHON}" ]]; then
  PYTHON=python
fi

usage() {
  cat <<'EOF'
Usage: sync_vmrack_qqpw.sh [--dry-run] [--skip-apply] [--skip-publish] [--static-probe] [--refresh-local]

Full sync loop for vmrack/qqpw dual egress:
  1) validate inventory/secrets dual-egress model
  2) apply WG + sing-box dual egress to vmrack1 (unless --skip-apply)
  3) remote check listeners / wg0
  4) static (+ optional live) dual-egress IP assertions
  5) render artifacts
  6) publish to SEA (unless --skip-publish)
  7) optional local mihomo profile refresh check
EOF
}

DRY_RUN=0
SKIP_APPLY=0
SKIP_PUBLISH=0
STATIC_PROBE=0
REFRESH_LOCAL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-apply)
      SKIP_APPLY=1
      shift
      ;;
    --skip-publish)
      SKIP_PUBLISH=1
      shift
      ;;
    --static-probe)
      STATIC_PROBE=1
      shift
      ;;
    --refresh-local)
      REFRESH_LOCAL=1
      shift
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

echo "[INFO] Validating dual-egress inventory model"
"${PYTHON}" "${ROOT_DIR}/scripts/probe_dual_egress_ips.py" --static-only

if [[ "${SKIP_APPLY}" -eq 0 ]]; then
  APPLY_ARGS=()
  [[ "${DRY_RUN}" -eq 1 ]] && APPLY_ARGS+=(--dry-run)
  bash "${ROOT_DIR}/scripts/apply_vmrack_dual_egress.sh" "${APPLY_ARGS[@]}"
  if [[ "${DRY_RUN}" -eq 0 ]]; then
    bash "${ROOT_DIR}/scripts/check_vmrack_dual_egress.sh"
  else
    bash "${ROOT_DIR}/scripts/check_vmrack_dual_egress.sh" --dry-run
  fi
else
  echo "[INFO] Skipping remote apply/check (--skip-apply)"
fi

if [[ "${STATIC_PROBE}" -eq 1 || "${DRY_RUN}" -eq 1 ]]; then
  echo "[INFO] Dual-egress probe mode: static-only"
  "${PYTHON}" "${ROOT_DIR}/scripts/probe_dual_egress_ips.py" --static-only
else
  echo "[INFO] Dual-egress probe mode: live exit IP"
  "${PYTHON}" "${ROOT_DIR}/scripts/probe_dual_egress_ips.py"
fi

echo "[INFO] Rendering subscription artifacts"
"${PYTHON}" "${ROOT_DIR}/scripts/render_artifacts.py"

MIHOMO_PATH="${ROOT_DIR}/generated/subscriptions/mihomo-universal.yaml"
QQPW_PATH="${ROOT_DIR}/generated/subscriptions/v2ray_node_qqpw.txt"
VMRACK_PATH="${ROOT_DIR}/generated/subscriptions/v2ray_node_vmrack1.txt"
grep -q 'name: GG-Vmrack1' "${MIHOMO_PATH}"
grep -q 'name: QQPW-Residential-SOCKS5' "${MIHOMO_PATH}"
grep -q 'name: QQPW-Residential-Reality' "${MIHOMO_PATH}"
grep -q 'name: ChatGPT' "${MIHOMO_PATH}"
grep -q 'name: PROXY' "${MIHOMO_PATH}"
! grep -q 'name: Vmrack-Public' "${MIHOMO_PATH}"
! grep -q 'name: QQPW-Residential$' "${MIHOMO_PATH}"
grep -q 'port: 10007' "${MIHOMO_PATH}"
grep -q 'port: 10006' "${MIHOMO_PATH}"
grep -q '@38.65.93.39:10007' "${QQPW_PATH}"
grep -q '@38.65.93.39:10006' "${QQPW_PATH}"
grep -q '@38.65.93.39:10003' "${VMRACK_PATH}"
! grep -q '@38.65.93.39:10003' "${QQPW_PATH}"
! grep -q 'GG-Vmrack1-Hysteria2' "${MIHOMO_PATH}"
grep -q 'DOMAIN-SUFFIX,openai.com,ChatGPT' "${MIHOMO_PATH}"

if [[ "${SKIP_PUBLISH}" -eq 1 || "${DRY_RUN}" -eq 1 ]]; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    bash "${ROOT_DIR}/scripts/publish_subscriptions_to_sea_host.sh" --dry-run
  else
    echo "[INFO] Skipping SEA publish (--skip-publish)"
  fi
else
  if [[ "${STATIC_PROBE}" -eq 1 ]]; then
    SEA_SUBSCRIPTION_DUAL_EGRESS_MODE=static \
      bash "${ROOT_DIR}/scripts/publish_subscriptions_to_sea_host.sh"
  else
    bash "${ROOT_DIR}/scripts/publish_subscriptions_to_sea_host.sh"
  fi
fi

if [[ "${REFRESH_LOCAL}" -eq 1 ]]; then
  echo "[INFO] Checking published mihomo profile contains dual-egress ports"
  curl -fsS "https://subs.sea.prod.gglohh.top/subscriptions/mihomo-universal.yaml" \
    | tee /tmp/mihomo-universal.synced.yaml \
    | grep -E 'QQPW-Residential-SOCKS5|QQPW-Residential-Reality|port: 10007|port: 10006|name: ChatGPT|name: GG-Vmrack1' >/dev/null
  echo "[OK] SEA mihomo profile reachable and contains dual-egress markers"
fi

echo "[OK] sync_vmrack_qqpw completed"
echo "[INFO] Consistency summary:"
printf '  - repo mihomo: %s\n' "${MIHOMO_PATH}"
printf '  - repo qqpw:   %s\n' "${QQPW_PATH}"
printf '  - repo vmrack: %s\n' "${VMRACK_PATH}"
printf '  - SEA URL:     %s\n' "https://subs.sea.prod.gglohh.top/subscriptions/mihomo-universal.yaml"
