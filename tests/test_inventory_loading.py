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


class InventoryLoadingTests(unittest.TestCase):
    def test_inventory_has_expected_nodes_and_policies(self) -> None:
        render_artifacts = load_module()

        inventory = render_artifacts.load_nodes_inventory(REPO_ROOT / "inventory" / "nodes.yaml")
        nodes = {node["name"]: node for node in inventory["nodes"]}

        self.assertEqual({"lisahost", "dedirock", "akilecloud"}, set(nodes))
        self.assertEqual("frozen", nodes["lisahost"]["change_policy"])
        self.assertEqual("mutable", nodes["dedirock"]["change_policy"])
        self.assertEqual("mutable", nodes["akilecloud"]["change_policy"])


if __name__ == "__main__":
    unittest.main()
