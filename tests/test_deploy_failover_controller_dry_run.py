from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DeployFailoverControllerDryRunTests(unittest.TestCase):
    def test_dry_run_prints_cron_plan(self) -> None:
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "deploy_infra_core_failover_controller.sh"), "--dry-run"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("reconcile_failover.py", result.stdout)
        self.assertIn("infra-core-vless-failover", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)


if __name__ == "__main__":
    unittest.main()
