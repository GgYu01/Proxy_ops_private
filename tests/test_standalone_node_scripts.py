from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PRIVATE_SCRIPT_APPLY = WORKSPACE_ROOT / "repos" / "proxy_ops_private" / "scripts" / "apply_standalone_node.sh"
PRIVATE_SCRIPT_CHECK = WORKSPACE_ROOT / "repos" / "proxy_ops_private" / "scripts" / "check_standalone_node.sh"
PUBLIC_REPO_ROOT = WORKSPACE_ROOT / "repos" / "remote_proxy"


class StandaloneNodeScriptTests(unittest.TestCase):
    def _bash(self) -> str:
        bash = shutil.which("bash")
        if bash is None and Path("C:/Program Files/Git/bin/bash.exe").exists():
            bash = "C:/Program Files/Git/bin/bash.exe"
        self.assertIsNotNone(bash, "bash is required for standalone node script tests")
        return str(bash)

    def _bash_path(self, path: Path) -> str:
        resolved = path.resolve()
        if os.name == "nt" and resolved.drive:
            drive = resolved.drive.rstrip(":").lower()
            tail = resolved.as_posix().split(":", 1)[1]
            return f"/{drive}{tail}"
        return resolved.as_posix()

    def _python(self) -> str:
        venv_python = WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        python = shutil.which("python") or shutil.which("python3")
        self.assertIsNotNone(python, "python is required for standalone node script tests")
        return str(python)

    def _write_private_fixture(self, root: Path) -> None:
        (root / "inventory").mkdir(parents=True, exist_ok=True)
        (root / "secrets" / "nodes").mkdir(parents=True, exist_ok=True)
        (root / "generated" / "standalone").mkdir(parents=True, exist_ok=True)
        (root / "inventory" / "nodes.yaml").write_text(
            json.dumps(
                {
                    "nodes": [
                        {
                            "name": "vmrack1",
                            "host": "example.invalid",
                            "ssh_port": 22,
                            "base_port": 10000,
                            "proxy_domain": "vmrack1.proxy.prod.gglohh.top",
                            "subscription_alias": "GG-Vmrack1",
                            "enabled": True,
                            "include_in_subscription": True,
                            "infra_core_candidate": True,
                            "change_policy": "mutable",
                            "provider": "VMRack",
                            "deployment_topology": "standalone_vps",
                            "runtime_service": "cliproxy-plus",
                        }
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "secrets" / "nodes" / "vmrack1.env").write_text(
            "\n".join(
                [
                    "PROXY_USER=admin",
                    "PROXY_PASS=Aa123456",
                    "SS_PASSWORD=secret_ss_password",
                    "VLESS_UUID=46e1f1cc-6476-4fbc-b25d-969fa643c816",
                    "REALITY_PRIVATE_KEY=test-private",
                    "REALITY_PUBLIC_KEY=test-public",
                    "REALITY_SHORT_ID=e0924c6d9062f4d5",
                    "REALITY_SERVER_NAMES=www.microsoft.com,microsoft.com",
                    "SING_BOX_IMAGE=ghcr.io/sagernet/sing-box:v1.13.2",
                    "ENABLE_DEPRECATED_SING_BOX_FLAGS=true",
                    "MEMORY_LIMIT=256M",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_fake_bin(self, root: Path) -> Path:
        fake_bin = root / "fake-bin"
        fake_bin.mkdir(parents=True, exist_ok=True)
        log_path = root / "fake-transport.log"
        python_path = self._bash_path(Path(self._python()))
        (fake_bin / "python3").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"exec '{python_path}' \"$@\"\n",
            encoding="utf-8",
        )
        (fake_bin / "sshpass").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf 'sshpass %s\\n' \"$*\" >> \"$FAKE_TRANSPORT_LOG\"\n"
            "if [[ \"$1\" == '-e' ]]; then\n"
            "  shift\n"
            "fi\n"
            "exec \"$@\"\n",
            encoding="utf-8",
        )
        (fake_bin / "ssh").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf 'ssh %s\\n' \"$*\" >> \"$FAKE_TRANSPORT_LOG\"\n"
            "if [[ ! -t 0 ]]; then\n"
            "  cat >/dev/null || true\n"
            "fi\n"
            "exit 0\n",
            encoding="utf-8",
        )
        os.chmod(fake_bin / "python3", 0o755)
        os.chmod(fake_bin / "sshpass", 0o755)
        os.chmod(fake_bin / "ssh", 0o755)
        return log_path

    def test_apply_script_stages_complete_bundle_and_invokes_remote_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            self._write_private_fixture(temp_root)
            log_path = self._write_fake_bin(temp_root)
            env = os.environ.copy()
            env["PATH"] = f"{temp_root / 'fake-bin'}{os.pathsep}{env['PATH']}"
            env["FAKE_TRANSPORT_LOG"] = str(log_path)
            env["PYTHON"] = self._python()
            env["PROXY_OPS_PRIVATE_ROOT_OVERRIDE"] = str(temp_root)
            env["REMOTE_PROXY_PUBLIC_REPO_DIR"] = str(PUBLIC_REPO_ROOT)
            env["REMOTE_PROXY_SSH_PASSWORD_VMRACK1"] = "test-password"

            result = subprocess.run(
                [
                    self._bash(),
                    "-lc",
                    f"export PATH='{self._bash_path(temp_root / 'fake-bin')}':$PATH; "
                    f"'{self._bash_path(PRIVATE_SCRIPT_APPLY)}' --node vmrack1",
                ],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            bundle_root = temp_root / "generated" / "standalone" / "vmrack1"
            self.assertTrue((bundle_root / "install.sh").exists())
            self.assertTrue((bundle_root / "config.env").exists())
            self.assertIn(
                "PROXY_PUBLIC_HOST=vmrack1.proxy.prod.gglohh.top",
                (bundle_root / "config.env").read_text(encoding="utf-8"),
            )
            self.assertTrue((bundle_root / "singbox.json").exists())
            self.assertTrue((bundle_root / "config" / "cliproxy-plus.env").exists())
            self.assertTrue((bundle_root / "config" / "cliproxy-plus.env.example").exists())
            self.assertTrue((bundle_root / "scripts" / "lib" / "runtime_compat.sh").exists())
            bundled_cliproxy_deploy = (
                bundle_root / "scripts" / "services" / "cliproxy_plus" / "deploy.sh"
            ).read_text(encoding="utf-8")
            self.assertIn("Traefik discovery labels", bundled_cliproxy_deploy)
            self.assertNotIn("PublishPort=${CLIPROXY_PORT}", bundled_cliproxy_deploy)
            self.assertNotIn("-p ${CLIPROXY_PORT}:${CLIPROXY_PORT}", bundled_cliproxy_deploy)
            transport_log = log_path.read_text(encoding="utf-8")
            self.assertIn("root@example.invalid", transport_log)
            self.assertIn("./install.sh cliproxy-plus", transport_log)
            self.assertIn("./scripts/service.sh cliproxy-plus verify", transport_log)
            self.assertIn("systemctl is-active cliproxy-plus", transport_log)

    def test_apply_script_uses_existing_ssh_when_password_env_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            self._write_private_fixture(temp_root)
            log_path = self._write_fake_bin(temp_root)
            env = os.environ.copy()
            env["PATH"] = f"{temp_root / 'fake-bin'}{os.pathsep}{env['PATH']}"
            env["FAKE_TRANSPORT_LOG"] = str(log_path)
            env["PYTHON"] = self._python()
            env["PROXY_OPS_PRIVATE_ROOT_OVERRIDE"] = str(temp_root)
            env["REMOTE_PROXY_PUBLIC_REPO_DIR"] = str(PUBLIC_REPO_ROOT)

            result = subprocess.run(
                [
                    self._bash(),
                    "-lc",
                    f"export PATH='{self._bash_path(temp_root / 'fake-bin')}':$PATH; "
                    f"'{self._bash_path(PRIVATE_SCRIPT_APPLY)}' --node vmrack1",
                ],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            transport_log = log_path.read_text(encoding="utf-8")
            self.assertIn("root@example.invalid", transport_log)
            self.assertNotIn("sshpass", transport_log)

    def test_check_script_invokes_remote_verification_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            self._write_private_fixture(temp_root)
            log_path = self._write_fake_bin(temp_root)
            env = os.environ.copy()
            env["PATH"] = f"{temp_root / 'fake-bin'}{os.pathsep}{env['PATH']}"
            env["FAKE_TRANSPORT_LOG"] = str(log_path)
            env["PYTHON"] = self._python()
            env["PROXY_OPS_PRIVATE_ROOT_OVERRIDE"] = str(temp_root)
            env["REMOTE_PROXY_SSH_PASSWORD_VMRACK1"] = "test-password"

            result = subprocess.run(
                [
                    self._bash(),
                    "-lc",
                    f"export PATH='{self._bash_path(temp_root / 'fake-bin')}':$PATH; "
                    f"'{self._bash_path(PRIVATE_SCRIPT_CHECK)}' --node vmrack1",
                ],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            transport_log = log_path.read_text(encoding="utf-8")
            self.assertIn("./scripts/service.sh cliproxy-plus verify", transport_log)
            self.assertIn("systemctl is-active cliproxy-plus", transport_log)


if __name__ == "__main__":
    unittest.main()
