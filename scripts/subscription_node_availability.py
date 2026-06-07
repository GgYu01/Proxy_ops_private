from __future__ import annotations

import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROBE_PORT_OFFSET = 1
DEFAULT_PROBE_TIMEOUT_SECONDS = 2.5
DEFAULT_EXCLUDE_AFTER_HOURS = 72
DEFAULT_MIN_PUBLISHED_NODES = 1
DEFAULT_LEDGER_PATH = "state/node_availability.json"
PROBE_SOURCE = "tcp_probe"


@dataclass(frozen=True)
class AvailabilityPolicy:
    probe_port_offset: int
    exclude_after_hours: int
    min_published_nodes: int
    probe_timeout_seconds: float
    ledger_path: Path


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
    worker_count = max(1, min(len(nodes), 8))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(
                _probe_host,
                name=str(node["name"]),
                host=str(node["host"]),
                port=int(node["base_port"]) + policy.probe_port_offset,
                timeout_seconds=policy.probe_timeout_seconds,
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


def _probe_host(*, name: str, host: str, port: int, timeout_seconds: float) -> ProbeResult:
    observed_at = _isoformat(_utc_now())
    try:
        connection = socket.create_connection((host, port), timeout=timeout_seconds)
    except Exception as exc:
        return ProbeResult(
            name=name,
            host=host,
            port=port,
            health="down",
            detail=f"tcp {host}:{port} failed: {type(exc).__name__}: {exc}",
            observed_at=observed_at,
        )
    try:
        return ProbeResult(
            name=name,
            host=host,
            port=port,
            health="healthy",
            detail=f"tcp connect ok {host}:{port}",
            observed_at=observed_at,
        )
    finally:
        connection.close()


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
