# 当前订阅接入速查

## 一句话结论

当前权威客户端入口是 SEA gateway 域名 HTTPS 订阅：

- `https://subs.sea.prod.gglohh.top/subscriptions`

节点池仍由 `inventory/subscriptions.yaml` 的 `failover_priority` 排序；发布产物只包含真实 VLESS/Reality 代理探测通过的节点。原 infra-core Traefik 域名 `:27111` 已随 `112.28.134.53` 主机退役，不得再作为客户端主入口。

## 适用范围

这份文档描述当前订阅入口的使用方式，适用于：

- LisaHost SEA BGP 上由 native Podman `sea-gateway` + Traefik 发现的 `gg-proxy-subscriptions` 静态订阅站
- 六节点池：`us_sea_bgp_01`、`lisahost`、`lisahost_kr`、`vmrack1`、`vmrack2`、`dedirock`
- Windows / Linux / macOS 客户端直接导入 `mihomo-universal.yaml` 或 VLESS 订阅

## 当前权威入口

- 多节点总订阅 URL
  - `https://subs.sea.prod.gglohh.top/subscriptions/v2ray_nodes.txt`
- Clash Verge Rev / mihomo universal profile
  - `https://subs.sea.prod.gglohh.top/subscriptions/mihomo-universal.yaml`
- 进程路由说明
  - `https://subs.sea.prod.gglohh.top/subscriptions/mihomo-process-routing.md`
- sing-box Remote Profile 清单
  - `https://subs.sea.prod.gglohh.top/subscriptions/singbox-client-profile.json`

单节点订阅 URL 示例：

- `GG-US-SEA-BGP-01`
  - `https://subs.sea.prod.gglohh.top/subscriptions/v2ray_node_us_sea_bgp_01.txt`
- `GG-Vmrack1`
  - `https://subs.sea.prod.gglohh.top/subscriptions/v2ray_node_vmrack1.txt`
- `GG-Dedirock`
  - `https://subs.sea.prod.gglohh.top/subscriptions/v2ray_node_dedirock.txt`

完整列表见 landing 页：`https://subs.sea.prod.gglohh.top/`

## 已退役入口

- `https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/*`
- 任何指向 `112.28.134.53` 或 `/mnt/hdo/infra-core` 的发布/运维路径
- 不要恢复 IP+HTTP 端口订阅入口

## 节点优先级

与 `inventory/subscriptions.yaml` 中 `failover_priority` 一致：

1. `us_sea_bgp_01` / `GG-US-SEA-BGP-01`
2. `lisahost` / `GG-Lisa-Stable`
3. `lisahost_kr` / `GG-Lisahost-KR`
4. `vmrack1` / `GG-Vmrack1`
5. `vmrack2` / `GG-Vmrack2`
6. `dedirock` / `GG-Dedirock`

## 发布订阅

在本地生成产物后：

```bash
python3 scripts/render_artifacts.py
bash scripts/publish_subscriptions_to_sea_host.sh --dry-run
REMOTE_PASSWORD='<operator-provided-password>' bash scripts/publish_subscriptions_to_sea_host.sh
```

旧脚本 `publish_subscriptions_to_infra_core.sh` 仅为兼容 wrapper，会委托到新脚本。`publish_subscriptions_to_sea_host.sh` 会在上传前先执行 `reconcile_subscription_node_availability.py --probe --report`，再执行 `render_artifacts.py`。

## 可用性门禁

- 探测方法是临时 mihomo 单节点配置 + 本地 HTTP proxy 访问 `https://api.openai.com/v1/models`。
- 只有真实代理 HTTP 层返回可接受状态码的节点才会进入公开订阅；TCP 端口连通只作为诊断字段。
- 所有节点真实代理探测失败时，`render_artifacts.py` 会 fail-fast，不发布坏订阅。
- 节点恢复后，下次 probe + render 会自动加回。
- 维护窗口可在 `inventory/nodes.yaml` 设置 `subscription_availability_exempt: true`。

```bash
python3 scripts/reconcile_subscription_node_availability.py --probe --report
```

## 验证

```bash
curl -fsS https://subs.sea.prod.gglohh.top/subscriptions/v2ray_nodes.txt | head -1
curl -fsS https://subs.sea.prod.gglohh.top/subscriptions/mihomo-universal.yaml | grep -E 'openai.com|chatgpt.com|wps.cn|wps.exe'
```

Windows 本机路由验收见根仓 `scripts/windows/accept-mihomo-windows.ps1`。

## 相关 ADR

- [ADR-0020](../../docs/adr/ADR-0020-sea-bgp-temporary-subscription-host.md) - infra-core 退役与 SEA BGP 临时订阅宿主
- [ADR-0021](../../docs/adr/ADR-0021-subscription-node-availability-pruning.md) - 可用性异常节点自动剔除
