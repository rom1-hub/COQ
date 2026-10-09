import hashlib
import json
import shutil

import pytest
from pathlib import Path

from scripts.validate_catalog import validate_catalog
from app.domain.verb_contracts import ScopeStatus, VerbGroup
from app.domain.candidate_lexicon import (
    CANDIDATE_SOURCE_COMMIT,
    CANDIDATE_SOURCE_ID,
    CandidateInfinitiveRecord,
    candidate_id_for,
)

ROOT = Path(__file__).resolve().parents[2]


def copy_registry(tmp_path: Path) -> Path:
    catalog_dir = tmp_path / "catalogs"
    catalog_dir.mkdir()
    for name in ("patterns.jsonl", "scopes.jsonl"):
        shutil.copyfile(ROOT / "data" / "catalogs" / name, catalog_dir / name)
    return catalog_dir


def jsonl_objects(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, objects: list[dict]) -> None:
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in objects), encoding="utf-8")


def test_initial_catalog_registries_validate_without_production_verbs():
    result = validate_catalog(ROOT / "data" / "catalogs")
    assert result["valid"] is True
    assert result["ready_for_production"] is False
    assert result["verb_count"] == 0
    assert result["pattern_count"] == 14
    assert result["scope_count"] == 19
    assert any("not populated yet" in warning for warning in result["warnings"])


def test_active_scope_cannot_be_enabled_without_approved_members(tmp_path):
    catalog_dir = copy_registry(tmp_path)
    scopes_path = catalog_dir / "scopes.jsonl"
    scopes = jsonl_objects(scopes_path)
    all_scope = next(item for item in scopes if item["scope_id"] == "all:approved_verbs")
    all_scope["status"] = ScopeStatus.ACTIVE.value
    write_jsonl(scopes_path, scopes)

    result = validate_catalog(catalog_dir)
    assert result["valid"] is False
    assert any("Active scope all:approved_verbs has no approved verb members" in error for error in result["errors"])


def test_scope_cannot_reference_an_unknown_pattern(tmp_path):
    catalog_dir = copy_registry(tmp_path)
    scopes_path = catalog_dir / "scopes.jsonl"
    scopes = jsonl_objects(scopes_path)
    ger_scope = next(item for item in scopes if item["scope_id"] == "family:ger")
    ger_scope["pattern_ids"] = ["unknown_pattern"]
    write_jsonl(scopes_path, scopes)

    result = validate_catalog(catalog_dir)
    assert result["valid"] is False
    assert any("family:ger: unknown pattern_id unknown_pattern" in error for error in result["errors"])


def test_linguistic_owner_lemma_decision_uses_one_pronominal_spelling_and_is_not_production_ready():
    result = validate_catalog(ROOT / "data" / "catalogs")
    decisions = jsonl_objects(ROOT / "data" / "catalogs" / "lemma-review-decisions.jsonl")

    assert len(decisions) == 3
    decision = next(item for item in decisions if item["decision_id"] == "LR-038")
    assert decision["canonical_infinitive"] == "entrehaïr"
    assert decision["display_infinitive"] == "s'entrehaïr"
    assert decision["group_id"] == "second"
    assert decision["construction_policy"] == "pronominal_only"
    assert decision["forms_review_status"] == "pending"
    assert decision["approved_for_production"] is False
    assert result["valid"] is True
    assert result["ready_for_production"] is False
    assert result["lemma_review_decision_count"] == 3



def test_fiche_and_s_en_fiche_are_noncanonical_tokens_with_academie_evidence():
    decisions = jsonl_objects(ROOT / "data" / "catalogs" / "lemma-review-decisions.jsonl")
    by_id = {item["decision_id"]: item for item in decisions}
    fiche = by_id["LR-039"]
    s_en_fiche = by_id["LR-040"]

    assert fiche["decision_outcome"] == "source_token_not_canonical_lemma"
    assert fiche["related_lemma"] == "ficher"
    assert fiche["forms_review_status"] == "not_applicable"
    assert any("conjuguer/A9F0671" in item["source_url"] for item in fiche["source_evidence"])
    # Preserve the Académie's nuance: fiche is also attested as a discouraged
    # popular/vulgar infinitive in a separate use, so the decision is not an
    # absolute claim that the form can never function as an infinitive.
    assert any("article/A9F0671" in item["source_url"] for item in fiche["source_evidence"])
    assert "desaconseja" in fiche["decision_note"]

    assert s_en_fiche["decision_scope"] == "editorial_observation"
    assert s_en_fiche["decision_outcome"] == "source_token_not_canonical_lemma"
    assert s_en_fiche["related_lemma"] == "ficher"
    assert s_en_fiche["related_construction"] == "s'en ficher"
    assert s_en_fiche["approved_for_production"] is False
    assert len(s_en_fiche["source_evidence"]) == 2


