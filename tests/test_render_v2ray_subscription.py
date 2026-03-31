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


class V2RayRenderTests(unittest.TestCase):
    def test_v2ray_subscription_contains_all_three_nodes(self) -> None:
        render_artifacts = load_module()

        artifact = render_artifacts.render_v2ray_subscription(REPO_ROOT)

        self.assertIn("GG-Lisa-Stable", artifact)
        self.assertIn("GG-Dedirock", artifact)
        self.assertIn("GG-Akile", artifact)
        self.assertEqual(3, sum(1 for line in artifact.splitlines() if line.startswith("vless://")))

    def test_single_node_subscription_contains_only_requested_node(self) -> None:
        render_artifacts = load_module()

        artifact = render_artifacts.render_v2ray_subscription(REPO_ROOT, node_name="dedirock")

        self.assertIn("GG-Dedirock", artifact)
        self.assertNotIn("GG-Lisa-Stable", artifact)
        self.assertNotIn("GG-Akile", artifact)
        self.assertEqual(1, sum(1 for line in artifact.splitlines() if line.startswith("vless://")))


if __name__ == "__main__":
    unittest.main()
