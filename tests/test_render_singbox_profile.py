from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "render_artifacts.py"
MIHOMO_EXISTING_RENDER_PATH = REPO_ROOT / "scripts" / "render_mihomo_from_existing_profile.py"
FIXTURE_NODE_NAMES = ("lisahost", "lisahost_kr", "vmrack1", "vmrack2", "dedirock", "us_sea_bgp_01")
FIXTURE_HEALTHY_NODE_NAMES = ("us_sea_bgp_01", "vmrack1", "dedirock")


def load_module():
    spec = importlib.util.spec_from_file_location("render_artifacts", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_existing_mihomo_module():
    spec = importlib.util.spec_from_file_location("render_mihomo_from_existing_profile", MIHOMO_EXISTING_RENDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {MIHOMO_EXISTING_RENDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_fixture(tmp_path: Path) -> Path:
    repo_root = tmp_path / "proxy_ops_private"
    shutil.copytree(REPO_ROOT / "inventory", repo_root / "inventory")
    secrets_dir = repo_root / "secrets" / "nodes"
    secrets_dir.mkdir(parents=True)
    for index, name in enumerate(FIXTURE_NODE_NAMES, start=1):
        (secrets_dir / f"{name}.env").write_text(
            "\n".join(
                [
                    f"VLESS_UUID=00000000-0000-4000-8000-{index:012d}",
                    f"REALITY_PUBLIC_KEY=test-public-key-{index}",
                    f"REALITY_SHORT_ID=testshort{index}",
                    "REALITY_SERVER_NAMES=www.cloudflare.com",
                    "",
                ]
            ),
            encoding="utf-8",
        )
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
                    for name in FIXTURE_HEALTHY_NODE_NAMES
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
            mihomo.index("DOMAIN-SUFFIX,openai.com,PROXY"),
        )
        self.assertEqual(
            "https://subs.sea.prod.gglohh.top/subscriptions/singbox-client-profile.json",
            singbox["url"],
        )
        self.assertIn(
            "https%3A%2F%2Fsubs.sea.prod.gglohh.top%2Fsubscriptions%2Fsingbox-client-profile.json",
            singbox["deeplink"],
        )

    def test_mihomo_routes_china_app_company_domains_direct_before_proxy_rules(self) -> None:
        render_artifacts = load_module()
        expected_keyword_rules = [
            "DOMAIN-KEYWORD,alibaba,DIRECT",
            "DOMAIN-KEYWORD,alicdn,DIRECT",
            "DOMAIN-KEYWORD,aliyun,DIRECT",
            "DOMAIN-KEYWORD,aliyuncs,DIRECT",
            "DOMAIN-KEYWORD,alipay,DIRECT",
            "DOMAIN-KEYWORD,alipayobjects,DIRECT",
            "DOMAIN-KEYWORD,antgroup,DIRECT",
            "DOMAIN-KEYWORD,taobao,DIRECT",
            "DOMAIN-KEYWORD,tmall,DIRECT",
            "DOMAIN-KEYWORD,xianyu,DIRECT",
            "DOMAIN-KEYWORD,goofish,DIRECT",
            "DOMAIN-KEYWORD,1688,DIRECT",
            "DOMAIN-KEYWORD,alimama,DIRECT",
            "DOMAIN-KEYWORD,aliexpress,DIRECT",
            "DOMAIN-KEYWORD,qwen,DIRECT",
            "DOMAIN-KEYWORD,qianwen,DIRECT",
            "DOMAIN-KEYWORD,tongyi,DIRECT",
            "DOMAIN-KEYWORD,dashscope,DIRECT",
            "DOMAIN-KEYWORD,bytedance,DIRECT",
            "DOMAIN-KEYWORD,bytecdn,DIRECT",
            "DOMAIN-KEYWORD,byteimg,DIRECT",
            "DOMAIN-KEYWORD,doubao,DIRECT",
            "DOMAIN-KEYWORD,douyin,DIRECT",
            "DOMAIN-KEYWORD,toutiao,DIRECT",
            "DOMAIN-KEYWORD,snssdk,DIRECT",
            "DOMAIN-KEYWORD,volcengine,DIRECT",
            "DOMAIN-KEYWORD,volces,DIRECT",
            "DOMAIN-KEYWORD,zijieapi,DIRECT",
            "DOMAIN-KEYWORD,pstatp,DIRECT",
            "DOMAIN-KEYWORD,amemv,DIRECT",
            "DOMAIN-KEYWORD,iesdouyin,DIRECT",
            "DOMAIN-KEYWORD,oceanengine,DIRECT",
            "DOMAIN-KEYWORD,feishu,DIRECT",
            "DOMAIN-KEYWORD,larksuite,DIRECT",
            "DOMAIN-KEYWORD,tiktok,DIRECT",
            "DOMAIN-KEYWORD,capcut,DIRECT",
            "DOMAIN-KEYWORD,jianying,DIRECT",
            "DOMAIN-KEYWORD,xiaomi,DIRECT",
            "DOMAIN-KEYWORD,miui,DIRECT",
            "DOMAIN-KEYWORD,mijia,DIRECT",
            "DOMAIN-KEYWORD,duokan,DIRECT",
            "DOMAIN-KEYWORD,mipay,DIRECT",
            "DOMAIN-KEYWORD,mi-img,DIRECT",
            "DOMAIN-KEYWORD,mimo,DIRECT",
        ]
        expected_suffix_rules = [
            "DOMAIN-SUFFIX,mi.com,DIRECT",
            "DOMAIN-SUFFIX,xiaomi.com,DIRECT",
            "DOMAIN-SUFFIX,miui.com,DIRECT",
            "DOMAIN-SUFFIX,mijia.tech,DIRECT",
            "DOMAIN-SUFFIX,duokan.com,DIRECT",
            "DOMAIN-SUFFIX,mipay.com,DIRECT",
        ]

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            mihomo = render_artifacts.render_mihomo_config(repo_root, platform="universal")

        rules = yaml.safe_load(mihomo)["rules"]
        for rule in [*expected_keyword_rules, *expected_suffix_rules]:
            self.assertIn(rule, rules)

        self.assertNotIn("DOMAIN-KEYWORD,mi,DIRECT", rules)
        expected_keywords = {item.split(",", 2)[1] for item in expected_keyword_rules}
        for rule in rules:
            if rule.startswith("DOMAIN-KEYWORD,"):
                payload = rule.split(",", 2)[1]
                if payload in expected_keywords:
                    self.assertTrue(rule.endswith(",DIRECT"), msg=rule)

        china_direct_indices = [rules.index(rule) for rule in [*expected_keyword_rules, *expected_suffix_rules]]
        self.assertLess(max(china_direct_indices), rules.index("DOMAIN-SUFFIX,openai.com,PROXY"))
        self.assertLess(
            max(china_direct_indices),
            rules.index(r"PROCESS-PATH-WILDCARD,C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\chrome_proxy.exe,PROXY"),
        )
        self.assertLess(max(china_direct_indices), rules.index("RULE-SET,proxy,PROXY"))
        self.assertLess(max(china_direct_indices), rules.index("MATCH,PROXY"))

    def test_existing_profile_mihomo_renderer_preserves_proxy_material(self) -> None:
        render_mihomo = load_existing_mihomo_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = copy_fixture(Path(tmp))
            render_mihomo.REPO_ROOT = repo_root
            render_mihomo.RENDER_ARTIFACTS_PATH = MODULE_PATH
            render_mihomo.PROFILE_PATH = repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml"
            render_mihomo.MANIFEST_PATH = repo_root / "generated" / "publish" / "sea-bgp" / "subscription-publish-manifest.json"
            render_mihomo.PROFILE_PATH.parent.mkdir(parents=True)
            render_mihomo.PROFILE_PATH.write_text(
                yaml.safe_dump(
                    {
                        "proxies": [{"name": "Existing", "uuid": "keep-this-uuid"}],
                        "proxy-groups": [{"name": "PROXY", "proxies": ["Existing", "DIRECT"]}],
                        "rules": ["MATCH,PROXY"],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            container_config_path = repo_root / "generated" / "publish" / "sea-bgp" / "gg-proxy-subscriptions.container"
            container_config_path.parent.mkdir(parents=True)
            container_config_path.write_text("ContainerName=gg-proxy-subscriptions\n", encoding="utf-8")
            unchanged_profile_path = repo_root / "generated" / "subscriptions" / "singbox-client-profile.json"
            unchanged_profile_path.write_text('{"name":"keep"}\n', encoding="utf-8")
            render_mihomo.MANIFEST_PATH.write_text(
                json.dumps(
                    {
                        "schema": "gg.proxy.subscription.publish.v1",
                        "published_nodes": ["GG-US-SEA-BGP-01"],
                        "container_config": {
                            "path": "generated/publish/sea-bgp/gg-proxy-subscriptions.container",
                            "sha256": "stale-container",
                        },
                        "generated_files": [
                            {
                                "path": "generated/subscriptions/mihomo-universal.yaml",
                                "sha256": "stale-mihomo",
                                "bytes": 1,
                            },
                            {
                                "path": "generated/subscriptions/singbox-client-profile.json",
                                "sha256": "stale-singbox",
                                "bytes": 1,
                            },
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            render_mihomo.main()
            rendered = yaml.safe_load(render_mihomo.PROFILE_PATH.read_text(encoding="utf-8"))
            manifest = json.loads(render_mihomo.MANIFEST_PATH.read_text(encoding="utf-8"))
            mihomo_bytes = render_mihomo.PROFILE_PATH.read_bytes()
            singbox_bytes = unchanged_profile_path.read_bytes()
            container_bytes = container_config_path.read_bytes()

        self.assertEqual([{"name": "Existing", "uuid": "keep-this-uuid"}], rendered["proxies"])
        self.assertEqual([{"name": "PROXY", "proxies": ["Existing", "DIRECT"]}], rendered["proxy-groups"])
        self.assertIn("DOMAIN-KEYWORD,alibaba,DIRECT", rendered["rules"])
        self.assertLess(
            rendered["rules"].index("DOMAIN-KEYWORD,alibaba,DIRECT"),
            rendered["rules"].index("DOMAIN-SUFFIX,openai.com,PROXY"),
        )
        manifest_files = {item["path"]: item for item in manifest["generated_files"]}
        self.assertEqual(hashlib.sha256(mihomo_bytes).hexdigest(), manifest_files["generated/subscriptions/mihomo-universal.yaml"]["sha256"])
        self.assertEqual(len(mihomo_bytes), manifest_files["generated/subscriptions/mihomo-universal.yaml"]["bytes"])
        self.assertEqual(
            hashlib.sha256(singbox_bytes).hexdigest(),
            manifest_files["generated/subscriptions/singbox-client-profile.json"]["sha256"],
        )
        self.assertEqual(len(singbox_bytes), manifest_files["generated/subscriptions/singbox-client-profile.json"]["bytes"])
        self.assertEqual(hashlib.sha256(container_bytes).hexdigest(), manifest["container_config"]["sha256"])
        self.assertEqual(["GG-US-SEA-BGP-01"], manifest["published_nodes"])


if __name__ == "__main__":
    unittest.main()
