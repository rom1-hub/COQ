# Contrato de API — COQ

**Versión:** `/api/v1`. **Estado:** están implementados `GET /api/v1/health`, `GET /api/v1/verbs/search` y `GET /api/v1/verbs/{verb_id}/conjugation`. La búsqueda y la consulta de conjugación utilizan exclusivamente el catálogo JSONL de producción y se cierran con `CATALOG_NOT_READY` cuando no hay datos aprobados.

Los modelos de petición/respuesta viven en `backend/app/api/contracts.py`; los modelos de datos del catálogo están en `backend/app/domain/verb_contracts.py`.

## 1. Convenciones

- JSON UTF-8; identificadores internos estables y separados de las etiquetas presentacionales.
- Solo datos aprobados se exponen en consultas públicas y prácticas. Los registros `draft`, `candidate`, `metadata_reviewed`, `forms_reviewed` y `rejected` no son elegibles para generar ejercicios.
- La interfaz no calcula grupo, familia, auxiliar, disponibilidad, conjugaciones ni respuestas correctas. Estas decisiones salen del backend/catálogo aprobado.
- Las formas variantes están en la misma lista de formas válidas: la consulta las muestra todas y el corrector las acepta todas. No se relajan los acentos.
- El frontend solo recibe las respuestas aceptadas después de enviar la respuesta correspondiente; nunca recibe la clave correcta junto con las preguntas iniciales.
- Los errores usan el enum `ApiErrorCode`; no se devuelve texto de excepción, ruta interna ni traceback.
- `participe_passe` es una forma base interna para componer tiempos, no un ID seleccionable. Los IDs seleccionables son los 11 tiempos/modos más `participe_present` y `gerondif_present`.

## 2. Endpoints implementados

### `GET /api/v1/health`

Devuelve el estado técnico, la disponibilidad del motor y si existe al menos un par verbo/patrón aprobado en el catálogo de producción. `production_catalog_ready=false` significa que las rutas dependientes de datos aprobados deben rechazar la consulta, no generar formas a partir de fixtures.

### `GET /api/v1/verbs/search?q={texto}&limit=10&exact=false`

Busca únicamente dentro de `verbs.jsonl`. `limit` debe estar entre 1 y 50. La búsqueda normal ordena: infinitivo canónico exacto, prefijo canónico, alias exacto y prefijo de alias. Los alias proceden de `VerbRecord.search_aliases`; no se infieren por terminaciones.

Con `exact=true`, solo se devuelven coincidencias exactas del infinitivo canónico o de un alias registrado. El cliente de interfaz utiliza esta modalidad para que una búsqueda parcial no termine seleccionando accidentalmente otro verbo. Un alias que resuelva a más de un verbo no se selecciona arbitrariamente.

La respuesta usa `VerbSearchResponse` y elementos `VerbSearchItem` (`verb_id`, infinitivo, etiqueta, grupo, familias y construcción predeterminada). Solo se devuelven registros de verbo aprobados para práctica, con patrón y construcción predeterminada aprobados. Una búsqueda válida sin coincidencias devuelve una lista vacía. Si el catálogo no está listo, responde HTTP 503 con `CATALOG_NOT_READY`.

La ruta no consulta `candidate-infinitives.jsonl`, auditorías ni decisiones léxicas pendientes.

### `GET /api/v1/verbs/{verb_id}/conjugation`

Acepta `form_id` como parámetro repetible y `construction_id` como parámetro opcional. Si se omite `form_id`, intenta devolver las formas seleccionables disponibles para la construcción aprobada.

La respuesta contiene las formas registradas por el backend. La interfaz agrupa las variantes de concordancia para mostrarlas en una única fila por sujeto; las variantes y el contexto original no se eliminan del contrato de datos. La capa de presentación añade el sujeto y `que` en los subjuntivos, y mantiene `en` en el gérondif.

La ruta no consume `frontend/verb-profiles.demo.json`, ni la lista de candidatos. Si el catálogo no contiene un verbo, una construcción y un patrón aprobados, responde con el código de error estable que corresponda; si no hay ningún par aprobado en el catálogo, responde HTTP 503 con `CATALOG_NOT_READY`.

## 3. Endpoints funcionales todavía propuestos

### `GET /api/v1/catalog/scopes`

Devuelve únicamente los grupos, familias y colecciones activas que pueden seleccionarse para practicar. No debe exponer como practicables colecciones `planned`, como «100 verbos más comunes» hasta que su membresía se defina y apruebe.

Respuesta propuesta: `ScopeListResponse` con `scope_id`, etiquetas, tipo, grupo asociado cuando corresponda, orden y estado activo. La opción sin filtro visible como «Todos los grupos y familias» se convierte a `scope_id="all:approved_verbs"`. Ese scope incluye solo registros aprobados; nunca el conjunto de candidatos completo.

