#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INVENTORY_PATH="${ROOT_DIR}/inventory/nodes.yaml"
REMOTE_HOST="${REMOTE_HOST:-112.28.134.53}"
REMOTE_USER="${REMOTE_USER:-gaoyx}"
REMOTE_PORT="${REMOTE_PORT:-52117}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:-666666}"
REMOTE_SERVICE_DIR="${REMOTE_SERVICE_DIR:-/mnt/hdo/infra-core/services/proxied/vless-sidecar}"
REMOTE_FAILOVER_STATE_PATH="${REMOTE_FAILOVER_STATE_PATH:-${REMOTE_SERVICE_DIR}/failover_state.json}"
TARGET_CONTAINER="${TARGET_CONTAINER:-cli-proxy-api-plus}"
REMOTE_SIDECAR_CONTAINER_NAME="${REMOTE_SIDECAR_CONTAINER_NAME:-infra_vless_sidecar}"
HELPER_IMAGE="${HELPER_IMAGE:-curlimages/curl:8.12.1}"
DIRECT_PROBE_URLS="${DIRECT_PROBE_URLS:-http://ifconfig.me/ip,http://api.ipify.org}"
PROXIED_TRACE_URLS="${PROXIED_TRACE_URLS:-https://openai.com/cdn-cgi/trace,https://chatgpt.com/cdn-cgi/trace}"
LOG_TAIL="${LOG_TAIL:-80}"
SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"

usage() {
  cat <<'EOF'
Usage: check_infra_core_egress_ip.sh [--container <name>] [--dry-run]
EOF
}

DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --container)
      TARGET_CONTAINER="${2:-}"
      shift 2
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${TARGET_CONTAINER}" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "${INVENTORY_PATH}" ]]; then
  echo "[ERROR] Missing inventory file: ${INVENTORY_PATH}"
  exit 2
fi

run_ssh() {
  SSHPASS="${REMOTE_PASSWORD}" sshpass -e ssh \
    -o StrictHostKeyChecking=no \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -p "${REMOTE_PORT}" \
    "${SSH_TARGET}" \
    "$@"
}

echo "[INFO] Infra-core egress verification"
echo "[INFO] Remote host: ${SSH_TARGET}:${REMOTE_PORT}"
echo "[INFO] Target container: ${TARGET_CONTAINER}"
echo "[INFO] Sidecar container: ${REMOTE_SIDECAR_CONTAINER_NAME}"
echo "[INFO] Matched-rule probe URLs: ${PROXIED_TRACE_URLS}"
echo "[INFO] Default-route probe URLs: ${DIRECT_PROBE_URLS}"
echo "[INFO] Probe strategy:"
printf '  - %s\n' \
  "matched-rule traffic uses Cloudflare trace endpoints that already match proxy_failover rules" \
  "default-route traffic uses plain IP echo endpoints to show what unmatched traffic does today" \
  "helper container fallback keeps the target container network namespace but avoids missing curl/wget problems"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[DRY-RUN] No remote checks executed."
  exit 0
fi

REMOTE_COMMAND="$(cat <<EOF
TARGET_CONTAINER='${TARGET_CONTAINER}' SIDECAR_CONTAINER='${REMOTE_SIDECAR_CONTAINER_NAME}' FAILOVER_STATE_PATH='${REMOTE_FAILOVER_STATE_PATH}' HELPER_IMAGE='${HELPER_IMAGE}' DIRECT_PROBE_URLS='${DIRECT_PROBE_URLS}' PROXIED_TRACE_URLS='${PROXIED_TRACE_URLS}' LOG_TAIL='${LOG_TAIL}' python3 - <<'PY'
import json
import os
import re
import subprocess
import sys


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, encoding='utf-8', capture_output=True, check=check)


def run_shell(container: str, shell_command: str) -> subprocess.CompletedProcess[str]:
    return run(['docker', 'exec', container, 'sh', '-lc', shell_command], check=False)


def inspect_field(container: str, field: str) -> str:
    result = run(['docker', 'inspect', container, '--format', field], check=True)
    return result.stdout.strip()


