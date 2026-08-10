from __future__ import annotations

import html
import hashlib
import ipaddress
import json
import os
import sys
import urllib.parse
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from subscription_node_availability import (
    ensure_minimum_published_nodes,
    exclusion_report,
    refresh_availability,
    registry_subscription_nodes,
    subscription_publishable_nodes,
)
PUBLIC_SUBSCRIPTIONS_HOST = "proxy-subscriptions.svc.prod.lab.gglohh.top"
SUBSCRIPTION_CONTAINER_NAME = "gg-proxy-subscriptions"
SUBSCRIPTION_CONTAINER_IMAGE = "docker.io/library/busybox:1.37"
SUBSCRIPTION_CONTAINER_COMMAND = "httpd -f -p 80 -h /www"
SUBSCRIPTION_CONTAINER_PORT = 80
SUBSCRIPTION_TRAEFIK_CERT_RESOLVER = "cf-staging"

DUSTINWIN_MIHOMO_RULESET_BASE_URL = (
    "https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset"
)

CURSOR_DIRECT_DOMAIN_SUFFIXES = [
    "cursor.sh",
    "cursor.com",
    "cursorapi.com",
    "cursor-cdn.com",
    "anysphere.co",
    "anysphere.inc",
]

CURSOR_DIRECT_DOMAIN_KEYWORDS = [
    "cursor",
]

WPS_DIRECT_DOMAIN_SUFFIXES = [
    "kingsoft.com",
    "kingsoft-office-service.com",
    "wps.cn",
    "wpscdn.cn",
    "wpscdn.com",
    "kdocs.cn",
    "kdocs.com",
    "ksosoft.com",
    "ksord.com",
    "wpsplus.com",
]

WPS_DIRECT_DOMAIN_KEYWORDS = [
    "kingsoft",
]

# Domestic platform and self-hosted services must bypass fake-ip and stay DIRECT.
# SSH/Git workflows to these hosts break when mihomo returns fake-ip addresses.
DOMESTIC_PLATFORM_DIRECT_DOMAIN_SUFFIXES = [
    "gglohh.top",
    "ringzle.com",
]

# Domestic APT and container registry mirrors must bypass fake-ip and stay DIRECT.
# WSL apt/podman workflows depend on these resolving to real addresses.
MIRROR_DIRECT_DOMAIN_SUFFIXES = [
    "mirrors.tuna.tsinghua.edu.cn",
    "deb.debian.org",
    "security.debian.org",
    "ftp.debian.org",
    "mirrors.aliyun.com",
    "mirrors.ustc.edu.cn",
    "mirrors.huaweicloud.com",
    "mirrors.cloud.tencent.com",
    "mirror.nju.edu.cn",
    "mirrors.163.com",
    "docker.m.daocloud.io",
    "daocloud.io",
]

OPENAI_PROXY_DOMAIN_SUFFIXES = [
    "openai.com",
    "chatgpt.com",
    "oaistatic.com",
    "oaiusercontent.com",
    "oaistatsig.com",
    "auth.openai.com",
    "auth0.openai.com",
    "cdn.openaimerge.com",
]

PRE_DOMAIN_DIRECT_PROCESS_PATHS_BY_PLATFORM = {
    "windows": [],
    "macos": [],
    "linux": [],
}

# Browsers (and browser-like fingerprint surfaces) go through ChatGPT so
# HTTP + WebRTC/STUN share the same QQPW residential exit.
CHATGPT_PROCESS_NAMES_BY_PLATFORM = {
    "windows": [
        "chrome.exe",
        "msedge.exe",
        "firefox.exe",
        "brave.exe",
        "opera.exe",
        "vivaldi.exe",
        "chromium.exe",
        "ChatGPT.exe",
        "ChatGPT Atlas.exe",
        "ChatGPTAtlas.exe",
    ],
    "macos": [
        "Google Chrome",
        "Google Chrome Helper",
        "Chromium",
        "Microsoft Edge",
        "Microsoft Edge Helper",
        "Firefox",
        "Brave Browser",
        "Opera",
        "Vivaldi",
        "Safari",
        "ChatGPT",
        "ChatGPT Helper",
        "ChatGPT Atlas",
        "ChatGPT Atlas Helper",
        "ChatGPTAtlas",
        "ChatGPTAtlas Helper",
    ],
    "linux": [
        "google-chrome",
        "chrome",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "msedge",
        "firefox",
        "brave",
        "brave-browser",
        "opera",
        "vivaldi",
        "chatgpt",
        "chatgpt-atlas",
        "chatgptatlas",
    ],
}

CHATGPT_PROCESS_PATHS_BY_PLATFORM = {
    "windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\*\AppData\Local\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Users\*\AppData\Local\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge Beta\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge Beta\Application\msedge.exe",
        r"C:\Users\*\AppData\Local\Microsoft\Edge Beta\Application\msedge.exe",
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        r"C:\Users\*\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\chrome_proxy.exe",
        r"C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\simprint.exe",
        r"C:\Program Files\OpenAI\ChatGPT\*",
        r"C:\Users\*\AppData\Local\Programs\ChatGPT\*",
        r"C:\Program Files\OpenAI\ChatGPT Atlas\*",
        r"C:\Users\*\AppData\Local\Programs\ChatGPT Atlas\*",
    ],
    "macos": [
        "/Applications/Google Chrome.app/Contents/*",
        "/Applications/Chromium.app/Contents/*",
        "/Applications/Microsoft Edge.app/Contents/*",
        "/Applications/Firefox.app/Contents/*",
        "/Applications/Brave Browser.app/Contents/*",
        "/Applications/Opera.app/Contents/*",
        "/Applications/Vivaldi.app/Contents/*",
        "/Applications/Safari.app/Contents/*",
        "/System/Applications/Safari.app/Contents/*",
        "/Users/*/Applications/Google Chrome.app/Contents/*",
        "/Users/*/Applications/Microsoft Edge.app/Contents/*",
        "/Applications/ChatGPT.app/Contents/*",
        "/Applications/ChatGPT Atlas.app/Contents/*",
        "/Users/*/Applications/ChatGPT.app/Contents/*",
        "/Users/*/Applications/ChatGPT Atlas.app/Contents/*",
    ],
    "linux": [
        "/opt/google/chrome/*",
        "/usr/bin/google-chrome*",
        "/usr/bin/chromium*",
        "/opt/microsoft/msedge/*",
        "/usr/bin/microsoft-edge*",
        "/usr/bin/firefox*",
        "/opt/brave.com/brave/*",
        "/usr/bin/brave*",
        "/opt/chatgpt/*",
        "/usr/bin/chatgpt*",
        "/opt/chatgpt-atlas/*",
        "/usr/bin/chatgpt-atlas*",
        "/usr/bin/chatgptatlas*",
    ],
}

DIRECT_PROCESS_NAMES_BY_PLATFORM = {
    "windows": [
        "ssh.exe",
        "git.exe",
        "QQ.exe",
        "QQProtect.exe",
        "TIM.exe",
        "Cursor.exe",
        "cursor.exe",
        "cursor-agent.exe",
        "WeChat.exe",
        "WeChatAppEx.exe",
        "WeChatBrowser.exe",
        "WeChatOCR.exe",
        "Weixin.exe",
        "WXWork.exe",
        "wps.exe",
        "wpp.exe",
        "et.exe",
        "wpspdf.exe",
        "wpscloudsvr.exe",
        "ksolaunch.exe",
        "wpsupdate.exe",
        "ksomisc.exe",
    ],
    "macos": [
        "ssh",
        "git",
        "QQ",
        "Cursor",
        "Cursor Helper",
        "Cursor Helper (GPU)",
        "Cursor Helper (Plugin)",
        "Cursor Helper (Renderer)",
        "cursor-agent",
        "WeChat",
        "Weixin",
        "WXWork",
    ],
    "linux": [
        "ssh",
        "git",
        "qq",
        "cursor",
        "cursor-agent",
        "wechat",
        "weixin",
        "wxwork",
    ],
}

PROCESS_NAMES_BY_PLATFORM = {
    "windows": [
        "Antigravity.exe",
        "Antigravity IDE.exe",
        "antigravity.exe",
        "antigravity-cli.exe",
        "agy.exe",
        "ChatGPT.exe",
        "ChatGPT Atlas.exe",
        "ChatGPTAtlas.exe",
        "Codex.exe",
        "codex.exe",
    ],
    "macos": [
        "Antigravity",
        "Antigravity Helper",
        "Antigravity Helper (GPU)",
        "Antigravity Helper (Plugin)",
        "Antigravity Helper (Renderer)",
        "antigravity",
        "antigravity-cli",
        "agy",
        "ChatGPT",
        "ChatGPT Helper",
        "ChatGPT Atlas",
        "ChatGPT Atlas Helper",
        "ChatGPTAtlas",
        "ChatGPTAtlas Helper",
        "Codex",
        "codex",
    ],
    "linux": [
        "antigravity",
        "antigravity-ide",
        "antigravity-cli",
        "agy",
        "chatgpt",
        "chatgpt-atlas",
        "chatgptatlas",
        "codex",
    ],
}

DIRECT_PROCESS_PATHS_BY_PLATFORM = {
    "windows": [
        r"C:\Users\*\AppData\Local\Programs\Cursor\*",
        r"C:\Users\*\AppData\Local\Kingsoft\WPS Office\*",
        r"C:\Users\*\AppData\Local\OpenAI\Codex\bin\*\codex.exe",
        r"C:\Program Files\WindowsApps\OpenAI.Codex_*\app\*",
    ],
    "macos": [
        "/Applications/Cursor.app/Contents/*",
        "/Applications/Codex.app/Contents/*",
        "/Users/*/Applications/Codex.app/Contents/*",
    ],
    "linux": [
        "/usr/bin/cursor*",
        "/opt/codex/*",
        "/usr/bin/codex",
    ],
}

PROCESS_PATHS_BY_PLATFORM = {
    "windows": [
        r"C:\Program Files\Google\Antigravity\*",
        r"C:\Program Files\Google\Antigravity*\*",
        r"C:\Users\*\AppData\Local\Programs\Antigravity\*",
        r"C:\Users\*\AppData\Local\OpenAI\Codex\bin\*\codex.exe",
        r"C:\Program Files\WindowsApps\OpenAI.Codex_*\app\*",
        r"C:\Users\*\Simprint\webview-fixed\*\msedgewebview2.exe",
        r"C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\chrome_proxy.exe",
        r"C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\simprint.exe",
        r"C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\*\*",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Users\*\AppData\Local\Microsoft\Edge\Application\msedge.exe",
    ],
    "macos": [
        "/Applications/Antigravity.app/Contents/*",
        "/Applications/ChatGPT.app/Contents/*",
        "/Applications/ChatGPT Atlas.app/Contents/*",
        "/Applications/Codex.app/Contents/*",
        "/Applications/Microsoft Edge.app/Contents/*",
    ],
    "linux": [
        "/opt/Antigravity/*",
        "/opt/antigravity/*",
        "/usr/bin/antigravity*",
        "/usr/bin/codex",
        "/opt/microsoft/msedge/*",
    ],
}

PROXY_PROCESS_PATHS_BY_PLATFORM = {
    "windows": [
        r"C:\Program Files\Google\Antigravity\*",
        r"C:\Program Files\Google\Antigravity*\*",
        r"C:\Users\*\AppData\Local\Programs\Antigravity\*",
    ],
    "macos": [
        "/Applications/Antigravity.app/Contents/*",
        "/Users/*/Applications/Antigravity.app/Contents/*",
    ],
    "linux": [
        "/opt/Antigravity/*",
        "/opt/antigravity/*",
        "/usr/bin/antigravity*",
    ],
}

