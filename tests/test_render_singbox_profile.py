from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "render_artifacts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("render_artifacts", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_fixture(tmp_path: Path) -> Path:
    repo_root = tmp_path / "proxy_ops_private"
    shutil.copytree(REPO_ROOT / "inventory", repo_root / "inventory")
    shutil.copytree(REPO_ROOT / "secrets", repo_root / "secrets")
    (repo_root / "state").mkdir(parents=True)
    (repo_root / "state" / "node_availability.json").write_text(
        json.dumps(
            {
                "updated_at": "2026-06-23T00:00:00Z",
                "nodes": {
                    name: {
                        "last_probe_at": "2026-06-23T00:00:00Z",
                        "last_health": "healthy",
                        "unavailable_since": None,
                        "last_success_at": "2026-06-23T00:00:00Z",
                        "detail": "fixture real proxy probe passed",
                    }
                    for name in ("us_sea_bgp_01", "vmrack1", "dedirock")
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return repo_root


class SingboxProfileRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_skip_probe = os.environ.get("SKIP_AVAILABILITY_PROBE")
        os.environ["SKIP_AVAILABILITY_PROBE"] = "1"

    def tearDown(self) -> None:
        if self._old_skip_probe is None:
            os.environ.pop("SKIP_AVAILABILITY_PROBE", None)
        else:
            os.environ["SKIP_AVAILABILITY_PROBE"] = self._old_skip_probe

    def test_remote_profile_manifest_contains_url_and_deeplink(self) -> None:
        render_artifacts = load_module()

        manifest = json.loads(render_artifacts.render_singbox_remote_profile(REPO_ROOT))

        self.assertEqual("GG Proxy Nodes Remote", manifest["name"])
        self.assertTrue(manifest["url"].startswith("https://"))
        self.assertIn("sing-box://import-remote-profile?url=", manifest["deeplink"])

    def test_generated_artifacts_include_both_singbox_manifest_filenames(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            self.assertTrue((repo_root / "generated" / "subscriptions" / "singbox-client-profile.json").exists())
            self.assertTrue((repo_root / "generated" / "subscriptions" / "singbox_remote_profile.json").exists())

    def test_generated_artifacts_include_single_node_subscription_variants(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            self.assertTrue((repo_root / "generated" / "subscriptions" / "v2ray_node_vmrack1.txt").exists())
            self.assertTrue((repo_root / "generated" / "subscriptions" / "v2ray_node_dedirock.txt").exists())
            self.assertTrue((repo_root / "generated" / "subscriptions" / "v2ray_node_us_sea_bgp_01.txt").exists())
            self.assertFalse((repo_root / "generated" / "subscriptions" / "v2ray_node_lisahost.txt").exists())
            self.assertFalse((repo_root / "generated" / "subscriptions" / "v2ray_node_lisahost_kr.txt").exists())
            self.assertFalse((repo_root / "generated" / "subscriptions" / "v2ray_node_vmrack2.txt").exists())
            self.assertTrue((repo_root / "generated" / "subscriptions" / "singbox-client-profile.json").exists())

    def test_generated_subscription_profiles_use_raw_ips_not_proxy_domains(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            mihomo = (repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml").read_text(encoding="utf-8")
            v2ray = (repo_root / "generated" / "subscriptions" / "v2ray_nodes.txt").read_text(encoding="utf-8")
            singbox = json.loads((repo_root / "generated" / "subscriptions" / "singbox-client-profile.json").read_text(encoding="utf-8"))
        self.assertIn("server: 69.5.53.82", mihomo)
        self.assertIn("server: 38.65.93.39", mihomo)
        self.assertIn("server: 67.215.238.140", mihomo)
        self.assertNotIn("server: 38.34.8.59", mihomo)
        self.assertNotIn("server: 203.227.191.106", mihomo)
        self.assertNotIn("server: 38.65.93.94", mihomo)
        self.assertIsNotNone(re.search(r"server:\s*(?:\d{1,3}\.){3}\d{1,3}", mihomo))
        self.assertNotIn(".proxy.prod.gglohh.top", mihomo)
        self.assertIn("@69.5.53.82:10003", v2ray)
        self.assertIn("@38.65.93.39:10003", v2ray)
        self.assertIn("@67.215.238.140:10003", v2ray)
        self.assertNotIn("@38.34.8.59:10003", v2ray)
        self.assertNotIn("@203.227.191.106:10003", v2ray)
        self.assertNotIn("@38.65.93.94:10003", v2ray)
        self.assertIsNotNone(re.search(r"vless://.*@(?:\d{1,3}\.){3}\d{1,3}", v2ray))
        self.assertNotIn(".proxy.prod.gglohh.top", v2ray)
        self.assertIn("IP-CIDR,69.5.53.82/32,DIRECT,no-resolve", mihomo)
        self.assertIn("IP-CIDR,38.65.93.39/32,DIRECT,no-resolve", mihomo)
        self.assertIn("IP-CIDR,67.215.238.140/32,DIRECT,no-resolve", mihomo)
        self.assertLess(
            mihomo.index("IP-CIDR,69.5.53.82/32,DIRECT,no-resolve"),
            mihomo.index("DOMAIN-SUFFIX,openai.com,ChatGPT"),
        )
        self.assertEqual(
            "https://subs.sea.prod.gglohh.top/subscriptions/singbox-client-profile.json",
            singbox["url"],
        )
        self.assertIn(
            "https%3A%2F%2Fsubs.sea.prod.gglohh.top%2Fsubscriptions%2Fsingbox-client-profile.json",
            singbox["deeplink"],
        )

    def test_mihomo_profile_keeps_gglohh_top_direct_and_exempt_from_fake_ip(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            mihomo = (repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml").read_text(encoding="utf-8")

        self.assertIn("DOMAIN-SUFFIX,gglohh.top,DIRECT", mihomo)
        self.assertIn("+.gglohh.top", mihomo)
        self.assertIn("*.gglohh.top", mihomo)
        self.assertIn("nameserver-policy:", mihomo)
        self.assertIn("223.5.5.5", mihomo)
        self.assertIn("119.29.29.29", mihomo)
        self.assertLess(mihomo.index("DOMAIN-SUFFIX,gglohh.top,DIRECT"), mihomo.index("RULE-SET,proxy,PROXY"))
        self.assertLess(mihomo.index("DOMAIN-SUFFIX,gglohh.top,DIRECT"), mihomo.index("RULE-SET,gfw,PROXY"))

    def test_mihomo_profile_keeps_ringzle_direct_and_exempt_from_fake_ip(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            mihomo = (repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml").read_text(encoding="utf-8")

        self.assertIn("DOMAIN-SUFFIX,ringzle.com,DIRECT", mihomo)
        self.assertIn("+.ringzle.com", mihomo)
        self.assertIn("*.ringzle.com", mihomo)
        self.assertIn("+.ringzle.com:", mihomo)
        self.assertIn("PROCESS-NAME,ssh.exe,DIRECT", mihomo)
        self.assertIn("PROCESS-NAME,git.exe,DIRECT", mihomo)
        self.assertLess(mihomo.index("DOMAIN-SUFFIX,ringzle.com,DIRECT"), mihomo.index("RULE-SET,proxy,PROXY"))
        self.assertLess(mihomo.index("DOMAIN-SUFFIX,ringzle.com,DIRECT"), mihomo.index("RULE-SET,gfw,PROXY"))

    def test_mihomo_profile_keeps_mirror_domains_direct_and_exempt_from_fake_ip(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            mihomo = (repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml").read_text(encoding="utf-8")

        for domain in (
            "mirrors.tuna.tsinghua.edu.cn",
            "deb.debian.org",
            "docker.m.daocloud.io",
            "daocloud.io",
        ):
            self.assertIn(f"DOMAIN-SUFFIX,{domain},DIRECT", mihomo)
            self.assertIn(domain, mihomo)
            self.assertIn(f"+.{domain}", mihomo)
            self.assertIn(f"+.{domain}:", mihomo)
        self.assertLess(
            mihomo.index("DOMAIN-SUFFIX,mirrors.tuna.tsinghua.edu.cn,DIRECT"),
            mihomo.index("RULE-SET,proxy,PROXY"),
        )

    def test_mihomo_profile_includes_vmrack_and_qqpw_distinct_ports(self) -> None:
        render_artifacts = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_artifacts.write_generated_artifacts(repo_root)

            mihomo = (repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml").read_text(encoding="utf-8")
            v2ray = (repo_root / "generated" / "subscriptions" / "v2ray_nodes.txt").read_text(encoding="utf-8")

        self.assertIn("name: GG-Vmrack1", mihomo)
        self.assertNotIn("name: GG-Vmrack1-Hysteria2", mihomo)
        self.assertNotIn("name: QQPW-Residential-SOCKS5", mihomo)
        self.assertIn("name: QQPW-Residential-Reality", mihomo)
        self.assertIn("name: QQPW-Residential-Hysteria2", mihomo)
        self.assertIn("name: ChatGPT", mihomo)
        self.assertIn("name: PROXY", mihomo)
        self.assertNotIn("name: Vmrack-Public", mihomo)
        self.assertNotIn("name: QQPW-Residential\n", mihomo)
        self.assertRegex(
            mihomo,
            r"name: GG-Vmrack1\r?\n\s+type: vless\r?\n\s+server: 38\.65\.93\.39\r?\n\s+port: 10003",
        )
        self.assertRegex(
            mihomo,
            r"name: QQPW-Residential-Reality\r?\n\s+type: vless\r?\n\s+server: 38\.65\.93\.39\r?\n\s+port: 10006",
        )
        self.assertRegex(
            mihomo,
            r"name: QQPW-Residential-Hysteria2\r?\n\s+type: hysteria2\r?\n\s+server: 38\.65\.93\.39\r?\n\s+port: 10005",
        )
        # ChatGPT group defaults to QQPW VLESS Reality; Hy2 is bonus after it.
        chatgpt_block = re.search(
            r"name: ChatGPT\r?\n\s+type: select\r?\n\s+proxies:\r?\n((?:\s+- .+\r?\n)+)",
            mihomo,
        )
        self.assertIsNotNone(chatgpt_block)
        chatgpt_proxies = chatgpt_block.group(1)
        self.assertLess(
            chatgpt_proxies.index("QQPW-Residential-Reality"),
            chatgpt_proxies.index("QQPW-Residential-Hysteria2"),
        )
        self.assertLess(
            chatgpt_proxies.index("QQPW-Residential-Reality"),
            chatgpt_proxies.index("GG-Vmrack1"),
        )
        self.assertIn("DOMAIN-SUFFIX,openai.com,ChatGPT", mihomo)
        self.assertIn("PROCESS-NAME,msedge.exe,ChatGPT", mihomo)
        self.assertIn("RULE-SET,cn,DIRECT", mihomo)
        # CN DIRECT must win before browser→ChatGPT process rules.
        self.assertLess(
            mihomo.index("RULE-SET,cn,DIRECT"),
            mihomo.index("PROCESS-NAME,msedge.exe,ChatGPT"),
        )
        self.assertLess(
            mihomo.index("DOMAIN-SUFFIX,openai.com,ChatGPT"),
            mihomo.index("RULE-SET,cn,DIRECT"),
        )
        # Old alias bug: QQPW Reality must never share the public VLESS port.
        self.assertNotRegex(
            mihomo,
            r"name: QQPW-Residential-Reality\r?\n(?:.*\r?\n){0,6}\s+port: 10003",
        )
        self.assertNotIn("QQPW-Residential-SOCKS5", v2ray)
        self.assertIn("QQPW-Residential-Reality", v2ray)
        self.assertIn("QQPW-Residential-Hysteria2", v2ray)
        self.assertNotIn("GG-Vmrack1-Hysteria2", v2ray)
        self.assertNotIn("@38.65.93.39:10007", v2ray)
        self.assertIn("@38.65.93.39:10006", v2ray)
        self.assertNotIn("@38.65.93.39:10003#QQPW", v2ray)
if __name__ == "__main__":
    unittest.main()
