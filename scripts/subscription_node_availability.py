from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROBE_PORT_OFFSET = 3
DEFAULT_PROBE_TIMEOUT_SECONDS = 2.5
DEFAULT_EXCLUDE_AFTER_HOURS = 72
DEFAULT_MIN_PUBLISHED_NODES = 1
DEFAULT_LEDGER_PATH = "state/node_availability.json"
DEFAULT_PROBE_METHOD = "mihomo_openai_http"
DEFAULT_OPENAI_PROBE_URL = "https://api.openai.com/v1/models"
DEFAULT_OPENAI_EXPECTED_STATUSES = (200, 401, 403, 404)
DEFAULT_MIHOMO_STARTUP_TIMEOUT_SECONDS = 8.0
DEFAULT_CURL_TIMEOUT_SECONDS = 12.0
DEFAULT_PROXY_PROBE_ATTEMPTS = 2
PROBE_SOURCE = "mihomo_openai_http_probe"


@dataclass(frozen=True)
class AvailabilityPolicy:
    probe_port_offset: int
    exclude_after_hours: int
    min_published_nodes: int
    probe_timeout_seconds: float
    ledger_path: Path
    probe_method: str
    openai_probe_url: str
    openai_expected_statuses: tuple[int, ...]
    mihomo_path: str | None
    curl_path: str | None
    mihomo_startup_timeout_seconds: float
    curl_timeout_seconds: float
    proxy_probe_attempts: int


@dataclass(frozen=True)
class ProbeResult:
    name: str
    host: str
    port: int
    health: str
    detail: str
    observed_at: str


@dataclass(frozen=True)
class NodeAvailabilityEntry:
    name: str
    last_probe_at: str | None
    last_health: str
    unavailable_since: str | None
    last_success_at: str | None
    detail: str | None


@dataclass(frozen=True)
class ExclusionReport:
    included: list[str]
    excluded: list[str]
    pending: list[str]
    unknown: list[str]


def load_availability_policy(repo_root: Path) -> AvailabilityPolicy:
    subscriptions_path = repo_root / "inventory" / "subscriptions.yaml"
    payload = yaml.safe_load(subscriptions_path.read_text(encoding="utf-8")) or {}
    policy = payload.get("availability_policy") or {}
    ledger_relative = str(policy.get("ledger_path") or DEFAULT_LEDGER_PATH)
    return AvailabilityPolicy(
        probe_port_offset=int(policy.get("probe_port_offset", DEFAULT_PROBE_PORT_OFFSET)),
        exclude_after_hours=int(policy.get("exclude_after_hours", DEFAULT_EXCLUDE_AFTER_HOURS)),
        min_published_nodes=int(policy.get("min_published_nodes", DEFAULT_MIN_PUBLISHED_NODES)),
        probe_timeout_seconds=float(policy.get("probe_timeout_seconds", DEFAULT_PROBE_TIMEOUT_SECONDS)),
        ledger_path=repo_root / ledger_relative,
        probe_method=str(policy.get("probe_method") or DEFAULT_PROBE_METHOD),
        openai_probe_url=str(policy.get("openai_probe_url") or DEFAULT_OPENAI_PROBE_URL),
        openai_expected_statuses=_parse_expected_statuses(
            policy.get("openai_expected_statuses", DEFAULT_OPENAI_EXPECTED_STATUSES)
        ),
        mihomo_path=_optional_str(policy.get("mihomo_path") or os.environ.get("MIHOMO_BIN")),
        curl_path=_optional_str(policy.get("curl_path") or os.environ.get("CURL_BIN")),
        mihomo_startup_timeout_seconds=float(
            policy.get("mihomo_startup_timeout_seconds", DEFAULT_MIHOMO_STARTUP_TIMEOUT_SECONDS)
        ),
        curl_timeout_seconds=float(policy.get("curl_timeout_seconds", DEFAULT_CURL_TIMEOUT_SECONDS)),
        proxy_probe_attempts=max(1, int(policy.get("proxy_probe_attempts", DEFAULT_PROXY_PROBE_ATTEMPTS))),
    )


def ledger_path(repo_root: Path) -> Path:
    return load_availability_policy(repo_root).ledger_path