MIHOMO_CONFIG_PLATFORMS = ("windows", "macos", "linux")


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
    subscriptions = load_json_yaml(path or REPO_ROOT / "inventory" / "subscriptions.yaml")
    public_base_url = os.environ.get("PUBLIC_BASE_URL")
    if public_base_url:
        subscriptions["subscription_base_url"] = public_base_url
    return subscriptions


def public_subscriptions_host(repo_root: Path = REPO_ROOT) -> str:
    subscriptions = load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    host = urllib.parse.urlparse(subscriptions["subscription_base_url"]).hostname
    return host or PUBLIC_SUBSCRIPTIONS_HOST


def publish_config(repo_root: Path = REPO_ROOT) -> dict:
    return dict(load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml").get("publish") or {})


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


def ordered_enabled_nodes(repo_root: Path, *, infra_core_only: bool = False) -> list[dict]:
    subscriptions = load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    configured_priority = subscriptions.get("failover_priority", [])
    if not isinstance(configured_priority, list):
        raise ValueError("failover_priority must be a list of node names")

    node_by_name = {
        node["name"]: node
        for node in build_node_models(repo_root)
        if node.get("enabled") and (node.get("infra_core_candidate") or not infra_core_only)
    }
    ordered_nodes: list[dict] = []
    seen: set[str] = set()
    for raw_name in configured_priority:
        node_name = str(raw_name)
        if node_name not in node_by_name:
            raise ValueError(f"failover_priority references unknown enabled node: {node_name}")
        ordered_nodes.append(node_by_name[node_name])
        seen.add(node_name)

    for node in node_by_name.values():
        if node["name"] not in seen:
            ordered_nodes.append(node)
    return ordered_nodes


def enabled_nodes(repo_root: Path) -> list[dict]:
    return ordered_enabled_nodes(repo_root)


def enabled_node_by_name(repo_root: Path, node_name: str) -> dict:
    for node in enabled_nodes(repo_root):
        if node["name"] == node_name:
            return node
    raise KeyError(f"Unknown enabled node: {node_name}")


def first_server_name(node: dict) -> str:
    names = str(node.get("reality_server_names") or node["secrets"]["REALITY_SERVER_NAMES"]).split(",")
    return names[0].strip()


def node_public_host(node: dict) -> str:
    return str(node["host"])


def node_egress_profiles(node: dict) -> dict:
    profiles = node.get("egress_profiles") or {}
    return dict(profiles) if isinstance(profiles, dict) else {}


def node_has_dual_egress(node: dict) -> bool:
    profiles = node_egress_profiles(node)
    return "public" in profiles and "wireguard_nat" in profiles


def public_vless_port(node: dict) -> int:
    profiles = node_egress_profiles(node)
    public = profiles.get("public") or {}
    protocols = public.get("protocols") or {}
    vless = protocols.get("vless") or {}
    offset = int(vless.get("port_offset", 3)) if isinstance(vless, dict) else 3
    return int(node["base_port"]) + offset


def wireguard_nat_profile(node: dict) -> dict:
    return dict(node_egress_profiles(node).get("wireguard_nat") or {})


def qqpw_vless_port(node: dict) -> int:
    protocols = (wireguard_nat_profile(node).get("protocols") or {})
    vless = protocols.get("vless") or {}
    offset = int(vless.get("port_offset", 6)) if isinstance(vless, dict) else 6
    return int(node["base_port"]) + offset


def qqpw_vless_uuid(node: dict) -> str:
    secrets = node["secrets"]
    return str(secrets.get("QQPW_VLESS_UUID") or secrets["VLESS_UUID"])


def qqpw_socks_port(node: dict) -> int:
    protocols = wireguard_nat_profile(node).get("protocols") or {}
    socks = protocols.get("socks") or {}
    offset = int(socks.get("port_offset", 7)) if isinstance(socks, dict) else 7
    return int(node["base_port"]) + offset


def socks5_link(node: dict, *, alias: str | None = None, port: int | None = None) -> str:
    secrets = node["secrets"]
    host = node_public_host(node)
    listen_port = qqpw_socks_port(node) if port is None else int(port)
    user = urllib.parse.quote(str(secrets.get("PROXY_USER") or "admin"), safe="")
    password = urllib.parse.quote(str(secrets["PROXY_PASS"]), safe="")
    alias_name = alias or "QQPW-Residential-SOCKS5"
    return f"socks5://{user}:{password}@{host}:{listen_port}#{urllib.parse.quote(alias_name)}"


def mihomo_proxy_socks5_for_qqpw(node: dict, *, alias: str | None = None) -> dict:
    secrets = node["secrets"]
    return {
        "name": alias or "QQPW-Residential-SOCKS5",
        "type": "socks5",
        "server": node_public_host(node),
        "port": qqpw_socks_port(node),
        "username": str(secrets.get("PROXY_USER") or "admin"),
        "password": secrets["PROXY_PASS"],
        "udp": True,
    }


def vless_link(
    node: dict,
    *,
    alias: str | None = None,
    port: int | None = None,
    uuid_value: str | None = None,
) -> str:
    host = node_public_host(node)
    listen_port = public_vless_port(node) if port is None else int(port)
    secrets = node["secrets"]
    uuid = uuid_value or secrets["VLESS_UUID"]
    alias_name = alias or str(node["subscription_alias"])
    alias_encoded = urllib.parse.quote(alias_name)
    sni = first_server_name(node)
    return (
        f"vless://{uuid}@{host}:{listen_port}"
        f"?security=reality&encryption=none"
        f"&pbk={secrets['REALITY_PUBLIC_KEY']}"
        f"&fp=chrome&type=tcp&flow=xtls-rprx-vision"
        f"&sni={urllib.parse.quote(sni)}"
        f"&sid={secrets['REALITY_SHORT_ID']}#{alias_encoded}"
    )


def node_hysteria2_enabled(node: dict) -> bool:
    hysteria2 = node.get("hysteria2") or {}
    return bool(hysteria2.get("enabled"))


def hysteria2_egress_profile(node: dict) -> str:
    hysteria2 = node.get("hysteria2") or {}
    return str(hysteria2.get("egress_profile") or "public")


def node_hysteria2_on_public_subscription(node: dict) -> bool:
    return node_hysteria2_enabled(node) and hysteria2_egress_profile(node) == "public"


def hysteria2_port(node: dict) -> int:
    profiles = wireguard_nat_profile(node)
    protocols = profiles.get("protocols") or {}
    hy2 = protocols.get("hysteria2") if isinstance(protocols, dict) else None
    if isinstance(hy2, dict) and hy2.get("port_offset") is not None:
        return int(node["base_port"]) + int(hy2["port_offset"])
    hysteria2 = node.get("hysteria2") or {}
    return int(node["base_port"]) + int(hysteria2.get("port_offset", 5))


def hysteria2_sni(node: dict) -> str:
    profiles = wireguard_nat_profile(node)
    protocols = profiles.get("protocols") or {}
    hy2 = protocols.get("hysteria2") if isinstance(protocols, dict) else None
    if isinstance(hy2, dict) and hy2.get("sni"):
        return str(hy2["sni"])
    hysteria2 = node.get("hysteria2") or {}
    return str(hysteria2.get("sni") or first_server_name(node))


def hysteria2_insecure(node: dict) -> bool:
    profiles = wireguard_nat_profile(node)
    protocols = profiles.get("protocols") or {}
    hy2 = protocols.get("hysteria2") if isinstance(protocols, dict) else None
    if isinstance(hy2, dict) and "insecure" in hy2:
        return bool(hy2["insecure"])
    hysteria2 = node.get("hysteria2") or {}
    return bool(hysteria2.get("insecure", True))


def hysteria2_alias(node: dict, *, alias: str | None = None) -> str:
    if alias:
        return alias
    hysteria2 = node.get("hysteria2") or {}
    suffix = str(hysteria2.get("alias_suffix", "-Hysteria2"))
    return f"{node['subscription_alias']}{suffix}"


def hysteria2_link(node: dict, *, alias: str | None = None) -> str:
    if not node_hysteria2_enabled(node):
        raise ValueError(f"node {node['name']} does not have hysteria2 enabled")
    secrets = node["secrets"]
    host = node_public_host(node)
    port = hysteria2_port(node)
    password = secrets["HYSTERIA2_PASSWORD"]
    sni = hysteria2_sni(node)
    name = urllib.parse.quote(hysteria2_alias(node, alias=alias))
    query = f"sni={urllib.parse.quote(sni)}"
    if hysteria2_insecure(node):
        query += "&insecure=1"
    query += "&alpn=h3"
    return f"hysteria2://{password}@{host}:{port}/?{query}#{name}"


def subscription_links_for_node(node: dict, *, aliases: dict[str, str] | None = None) -> list[str]:
    aliases = aliases or {}
    links = [vless_link(node, alias=aliases.get("vless"))]
    if node_hysteria2_on_public_subscription(node):
        links.append(hysteria2_link(node, alias=aliases.get("hysteria2")))
    return links


def extra_single_node_subscriptions(repo_root: Path = REPO_ROOT) -> list[dict]:
    subscriptions = load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    entries = subscriptions.get("extra_single_node_subscriptions", [])
    if not isinstance(entries, list):
        raise ValueError("extra_single_node_subscriptions must be a list")
    return [dict(entry) for entry in entries]


def extra_single_node_subscription_filename(filename: str) -> str:
    return f"v2ray_node_{filename}.txt"


def mihomo_proxy_hysteria2_for_node(node: dict, *, alias: str | None = None) -> dict:
    secrets = node["secrets"]
    return {
        "name": hysteria2_alias(node, alias=alias),
        "type": "hysteria2",
        "server": node_public_host(node),
        "port": hysteria2_port(node),
        "password": secrets["HYSTERIA2_PASSWORD"],
        "sni": hysteria2_sni(node),
        "skip-cert-verify": hysteria2_insecure(node),
        "alpn": ["h3"],
    }


def extra_single_node_entries_for_source(repo_root: Path, source_node_name: str) -> list[dict]:
    eligible_names = {str(node["name"]) for node in subscription_publishable_nodes(repo_root)}
    if source_node_name not in eligible_names:
        return []
    return [
        entry
        for entry in extra_single_node_subscriptions(repo_root)
        if str(entry.get("source_node")) == source_node_name
    ]


def subscription_links_for_wireguard_nat_entry(node: dict, entry: dict) -> list[str]:
    aliases = dict(entry.get("aliases") or {})
    # VLESS is the required client path; Hy2 is optional bonus only.
    links: list[str] = [
        vless_link(
            node,
            alias=aliases.get("vless") or "QQPW-Residential-Reality",
            port=qqpw_vless_port(node),
            uuid_value=qqpw_vless_uuid(node),
        ),
    ]
    if node_hysteria2_enabled(node):
        links.append(hysteria2_link(node, alias=aliases.get("hysteria2")))
    return links


def subscription_links_for_extra_entry(repo_root: Path, entry: dict) -> list[str]:
    source_node_name = str(entry["source_node"])
    eligible_names = {str(node["name"]) for node in subscription_publishable_nodes(repo_root)}
    if source_node_name not in eligible_names:
        return []
    node = enabled_node_by_name(repo_root, source_node_name)
    profile = str(entry.get("egress_profile") or "alias")
    if profile == "wireguard_nat":
        if not node_has_dual_egress(node):
            raise ValueError(
                f"extra subscription {entry.get('filename')} requires dual egress on {source_node_name}"
            )
        return subscription_links_for_wireguard_nat_entry(node, entry)
    aliases = dict(entry.get("aliases") or {})
    return subscription_links_for_node(node, aliases=aliases)


def mihomo_proxies_for_wireguard_nat_entry(node: dict, entry: dict) -> list[dict]:
    aliases = dict(entry.get("aliases") or {})
    # VLESS first so ChatGPT group defaults to QQPW Reality; Hy2 is bonus.
    proxies: list[dict] = [
        mihomo_proxy_for_node(
            node,
            alias=aliases.get("vless") or "QQPW-Residential-Reality",
            port=qqpw_vless_port(node),
            uuid_value=qqpw_vless_uuid(node),
        ),
    ]
    if node_hysteria2_enabled(node):
        proxies.append(mihomo_proxy_hysteria2_for_node(node, alias=aliases.get("hysteria2")))
    return proxies


def mihomo_proxies_for_extra_entry(repo_root: Path, entry: dict) -> list[dict]:
    source_node_name = str(entry["source_node"])
    eligible_names = {str(node["name"]) for node in subscription_publishable_nodes(repo_root)}
    if source_node_name not in eligible_names:
        return []
    node = enabled_node_by_name(repo_root, source_node_name)
    profile = str(entry.get("egress_profile") or "alias")
    if profile == "wireguard_nat":
        if not node_has_dual_egress(node):
            raise ValueError(
                f"extra subscription {entry.get('filename')} requires dual egress on {source_node_name}"
            )
        return mihomo_proxies_for_wireguard_nat_entry(node, entry)
    aliases = dict(entry.get("aliases") or {})
    proxies = [mihomo_proxy_for_node(node, alias=aliases.get("vless"))]
    if node_hysteria2_on_public_subscription(node):
        proxies.append(mihomo_proxy_hysteria2_for_node(node, alias=aliases.get("hysteria2")))
    return proxies


def mihomo_extra_proxies(repo_root: Path) -> list[dict]:
    proxies: list[dict] = []
    for entry in extra_single_node_subscriptions(repo_root):
        proxies.extend(mihomo_proxies_for_extra_entry(repo_root, entry))
    return proxies


def mihomo_extra_proxy_names(repo_root: Path) -> list[str]:
    return [str(proxy["name"]) for proxy in mihomo_extra_proxies(repo_root)]


def mihomo_proxies_for_nodes(nodes: list[dict], *, repo_root: Path | None = None) -> list[dict]:
    proxies: list[dict] = []
    for node in nodes:
        proxies.append(mihomo_proxy_for_node(node))
        if node_hysteria2_on_public_subscription(node):
            proxies.append(mihomo_proxy_hysteria2_for_node(node))
    if repo_root is not None:
        proxies.extend(mihomo_extra_proxies(repo_root))
    return proxies


def mihomo_proxy_names_for_nodes(nodes: list[dict], *, repo_root: Path | None = None) -> list[str]:
    names: list[str] = []
    for node in nodes:
        names.append(str(node["subscription_alias"]))
        if node_hysteria2_on_public_subscription(node):
            names.append(hysteria2_alias(node))
    if repo_root is not None:
        names.extend(mihomo_extra_proxy_names(repo_root))
    return names


def mihomo_proxy_for_node(
    node: dict,
    *,
    alias: str | None = None,
    port: int | None = None,
    uuid_value: str | None = None,
) -> dict:
    secrets = node["secrets"]
    return {
        "name": alias or str(node["subscription_alias"]),
        "type": "vless",
        "server": node_public_host(node),
        "port": public_vless_port(node) if port is None else int(port),
        "uuid": uuid_value or secrets["VLESS_UUID"],
        "network": "tcp",
        "tls": True,
        "udp": True,
        "flow": "xtls-rprx-vision",
        "servername": first_server_name(node),
        "client-fingerprint": "chrome",
        "reality-opts": {
            "public-key": secrets["REALITY_PUBLIC_KEY"],
            "short-id": secrets["REALITY_SHORT_ID"],
        },
    }


def mihomo_rule_provider(name: str, behavior: str) -> dict:
    return {
        "type": "http",
        "behavior": behavior,
        "format": "mrs",
        "url": f"{DUSTINWIN_MIHOMO_RULESET_BASE_URL}/{name}.mrs",
        "path": f"./ruleset/dustinwin/{name}.mrs",
        "interval": 86400,
        "proxy": "PROXY",
    }


def mihomo_dns_config() -> dict:
    domestic_resolvers = ["223.5.5.5", "119.29.29.29"]
    return {
        "enable": True,
        "listen": "0.0.0.0:1053",
        "ipv6": False,
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "fake-ip-filter": [
            "*.lan",
            "localhost.ptlogin2.qq.com",
            "dns.msftncsi.com",
            "www.msftncsi.com",
            "time.windows.com",
            "time.apple.com",
            "time.asia.apple.com",
            *mihomo_domestic_platform_fake_ip_filter_patterns(),
            *mihomo_mirror_fake_ip_filter_patterns(),
        ],
        "default-nameserver": domestic_resolvers,
        "nameserver": ["https://dns.alidns.com/dns-query", "https://doh.pub/dns-query"],
        "nameserver-policy": mihomo_domestic_dns_nameserver_policy(),
        "proxy-server-nameserver": ["https://dns.alidns.com/dns-query", "https://doh.pub/dns-query"],
        "fallback": ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"],
        "fallback-filter": {
            "geoip": False,
        },
    }


def proxy_node_route_exclude_addresses(repo_root: Path = REPO_ROOT) -> list[str]:
    addresses: list[str] = []
    seen: set[str] = set()
    for node in registry_subscription_nodes(repo_root):
        host = node_public_host(node).strip()
        try:
            ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError(f"proxy node TUN route exclusion requires an IP host for {node['name']}: {host}") from exc
        if not host or host in seen:
            continue
        addresses.append(f"{host}/32")
        seen.add(host)
    return addresses


def mihomo_tun_config(repo_root: Path = REPO_ROOT) -> dict:
    return {
        "enable": True,
        "stack": "mixed",
        "auto-route": True,
        "auto-redirect": True,
        "strict-route": True,
        "auto-detect-interface": True,
        "route-exclude-address": proxy_node_route_exclude_addresses(repo_root),
        "dns-hijack": ["any:53"],
    }


def mihomo_process_values(mapping: dict[str, list[str]], platform: str) -> list[str]:
    if platform == "universal":
        values: list[str] = []
        seen: set[str] = set()
        for platform_name in MIHOMO_CONFIG_PLATFORMS:
            for value in mapping[platform_name]:
                if value not in seen:
                    values.append(value)
                    seen.add(value)
        return values
    try:
        return mapping[platform]
    except KeyError as exc:
        raise ValueError(f"Unsupported mihomo platform: {platform}") from exc


def annotate_mihomo_rules_yaml(yaml_text: str) -> str:
    cursor_domain_help = """rules:
# === HIGHEST PRIORITY CURSOR DOMAIN DIRECT PROTECTIONS ===
# Cursor domains are fuzzy-matched with DOMAIN-KEYWORD,cursor before process
# rules. This makes Cursor destinations direct no matter which app opens them,
# including apps with process-level PROXY overrides.
# === END HIGHEST PRIORITY CURSOR DOMAIN DIRECT PROTECTIONS ===
"""
    openai_domain_help = """# === OFFICIAL OPENAI / CHATGPT DOMAIN ChatGPT GROUP RULES ===
# Only official OpenAI-family destination domains are forced through the
# ChatGPT group (default: QQPW residential VLESS Reality). Hy2 is optional.
# Do not add broad DOMAIN-KEYWORD,openai/codex/openaiapi rules; those would
# over-route OpenAI-compatible relay domains.
# === END OFFICIAL OPENAI / CHATGPT DOMAIN ChatGPT GROUP RULES ===
"""
    pre_domain_process_help = """# === HIGHEST PRIORITY PROCESS DIRECT EXCEPTIONS ===
# Reserved for rare process exceptions that must stay DIRECT even before
# OpenAI/ChatGPT domain and browser fingerprint ChatGPT-group rules.
# === END HIGHEST PRIORITY PROCESS DIRECT EXCEPTIONS ===
"""
    chatgpt_process_help = """# === BROWSER / FINGERPRINT ChatGPT PROCESS RULES ===
# Major browsers and ChatGPT desktop apps are forced through the ChatGPT
# group so HTTP + WebRTC/STUN share the same QQPW residential exit IP.
# This is what keeps global browser fingerprints aligned with ChatGPT.
# === END BROWSER / FINGERPRINT ChatGPT PROCESS RULES ===
"""
    wps_domain_help = """# === WPS / KINGSOFT DOMAIN DIRECT PROTECTIONS ===
# WPS Office and Kingsoft domains are matched before process rules so WPS
# embedded WebView or helper subprocess traffic stays DIRECT even when the
# process name is shared with other apps.
# === END WPS / KINGSOFT DOMAIN DIRECT PROTECTIONS ===
"""
    process_help = """# === USER-EDITABLE PROCESS DIRECT PROTECTIONS ===
# This editable block contains DIRECT process protections.
# This profile is for users in mainland China: private, China, Apple China,
# Microsoft China, Google China, QQ/WeChat/Cursor, WPS Office /
# cloud sync / update, and subscription update traffic stay DIRECT;
# non-mainland fallback traffic uses PROXY. Browsers and ChatGPT desktop
# apps are routed by the ChatGPT process rules above, not here.
# To stop protecting one DIRECT process, comment out its line. Keep these
# process rules explicit and predictable.
"""
    direct_end_help = """# === END USER-EDITABLE PROCESS DIRECT PROTECTIONS ===
# === USER-EDITABLE PROCESS PROXY OVERRIDES ===
# These narrow PROXY overrides target selected non-browser developer desktop
# app install paths: Antigravity. Browser fingerprint traffic uses ChatGPT
# process rules above. These overrides deliberately do not target shared
# runtimes such as msedgewebview2.exe, node, or python.
# Comment individual lines out to route that app by destination rules only.
"""
    proxy_end_help = """# === END USER-EDITABLE PROCESS PROXY OVERRIDES ===
"""
    domain_help = """# Domain and DustinWin/ruleset_geodata rules start below.
"""
    no_proxy_help = """# No default process proxy overrides for this platform.
# === END USER-EDITABLE PROCESS PROXY OVERRIDES ===
# Domain and DustinWin/ruleset_geodata rules start below.
"""
    yaml_text = yaml_text.replace("rules:\n", cursor_domain_help, 1)
    first_openai_domain_rule = "- DOMAIN-SUFFIX,openai.com,ChatGPT"
    if first_openai_domain_rule in yaml_text:
        yaml_text = yaml_text.replace(first_openai_domain_rule, openai_domain_help + first_openai_domain_rule, 1)
    first_chatgpt_process_rule = "- PROCESS-NAME,chrome.exe,ChatGPT"
    if first_chatgpt_process_rule in yaml_text:
        yaml_text = yaml_text.replace(
            first_chatgpt_process_rule,
            chatgpt_process_help + first_chatgpt_process_rule,
            1,
        )
    else:
        first_chatgpt_process_rule = "- PROCESS-NAME,Google Chrome,ChatGPT"
        if first_chatgpt_process_rule in yaml_text:
            yaml_text = yaml_text.replace(
                first_chatgpt_process_rule,
                chatgpt_process_help + first_chatgpt_process_rule,
                1,
            )
        else:
            first_chatgpt_process_rule = "- PROCESS-NAME,google-chrome,ChatGPT"
            if first_chatgpt_process_rule in yaml_text:
                yaml_text = yaml_text.replace(
                    first_chatgpt_process_rule,
                    chatgpt_process_help + first_chatgpt_process_rule,
                    1,
                )
    first_wps_domain_rule = "- DOMAIN-KEYWORD,kingsoft,DIRECT"
    if first_wps_domain_rule in yaml_text:
        yaml_text = yaml_text.replace(first_wps_domain_rule, wps_domain_help + first_wps_domain_rule, 1)
    first_direct_process_rule = "- PROCESS-NAME,ssh.exe,DIRECT"
    if first_direct_process_rule in yaml_text:
        yaml_text = yaml_text.replace(first_direct_process_rule, process_help + first_direct_process_rule, 1)
    else:
        first_direct_process_rule = "- PROCESS-NAME,ssh,DIRECT"
        if first_direct_process_rule in yaml_text:
            yaml_text = yaml_text.replace(first_direct_process_rule, process_help + first_direct_process_rule, 1)
    first_proxy_rule = r"- PROCESS-PATH-WILDCARD,C:\Program Files\Google\Antigravity\*,PROXY"
    if first_proxy_rule in yaml_text:
        yaml_text = yaml_text.replace(first_proxy_rule, direct_end_help + first_proxy_rule, 1)
    else:
        first_proxy_rule = "- PROCESS-PATH-WILDCARD,/Applications/Antigravity.app/Contents/*,PROXY"
        if first_proxy_rule in yaml_text:
            yaml_text = yaml_text.replace(first_proxy_rule, direct_end_help + first_proxy_rule, 1)
        else:
            first_domain_rule = "- DOMAIN,"
            if first_domain_rule in yaml_text:
                yaml_text = yaml_text.replace(first_domain_rule, direct_end_help + no_proxy_help + first_domain_rule, 1)
                return yaml_text

    proxy_rule_index = yaml_text.find(first_proxy_rule)
    first_domain_rule_index = yaml_text.find("\n- DOMAIN,", proxy_rule_index if proxy_rule_index >= 0 else 0)
    if first_domain_rule_index >= 0:
        insert_at = first_domain_rule_index + 1
        yaml_text = yaml_text[:insert_at] + proxy_end_help + domain_help + yaml_text[insert_at:]
    return yaml_text


def mihomo_cursor_domain_direct_rules() -> list[str]:
    return [
        *[f"DOMAIN-KEYWORD,{keyword},DIRECT" for keyword in CURSOR_DIRECT_DOMAIN_KEYWORDS],
        *[f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in CURSOR_DIRECT_DOMAIN_SUFFIXES],
    ]


def mihomo_wps_domain_direct_rules() -> list[str]:
    return [
        *[f"DOMAIN-KEYWORD,{keyword},DIRECT" for keyword in WPS_DIRECT_DOMAIN_KEYWORDS],
        *[f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in WPS_DIRECT_DOMAIN_SUFFIXES],
    ]


def mihomo_domestic_platform_fake_ip_filter_patterns() -> list[str]:
    patterns: list[str] = []
    seen: set[str] = set()
    for domain in DOMESTIC_PLATFORM_DIRECT_DOMAIN_SUFFIXES:
        for pattern in (domain, f"+.{domain}", f"*.{domain}"):
            if pattern not in seen:
                patterns.append(pattern)
                seen.add(pattern)
    return patterns


def mihomo_domestic_platform_direct_rules() -> list[str]:
    return [
        f"DOMAIN-SUFFIX,{domain},DIRECT"
        for domain in DOMESTIC_PLATFORM_DIRECT_DOMAIN_SUFFIXES
    ]


def mihomo_mirror_fake_ip_filter_patterns() -> list[str]:
    patterns: list[str] = []
    seen: set[str] = set()
    for domain in MIRROR_DIRECT_DOMAIN_SUFFIXES:
        for pattern in (domain, f"+.{domain}", f"*.{domain}"):
            if pattern not in seen:
                patterns.append(pattern)
                seen.add(pattern)
    return patterns


def mihomo_domestic_dns_nameserver_policy() -> dict[str, list[str]]:
    domestic_resolvers = ["223.5.5.5", "119.29.29.29"]
    policy: dict[str, list[str]] = {}
    for domain in DOMESTIC_PLATFORM_DIRECT_DOMAIN_SUFFIXES:
        policy[f"+.{domain}"] = domestic_resolvers
    for domain in MIRROR_DIRECT_DOMAIN_SUFFIXES:
        policy[f"+.{domain}"] = domestic_resolvers
    return policy


def mihomo_mirror_direct_rules() -> list[str]:
    return [f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in MIRROR_DIRECT_DOMAIN_SUFFIXES]


def mihomo_openai_domain_proxy_rules() -> list[str]:
    return [f"DOMAIN-SUFFIX,{domain},ChatGPT" for domain in OPENAI_PROXY_DOMAIN_SUFFIXES]


def mihomo_proxy_node_direct_rules(repo_root: Path = REPO_ROOT) -> list[str]:
    rules: list[str] = []
    seen: set[str] = set()
    for node in registry_subscription_nodes(repo_root):
        host = node_public_host(node).strip()
        try:
            ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError(f"proxy node DIRECT bootstrap rule requires an IP host for {node['name']}: {host}") from exc
        if not host or host in seen:
            continue
        rules.append(f"IP-CIDR,{host}/32,DIRECT,no-resolve")
        seen.add(host)
    return rules


def mihomo_pre_domain_direct_process_rules(platform: str) -> list[str]:
    process_paths = mihomo_process_values(PRE_DOMAIN_DIRECT_PROCESS_PATHS_BY_PLATFORM, platform)

    rules: list[str] = []
    seen: set[str] = set()
    for process_path in process_paths:
        rule_type = "PROCESS-PATH-WILDCARD" if "*" in process_path else "PROCESS-PATH"
        rule = f"{rule_type},{process_path},DIRECT"
        if rule not in seen:
            rules.append(rule)
            seen.add(rule)
    return rules


def mihomo_chatgpt_process_rules(platform: str) -> list[str]:
    process_names = mihomo_process_values(CHATGPT_PROCESS_NAMES_BY_PLATFORM, platform)
    process_paths = mihomo_process_values(CHATGPT_PROCESS_PATHS_BY_PLATFORM, platform)

    rules: list[str] = []
    seen: set[str] = set()
    for process_name in process_names:
        rule = f"PROCESS-NAME,{process_name},ChatGPT"
        if rule not in seen:
            rules.append(rule)
            seen.add(rule)
    for process_path in process_paths:
        rule_type = "PROCESS-PATH-WILDCARD" if "*" in process_path else "PROCESS-PATH"
        rule = f"{rule_type},{process_path},ChatGPT"
        if rule not in seen:
            rules.append(rule)
            seen.add(rule)
    return rules


def mihomo_direct_process_rules(platform: str) -> list[str]:
    process_names = mihomo_process_values(DIRECT_PROCESS_NAMES_BY_PLATFORM, platform)
    process_paths = mihomo_process_values(DIRECT_PROCESS_PATHS_BY_PLATFORM, platform)

    rules: list[str] = []
    seen: set[str] = set()
    for process_name in process_names:
        rule = f"PROCESS-NAME,{process_name},DIRECT"
        if rule not in seen:
            rules.append(rule)
            seen.add(rule)
    for process_path in process_paths:
        rule_type = "PROCESS-PATH-WILDCARD" if "*" in process_path else "PROCESS-PATH"
        rule = f"{rule_type},{process_path},DIRECT"
        if rule not in seen:
            rules.append(rule)
            seen.add(rule)
    return rules


def mihomo_proxy_process_rules(platform: str) -> list[str]:
    process_paths = mihomo_process_values(PROXY_PROCESS_PATHS_BY_PLATFORM, platform)

    rules: list[str] = []
    seen: set[str] = set()
    for process_path in process_paths:
        rule_type = "PROCESS-PATH-WILDCARD" if "*" in process_path else "PROCESS-PATH"
        rule = f"{rule_type},{process_path},PROXY"
        if rule not in seen:
            rules.append(rule)
            seen.add(rule)
    return rules


def _qqpw_names_vless_first(names: list[str]) -> list[str]:
    """Prefer QQPW VLESS Reality; keep Hy2 as trailing bonus."""
    vless = [name for name in names if "Reality" in name or ("Hysteria" not in name and "SOCKS" not in name.upper())]
    hy2 = [name for name in names if "Hysteria" in name]
    rest = [name for name in names if name not in vless and name not in hy2]
    # Deduplicate while preserving order: Reality-like first, then other non-hy2, then hy2.
    ordered: list[str] = []
    for group in (vless, rest, hy2):
        for name in group:
            if name not in ordered:
                ordered.append(name)
    return ordered


def mihomo_classify_proxy_names(nodes: list[dict], *, repo_root: Path | None = None) -> dict[str, list[str]]:
    """Split leaf proxies into ChatGPT (QQPW) vs general PROXY candidates."""
    qqpw_names: list[str] = []
    general_names: list[str] = []
    for proxy in mihomo_proxies_for_nodes(nodes, repo_root=repo_root):
        name = str(proxy["name"])
        if name.startswith("QQPW-"):
            qqpw_names.append(name)
        else:
            general_names.append(name)
    qqpw_names = _qqpw_names_vless_first(qqpw_names)
    return {
        "qqpw": qqpw_names,
        "general": general_names,
        "all": general_names + qqpw_names,
    }


def mihomo_proxy_groups_for_nodes(nodes: list[dict], *, repo_root: Path | None = None) -> list[dict]:
    classified = mihomo_classify_proxy_names(nodes, repo_root=repo_root)
    qqpw_names = classified["qqpw"]
    general_names = classified["general"]
    # Auto prefers general (non-QQPW) exits; ChatGPT defaults to QQPW VLESS.
    auto_proxies = general_names or classified["all"] or ["DIRECT"]
    chatgpt_proxies = [*qqpw_names, *general_names, "DIRECT"]
    if not qqpw_names and not general_names:
        chatgpt_proxies = ["DIRECT"]
    proxy_select = ["Auto", *general_names, *qqpw_names, "DIRECT"]

    return [
        {
            "name": "PROXY",
            "type": "select",
            "proxies": proxy_select,
        },
        {
            "name": "ChatGPT",
            "type": "select",
            "proxies": chatgpt_proxies,
        },
        {
            "name": "Auto",
            "type": "url-test",
            "proxies": auto_proxies,
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
            "tolerance": 80,
        },
    ]


def render_mihomo_config(repo_root: Path = REPO_ROOT, *, platform: str) -> str:
    nodes = subscription_publishable_nodes(repo_root)
    default_proxy = "PROXY"
    config = {
        "mixed-port": 7890,
        "allow-lan": False,
        "bind-address": "127.0.0.1",
        "mode": "rule",
        "find-process-mode": "always",
        "log-level": "info",
        "ipv6": False,
        "unified-delay": True,
        "tcp-concurrent": True,
        "geodata-mode": False,
        "external-controller": "127.0.0.1:9090",
        "external-ui": "ui",
        "profile": {
            "store-selected": True,
            "store-fake-ip": True,
        },
        "tun": mihomo_tun_config(repo_root),
        "dns": mihomo_dns_config(),
        "proxies": mihomo_proxies_for_nodes(nodes, repo_root=repo_root),
        "proxy-groups": mihomo_proxy_groups_for_nodes(nodes, repo_root=repo_root),
        "rule-providers": {
            "privateip": mihomo_rule_provider("privateip", "ipcidr"),
            "cn": mihomo_rule_provider("cn", "domain"),
            "cnip": mihomo_rule_provider("cnip", "ipcidr"),
            "apple-cn": mihomo_rule_provider("apple-cn", "domain"),
            "microsoft-cn": mihomo_rule_provider("microsoft-cn", "domain"),
            "google-cn": mihomo_rule_provider("google-cn", "domain"),
            "ads": mihomo_rule_provider("ads", "domain"),
            "proxy": mihomo_rule_provider("proxy", "domain"),
            "gfw": mihomo_rule_provider("gfw", "domain"),
            "tld-proxy": mihomo_rule_provider("tld-proxy", "domain"),
            "telegramip": mihomo_rule_provider("telegramip", "ipcidr"),
        },
        "rules": [
            *mihomo_cursor_domain_direct_rules(),
            *mihomo_proxy_node_direct_rules(repo_root),
            *mihomo_pre_domain_direct_process_rules(platform),
            *mihomo_openai_domain_proxy_rules(),
            *mihomo_chatgpt_process_rules(platform),
            *mihomo_wps_domain_direct_rules(),
            *mihomo_direct_process_rules(platform),
            *mihomo_proxy_process_rules(platform),
            *mihomo_domestic_platform_direct_rules(),
            *mihomo_mirror_direct_rules(),
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
            f"MATCH,{default_proxy}",
        ],
    }
    return annotate_mihomo_rules_yaml(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))


