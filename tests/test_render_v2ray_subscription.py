from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "render_artifacts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("render_artifacts", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_fixture(tmp_path: Path) -> Path:
    repo_root = tmp_path / "proxy_ops_private"
    shutil.copytree(REPO_ROOT / "inventory", repo_root / "inventory")
    shutil.copytree(REPO_ROOT / "secrets", repo_root / "secrets")
    (repo_root / "state").mkdir(parents=True)
    (repo_root / "state" / "node_availability.json").write_text(
        json.dumps(
            {
                "updated_at": "2026-06-23T00:00:00Z",
                "nodes": {
                    name: {
                        "last_probe_at": "2026-06-23T00:00:00Z",
                        "last_health": "healthy",
                        "unavailable_since": None,
                        "last_success_at": "2026-06-23T00:00:00Z",
                        "detail": "fixture real proxy probe passed",
                    }
                    for name in ("us_sea_bgp_01", "vmrack1", "dedirock")
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return repo_root


class V2RayRenderTests(unittest.TestCase):
    def test_v2ray_subscription_contains_only_currently_healthy_raw_ip_nodes(self) -> None:
        render_artifacts = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))

            artifact = render_artifacts.render_v2ray_subscription(repo_root)

        self.assertIn("GG-Vmrack1", artifact)
        self.assertIn("GG-Dedirock", artifact)
        self.assertIn("GG-US-SEA-BGP-01", artifact)
        self.assertNotIn("GG-Lisa-Stable", artifact)
        self.assertNotIn("GG-Lisahost-KR", artifact)
        self.assertNotIn("GG-Vmrack2", artifact)
        self.assertEqual(3, sum(1 for line in artifact.splitlines() if line.startswith("vless://")))
        self.assertIn("@69.5.53.82:10003", artifact)
        self.assertIn("@38.65.93.39:10003", artifact)
        self.assertIn("@67.215.238.140:10003", artifact)
        self.assertIn("sni=www.cloudflare.com", artifact)
        self.assertNotIn("sni=www.microsoft.com", artifact)
        self.assertNotIn("@38.34.8.59:10003", artifact)
        self.assertNotIn("@203.227.191.106:10003", artifact)
        self.assertNotIn("@38.65.93.94:10003", artifact)
        self.assertIsNotNone(re.search(r"vless://[^@\n]+@(?:\d{1,3}\.){3}\d{1,3}:10003", artifact))
        self.assertNotIn(".proxy.prod.gglohh.top:10003", artifact)

    def test_single_node_subscription_contains_only_requested_node(self) -> None:
        render_artifacts = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))

            artifact = render_artifacts.render_v2ray_subscription(repo_root, node_name="dedirock")

        self.assertIn("GG-Dedirock", artifact)
        self.assertNotIn("GG-Lisa-Stable", artifact)
        self.assertNotIn("GG-Lisahost-KR", artifact)
        self.assertNotIn("GG-Vmrack1", artifact)
        self.assertNotIn("GG-Vmrack2", artifact)
        self.assertNotIn("GG-US-SEA-BGP-01", artifact)
        self.assertEqual(1, sum(1 for line in artifact.splitlines() if line.startswith("vless://")))
        self.assertIn("@67.215.238.140:10003", artifact)

    def test_single_node_subscription_returns_empty_for_unhealthy_node(self) -> None:
        render_artifacts = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))

            artifact = render_artifacts.render_v2ray_subscription(repo_root, node_name="lisahost")

        self.assertEqual("", artifact)


if __name__ == "__main__":
    unittest.main()
