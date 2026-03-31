from __future__ import annotations

import json
import urllib.parse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FAILOVER_PRIORITY = ["lisahost", "akilecloud", "dedirock"]


def load_json_yaml(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def load_nodes_inventory(path: Path | None = None) -> dict:
    return load_json_yaml(path or REPO_ROOT / "inventory" / "nodes.yaml")


def load_subscriptions_config(path: Path | None = None) -> dict:
    return load_json_yaml(path or REPO_ROOT / "inventory" / "subscriptions.yaml")


def load_node_secrets(repo_root: Path, node_name: str) -> dict[str, str]:
    return load_env_file(repo_root / "secrets" / "nodes" / f"{node_name}.env")


def build_node_models(repo_root: Path) -> list[dict]:
    inventory = load_nodes_inventory(repo_root / "inventory" / "nodes.yaml")
    nodes: list[dict] = []
    for node in inventory["nodes"]:
        merged = dict(node)
        merged["secrets"] = load_node_secrets(repo_root, node["name"])
        nodes.append(merged)
    return nodes


def first_server_name(node: dict) -> str:
    names = node["secrets"]["REALITY_SERVER_NAMES"].split(",")
    return names[0].strip()


def vless_link(node: dict) -> str:
    host = node["host"]
    port = int(node["base_port"]) + 3
    secrets = node["secrets"]
    alias = urllib.parse.quote(node["subscription_alias"])
    sni = first_server_name(node)
    return (
        f"vless://{secrets['VLESS_UUID']}@{host}:{port}"
        f"?security=reality&encryption=none"
        f"&pbk={secrets['REALITY_PUBLIC_KEY']}"
        f"&fp=chrome&type=tcp&flow=xtls-rprx-vision"
        f"&sni={urllib.parse.quote(sni)}"
        f"&sid={secrets['REALITY_SHORT_ID']}#{alias}"
    )


def render_v2ray_subscription(repo_root: Path = REPO_ROOT) -> str:
    nodes = [node for node in build_node_models(repo_root) if node.get("enabled")]
    return "\n".join(vless_link(node) for node in nodes) + "\n"


def render_hiddify_import(repo_root: Path = REPO_ROOT) -> str:
    subscriptions = load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    subscription_url = subscriptions["subscription_base_url"].rstrip("/") + "/v2ray_nodes.txt"
    profile_name = subscriptions["hiddify_fragment_name"]
    return f"hiddify://import/{subscription_url}#{urllib.parse.quote(profile_name)}\n"


def render_singbox_remote_profile(repo_root: Path = REPO_ROOT) -> str:
    subscriptions = load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    remote_url = subscriptions["subscription_base_url"].rstrip("/") + "/singbox-client-profile.json"
    profile_name = subscriptions["remote_profile_name"]
    deeplink = (
        "sing-box://import-remote-profile?url="
        + urllib.parse.quote(remote_url, safe="")
        + "#"
        + urllib.parse.quote(profile_name)
    )
    manifest = {
        "name": profile_name,
        "url": remote_url,
        "update_interval_hours": subscriptions["update_interval_hours"],
        "deeplink": deeplink,
    }
    return json.dumps(manifest, indent=2) + "\n"


def proxy_outbound_for_node(node: dict) -> dict:
    secrets = node["secrets"]
    return {
        "type": "vless",
        "tag": f"proxy_{node['name']}",
        "server": node["host"],
        "server_port": int(node["base_port"]) + 3,
        "uuid": secrets["VLESS_UUID"],
        "flow": "xtls-rprx-vision",
        "packet_encoding": "xudp",
        "tls": {
            "enabled": True,
            "server_name": first_server_name(node),
            "utls": {
                "enabled": True,
                "fingerprint": "chrome",
            },
            "reality": {
                "enabled": True,
                "public_key": secrets["REALITY_PUBLIC_KEY"],
                "short_id": secrets["REALITY_SHORT_ID"],
            },
        },
    }


def render_infra_core_config(repo_root: Path = REPO_ROOT) -> str:
    template = load_json_yaml(repo_root / "templates" / "infra_core_current_config.json")
    node_by_name = {
        node["name"]: node
        for node in build_node_models(repo_root)
        if node.get("enabled") and node.get("infra_core_candidate")
    }
    ordered_nodes = [node_by_name[name] for name in FAILOVER_PRIORITY if name in node_by_name]
    proxy_tags = [f"proxy_{node['name']}" for node in ordered_nodes]

    template["outbounds"] = [
        *[proxy_outbound_for_node(node) for node in ordered_nodes],
        {
            "type": "selector",
            "tag": "proxy_failover",
            "outbounds": proxy_tags,
            "default": proxy_tags[0] if proxy_tags else "",
            "interrupt_exist_connections": True,
        },
        {
            "type": "direct",
            "tag": "direct",
        },
    ]

    for server in template["dns"]["servers"]:
        if server.get("detour") == "proxy":
            server["detour"] = "proxy_failover"

    route_rules = template["route"]["rules"]
    for rule in route_rules:
        if rule.get("outbound") == "proxy":
            rule["outbound"] = "proxy_failover"
        if "ip_cidr" in rule and rule.get("outbound") == "direct":
            rule["ip_cidr"] = [f"{node['host']}/32" for node in ordered_nodes]

    return json.dumps(template, indent=2) + "\n"


def render_infra_core_failover_policy(repo_root: Path = REPO_ROOT) -> str:
    node_by_name = {
        node["name"]: node
        for node in build_node_models(repo_root)
        if node.get("enabled") and node.get("infra_core_candidate")
    }
    ordered_nodes = [node_by_name[name] for name in FAILOVER_PRIORITY if name in node_by_name]
    policy = {
        "selector_tag": "proxy_failover",
        "default_tag": "proxy_lisahost",
        "probe_url": "http://www.gstatic.com/generate_204",
        "probe_timeout_seconds": 8,
        "priority": [],
    }
    for node in ordered_nodes:
        policy["priority"].append(
            {
                "tag": f"proxy_{node['name']}",
                "name": node["name"],
                "host": node["host"],
                "http_port": int(node["base_port"]) + 1,
                "proxy_user": node["secrets"]["PROXY_USER"],
                "proxy_pass": node["secrets"]["PROXY_PASS"],
            }
        )
    return json.dumps(policy, indent=2) + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_generated_artifacts(repo_root: Path = REPO_ROOT) -> None:
    write_text(repo_root / "generated" / "subscriptions" / "v2ray_nodes.txt", render_v2ray_subscription(repo_root))
    write_text(repo_root / "generated" / "subscriptions" / "hiddify_import.txt", render_hiddify_import(repo_root))
    singbox_manifest = render_singbox_remote_profile(repo_root)
    write_text(repo_root / "generated" / "subscriptions" / "singbox-client-profile.json", singbox_manifest)
    write_text(repo_root / "generated" / "subscriptions" / "singbox_remote_profile.json", render_singbox_remote_profile(repo_root))
    write_text(repo_root / "generated" / "infra-core" / "vless-sidecar" / "config.json", render_infra_core_config(repo_root))
    write_text(
        repo_root / "generated" / "infra-core" / "vless-sidecar" / "failover_policy.json",
        render_infra_core_failover_policy(repo_root),
    )


def main() -> None:
    write_generated_artifacts(REPO_ROOT)


if __name__ == "__main__":
    main()