def single_node_subscription_filename(node_name: str) -> str:
    return f"v2ray_node_{node_name}.txt"


def render_v2ray_subscription(repo_root: Path = REPO_ROOT, node_name: str | None = None) -> str:
    if node_name is None:
        nodes = subscription_publishable_nodes(repo_root)
    else:
        eligible_names = {node["name"] for node in subscription_publishable_nodes(repo_root)}
        if node_name not in eligible_names:
            return ""
        nodes = [enabled_node_by_name(repo_root, node_name)]
    if not nodes:
        return ""
    links: list[str] = []
    for node in nodes:
        links.extend(subscription_links_for_node(node))
    # Extra profiles (e.g. qqpw wireguard_nat) are published as their own files and
    # only folded into the multi-node subscription — never aliased into a host file.
    if node_name is None:
        for entry in extra_single_node_subscriptions(repo_root):
            links.extend(subscription_links_for_extra_entry(repo_root, entry))
    return "\n".join(links) + "\n"


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


def subscription_public_port(subscriptions: dict) -> str:
    parsed = urllib.parse.urlparse(subscriptions["subscription_base_url"])
    if parsed.port is not None:
        return str(parsed.port)
    if parsed.scheme == "https":
        return "443"
    if parsed.scheme == "http":
        return "80"
    return "unknown"


