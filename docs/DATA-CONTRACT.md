# Contrato de datos verbales — COQ

**Versión:** 1.0 (contrato técnico preliminar; no es todavía un catálogo lingüístico aprobado).

Este documento define cómo se representa un verbo, sus construcciones, el patrón morfológico, las formas excepcionales, las variantes y la evidencia de revisión. El motor de conjugación no se implementa en esta fase.

## 1. Principios obligatorios

1. Los identificadores internos son estables y distintos de las etiquetas visibles de la interfaz.
2. El infinitivo base se guarda sin el pronombre reflexivo: `parler`, no `se parler`. Las construcciones se registran por separado como `parler` y, si está validada, `se parler`.
3. El grupo verbal, la familia morfológica, el patrón de conjugación, la construcción y el auxiliar son campos diferentes. No deducir todos los datos de las últimas letras del infinitivo.
4. Una conjugación habitual se genera a partir de un patrón Python registrado. Las excepciones por verbo se expresan como sobrescrituras de forma exacta, no como código ejecutable almacenado en JSON.
5. El registro debe distinguir una forma que no existe/no se usa de una forma que aún no se ha revisado.
6. Toda variante aceptada en los ejercicios debe almacenarse explícitamente. La lista de formas válidas se usa tanto para mostrar variantes como para corregir respuestas.
7. Ningún verbo o forma no aprobado entra en ejercicios de producción. El perfil de `parler` de `frontend/verb-profiles.demo.json` es únicamente un fixture de interfaz y nunca se cargará como catálogo de producción.
8. Cada registro mantiene evidencia de procedencia. No se infieren licencias a partir de que una web sea accesible públicamente.

## 2. Entidades

### 2.1 `VerbRecord` — lema/infinitivo

| Campo | Tipo | Obligatorio | Significado |
|---|---|---:|---|
| `schema_version` | literal `1.0` | Sí | Versión del contrato del registro. |
| `verb_id` | ID estable, por ejemplo `v_parler` | Sí | Clave interna única. No cambiar porque cambie una etiqueta. |
| `infinitive` | string en minúsculas | Sí | Infinitivo base, con sus diacríticos franceses. No incluye `se`/`s'`. |
| `search_aliases` | lista de strings | No | Alias buscables confirmados, sin sustituir el infinitivo canónico. |
| `group_id` | `first`, `second`, `third` o `null` | No hasta revisión | Grupo gramatical. `null` significa no auditado, no un cuarto grupo. |
| `family_ids` | lista de IDs | Sí, puede estar vacía en borradores | Familias morfológicas aplicables. Un verbo puede tener más de una etiqueta si las categorías se solapan. |
| `pattern_id` | ID o `null` | No hasta revisión | Regla de conjugación registrada por el motor Python. |
| `regularity` | `regular`, `orthographic_alternation`, `irregular` | Sí | Describe el comportamiento del lema, no la calidad de su revisión. |
| `traits` | lista `impersonal`, `defective` | Sí | Etiquetas lingüísticas verificadas. |
| `review_status` | estado de revisión | Sí | Estado general del registro. |
| `default_construction_id` | ID | Sí | Construcción predeterminada cuando se busca el infinitivo sin prefijo pronominal. |
| `constructions` | lista de `ConstructionProfile` | Sí | Una o más construcciones con auxiliar, concordancia y disponibilidad propios. |
| `source_evidence` | lista de evidencias | Sí, puede estar vacía en borradores | Referencias y método usados para validar metadatos. |
| `notes` | string o `null` | No | Notas de revisión; no se usan como reglas ejecutables. |

El contrato evita una ambigüedad importante: un lema puede admitir formas pronominales y no pronominales. Cada una es una construcción separada. Para el filtro pedagógico de COQ, cada construcción aprobada tiene exactamente un auxiliar asignado; no se modelan alternancias de auxiliar por sentido dentro de una misma construcción en los ejercicios estándar.

### 2.2 `ConstructionProfile` — construcción

Contiene `construction_id`, `kind` (`non_pronominal` o `pronominal`), `display_infinitive`, `auxiliary`, `participle_agreement`, `review_status`, `form_overrides`, `availability_overrides`, `source_evidence` y `notes`.

Reglas compatibles con las decisiones pedagógicas aprobadas:

