"""Strict JSONL loader for COQ's approved production verb catalogue."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from pydantic import ValidationError

from app.domain.verb_contracts import (
    ConjugationPattern,
    ReviewStatus,
    VerbRecord,
)

ModelT = TypeVar("ModelT")


class CatalogLoadError(RuntimeError):
    """Raised when a production catalogue file exists but cannot be validated."""


DEFAULT_CATALOG_DIRECTORY = Path(__file__).resolve().parents[3] / "data" / "catalogs"


def _read_jsonl(path: Path, model_type: type[ModelT]) -> tuple[tuple[ModelT, ...], bool]:
    """Read one JSON record per line. Missing files mean an unpopulated catalogue."""
    if not path.exists():
        return (), False

    records: list[ModelT] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    records.append(model_type.model_validate(json.loads(line)))  # type: ignore[attr-defined]
                except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                    raise CatalogLoadError(
                        f"Invalid catalogue record at {path.name}:{line_number}"
                    ) from exc
    except OSError as exc:
        raise CatalogLoadError(f"Cannot read catalogue file {path.name}") from exc
    return tuple(records), True


class JsonlCatalogRepository:
    """Read-only repository for canonical verbs and registered pattern metadata.

    Candidate-infinitive and audit files are deliberately never read here.
    """

    def __init__(self, catalog_directory: Path | str = DEFAULT_CATALOG_DIRECTORY) -> None:
        self.catalog_directory = Path(catalog_directory)
        self.verbs, self.verbs_file_present = _read_jsonl(
            self.catalog_directory / "verbs.jsonl", VerbRecord
        )
        self.patterns, self.patterns_file_present = _read_jsonl(
            self.catalog_directory / "patterns.jsonl", ConjugationPattern
        )

        self._verbs_by_id = self._unique_index(self.verbs, "verb_id", "verbs.jsonl")
        self._patterns_by_id = self._unique_index(self.patterns, "pattern_id", "patterns.jsonl")
        self.production_ready = self._has_approved_pair()

    @staticmethod
    def _unique_index(records: tuple[ModelT, ...], key: str, filename: str) -> dict[str, ModelT]:
        index: dict[str, ModelT] = {}
        for record in records:
            identifier = str(getattr(record, key))
            if identifier in index:
                raise CatalogLoadError(f"Duplicate {key} in {filename}")
            index[identifier] = record
        return index

    def _has_approved_pair(self) -> bool:
        if not self.verbs_file_present:
            return False
        for verb in self.verbs:
            if verb.review_status != ReviewStatus.APPROVED or not verb.pattern_id:
                continue
            pattern = self._patterns_by_id.get(verb.pattern_id)
            if pattern is None or pattern.review_status != ReviewStatus.APPROVED:
                continue
            if any(
                construction.review_status == ReviewStatus.APPROVED
                for construction in verb.constructions
            ):
                return True
        return False

    def verb_by_id(self, verb_id: str) -> VerbRecord | None:
        return self._verbs_by_id.get(verb_id)  # type: ignore[return-value]

    def pattern_by_id(self, pattern_id: str) -> ConjugationPattern | None:
        return self._patterns_by_id.get(pattern_id)  # type: ignore[return-value]


@lru_cache(maxsize=1)
def get_catalog_repository() -> JsonlCatalogRepository:
    """Return a process-level snapshot; restart the API after changing catalogue files."""
    return JsonlCatalogRepository()
