#!/usr/bin/env python3
"""Import a pinned MIT-licensed list of French verb-name candidates.

This tool imports names and *unverified* group suggestions only. It does not
import conjugation forms and cannot mark anything approved. It never accesses
the Académie française website.

Run from the project root:
    py scripts/import_candidate_infinitives.py

For an offline/reproducible test, pass both --input-json and --license-file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.candidate_lexicon import (  # noqa: E402
    CANDIDATE_SOURCE_COMMIT,
    CANDIDATE_SOURCE_ID,
    CandidateInfinitiveRecord,
    candidate_id_for,
    normalize_candidate_form,
)
from app.domain.verb_contracts import VerbGroup  # noqa: E402

SOURCE_BASE = f"https://raw.githubusercontent.com/einenlum/french-verbs-list/{CANDIDATE_SOURCE_COMMIT}"
SOURCE_JSON_URL = f"{SOURCE_BASE}/verbs.json"
SOURCE_LICENSE_URL = f"{SOURCE_BASE}/LICENSE"
# Git object IDs pin the exact raw files at the selected upstream commit.
SOURCE_JSON_GIT_BLOB_SHA = "b36b7c1dee4d93e9589701dfbb5d5319618d71f2"
SOURCE_LICENSE_GIT_BLOB_SHA = "f53ad6d11f70631cdeaeffc3685d47634c3c23cd"
GROUP_KEYS = {
    "first_group": VerbGroup.FIRST,
    "second_group": VerbGroup.SECOND,
    "third_group": VerbGroup.THIRD,
}
LICENSE_RELATIVE_PATH = Path("licenses/french-verbs-list-MIT.txt")


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git_blob_sha1(content: bytes) -> str:
    """Compute the Git SHA-1 for an ordinary blob object."""
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def verify_pinned_source(source_bytes: bytes, license_bytes: bytes) -> None:
    source_sha = git_blob_sha1(source_bytes)
    license_sha = git_blob_sha1(license_bytes)
    if source_sha != SOURCE_JSON_GIT_BLOB_SHA:
        raise ValueError(
            "verbs.json does not match the pinned upstream blob; refusing to label a different file as the reviewed commit "
            f"(expected {SOURCE_JSON_GIT_BLOB_SHA}, got {source_sha})"
        )
    if license_sha != SOURCE_LICENSE_GIT_BLOB_SHA:
        raise ValueError(
            "LICENSE does not match the pinned upstream blob; refusing to import without the exact MIT notice "
            f"(expected {SOURCE_LICENSE_GIT_BLOB_SHA}, got {license_sha})"
        )


def download_bytes(url: str, *, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "COQ-candidate-lexicon-import/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_source_payload(payload: Any) -> dict[str, list[str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("verbs"), dict):
        raise ValueError("Expected source JSON structure {'verbs': {'first_group': [...], ...}}")
    source_groups = payload["verbs"]
    parsed: dict[str, list[str]] = {}
    for key in GROUP_KEYS:
        values = source_groups.get(key)
        if not isinstance(values, list) or not values:
            raise ValueError(f"Missing or empty source group: {key}")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"Every source entry in {key} must be a non-empty string")
        parsed[key] = values
    return parsed


def build_candidate_records(payload: Any) -> tuple[list[CandidateInfinitiveRecord], dict[str, Any]]:
    """Merge duplicate tokens, keeping every group suggested by the source."""
    source_groups = parse_source_payload(payload)
    suggestions: dict[str, set[VerbGroup]] = defaultdict(set)
    raw_counts: dict[str, int] = {}

    for source_key, group in GROUP_KEYS.items():
        values = source_groups[source_key]
        raw_counts[source_key] = len(values)
        for raw_value in values:
            candidate_form = normalize_candidate_form(raw_value)
            if len(candidate_form) < 2 or len(candidate_form) > 100:
                raise ValueError(f"Source token length is outside the allowed range: {raw_value!r}")
            suggestions[candidate_form].add(group)

    records: list[CandidateInfinitiveRecord] = []
    for candidate_form in sorted(suggestions, key=str.casefold):
        records.append(
            CandidateInfinitiveRecord(
                candidate_id=candidate_id_for(candidate_form),
                candidate_form=candidate_form,
                suggested_groups=sorted(suggestions[candidate_form], key=lambda value: value.value),
                source_id=CANDIDATE_SOURCE_ID,
                source_commit=CANDIDATE_SOURCE_COMMIT,
                review_status="candidate",
                group_suggestions_are_unverified=True,
                requires_lemma_review=True,
            )
        )

    stats = {
        "raw_entry_counts_by_source_group": raw_counts,
        "raw_entry_count": sum(raw_counts.values()),
        "unique_candidate_count": len(records),
        "duplicate_entries_collapsed": sum(raw_counts.values()) - len(records),
        "candidates_with_multiple_group_suggestions": sum(len(groups) > 1 for groups in suggestions.values()),
        "group_suggestions_are_unverified": True,
        "conjugation_forms_imported": False,
        "candidate_verb_forms_canonicalized": False,
        "notes": "Candidate forms retain the source token after whitespace/NFC/case normalization; review each token before creating a VerbRecord.",
    }
    return records, stats


def validate_license(license_bytes: bytes) -> str:
    text = license_bytes.decode("utf-8")
    if "MIT License" not in text or "Yann Rabiller" not in text:
        raise ValueError("Downloaded license does not match the expected MIT notice for Yann Rabiller")
    return text


def write_inventory(
    records: list[CandidateInfinitiveRecord],
    stats: dict[str, Any],
    source_json_bytes: bytes,
    license_text: str,
    catalog_dir: Path,
) -> dict[str, Path]:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    licenses_dir = catalog_dir / LICENSE_RELATIVE_PATH.parent
    licenses_dir.mkdir(parents=True, exist_ok=True)

    candidates_path = catalog_dir / "candidate-infinitives.jsonl"
    manifest_path = catalog_dir / "candidate-lexicon-manifest.json"
    license_path = catalog_dir / LICENSE_RELATIVE_PATH
    notices_path = catalog_dir / "THIRD_PARTY_NOTICES.md"

    candidates_path.write_text(
        "".join(record.model_dump_json(exclude_none=True) + "\n" for record in records),
        encoding="utf-8",
    )
    license_bytes = license_text.encode("utf-8")
    license_path.write_bytes(license_bytes)

    manifest = {
        "manifest_version": "1.0",
        "dataset_id": CANDIDATE_SOURCE_ID,
        "source_repository": "https://github.com/einenlum/french-verbs-list",
        "source_commit": CANDIDATE_SOURCE_COMMIT,
        "source_json_url": SOURCE_JSON_URL,
        "source_license_url": SOURCE_LICENSE_URL,
        "license": "MIT",
        "license_file": str(LICENSE_RELATIVE_PATH).replace("\\", "/"),
        "license_sha256": sha256_hex(license_bytes),
        "source_json_sha256": sha256_hex(source_json_bytes),
        "source_json_git_blob_sha": git_blob_sha1(source_json_bytes),
        "license_git_blob_sha": git_blob_sha1(license_bytes),
        "candidate_output": "candidate-infinitives.jsonl",
        "candidate_output_sha256": sha256_hex(candidates_path.read_bytes()),
        "source_note": "The upstream README describes this list as a work in progress. It is used only as a candidate inventory; no source group suggestion or conjugation form is approved by importing it.",
        **stats,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    notices_path.write_text(
        "# Third-party notices\n\n"
        "## french-verbs-list — candidate infinitive inventory only\n\n"
        "Source: [einenlum/french-verbs-list](https://github.com/einenlum/french-verbs-list)\n\n"
        f"Pinned source commit: `{CANDIDATE_SOURCE_COMMIT}`.\n\n"
        "The imported file contains candidate verb-name tokens and unverified group suggestions only. "
        "COQ does not import conjugation forms from this source and does not treat these suggestions as reviewed facts. "
        "See `candidate-lexicon-manifest.json` for source hashes, counts and provenance.\n\n"
        "The upstream repository is distributed under the MIT License. Its notice is preserved at "
        f"`{str(LICENSE_RELATIVE_PATH).replace(chr(92), '/')}`.\n",
        encoding="utf-8",
    )
    return {
        "candidates": candidates_path,
        "manifest": manifest_path,
        "license": license_path,
        "notices": notices_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, help="Use a previously downloaded verbs.json instead of network.")
    parser.add_argument("--license-file", type=Path, help="Local MIT LICENSE file; required with --input-json.")
    parser.add_argument("--catalog-dir", type=Path, default=ROOT / "data" / "catalogs")
    args = parser.parse_args()

    if bool(args.input_json) != bool(args.license_file):
        parser.error("--input-json and --license-file must be supplied together")

    if args.input_json:
        source_bytes = args.input_json.read_bytes()
        license_bytes = args.license_file.read_bytes()
    else:
        source_bytes = download_bytes(SOURCE_JSON_URL)
        license_bytes = download_bytes(SOURCE_LICENSE_URL)

    verify_pinned_source(source_bytes, license_bytes)
    license_text = validate_license(license_bytes)
    payload = json.loads(source_bytes.decode("utf-8"))
    records, stats = build_candidate_records(payload)
    outputs = write_inventory(records, stats, source_bytes, license_text, args.catalog_dir)
    print(json.dumps({"valid": True, "stats": stats, "outputs": {key: str(value) for key, value in outputs.items()}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
