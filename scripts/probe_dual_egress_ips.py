#!/usr/bin/env python3
"""Probe vmrack public vs qqpw WireGuard egress IPs through local mihomo."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent


def load_render_artifacts():
    spec = importlib.util.spec_from_file_location(
        "render_artifacts", SCRIPTS_DIR / "render_artifacts.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load render_artifacts")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_availability():
    spec = importlib.util.spec_from_file_location(
        "subscription_node_availability",
        SCRIPTS_DIR / "subscription_node_availability.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load subscription_node_availability")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reserve_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def resolve_mihomo(path_hint: str | None) -> str:
    candidates = []
    if path_hint:
        candidates.append(path_hint)
    env = os.environ.get("MIHOMO_BIN")
    if env:
        candidates.append(env)
    candidates.extend(
        [
            r"C:\Tools\mihomo\mihomo-windows-amd64.exe",
            "mihomo",
            "mihomo-windows-amd64.exe",
        ]
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return str(Path(candidate))
        from shutil import which

        found = which(candidate)
        if found:
            return found
    raise FileNotFoundError("mihomo executable not found; set MIHOMO_BIN")


def wait_port(port: int, process: subprocess.Popen[str], timeout: float) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"mihomo exited early rc={process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"mihomo mixed-port {port} not ready")


def fetch_ip_via_proxy(*, proxy_url: str, probe_url: str, timeout: float) -> str:
    try:
        import httpx

        with httpx.Client(proxy=proxy_url, timeout=timeout, http2=False) as client:
            response = client.get(probe_url)
            response.raise_for_status()
            return response.text.strip()
    except Exception:
        curl = subprocess.run(
            [
                "curl",
                "-sS",
                "--http1.1",
                "--proxy",
                proxy_url,
                "--connect-timeout",
                str(max(5, int(timeout))),
                "--max-time",
                str(max(1, int(timeout))),
                probe_url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if curl.returncode != 0:
            raise RuntimeError(curl.stderr.strip() or curl.stdout.strip() or "curl failed")
        return curl.stdout.strip()


def probe_proxy_exit_ip(
    *,
    mihomo_bin: str,
    proxy: dict[str, Any],
    probe_url: str,
    timeout: float,
) -> str:
    with tempfile.TemporaryDirectory(prefix="dual-egress-probe-") as tmp:
        tmp_path = Path(tmp)
        mixed_port = reserve_port()
        controller_port = reserve_port()
        config = {
            "mixed-port": mixed_port,
            "allow-lan": False,
            "mode": "rule",
            "log-level": "warning",
            "external-controller": f"127.0.0.1:{controller_port}",
            "proxies": [proxy],
            "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": [proxy["name"]]}],
            "rules": ["MATCH,PROXY"],
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        process = subprocess.Popen(
            [mihomo_bin, "-d", str(tmp_path), "-f", str(config_path)],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            wait_port(mixed_port, process, timeout=8.0)
            return fetch_ip_via_proxy(
                proxy_url=f"http://127.0.0.1:{mixed_port}",
                probe_url=probe_url,
                timeout=timeout,
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


def dual_egress_assertions(repo_root: Path) -> list[dict[str, Any]]:
    render = load_render_artifacts()
    subscriptions = render.load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    policy = subscriptions.get("availability_policy") or {}
    probe_url = str(policy.get("egress_ip_probe_url") or "https://api.ipify.org")
    timeout = float(policy.get("curl_timeout_seconds") or 12)
    mihomo_bin = resolve_mihomo(str(policy.get("mihomo_path") or "") or None)

    node = render.enabled_node_by_name(repo_root, "vmrack1")
    if not render.node_has_dual_egress(node):
        raise SystemExit("[ERROR] vmrack1 is missing dual egress_profiles")

    public_expected = str(
        ((render.node_egress_profiles(node).get("public") or {}).get("expected_exit_ip"))
        or node["host"]
    )
    wg_forbidden = str(
        ((render.wireguard_nat_profile(node).get("expected_exit_ip_not")) or public_expected)
    )

    results: list[dict[str, Any]] = []
    public_proxy = render.mihomo_proxy_for_node(node)
    public_ip = probe_proxy_exit_ip(
        mihomo_bin=mihomo_bin,
        proxy=public_proxy,
        probe_url=probe_url,
        timeout=timeout,
    )
    public_ok = public_ip == public_expected
    results.append(
        {
            "profile": "public",
            "proxy": public_proxy["name"],
            "observed_exit_ip": public_ip,
            "expected_exit_ip": public_expected,
            "ok": public_ok,
        }
    )

    entry = next(
        item
        for item in render.extra_single_node_subscriptions(repo_root)
        if str(item.get("filename")) == "qqpw"
    )
    for proxy in render.mihomo_proxies_for_wireguard_nat_entry(node, entry):
        observed = probe_proxy_exit_ip(
            mihomo_bin=mihomo_bin,
            proxy=proxy,
            probe_url=probe_url,
            timeout=timeout,
        )
        ok = observed != wg_forbidden and bool(observed)
        results.append(
            {
                "profile": "wireguard_nat",
                "proxy": proxy["name"],
                "observed_exit_ip": observed,
                "expected_exit_ip_not": wg_forbidden,
                "ok": ok,
            }
        )
    return results


def assert_static_render_separation(repo_root: Path) -> None:
    render = load_render_artifacts()
    node = render.enabled_node_by_name(repo_root, "vmrack1")
    entry = next(
        item
        for item in render.extra_single_node_subscriptions(repo_root)
        if str(item.get("filename")) == "qqpw"
    )
    public_port = render.public_vless_port(node)
    qqpw_ports = {
        render.hysteria2_port(node),
        render.qqpw_vless_port(node),
        render.qqpw_socks_port(node),
    }
    if public_port in qqpw_ports:
        raise SystemExit(
            f"[ERROR] public port {public_port} overlaps qqpw ports {sorted(qqpw_ports)}"
        )
    public_links = render.subscription_links_for_node(node)
    qqpw_links = render.subscription_links_for_wireguard_nat_entry(node, entry)
    if any(f":{port}" in link for link in public_links for port in qqpw_ports):
        raise SystemExit("[ERROR] public vmrack subscription unexpectedly includes qqpw ports")
    if any(f":{public_port}" in link for link in qqpw_links):
        raise SystemExit("[ERROR] qqpw subscription unexpectedly includes public VLESS port")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Only validate rendered port/UUID separation (no live mihomo probe)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    assert_static_render_separation(args.repo_root)
    if args.static_only:
        payload = {"static_ok": True, "probes": []}
        print(json.dumps(payload, indent=2) if args.json else "[OK] static dual-egress separation")
        return 0

    results = dual_egress_assertions(args.repo_root)
    failed = [item for item in results if not item["ok"]]
    if args.json:
        print(json.dumps({"static_ok": True, "probes": results}, indent=2))
    else:
        for item in results:
            status = "OK" if item["ok"] else "FAIL"
            print(f"[{status}] {item['profile']} {item['proxy']} -> {item['observed_exit_ip']}")
    if failed:
        print("[ERROR] dual egress IP assertions failed", file=sys.stderr)
        return 1
    print("[OK] dual egress IP assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
