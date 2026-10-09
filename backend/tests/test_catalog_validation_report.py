import pytest
from pydantic import ValidationError

from app.domain.catalog_validation_report import CatalogValidationReport


def sample_report(**overrides):
    values = {
        "valid": True,
        "ready_for_production": False,
        "verb_count": 0,
        "approved_verb_count": 0,
        "candidate_infinitive_count": 7075,
        "lemma_review_decision_count": 1,
        "pattern_count": 14,
        "scope_count": 19,
        "warnings": ["Production verbs.jsonl is not populated yet."],
        "errors": [],
    }
    values.update(overrides)
    return values


def test_validation_report_requires_every_counter_including_review_decisions():
    payload = sample_report()
    del payload["lemma_review_decision_count"]
    with pytest.raises(ValidationError, match="lemma_review_decision_count"):
        CatalogValidationReport.model_validate(payload)


def test_validation_report_has_stable_required_counts():
    report = CatalogValidationReport.model_validate(sample_report())
    assert report.lemma_review_decision_count == 1
    assert report.candidate_infinitive_count == 7075
    assert report.model_dump(mode="json")["scope_count"] == 19


def test_validation_report_rejects_more_approved_verbs_than_total_verbs():
    with pytest.raises(ValidationError, match="approved_verb_count cannot exceed verb_count"):
        CatalogValidationReport.model_validate(sample_report(verb_count=1, approved_verb_count=2))


def test_validation_report_cannot_be_ready_with_errors_or_zero_approved_verbs():
    with pytest.raises(ValidationError, match="cannot be ready for production"):
        CatalogValidationReport.model_validate(
            sample_report(valid=False, ready_for_production=True, errors=["invalid record"], verb_count=1)
        )
    with pytest.raises(ValidationError, match="must contain an approved verb"):
        CatalogValidationReport.model_validate(sample_report(ready_for_production=True))


def test_validation_report_rejects_extra_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CatalogValidationReport.model_validate(sample_report(unexpected_counter=8))


def test_exported_validation_report_schema_keeps_the_required_decision_counter():
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[2]
    schema = json.loads((root / "data" / "catalogs" / "catalog-validation-report.schema.json").read_text(encoding="utf-8"))
    assert "lemma_review_decision_count" in schema["properties"]
    assert "lemma_review_decision_count" in schema["required"]
