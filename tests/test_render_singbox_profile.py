from __future__ import annotations

import importlib.util
import json
import os
import re
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


class SingboxProfileRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_skip_probe = os.environ.get("SKIP_AVAILABILITY_PROBE")
        os.environ["SKIP_AVAILABILITY_PROBE"] = "1"

    def tearDown(self) -> None:
        if self._old_skip_probe is None:
            os.environ.pop("SKIP_AVAILABILITY_PROBE", None)
        else:
            os.environ["SKIP_AVAILABILITY_PROBE"] = self._old_skip_probe

    def test_remote_profile_manifest_contains_url_and_deeplink(self) -> None:
        render_artifacts = load_module()

        manifest = json.loads(render_artifacts.render_singbox_remote_profile(REPO_ROOT))

        self.assertEqual("GG Proxy Nodes Remote", manifest["name"])
        self.assertTrue(manifest["url"].startswith("https://"))
        self.assertIn("sing-box://import-remote-profile?url=", manifest["deeplink"])

    def test_generated_artifacts_include_both_singbox_manifest_filenames(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            self.assertTrue((repo_root / "generated" / "subscriptions" / "singbox-client-profile.json").exists())
            self.assertTrue((repo_root / "generated" / "subscriptions" / "singbox_remote_profile.json").exists())

    def test_generated_artifacts_include_single_node_subscription_variants(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            self.assertTrue((repo_root / "generated" / "subscriptions" / "v2ray_node_vmrack1.txt").exists())
            self.assertTrue((repo_root / "generated" / "subscriptions" / "v2ray_node_dedirock.txt").exists())
            self.assertTrue((repo_root / "generated" / "subscriptions" / "v2ray_node_us_sea_bgp_01.txt").exists())
            self.assertFalse((repo_root / "generated" / "subscriptions" / "v2ray_node_lisahost.txt").exists())
            self.assertFalse((repo_root / "generated" / "subscriptions" / "v2ray_node_lisahost_kr.txt").exists())
            self.assertFalse((repo_root / "generated" / "subscriptions" / "v2ray_node_vmrack2.txt").exists())
            self.assertTrue((repo_root / "generated" / "subscriptions" / "singbox-client-profile.json").exists())

    def test_generated_subscription_profiles_use_raw_ips_not_proxy_domains(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            mihomo = (repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml").read_text(encoding="utf-8")
            v2ray = (repo_root / "generated" / "subscriptions" / "v2ray_nodes.txt").read_text(encoding="utf-8")
            singbox = json.loads((repo_root / "generated" / "subscriptions" / "singbox-client-profile.json").read_text(encoding="utf-8"))
        self.assertIn("server: 69.5.53.82", mihomo)
        self.assertIn("server: 38.65.93.39", mihomo)
        self.assertIn("server: 67.215.238.140", mihomo)
        self.assertNotIn("server: 38.34.8.59", mihomo)
        self.assertNotIn("server: 203.227.191.106", mihomo)
        self.assertNotIn("server: 38.65.93.94", mihomo)
        self.assertIsNotNone(re.search(r"server:\s*(?:\d{1,3}\.){3}\d{1,3}", mihomo))
        self.assertNotIn(".proxy.prod.gglohh.top", mihomo)
        self.assertIn("@69.5.53.82:10003", v2ray)
        self.assertIn("@38.65.93.39:10003", v2ray)
        self.assertIn("@67.215.238.140:10003", v2ray)
        self.assertNotIn("@38.34.8.59:10003", v2ray)
        self.assertNotIn("@203.227.191.106:10003", v2ray)
        self.assertNotIn("@38.65.93.94:10003", v2ray)
        self.assertIsNotNone(re.search(r"vless://.*@(?:\d{1,3}\.){3}\d{1,3}", v2ray))
        self.assertNotIn(".proxy.prod.gglohh.top", v2ray)
        self.assertIn("IP-CIDR,69.5.53.82/32,DIRECT,no-resolve", mihomo)
        self.assertIn("IP-CIDR,38.65.93.39/32,DIRECT,no-resolve", mihomo)
        self.assertIn("IP-CIDR,67.215.238.140/32,DIRECT,no-resolve", mihomo)
        self.assertLess(
            mihomo.index("IP-CIDR,69.5.53.82/32,DIRECT,no-resolve"),
            mihomo.index("DOMAIN-SUFFIX,openai.com,PROXY"),
        )
        self.assertEqual(
            "https://subs.sea.prod.gglohh.top/subscriptions/singbox-client-profile.json",
            singbox["url"],
        )
        self.assertIn(
            "https%3A%2F%2Fsubs.sea.prod.gglohh.top%2Fsubscriptions%2Fsingbox-client-profile.json",
            singbox["deeplink"],
        )


if __name__ == "__main__":
    unittest.main()
