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
- `Lisahost` is tracked as a frozen reference node
- `dedirock` and `akilecloud` are the mutable rollout targets

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
