#!/usr/bin/env python3
"""Validate COQ JSONL catalog registries and cross-references.

The production verbs.jsonl file is intentionally absent until the source and
licensing review is completed. Run with --require-verb-catalog to enforce that
it exists before preparing a production release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TypeVar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import ValidationError  # noqa: E402
from app.domain.candidate_lexicon import CandidateInfinitiveRecord, candidate_id_for  # noqa: E402
from app.domain.catalog_validation_report import CatalogValidationReport  # noqa: E402
from app.domain.lemma_review_decisions import LemmaReviewDecision  # noqa: E402
from app.domain.verb_contracts import (  # noqa: E402
    CatalogScope,
    ConjugationPattern,
    ReviewStatus,
    ScopeKind,
    ScopeStatus,
    VerbGroup,
    VerbRecord,
)

ModelT = TypeVar("ModelT")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_jsonl(path: Path, model: type[ModelT], *, required: bool) -> tuple[list[ModelT], list[str]]:
    errors: list[str] = []
    records: list[ModelT] = []
    if not path.exists():
        if required:
            errors.append(f"Required catalog file is missing: {display_path(path)}")
        return records, errors

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
            records.append(model.model_validate(payload))
        except (json.JSONDecodeError, ValidationError) as exc:
            errors.append(f"{display_path(path)}:{line_number}: {exc}")
    return records, errors


def unique_by(records: list, attribute: str, label: str, errors: list[str]) -> dict[str, object]:
    index: dict[str, object] = {}
    for record in records:
        key = str(getattr(record, attribute))
        if key in index:
            errors.append(f"Duplicate {label}: {key}")
        else:
            index[key] = record
    return index


def group_scope_id(group: VerbGroup) -> str:
    return {
        VerbGroup.FIRST: "group:1",
        VerbGroup.SECOND: "group:2",
        VerbGroup.THIRD: "group:3",
    }[group]


def validate_catalog(catalog_dir: Path, *, require_verb_catalog: bool = False) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    patterns, parse_errors = read_jsonl(catalog_dir / "patterns.jsonl", ConjugationPattern, required=True)
    errors.extend(parse_errors)
    scopes, parse_errors = read_jsonl(catalog_dir / "scopes.jsonl", CatalogScope, required=True)
    errors.extend(parse_errors)
    verbs, parse_errors = read_jsonl(catalog_dir / "verbs.jsonl", VerbRecord, required=require_verb_catalog)
    errors.extend(parse_errors)
    candidates, parse_errors = read_jsonl(catalog_dir / "candidate-infinitives.jsonl", CandidateInfinitiveRecord, required=False)
    errors.extend(parse_errors)
    lemma_decisions, parse_errors = read_jsonl(
        catalog_dir / "lemma-review-decisions.jsonl", LemmaReviewDecision, required=False
    )
    errors.extend(parse_errors)

    pattern_index = unique_by(patterns, "pattern_id", "pattern_id", errors)
    scope_index = unique_by(scopes, "scope_id", "scope_id", errors)
    verb_index = unique_by(verbs, "verb_id", "verb_id", errors)
    candidate_index = unique_by(candidates, "candidate_id", "candidate_id", errors)
    unique_by(lemma_decisions, "decision_id", "decision_id", errors)

    candidate_decision_ids: set[str] = set()
    editorial_observation_forms: set[str] = set()
    for decision in lemma_decisions:
        if decision.decision_scope == "candidate":
            candidate_id = decision.source_candidate_id or ""
            if candidate_id in candidate_decision_ids:
                errors.append(f"Duplicate candidate review decision source: {candidate_id}")
            candidate_decision_ids.add(candidate_id)
        else:
            normalized_form = decision.source_candidate_form
            if normalized_form in editorial_observation_forms:
                errors.append(f"Duplicate editorial observation form: {normalized_form}")
            editorial_observation_forms.add(normalized_form)

    # Candidate decisions reference imported rows; editorial observations are
    # intentionally independent of that source inventory and must not fabricate
    # candidate entries for conjugated forms or expressions.
    candidate_file_for_decisions = catalog_dir / "candidate-infinitives.jsonl"
    for decision in lemma_decisions:
        if candidate_file_for_decisions.exists() and decision.decision_scope == "candidate":
            source_candidate = candidate_index.get(decision.source_candidate_id or "")
            if source_candidate is None:
                errors.append(
                    f"{decision.decision_id}: source candidate {decision.source_candidate_id} "
                    "is missing from candidate-infinitives.jsonl"
                )
            elif source_candidate.candidate_form != decision.source_candidate_form:
                errors.append(
                    f"{decision.decision_id}: source candidate form does not match candidate inventory"
                )
        if decision.related_lemma is not None and candidate_file_for_decisions.exists():
            related_id = candidate_id_for(decision.related_lemma)
            related_candidate = candidate_index.get(related_id)
            if related_candidate is None:
                errors.append(
                    f"{decision.decision_id}: related lemma {decision.related_lemma!r} "
                    "is missing from candidate-infinitives.jsonl"
                )
            elif related_candidate.candidate_form != decision.related_lemma:
                errors.append(f"{decision.decision_id}: related lemma does not match its stable candidate ID")

    candidate_manifest_path = catalog_dir / "candidate-lexicon-manifest.json"
    candidate_file_path = catalog_dir / "candidate-infinitives.jsonl"
    if candidate_file_path.exists():
        if not candidate_manifest_path.exists():
            errors.append("candidate-infinitives.jsonl exists but candidate-lexicon-manifest.json is missing")
        else:
            try:
                manifest = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
                if manifest.get("unique_candidate_count") != len(candidates):
                    errors.append("candidate manifest unique_candidate_count does not match JSONL records")
                candidate_hash = hashlib.sha256(candidate_file_path.read_bytes()).hexdigest()
                if manifest.get("candidate_output_sha256") != candidate_hash:
                    errors.append("candidate manifest candidate_output_sha256 does not match candidate JSONL")
                if any(candidate.source_id != manifest.get("dataset_id") for candidate in candidates):
                    errors.append("candidate records do not match candidate manifest dataset_id")
                if any(candidate.source_commit != manifest.get("source_commit") for candidate in candidates):
                    errors.append("candidate records do not match candidate manifest source_commit")
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"Invalid candidate-lexicon-manifest.json: {exc}")
    elif candidate_manifest_path.exists():
        errors.append("candidate-lexicon-manifest.json exists without candidate-infinitives.jsonl")

    canonical_lemmas: dict[str, str] = {}
    for verb in verbs:
        lemma = verb.infinitive.casefold()
        if lemma in canonical_lemmas:
            errors.append(
                f"Duplicate canonical infinitive {verb.infinitive!r}: "
                f"{canonical_lemmas[lemma]} and {verb.verb_id}"
            )
        else:
            canonical_lemmas[lemma] = verb.verb_id

        if verb.group_id is not None and group_scope_id(verb.group_id) not in scope_index:
            errors.append(f"{verb.verb_id}: missing group scope {group_scope_id(verb.group_id)}")
        for family_id in verb.family_ids:
            scope_id = f"family:{family_id}"
            if scope_id not in scope_index:
                errors.append(f"{verb.verb_id}: missing family scope {scope_id}")
        if verb.pattern_id and verb.pattern_id not in pattern_index:
            errors.append(f"{verb.verb_id}: unknown pattern_id {verb.pattern_id}")
        elif verb.pattern_id and verb.review_status in {ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED}:
            pattern = pattern_index[verb.pattern_id]
            if pattern.review_status != ReviewStatus.APPROVED:
                errors.append(f"{verb.verb_id}: forms-reviewed/approved verb references unapproved pattern {verb.pattern_id}")
            if verb.group_id is not None and pattern.group_id != verb.group_id:
                errors.append(f"{verb.verb_id}: group does not match pattern {verb.pattern_id}")

        for construction in verb.constructions:
            if construction.review_status in {ReviewStatus.METADATA_REVIEWED, ReviewStatus.FORMS_REVIEWED, ReviewStatus.APPROVED} and not construction.source_evidence:
                errors.append(f"{verb.verb_id}/{construction.construction_id}: reviewed construction has no evidence")

    for pattern in patterns:
        family_scope_id = f"family:{pattern.family_id}"
        scope = scope_index.get(family_scope_id)
        if scope is None:
            errors.append(f"{pattern.pattern_id}: missing family scope {family_scope_id}")
        elif isinstance(scope, CatalogScope) and scope.group_id != pattern.group_id:
            errors.append(f"{pattern.pattern_id}: group differs from {family_scope_id}")

    for scope in scopes:
        for pattern_id in scope.pattern_ids:
            if pattern_id not in pattern_index:
                errors.append(f"{scope.scope_id}: unknown pattern_id {pattern_id}")
        for verb_id in scope.verb_ids:
            if verb_id not in verb_index:
                errors.append(f"{scope.scope_id}: unknown verb_id {verb_id}")

        if scope.status != ScopeStatus.ACTIVE:
            continue

        approved_members: list[VerbRecord] = [verb for verb in verbs if verb.review_status == ReviewStatus.APPROVED]
        if scope.kind == ScopeKind.ALL:
            members = approved_members
        elif scope.kind == ScopeKind.GROUP:
            members = [verb for verb in approved_members if verb.group_id == scope.group_id]
        elif scope.kind == ScopeKind.FAMILY:
            members = [
                verb for verb in approved_members
                if scope.scope_id.split(":", 1)[1] in verb.family_ids
                or verb.verb_id in scope.verb_ids
                or verb.pattern_id in scope.pattern_ids
            ]
        else:  # curated collection
            members = [
                verb for verb in approved_members
                if verb.verb_id in scope.verb_ids or verb.pattern_id in scope.pattern_ids
            ]

        if not members:
            errors.append(f"Active scope {scope.scope_id} has no approved verb members")
        for pattern_id in scope.pattern_ids:
            pattern = pattern_index.get(pattern_id)
            if pattern is not None and pattern.review_status != ReviewStatus.APPROVED:
                errors.append(f"Active scope {scope.scope_id} references unapproved pattern {pattern_id}")

    verbs_path = catalog_dir / "verbs.jsonl"
    approved_count = sum(verb.review_status == ReviewStatus.APPROVED for verb in verbs)
    ready = approved_count > 0 and not errors
    if not verbs_path.exists():
        warnings.append("Production verbs.jsonl is not populated yet; metadata registries validated only.")
    if not candidate_file_path.exists():
        warnings.append("Candidate infinitive inventory has not been imported yet; run scripts/import_candidate_infinitives.py when ready.")
    elif not verbs:
        warnings.append("Production verbs.jsonl exists but contains no records.")
    if verbs and not any(verb.review_status == ReviewStatus.APPROVED for verb in verbs):
        warnings.append("No approved verbs; production conjugation lookup/practice is not ready.")
    if errors:
        ready = False
    # Validate the report itself through a typed contract. The counter fields
    # are required, so a stale/incomplete report implementation cannot silently
    # omit a metric that CI or downstream tooling relies on.
    report = CatalogValidationReport(
        valid=not errors,
        ready_for_production=ready,
        verb_count=len(verbs),
        approved_verb_count=approved_count,
        candidate_infinitive_count=len(candidates),
        lemma_review_decision_count=len(lemma_decisions),
        pattern_count=len(patterns),
        scope_count=len(scopes),
        warnings=warnings,
        errors=errors,
    )
    return report.model_dump(mode="json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=ROOT / "data" / "catalogs")
    parser.add_argument(
        "--require-verb-catalog",
        action="store_true",
        help="Fail if data/catalogs/verbs.jsonl is missing (production-release check).",
    )
    parser.add_argument(
        "--require-production-ready",
        action="store_true",
        help="Fail unless at least one approved verb exists and all validations pass.",
    )
    args = parser.parse_args()
    report = validate_catalog(args.catalog_dir, require_verb_catalog=args.require_verb_catalog)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] and (report["ready_for_production"] or not args.require_production_ready) else 1


if __name__ == "__main__":
    raise SystemExit(main())
