from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ApplyStandaloneDryRunTests(unittest.TestCase):
    def _bash(self) -> str:
        bash = shutil.which("bash")
        if bash is None and Path("C:/Program Files/Git/bin/bash.exe").exists():
            bash = "C:/Program Files/Git/bin/bash.exe"
        self.assertIsNotNone(bash, "bash is required for standalone dry-run tests")
        return str(bash)

    def _bash_path(self, path: Path) -> str:
        resolved = path.resolve()
        if os.name == "nt" and resolved.drive:
            drive = resolved.drive.rstrip(":").lower()
            tail = resolved.as_posix().split(":", 1)[1]
            return f"/{drive}{tail}"
        return resolved.as_posix()

    def _write_python_wrapper(self, root: Path) -> Path:
        fake_bin = root / "fake-bin"
        fake_bin.mkdir(parents=True, exist_ok=True)
        python_path = self._bash_path(Path(sys.executable))
        wrapper = fake_bin / "python3"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"exec '{python_path}' \"$@\"\n",
            encoding="utf-8",
        )
        os.chmod(wrapper, 0o755)
        return fake_bin

    def _run_dry_run(self, node: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_bin = self._write_python_wrapper(Path(tmp_dir))
            script = REPO_ROOT / "scripts" / "apply_standalone_node.sh"
            env = os.environ.copy()
            return subprocess.run(
                [
                    self._bash(),
                    "-lc",
                    f"export PATH='{self._bash_path(fake_bin)}':$PATH; "
                    f"'{self._bash_path(script)}' --dry-run --node '{node}'",
                ],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=env,
                check=False,
            )

    def test_dry_run_allows_lisahost_and_prints_cliproxy_rollout_contract(self) -> None:
        result = self._run_dry_run("lisahost")

        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("Target node: lisahost", result.stdout)
        self.assertIn("Files to upload:", result.stdout)
        self.assertIn("config/cliproxy-plus.env", result.stdout)
        self.assertIn("Verification commands:", result.stdout)
        self.assertIn("systemctl is-active cliproxy-plus", result.stdout)
        self.assertIn("./scripts/service.sh cliproxy-plus verify", result.stdout)
        self.assertIn("/etc/remote_proxy", result.stdout)
        self.assertIn("/var/lib/remote_proxy", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)

    def test_dry_run_allows_lisahost_kr_and_prints_singbox_contract(self) -> None:
        result = self._run_dry_run("lisahost_kr")

        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
        self.assertIn("Target node: lisahost_kr", result.stdout)
        self.assertIn("SSH target: root@203.227.191.106:32437", result.stdout)
        self.assertIn("systemctl is-active remote-proxy", result.stdout)
        self.assertIn("./scripts/verify.sh", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)


if __name__ == "__main__":
    unittest.main()
