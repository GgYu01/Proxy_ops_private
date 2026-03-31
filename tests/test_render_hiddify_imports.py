from __future__ import annotations

import importlib.util
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


class HiddifyImportRenderTests(unittest.TestCase):
    def test_multi_node_hiddify_import_points_to_multi_node_subscription(self) -> None:
        render_artifacts = load_module()

        deeplink = render_artifacts.render_hiddify_import(REPO_ROOT)

        self.assertIn("/subscriptions/v2ray_nodes.txt", deeplink)
        self.assertIn("#GG%20Proxy%20Nodes", deeplink)

    def test_single_node_hiddify_import_points_to_single_node_subscription(self) -> None:
        render_artifacts = load_module()

        deeplink = render_artifacts.render_hiddify_import(REPO_ROOT, node_name="akilecloud")

        self.assertIn("/subscriptions/v2ray_node_akilecloud.txt", deeplink)
        self.assertIn("#GG-Akile", deeplink)


if __name__ == "__main__":
    unittest.main()
