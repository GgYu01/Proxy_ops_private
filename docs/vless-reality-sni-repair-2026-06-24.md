# VLESS/Reality SNI Repair - 2026-06-24

## Root Cause

`dedirock` and `us_sea_bgp_01` had reachable TCP `10003`, working local HTTP/SOCKS proxy egress, and working direct OpenAI egress, but external VLESS/Reality clients failed with TLS EOF and server logs showed:

`TLS handshake: REALITY: processed invalid connection`

The failure was isolated to the Reality handshake target. A temporary SNI matrix on `dedirock` showed `www.microsoft.com` and `microsoft.com` failing, while `www.cloudflare.com`, `www.apple.com`, and `www.bing.com` returned OpenAI HTTP `401` through VLESS/Reality. The durable fix is to use `www.cloudflare.com:443` as the Reality handshake target and `www.cloudflare.com` as the client SNI.

## Applied Configuration

- Inventory fields:
  - `reality_dest=www.cloudflare.com:443`
  - `reality_server_names=www.cloudflare.com`
- Published nodes:
  - `GG-US-SEA-BGP-01`
  - `GG-Vmrack1`
  - `GG-Dedirock`
- Published endpoint:
  - `https://subs.sea.prod.gglohh.top/subscriptions`

## Verification Evidence

- `reconcile_subscription_node_availability.py --probe` marked all three published nodes healthy:
  - `us_sea_bgp_01`: `proxy=ok (attempt1: httpx openai proxy http status=401)`
  - `vmrack1`: `proxy=ok (attempt1: httpx openai proxy http status=401)`
  - `dedirock`: `proxy=ok (attempt1: httpx openai proxy http status=401)`
- `mihomo-universal.yaml` syntax passed with `C:\Tools\mihomo\mihomo-windows-amd64.exe -t`.
- Published `mihomo-universal.yaml` and `v2ray_nodes.txt` contain only the three healthy nodes and all use `sni=www.cloudflare.com`.
- Local SYSTEM mihomo was refreshed and returned OpenAI HTTP `401` through `127.0.0.1:7890`; `PROXY` selected `GG-US-SEA-BGP-01`.

## Residual Log Noise

After the fix, `us_sea_bgp_01` still received bursts of `REALITY: processed invalid connection` from the same NAT public source while successful VLESS/Reality OpenAI traffic also worked. A short isolation test stopped local SYSTEM mihomo for 12 seconds; the invalid connections continued during that window. That means the residual log noise is not caused by the refreshed local SYSTEM mihomo or the newly published subscription artifact.

Treat future `REALITY: processed invalid connection` lines as a failure only when paired with a failed real VLESS/Reality OpenAI probe for that same client/profile. TCP reachability and raw TLS logs alone are not sufficient health signals.
