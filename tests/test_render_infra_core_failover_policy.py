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


class InfraCoreFailoverPolicyRenderTests(unittest.TestCase):
    def test_failover_policy_uses_expected_priority_order_and_probe_target(self) -> None:
        render_artifacts = load_module()

        policy = json.loads(render_artifacts.render_infra_core_failover_policy(REPO_ROOT))

        self.assertEqual("proxy_failover", policy["selector_tag"])
        self.assertEqual("proxy_lisahost", policy["default_tag"])
        self.assertEqual("http://www.gstatic.com/generate_204", policy["probe_url"])
        self.assertEqual(
            ["proxy_lisahost", "proxy_akilecloud", "proxy_dedirock"],
            [item["tag"] for item in policy["priority"]],
        )


if __name__ == "__main__":
    unittest.main()