def render_subscription_landing_page(repo_root: Path = REPO_ROOT) -> str:
    subscriptions = load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    base_url = subscriptions["subscription_base_url"].rstrip("/")
    public_port = subscription_public_port(subscriptions)
    multi_node_url = base_url + "/v2ray_nodes.txt"
    singbox_url = base_url + "/singbox-client-profile.json"
    windows_install_script_url = base_url + "/install-mihomo-windows.ps1"
    windows_install_command = (
        f"iwr -UseB {windows_install_script_url} -OutFile "
        "$env:TEMP\\install-mihomo-windows.ps1; "
        "powershell -ExecutionPolicy Bypass -File $env:TEMP\\install-mihomo-windows.ps1"
    )

    node_sections: list[str] = []
    availability = exclusion_report(repo_root)
    pending_names = set(availability.pending)
    for index, node in enumerate(subscription_publishable_nodes(repo_root), start=1):
        node_name = str(node["name"])
        alias = html.escape(str(node["subscription_alias"]))
        provider = html.escape(str(node.get("provider", "unknown")))
        pending_note = " · 探测异常，暂仍发布" if node_name in pending_names else ""
        protocol_note = "VLESS Reality"
        if node_hysteria2_on_public_subscription(node):
            protocol_note += " · Hysteria2"
        if node_has_dual_egress(node):
            expected = ((node_egress_profiles(node).get("public") or {}).get("expected_exit_ip") or node_public_host(node))
            protocol_note += f" · public egress {expected}"
        v2ray_url = base_url + f"/{single_node_subscription_filename(node_name)}"
        v2ray_url_html = html.escape(v2ray_url)
        node_sections.append(
            "\n".join(
                [
                    "      <article class=\"node-row\">",
                    "        <div class=\"node-rank\">",
                    f"          <span>{index:02d}</span>",
                    "        </div>",
                    "        <div class=\"node-copy\">",
                    f"          <h3>{alias}</h3>",
                    f"          <p>{provider} · {protocol_note} · 端口 {int(node['base_port']) + 3}{pending_note}</p>",
                    "        </div>",
                    "        <div class=\"node-actions\">",
                    f"          <a class=\"text-link\" href=\"{v2ray_url_html}\">订阅 URL</a>",
                    "          <button type=\"button\" "
                    f"data-copy=\"{html.escape(v2ray_url, quote=True)}\" "
                    f"aria-label=\"复制{alias}订阅 URL\">复制</button>",
                    "        </div>",
                    "        <div class=\"node-url\">",
                    f"          <span>{v2ray_url_html}</span>",
                    "        </div>",
                    "      </article>",
                ]
            )
        )

    for extra in extra_single_node_subscriptions(repo_root):
        source_node_name = str(extra["source_node"])
        filename = str(extra["filename"])
        title = html.escape(str(extra.get("title", filename)))
        description = html.escape(str(extra.get("description", "")))
        aliases = dict(extra.get("aliases") or {})
        v2ray_url = base_url + f"/{extra_single_node_subscription_filename(filename)}"
        v2ray_url_html = html.escape(v2ray_url)
        node_sections.append(
            "\n".join(
                [
                    "      <article class=\"node-row\">",
                    "        <div class=\"node-rank\">",
                    "          <span>+</span>",
                    "        </div>",
                    "        <div class=\"node-copy\">",
                    f"          <h3>{title}</h3>",
                    f"          <p>{description}</p>",
                    "        </div>",
                    "        <div class=\"node-actions\">",
                    f"          <a class=\"text-link\" href=\"{v2ray_url_html}\">订阅 URL</a>",
                    "          <button type=\"button\" "
                    f"data-copy=\"{html.escape(v2ray_url, quote=True)}\" "
                    f"aria-label=\"复制{title}订阅 URL\">复制</button>",
                    "        </div>",
                    "        <div class=\"node-url\">",
                    f"          <span>{v2ray_url_html}</span>",
                    "        </div>",
                    "      </article>",
                ]
            )
        )

    node_links_html = "\n".join(node_sections)
    multi_node_url_html = html.escape(multi_node_url)
    singbox_url_html = html.escape(singbox_url)
    mihomo_universal_url_html = html.escape(base_url + "/mihomo-universal.yaml")
    mihomo_process_notes_url_html = html.escape(base_url + "/mihomo-process-routing.md")
    windows_install_script_url_html = html.escape(windows_install_script_url)
    windows_install_command_html = html.escape(windows_install_command)
    windows_install_command_copy = html.escape(windows_install_command, quote=True)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GG Proxy Subscriptions</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #19202f;
      --muted: #687185;
      --line: rgba(25, 32, 47, 0.12);
      --paper: rgba(255, 255, 255, 0.82);
      --green: #12b981;
      --blue: #2563eb;
      --coral: #ef5d44;
      --yellow: #f6c84c;
      font-family: "Segoe UI", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      background: #fffaf0;
      color: var(--ink);
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      padding: 26px 30px 34px;
      background:
        linear-gradient(135deg, #fdf7e3 0%, #eafaf4 42%, #eef5ff 100%);
      overflow-x: hidden;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(25, 32, 47, 0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(25, 32, 47, 0.045) 1px, transparent 1px);
      background-size: 46px 46px;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.5), transparent 72%);
    }}
    main {{
      position: relative;
      max-width: 1180px;
      margin: 0 auto;
      display: grid;
      gap: 20px;
    }}
    .hero {{
      min-height: 220px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 24px;
      align-items: end;
      padding: 38px 42px 34px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background:
        linear-gradient(120deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.66)),
        radial-gradient(circle at 82% 20%, rgba(18, 185, 129, 0.22), transparent 28%),
        radial-gradient(circle at 12% 16%, rgba(239, 93, 68, 0.16), transparent 24%);
      box-shadow: 0 22px 60px rgba(37, 99, 235, 0.11);
      backdrop-filter: blur(18px);
    }}
    .eyebrow {{
      margin: 0 0 12px;
      color: var(--coral);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    h1 {{
      max-width: 720px;
      margin: 0;
      font-size: 54px;
      line-height: 1.02;
      letter-spacing: 0;
      font-weight: 800;
    }}
    .hero-copy {{
      max-width: 680px;
      margin: 18px 0 0;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.7;
    }}
    .status-board {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .metric {{
      min-height: 88px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.72);
    }}
    .metric strong {{
      display: block;
      font-size: 30px;
      line-height: 1;
    }}
    .metric span {{
      display: block;
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .notice {{
      display: flex;
      gap: 12px;
      align-items: center;
      min-height: 54px;
      padding: 14px 18px;
      border: 1px solid rgba(18, 185, 129, 0.28);
      border-radius: 8px;
      background: rgba(236, 253, 245, 0.78);
      color: #047857;
      font-weight: 600;
    }}
    .notice-dot {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 0 6px rgba(18, 185, 129, 0.13);
    }}
    .surface {{
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--paper);
      backdrop-filter: blur(18px);
      box-shadow: 0 16px 44px rgba(25, 32, 47, 0.08);
    }}
    .section-heading {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: end;
      margin-bottom: 18px;
    }}
    h2 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }}
    .section-heading p {{
      max-width: 520px;
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}
    .primary-links {{
      display: grid;
      grid-template-columns: 1.2fr 1fr 1fr;
      gap: 14px;
    }}
    .link-panel {{
      min-width: 0;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.68);
    }}
    .link-panel strong {{
      display: block;
      margin-bottom: 10px;
      font-size: 16px;
    }}
    .link-panel code,
    .node-url span {{
      display: block;
      word-break: break-all;
      color: #334155;
      font-family: "Cascadia Mono", "Consolas", monospace;
      font-size: 13px;
      line-height: 1.55;
    }}
    .copy-line {{
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 14px;
    }}
    button {{
      flex: none;
      height: 34px;
      padding: 0 14px;
      border: 1px solid rgba(37, 99, 235, 0.24);
      border-radius: 8px;
      background: #ffffff;
      color: var(--blue);
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover {{
      border-color: var(--blue);
      box-shadow: 0 6px 18px rgba(37, 99, 235, 0.12);
    }}
    .nodes {{
      display: grid;
      gap: 10px;
    }}
    .node-row {{
      display: grid;
      grid-template-columns: 58px minmax(220px, 0.8fr) minmax(280px, 1fr);
      gap: 16px;
      align-items: center;
      min-height: 112px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.66);
    }}
    .node-rank span {{
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: #fff6d8;
      color: #8a5a00;
      font-weight: 800;
    }}
    .node-copy h3 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .node-copy p {{
      margin: 8px 0 0;
      color: var(--muted);
      line-height: 1.5;
    }}
    .node-actions {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }}
    .node-url {{
      grid-column: 2 / 4;
      padding-top: 4px;
    }}
    .text-link {{
      display: inline-flex;
      align-items: center;
      height: 34px;
      color: var(--blue);
      font-weight: 700;
      text-decoration: none;
    }}
    .text-link:hover {{
      text-decoration: underline;
    }}
    .toast {{
      position: fixed;
      right: 28px;
      bottom: 28px;
      padding: 12px 16px;
      border-radius: 8px;
      background: #19202f;
      color: #fff;
      opacity: 0;
      transform: translateY(10px);
      transition: opacity 160ms ease, transform 160ms ease;
    }}
    .toast[data-visible="true"] {{
      opacity: 1;
      transform: translateY(0);
    }}
    @media (max-width: 900px) {{
      body {{
        padding: 16px;
      }}
      .hero {{
        grid-template-columns: 1fr;
        padding: 28px 24px;
      }}
      h1 {{
        font-size: 38px;
      }}
      .primary-links {{
        grid-template-columns: 1fr;
      }}
      .section-heading {{
        display: block;
      }}
      .section-heading p {{
        margin-top: 8px;
      }}
      .node-row {{
        grid-template-columns: 46px minmax(0, 1fr);
      }}
      .node-actions {{
        grid-column: 1 / 3;
        justify-content: flex-start;
      }}
      .node-url {{
        grid-column: 1 / 3;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <p class="eyebrow">Proxy Subscriptions</p>
        <h1>GG Proxy Subscriptions</h1>
        <p class="hero-copy">一个明亮、免登录、可直接复制的订阅入口。Clash Verge Rev / mihomo 配置优先，同时保留 VLESS URL 和 sing-box Remote Profile 兼容入口。</p>
      </div>
      <div class="status-board" aria-label="订阅状态摘要">
        <div class="metric"><strong>{len(subscription_publishable_nodes(repo_root))}</strong><span>健康发布节点</span></div>
        <div class="metric"><strong>{subscriptions["update_interval_hours"]}h</strong><span>建议更新周期</span></div>
        <div class="metric"><strong>{public_port}</strong><span>订阅入口端口</span></div>
        <div class="metric"><strong>KR</strong><span>新增区域</span></div>
      </div>
    </section>

    <div class="notice"><span class="notice-dot"></span><span>这个订阅站点不需要用户名密码。如果浏览器提示你输入用户名密码，通常说明你访问错了入口，或者命中了旧缓存。</span></div>

    <section class="surface">
      <div class="section-heading">
        <h2>多节点入口</h2>
        <p>优先导入 Clash Verge Rev / mihomo universal profile。VLESS URL 只作兼容客户端原始节点订阅。</p>
      </div>
      <div class="primary-links">
        <div class="link-panel">
          <strong>手动订阅 URL</strong>
          <code>{multi_node_url_html}</code>
          <div class="copy-line">
            <a class="text-link" href="{multi_node_url_html}">打开</a>
            <button type="button" data-copy="{multi_node_url_html}" aria-label="复制多节点订阅 URL">复制</button>
          </div>
        </div>
        <div class="link-panel">
          <strong>sing-box Remote Profile</strong>
          <code>{singbox_url_html}</code>
          <div class="copy-line">
            <a class="text-link" href="{singbox_url_html}">打开</a>
            <button type="button" data-copy="{singbox_url_html}" aria-label="复制 sing-box Remote Profile URL">复制</button>
          </div>
        </div>
      </div>
    </section>

    <section class="surface">
      <div class="section-heading">
        <h2>Clash Verge Rev / mihomo</h2>
        <p>The universal profile is the recommended Clash Verge Rev import. It keeps the existing VLESS Reality nodes, enables TUN rule mode, uses DustinWin/ruleset_geodata mihomo-ruleset, keeps mainland China/private traffic direct, and routes non-mainland fallback traffic through PROXY.</p>
      </div>
      <div class="primary-links">
        <div class="link-panel">
          <strong>Universal mihomo YAML</strong>
          <code>{mihomo_universal_url_html}</code>
          <div class="copy-line">
            <a class="text-link" href="{mihomo_universal_url_html}">Open</a>
            <button type="button" data-copy="{mihomo_universal_url_html}" aria-label="Copy universal mihomo YAML URL">Copy</button>
          </div>
        </div>
        <div class="link-panel">
          <strong>Process routing notes</strong>
          <code>{mihomo_process_notes_url_html}</code>
          <div class="copy-line">
            <a class="text-link" href="{mihomo_process_notes_url_html}">Open</a>
            <button type="button" data-copy="{mihomo_process_notes_url_html}" aria-label="Copy process routing notes URL">Copy</button>
          </div>
        </div>
        <div class="link-panel">
          <strong>Ruleset source</strong>
          <code>DustinWin/ruleset_geodata mihomo-ruleset</code>
          <div class="copy-line">
            <a class="text-link" href="https://github.com/DustinWin/ruleset_geodata">Open</a>
          </div>
        </div>
      </div>
    </section>

    <section class="surface">
      <div class="section-heading">
        <h2>Windows 快速部署</h2>
        <p>默认安装 mihomo core 和 MetaCubeXD Web UI，不安装 MetaCubeXD 桌面版。请用管理员 PowerShell 运行，脚本会校验 GitHub release digest、备份旧文件，并注册 SYSTEM 开机任务。</p>
      </div>
      <div class="primary-links">
        <div class="link-panel">
          <strong>复制一键安装命令</strong>
          <code>{windows_install_command_html}</code>
          <div class="copy-line">
            <button type="button" data-copy="{windows_install_command_copy}" aria-label="复制 Windows mihomo 一键安装命令">复制</button>
          </div>
        </div>
        <div class="link-panel">
          <strong>下载 PowerShell 脚本</strong>
          <code>{windows_install_script_url_html}</code>
          <div class="copy-line">
            <a class="text-link" href="{windows_install_script_url_html}">打开</a>
            <button type="button" data-copy="{windows_install_script_url_html}" aria-label="复制 Windows mihomo 安装脚本 URL">复制</button>
          </div>
        </div>
        <div class="link-panel">
          <strong>Dashboard 地址</strong>
          <code>http://127.0.0.1:9090/ui/</code>
          <p>订阅 URL 应写入 mihomo profile；MetaCubeXD Web 面板不是订阅源配置中心，它只连接本机 controller 来切换节点和查看连接。</p>
        </div>
      </div>
    </section>

    <section class="surface">
      <div class="section-heading">
        <h2>单节点入口</h2>
        <p>需要固定线路时，直接复制对应单节点订阅。新增 KR 节点已经纳入同一发布面。</p>
      </div>
      <div class="nodes">
{node_links_html}
      </div>
    </section>
  </main>
  <div class="toast" id="copy-toast" role="status" aria-live="polite">已复制</div>
  <script>
    const toast = document.getElementById("copy-toast");
    let toastTimer = 0;
    function showToast(message) {{
      toast.textContent = message;
      toast.dataset.visible = "true";
      window.clearTimeout(toastTimer);
      toastTimer = window.setTimeout(() => {{
        toast.dataset.visible = "false";
      }}, 1400);
    }}
    async function copyToClipboard(value) {{
      if (navigator.clipboard && window.isSecureContext) {{
        await navigator.clipboard.writeText(value);
        return;
      }}
      const textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }}
    document.addEventListener("click", async (event) => {{
      const button = event.target.closest("button[data-copy]");
      if (!button) {{
        return;
      }}
      try {{
        await copyToClipboard(button.dataset.copy);
        showToast("已复制到剪贴板");
      }} catch (error) {{
        showToast("复制失败，请手动选择链接");
      }}
    }});
  </script>
</body>
</html>
"""


def render_windows_mihomo_install_script(repo_root: Path = REPO_ROOT) -> str:
    subscriptions = load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    profile_url = subscriptions["subscription_base_url"].rstrip("/") + "/mihomo-universal.yaml"
    script = r'''<#
Installs mihomo with MetaCubeXD Web UI on Windows.

Run from an elevated PowerShell session. The script downloads official latest
GitHub release assets, validates SHA256 digests returned by GitHub, validates
the mihomo profile, and registers a resident SYSTEM startup task.
#>

[CmdletBinding()]
param(
    [string]$InstallRoot = 'C:\Tools\mihomo',
    [string]$ProgramDataRoot = 'C:\ProgramData\mihomo',
    [string]$SystemConfigRoot = 'C:\Windows\System32\config\systemprofile\.config\mihomo',
    [string]$ProfileUrl = '__PROFILE_URL__',
    [string]$TaskName = 'Mihomo TUN Transparent Proxy',
    [int]$StartupWaitSeconds = 8
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$MihomoExe = Join-Path $InstallRoot 'mihomo-windows-amd64.exe'
$ProfilePath = Join-Path $ProgramDataRoot 'mihomo-universal.yaml'
$SafeProfilePath = Join-Path $SystemConfigRoot 'mihomo-universal.yaml'
$UiPath = Join-Path $SystemConfigRoot 'ui'
$LogPath = Join-Path $ProgramDataRoot 'install-mihomo-windows.log'
$WorkRoot = Join-Path $env:TEMP ('mihomo-install-' + [guid]::NewGuid().ToString('N'))

function Write-Step {
    param([Parameter(Mandatory)] [string]$Message)
    Write-Host ''
    Write-Host "== $Message =="
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this script from an elevated PowerShell session. TUN and SYSTEM startup task setup require administrator rights.'
    }
}

function Invoke-GitHubApi {
    param([Parameter(Mandatory)] [string]$Uri)
    Invoke-RestMethod -Uri $Uri -Headers @{ 'User-Agent' = 'proxy-platform-mihomo-installer' } -TimeoutSec 30
}

function Select-RequiredAsset {
    param(
        [Parameter(Mandatory)] $Release,
        [Parameter(Mandatory)] [string[]]$Patterns,
        [Parameter(Mandatory)] [string]$Label
    )

    foreach ($pattern in $Patterns) {
        $matches = @($Release.assets | Where-Object { $_.name -match $pattern } | Sort-Object name)
        if ($matches.Count -gt 0) {
            return $matches[0]
        }
    }
    $available = @($Release.assets | ForEach-Object { $_.name }) -join ', '
    throw "No $Label release asset matched. Available assets: $available"
}

function Save-Download {
    param(
        [Parameter(Mandatory)] [string]$Url,
        [Parameter(Mandatory)] [string]$Path,
        [int]$MaxAttempts = 4
    )

    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    $lastError = $null

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        Write-Host "download_attempt=$attempt url=$Url"
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue

        if ($curl) {
            & $curl.Source -fL --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 300 -o $Path $Url
            if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $Path) -and ((Get-Item -LiteralPath $Path).Length -gt 0)) {
                return
            }
            $lastError = "curl.exe download failed with exit code $LASTEXITCODE"
            Write-Warning $lastError
            Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        }

        try {
            Invoke-WebRequest -Uri $Url -OutFile $Path -UseBasicParsing -TimeoutSec 300
            if (Test-Path -LiteralPath $Path) {
                if ((Get-Item -LiteralPath $Path).Length -gt 0) {
                    return
                }
            }
            $lastError = "Invoke-WebRequest created an empty or missing file"
            Write-Warning $lastError
        } catch {
            $lastError = "Invoke-WebRequest failed: $($_.Exception.Message)"
            Write-Warning $lastError
        }

        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        if ($attempt -lt $MaxAttempts) {
            Start-Sleep -Seconds ([Math]::Min(12, 2 * $attempt))
        }
    }

    throw "Download failed after $MaxAttempts attempts: $Url; last_error=$lastError"
}

function Assert-FileDigest {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Digest,
        [Parameter(Mandatory)] [string]$Label
    )

    if ($Digest -notmatch '^sha256:[0-9a-fA-F]{64}$') {
        throw "$Label release asset does not expose a usable sha256 digest"
    }
    $expected = $Digest.Substring(7).ToLowerInvariant()
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    Write-Host "$Label expected_sha256=$expected"
    Write-Host "$Label actual_sha256=$actual"
    if ($actual -ne $expected) {
        throw "$Label SHA256 mismatch"
    }
}

function Backup-ExistingPath {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$BackupRoot
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    $leaf = Split-Path -Leaf $Path
    $destination = Join-Path $BackupRoot $leaf
    Copy-Item -LiteralPath $Path -Destination $destination -Recurse -Force
    Write-Host "backup_path=$destination"
}

function Stop-MihomoRuntime {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Get-Process mihomo-windows-amd64, mihomo -ErrorAction SilentlyContinue | Stop-Process -Force
}

function Set-YamlScalarValue {
    param(
        [Parameter(Mandatory)] [string]$Text,
        [Parameter(Mandatory)] [string]$Key,
        [Parameter(Mandatory)] [string]$Value
    )

    if ($Text -match "(?m)^$([regex]::Escape($Key)):\s*.+$") {
        return [regex]::Replace($Text, "(?m)^$([regex]::Escape($Key)):\s*.+$", "$Key`: $Value")
    }
    return $Text.TrimEnd() + "`r`n$Key`: $Value`r`n"
}

function Write-ReviewedProfile {
    param(
        [Parameter(Mandatory)] [string]$SourcePath,
        [Parameter(Mandatory)] [string]$DestinationPath
    )

    # Runtime binding invariants:
    # SYSTEM profile: C:\Windows\System32\config\systemprofile\.config\mihomo\mihomo-universal.yaml
    # external-controller: 127.0.0.1:9090
    # external-ui: ui
    $profile = Get-Content -LiteralPath $SourcePath -Raw
    $profile = Set-YamlScalarValue -Text $profile -Key 'external-controller' -Value '127.0.0.1:9090'
    $profile = Set-YamlScalarValue -Text $profile -Key 'external-ui' -Value 'ui'
    New-Item -ItemType Directory -Path (Split-Path -Parent $DestinationPath) -Force | Out-Null
    Set-Content -LiteralPath $DestinationPath -Value $profile -Encoding UTF8
}

function Expand-MihomoAsset {
    param(
        [Parameter(Mandatory)] [string]$ArchivePath,
        [Parameter(Mandatory)] [string]$DestinationRoot
    )

    $extractRoot = Join-Path $WorkRoot 'mihomo'
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $extractRoot -Force
    $candidate = Get-ChildItem -LiteralPath $extractRoot -Recurse -File |
        Where-Object { $_.Name -match '^mihomo.*\.exe$' } |
        Sort-Object FullName |
        Select-Object -First 1
    if (-not $candidate) {
        throw 'mihomo executable was not found inside the downloaded archive'
    }
    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
    Copy-Item -LiteralPath $candidate.FullName -Destination $MihomoExe -Force
}

function Expand-MetaCubeXDWebUi {
    param(
        [Parameter(Mandatory)] [string]$ArchivePath,
        [Parameter(Mandatory)] [string]$DestinationRoot,
        [Parameter(Mandatory)] [string]$BackupRoot
    )

    $tar = Get-Command tar.exe -ErrorAction SilentlyContinue
    if (-not $tar) {
        throw 'tar.exe was not found. Windows 10/11 includes it by default; install bsdtar or update Windows.'
    }

    $extractRoot = Join-Path $WorkRoot 'metacubexd'
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
    & $tar.Source -xzf $ArchivePath -C $extractRoot
    if ($LASTEXITCODE -ne 0) {
        throw "MetaCubeXD extraction failed with exit code $LASTEXITCODE"
    }

    $index = Get-ChildItem -LiteralPath $extractRoot -Recurse -File -Filter 'index.html' |
        Sort-Object FullName |
        Select-Object -First 1
    if (-not $index) {
        throw 'MetaCubeXD Web UI index.html was not found inside compressed-dist.tgz'
    }

    $sourceUi = Split-Path -Parent $index.FullName
    Backup-ExistingPath -Path $DestinationRoot -BackupRoot $BackupRoot
    if (Test-Path -LiteralPath $DestinationRoot) {
        Remove-Item -LiteralPath $DestinationRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
    Copy-Item -Path (Join-Path $sourceUi '*') -Destination $DestinationRoot -Recurse -Force
}

function Register-MihomoStartupTask {
    $action = New-ScheduledTaskAction -Execute $MihomoExe -Argument "-f `"$SafeProfilePath`"" -WorkingDirectory $InstallRoot
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1)

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
    Start-ScheduledTask -TaskName $TaskName
}

function Assert-Listener {
    param([Parameter(Mandatory)] [int]$Port)
    $listener = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -eq '127.0.0.1' -and $_.LocalPort -eq $Port } |
        Select-Object -First 1
    if (-not $listener) {
        throw "Expected listener was not found on 127.0.0.1:$Port"
    }
    Write-Host "listener_ok=127.0.0.1:$Port"
}

function Assert-HttpOk {
    param([Parameter(Mandatory)] [string]$Url)
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
    if ([int]$response.StatusCode -lt 200 -or [int]$response.StatusCode -ge 300) {
        throw "$Url returned HTTP $($response.StatusCode)"
    }
    Write-Host "http_ok=$Url status=$($response.StatusCode)"
}

Assert-Administrator
New-Item -ItemType Directory -Path $ProgramDataRoot, $InstallRoot, $SystemConfigRoot, $WorkRoot -Force | Out-Null
Start-Transcript -Path $LogPath -Append | Out-Null

try {
    $backupRoot = Join-Path $ProgramDataRoot ('backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))

    Write-Step 'Resolve official latest GitHub releases'
    $mihomoRelease = Invoke-GitHubApi -Uri 'https://api.github.com/repos/MetaCubeX/mihomo/releases/latest'
    $metacubeRelease = Invoke-GitHubApi -Uri 'https://api.github.com/repos/MetaCubeX/metacubexd/releases/latest'
    $mihomoAsset = Select-RequiredAsset -Release $mihomoRelease -Label 'mihomo Windows amd64' -Patterns @(
        '^mihomo-windows-amd64-v[0-9]+\.[0-9]+\.[0-9]+\.zip$',
        '^mihomo-windows-amd64-compatible-.*\.zip$',
        '^mihomo-windows-amd64.*\.zip$'
    )
    $metacubeAsset = Select-RequiredAsset -Release $metacubeRelease -Label 'MetaCubeXD Web UI' -Patterns @(
        '^compressed-dist\.tgz$'
    )
    Write-Host "mihomo_release=$($mihomoRelease.tag_name)"
    Write-Host "mihomo_asset=$($mihomoAsset.name)"
    Write-Host "metacubexd_release=$($metacubeRelease.tag_name)"
    Write-Host "metacubexd_asset=$($metacubeAsset.name)"

    Write-Step 'Download and verify release assets'
    $mihomoArchive = Join-Path $WorkRoot $mihomoAsset.name
    $metacubeArchive = Join-Path $WorkRoot $metacubeAsset.name
    Save-Download -Url $mihomoAsset.browser_download_url -Path $mihomoArchive
    Save-Download -Url $metacubeAsset.browser_download_url -Path $metacubeArchive
    Assert-FileDigest -Path $mihomoArchive -Digest $mihomoAsset.digest -Label 'mihomo'
    Assert-FileDigest -Path $metacubeArchive -Digest $metacubeAsset.digest -Label 'metacubexd'

    Write-Step 'Download and prepare mihomo profile'
    $downloadedProfile = Join-Path $WorkRoot 'mihomo-universal.yaml'
    Save-Download -Url $ProfileUrl -Path $downloadedProfile
    Backup-ExistingPath -Path $ProfilePath -BackupRoot $backupRoot
    Backup-ExistingPath -Path $SafeProfilePath -BackupRoot $backupRoot
    Write-ReviewedProfile -SourcePath $downloadedProfile -DestinationPath $ProfilePath

    Write-Step 'Install mihomo executable and MetaCubeXD Web UI'
    Stop-MihomoRuntime
    Backup-ExistingPath -Path $MihomoExe -BackupRoot $backupRoot
    Expand-MihomoAsset -ArchivePath $mihomoArchive -DestinationRoot $InstallRoot
    Expand-MetaCubeXDWebUi -ArchivePath $metacubeArchive -DestinationRoot $UiPath -BackupRoot $backupRoot

    Write-Step 'Validate and sync SYSTEM profile'
    & $MihomoExe -t -f $ProfilePath
    if ($LASTEXITCODE -ne 0) {
        throw "mihomo configuration validation failed with exit code $LASTEXITCODE"
    }
    Copy-Item -LiteralPath $ProfilePath -Destination $SafeProfilePath -Force
    & $MihomoExe -t -f $SafeProfilePath
    if ($LASTEXITCODE -ne 0) {
        throw "SYSTEM mihomo configuration validation failed with exit code $LASTEXITCODE"
    }

    Write-Step 'Register and start SYSTEM startup task'
    Register-MihomoStartupTask
    Start-Sleep -Seconds $StartupWaitSeconds

    Write-Step 'Verify local runtime'
    Assert-Listener -Port 7890
    Assert-Listener -Port 9090
    Assert-HttpOk -Url 'http://127.0.0.1:9090/version'
    Assert-HttpOk -Url 'http://127.0.0.1:9090/ui/'

    Write-Host ''
    Write-Host 'install_result=PASS'
    Write-Host 'dashboard_url=http://127.0.0.1:9090/ui/'
    Write-Host "profile_url=$ProfileUrl"
    Write-Host "log_path=$LogPath"
} finally {
    if (Test-Path -LiteralPath $WorkRoot) {
        Remove-Item -LiteralPath $WorkRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    Stop-Transcript | Out-Null
}
'''
    return script.replace("__PROFILE_URL__", profile_url).replace("\r\n", "\n")


def proxy_outbound_for_node(node: dict) -> dict:
    secrets = node["secrets"]
    return {
        "type": "vless",
        "tag": f"proxy_{node['name']}",
        "server": node_public_host(node),
        "server_port": public_vless_port(node),
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


def render_mihomo_process_routing_notes(repo_root: Path = REPO_ROOT) -> str:
    nodes = subscription_publishable_nodes(repo_root)
    aliases = ", ".join(str(node["subscription_alias"]) for node in nodes)
    process_sections = []
    for platform in ("windows", "macos", "linux"):
        direct_names = "\n".join(f"- `{name}`" for name in DIRECT_PROCESS_NAMES_BY_PLATFORM[platform])
        direct_paths = "\n".join(f"- `{path}`" for path in DIRECT_PROCESS_PATHS_BY_PLATFORM[platform])
        chatgpt_names = "\n".join(f"- `{name}`" for name in CHATGPT_PROCESS_NAMES_BY_PLATFORM[platform])
        chatgpt_paths = "\n".join(f"- `{path}`" for path in CHATGPT_PROCESS_PATHS_BY_PLATFORM[platform])
        proxy_paths = "\n".join(f"- `{path}`" for path in PROXY_PROCESS_PATHS_BY_PLATFORM[platform])
        if not proxy_paths:
            proxy_paths = "- none by default"
        observed_names = "\n".join(f"- `{name}`" for name in PROCESS_NAMES_BY_PLATFORM[platform])
        observed_paths = "\n".join(f"- `{path}`" for path in PROCESS_PATHS_BY_PLATFORM[platform])
        process_sections.append(
            f"""## {platform}

### ChatGPT process names (browser fingerprint)

{chatgpt_names}

### ChatGPT process paths (browser fingerprint)

{chatgpt_paths}

### DIRECT process names

{direct_names}

### DIRECT process paths

{direct_paths}

### Default process-level PROXY overrides

{proxy_paths}

### Observed app process names, not proxied by default

{observed_names}

### Observed app process paths, not proxied by default

{observed_paths}
"""
        )
    process_text = "\n".join(process_sections)
    return f"""# Clash Verge Rev / mihomo process routing notes

Generated for the GG proxy subscription service.

## Scope

- Published profile: `mihomo-universal.yaml`
- Node source: current enabled `Proxy_ops_private` inventory
- Published VLESS Reality nodes: {aliases}
- Ruleset source: `DustinWin/ruleset_geodata` release asset `mihomo-ruleset`
- TUN mode: enabled with `auto-route`, `auto-redirect`, `strict-route`, and DNS hijack for `any:53`

## Evidence and assumptions

- Local Windows evidence on this workstation showed multiple `Codex.exe` desktop processes and multiple `codex.exe` CLI helper processes under the OpenAI Codex app package and user-local Codex bin directory.
- Browser and WebView fingerprint traffic (Chrome / Edge / Firefox / Brave / Safari / Simprint Chrome profile / ChatGPT desktop) is process-routed to the `ChatGPT` group so HTTP and WebRTC/STUN share the QQPW residential exit.
- Official OpenAI / ChatGPT / Codex domains are high-priority `ChatGPT` group rules: {", ".join(f"`{domain}`" for domain in OPENAI_PROXY_DOMAIN_SUFFIXES)}. The ChatGPT group defaults to `QQPW-Residential-Reality` (WG residential VLESS). `QQPW-Residential-Hysteria2` is optional. Other nodes remain selectable in that group.
- General non-browser traffic uses the `PROXY` group (default `Auto` over non-QQPW nodes). QQPW exits remain selectable there too.
- Codex CLI/desktop install paths remain `DIRECT` fallbacks for non-OpenAI destinations after official domain rules.
- Antigravity install paths remain process-level `PROXY` overrides (developer tooling, not browser fingerprint).
- `codexsdk`, `antigravitysdk`, and `cursorsdk` are SDK/library usage patterns, not stable standalone processes. Generic host processes such as `node` and `python` are not process-proxied by default; destination rules decide whether traffic is direct or proxied.
- `mihomo-universal.yaml` merges the Windows, macOS, and Linux process rules into one file. Rules for executables or paths that do not exist on the current OS are expected to miss, not to run or launch anything.
- Cursor domain rules are the highest-priority DIRECT rules and are evaluated before process rules, so Cursor destinations stay direct no matter which app opens them. The first rule is fuzzy `DOMAIN-KEYWORD,cursor,DIRECT`, followed by explicit suffixes: `cursor.sh`, `cursor.com`, `cursorapi.com`, `cursor-cdn.com`, `anysphere.co`, and `anysphere.inc`.
- Cursor is also protected by DIRECT process rules in this profile.
- WPS / Kingsoft domain rules are evaluated after Cursor and before process rules. The first rule is `DOMAIN-KEYWORD,kingsoft,DIRECT`, followed by suffixes: {", ".join(f"`{domain}`" for domain in WPS_DIRECT_DOMAIN_SUFFIXES)}.
- WPS Office, cloud sync (`wpscloudsvr.exe`), and update helpers are also protected by DIRECT process/path rules on Windows.
- Domestic APT and container registry mirrors are DIRECT and exempt from fake-ip so WSL apt/podman and local package workflows resolve real addresses. Covered suffixes: {", ".join(f"`{domain}`" for domain in MIRROR_DIRECT_DOMAIN_SUFFIXES)}.
- Domestic platform domains are DIRECT and exempt from fake-ip so SSH/Git to self-hosted services resolve real addresses. Covered suffixes: {", ".join(f"`{domain}`" for domain in DOMESTIC_PLATFORM_DIRECT_DOMAIN_SUFFIXES)}.
- `ssh` / `git` processes are DIRECT on all platforms so Git-over-SSH and shell access do not break on fake-ip destinations.

## Domestic platform DIRECT rules

{chr(10).join(f"- `DOMAIN-SUFFIX,{domain},DIRECT`" for domain in DOMESTIC_PLATFORM_DIRECT_DOMAIN_SUFFIXES)}

## Domestic mirror DIRECT rules

{chr(10).join(f"- `DOMAIN-SUFFIX,{domain},DIRECT`" for domain in MIRROR_DIRECT_DOMAIN_SUFFIXES)}

## WPS / Kingsoft domain DIRECT rules

- `DOMAIN-KEYWORD,kingsoft,DIRECT`
{chr(10).join(f"- `DOMAIN-SUFFIX,{domain},DIRECT`" for domain in WPS_DIRECT_DOMAIN_SUFFIXES)}

## Direct process protections

Private and mainland China direct guardrails are evaluated before proxy rules. That is intentional for TUN rule mode: domestic CDN traffic, local China apps, Cursor, WPS, and generic runtimes should stay `DIRECT` when they hit China/private rule providers. Browsers are process-routed to `ChatGPT`. The final fallback is `MATCH,PROXY`, so non-mainland non-browser destinations are proxied for mainland China users.

{process_text}
## Operational notes

- Import `mihomo-universal.yaml` into Clash Verge Rev as the remote profile for Windows, macOS, and Linux.
- Enable Clash Verge Rev service mode/admin permissions before enabling TUN.
- Keep the subscription host direct so profile updates do not depend on the proxy path.
- If a China app unexpectedly uses the proxy, inspect the destination and add a narrow DIRECT process/path or domain rule. Do not add broad shared-runtime proxy rules.
"""


def render_subscription_container_config(repo_root: Path = REPO_ROOT) -> str:
    publish = publish_config(repo_root)
    remote_public_root = str(publish.get("remote_public_root") or "/srv/proxy-subscriptions/public")
    subscription_host = public_subscriptions_host(repo_root)
    return f"""[Unit]
Description=GG Proxy Subscriptions Static Service
After=network-online.target
Wants=network-online.target

[Container]
Image={SUBSCRIPTION_CONTAINER_IMAGE}
ContainerName={SUBSCRIPTION_CONTAINER_NAME}
Exec={SUBSCRIPTION_CONTAINER_COMMAND}
Volume={remote_public_root}:/www:ro,Z
Label=traefik.enable=true
Label=traefik.http.routers.sea-subs.rule=Host(`{subscription_host}`)
Label=traefik.http.routers.sea-subs.entrypoints=websecure
Label=traefik.http.routers.sea-subs.tls=true
Label=traefik.http.routers.sea-subs.tls.certresolver={SUBSCRIPTION_TRAEFIK_CERT_RESOLVER}
Label=traefik.http.routers.sea-subs.service=sea-subs
Label=traefik.http.services.sea-subs.loadbalancer.server.port={SUBSCRIPTION_CONTAINER_PORT}

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
"""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_subscription_publish_manifest(repo_root: Path = REPO_ROOT) -> str:
    subscriptions = load_subscriptions_config(repo_root / "inventory" / "subscriptions.yaml")
    publish = publish_config(repo_root)
    subscriptions_dir = repo_root / "generated" / "subscriptions"
    config_path = repo_root / "generated" / "publish" / "sea-bgp" / f"{SUBSCRIPTION_CONTAINER_NAME}.container"
    generated_files = []
    for path in sorted(subscriptions_dir.glob("*")):
        if path.is_file():
            generated_files.append(
                {
                    "path": str(path.relative_to(repo_root)).replace("\\", "/"),
                    "sha256": _sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    payload = {
        "schema": "gg.proxy.subscription.publish.v1",
        "source": "repos/proxy_ops_private/scripts/render_artifacts.py",
        "subscription_base_url": subscriptions["subscription_base_url"],
        "publish_node": publish.get("node"),
        "remote_public_root": publish.get("remote_public_root"),
        "remote_subscriptions_dir": publish.get("remote_subscriptions_dir"),
        "remote_config_dir": publish.get("remote_config_dir"),
        "remote_container_config": publish.get("remote_container_config"),
        "container_config": {
            "path": str(config_path.relative_to(repo_root)).replace("\\", "/"),
            "sha256": _sha256_file(config_path),
            "container_name": SUBSCRIPTION_CONTAINER_NAME,
            "image": SUBSCRIPTION_CONTAINER_IMAGE,
            "command": SUBSCRIPTION_CONTAINER_COMMAND,
            "traefik_host": public_subscriptions_host(repo_root),
        },
        "published_nodes": [str(node["subscription_alias"]) for node in subscription_publishable_nodes(repo_root)],
        "generated_files": generated_files,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def remove_legacy_mihomo_platform_profiles(repo_root: Path = REPO_ROOT) -> None:
    subscriptions_dir = repo_root / "generated" / "subscriptions"
    for filename in ("mihomo-windows.yaml", "mihomo-macos.yaml", "mihomo-linux.yaml"):
        path = subscriptions_dir / filename
        if path.exists():
            path.unlink()


def remove_legacy_import_deep_link_files(repo_root: Path = REPO_ROOT) -> None:
    subscriptions_dir = repo_root / "generated" / "subscriptions"
    for path in subscriptions_dir.glob("*_import*.txt"):
        path.unlink()


def prune_stale_single_node_subscriptions(repo_root: Path = REPO_ROOT) -> None:
    subscriptions_dir = repo_root / "generated" / "subscriptions"
    eligible_names = {str(node["name"]) for node in subscription_publishable_nodes(repo_root)}
    eligible_names.update(
        str(entry["filename"]) for entry in extra_single_node_subscriptions(repo_root)
    )
    for path in subscriptions_dir.glob("v2ray_node_*.txt"):
        node_name = path.name.removeprefix("v2ray_node_").removesuffix(".txt")
        if node_name not in eligible_names:
            path.unlink()


def render_extra_single_node_subscription(repo_root: Path, entry: dict) -> str:
    links = subscription_links_for_extra_entry(repo_root, entry)
    if not links:
        return ""
    return "\n".join(links) + "\n"


def write_generated_artifacts(repo_root: Path = REPO_ROOT) -> None:
    refresh_availability(repo_root)
    eligible = subscription_publishable_nodes(repo_root)
    ensure_minimum_published_nodes(repo_root, eligible)
    report = exclusion_report(repo_root)
    if report.excluded or report.pending:
        print(
            "[INFO] subscription availability: "
            f"eligible={len(eligible)} excluded={report.excluded} pending={report.pending}"
        )

    remove_legacy_mihomo_platform_profiles(repo_root)
    remove_legacy_import_deep_link_files(repo_root)
    write_text(repo_root / "generated" / "subscriptions" / "index.html", render_subscription_landing_page(repo_root))
    write_text(repo_root / "generated" / "subscriptions" / "v2ray_nodes.txt", render_v2ray_subscription(repo_root))
    for node in eligible:
        write_text(
            repo_root / "generated" / "subscriptions" / single_node_subscription_filename(node["name"]),
            render_v2ray_subscription(repo_root, node_name=node["name"]),
        )
    for entry in extra_single_node_subscriptions(repo_root):
        write_text(
            repo_root / "generated" / "subscriptions" / extra_single_node_subscription_filename(str(entry["filename"])),
            render_extra_single_node_subscription(repo_root, entry),
        )
    prune_stale_single_node_subscriptions(repo_root)
    singbox_manifest = render_singbox_remote_profile(repo_root)
    write_text(repo_root / "generated" / "subscriptions" / "singbox-client-profile.json", singbox_manifest)
    write_text(repo_root / "generated" / "subscriptions" / "singbox_remote_profile.json", render_singbox_remote_profile(repo_root))
    write_text(repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml", render_mihomo_config(repo_root, platform="universal"))
    write_text(
        repo_root / "generated" / "subscriptions" / "install-mihomo-windows.ps1",
        render_windows_mihomo_install_script(repo_root),
    )
    write_text(
        repo_root / "generated" / "subscriptions" / "mihomo-process-routing.md",
        render_mihomo_process_routing_notes(repo_root),
    )
    write_text(
        repo_root / "generated" / "publish" / "sea-bgp" / f"{SUBSCRIPTION_CONTAINER_NAME}.container",
        render_subscription_container_config(repo_root),
    )
    write_text(
        repo_root / "generated" / "publish" / "sea-bgp" / "subscription-publish-manifest.json",
        render_subscription_publish_manifest(repo_root),
    )


def main() -> None:
    write_generated_artifacts(REPO_ROOT)


if __name__ == "__main__":
    main()
