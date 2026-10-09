# Contrato de API — COQ

**Versión propuesta:** `/api/v1`. **Estado:** los modelos Pydantic están definidos; por ahora solo está implementado `GET /api/v1/health`. Las rutas funcionales descritas abajo no deben presentarse como operativas hasta que se implementen y pasen pruebas de integración.

Los modelos de petición/respuesta viven en `backend/app/api/contracts.py`; los modelos de datos del catálogo están en `backend/app/domain/verb_contracts.py`.

## 1. Convenciones

- JSON UTF-8; identificadores internos estables y separados de las etiquetas presentacionales.
- Solo datos aprobados se exponen en consultas públicas y prácticas. Los registros `draft`, `candidate`, `metadata_reviewed`, `forms_reviewed` y `rejected` no son elegibles para generar ejercicios.
- La interfaz no calcula grupo, familia, auxiliar, disponibilidad, conjugaciones ni respuestas correctas. Estas decisiones salen del backend/catálogo aprobado.
- Las formas variantes están en la misma lista de formas válidas: la consulta las muestra todas y el corrector las acepta todas. No se relajan los acentos.
- El frontend solo recibe las respuestas aceptadas después de enviar la respuesta correspondiente; nunca recibe la clave correcta junto con las preguntas iniciales.
- Los errores usan el enum `ApiErrorCode`; no se devuelve texto de excepción, ruta interna ni traceback.
- `participe_passe` es una forma base interna para componer tiempos, no un ID seleccionable. Los IDs seleccionables son los 11 tiempos/modos más `participe_present` y `gerondif_present`.

## 2. Endpoint implementado

### `GET /api/v1/health`

Devuelve el estado técnico y declara explícitamente si los contratos lingüísticos y el motor están disponibles. No implica que la conjugación real funcione.

## 3. Endpoints funcionales propuestos

### `GET /api/v1/catalog/scopes`

Devuelve únicamente los grupos, familias y colecciones activas que pueden seleccionarse para practicar. No debe exponer como practicables colecciones `planned`, como «100 verbos más comunes» hasta que su membresía se defina y apruebe.

Respuesta: `ScopeListResponse` con `scope_id`, etiquetas, tipo, grupo asociado cuando corresponda, orden y estado activo. La respuesta solo puede incluir scopes con estado `active`; los valores `planned` no se publican como opciones funcionales.

La opción sin filtro visible como «Todos los grupos y familias» se convierte a `scope_id="all:approved_verbs"`. Ese scope incluye solo registros aprobados, nunca el conjunto de candidatos completo. El scope global no representa un cuarto grupo gramatical.

### `GET /api/v1/verbs/search?q={texto}&limit=10`

Busca por infinitivo canónico y alias. `limit` entre 1 y 50; orden estable: coincidencia exacta, prefijo, luego otra coincidencia soportada explícitamente. Solo devuelve verbos aprobados. Una consulta sin resultados devuelve una lista vacía, no un error del servidor.

Respuesta: `VerbSearchResponse` con elementos `VerbSearchItem` (`verb_id`, infinitivo, etiqueta, grupo, familias y construcción predeterminada). No inferir un verbo nuevo a partir de una terminación ni conjugar una cadena desconocida.

### `GET /api/v1/verbs/{verb_id}/profile`

Devuelve el perfil aprobado necesario para los filtros de «Practicar»: grupo, familias, patrón, construcción(es) válidas, auxiliar por construcción, formas seleccionables disponibles y enlaces de referencia. Si el verbo no está aprobado, no se debe fingir que sus filtros están verificados.

Respuesta: `VerbProfileResponse`. La interfaz bloquea grupo/familia, construcción y auxiliar a partir de este perfil y deja editable el tiempo/forma. El perfil de demostración `parler` en el frontend no es respuesta de producción.

### `GET /api/v1/verbs/{verb_id}/conjugation`

Parámetros:

- `form_id`: parámetro repetible; si se omite, consulta todas las formas seleccionables que el verbo tenga aprobadas y disponibles.
- `construction_id`: opcional; por defecto usa la construcción predeterminada. Un `construction_id` que no pertenezca al verbo devuelve `CONSTRUCTION_NOT_AVAILABLE`.

Respuesta: `ConjugationLookupResponse`, agrupada en tablas. Cada fila incluye sujeto/contexto y `display_forms`, con las variantes de consulta. Para el subjonctif la vista construye el sujeto con `que` (`que je sois`); el valor que se solicita en la práctica es únicamente `sois`. Para el gérondif el objetivo completo es `en parlant`.

