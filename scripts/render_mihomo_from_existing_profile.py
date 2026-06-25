from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDER_ARTIFACTS_PATH = REPO_ROOT / "scripts" / "render_artifacts.py"
PROFILE_PATH = REPO_ROOT / "generated" / "subscriptions" / "mihomo-universal.yaml"
MANIFEST_PATH = REPO_ROOT / "generated" / "publish" / "sea-bgp" / "subscription-publish-manifest.json"


def load_render_artifacts():
    spec = importlib.util.spec_from_file_location("render_artifacts", RENDER_ARTIFACTS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {RENDER_ARTIFACTS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def update_manifest_hashes() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    container_config = manifest.get("container_config") or {}
    container_path = REPO_ROOT / container_config.get("path", "")
    if container_path.is_file():
        container_config["sha256"] = hashlib.sha256(container_path.read_bytes()).hexdigest()

    for item in manifest.get("generated_files") or []:
        path = REPO_ROOT / item.get("path", "")
        if path.is_file():
            data = path.read_bytes()
            item["sha256"] = hashlib.sha256(data).hexdigest()
            item["bytes"] = len(data)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    render_artifacts = load_render_artifacts()
    existing = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    if not isinstance(existing, dict):
        raise SystemExit(f"{PROFILE_PATH} must contain a mapping")

    platform = "universal"
    subscription_host = render_artifacts.public_subscriptions_host(REPO_ROOT)
    existing["tun"] = render_artifacts.mihomo_tun_config(REPO_ROOT)
    existing["dns"] = render_artifacts.mihomo_dns_config()
    existing["rule-providers"] = {
        "privateip": render_artifacts.mihomo_rule_provider("privateip", "ipcidr"),
        "cn": render_artifacts.mihomo_rule_provider("cn", "domain"),
        "cnip": render_artifacts.mihomo_rule_provider("cnip", "ipcidr"),
        "apple-cn": render_artifacts.mihomo_rule_provider("apple-cn", "domain"),
        "microsoft-cn": render_artifacts.mihomo_rule_provider("microsoft-cn", "domain"),
        "google-cn": render_artifacts.mihomo_rule_provider("google-cn", "domain"),
        "ads": render_artifacts.mihomo_rule_provider("ads", "domain"),
        "proxy": render_artifacts.mihomo_rule_provider("proxy", "domain"),
        "gfw": render_artifacts.mihomo_rule_provider("gfw", "domain"),
        "tld-proxy": render_artifacts.mihomo_rule_provider("tld-proxy", "domain"),
        "telegramip": render_artifacts.mihomo_rule_provider("telegramip", "ipcidr"),
    }
    existing["rules"] = [
        *render_artifacts.mihomo_cursor_domain_direct_rules(),
        *render_artifacts.mihomo_proxy_node_direct_rules(REPO_ROOT),
        *render_artifacts.mihomo_pre_domain_direct_process_rules(platform),
        *render_artifacts.mihomo_china_app_company_domain_direct_rules(),
        *render_artifacts.mihomo_openai_domain_proxy_rules(),
        *render_artifacts.mihomo_wps_domain_direct_rules(),
        *render_artifacts.mihomo_direct_process_rules(platform),
        *render_artifacts.mihomo_proxy_process_rules(platform),
        f"DOMAIN,{subscription_host},DIRECT",
        f"DOMAIN-SUFFIX,{subscription_host},DIRECT",
        "RULE-SET,privateip,DIRECT,no-resolve",
        "RULE-SET,ads,REJECT",
        "RULE-SET,apple-cn,DIRECT",
        "RULE-SET,microsoft-cn,DIRECT",
        "RULE-SET,google-cn,DIRECT",
        "RULE-SET,cn,DIRECT",
        "RULE-SET,cnip,DIRECT,no-resolve",
        "RULE-SET,telegramip,PROXY,no-resolve",
        "RULE-SET,proxy,PROXY",
        "RULE-SET,gfw,PROXY",
        "RULE-SET,tld-proxy,PROXY",
        "MATCH,PROXY",
    ]

    rendered = yaml.safe_dump(existing, sort_keys=False, allow_unicode=True)
    PROFILE_PATH.write_text(render_artifacts.annotate_mihomo_rules_yaml(rendered), encoding="utf-8")
    update_manifest_hashes()


if __name__ == "__main__":
    try:
        main()
    except KeyError as exc:
        raise SystemExit(f"missing required generated profile field: {exc}") from exc
