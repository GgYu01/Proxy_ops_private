from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


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

    def _bash_path(self, path: Path) -> str:
        raw = path.resolve().as_posix()
        if len(raw) >= 3 and raw[1:3] == ":/":
            return f"/{raw[0].lower()}{raw[2:]}"
        return raw

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
        self.assertIn("https://subs.sea.prod.gglohh.top/subscriptions", result.stdout)
        self.assertIn("[INFO] Public landing URL: https://subs.sea.prod.gglohh.top/", result.stdout)
        self.assertIn("/srv/proxy-subscriptions/public/subscriptions", result.stdout)
        self.assertIn("[INFO] Remote config dir: /srv/proxy-subscriptions/config", result.stdout)
        self.assertIn("generated/publish/sea-bgp/gg-proxy-subscriptions.container", result.stdout)
        self.assertIn("generated/publish/sea-bgp/subscription-publish-manifest.json", result.stdout)
        self.assertIn("[INFO] Subscription container unit: gg-proxy-subscriptions", result.stdout)
        self.assertIn("[INFO] Subscription container image: docker.io/library/busybox:1.37", result.stdout)
        self.assertIn("[INFO] Subscription container command: httpd -f -p 80 -h /www", result.stdout)
        self.assertIn("[INFO] Subscription container mount: /srv/proxy-subscriptions/public:/www:ro,Z", result.stdout)
        self.assertIn("[INFO] Subscription public endpoint: HTTPS 443 via Traefik", result.stdout)
        self.assertNotIn("Subscription HTTP publish", result.stdout)
        old_subscription_port = "180" + "80"
        self.assertNotIn(old_subscription_port, result.stdout)
        self.assertIn("Host(`subs.sea.prod.gglohh.top`)", result.stdout)
        self.assertIn("[DRY-RUN]", result.stdout)

    def test_generated_remote_publish_config_is_tracked_in_git(self) -> None:
        config_path = REPO_ROOT / "generated" / "publish" / "sea-bgp" / "gg-proxy-subscriptions.container"
        manifest_path = REPO_ROOT / "generated" / "publish" / "sea-bgp" / "subscription-publish-manifest.json"

        self.assertTrue(config_path.exists())
        self.assertTrue(manifest_path.exists())
        config_text = config_path.read_text(encoding="utf-8")
        self.assertIn("ContainerName=gg-proxy-subscriptions", config_text)
        self.assertIn("Volume=/srv/proxy-subscriptions/public:/www:ro,Z", config_text)
        self.assertIn("Label=traefik.http.routers.sea-subs.rule=Host(`subs.sea.prod.gglohh.top`)", config_text)
        self.assertNotIn("REMOTE_PASSWORD", config_text)
        for path in (config_path, manifest_path):
            result = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", str(path.relative_to(REPO_ROOT))],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)

    def test_inventory_does_not_reference_legacy_subscription_http_unit(self) -> None:
        subscriptions = yaml.safe_load((REPO_ROOT / "inventory" / "subscriptions.yaml").read_text(encoding="utf-8"))
        publish = subscriptions["publish"]

        self.assertNotIn("systemd_unit", publish)
        old_subscription_port = "180" + "80"
        self.assertNotIn(old_subscription_port, str(publish))
        self.assertNotIn("http.service", str(publish))

    def test_availability_probe_targets_published_proxy_port(self) -> None:
        subscriptions = yaml.safe_load((REPO_ROOT / "inventory" / "subscriptions.yaml").read_text(encoding="utf-8"))

        self.assertEqual(3, subscriptions["availability_policy"]["probe_port_offset"])

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

    def test_publish_runs_availability_probe_before_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            bin_dir = workdir / "bin"
            bin_dir.mkdir()
            log_file = workdir / "commands.log"

            python_wrapper = bin_dir / "python"
            python_wrapper.write_text(
                "\n".join(
                    [
                        "#!/bin/sh",
                        f"printf '%s\\n' \"$*\" >> '{log_file.as_posix()}'",
                        "case \"$*\" in",
                        "  *reconcile_subscription_node_availability.py*) exit 0 ;;",
                        "  *render_artifacts.py*) exit 0 ;;",
                        "esac",
                        f"exec '{self._python()}' \"$@\"",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            ssh_wrapper = bin_dir / "ssh"
            ssh_wrapper.write_text(
                "\n".join(
                    [
                        "#!/bin/sh",
                        f"printf 'ssh %s\\n' \"$*\" >> '{log_file.as_posix()}'",
                        "case \"$*\" in",
                        "  *mkdir*) exit 0 ;;",
                        "  *tar*xzf*) mkdir -p /tmp/publish-fixture-stage && tar xzf - -C /tmp/publish-fixture-stage; exit 0 ;;",
                        "  *mv*) exit 0 ;;",
                        "  *systemctl*) exit 0 ;;",
                        "esac",
                        "exit 0",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            curl_wrapper = bin_dir / "curl"
            curl_wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            for wrapper in (python_wrapper, ssh_wrapper, curl_wrapper):
                wrapper.chmod(0o755)

            env = self._env(
                PYTHON=str(python_wrapper),
                SSH_BIN=str(ssh_wrapper),
                REMOTE_HOST="root@example.invalid",
                REMOTE_PORT="42778",
            )
            result = subprocess.run(
                [self._bash(), str(REPO_ROOT / "scripts" / "publish_subscriptions_to_sea_host.sh")],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
            log_text = log_file.read_text(encoding="utf-8")
            self.assertIn("reconcile_subscription_node_availability.py --probe --report", log_text)
            self.assertIn("render_artifacts.py", log_text)
            self.assertLess(
                log_text.index("reconcile_subscription_node_availability.py --probe --report"),
                log_text.index("render_artifacts.py"),
            )
            self.assertIn("/srv/proxy-subscriptions/config.staging", log_text)
            self.assertIn("/srv/proxy-subscriptions/config/gg-proxy-subscriptions.container", log_text)
            self.assertIn("/etc/containers/systemd/gg-proxy-subscriptions.container", log_text)
            self.assertNotIn("cat > '/etc/containers/systemd/gg-proxy-subscriptions.container'", log_text)

    def test_publish_can_use_prevalidated_availability_ledger_without_local_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            bin_dir = workdir / "bin"
            bin_dir.mkdir()
            log_file = workdir / "commands.log"

            python_wrapper = bin_dir / "python"
            python_wrapper.write_text(
                "\n".join(
                    [
                        "#!/bin/sh",
                        f"printf '%s\\n' \"$*\" >> '{log_file.as_posix()}'",
                        "case \"$*\" in",
                        "  *reconcile_subscription_node_availability.py*) exit 0 ;;",
                        "  *render_artifacts.py*) exit 0 ;;",
                        "esac",
                        f"exec '{self._python()}' \"$@\"",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            ssh_wrapper = bin_dir / "ssh"
            ssh_wrapper.write_text(
                "\n".join(
                    [
                        "#!/bin/sh",
                        f"printf 'ssh %s\\n' \"$*\" >> '{log_file.as_posix()}'",
                        "case \"$*\" in",
                        "  *mkdir*) exit 0 ;;",
                        "  *tar*xzf*) mkdir -p /tmp/publish-fixture-stage && tar xzf - -C /tmp/publish-fixture-stage; exit 0 ;;",
                        "  *mv*) exit 0 ;;",
                        "  *systemctl*) exit 0 ;;",
                        "esac",
                        "exit 0",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            curl_wrapper = bin_dir / "curl"
            curl_wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            for wrapper in (python_wrapper, ssh_wrapper, curl_wrapper):
                wrapper.chmod(0o755)

            env = self._env(
                PYTHON=str(python_wrapper),
                SSH_BIN=str(ssh_wrapper),
                REMOTE_HOST="root@example.invalid",
                REMOTE_PORT="42778",
                SEA_SUBSCRIPTION_SKIP_LOCAL_PROBE="1",
            )
            result = subprocess.run(
                [self._bash(), str(REPO_ROOT / "scripts" / "publish_subscriptions_to_sea_host.sh")],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)
            self.assertIn("from existing availability ledger", result.stdout)
            log_text = log_file.read_text(encoding="utf-8")
            self.assertIn("reconcile_subscription_node_availability.py --report", log_text)
            self.assertNotIn("--probe", log_text)
            self.assertIn("render_artifacts.py", log_text)


if __name__ == "__main__":
    unittest.main()