| Construcción | Auxiliar COQ | Política de participio pasado |
|---|---|---|
| No pronominal con AVOIR | `avoir` | `invariable` (simplificación pedagógica explícita de COQ) |
| No pronominal con ÊTRE | `etre` | `subject` |
| Pronominal | `etre` | `verb_specific`, revisada por verbo/construcción |

Una combinación que contradice estas reglas se rechaza en la validación del modelo. La regla pedagógica no debe presentarse como exposición exhaustiva de la gramática francesa.

### 2.3 `ConjugationPattern` — patrón de conjugación

Campos: `pattern_id`, `group_id`, `family_id`, `algorithm_key`, `algorithm_version`, `model_verb_id` opcional, `review_status`, `source_evidence` y `notes`.

- `algorithm_key` solo puede apuntar a una implementación registrada explícitamente en Python. Nunca se interpreta como nombre de función importable desde un dato.
- Las familias de COQ son metadatos de clasificación; no se deduce que todos sus verbos compartan un algoritmo idéntico sin comprobarlo.
- Un patrón aprobado requiere evidencia de revisión y pruebas de regresión con verbos representativos y excepciones.

### 2.4 `FormOverride` — forma excepcional o variante

Cada sobrescritura especifica `form_id`, contexto opcional, `preferred_form`, lista `alternatives`, operación (`replace` o `add`), estado de revisión, evidencia y nota.

- `preferred_form` es la forma mostrada primero.
- `alternatives` contiene otras formas válidas, escritas exactamente como deben presentarse y aceptarse.
- Las formas se guardan como la forma verbal objetivo, no incluyen el sujeto ni la partícula del subjuntivo. Por ejemplo, el valor para el ejercicio puede ser `sois`, mientras la capa de presentación construye `que je sois`.
- Para `gérondif présent`, la forma completa incluye `en`: `en parlant`.
- Los acentos se preservan estrictamente. Solo se normalizan mayúsculas, espacios exteriores/duplicados y apóstrofo recto/tipográfico durante la corrección.
- Las formas compuestas pueden tener sobrescrituras concretas por persona y contexto de género/número.
- `participe_passe` existe como forma base interna para generar tiempos compuestos, pero no es una opción independiente del menú de consulta en esta fase.

### 2.5 `FormAvailability` — disponibilidad

Registra `form_id`, contexto, estado (`available`, `unavailable`, `not_reviewed`), motivo y evidencia.

- No tener una fila de conjugación no demuestra que una forma no exista.
- Los verbos impersonales y defectivos requieren restricciones explícitas o un patrón de disponibilidad aprobado.
- Una forma `unavailable` requiere motivo y evidencia.
- Las formas `not_reviewed` no se muestran como válidas ni se incluyen en ejercicios.
- La consulta muestra solo las conjugaciones disponibles verificadas. El generador solo muestrea formas aprobadas.

### 2.6 `SourceEvidence` — procedencia

Campos: `source_id`, `authority`, `label`, URL, `method`, `scopes`, fecha de consulta, edición/versión y, si corresponde, licencia, URL de licencia y versión del conjunto de datos.

Métodos admitidos: `manual_reference_check`, `licensed_dataset`, `linguistic_owner_approval` y `coq_rule_review`. No existe un método de extracción automática de la Académie.


### 2.7 `CandidateInfinitiveRecord` — cola de revisión, no verbo de producción

`data/catalogs/candidate-infinitives.jsonl` usa un modelo separado para nombres procedentes de una fuente auxiliar. Incluye `candidate_id` estable, `candidate_form`, `suggested_groups`, `source_id`, `source_commit`, `review_status="candidate"`, `group_suggestions_are_unverified=true` y `requires_lemma_review=true`. Este tipo no tiene campos de conjugación y no puede convertirse de manera automática en `VerbRecord` ni en un registro aprobado.

El importador está fijado a un commit y valida los Git blob SHA del JSON y del aviso de licencia antes de generar los registros. El manifiesto conserva hashes, número de entradas originales, deduplicaciones y procedencia. Los tokens importados pueden contener errores o grupos discutibles: solo sirven como lista de trabajo. La evidencia para un `VerbRecord` revisado debe generarse de nuevo durante la revisión lingüística.

Las expectativas generales de terminación y las excepciones declaradas del auditor se almacenan en `candidate-audit-rules.json`, validadas por un modelo Pydantic y exportadas a JSON Schema. No se codifican excepciones por infinitivo dentro del algoritmo.

