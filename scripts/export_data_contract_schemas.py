"""Export machine-readable JSON Schemas for the Pydantic COQ data contracts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.candidate_audit_rules import CandidateAuditRules  # noqa: E402
from app.domain.candidate_lexicon import CandidateInfinitiveRecord  # noqa: E402
from app.domain.catalog_validation_report import CatalogValidationReport  # noqa: E402
from app.domain.lemma_review_decisions import LemmaReviewDecision  # noqa: E402
from app.domain.verb_contracts import CatalogScope, ConjugationPattern, VerbRecord  # noqa: E402

DESTINATION = ROOT / "data" / "catalogs"
SCHEMAS = {
    "verb-record.schema.json": VerbRecord,
    "conjugation-pattern.schema.json": ConjugationPattern,
    "catalog-scope.schema.json": CatalogScope,
    "candidate-infinitive.schema.json": CandidateInfinitiveRecord,
    "lemma-review-decision.schema.json": LemmaReviewDecision,
    "candidate-audit-rules.schema.json": CandidateAuditRules,
    "catalog-validation-report.schema.json": CatalogValidationReport,
}


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        schema = model.model_json_schema(mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        path = DESTINATION / filename
        path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
