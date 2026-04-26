#!/usr/bin/env python3
"""Estimate object-storage cost for a DLRS archive.

Walks every ``*.pointer.json`` under ``humans/`` and produces a per-record
and per-archive monthly cost projection in USD using a small built-in price
table. The table is intentionally conservative; tune ``PRICES`` (or pass
``--prices`` pointing at a JSON override) to match your contract.

Cost model:

  monthly_storage_cost = size_GB * storage_price_per_GB_per_month
  monthly_egress_cost  = size_GB * egress_price_per_GB * egress_factor

``egress_factor`` defaults to 0.05 (i.e. each month we egress 5% of the
asset for runtime use). Override with ``--egress-factor``.

This is a v0.3 reference utility — not authoritative pricing.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# USD per GB-month (storage) and USD per GB (egress). Conservative ballpark
# values pulled from public pricing pages as of 2026-Q2.
PRICES: dict[str, dict[str, float]] = {
    "s3":    {"storage": 0.023, "egress": 0.090},
    "oss":   {"storage": 0.020, "egress": 0.075},
    "cos":   {"storage": 0.020, "egress": 0.075},
    "minio": {"storage": 0.005, "egress": 0.000},
    "obj":   {"storage": 0.020, "egress": 0.080},
    "repo":  {"storage": 0.000, "egress": 0.000},
}


def _scheme_of(uri: str) -> str:
    return uri.split("://", 1)[0] if "://" in uri else "obj"


def estimate(prices: dict[str, dict[str, float]], egress_factor: float) -> dict[str, Any]:
    by_record: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "size_gb": 0.0,
        "monthly_storage_usd": 0.0,
        "monthly_egress_usd": 0.0,
        "pointer_count": 0,
        "by_scheme": defaultdict(lambda: {"size_gb": 0.0, "count": 0}),
    })

    for pointer_path in sorted(ROOT.rglob("*.pointer.json")):
        if "/.git/" in str(pointer_path):
            continue
        try:
            data = json.loads(pointer_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        size_bytes = data.get("size_bytes") or 0
        size_gb = size_bytes / (1024 ** 3) if size_bytes else 0.0
        scheme = _scheme_of(data.get("storage_uri", ""))
        price = prices.get(scheme, prices.get("obj", {"storage": 0.0, "egress": 0.0}))
        # Find the owning record_id by scanning parents for manifest.json
        record_id = "<unknown>"
        for parent in pointer_path.parents:
            mf = parent / "manifest.json"
            if mf.exists():
                try:
                    record_id = json.loads(mf.read_text())["record_id"]
                except Exception:
                    pass
                break
        rec = by_record[record_id]
        rec["size_gb"] += size_gb
        rec["pointer_count"] += 1
        rec["monthly_storage_usd"] += size_gb * price["storage"]
        rec["monthly_egress_usd"] += size_gb * price["egress"] * egress_factor
        rec["by_scheme"][scheme]["size_gb"] += size_gb
        rec["by_scheme"][scheme]["count"] += 1

    totals = {
        "records": len(by_record),
        "size_gb": sum(r["size_gb"] for r in by_record.values()),
        "monthly_storage_usd": sum(r["monthly_storage_usd"] for r in by_record.values()),
        "monthly_egress_usd": sum(r["monthly_egress_usd"] for r in by_record.values()),
    }
    totals["monthly_total_usd"] = totals["monthly_storage_usd"] + totals["monthly_egress_usd"]
    # Convert defaultdicts for JSON serialisation.
    by_record_serialisable = {}
    for rid, rec in by_record.items():
        rec["by_scheme"] = {k: dict(v) for k, v in rec["by_scheme"].items()}
        by_record_serialisable[rid] = rec
    return {"totals": totals, "by_record": by_record_serialisable}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Estimate storage/egress costs for a DLRS archive.")
    parser.add_argument("--prices", type=Path, default=None, help="Optional JSON file overriding PRICES.")
    parser.add_argument("--egress-factor", type=float, default=0.05,
                        help="Fraction of stored data egressed per month (default 0.05 = 5%%).")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable summary.")
    args = parser.parse_args(argv[1:])

    prices = PRICES
    if args.prices:
        prices = json.loads(args.prices.read_text(encoding="utf-8"))

    result = estimate(prices, args.egress_factor)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    t = result["totals"]
    print(f"DLRS storage cost estimate (egress factor {args.egress_factor:.2%})")
    print(f"  records                : {t['records']}")
    print(f"  total size             : {t['size_gb']:.3f} GB")
    print(f"  monthly storage USD    : ${t['monthly_storage_usd']:.2f}")
    print(f"  monthly egress  USD    : ${t['monthly_egress_usd']:.2f}")
    print(f"  monthly total   USD    : ${t['monthly_total_usd']:.2f}")
    print()
    print("Per record:")
    for rid, rec in result["by_record"].items():
        print(f"  {rid}: {rec['size_gb']:.3f} GB  storage ${rec['monthly_storage_usd']:.2f}  egress ${rec['monthly_egress_usd']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