### `GET /api/v1/verbs/{verb_id}/profile`

Devuelve el perfil aprobado necesario para los filtros de «Practicar»: grupo, familias, patrón, construcción(es) válidas, auxiliar por construcción, formas seleccionables disponibles y enlaces de referencia. La interfaz bloqueará grupo/familia, construcción y auxiliar a partir de este perfil y dejará editable el tiempo/forma. El perfil de demostración `parler` en el frontend no es respuesta de producción.

### `POST /api/v1/exercises`

Petición: `ExerciseCreateRequest`.

- Requiere exactamente una fuente de selección: `verb_id` o `scope_id` activo.
- Si se especifica un verbo, `construction_id` puede seleccionar una construcción aprobada de ese verbo; grupo, familia, construcción y auxiliar se derivan del perfil del servidor. No se aceptan filtros `construction`/`auxiliary` junto a `verb_id`.
- Si se especifica `scope_id`, no se permite `construction_id`; se pueden añadir filtros `construction` y `auxiliary` para seleccionar subconjuntos.
- `form_ids` es una lista no vacía, sin duplicados, de IDs seleccionables. La interfaz convierte «Todos los tiempos verbales» en la lista de formas seleccionables elegibles.
- `question_count` por defecto es 20; el límite técnico propuesto es 1–100.
- Para tiempos compuestos, cada pregunta debe llevar persona y contexto explícitos de género/número. Estos datos no se mostrarán como explicaciones en las tablas de «Ver conjugación».
- El generador muestrea solo construcciones, formas, sujetos y contextos aprobados y disponibles. Un verbo defectivo no genera preguntas para las personas/tiempos excluidos.

Respuesta propuesta: `ExerciseSessionResponse`, con `session_id` y preguntas sin respuestas correctas ni variantes aceptadas.

### `POST /api/v1/exercises/{session_id}/answers`

Petición: `ExerciseAnswerRequest` (`question_id`, `answer`). El backend recupera la clave desde la sesión, normaliza únicamente mayúsculas/minúsculas, espacios y tipo de apóstrofo, preservando acentos, y compara contra la lista completa de formas aprobadas.

Respuesta propuesta: `ExerciseAnswerResponse` indica si es correcta y, tras el envío, devuelve la forma preferida y todas las variantes aceptadas.

## 4. Códigos de error estables

- `INVALID_REQUEST`: filtros o formato incompatibles.
- `VERB_NOT_FOUND`: el ID o infinitivo no se encuentra entre los verbos aprobados.
- `VERB_NOT_APPROVED`: existe un registro, pero no está aprobado para el uso solicitado.
- `CONSTRUCTION_NOT_AVAILABLE`: la construcción no pertenece al verbo o no está aprobada.
- `FORM_NOT_AVAILABLE`: el verbo no tiene esa forma disponible y revisada.
- `CATALOG_NOT_READY`: el catálogo no tiene el contenido aprobado necesario para atender la consulta.
- `SCOPE_NOT_ACTIVE`: grupo/familia/colección ausente, pendiente o retirado.
- `INSUFFICIENT_QUESTIONS`: no existen suficientes preguntas elegibles con los filtros seleccionados.
- `SESSION_NOT_FOUND`: sesión inexistente o expirada.
- `QUESTION_NOT_IN_SESSION`: pregunta que no pertenece a esa sesión.

Formato de error: `ApiErrorResponse` con `code`, `message` apto para el usuario y `details` estructurado. No exponer respuestas correctas antes de enviar cada pregunta.

## 5. Persistencia y estado

La fuente de verdad del catálogo es JSONL validado mediante Pydantic. La sesión de práctica debe mantener respuestas correctas en el servidor. No elegir una sesión en memoria como solución de producción multiinstancia; antes del despliegue del generador se decidirá un almacén de sesiones adecuado al proveedor y su persistencia.

## 6. Criterios de aceptación

1. Los modelos de catálogo y los JSON Schema pasan validación automática.
2. La búsqueda solo devuelve registros de verbos, patrones y construcción predeterminada aprobados.
3. Las búsquedas exactas por infinitivo/alias nunca seleccionan arbitrariamente una coincidencia por prefijo ni un alias ambiguo.
4. Una consulta de verbo con formas alternativas las devuelve todas sin perder acentos.
5. La generación no produce preguntas de formas no disponibles ni de registros pendientes.
6. La respuesta inicial de una pregunta nunca contiene las formas correctas.
7. El corrector acepta las variantes registradas, no elimina tildes ni añade variantes por analogía.
8. Los IDs de grupos/familias/colecciones coinciden con los del selector.
