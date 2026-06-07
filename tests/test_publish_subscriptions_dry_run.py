from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublishSubscriptionsDryRunTests(unittest.TestCase):
    def _bash(self) -> str:
        bash = shutil.which("bash")
        if bash is None and Path("C:/Program Files/Git/bin/bash.exe").exists():
            bash = "C:/Program Files/Git/bin/bash.exe"
        self.assertIsNotNone(bash, "bash is required for publish script dry-run test")
        return str(bash)

    def _python(self) -> str:
        venv_python = REPO_ROOT.parent.parent / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        python = shutil.which("python") or shutil.which("python3")
        self.assertIsNotNone(python, "python is required for publish script dry-run test")
        return str(python)

    def _env(self, **overrides: str) -> dict[str, str]:
        return {**os.environ, "PYTHON": self._python(), **overrides}

    def test_dry_run_prints_public_base_url_and_target(self) -> None:
        env = self._env(
            REMOTE_HOST="root@example.invalid",
            REMOTE_PORT="42778",
        )
        result = subprocess.run(
            [self._bash(), str(REPO_ROOT / "scripts" / "publish_subscriptions_to_sea_host.sh"), "--dry-run"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("[INFO] Publish target: root@example.invalid:42778", result.stdout)
        self.assertIn("http://69.5.53.82:18080/subscriptions", result.stdout)
        self.assertIn("[INFO] Public landing URL: http://69.5.53.82:18080/", result.stdout)
        self.assertIn("/srv/proxy-subscriptions/public/subscriptions", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)

    def test_dry_run_requires_inventory_publish_metadata(self) -> None:
        env = self._env()
        result = subprocess.run(
            [self._bash(), str(REPO_ROOT / "scripts" / "publish_subscriptions_to_sea_host.sh"), "--dry-run"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("us_sea_bgp_01", result.stdout)

    def test_infra_core_wrapper_delegates_to_sea_host_script(self) -> None:
        env = self._env(
            REMOTE_HOST="root@example.invalid",
            REMOTE_PORT="42778",
        )
        result = subprocess.run(
            [self._bash(), str(REPO_ROOT / "scripts" / "publish_subscriptions_to_infra_core.sh"), "--dry-run"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("deprecated", result.stderr.lower())
        self.assertIn("/srv/proxy-subscriptions/public/subscriptions", result.stdout)


if __name__ == "__main__":
    unittest.main()
