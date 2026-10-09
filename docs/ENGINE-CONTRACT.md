# Contrato inicial del motor de conjugación — COQ

**Estado:** primera implementación técnica, deliberadamente limitada. No habilita formas en producción ni sustituye la revisión lingüística de cada lema/patrón.

## 1. Responsabilidad

`backend/app/domain/conjugation_engine.py` es lógica de dominio pura. Recibe un `VerbRecord`, un `ConjugationPattern`, el `construction_id`, un `FormId` seleccionable y su `FormContext`; devuelve el grupo verbal objetivo, la forma preferida y las variantes aceptadas. No lee archivos, no hace HTTP, no accede al navegador y no conoce etiquetas de UI.

La consulta no incluye el sujeto ni el marcador `que` del subjuntivo en la forma: la vista puede formar `que je sois`. Un tiempo compuesto devuelve el grupo verbal completo (`aie mangé`), sin sujeto. El gérondif incluye `en` (`en parlant`). Una construcción pronominal incluye su clítico; el imperativo afirmativo usa el clítico enclítico con guion (`lave-toi`).

## 2. Barreras de seguridad

- El lema, el patrón y la construcción deben estar en estado `approved`.
- `verb.pattern_id` debe coincidir con el patrón suministrado; el grupo del lema y del patrón también deben coincidir.
- `algorithm_key` se resuelve en un registro fijo de algoritmos Python. No se importa ni evalúa código indicado por datos.
- No se deduce una familia por la terminación del infinitivo. Cada algoritmo se ejecuta únicamente si el catálogo le asigna explícitamente ese patrón.
- Las sobrescrituras solo se aplican cuando están `forms_reviewed` o `approved`. Una sobrescritura coincidente que siga pendiente bloquea la generación para evitar que un algoritmo base la oculte.
- Las variantes mantienen acentos y escritura exactos. El motor no “corrige” la respuesta del alumno.
- Para verbos defectivos o impersonales se requiere una decisión explícita de disponibilidad o una sobrescritura revisada para la forma/contexto pedido.
- `participe_passe` es interno y no se puede solicitar como forma visible independiente.

## 3. Alcance implementado

La versión 1 implementa únicamente `first_group_regular_er` (versión de algoritmo `1`) para verbos regulares del primer grupo en `-ER`, sin alternancia ortográfica. Una versión de algoritmo no implementada se rechaza explícitamente. Cubre los seis modos/tiempos simples que aplican a la persona solicitada, las formas imperativas `tu/nous/vous`, participe présent, gérondif présent y la composición de los cinco tiempos compuestos acordados.

Las familias `-GER`, `-CER`, `-ELER`, `-ETER`, `-YER`, `E/È`, el segundo grupo, los patrones del tercer grupo y los irregulares quedan sin implementar. El motor los rechaza con error explícito; no cae por defecto en el algoritmo `-ER`.

Los auxiliares `avoir` y `être` se representan como paradigmas internos cerrados que solo se consultan a partir de `ConstructionProfile.auxiliary` y la receta `COMPOUND_AUXILIARY_TENSE`. No hay heurísticas por infinitivo para escoger auxiliar.

## 3.1 Caso de referencia contrastado manualmente

Como primera referencia del patrón regular en `-ER`, se contrastaron manualmente formas seleccionadas de `ficher` con el cuadro de conjugación de la Académie française: https://www.dictionnaire-academie.fr/conjuguer/A9F0671. La consulta manual del 9 de octubre de 2026 identifica `ficher` como verbo regular del primer grupo en `-er` y lo conjuga como `aimer`. La prueba de regresión usa un registro sintético; no agrega `ficher` al catálogo de producción ni importa una tabla externa de formas. Este contraste habilita únicamente pruebas del algoritmo `first_group_regular_er` en los casos cubiertos, no la aprobación global de la familia ni de cualquier verbo candidato.

## 4. Tiempos compuestos y concordancia

- La receta compuesto→tiempo del auxiliar procede de `COMPOUND_AUXILIARY_TENSE`.
- El auxiliar procede exclusivamente del `ConstructionProfile` aprobado.
- Para `invariable`, el participio se mantiene invariable.
- Para `subject`, el motor aplica la política pedagógica de COQ según género y número del contexto.
- Para `verb_specific`, no se infiere concordancia: se exige una sobrescritura aprobada del participe passé (invariable genérica o específica por género/número) o de la forma compuesta completa.
- El resultado contiene solo el grupo verbal: no el sujeto ni `que`.

## 5. Errores de dominio

El motor define errores estables (`UNAPPROVED_RECORD`, `PATTERN_MISMATCH`, `UNSUPPORTED_PATTERN`, `INVALID_FORM_CONTEXT`, `FORM_UNAVAILABLE`, `FORM_NOT_REVIEWED`, `CATALOG_CONFLICT`). El enum API actual todavía no tiene un código para cada error de dominio; la integración deberá ampliar `ApiErrorCode` y mapearlos expresamente. No debe exponer trazas ni rutas internas.

## 6. Puerta para ampliar patrones

Cada nueva `algorithm_key` requiere pruebas de regresión propias para cada forma que afirme soportar, evidencia de revisión del patrón y contraste manual de casos representativos según `docs/CONTRATS-LINGUISTIQUES.md`. El algoritmo solo se podrá asignar a patrones de producción cuando el patrón esté revisado y aprobado. La lista MIT de candidatos no es evidencia de formas.

