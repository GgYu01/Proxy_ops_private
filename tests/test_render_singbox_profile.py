from __future__ import annotations

import importlib.util
import json
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


class SingboxProfileRenderTests(unittest.TestCase):
    def test_remote_profile_manifest_contains_url_and_deeplink(self) -> None:
        render_artifacts = load_module()

        manifest = json.loads(render_artifacts.render_singbox_remote_profile(REPO_ROOT))

        self.assertEqual("GG Proxy Nodes Remote", manifest["name"])
        self.assertTrue(manifest["url"].startswith("https://"))
        self.assertIn("sing-box://import-remote-profile?url=", manifest["deeplink"])

    def test_generated_artifacts_include_both_singbox_manifest_filenames(self) -> None:
        render_artifacts = load_module()

        render_artifacts.write_generated_artifacts(REPO_ROOT)

        self.assertTrue((REPO_ROOT / "generated" / "subscriptions" / "singbox-client-profile.json").exists())
        self.assertTrue((REPO_ROOT / "generated" / "subscriptions" / "singbox_remote_profile.json").exists())

    def test_generated_artifacts_include_single_node_subscription_variants(self) -> None:
        render_artifacts = load_module()

        render_artifacts.write_generated_artifacts(REPO_ROOT)

        self.assertTrue((REPO_ROOT / "generated" / "subscriptions" / "v2ray_node_lisahost.txt").exists())
        self.assertTrue((REPO_ROOT / "generated" / "subscriptions" / "v2ray_node_akilecloud.txt").exists())
        self.assertTrue((REPO_ROOT / "generated" / "subscriptions" / "v2ray_node_dedirock.txt").exists())
        self.assertTrue((REPO_ROOT / "generated" / "subscriptions" / "hiddify_import_lisahost.txt").exists())
        self.assertTrue((REPO_ROOT / "generated" / "subscriptions" / "hiddify_import_akilecloud.txt").exists())
        self.assertTrue((REPO_ROOT / "generated" / "subscriptions" / "hiddify_import_dedirock.txt").exists())


if __name__ == "__main__":
    unittest.main()
