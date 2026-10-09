import json
from pathlib import Path

import pytest

from app.domain.candidate_audit import CandidateAuditFlag, audit_candidate, audit_candidate_file
from app.domain.candidate_audit_rules import GroupSuffixException, load_candidate_audit_rules, group_suffix_is_compatible
from app.domain.candidate_lexicon import (
    CANDIDATE_SOURCE_COMMIT,
    CANDIDATE_SOURCE_ID,
    CandidateInfinitiveRecord,
    candidate_id_for,
)


def candidate(form: str, groups: list[str]) -> CandidateInfinitiveRecord:
    return CandidateInfinitiveRecord(
        candidate_id=candidate_id_for(form),
        candidate_form=form,
        suggested_groups=groups,
        source_id=CANDIDATE_SOURCE_ID,
        source_commit=CANDIDATE_SOURCE_COMMIT,
    )


def test_candidate_audit_is_triage_not_approval():
    result = audit_candidate(candidate("parler", ["first"]))

    assert result.triage == "basic_review"
    assert result.flags == []
    assert result.approved_for_production is False
    assert result.review_status == "candidate"


def test_candidate_audit_flags_incompatible_group_ending_without_rejecting():
    result = audit_candidate(candidate("parler", ["third"]))

    assert CandidateAuditFlag.THIRD_GROUP_SUFFIX_MISMATCH in result.flags
    assert result.triage == "priority_review"
    assert result.approved_for_production is False


def test_candidate_audit_allows_aller_as_third_group_exception():
    result = audit_candidate(candidate("aller", ["third"]))

    assert CandidateAuditFlag.THIRD_GROUP_SUFFIX_MISMATCH not in result.flags
    assert result.approved_for_production is False


def test_candidate_audit_flags_noncanonical_looking_tokens_for_manual_review():
    result = audit_candidate(candidate("abat-carrer", ["first"]))

    assert CandidateAuditFlag.HYPHENATED_TOKEN in result.flags
    assert CandidateAuditFlag.FIRST_GROUP_NOT_ER not in result.flags
    assert result.triage == "manual_review"


def test_candidate_audit_does_not_collapse_accented_lemmas():
    accented = audit_candidate(candidate("aérer", ["first"]))
    unaccented = audit_candidate(candidate("aerer", ["first"]))

    assert accented.candidate_form == "aérer"
    assert unaccented.candidate_form == "aerer"
    assert accented.candidate_id != unaccented.candidate_id


