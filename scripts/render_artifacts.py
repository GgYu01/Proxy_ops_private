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
    "macos": [
        "/Applications/Safari.app/Contents/*",
        "/System/Applications/Safari.app/Contents/*",
    ],
    "linux": [],
}

DIRECT_PROCESS_NAMES_BY_PLATFORM = {
    "windows": [
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
        r"C:\Program Files\Microsoft\Edge Beta\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge Beta\Application\msedge.exe",
        r"C:\Users\*\AppData\Local\Microsoft\Edge Beta\Application\msedge.exe",
        r"C:\Users\*\AppData\Local\Programs\Cursor\*",
        r"C:\Users\*\AppData\Local\Kingsoft\WPS Office\*",
        r"C:\Users\*\AppData\Local\OpenAI\Codex\bin\*\codex.exe",
        r"C:\Program Files\WindowsApps\OpenAI.Codex_*\app\*",
        r"C:\Program Files\OpenAI\ChatGPT\*",
        r"C:\Users\*\AppData\Local\Programs\ChatGPT\*",
        r"C:\Program Files\OpenAI\ChatGPT Atlas\*",
        r"C:\Users\*\AppData\Local\Programs\ChatGPT Atlas\*",
    ],
    "macos": [
        "/Applications/Cursor.app/Contents/*",
        "/Applications/ChatGPT.app/Contents/*",
        "/Applications/ChatGPT Atlas.app/Contents/*",
        "/Applications/Codex.app/Contents/*",
        "/Users/*/Applications/ChatGPT.app/Contents/*",
        "/Users/*/Applications/ChatGPT Atlas.app/Contents/*",
        "/Users/*/Applications/Codex.app/Contents/*",
    ],
    "linux": [
        "/usr/bin/cursor*",
        "/opt/chatgpt/*",
        "/usr/bin/chatgpt*",
        "/opt/chatgpt-atlas/*",
        "/usr/bin/chatgpt-atlas*",
        "/usr/bin/chatgptatlas*",
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
        r"C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\chrome_proxy.exe",
        r"C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\simprint.exe",
        r"C:\Program Files\Google\Antigravity\*",
        r"C:\Program Files\Google\Antigravity*\*",
        r"C:\Users\*\AppData\Local\Programs\Antigravity\*",
    ],
    "macos": [
        "/Applications/Antigravity.app/Contents/*",
        "/Users/*/Applications/Antigravity.app/Contents/*",
        "/Applications/Microsoft Edge.app/Contents/*",
        "/Users/*/Applications/Microsoft Edge.app/Contents/*",
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


def vless_link(node: dict) -> str:
    host = node_public_host(node)
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


def mihomo_proxy_for_node(node: dict) -> dict:
    secrets = node["secrets"]
    return {
        "name": str(node["subscription_alias"]),
        "type": "vless",
        "server": node_public_host(node),
        "port": int(node["base_port"]) + 3,
        "uuid": secrets["VLESS_UUID"],
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
        ],
        "default-nameserver": ["223.5.5.5", "119.29.29.29"],
        "nameserver": ["https://dns.alidns.com/dns-query", "https://doh.pub/dns-query"],
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
    openai_domain_help = """# === OFFICIAL OPENAI / CHATGPT DOMAIN PROXY RULES ===
# Only official OpenAI-family destination domains are forced through PROXY.
# Do not add broad DOMAIN-KEYWORD,openai/codex/openaiapi rules; those would
# over-route OpenAI-compatible relay domains.
# === END OFFICIAL OPENAI / CHATGPT DOMAIN PROXY RULES ===
"""
    pre_domain_process_help = """# === HIGHEST PRIORITY PROCESS DIRECT EXCEPTIONS ===
# These process exceptions intentionally run before OpenAI/ChatGPT domain
# proxy rules. Safari is kept DIRECT even when it opens official OpenAI-family
# destinations; use Microsoft Edge for browser-wide PROXY behavior on macOS.
# === END HIGHEST PRIORITY PROCESS DIRECT EXCEPTIONS ===
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
# Microsoft China, Google China, QQ/WeChat/Cursor/Edge Beta, WPS Office /
# cloud sync / update, OpenAI-family desktop app non-OpenAI destinations, and
# subscription update traffic stay DIRECT; non-mainland fallback traffic uses
# PROXY.
# To stop protecting one DIRECT process, comment out its line. Keep these
# process rules explicit and predictable.
"""
    direct_end_help = """# === END USER-EDITABLE PROCESS DIRECT PROTECTIONS ===
# === USER-EDITABLE PROCESS PROXY OVERRIDES ===
# These narrow PROXY overrides target Simprint's Chrome profile browser plus
# selected non-OpenAI developer desktop app install paths: Antigravity.
# OpenAI-family desktop app paths are DIRECT fallbacks; official OpenAI domains
# are proxied by destination rules above. These overrides deliberately do not
# target shared runtimes such as msedgewebview2.exe, node, or python.
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
    first_openai_domain_rule = "- DOMAIN-SUFFIX,openai.com,PROXY"
    first_pre_domain_process_rule = "- PROCESS-PATH-WILDCARD,/Applications/Safari.app/Contents/*,DIRECT"
    if first_pre_domain_process_rule in yaml_text:
        yaml_text = yaml_text.replace(
            first_pre_domain_process_rule,
            pre_domain_process_help + first_pre_domain_process_rule,
            1,
        )
    if first_openai_domain_rule in yaml_text:
        yaml_text = yaml_text.replace(first_openai_domain_rule, openai_domain_help + first_openai_domain_rule, 1)
    first_wps_domain_rule = "- DOMAIN-KEYWORD,kingsoft,DIRECT"
    if first_wps_domain_rule in yaml_text:
        yaml_text = yaml_text.replace(first_wps_domain_rule, wps_domain_help + first_wps_domain_rule, 1)
    first_process_rule = "- PROCESS-NAME,"
    if first_process_rule in yaml_text:
        yaml_text = yaml_text.replace(first_process_rule, process_help + first_process_rule, 1)
    first_proxy_rule = r"- PROCESS-PATH-WILDCARD,C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\chrome_proxy.exe,PROXY"
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


def mihomo_openai_domain_proxy_rules() -> list[str]:
    return [f"DOMAIN-SUFFIX,{domain},PROXY" for domain in OPENAI_PROXY_DOMAIN_SUFFIXES]


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


def render_mihomo_config(repo_root: Path = REPO_ROOT, *, platform: str) -> str:
    nodes = subscription_publishable_nodes(repo_root)
    proxy_names = [str(node["subscription_alias"]) for node in nodes]
    default_proxy = "PROXY"
    subscription_host = public_subscriptions_host(repo_root)
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
        "proxies": [mihomo_proxy_for_node(node) for node in nodes],
        "proxy-groups": [
            {
                "name": "PROXY",
                "type": "select",
                "proxies": [*proxy_names[:1], "Auto", *proxy_names[1:], "DIRECT"],
            },
            {
                "name": "Auto",
                "type": "url-test",
                "proxies": proxy_names,
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 80,
            },
        ],
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
            *mihomo_wps_domain_direct_rules(),
            *mihomo_direct_process_rules(platform),
            *mihomo_proxy_process_rules(platform),
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
    return "\n".join(vless_link(node) for node in nodes) + "\n"


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

    node_sections: list[str] = []
    availability = exclusion_report(repo_root)
    pending_names = set(availability.pending)
    for index, node in enumerate(subscription_publishable_nodes(repo_root), start=1):
        node_name = str(node["name"])
        alias = html.escape(str(node["subscription_alias"]))
        provider = html.escape(str(node.get("provider", "unknown")))
        pending_note = " · 探测异常，暂仍发布" if node_name in pending_names else ""
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
                    f"          <p>{provider} · VLESS Reality · 端口 {int(node['base_port']) + 3}{pending_note}</p>",
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

    node_links_html = "\n".join(node_sections)
    multi_node_url_html = html.escape(multi_node_url)
    singbox_url_html = html.escape(singbox_url)
    mihomo_universal_url_html = html.escape(base_url + "/mihomo-universal.yaml")
    mihomo_process_notes_url_html = html.escape(base_url + "/mihomo-process-routing.md")

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


def proxy_outbound_for_node(node: dict) -> dict:
    secrets = node["secrets"]
    return {
        "type": "vless",
        "tag": f"proxy_{node['name']}",
        "server": node_public_host(node),
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


def render_mihomo_process_routing_notes(repo_root: Path = REPO_ROOT) -> str:
    nodes = subscription_publishable_nodes(repo_root)
    aliases = ", ".join(str(node["subscription_alias"]) for node in nodes)
    process_sections = []
    for platform in ("windows", "macos", "linux"):
        direct_names = "\n".join(f"- `{name}`" for name in DIRECT_PROCESS_NAMES_BY_PLATFORM[platform])
        direct_paths = "\n".join(f"- `{path}`" for path in DIRECT_PROCESS_PATHS_BY_PLATFORM[platform])
        proxy_paths = "\n".join(f"- `{path}`" for path in PROXY_PROCESS_PATHS_BY_PLATFORM[platform])
        if not proxy_paths:
            proxy_paths = "- none by default"
        observed_names = "\n".join(f"- `{name}`" for name in PROCESS_NAMES_BY_PLATFORM[platform])
        observed_paths = "\n".join(f"- `{path}`" for path in PROCESS_PATHS_BY_PLATFORM[platform])
        process_sections.append(
            f"""## {platform}

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
- Browser and WebView runtimes such as Edge Beta, `msedge.exe`, and `msedgewebview2.exe` are intentionally not process-proxied by default because that over-routes unrelated browsing. They use `PROXY` only when destination rules require it.
- Official OpenAI / ChatGPT / Codex domains are high-priority `PROXY` rules: {", ".join(f"`{domain}`" for domain in OPENAI_PROXY_DOMAIN_SUFFIXES)}. This covers ChatGPT/Codex WebSocket traffic to `chatgpt.com` without broad keyword rules.
- OpenAI-family desktop app paths are `DIRECT` fallbacks after those official domain rules. That prevents Codex Desktop, ChatGPT, or ChatGPT Atlas non-OpenAI destinations such as Google push channels from being dragged into `MATCH,PROXY` by process identity.
- On macOS, Safari app paths are high-priority `DIRECT` process exceptions before official OpenAI domain rules. Use Microsoft Edge when browser-wide `PROXY` behavior is required.
- Antigravity, macOS Microsoft Edge, and Simprint Chrome profile paths are default process-level `PROXY` overrides. Simprint rules target the Chromium browser Simprint launches, not `C:\\Users\\...\\Simprint\\simprint.exe`, not `C:\\Users\\...\\Simprint\\simprint-runtime.exe`, and not Simprint's fixed WebView2 UI runtime.
- `codexsdk`, `antigravitysdk`, and `cursorsdk` are SDK/library usage patterns, not stable standalone processes. Generic host processes such as `node` and `python` are not process-proxied by default; destination rules decide whether traffic is direct or proxied.
- `mihomo-universal.yaml` merges the Windows, macOS, and Linux process rules into one file. Rules for executables or paths that do not exist on the current OS are expected to miss, not to run or launch anything.
- Antigravity, ChatGPT, ChatGPT Atlas, Codex, Simprint, and stable Microsoft Edge can spawn helper, renderer, GPU, plugin, update, and CLI processes. The default profile uses narrow app install path rules only where process identity is the right control; OpenAI-family apps remain destination-rule based with DIRECT app fallbacks.
- Cursor domain rules are the highest-priority DIRECT rules and are evaluated before process rules, so Cursor destinations stay direct no matter which app opens them. The first rule is fuzzy `DOMAIN-KEYWORD,cursor,DIRECT`, followed by explicit suffixes: `cursor.sh`, `cursor.com`, `cursorapi.com`, `cursor-cdn.com`, `anysphere.co`, and `anysphere.inc`.
- Cursor is also protected by DIRECT process rules in this profile.
- WPS / Kingsoft domain rules are evaluated after Cursor and before process rules. The first rule is `DOMAIN-KEYWORD,kingsoft,DIRECT`, followed by suffixes: {", ".join(f"`{domain}`" for domain in WPS_DIRECT_DOMAIN_SUFFIXES)}.
- WPS Office, cloud sync (`wpscloudsvr.exe`), and update helpers are also protected by DIRECT process/path rules on Windows.

## WPS / Kingsoft domain DIRECT rules

- `DOMAIN-KEYWORD,kingsoft,DIRECT`
{chr(10).join(f"- `DOMAIN-SUFFIX,{domain},DIRECT`" for domain in WPS_DIRECT_DOMAIN_SUFFIXES)}

## Direct process protections

Private and mainland China direct guardrails are evaluated before proxy rules. That is intentional for TUN rule mode: domestic CDN traffic, local China apps, Edge Beta, Cursor, WebView2, Safari, and generic runtimes should stay `DIRECT` when they hit China/private rule providers. The final fallback is `MATCH,PROXY`, so non-mainland destinations are proxied for mainland China users.

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
    for path in subscriptions_dir.glob("v2ray_node_*.txt"):
        node_name = path.name.removeprefix("v2ray_node_").removesuffix(".txt")
        if node_name not in eligible_names:
            path.unlink()


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
    prune_stale_single_node_subscriptions(repo_root)
    singbox_manifest = render_singbox_remote_profile(repo_root)
    write_text(repo_root / "generated" / "subscriptions" / "singbox-client-profile.json", singbox_manifest)
    write_text(repo_root / "generated" / "subscriptions" / "singbox_remote_profile.json", render_singbox_remote_profile(repo_root))
    write_text(repo_root / "generated" / "subscriptions" / "mihomo-universal.yaml", render_mihomo_config(repo_root, platform="universal"))
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
