import json
import os
import uuid

def load_env_file(filepath):
    config = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    config[key.strip()] = value.strip()
    return config

def main():
    config = load_env_file('config.env')
    
    # Defaults
    base_port = int(config.get('BASE_PORT', 10000))
    user = config.get('PROXY_USER', 'admin')
    password = config.get('PROXY_PASS', 'password')
    # Backward compatibility: Check VLESS_UUID first, then VMess
    vmess_uuid = config.get('VLESS_UUID') or config.get('VMESS_UUID') or str(uuid.uuid4())
    ss_method = config.get('SS_METHOD', 'chacha20-ietf-poly1305')
    ss_pass = config.get('SS_PASSWORD', 'secret')
    
    # Reality Config
    reality_priv = config.get('REALITY_PRIVATE_KEY')
    reality_short_id = config.get('REALITY_SHORT_ID', '')
    reality_dest = config.get('REALITY_DEST', 'www.microsoft.com:443')
    reality_sn = config.get('REALITY_SERVER_NAMES', 'www.microsoft.com').split(',')

    # Validation: If Reality is enabled (implied by default), check for Private Key
    # We allow reality_priv to be empty ONLY if we fall back to a non-Reality config, 
    # but our design enforces Reality for VLESS.
    if not reality_priv:
        print("❌ ERROR: REALITY_PRIVATE_KEY is missing in config.env!")
        print("   Solution 1: Run './scripts/gen_keys.sh' to auto-generate keys.")
        print("   Solution 2: Paste your own keys into config.env.")
        exit(1)

    print(f"Generating config with Base Port: {base_port}")
    
    sb_config = {
        "log": {
            "level": "info",
            "timestamp": True
        },
        "dns": {
            "servers": [
                {"tag": "google", "address": "8.8.8.8"},
                {"tag": "local", "address": "local"}
            ],
            "strategy": "ipv4_only"
        },
        "inbounds": [
            # 1. SOCKS5 (Local/Debug)
            {
                "type": "socks",
                "tag": "socks-in",
                "listen": "::",
                "listen_port": base_port,
                "users": [{"username": user, "password": password}]
            },
            # 2. HTTP (Local/Debug)
            {
                "type": "http",
                "tag": "http-in",
                "listen": "::",
                "listen_port": base_port + 1,
                "users": [{"username": user, "password": password}]
            },
            # 3. Shadowsocks (Low Mem, High Speed)
            {
                "type": "shadowsocks",
                "tag": "ss-in",
                "listen": "::",
                "listen_port": base_port + 2,
                "method": ss_method,
                "password": ss_pass
            },
            # 4. VLESS + Reality (Stealth King)
            {
                "type": "vless",
                "tag": "vless-in",
                "listen": "::",
                "listen_port": base_port + 3,
                "users": [{"uuid": vmess_uuid, "flow": "xtls-rprx-vision"}],
                "tls": {
                    "enabled": True,
                    "server_name": reality_sn[0],
                    "reality": {
                        "enabled": True,
                        "handshake": {
                            "server": reality_dest,
                            "server_port": 443
                        },
                        "private_key": reality_priv,
                        "short_id": [reality_short_id]
                    }
                } if reality_priv else None
            },
            # 5. Trojan (HTTPS Camouflage, Stability)
            {
                "type": "trojan",
                "tag": "trojan-in",
                "listen": "::",
                "listen_port": base_port + 4,
                "users": [{"password": password}]
            }
        ],
        "outbounds": [
            {
                "type": "direct", 
                "tag": "direct",
                # Stealth: Use system stack to mimic standard OS traffic
                "domain_strategy": "ipv4_only" 
            },
            {"type": "block", "tag": "block"}
        ]
    }
    
    with open('singbox.json', 'w') as f:
        json.dump(sb_config, f, indent=2)
    
    print("[OK] singbox.json generated successfully.")

if __name__ == '__main__':
    main()
