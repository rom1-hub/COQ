"""Heuristic triage for the candidate infinitive inventory.

Findings are review hints only. They never accept, reject, normalize, or promote a
candidate. The catalogue owner must verify lemma, group, family and forms.
"""
from __future__ import annotations

import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from app.domain.candidate_lexicon import CandidateInfinitiveRecord
from app.domain.catalog_findings import CandidateAuditFlag
from app.domain.candidate_audit_rules import (
    CandidateAuditRules,
    group_suffix_is_compatible,
    has_recognized_infinitive_ending,
    load_candidate_audit_rules,
)
from app.domain.lemma_review_decisions import LemmaReviewDecision
from app.domain.verb_contracts import ContractModel


class CandidateAuditRecord(ContractModel):
    candidate_id: str = Field(pattern=r"^cand_[0-9a-f]{16}$")
    candidate_form: str = Field(min_length=2, max_length=100)
    suggested_groups: list[str] = Field(min_length=1, max_length=3)
    flags: list[CandidateAuditFlag]
    resolved_flags: list[CandidateAuditFlag] = Field(default_factory=list)
    open_flags: list[CandidateAuditFlag] = Field(default_factory=list)
    triage: Literal["priority_review", "manual_review", "basic_review", "resolved"]
    review_decision_id: str | None = None
    decision_outcome: Literal["lemma_metadata_reviewed", "source_token_not_canonical_lemma"] | None = None
    canonical_infinitive: str | None = None
    display_infinitive: str | None = None
    related_lemma: str | None = None
    related_construction: str | None = None
    reviewed_group_id: Literal["first", "second", "third"] | None = None
    construction_policy: Literal["pronominal_only", "non_pronominal_only", "multiple_constructions"] | None = None
    review_status: Literal["candidate", "metadata_reviewed_forms_pending", "source_token_not_canonical_lemma"] = "candidate"
    forms_review_status: Literal["pending", "not_applicable"] = "pending"
    approved_for_production: Literal[False] = False


def audit_candidate(
    record: CandidateInfinitiveRecord, rules: CandidateAuditRules | None = None
) -> CandidateAuditRecord:
    """Return raw explainable findings using the validated rules registry."""
    lemma = unicodedata.normalize("NFC", record.candidate_form).strip().lower()
    rules = rules or load_candidate_audit_rules()
    flags: list[CandidateAuditFlag] = []
    groups = {group.value if hasattr(group, "value") else str(group) for group in record.suggested_groups}

    if len(groups) > 1:
        flags.append(CandidateAuditFlag.MULTIPLE_GROUP_SUGGESTIONS)

    # Ending equivalence and per-group expectations are declarative data.
    # Matching a suffix is only a triage hint; it is not linguistic approval.
    ordinary_ending = has_recognized_infinitive_ending(lemma, rules)

    if "first" in groups and not group_suffix_is_compatible(lemma, "first", rules):
        flags.append(CandidateAuditFlag.FIRST_GROUP_NOT_ER)
    if "second" in groups and not group_suffix_is_compatible(lemma, "second", rules):
        flags.append(CandidateAuditFlag.SECOND_GROUP_NOT_IR)
    if "third" in groups and not group_suffix_is_compatible(lemma, "third", rules):
        flags.append(CandidateAuditFlag.THIRD_GROUP_SUFFIX_MISMATCH)
    if not ordinary_ending:
        flags.append(CandidateAuditFlag.UNUSUAL_INFINITIVE_ENDING)
    if "-" in lemma:
        flags.append(CandidateAuditFlag.HYPHENATED_TOKEN)
    if any(char.isspace() for char in lemma):
        flags.append(CandidateAuditFlag.MULTIWORD_TOKEN)
    if "'" in lemma or "’" in lemma:
        flags.append(CandidateAuditFlag.APOSTROPHE_TOKEN)
    if any(not (char.isalpha() or char in "- '’") for char in lemma):
        flags.append(CandidateAuditFlag.NON_LETTER_SYMBOL)

    if any(
        flag in flags
        for flag in (
            CandidateAuditFlag.FIRST_GROUP_NOT_ER,
            CandidateAuditFlag.SECOND_GROUP_NOT_IR,
            CandidateAuditFlag.THIRD_GROUP_SUFFIX_MISMATCH,
            CandidateAuditFlag.UNUSUAL_INFINITIVE_ENDING,
            CandidateAuditFlag.NON_LETTER_SYMBOL,
            CandidateAuditFlag.MULTIPLE_GROUP_SUGGESTIONS,
        )
    ):
        triage = "priority_review"
    elif flags:
        triage = "manual_review"
    else:
        triage = "basic_review"

    return CandidateAuditRecord(
        candidate_id=record.candidate_id,
        candidate_form=lemma,
        suggested_groups=sorted(groups),
        flags=flags,
        resolved_flags=[],
        open_flags=list(flags),
        triage=triage,
    )