def test_audit_file_writes_jsonl_csv_and_summary_but_never_approves(tmp_path: Path):
    input_path = tmp_path / "candidate-infinitives.jsonl"
    input_path.write_text(
        "\n".join([
            candidate("finir", ["second"]).model_dump_json(),
            candidate("parler", ["third"]).model_dump_json(),
        ]) + "\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "reports"

    summary = audit_candidate_file(input_path, output_dir)

    assert summary["candidate_count"] == 2
    assert summary["candidates_with_findings"] == 1
    assert summary["approved_for_production_count"] == 0
    assert (output_dir / "candidate-infinitives-audit.jsonl").exists()
    assert (output_dir / "candidate-infinitives-audit.csv").read_text(encoding="utf-8-sig").startswith("candidate_id,")
    loaded_summary = json.loads((output_dir / "candidate-infinitives-audit-summary.json").read_text(encoding="utf-8"))
    assert loaded_summary["approved_for_production_count"] == 0



def test_csv_audit_report_exports_all_decision_fields_and_generic_noncanonical_status(tmp_path: Path):
    source = candidate("fiche", ["first"])
    input_path = tmp_path / "candidate-infinitives.jsonl"
    input_path.write_text(source.model_dump_json() + "\n", encoding="utf-8")
    catalogs = Path(__file__).resolve().parents[2] / "data" / "catalogs"
    decisions_path = tmp_path / "decisions.jsonl"
    fiche_decision = next(
        item for item in (json.loads(line) for line in (catalogs / "lemma-review-decisions.jsonl").read_text(encoding="utf-8").splitlines())
        if item["decision_id"] == "LR-039"
    )
    # Source candidate id is stable across import and audit.
    assert fiche_decision["source_candidate_id"] == source.candidate_id
    decisions_path.write_text(json.dumps(fiche_decision, ensure_ascii=False) + "\n", encoding="utf-8")

    audit_candidate_file(input_path, tmp_path / "reports", decisions_path)
    csv_text = (tmp_path / "reports" / "candidate-infinitives-audit.csv").read_text(encoding="utf-8-sig")
    assert csv_text.splitlines()[0].count("decision_outcome") == 1
    assert "source_token_not_canonical_lemma" in csv_text
    assert "ficher" in csv_text


def test_audit_file_fails_on_invalid_jsonl_record(tmp_path: Path):
    input_path = tmp_path / "broken.jsonl"
    input_path.write_text('{"candidate_id":"bad"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Candidate JSONL is invalid"):
        audit_candidate_file(input_path, tmp_path / "reports")


@pytest.mark.parametrize(
    ("form", "group"),
    [("amuïr", "second"), ("haïr", "second"), ("ouïr", "third")],
)
def test_diaeresis_ir_ending_is_recognized_without_inferring_group_truth(form: str, group: str):
    result = audit_candidate(candidate(form, [group]))

    assert CandidateAuditFlag.UNUSUAL_INFINITIVE_ENDING not in result.flags
    assert CandidateAuditFlag.SECOND_GROUP_NOT_IR not in result.flags
    assert result.approved_for_production is False


def test_hyphenated_entre_hair_is_only_flagged_for_source_token_review():
    result = audit_candidate(candidate("entre-haïr", ["second"]))

    assert result.flags == [CandidateAuditFlag.HYPHENATED_TOKEN]
    assert result.triage == "manual_review"
    assert result.approved_for_production is False


def test_lemma_review_decision_is_applied_as_data_without_erasing_raw_findings(tmp_path: Path):
    catalogs = Path(__file__).resolve().parents[2] / "data" / "catalogs"
    decision_record = json.loads((catalogs / "lemma-review-decisions.jsonl").read_text(encoding="utf-8").splitlines()[0])
    source = candidate("entre-haïr", ["second"])
    assert source.candidate_id == decision_record["source_candidate_id"]

    input_path = tmp_path / "candidate-infinitives.jsonl"
    input_path.write_text(source.model_dump_json() + "\n", encoding="utf-8")
    decisions_path = tmp_path / "lemma-review-decisions.jsonl"
    decisions_path.write_text(json.dumps(decision_record, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = audit_candidate_file(input_path, tmp_path / "reports", decisions_path)
    row = json.loads((tmp_path / "reports" / "candidate-infinitives-audit.jsonl").read_text(encoding="utf-8"))

    assert row["flags"] == ["hyphenated_token_needs_lemma_review"]
    assert row["resolved_flags"] == ["hyphenated_token_needs_lemma_review"]
    assert row["open_flags"] == []
    assert row["review_decision_id"] == "LR-038"
    assert row["canonical_infinitive"] == "entrehaïr"
    assert row["display_infinitive"] == "s'entrehaïr"
    assert row["reviewed_group_id"] == "second"
    assert row["construction_policy"] == "pronominal_only"
    assert row["review_status"] == "metadata_reviewed_forms_pending"
    assert row["forms_review_status"] == "pending"
    assert row["approved_for_production"] is False
    assert summary["candidates_with_only_resolved_findings"] == 1
    assert summary["candidates_with_open_findings"] == 0
    assert summary["approved_for_production_count"] == 0


def test_review_decision_cannot_resolve_a_finding_that_was_not_raised(tmp_path: Path):
    source = candidate("parler", ["first"])
    decision = {
        "schema_version": "1.3",
        "decision_id": "LR-900",
        "source_candidate_id": source.candidate_id,
        "source_candidate_form": source.candidate_form,
        "canonical_infinitive": "parler",
        "display_infinitive": "parler",
        "group_id": "first",
        "construction_policy": "non_pronominal_only",
        "resolves_findings": ["hyphenated_token_needs_lemma_review"],
        "decision_outcome": "lemma_metadata_reviewed",
        "forms_review_status": "pending",
        "decision_authority": "linguistic_owner",
        "decision_note": "Test decision for stale finding detection.",
        "approved_for_production": False,
    }
    input_path = tmp_path / "candidate-infinitives.jsonl"
    input_path.write_text(source.model_dump_json() + "\n", encoding="utf-8")
    decisions_path = tmp_path / "decisions.jsonl"
    decisions_path.write_text(json.dumps(decision) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="resolves_findings do not match current heuristic findings"):
        audit_candidate_file(input_path, tmp_path / "reports", decisions_path)


def test_review_decision_file_rejects_multiple_active_decisions_for_same_candidate(tmp_path: Path):
    source = candidate("entre-haïr", ["second"])
    catalogs = Path(__file__).resolve().parents[2] / "data" / "catalogs"
    decision = json.loads((catalogs / "lemma-review-decisions.jsonl").read_text(encoding="utf-8").splitlines()[0])
    input_path = tmp_path / "candidate-infinitives.jsonl"
    input_path.write_text(source.model_dump_json() + "\n", encoding="utf-8")
    decisions_path = tmp_path / "decisions.jsonl"
    second = dict(decision, decision_id="LR-040")
    decisions_path.write_text(
        json.dumps(decision, ensure_ascii=False) + "\n" + json.dumps(second, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="multiple active decisions for source_candidate_id"):
        audit_candidate_file(input_path, tmp_path / "reports", decisions_path)



def test_candidate_audit_rules_are_declarative_and_exceptions_are_not_hardcoded():
    rules = load_candidate_audit_rules()
    assert rules.equivalent_suffix_classes["ir_ending_for_audit"] == ["ir", "ïr"]
    assert rules.group_expected_suffix_classes["second"] == ["ir_ending_for_audit"]
    assert group_suffix_is_compatible("aller", "third", rules)
    assert not group_suffix_is_compatible("parler", "third", rules)

    # Demonstrate the same algorithm honors a registry entry for an entirely
    # different candidate, without adding a condition to the Python auditor.
    extra = GroupSuffixException(
        candidate_form="faller",
        group_id="third",
        accepted_suffixes=["er"],
        rationale="Synthetic test rule to prove exceptions are registry data.",
    )
    custom = rules.model_copy(update={"group_suffix_exceptions": [*rules.group_suffix_exceptions, extra]})
    assert group_suffix_is_compatible("faller", "third", custom)
    result = audit_candidate(candidate("faller", ["third"]), custom)
    assert CandidateAuditFlag.THIRD_GROUP_SUFFIX_MISMATCH not in result.flags


def test_review_decision_loader_requires_explicit_file_when_one_is_requested(tmp_path: Path):
    source = candidate("parler", ["first"])
    input_path = tmp_path / "candidate-infinitives.jsonl"
    input_path.write_text(source.model_dump_json() + "\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Lemma review decision file not found"):
        audit_candidate_file(input_path, tmp_path / "reports", tmp_path / "missing-decisions.jsonl")