Las decisiones individuales de revisión se almacenan en `lemma-review-decisions.jsonl`. El motor de auditoría no debe incluir condicionales por infinitivo (`if lemma == ...`). Cada decisión identifica el token fuente, el lema canónico o lema relacionado, la forma visible, el grupo, la política de construcción, la evidencia de fuentes (`source_evidence`) y los códigos de hallazgo que resuelve explícitamente. Los tokens fuente que no se aceptan como lemas canónicos de COQ usan `source_token_not_canonical_lemma`; esta clasificación de catálogo no pretende negar todos los usos lingüísticos posibles del token. El informe conserva los hallazgos brutos y separa `resolved_flags` de `open_flags`, de modo que una decisión no borra el historial ni se confunde con una aprobación de formas.

### Recetas estructurales de tiempos compuestos

La constante `COMPOUND_AUXILIARY_TENSE` de `backend/app/domain/verb_contracts.py` fija una única receta auxiliar por tiempo compuesto:

| Tiempo compuesto | Tiempo del auxiliar | Forma base añadida |
|---|---|---|
| Passé composé | `present_indicatif` | `participe_passe` |
| Plus-que-parfait | `imparfait` | `participe_passe` |
| Conditionnel passé | `conditionnel_present` | `participe_passe` |
| Futur antérieur | `futur_simple` | `participe_passe` |
| Subjonctif passé | `subjonctif_present` | `participe_passe` |

Esta tabla define solo el tiempo del auxiliar. El auxiliar concreto (`avoir` o `être`), la construcción pronominal/no pronominal y la política de concordancia siempre vienen del perfil aprobado del verbo. No se duplica esta relación en los registros JSON ni en JavaScript.

## 3. Estados de revisión

| Estado | Uso |
|---|---|
| `draft` | Registro incompleto en edición. |
| `candidate` | Candidato pendiente de validación. |
| `metadata_reviewed` | Lema, grupo, familia y construcción revisados; las formas no se consideran automáticamente aprobadas. |
| `forms_reviewed` | Formas concretas revisadas, pero falta aprobación completa del registro o del patrón. |
| `approved` | Se puede usar en producción conforme a sus perfiles aprobados y las reglas de disponibilidad. |
| `rejected` | Registro que no debe utilizarse. |

La revisión de metadatos y la revisión de formas no son equivalentes. Un verbo puede tener un grupo verificado pero conservar formas pendientes.

## 4. Formas y contextos

IDs seleccionables, sin etiquetas dentro de la clave:

- Tiempos/modos: `present_indicatif`, `imperatif_present`, `imparfait`, `conditionnel_present`, `futur_simple`, `subjonctif_present`, `passe_compose`, `plus_que_parfait`, `conditionnel_passe`, `futur_anterieur`, `subjonctif_passe`.
- Formas no personales: `participe_present`, `gerondif_present`.
- Base interna no seleccionable: `participe_passe`.

El contexto de persona usa una de las nueve personas aprobadas por COQ (`je`, `tu`, `il`, `elle`, `on`, `nous`, `vous`, `ils`, `elles`). En sobrescrituras, disponibilidad específica y preguntas de tiempo compuesto, el género/número deben ser explícitos. Para `on`, COQ permite masculino singular, masculino plural y femenino plural; no femenino singular. Para `vous`, el singular exige `usage=courtesy` y el plural no puede usar esa marca. Las combinaciones persona/género/número incompatibles se rechazan en Pydantic.

## 5. Familias, grupos y colecciones

La clasificación visible del selector no debe codificarse como lógica de conjugación. IDs que deben mantenerse estables:

- Scope virtual de todos los verbos aprobados: `all:approved_verbs`. En la UI, la opción vacía «Todos los grupos y familias» se transforma en ese ID al construir la petición de práctica; no significa incluir candidatos pendientes.
- Grupos: `group:1`, `group:2`, `group:3`.
- Familias morfológicas: `family:first_regular`, `family:ger`, `family:cer`, `family:eler`, `family:eter`, `family:yer`, `family:e_grave`, `family:second_ir` (clasificación interna), `family:third_ir`, `family:dre`, `family:indre_aindre_oindre`, `family:uire`, `family:oir_oire`.
- Colecciones editoriales pendientes: `collection:common_100` y `collection:third_group_future_families`.

La definición central de opciones se almacena en `data/catalogs/scopes.jsonl`; los metadatos de patrones registrados están en `data/catalogs/patterns.jsonl`. Ambos catálogos de arranque están en estado `planned`/`draft`: describen la taxonomía y no habilitan ejercicios. Los IDs visibles no deben reconstruirse a partir de etiquetas en el frontend.

