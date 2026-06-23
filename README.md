# Proxy Ops Private

Private operations repository for proxy node convergence.

## Purpose

This repository is the private source of truth for:

- fixed node secrets
- node inventory
- generated client subscriptions
- generated `infra-core` sidecar config
- rollout and verification scripts

## Boundary

- Public baseline logic stays in `/workspaces/proxy_own/remote_proxy`
- Fixed secrets and generated artifacts belong here
- standalone 节点按 inventory 中的 `runtime_service` 分别走 sing-box 或 `cliproxy-plus` 生命周期
- `dedirock` 是首个测试 / 验证节点

当前要特别区分两条线：

- `remote_proxy`
  继续是公开部署基线，负责 sing-box / cliproxy-plus 的标准生命周期脚本。
- `proxy_ops_private`
  继续是私有现场真相源，负责“哪些节点在现场、每个节点的固定密钥是什么、当前订阅文件是什么”，以及基于这些私有事实渲染出来的 sing-box / `cliproxy-plus` 单机部署包。

换句话说，这里保存的是“你的现场清单和现场参数”，不是另一个独立控制面。

## Main Directories

- `inventory/`: node metadata and publication settings
- `secrets/nodes/`: per-node fixed secret inputs
- `generated/`: generated multi-node subscriptions, single-node subscriptions, and `infra-core` config
- `docs/`: current deployment quickstarts and operator-facing notes
- `scripts/`: local render/apply/check tooling
- `tests/`: local unit tests for inventory and generated outputs

## Current Client Entry

If you need the current authoritative client usage for the deployed
subscription service, read:

- `docs/client-subscription-quickstart.md`

That document is the current truth for Windows / Linux / Android subscription
import. It takes priority over old standalone `show_info.sh` usage notes.

## Verification

Use the egress check script when you need to prove which public IP a shared
`infra-core` workload is actually using:

```bash
bash /workspaces/proxy_own/proxy_ops_private/scripts/check_infra_core_egress_ip.sh
```

What it reports:

- `matched_rule_observed_ip`: the public IP seen when the container accesses a
  URL that is guaranteed to match the current `proxy_failover` routing rules
- `default_route_observed_ip`: the public IP seen when the container accesses a
  plain IP echo endpoint that does not match the proxy rules
- `selector_current` / `selector_selected`: the current failover controller
  decision
- `latest_sidecar_log_tag`: the latest `outbound/vless[...]` tag from
  `infra_vless_sidecar`

Why both IPs matter:

- Current `vless-sidecar` policy keeps `route.final=direct`
- That means only rule-matched domains like `openai.com` or `chatgpt.com` go
  through `proxy_failover`
- A random `curl https://api.ipify.org` is not a valid proxy verification in
  this setup, because it can legitimately return the `Ubuntu.online` host IP

## Standalone Node Rollout

`apply_standalone_node.sh` / `check_standalone_node.sh` 现在已经是正式可执行脚本，不再只是 dry-run 占位。

当前使用方式：

```bash
export REMOTE_PROXY_SSH_PASSWORD_LISAHOST_KR='<operator-provided-password>'
bash repos/proxy_ops_private/scripts/apply_standalone_node.sh --node lisahost_kr

export REMOTE_PROXY_SSH_PASSWORD_VMRACK1='<operator-provided-password>'
bash repos/proxy_ops_private/scripts/apply_standalone_node.sh --node vmrack1

export REMOTE_PROXY_SSH_PASSWORD_VMRACK2='<operator-provided-password>'
bash repos/proxy_ops_private/scripts/apply_standalone_node.sh --node vmrack2

export REMOTE_PROXY_SSH_PASSWORD_DEDIROCK='<operator-provided-password>'
bash repos/proxy_ops_private/scripts/apply_standalone_node.sh --node dedirock
```

对应巡检：

```bash
export REMOTE_PROXY_SSH_PASSWORD_VMRACK1='<operator-provided-password>'
bash repos/proxy_ops_private/scripts/check_standalone_node.sh --node vmrack1
```

脚本约束：

- 默认 SSH 用户是 `root`
- 默认远端工作目录是 `/root/remote_proxy`
- live apply 前会先备份远端旧目录到 `/root/remote_proxy_backups/<node>/<timestamp>`
- live apply 同时备份 `/etc/remote_proxy`、`/var/lib/remote_proxy` 和对应 systemd / Quadlet 产物
- `infra-core` sidecar 和订阅站的节点优先级来自 `inventory/subscriptions.yaml` 的 `failover_priority`
- `lisahost_kr` 作为 sing-box 订阅节点纳入多节点订阅和 sidecar failover，`cliproxy-plus` rollout 仍按各节点 `runtime_service` 单独判断
