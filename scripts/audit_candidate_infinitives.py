#!/usr/bin/env python3
"""Create a heuristic audit queue for the imported candidate infinitives.

Run from the COQ project root:
    py scripts/audit_candidate_infinitives.py

The report is for triage only and must not be used as automatic approval.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.candidate_audit import audit_candidate_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data" / "catalogs" / "candidate-infinitives.jsonl",
        help="JSONL produced by import_candidate_infinitives.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "catalogs",
        help="Directory in which to write audit reports",
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        default=None,
        help=(
            "Optional JSONL of linguistic-owner decisions. By default, the auditor "
            "uses lemma-review-decisions.jsonl beside the candidate inventory when present."
        ),
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=None,
        help="Optional JSON rule registry. Defaults to data/catalogs/candidate-audit-rules.json.",
    )
    args = parser.parse_args()
    if not args.input.exists():
        parser.error(f"Candidate inventory not found: {args.input}. Run scripts/import_candidate_infinitives.py first.")
    try:
        summary = audit_candidate_file(args.input, args.output_dir, args.decisions, args.rules)
    except (OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"valid": True, **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
