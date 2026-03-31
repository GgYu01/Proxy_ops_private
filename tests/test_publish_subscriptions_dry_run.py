from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublishSubscriptionsDryRunTests(unittest.TestCase):
    def test_dry_run_prints_public_base_url_and_target(self) -> None:
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "publish_subscriptions_to_infra_core.sh"), "--dry-run"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions", result.stdout)
        self.assertIn("/mnt/hdo/infra-core/services/proxy-subscriptions", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)


if __name__ == "__main__":
    unittest.main()