def _load_review_decisions(path: Path) -> list[LemmaReviewDecision]:
    """Load a validated ledger of candidate decisions and editorial observations."""
    if not path.exists():
        raise FileNotFoundError(f"Lemma review decision file not found: {path}")
    decisions: list[LemmaReviewDecision] = []
    seen_decision_ids: set[str] = set()
    seen_candidate_ids: set[str] = set()
    seen_observations: set[str] = set()
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                decision = LemmaReviewDecision.model_validate_json(raw_line)
            except Exception as exc:
                errors.append(f"line {line_number}: {exc}")
                continue
            if decision.decision_id in seen_decision_ids:
                errors.append(f"line {line_number}: duplicate decision_id {decision.decision_id}")
                continue
            if decision.decision_scope == "candidate":
                candidate_id = decision.source_candidate_id
                if candidate_id in seen_candidate_ids:
                    errors.append(
                        f"line {line_number}: multiple active decisions for source_candidate_id {candidate_id}"
                    )
                    continue
                seen_candidate_ids.add(candidate_id or "")
            else:
                observation_key = decision.source_candidate_form
                if observation_key in seen_observations:
                    errors.append(
                        f"line {line_number}: duplicate editorial observation {observation_key!r}"
                    )
                    continue
                seen_observations.add(observation_key)
            seen_decision_ids.add(decision.decision_id)
            decisions.append(decision)
    if errors:
        raise ValueError("Lemma review decision JSONL is invalid:\n" + "\n".join(errors[:25]))
    return decisions


def _apply_review_decision(
    audit: CandidateAuditRecord,
    record: CandidateInfinitiveRecord,
    decision: LemmaReviewDecision,
) -> CandidateAuditRecord:
    """Apply a candidate-scoped decision, preserving the original heuristic flags."""
    if decision.decision_scope != "candidate":
        raise ValueError(f"{decision.decision_id}: editorial observations cannot be applied to candidate rows")
    if decision.source_candidate_id != record.candidate_id:
        raise ValueError(f"{decision.decision_id}: source candidate ID does not match")
    if decision.source_candidate_form != record.candidate_form:
        raise ValueError(f"{decision.decision_id}: source candidate form does not match inventory")

    raw = set(audit.flags)
    resolutions = set(decision.resolves_findings)
    stale = resolutions - raw
    if stale:
        stale_names = sorted(item.value for item in stale)
        raise ValueError(
            f"{decision.decision_id}: resolves_findings do not match current heuristic findings: {stale_names}"
        )

    resolved = [flag for flag in audit.flags if flag in resolutions]
    open_flags = [flag for flag in audit.flags if flag not in resolutions]
    if decision.decision_outcome == "source_token_not_canonical_lemma":
        return audit.model_copy(update={
            "resolved_flags": resolved,
            "open_flags": open_flags,
            "triage": "resolved" if not open_flags else audit.triage,
            "review_decision_id": decision.decision_id,
            "decision_outcome": decision.decision_outcome,
            "canonical_infinitive": None,
            "display_infinitive": None,
            "related_lemma": decision.related_lemma,
            "related_construction": decision.related_construction,
            "reviewed_group_id": None,
            "construction_policy": None,
            "review_status": "source_token_not_canonical_lemma",
            "forms_review_status": "not_applicable",
            "approved_for_production": False,
        })

    return audit.model_copy(update={
        "resolved_flags": resolved,
        "open_flags": open_flags,
        "triage": "resolved" if not open_flags else audit.triage,
        "review_decision_id": decision.decision_id,
        "decision_outcome": decision.decision_outcome,
        "canonical_infinitive": decision.canonical_infinitive,
        "display_infinitive": decision.display_infinitive,
        "related_lemma": None,
        "related_construction": None,
        "reviewed_group_id": decision.group_id.value if hasattr(decision.group_id, "value") else str(decision.group_id),
        "construction_policy": decision.construction_policy,
        "review_status": "metadata_reviewed_forms_pending",
        "forms_review_status": decision.forms_review_status,
        "approved_for_production": False,
    })