Las formas no disponibles se omiten de la tabla o se presentan como no disponibles solo cuando existe una regla de disponibilidad documentada. No completar huecos mediante analogía sin revisión.

### `POST /api/v1/exercises`

Petición: `ExerciseCreateRequest`.

- Requiere exactamente una fuente de selección: `verb_id` o `scope_id` activo.
- Si se especifica un verbo, `construction_id` puede seleccionar una construcción aprobada de ese verbo; grupo, familia, construcción y auxiliar se derivan del perfil del servidor. No se aceptan filtros `construction`/`auxiliary` junto a `verb_id`, porque esos controles deben estar bloqueados en la interfaz.
- Si se especifica `scope_id`, no se permite `construction_id`; se pueden añadir filtros `construction` y `auxiliary` para seleccionar subconjuntos.
- `form_ids` es una lista no vacía, sin duplicados, de IDs seleccionables. La interfaz convierte «Todos los tiempos verbales» en la lista de formas seleccionables elegibles.
- `question_count` por defecto es 20; el límite técnico de API propuesto es 1–100.
- Para tiempos compuestos, cada pregunta y fila de tabla debe llevar persona y contexto de género/número explícitos, incluso cuando la política pedagógica de COQ mantiene invariable el participio con `avoir`.
- El generador muestrea solo construcciones, formas, sujetos y contextos aprobados y disponibles. Un verbo defectivo no genera preguntas para las personas/tiempos excluidos.

Respuesta: `ExerciseSessionResponse`, con `session_id` y preguntas sin respuestas correctas ni variantes aceptadas.

### `POST /api/v1/exercises/{session_id}/answers`

Petición: `ExerciseAnswerRequest` (`question_id`, `answer`). El backend recupera la clave desde la sesión, normaliza únicamente mayúsculas/minúsculas, espacios y el tipo de apóstrofo, preservando acentos, y compara contra la lista completa de formas aprobadas.

Respuesta: `ExerciseAnswerResponse` indica si es correcta y, tras el envío, devuelve la forma preferida y todas las variantes aceptadas para la revisión del estudiante.

## 4. Códigos de error estables

- `INVALID_REQUEST`: filtros o formato incompatibles.
- `VERB_NOT_FOUND`: el ID o infinitivo no se encuentra.
- `VERB_NOT_APPROVED`: existe un candidato, pero no está aprobado para el uso solicitado.
- `CONSTRUCTION_NOT_AVAILABLE`: la construcción no pertenece al verbo o no está aprobada.
- `FORM_NOT_AVAILABLE`: el verbo no tiene esa forma disponible y revisada.
- `SCOPE_NOT_ACTIVE`: grupo/familia/colección ausente, pendiente o retirado.
- `INSUFFICIENT_QUESTIONS`: no existen suficientes preguntas elegibles con los filtros seleccionados.
- `SESSION_NOT_FOUND`: sesión inexistente o expirada.
- `QUESTION_NOT_IN_SESSION`: pregunta que no pertenece a esa sesión.

Formato de error: `ApiErrorResponse` con `code`, `message` apto para el usuario y `details` estructurado. No exponer respuestas correctas antes de enviar cada pregunta.

## 5. Persistencia y estado

La fuente de verdad del catálogo es JSONL validado mediante Pydantic. La sesión de práctica debe mantener respuestas correctas en el servidor. No elegir una sesión en memoria como solución de producción multiinstancia; antes del despliegue del generador se decidirá un almacén de sesiones adecuado al proveedor y su persistencia.

## 6. Criterios de aceptación antes de implementar los endpoints

1. Los modelos de catálogo y los JSON Schema pasan validación automática.
2. La búsqueda solo devuelve registros aprobados.
3. Una consulta de verbo con formas alternativas las devuelve todas sin perder acentos.
4. La generación no produce preguntas de formas no disponibles ni de registros pendientes.
5. La respuesta inicial de una pregunta nunca contiene las formas correctas.
6. El corrector acepta las variantes registradas, no elimina tildes ni añade variantes por analogía.
7. Los IDs de grupos/familias/colecciones coinciden con los del selector.
8. Ningún endpoint funcional se considera activo hasta que sus pruebas de integración pasen con el motor real.
