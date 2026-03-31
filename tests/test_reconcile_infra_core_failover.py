from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "reconcile_infra_core_failover.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reconcile_infra_core_failover", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReconcileFailoverTests(unittest.TestCase):
    def test_choose_active_tag_prefers_first_healthy_in_priority_order(self) -> None:
        module = load_module()
        choice = module.choose_active_tag(
            ["proxy_lisahost", "proxy_akilecloud", "proxy_dedirock"],
            {
                "proxy_lisahost": False,
                "proxy_akilecloud": True,
                "proxy_dedirock": True,
            },
            "proxy_dedirock",
        )
        self.assertEqual("proxy_akilecloud", choice)

    def test_choose_active_tag_returns_current_when_all_probes_fail(self) -> None:
        module = load_module()
        choice = module.choose_active_tag(
            ["proxy_lisahost", "proxy_akilecloud", "proxy_dedirock"],
            {
                "proxy_lisahost": False,
                "proxy_akilecloud": False,
                "proxy_dedirock": False,
            },
            "proxy_akilecloud",
        )
        self.assertEqual("proxy_akilecloud", choice)


if __name__ == "__main__":
    unittest.main()
