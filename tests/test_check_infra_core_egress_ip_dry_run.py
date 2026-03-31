from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CheckInfraCoreEgressIpDryRunTests(unittest.TestCase):
    def test_dry_run_prints_probe_plan_and_container_scope(self) -> None:
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "check_infra_core_egress_ip.sh"), "--dry-run"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("cli-proxy-api-plus", result.stdout)
        self.assertIn("openai.com/cdn-cgi/trace", result.stdout)
        self.assertIn("ifconfig.me/ip", result.stdout)
        self.assertIn("helper container fallback", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)


if __name__ == "__main__":
    unittest.main()
