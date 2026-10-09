import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.candidate_lexicon import (
    CANDIDATE_SOURCE_COMMIT,
    CANDIDATE_SOURCE_ID,
    CandidateInfinitiveRecord,
    candidate_id_for,
)
from scripts.import_candidate_infinitives import (
    build_candidate_records,
    git_blob_sha1,
    validate_license,
    verify_pinned_source,
    write_inventory,
)


def payload() -> dict:
    return {
        "verbs": {
            "first_group": ["parler", "aimer", "AÉRER", "éclairer"],
            "second_group": ["finir", "réussir"],
            "third_group": ["parler", "dormir", "e\u0301clairer"],
        }
    }


def test_candidate_import_merges_duplicates_and_keeps_group_suggestions_unverified():
    records, stats = build_candidate_records(payload())
    by_form = {record.candidate_form: record for record in records}

    assert stats["raw_entry_count"] == 9
    assert stats["unique_candidate_count"] == 7
    assert stats["duplicate_entries_collapsed"] == 2
    assert by_form["parler"].suggested_groups == ["first", "third"]
    assert by_form["parler"].group_suggestions_are_unverified is True
    assert by_form["parler"].review_status == "candidate"
    assert by_form["éclairer"].suggested_groups == ["first", "third"]
    assert all(not hasattr(record, "forms") for record in records)


def test_candidate_id_is_stable_and_preserves_french_diacritics():
    assert candidate_id_for("  AÉRER  ") == candidate_id_for("aérer")
    assert candidate_id_for("aérer") != candidate_id_for("aerer")


def test_candidate_record_cannot_be_promoted_to_approved_without_review_model():
    valid = CandidateInfinitiveRecord(
        candidate_id=candidate_id_for("parler"),
        candidate_form="parler",
        suggested_groups=["first"],
        source_id=CANDIDATE_SOURCE_ID,
        source_commit=CANDIDATE_SOURCE_COMMIT,
    )
    assert valid.review_status == "candidate"
    with pytest.raises(ValidationError):
        CandidateInfinitiveRecord(
            candidate_id=candidate_id_for("parler"),
            candidate_form="parler",
            suggested_groups=["first"],
            source_id=CANDIDATE_SOURCE_ID,
            source_commit=CANDIDATE_SOURCE_COMMIT,
            review_status="approved",
        )


def test_candidate_import_preserves_mit_license_and_manifest(tmp_path: Path):
    license_text = "MIT License\n\nCopyright (c) 2018 Yann Rabiller\n\nPermission is hereby granted...\n"
    validated_license = validate_license(license_text.encode("utf-8"))
    records, stats = build_candidate_records(payload())
    source_bytes = json.dumps(payload(), ensure_ascii=False).encode("utf-8")

    outputs = write_inventory(records, stats, source_bytes, validated_license, tmp_path / "catalogs")
    manifest = json.loads(outputs["manifest"].read_text(encoding="utf-8"))

    assert outputs["candidates"].exists()
    assert outputs["license"].read_text(encoding="utf-8") == license_text
    assert outputs["notices"].exists()
    assert manifest["source_commit"] == CANDIDATE_SOURCE_COMMIT
    assert manifest["unique_candidate_count"] == len(records)
    assert manifest["conjugation_forms_imported"] is False


def test_git_blob_sha1_uses_git_object_header():
    # Known Git blob id for a byte string; ensures pin verification matches Git's object format.
    assert git_blob_sha1(b"test\n") == "9daeafb9864cf43055ae93beb0afd6c7d144bfa4"


def test_pinned_import_rejects_unrelated_local_files():
    with pytest.raises(ValueError, match="does not match the pinned upstream blob"):
        verify_pinned_source(b"fake verbs", b"fake license")