def load_ledger(repo_root: Path) -> dict[str, Any]:
    path = ledger_path(repo_root)
    if not path.exists():
        return {"updated_at": None, "nodes": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    payload.setdefault("nodes", {})
    return payload


def save_ledger(repo_root: Path, payload: dict[str, Any]) -> Path:
    path = ledger_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def probe_nodes(repo_root: Path, *, policy: AvailabilityPolicy | None = None) -> list[ProbeResult]:
    policy = policy or load_availability_policy(repo_root)
    inventory_path = repo_root / "inventory" / "nodes.yaml"
    payload = yaml.safe_load(inventory_path.read_text(encoding="utf-8")) or {}
    nodes = [item for item in payload.get("nodes", []) if item.get("enabled")]
    if not nodes:
        return []

    results: list[ProbeResult | None] = [None] * len(nodes)
    worker_count = 1 if policy.probe_method == DEFAULT_PROBE_METHOD else max(1, min(len(nodes), 8))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(
                _probe_node,
                repo_root=repo_root,
                node=_merge_node_secrets(repo_root, node),
                policy=policy,
            ): index
            for index, node in enumerate(nodes)
        }
        for future in as_completed(future_map):
            results[future_map[future]] = future.result()
    return [item for item in results if item is not None]


def update_ledger(
    repo_root: Path,
    probe_results: list[ProbeResult],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or _utc_now()
    payload = load_ledger(repo_root)
    nodes: dict[str, Any] = dict(payload.get("nodes") or {})
    seen: set[str] = set()

    for result in probe_results:
        seen.add(result.name)
        previous = nodes.get(result.name) or {}
        entry = _merge_probe_result(previous, result, now=now)
        nodes[result.name] = entry

    payload["updated_at"] = _isoformat(now)
    payload["nodes"] = nodes
    save_ledger(repo_root, payload)
    return payload


def refresh_availability(
    repo_root: Path,
    *,
    now: datetime | None = None,
    skip_probe: bool = False,
) -> dict[str, Any]:
    if skip_probe or os.environ.get("SKIP_AVAILABILITY_PROBE") == "1":
        return load_ledger(repo_root)
    results = probe_nodes(repo_root)
    return update_ledger(repo_root, results, now=now)


def node_is_availability_exempt(node: dict[str, Any]) -> bool:
    return bool(node.get("subscription_availability_exempt", False))


def registry_subscription_nodes(repo_root: Path) -> list[dict[str, Any]]:
    subscriptions_path = repo_root / "inventory" / "subscriptions.yaml"
    inventory_path = repo_root / "inventory" / "nodes.yaml"
    subscriptions = yaml.safe_load(subscriptions_path.read_text(encoding="utf-8")) or {}
    inventory = yaml.safe_load(inventory_path.read_text(encoding="utf-8")) or {}
    configured_priority = subscriptions.get("failover_priority", [])
    if not isinstance(configured_priority, list):
        raise ValueError("failover_priority must be a list of node names")

    node_by_name = {
        str(node["name"]): _merge_node_secrets(repo_root, node)
        for node in inventory.get("nodes", [])
        if node.get("enabled") and node.get("include_in_subscription", True)
    }
    ordered_nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_name in configured_priority:
        node_name = str(raw_name)
        if node_name not in node_by_name:
            raise ValueError(f"failover_priority references unknown enabled node: {node_name}")
        ordered_nodes.append(node_by_name[node_name])
        seen.add(node_name)
    for node in node_by_name.values():
        if str(node["name"]) not in seen:
            ordered_nodes.append(node)
    return ordered_nodes


def subscription_eligible_nodes(
    repo_root: Path,
    *,
    now: datetime | None = None,
    ledger: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    now = now or _utc_now()
    policy = load_availability_policy(repo_root)
    ledger = ledger if ledger is not None else load_ledger(repo_root)
    ledger_nodes = ledger.get("nodes") or {}
    eligible: list[dict[str, Any]] = []

    for node in registry_subscription_nodes(repo_root):
        name = str(node["name"])
        if node_is_availability_exempt(node):
            eligible.append(node)
            continue
        entry = ledger_nodes.get(name)
        if not entry or not entry.get("unavailable_since"):
            eligible.append(node)
            continue
        unavailable_since = _parse_iso(str(entry["unavailable_since"]))
        if now - unavailable_since < timedelta(hours=policy.exclude_after_hours):
            eligible.append(node)
            continue
    return eligible


def subscription_publishable_nodes(
    repo_root: Path,
    *,
    ledger: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ledger = ledger if ledger is not None else load_ledger(repo_root)
    ledger_nodes = ledger.get("nodes") or {}
    publishable: list[dict[str, Any]] = []

    for node in registry_subscription_nodes(repo_root):
        name = str(node["name"])
        if node_is_availability_exempt(node):
            publishable.append(node)
            continue
        entry = ledger_nodes.get(name)
        if entry and entry.get("last_health") == "healthy":
            publishable.append(node)
    return publishable


def exclusion_report(
    repo_root: Path,
    *,
    now: datetime | None = None,
    ledger: dict[str, Any] | None = None,
) -> ExclusionReport:
    now = now or _utc_now()
    policy = load_availability_policy(repo_root)
    ledger = ledger if ledger is not None else load_ledger(repo_root)
    ledger_nodes = ledger.get("nodes") or {}
    included: list[str] = []
    excluded: list[str] = []
    pending: list[str] = []
    unknown: list[str] = []

    for node in registry_subscription_nodes(repo_root):
        name = str(node["name"])
        if node_is_availability_exempt(node):
            included.append(name)
            continue
        entry = ledger_nodes.get(name)
        if not entry:
            unknown.append(name)
            included.append(name)
            continue
        unavailable_since = entry.get("unavailable_since")
        if not unavailable_since:
            included.append(name)
            continue
        age = now - _parse_iso(str(unavailable_since))
        if age >= timedelta(hours=policy.exclude_after_hours):
            excluded.append(name)
        else:
            pending.append(name)
            included.append(name)
    return ExclusionReport(included=included, excluded=excluded, pending=pending, unknown=unknown)


def ensure_minimum_published_nodes(repo_root: Path, eligible: list[dict[str, Any]]) -> None:
    policy = load_availability_policy(repo_root)
    if len(eligible) < policy.min_published_nodes:
        report = exclusion_report(repo_root)
        raise RuntimeError(
            "subscription availability gate failed: "
            f"eligible_nodes={len(eligible)} < min_published_nodes={policy.min_published_nodes}; "
            f"excluded={report.excluded}; pending={report.pending}"
        )


def is_subscription_eligible_from_ledger(
    *,
    node_name: str,
    subscription_availability_exempt: bool,
    ledger_entry: dict[str, Any] | None,
    exclude_after_hours: int,
    now: datetime | None = None,
) -> bool:
    if subscription_availability_exempt:
        return True
    if not ledger_entry or not ledger_entry.get("unavailable_since"):
        return True
    now = now or _utc_now()
    unavailable_since = _parse_iso(str(ledger_entry["unavailable_since"]))
    return now - unavailable_since < timedelta(hours=exclude_after_hours)


def load_ledger_for_platform(workspace_root: Path) -> tuple[dict[str, Any], AvailabilityPolicy | None]:
    repo_root = workspace_root / "repos" / "proxy_ops_private"
    subscriptions_path = repo_root / "inventory" / "subscriptions.yaml"
    if not subscriptions_path.exists():
        return {"nodes": {}}, None
    policy = load_availability_policy(repo_root)
    return load_ledger(repo_root), policy


def _merge_node_secrets(repo_root: Path, node: dict[str, Any]) -> dict[str, Any]:
    merged = dict(node)
    secrets_path = repo_root / "secrets" / "nodes" / f"{node['name']}.env"
    merged["secrets"] = _load_env_file(secrets_path) if secrets_path.exists() else {}
    return merged


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _merge_probe_result(previous: dict[str, Any], result: ProbeResult, *, now: datetime) -> dict[str, Any]:
    observed_at = result.observed_at
    if result.health == "healthy":
        return {
            "last_probe_at": observed_at,
            "last_health": "healthy",
            "unavailable_since": None,
            "last_success_at": observed_at,
            "detail": result.detail,
        }
    unavailable_since = previous.get("unavailable_since")
    if not unavailable_since:
        unavailable_since = observed_at
    return {
        "last_probe_at": observed_at,
        "last_health": "down",
        "unavailable_since": unavailable_since,
        "last_success_at": previous.get("last_success_at"),
        "detail": result.detail,
    }


def _probe_node(*, repo_root: Path, node: dict[str, Any], policy: AvailabilityPolicy) -> ProbeResult:
    name = str(node["name"])
    host = str(node["host"])
    port = int(node["base_port"]) + policy.probe_port_offset
    observed_at = _isoformat(_utc_now())
    tcp_ok, tcp_detail = _tcp_probe(host=host, port=port, timeout_seconds=policy.probe_timeout_seconds)
    if policy.probe_method == "tcp":
        return ProbeResult(
            name=name,
            host=host,
            port=port,
            health="healthy" if tcp_ok else "down",
            detail=tcp_detail,
            observed_at=observed_at,
        )

    proxy_ok = False
    proxy_details: list[str] = []
    for attempt in range(1, policy.proxy_probe_attempts + 1):
        proxy_ok, proxy_detail = _probe_node_through_mihomo(repo_root=repo_root, node=node, policy=policy)
        proxy_details.append(f"attempt{attempt}: {proxy_detail}")
        if proxy_ok:
            break
    health = "healthy" if proxy_ok else "down"
    return ProbeResult(
        name=name,
        host=host,
        port=port,
        health=health,
        detail=(
            f"tcp={'ok' if tcp_ok else 'failed'} ({tcp_detail}); "
            f"proxy={'ok' if proxy_ok else 'failed'} ({' | '.join(proxy_details)})"
        ),
        observed_at=observed_at,
    )


def _tcp_probe(*, host: str, port: int, timeout_seconds: float) -> tuple[bool, str]:
    try:
        connection = socket.create_connection((host, port), timeout=timeout_seconds)
    except Exception as exc:
        return False, f"tcp {host}:{port} failed: {type(exc).__name__}: {exc}"
    try:
        return True, f"tcp connect ok {host}:{port}"
    finally:
        connection.close()


def _probe_node_through_mihomo(
    *,
    repo_root: Path,
    node: dict[str, Any],
    policy: AvailabilityPolicy,
) -> tuple[bool, str]:
    missing = _missing_proxy_fields(node)
    if missing:
        return False, f"missing node proxy fields: {', '.join(missing)}"

    mihomo_bin = _resolve_executable(policy.mihomo_path, ["mihomo", "mihomo-windows-amd64.exe"])
    if not mihomo_bin:
        return False, "mihomo executable not found; set MIHOMO_BIN or availability_policy.mihomo_path"

    curl_bin = _resolve_executable(policy.curl_path, ["curl", "curl.exe"])
    if not curl_bin:
        return False, "curl executable not found; set CURL_BIN or availability_policy.curl_path"

    with tempfile.TemporaryDirectory(prefix=f"node-probe-{node['name']}-") as tmp:
        tmp_path = Path(tmp)
        mixed_port = _reserve_loopback_port()
        controller_port = _reserve_loopback_port()
        config_path = tmp_path / "mihomo-node-probe.yaml"
        config_path.write_text(
            yaml.safe_dump(
                _single_node_mihomo_config(
                    node,
                    mixed_port=mixed_port,
                    controller_port=controller_port,
                    probe_port_offset=policy.probe_port_offset,
                ),
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        command = [mihomo_bin, "-d", str(tmp_path), "-f", str(config_path)]
        process = subprocess.Popen(
            command,
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            ready, ready_detail = _wait_for_port(
                port=mixed_port,
                timeout_seconds=policy.mihomo_startup_timeout_seconds,
                process=process,
            )
            if not ready:
                return False, f"mihomo startup failed: {ready_detail}; { _tail_process_output(process) }".strip()

            proxy_url = f"http://127.0.0.1:{mixed_port}"
            httpx_ok, httpx_detail = _probe_url_with_httpx(
                url=policy.openai_probe_url,
                proxy_url=proxy_url,
                timeout_seconds=policy.curl_timeout_seconds,
                expected_statuses=policy.openai_expected_statuses,
            )
            if httpx_ok:
                return True, httpx_detail

            curl_ok, curl_detail = _probe_url_with_curl(
                curl_bin=curl_bin,
                url=policy.openai_probe_url,
                proxy_url=proxy_url,
                timeout_seconds=policy.curl_timeout_seconds,
                expected_statuses=policy.openai_expected_statuses,
            )
            if curl_ok:
                return True, curl_detail
            return False, f"{httpx_detail}; {curl_detail}"
        finally:
            _terminate_process(process)


def _probe_url_with_httpx(
    *,
    url: str,
    proxy_url: str,
    timeout_seconds: float,
    expected_statuses: tuple[int, ...],
) -> tuple[bool, str]:
    try:
        import httpx

        with httpx.Client(proxy=proxy_url, timeout=timeout_seconds, http2=False) as client:
            response = client.get(url)
    except Exception as exc:
        return False, f"httpx openai proxy failed: {type(exc).__name__}: {_one_line(str(exc))}"
    if response.status_code in expected_statuses:
        return True, f"httpx openai proxy http status={response.status_code}"
    return False, f"httpx openai proxy http status={response.status_code}"


def _probe_url_with_curl(
    *,
    curl_bin: str,
    url: str,
    proxy_url: str,
    timeout_seconds: float,
    expected_statuses: tuple[int, ...],
) -> tuple[bool, str]:
    curl = subprocess.run(
        [
            curl_bin,
            "-sS",
            "-o",
            os.devnull,
            "-w",
            "%{http_code}",
            "--http1.1",
            "--proxy",
            proxy_url,
            "--connect-timeout",
            str(max(5, int(timeout_seconds))),
            "--max-time",
            str(max(1, int(timeout_seconds))),
            url,
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    status_text = (curl.stdout or "").strip()[-3:]
    status = int(status_text) if status_text.isdigit() else 0
    stderr = _one_line(curl.stderr)
    if status in expected_statuses:
        return True, f"curl openai proxy http status={status}"
    return (
        False,
        f"curl openai proxy http status={status or 'none'} exit={curl.returncode}"
        + (f" stderr={stderr}" if stderr else ""),
    )


def _single_node_mihomo_config(
    node: dict[str, Any],
    *,
    mixed_port: int,
    controller_port: int,
    probe_port_offset: int,
) -> dict[str, Any]:
    return {
        "mixed-port": mixed_port,
        "allow-lan": False,
        "bind-address": "127.0.0.1",
        "mode": "rule",
        "log-level": "warning",
        "ipv6": False,
        "external-controller": f"127.0.0.1:{controller_port}",
        "dns": {"enable": True, "nameserver": ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"]},
        "proxies": [_mihomo_proxy_for_node(node, probe_port_offset=probe_port_offset)],
        "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": [str(node["subscription_alias"])]}],
        "rules": ["MATCH,PROXY"],
    }


def _mihomo_proxy_for_node(node: dict[str, Any], *, probe_port_offset: int) -> dict[str, Any]:
    secrets = node.get("secrets") or {}
    return {
        "name": str(node["subscription_alias"]),
        "type": "vless",
        "server": str(node["host"]),
        "port": int(node["base_port"]) + probe_port_offset,
        "uuid": secrets["VLESS_UUID"],
        "network": "tcp",
        "tls": True,
        "udp": True,
        "flow": "xtls-rprx-vision",
        "servername": _first_server_name(secrets),
        "client-fingerprint": "chrome",
        "reality-opts": {
            "public-key": secrets["REALITY_PUBLIC_KEY"],
            "short-id": secrets["REALITY_SHORT_ID"],
        },
    }


def _missing_proxy_fields(node: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in ("base_port", "subscription_alias"):
        if field not in node or node.get(field) in (None, ""):
            missing.append(field)
    secrets = node.get("secrets") or {}
    for field in ("VLESS_UUID", "REALITY_PUBLIC_KEY", "REALITY_SHORT_ID", "REALITY_SERVER_NAMES"):
        if not secrets.get(field):
            missing.append(f"secrets.{field}")
    return missing


def _first_server_name(secrets: dict[str, str]) -> str:
    return str(secrets["REALITY_SERVER_NAMES"]).split(",", 1)[0].strip()


def _resolve_executable(configured: str | None, candidates: list[str]) -> str | None:
    if configured:
        configured_path = Path(configured)
        if configured_path.exists():
            return str(configured_path)
        resolved = shutil.which(configured)
        if resolved:
            return resolved
        return None
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    default_windows = Path(r"C:\Tools\mihomo\mihomo-windows-amd64.exe")
    if "mihomo" in candidates[0] and default_windows.exists():
        return str(default_windows)
    return None


def _reserve_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(*, port: int, timeout_seconds: float, process: subprocess.Popen[str]) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False, f"mihomo exited rc={process.returncode}"
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return True, f"127.0.0.1:{port} listening"
        except OSError as exc:
            last_error = str(exc)
            time.sleep(0.2)
    return False, f"timeout waiting for 127.0.0.1:{port}; last_error={last_error}"


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def _tail_process_output(process: subprocess.Popen[str]) -> str:
    if not process.stdout:
        return ""
    if process.poll() is None:
        return ""
    try:
        return _one_line(process.stdout.read()[-500:])
    except Exception:
        return ""


def _one_line(value: str | None) -> str:
    return " ".join((value or "").split())[:500]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_expected_statuses(value: Any) -> tuple[int, ...]:
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",")]
    else:
        raw_items = list(value)
    statuses = tuple(int(item) for item in raw_items if str(item).strip())
    if not statuses:
        raise ValueError("openai_expected_statuses must not be empty")
    return statuses


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