def parse_ip(payload: str) -> str | None:
    trace_match = re.search(r'(?m)^ip=([^\\n]+)$', payload)
    if trace_match:
        return trace_match.group(1).strip()
    text = payload.strip()
    if re.fullmatch(r'[0-9a-fA-F:.]+', text):
        return text
    return None


def helper_probe(container: str, helper_image: str, url: str, insecure: bool) -> tuple[str | None, str | None]:
    curl_flags = ['-fsSL', '--max-time', '20']
    if insecure:
        curl_flags.insert(0, '-k')
    result = run(
        ['docker', 'run', '--rm', '--network', f'container:{container}', helper_image, *curl_flags, url],
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip(), 'helper-container'
    return None, None


def container_probe(container: str, url: str, insecure: bool) -> tuple[str | None, str | None]:
    commands = [
        f"curl {'-k ' if insecure else ''}-fsSL --max-time 20 '{url}'",
        f"wget {'--no-check-certificate ' if insecure else ''}-qO- --timeout=20 '{url}'",
        f"busybox wget {'--no-check-certificate ' if insecure else ''}-qO- --timeout=20 '{url}'",
    ]
    for shell_command in commands:
        result = run_shell(container, shell_command)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), 'container'
    return None, None


def run_probe(container: str, urls: list[str], helper_image: str, insecure: bool) -> tuple[str | None, str | None, str | None]:
    for url in urls:
        payload, source = container_probe(container, url, insecure)
        if payload:
            return url, payload, source
    for url in urls:
        payload, source = helper_probe(container, helper_image, url, insecure)
        if payload:
            return url, payload, source
    return None, None, None


target_container = os.environ['TARGET_CONTAINER']
sidecar_container = os.environ['SIDECAR_CONTAINER']
state_path = os.environ['FAILOVER_STATE_PATH']
helper_image = os.environ['HELPER_IMAGE']
direct_urls = [item for item in os.environ['DIRECT_PROBE_URLS'].split(',') if item]
proxied_urls = [item for item in os.environ['PROXIED_TRACE_URLS'].split(',') if item]
log_tail = int(os.environ['LOG_TAIL'])

target_network_mode = inspect_field(target_container, '{{.HostConfig.NetworkMode}}')
target_container_id = inspect_field(target_container, '{{.Id}}')
sidecar_container_id = inspect_field(sidecar_container, '{{.Id}}')

state = {}
try:
    with open(state_path, 'r', encoding='utf-8') as handle:
        state = json.load(handle)
except FileNotFoundError:
    state = {}

latest_log_tag = None
latest_log_line = None
logs = run(['docker', 'logs', f'--tail={log_tail}', sidecar_container], check=False)
log_text = (logs.stdout or '') + (logs.stderr or '')
for line in reversed([item.strip() for item in log_text.splitlines() if item.strip()]):
    match = re.search(r'outbound/vless\\[(proxy_[^\\]]+)\\]', line)
    if match:
        latest_log_tag = match.group(1)
        latest_log_line = line
        break

direct_url, direct_payload, direct_source = run_probe(target_container, direct_urls, helper_image, insecure=False)
proxied_url, proxied_payload, proxied_source = run_probe(target_container, proxied_urls, helper_image, insecure=True)

result = {
    'target_container': target_container,
    'target_container_id': target_container_id,
    'target_network_mode': target_network_mode,
    'shares_sidecar_namespace': target_network_mode == f'container:{sidecar_container_id}',
    'sidecar_container': sidecar_container,
    'sidecar_container_id': sidecar_container_id,
    'selector_current': state.get('current'),
    'selector_selected': state.get('selected'),
    'selector_priority': state.get('priority', []),
    'health': state.get('health', {}),
    'diagnostics': state.get('diagnostics', {}),
    'direct_probe_url': direct_url,
    'direct_probe_source': direct_source,
    'direct_probe_ip': parse_ip(direct_payload or ''),
    'direct_probe_payload': (direct_payload or '').strip(),
    'proxied_probe_url': proxied_url,
    'proxied_probe_source': proxied_source,
    'proxied_probe_ip': parse_ip(proxied_payload or ''),
    'proxied_probe_payload': (proxied_payload or '').strip(),
    'latest_sidecar_log_tag': latest_log_tag,
    'latest_sidecar_log_line': latest_log_line,
}
print(json.dumps(result, ensure_ascii=False))
PY
EOF
)"