«100 verbos más comunes» es una colección curada, no una familia morfológica. Debe seguir desactivada para la generación de ejercicios hasta que sus miembros sean definidos. La opción de futuras familias tampoco habilita prácticas mientras no exista una membresía aprobada.

Cada familia activa debe indicar su grupo y el método de membresía: patrones registrados, lista de verbos revisada o combinación explícitamente definida. No se consideran correctas las familias cuyas membresías solo se hayan inferido por terminación.

## 6. Fuente de verdad y formato de almacenamiento

- Fuente de verdad: registros JSON Lines (JSONL), un `VerbRecord` por línea en `data/catalogs/verbs.jsonl`, ordenados por `verb_id`. Los cambios producen diffs por registro, fáciles de revisar.
- Patrones y scopes son catálogos JSONL separados y versionados (`patterns.jsonl`, `scopes.jsonl`), no duplicados en todos los verbos. Un `all:approved_verbs` virtual permite representar la opción de la UI «Todos los grupos y familias» sin introducir un cuarto grupo gramatical.
- `scripts/validate_catalog.py` verifica JSONL, IDs únicos, referencias a patrones/familias/grupos y que ningún scope activo se quede sin miembros aprobados. La ausencia de `verbs.jsonl` se indica explícitamente; `--require-production-ready` debe usarse como gate de publicación cuando exista un catálogo real. El resultado está definido por `CatalogValidationReport` (`backend/app/domain/catalog_validation_report.py`), con contadores obligatorios para verbos, aprobados, candidatos, decisiones de revisión, patrones y scopes; su JSON Schema se exporta como `catalog-validation-report.schema.json`.
- El backend carga los registros validados al iniciar y mantiene índices en memoria mientras el volumen sea adecuado. Solo se añadirá SQLite como índice/almacén de ejecución si las pruebas de rendimiento lo justifican; SQLite no será otra fuente manual de verdad.
- El catálogo de producción no se rellena con el fixture de `parler`, ni con resultados de pruebas, ni con datos del repositorio experimental anterior.
- Las fuentes deben verificarse por licencia antes de incorporarse. Un enlace a una fuente no equivale a permiso para copiar un conjunto de datos completo.
- La cola `candidate-infinitives.jsonl` nunca se consulta desde los endpoints de producción. Su estado y sus sugerencias no habilitan conjugación, perfil ni ejercicios. La fuente de formas conjugadas para producción sigue pendiente de selección/licencia.

## 7. Puertas de calidad antes de aprobar un registro

1. ID único e infinitivo canónico.
2. Grupo, familia y patrón asignados con evidencia.
3. Cada construcción tiene auxiliar/política de concordancia coherentes con COQ y revisados.
4. Participio presente, participio pasado y variantes importantes revisados.
5. Disponibilidad de formas identificada para los defectivos e impersonales.
6. Pruebas de regresión para formas simples, compuestas, acentos, alternativas y los contextos de género/número pertinentes.
7. Ninguna forma no revisada aparece en ejercicios.
8. Cada tiempo compuesto declara una de las cinco recetas de auxiliar aprobadas; el auxiliar específico sale del perfil de construcción.
9. Las sobrescrituras y los estados de disponibilidad con contexto para un tiempo compuesto tienen persona y género/número explícitos.
10. La evidencia y procedencia permiten volver a la fuente original.


## Decisión explícita de lema pendiente de formas

`data/catalogs/lemma-review-decisions.jsonl` contiene decisiones del responsable lingüístico sobre identidad canónica y metadatos que aún no constituyen un `VerbRecord` de producción. Cada decisión mantiene la referencia al token importado. La decisión `LR-038` fija `entrehaïr` como lema técnico, `s'entrehaïr` como única forma visible, grupo segundo y construcción solo pronominal. `LR-039` conserva `fiche` como token de fuente no canónico para COQ y lo relaciona con `ficher`: la tabla de la Académie muestra `je fiche`, pero la entrada lexicográfica también registra un infinitivo `fiche` en un uso popular/vulgar desaconsejado. `LR-040` registra `s'en fiche` como forma dentro de la construcción `s'en ficher`, no como lema independiente. Las fuentes se guardan explícitamente en cada decisión y ninguna de estas decisiones aprueba formas conjugadas ni habilita consulta o ejercicios.
