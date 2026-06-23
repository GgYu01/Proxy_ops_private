from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "render_artifacts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("render_artifacts", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_healthy_fixture(repo_root: Path) -> None:
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
                    for name in ("us_sea_bgp_01", "lisahost_kr", "dedirock")
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


class SubscriptionLandingPageRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_skip_probe = os.environ.get("SKIP_AVAILABILITY_PROBE")
        os.environ["SKIP_AVAILABILITY_PROBE"] = "1"

    def tearDown(self) -> None:
        if self._old_skip_probe is None:
            os.environ.pop("SKIP_AVAILABILITY_PROBE", None)
        else:
            os.environ["SKIP_AVAILABILITY_PROBE"] = self._old_skip_probe

    def test_write_generated_artifacts_emits_subscription_landing_page(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / "inventory").mkdir(parents=True, exist_ok=True)
            (repo_root / "templates").mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / "inventory" / "nodes.yaml", repo_root / "inventory" / "nodes.yaml")
            shutil.copy2(
                REPO_ROOT / "inventory" / "subscriptions.yaml",
                repo_root / "inventory" / "subscriptions.yaml",
            )
            shutil.copytree(REPO_ROOT / "secrets" / "nodes", repo_root / "secrets" / "nodes")
            write_healthy_fixture(repo_root)

            render_artifacts.write_generated_artifacts(repo_root)

            landing_page_path = repo_root / "generated" / "subscriptions" / "index.html"
            self.assertTrue(landing_page_path.exists(), "generated landing page should exist for root access")

            landing_page = landing_page_path.read_text(encoding="utf-8")
            self.assertIn("GG Proxy Subscriptions", landing_page)
            self.assertIn("不需要用户名密码", landing_page)
            self.assertIn("/subscriptions/v2ray_nodes.txt", landing_page)
            self.assertIn("mihomo-universal.yaml", landing_page)
            self.assertIn("sing-box", landing_page)
            self.assertIn("GG-Lisahost-KR", landing_page)
            self.assertIn("GG-Dedirock", landing_page)
            self.assertIn("GG-US-SEA-BGP-01", landing_page)
            self.assertIn("linear-gradient(135deg, #fdf7e3", landing_page)
            self.assertIn("copyToClipboard", landing_page)
            self.assertIn("aria-label=\"复制多节点订阅 URL\"", landing_page)


if __name__ == "__main__":
    unittest.main()
