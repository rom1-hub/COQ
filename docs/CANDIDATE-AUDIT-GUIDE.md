# Guía para revisar el inventario de infinitivos candidatos

## Objetivo

Los 7.075 tokens importados desde `einenlum/french-verbs-list` son **candidatos**, no 7.075 verbos confirmados. El script `scripts/audit_candidate_infinitives.py` genera señales explicables para ordenar la revisión. No modifica los tokens, no elimina candidatos, no decide la familia definitiva y no aprueba verbos.

## Ejecución

Desde la raíz de COQ, después de ejecutar `scripts/import_candidate_infinitives.py`:

```powershell
.\.venv\Scripts\python.exe scripts\audit_candidate_infinitives.py
```

El auditor lee sus expectativas de terminación desde `data/catalogs/candidate-audit-rules.json`; el algoritmo no contiene reglas `if infinitivo == ...`. Las excepciones léxicas de las heurísticas se declaran en ese registro. Para probar una versión alternativa de las reglas, puede usarse `--rules ruta.json`.

Por defecto, si existe `data/catalogs/lemma-review-decisions.jsonl`, el auditor también carga esas decisiones declarativas y las aplica por `source_candidate_id`. Se puede indicar otro archivo explícitamente con `--decisions ruta.jsonl`.

Los informes aparecen en `data/catalogs/`:

- `candidate-infinitives-audit-summary.json`: totales por tipo de alerta y prioridad.
- `candidate-infinitives-audit.csv`: formato apto para filtrar y revisar manualmente.
- `candidate-infinitives-audit.jsonl`: representación estructurada de cada candidato y sus alertas.

El informe conserva `flags` como hallazgos heurísticos originales y añade `resolved_flags` y `open_flags`. Una decisión humana solo resuelve los códigos que enumera en `resolves_findings`; el auditor no contiene excepciones específicas por infinitivo. Las decisiones también incorporan lema canónico, forma visible, grupo y política de construcción, pero no aprueban las formas conjugadas ni habilitan producción.

## Qué significa cada prioridad

- `priority_review`: la terminación parece contradecir las expectativas declaradas para el grupo, hay una terminación no reconocida por las heurísticas, el origen sugiere varios grupos o hay símbolos no alfabéticos. Revisar primero.
- `manual_review`: contiene guion, espacios o apóstrofos. Puede ser legítimo, pero la forma canónica necesita revisión.
- `basic_review`: no saltó ninguna de las heurísticas básicas. Sigue siendo candidato pendiente; no equivale a aprobado.

## Limitaciones lingüísticas

Las reglas sobre terminaciones son deliberadamente aproximadas. Para la detección de terminaciones, `-ïr` y `-ir` pertenecen a la misma clase de terminación; esto no elimina el diacrítico de la grafía canónica ni determina por sí solo el grupo gramatical. Por ejemplo, que un verbo termine en `-ir` o `-ïr` no prueba que pertenezca al segundo grupo: se debe revisar el participio presente y su paradigma. Del mismo modo, el grupo `-er` no basta por sí solo para decidir que un token es un infinitivo canónico. Las formas pronominales, los verbos defectivos/impersonales, las variantes, las familias ortográficas, los auxiliares y las formas conjugadas requieren decisiones y evidencia independientes.

No se debe pasar automáticamente ningún candidato a `data/catalogs/verbs.jsonl`. Un futuro proceso de aprobación deberá dejar evidencia, revisión lingüística y pruebas de regresión.


## Decisión lingüística registrada: `s'entrehaïr`

La arquitectura del auditor usa reglas generales en `candidate-audit-rules.json` y decisiones léxicas declarativas en `lemma-review-decisions.jsonl`. La evidencia de cada decisión se registra en `source_evidence`; no se crean ramas de código por infinitivo.

La decisión `LR-038` registra `entrehaïr` como lema técnico canónico y `s'entrehaïr` como única forma visible. En el registro de decisión declara que resuelve el hallazgo de guion del token fuente; el informe conserva ese hallazgo histórico en `flags` y lo separa de `open_flags`. Esta resolución viaja como dato revisable y no incorpora una rama especial al código. No se conserva el guion en el lema ni en la forma visible. Se clasifica en el segundo grupo y su construcción es siempre pronominal. El token de origen `entre-haïr` se mantiene únicamente para trazabilidad de la importación, no como variante que se muestra o se acepta.

Esta decisión aprueba los metadatos indicados, no las formas conjugadas: `forms_review_status` sigue en `pending` y el registro no está aprobado para producción. Las alertas del auditor sobre guiones continúan siendo pistas de revisión para otros candidatos.


## Decisiones léxicas sobre `ficher`

- `LR-039`: el token fuente `fiche` no se incorpora como lema canónico general de COQ y se relaciona con `ficher`. La tabla de conjugación de la Académie registra `je fiche`; su entrada léxica también menciona el infinitivo `fiche` en un uso popular/vulgar desaconsejado. La decisión, por tanto, es una política de canonización del catálogo COQ, no una afirmación de que la forma nunca se use como infinitivo.
- `LR-040`: `s'en fiche` se registra como observación editorial de la construcción `s'en ficher`, no como nuevo lema.
- Las evidencias aparecen en `source_evidence`, con URL, clase de fuente, afirmación respaldada y fecha de consulta. Ninguna de estas decisiones valida aún las conjugaciones de `ficher`.
