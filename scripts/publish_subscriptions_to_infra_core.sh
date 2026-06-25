#!/usr/bin/env bash
set -euo pipefail

echo "[WARN] publish_subscriptions_to_infra_core.sh is deprecated." >&2
echo "[WARN] infra-core (112.28.134.53 / /mnt/hdo/infra-core / :27111) is retired." >&2
echo "[WARN] Delegating to publish_subscriptions_to_sea_host.sh." >&2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/publish_subscriptions_to_sea_host.sh" "$@"
