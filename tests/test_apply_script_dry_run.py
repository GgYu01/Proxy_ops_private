from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ApplyStandaloneDryRunTests(unittest.TestCase):
    def test_dry_run_prints_target_files_and_verification_commands(self) -> None:
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "apply_standalone_node.sh"), "--dry-run", "--node", "dedirock"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("Target node: dedirock", result.stdout)
        self.assertIn("Files to upload:", result.stdout)
        self.assertIn("Verification commands:", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)


if __name__ == "__main__":
    unittest.main()
