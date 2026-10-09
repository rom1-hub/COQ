from __future__ import annotations

import json
from pathlib import Path

from app.domain.candidate_lexicon import candidate_id_for
from app.domain.lemma_review_decisions import LemmaReviewDecision
from scripts.validate_catalog import validate_catalog

ROOT = Path(__file__).resolve().parents[2]
CATALOG_DIR = ROOT / "data" / "catalogs"


def test_parler_pilot_decision_is_explicitly_pending_and_not_production_approved() -> None:
    decision_path = CATALOG_DIR / "lemma-review-decisions.jsonl"
    decisions = [
        json.loads(line)
        for line in decision_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    payload = next(item for item in decisions if item["decision_id"] == "LR-041")
    decision = LemmaReviewDecision.model_validate(payload)

    assert decision.source_candidate_form == "parler"
    assert decision.source_candidate_id == candidate_id_for("parler")
    assert decision.canonical_infinitive == "parler"
    assert decision.group_id.value == "first"
    assert decision.forms_review_status == "pending"
    assert decision.approved_for_production is False

    report = validate_catalog(CATALOG_DIR)
    assert report["valid"] is True, report["errors"]
    assert report["ready_for_production"] is False
    assert report["verb_count"] == 0
    assert report["approved_verb_count"] == 0
    assert report["lemma_review_decision_count"] == 4
