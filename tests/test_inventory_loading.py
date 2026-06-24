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

        self.assertEqual(
            {"lisahost", "lisahost_kr", "vmrack1", "vmrack2", "dedirock", "us_sea_bgp_01"},
            set(nodes),
        )
        self.assertEqual("mutable", nodes["lisahost"]["change_policy"])
        self.assertEqual("mutable", nodes["lisahost_kr"]["change_policy"])
        self.assertEqual("mutable", nodes["vmrack1"]["change_policy"])
        self.assertEqual("mutable", nodes["vmrack2"]["change_policy"])
        self.assertEqual("mutable", nodes["dedirock"]["change_policy"])
        self.assertEqual("validation", nodes["dedirock"]["rollout_role"])
        self.assertEqual("standalone_vps", nodes["lisahost"]["deployment_topology"])
        self.assertEqual("cliproxy-plus", nodes["lisahost"]["runtime_service"])
        self.assertEqual("203.227.191.106", nodes["lisahost_kr"]["host"])
        self.assertEqual(32437, nodes["lisahost_kr"]["ssh_port"])
        self.assertEqual("root", nodes["lisahost_kr"]["ssh_user"])
        self.assertEqual("standalone_vps", nodes["lisahost_kr"]["deployment_topology"])
        self.assertEqual("singbox", nodes["lisahost_kr"]["runtime_service"])
        self.assertEqual("standalone_vps", nodes["vmrack1"]["deployment_topology"])
        self.assertEqual("cliproxy-plus", nodes["vmrack1"]["runtime_service"])
        self.assertEqual("standalone_vps", nodes["vmrack2"]["deployment_topology"])
        self.assertEqual("cliproxy-plus", nodes["vmrack2"]["runtime_service"])
        self.assertEqual("standalone_vps", nodes["dedirock"]["deployment_topology"])
        self.assertEqual("cliproxy-plus", nodes["dedirock"]["runtime_service"])
        self.assertEqual("69.5.53.82", nodes["us_sea_bgp_01"]["host"])
        self.assertEqual(42778, nodes["us_sea_bgp_01"]["ssh_port"])
        self.assertEqual("root", nodes["us_sea_bgp_01"]["ssh_user"])
        self.assertEqual("standalone_vps", nodes["us_sea_bgp_01"]["deployment_topology"])
        self.assertEqual("singbox", nodes["us_sea_bgp_01"]["runtime_service"])

        for node_name in ("us_sea_bgp_01", "vmrack1", "dedirock"):
            self.assertEqual("www.cloudflare.com:443", nodes[node_name]["reality_dest"])
            self.assertEqual("www.cloudflare.com", nodes[node_name]["reality_server_names"])


if __name__ == "__main__":
    unittest.main()
