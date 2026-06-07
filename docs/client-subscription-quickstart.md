# 当前订阅接入速查

## 一句话结论

当前权威客户端入口是 LisaHost SEA BGP 临时宿主上的 HTTP 订阅：

- `http://69.5.53.82:18080/subscriptions`

节点池为 **六节点**，故障转移优先级以 `us_sea_bgp_01` / `GG-US-SEA-BGP-01` 为首。

原 infra-core Traefik 域名 `:27111` 已随 `112.28.134.53` 主机退役，**不得**再作为客户端主入口。

## 适用范围

这份文档描述当前订阅入口的使用方式，适用于：

- LisaHost SEA BGP（`69.5.53.82`）上由 `gg-proxy-subscriptions-http.service` 提供的静态订阅站
- 六节点池：`us_sea_bgp_01`、`Lisahost`、`Lisahost-KR`、`vmrack1`、`vmrack2`、`dedirock`
- Windows / Linux / macOS 客户端直接导入 `mihomo-universal.yaml` 或 VLESS 订阅

## 当前权威入口

- 多节点总订阅 URL
  - `http://69.5.53.82:18080/subscriptions/v2ray_nodes.txt`
- Clash Verge Rev / mihomo universal profile
  - `http://69.5.53.82:18080/subscriptions/mihomo-universal.yaml`
- 进程路由说明
  - `http://69.5.53.82:18080/subscriptions/mihomo-process-routing.md`
- sing-box Remote Profile 清单
  - `http://69.5.53.82:18080/subscriptions/singbox-client-profile.json`

单节点订阅 URL（示例）：

- `GG-US-SEA-BGP-01`
  - `http://69.5.53.82:18080/subscriptions/v2ray_node_us_sea_bgp_01.txt`
- `GG-Lisa-Stable`
  - `http://69.5.53.82:18080/subscriptions/v2ray_node_lisahost.txt`
- `GG-Lisahost-KR`
  - `http://69.5.53.82:18080/subscriptions/v2ray_node_lisahost_kr.txt`

完整列表见 landing 页：`http://69.5.53.82:18080/`

## 已退役入口（勿用）

- `https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/*`
- 任何指向 `112.28.134.53` 或 `/mnt/hdo/infra-core` 的发布/运维路径

## 节点优先级

与 `inventory/subscriptions.yaml` 中 `failover_priority` 一致：

1. `us_sea_bgp_01` / `GG-US-SEA-BGP-01`
2. `lisahost` / `GG-Lisa-Stable`
3. `lisahost_kr` / `GG-Lisahost-KR`
4. `vmrack1` / `GG-Vmrack1`
5. `vmrack2` / `GG-Vmrack2`
6. `dedirock` / `GG-Dedirock`

## 发布订阅（运维）

在本地生成产物后：

```bash
python3 scripts/render_artifacts.py
bash scripts/publish_subscriptions_to_sea_host.sh --dry-run
REMOTE_PASSWORD='...' bash scripts/publish_subscriptions_to_sea_host.sh
```

旧脚本 `publish_subscriptions_to_infra_core.sh` 仅为兼容 wrapper，会委托到新脚本。

## 验证

```bash
curl -fsS http://69.5.53.82:18080/subscriptions/v2ray_nodes.txt | head -1
curl -fsS http://69.5.53.82:18080/subscriptions/mihomo-universal.yaml | grep -E 'wps.cn|wps.exe'
```

Windows 本机路由验收见根仓 `scripts/windows/accept-mihomo-windows.ps1`。

## 相关 ADR

- [ADR-0020](../../docs/adr/ADR-0020-sea-bgp-temporary-subscription-host.md) — infra-core 退役与 SEA BGP 临时订阅宿主
