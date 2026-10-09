# Catálogos COQ

El contrato de datos está definido en [`docs/DATA-CONTRACT.md`](../../docs/DATA-CONTRACT.md). El catálogo de verbos de producción todavía no está poblado.

- `verbs.jsonl` será la fuente canónica: un `VerbRecord` JSON por línea, validado con Pydantic y ordenado por `verb_id`. Solo entradas revisadas según las puertas de calidad pueden pasar a `approved`.
- `candidate-infinitives.jsonl` es una cola de lemas candidatos proveniente de una lista MIT fijada a un commit exacto. No es catálogo de producción; cada registro conserva `review_status=candidate` y las sugerencias de grupo quedan explícitamente sin verificar. El archivo se crea al ejecutar `py scripts/import_candidate_infinitives.py` con acceso a Internet.
- `candidate-lexicon-manifest.json` registra commit, hashes, conteos y advertencias de la fuente. `licenses/french-verbs-list-MIT.txt` preserva el aviso de licencia; `THIRD_PARTY_NOTICES.md` documenta el uso limitado. No borrar estos avisos si se conservan los candidatos importados.
- `patterns.jsonl` define IDs de patrones y claves previstas de algoritmo. Las entradas iniciales son `draft`; una clave no implica que el algoritmo ya exista o esté aprobado.
- `scopes.jsonl` define IDs estables y etiquetas para grupos, familias, colecciones y `all:approved_verbs`. Los scopes iniciales están `planned`, porque aún no hay miembros aprobados.
- Los esquemas JSON (`verb-record.schema.json`, `conjugation-pattern.schema.json`, `catalog-scope.schema.json` y `candidate-infinitive.schema.json`) se generan desde los modelos Pydantic.
- Ejecutar `py scripts/validate_catalog.py` (con `PYTHONPATH=backend` si la instalación no define el path) para comprobar IDs y referencias. Antes de una publicación que necesite catálogo real, ejecutar también `py scripts/validate_catalog.py --require-production-ready`.
- Los perfiles de prueba de la interfaz en `frontend/verb-profiles.demo.json` no pertenecen al catálogo de producción y no deben importarse.
- No añadir registros `approved` sin evidencia de procedencia y revisión de formas.
- No extraer automáticamente tablas de conjugación de la Académie française; consultar `docs/DATA-SOURCE-AUDIT.md`.


## Auditoría de candidatos

Ejecutar `py scripts/audit_candidate_infinitives.py` después de importar `candidate-infinitives.jsonl`. Los informes de salida son una cola de revisión, nunca una fuente de producción. Ningún candidato se promueve automáticamente.

- `lemma-review-decisions.jsonl` usa el contrato 1.3. Cada decisión puede conservar `source_evidence` con fuente, URL HTTPS, afirmación respaldada y fecha de consulta. `source_token_not_canonical_lemma` significa que el token no se incorpora como lema canónico general de COQ; no afirma que todos sus usos sean imposibles en la lengua.