def test_lemma_review_decision_rejects_hyphenated_display_form():
    from app.domain.lemma_review_decisions import LemmaReviewDecision

    decision = jsonl_objects(ROOT / "data" / "catalogs" / "lemma-review-decisions.jsonl")[0]
    decision["display_infinitive"] = "s'entre-haïr"
    with pytest.raises(Exception, match="no hyphenated variant is accepted"):
        LemmaReviewDecision.model_validate(decision)



def test_pronominal_marker_contract_supports_se_and_s_apostrophe_without_verb_specific_logic():
    from app.domain.lemma_review_decisions import LemmaReviewDecision
    from app.domain.candidate_lexicon import candidate_id_for

    base = {
        "schema_version": "1.3",
        "decision_id": "LR-901",
        "source_candidate_id": candidate_id_for("laver"),
        "source_candidate_form": "laver",
        "canonical_infinitive": "laver",
        "display_infinitive": "se laver",
        "group_id": "first",
        "construction_policy": "pronominal_only",
        "pronominal_marker": "se",
        "resolves_findings": [],
        "decision_outcome": "lemma_metadata_reviewed",
        "forms_review_status": "pending",
        "decision_authority": "linguistic_owner",
        "decision_note": "Prueba de contrato para el marcador pronominal se.",
        "approved_for_production": False,
    }
    assert LemmaReviewDecision.model_validate(base).display_infinitive == "se laver"
    elided = dict(
        base,
        decision_id="LR-902",
        source_candidate_id=candidate_id_for("habiller"),
        source_candidate_form="habiller",
        canonical_infinitive="habiller",
        display_infinitive="s'habiller",
        pronominal_marker="s'",
    )
    assert LemmaReviewDecision.model_validate(elided).display_infinitive == "s'habiller"
    invalid = dict(base, pronominal_marker=None)
    with pytest.raises(Exception, match="must declare pronominal_marker"):
        LemmaReviewDecision.model_validate(invalid)



def test_editorial_observation_needs_no_imported_source_candidate_but_related_lemma_must_exist(tmp_path):
    """Editorial observations describe a source token, not an imported candidate row.

    Candidate-scoped decisions must resolve to an imported row. Editorial
    observations (for example, a conjugated expression such as “s'en fiche”)
    intentionally have no source_candidate_id, but their related canonical
    lemma must exist in the candidate inventory when that inventory is present.
    """
    catalog_dir = copy_registry(tmp_path)
    shutil.copyfile(
        ROOT / "data" / "catalogs" / "lemma-review-decisions.jsonl",
        catalog_dir / "lemma-review-decisions.jsonl",
    )

    records = [
        CandidateInfinitiveRecord(
            candidate_id=candidate_id_for("entre-haïr"),
            candidate_form="entre-haïr",
            suggested_groups=[VerbGroup.SECOND],
            source_commit=CANDIDATE_SOURCE_COMMIT,
        ),
        CandidateInfinitiveRecord(
            candidate_id=candidate_id_for("fiche"),
            candidate_form="fiche",
            suggested_groups=[VerbGroup.FIRST],
            source_commit=CANDIDATE_SOURCE_COMMIT,
        ),
        CandidateInfinitiveRecord(
            candidate_id=candidate_id_for("ficher"),
            candidate_form="ficher",
            suggested_groups=[VerbGroup.FIRST],
            source_commit=CANDIDATE_SOURCE_COMMIT,
        ),
    ]
    candidate_path = catalog_dir / "candidate-infinitives.jsonl"
    candidate_path.write_text(
        "".join(record.model_dump_json(exclude_none=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = {
        "dataset_id": CANDIDATE_SOURCE_ID,
        "source_commit": CANDIDATE_SOURCE_COMMIT,
        "unique_candidate_count": len(records),
        "candidate_output_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    }
    (catalog_dir / "candidate-lexicon-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    result = validate_catalog(catalog_dir)

    assert result["valid"] is True, result["errors"]
    assert result["lemma_review_decision_count"] == 3
    assert result["ready_for_production"] is False


def test_editorial_observation_related_lemma_must_be_present_when_inventory_exists(tmp_path):
    catalog_dir = copy_registry(tmp_path)
    shutil.copyfile(
        ROOT / "data" / "catalogs" / "lemma-review-decisions.jsonl",
        catalog_dir / "lemma-review-decisions.jsonl",
    )
    record = CandidateInfinitiveRecord(
        candidate_id=candidate_id_for("entre-haïr"),
        candidate_form="entre-haïr",
        suggested_groups=[VerbGroup.SECOND],
        source_commit=CANDIDATE_SOURCE_COMMIT,
    )
    candidate_path = catalog_dir / "candidate-infinitives.jsonl"
    candidate_path.write_text(record.model_dump_json(exclude_none=True) + "\n", encoding="utf-8")
    manifest = {
        "dataset_id": CANDIDATE_SOURCE_ID,
        "source_commit": CANDIDATE_SOURCE_COMMIT,
        "unique_candidate_count": 1,
        "candidate_output_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    }
    (catalog_dir / "candidate-lexicon-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    result = validate_catalog(catalog_dir)

    assert result["valid"] is False
    assert any("related lemma 'ficher' is missing" in error for error in result["errors"])
