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


class InfraCoreConfigRenderTests(unittest.TestCase):
    def test_infra_core_config_contains_priority_failover_and_direct_rules(self) -> None:
        render_artifacts = load_module()

        config = json.loads(render_artifacts.render_infra_core_config(REPO_ROOT))
        outbounds = {item["tag"]: item for item in config["outbounds"]}
        route_rules = config["route"]["rules"]

        self.assertIn("proxy_lisahost", outbounds)
        self.assertIn("proxy_dedirock", outbounds)
        self.assertIn("proxy_akilecloud", outbounds)
        self.assertIn("proxy_failover", outbounds)
        self.assertIn("direct", outbounds)
        self.assertEqual("selector", outbounds["proxy_failover"]["type"])
        self.assertEqual(
            ["proxy_lisahost", "proxy_akilecloud", "proxy_dedirock"],
            outbounds["proxy_failover"]["outbounds"],
        )
        self.assertEqual("proxy_lisahost", outbounds["proxy_failover"]["default"])
        self.assertTrue(any(rule.get("ip_is_private") is True for rule in route_rules))
        self.assertTrue(any("svc.prod.lab.gglohh.top" in rule.get("domain_suffix", []) for rule in route_rules))
        self.assertTrue(
            any(rule.get("outbound") == "proxy_failover" for rule in route_rules if "domain_suffix" in rule or "domain_keyword" in rule)
        )


if __name__ == "__main__":
    unittest.main()