REMOTE_JSON="$(run_ssh "${REMOTE_COMMAND}")"

python3 - <<'PY' "${INVENTORY_PATH}" "${REMOTE_JSON}" "${REMOTE_HOST}"
import json
import sys
from pathlib import Path


inventory_path = Path(sys.argv[1])
remote_result = json.loads(sys.argv[2])
remote_host = sys.argv[3]
inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
node_by_host = {item['host']: item['name'] for item in inventory.get('nodes', [])}
node_by_tag = {f"proxy_{item['name']}": item for item in inventory.get('nodes', [])}

proxied_ip = remote_result.get('proxied_probe_ip')
matched_node_name = node_by_host.get(proxied_ip)
matched_node = next((item for item in inventory.get('nodes', []) if item['name'] == matched_node_name), None)
selected_tag = remote_result.get('selector_selected') or remote_result.get('selector_current')
selected_node = node_by_tag.get(selected_tag) if selected_tag else None
latest_log_tag = remote_result.get('latest_sidecar_log_tag')
latest_log_node = node_by_tag.get(latest_log_tag) if latest_log_tag else None

print('[INFO] Live verification result')
print(f"target_container={remote_result.get('target_container')}")
print(f"target_network_mode={remote_result.get('target_network_mode')}")
print(f"shares_sidecar_namespace={str(remote_result.get('shares_sidecar_namespace')).lower()}")
print(f"default_route_probe_url={remote_result.get('direct_probe_url')}")
print(f"default_route_observed_ip={remote_result.get('direct_probe_ip')}")
print(f"default_route_probe_source={remote_result.get('direct_probe_source')}")
print(f"matched_rule_probe_url={remote_result.get('proxied_probe_url')}")
print(f"matched_rule_observed_ip={proxied_ip}")
print(f"matched_rule_probe_source={remote_result.get('proxied_probe_source')}")
print(f"matched_rule_node={matched_node_name}")
if matched_node is not None:
    print(f"matched_rule_node_provider={matched_node.get('provider')}")
print(f"selector_current={remote_result.get('selector_current')}")
print(f"selector_selected={remote_result.get('selector_selected')}")
print(f"latest_sidecar_log_tag={latest_log_tag}")
if remote_result.get('latest_sidecar_log_line'):
    print(f"latest_sidecar_log_line={remote_result.get('latest_sidecar_log_line')}")

verdicts = []

if remote_result.get('direct_probe_ip'):
    if remote_result['direct_probe_ip'] == remote_host:
        verdicts.append(
            'unmatched traffic is still using the Ubuntu.online default route, which is expected because route.final=direct'
        )
    else:
        verdicts.append(
            f"unmatched traffic is using a non-host egress IP: {remote_result['direct_probe_ip']}"
        )
else:
    verdicts.append('default-route probe did not return an IP')

if proxied_ip and matched_node_name:
    verdicts.append(
        f"matched proxy traffic is exiting via {matched_node_name} ({proxied_ip})"
    )
elif proxied_ip:
    verdicts.append(
        f"matched proxy traffic returned {proxied_ip}, but inventory has no node with that host IP"
    )
else:
    verdicts.append('matched-rule probe did not return an IP')

if selected_node is not None and matched_node is not None:
    if selected_node['name'] == matched_node['name']:
        verdicts.append(
            f"selector state and observed matched-rule egress agree on {selected_node['name']}"
        )
    else:
        verdicts.append(
            f"WARNING selector chose {selected_node['name']} but matched-rule traffic observed {matched_node['name']}"
        )

if latest_log_node is not None and matched_node is not None:
    if latest_log_node['name'] == matched_node['name']:
        verdicts.append(
            f"sidecar logs also show {latest_log_node['name']} for the latest proxied connection"
        )
    else:
        verdicts.append(
            f"WARNING latest sidecar log tag {latest_log_node['name']} disagrees with matched-rule IP {matched_node['name']}"
        )

print('verdict=' + ' | '.join(verdicts))
PY