def audit_candidate_file(
    input_path: Path,
    output_dir: Path,
    decision_path: Path | None = None,
    rules_path: Path | None = None,
) -> dict[str, Any]:
    """Audit candidates, apply matching declarative decisions, and emit reports.

    Raw heuristic flags are always preserved. A reviewed decision separately marks
    which findings are resolved and which remain open; forms remain unapproved.
    """
    import csv
    import json

    records: list[CandidateInfinitiveRecord] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    with input_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                record = CandidateInfinitiveRecord.model_validate_json(raw_line)
            except Exception as exc:  # include the source line in the report
                errors.append(f"line {line_number}: {exc}")
                continue
            if record.candidate_id in seen_ids:
                errors.append(f"line {line_number}: duplicate candidate_id {record.candidate_id}")
                continue
            seen_ids.add(record.candidate_id)
            records.append(record)

    if errors:
        raise ValueError("Candidate JSONL is invalid:\n" + "\n".join(errors[:25]))

    rules = load_candidate_audit_rules(str(rules_path) if rules_path else None)
    audit_by_id = {record.candidate_id: audit_candidate(record, rules) for record in records}
    source_by_id = {record.candidate_id: record for record in records}
    if decision_path is None:
        default_decisions = input_path.with_name("lemma-review-decisions.jsonl")
        decision_path = default_decisions if default_decisions.exists() else None
    decisions = _load_review_decisions(decision_path) if decision_path is not None else []
    editorial_observations = [item for item in decisions if item.decision_scope == "editorial_observation"]
    candidate_decisions = [item for item in decisions if item.decision_scope == "candidate"]
    for decision in candidate_decisions:
        source = source_by_id.get(decision.source_candidate_id or "")
        if source is None:
            raise ValueError(
                f"{decision.decision_id}: source candidate {decision.source_candidate_id} "
                "is not present in the candidate inventory"
            )
        audit_by_id[source.candidate_id] = _apply_review_decision(
            audit_by_id[source.candidate_id], source, decision
        )
    audited = [audit_by_id[record.candidate_id] for record in records]
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "candidate-infinitives-audit.jsonl"
    csv_path = output_dir / "candidate-infinitives-audit.csv"
    summary_path = output_dir / "candidate-infinitives-audit-summary.json"

    jsonl_path.write_text(
        "".join(item.model_dump_json(exclude_none=True) + "\n" for item in audited),
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "candidate_id", "candidate_form", "suggested_groups", "triage", "flags",
                "resolved_flags", "open_flags", "review_decision_id", "decision_outcome", "canonical_infinitive",
                "display_infinitive", "related_lemma", "related_construction", "reviewed_group_id", "construction_policy", "review_status",
                "forms_review_status", "approved_for_production",
            ],
        )
        writer.writeheader()
        for item in audited:
            writer.writerow({
                "candidate_id": item.candidate_id,
                "candidate_form": item.candidate_form,
                "suggested_groups": ", ".join(item.suggested_groups),
                "triage": item.triage,
                "flags": "; ".join(flag.value for flag in item.flags),
                "resolved_flags": "; ".join(flag.value for flag in item.resolved_flags),
                "open_flags": "; ".join(flag.value for flag in item.open_flags),
                "review_decision_id": item.review_decision_id or "",
                "decision_outcome": item.decision_outcome or "",
                "canonical_infinitive": item.canonical_infinitive or "",
                "display_infinitive": item.display_infinitive or "",
                "related_lemma": item.related_lemma or "",
                "related_construction": item.related_construction or "",
                "reviewed_group_id": item.reviewed_group_id or "",
                "construction_policy": item.construction_policy or "",
                "review_status": item.review_status,
                "forms_review_status": item.forms_review_status,
                "approved_for_production": "false",
            })

    flag_counts = Counter(flag.value for item in audited for flag in item.flags)
    resolved_counts = Counter(flag.value for item in audited for flag in item.resolved_flags)
    open_counts = Counter(flag.value for item in audited for flag in item.open_flags)
    triage_counts = Counter(item.triage for item in audited)
    review_status_counts = Counter(item.review_status for item in audited)
    summary: dict[str, Any] = {
        "input_file": str(input_path),
        "decision_file": str(decision_path) if decision_path else None,
        "candidate_count": len(records),
        "candidates_with_findings": sum(bool(item.flags) for item in audited),
        "candidates_without_heuristic_findings": sum(not item.flags for item in audited),
        "candidates_with_open_findings": sum(bool(item.open_flags) for item in audited),
        "candidates_with_only_resolved_findings": sum(bool(item.flags) and not item.open_flags for item in audited),
        "candidates_with_review_decisions": sum(item.review_decision_id is not None for item in audited),
        "editorial_observation_decision_count": len(editorial_observations),
        "decision_outcome_counts": dict(sorted(Counter(item.decision_outcome for item in decisions).items())),
        "review_status_counts": dict(sorted(review_status_counts.items())),
        "triage_counts": dict(sorted(triage_counts.items())),
        "finding_counts": dict(sorted(flag_counts.items())),
        "resolved_finding_counts": dict(sorted(resolved_counts.items())),
        "open_finding_counts": dict(sorted(open_counts.items())),
        "approved_for_production_count": 0,
        "important_limit": (
            "Heuristic flags are preserved as raw findings. Candidate-scoped decisions may mark listed findings as resolved; editorial observations are retained in the decision ledger but are not treated as imported candidates. "
            "Source tokens not accepted as canonical COQ lemmas remain traceable and linked to a related lemma; this decision does not claim that every usage is impossible in the language. No conjugation forms are approved for production. Absence of a flag is not linguistic validation."
        ),
        "outputs": {
            "jsonl": jsonl_path.name,
            "csv": csv_path.name,
            "summary": summary_path.name,
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary
