#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from subscription_node_availability import (
    exclusion_report,
    load_availability_policy,
    probe_nodes,
    refresh_availability,
    subscription_eligible_nodes,
    subscription_publishable_nodes,
    update_ledger,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe proxy nodes and maintain subscription availability ledger.")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Run the configured real proxy availability probe and update the ledger.",
    )
    parser.add_argument("--report", action="store_true", help="Print inclusion/exclusion report.")
    parser.add_argument("--dry-run", action="store_true", help="With --probe, probe but do not write ledger.")
    args = parser.parse_args()

    if args.probe:
        results = probe_nodes(REPO_ROOT)
        if args.dry_run:
            print(json.dumps([asdict(item) for item in results], indent=2, ensure_ascii=False))
        else:
            update_ledger(REPO_ROOT, results)
            print(f"[INFO] Updated ledger: {load_availability_policy(REPO_ROOT).ledger_path}")
    elif not args.report:
        refresh_availability(REPO_ROOT)

    report = exclusion_report(REPO_ROOT)
    eligible = subscription_eligible_nodes(REPO_ROOT)
    publishable = subscription_publishable_nodes(REPO_ROOT)
    print(f"[INFO] eligible_nodes={len(eligible)} publishable_nodes={len(publishable)} included={report.included} pending={report.pending} excluded={report.excluded} unknown={report.unknown}")
    if args.report:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
