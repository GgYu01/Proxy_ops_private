from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ApplyInfraCoreDryRunTests(unittest.TestCase):
    def test_dry_run_defaults_to_hot_reload_and_prints_fallback(self) -> None:
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "apply_infra_core_sidecar.sh"), "--dry-run"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("Default path: hot reload", result.stdout)
        self.assertIn("apply_runtime_routing.sh", result.stdout)
        self.assertIn("Full restart fallback:", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)


if __name__ == "__main__":
    unittest.main()
