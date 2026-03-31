from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_CONFIG_PATH = "/mnt/hdo/infra-core/services/proxied/vless-sidecar/config.json"
DEFAULT_APPLY_SCRIPT = "/mnt/hdo/infra-core/services/proxied/vless-sidecar/apply_runtime_routing.sh"
DEFAULT_STATE_PATH = "/mnt/hdo/infra-core/services/proxied/vless-sidecar/failover_state.json"
DEFAULT_POLICY_PATH = "/mnt/hdo/infra-core/services/proxied/vless-sidecar/failover_policy.json"


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def find_selector(config: dict, selector_tag: str) -> dict:
    for outbound in config.get("outbounds", []):
        if outbound.get("tag") == selector_tag:
            return outbound
    raise ValueError(f"selector outbound not found: {selector_tag}")


def choose_active_tag(priority: list[str], health: dict[str, bool], current: str) -> str:
    for tag in priority:
        if health.get(tag):
            return tag
    return current


def run_command(args: list[str], *, check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        encoding="utf-8",
        capture_output=capture_output,
        check=check,
    )


def probe_node_http(node: dict, probe_url: str, timeout_seconds: int) -> tuple[bool, str]:
    result = subprocess.run(
        [
            "curl",
            "-fsS",
            "--max-time",
            str(timeout_seconds),
            "--proxy",
            f"http://{node['proxy_user']}:{node['proxy_pass']}@{node['host']}:{node['http_port']}",
            probe_url,
            "-o",
            "/dev/null",
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return True, "ok"
    return False, (result.stderr or result.stdout or "probe failed").strip()


def persist_state(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def apply_runtime_reload(config_path: Path, apply_script: Path) -> None:
    result = run_command(
        [
            "bash",
            str(apply_script),
        ],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "apply_runtime_routing.sh failed")


def reconcile(config_path: Path, apply_script: Path, state_path: Path, policy_path: Path, dry_run: bool) -> int:
    config = load_config(config_path)
    policy = load_config(policy_path)
    selector_tag = policy["selector_tag"]
    selector = find_selector(config, selector_tag)
    current = selector.get("default") or (selector.get("outbounds") or [""])[0]
    priority_nodes = policy["priority"]
    priority_tags = [node["tag"] for node in priority_nodes]

    health: dict[str, bool] = {}
    diagnostics: dict[str, str] = {}
    for node in priority_nodes:
        ok, message = probe_node_http(node, policy["probe_url"], policy["probe_timeout_seconds"])
        health[node["tag"]] = ok
        diagnostics[node["tag"]] = message

    selected = choose_active_tag(priority_tags, health, current)

    state_payload = {
        "selector_tag": selector_tag,
        "priority": priority_tags,
        "current": current,
        "selected": selected,
        "health": health,
        "diagnostics": diagnostics,
        "probe_url": policy["probe_url"],
        "updated_at_epoch": int(time.time()),
    }

    print(json.dumps(state_payload, indent=2))

    if dry_run:
        return 0

    if selected != current:
        selector["default"] = selected
        save_config(config_path, config)
        apply_runtime_reload(config_path, apply_script)

    persist_state(state_path, state_payload)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile infra-core proxy failover selection.")
    parser.add_argument("--config-path", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--apply-script", default=DEFAULT_APPLY_SCRIPT)
    parser.add_argument("--state-path", default=DEFAULT_STATE_PATH)
    parser.add_argument("--policy-path", default=DEFAULT_POLICY_PATH)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return reconcile(
        config_path=Path(args.config_path),
        apply_script=Path(args.apply_script),
        state_path=Path(args.state_path),
        policy_path=Path(args.policy_path),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
