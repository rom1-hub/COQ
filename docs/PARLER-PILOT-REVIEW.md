# Revisión piloto de `parler` — COQ

**Estado:** auditoría técnica y lingüística propuesta; pendiente de aprobación explícita del responsable lingüístico. Este documento no aprueba el patrón ni incorpora `parler` al catálogo de producción.

## Fuente lingüística

- Académie française, *Dictionnaire de l’Académie française*, 9.ª edición, conjugación de `parler`: <https://www.dictionnaire-academie.fr/conjuguer/A9P0685>.
- Académie française, entrada `en`, apartado IV sobre la formación del gérondif: <https://www.dictionnaire-academie.fr/article/A9E1238>.
- Contratos COQ: `docs/CONTRATS-LINGUISTIQUES.md`, apartados L-02, L-03, L-04, L-05 y L-06.

La Académie clasifica `parler` como regular del primer grupo en `-er` y señala que se conjuga como `aimer`. La conjugación de la fuente respalda las formas finitas estándar, el imperativo y el participio presente `parlant`. COQ añade su matriz de sujetos y contextos, los cinco tiempos compuestos acordados y `en` para el gérondif.

## Matriz de las 13 formas COQ

| ID | Ejemplos representativos esperados | Regla COQ aplicada |
|---|---|---|
| `present_indicatif` | `parle`, `parlons`, `parlent` | Patrón regular `-ER` |
| `imperatif_present` | `parle`, `parlons`, `parlez` | Solo `tu`, `nous`, `vous` |
| `imparfait` | `parlais`, `parlions`, `parlaient` | Patrón regular `-ER` |
| `conditionnel_present` | `parlerais`, `parlerions`, `parleraient` | Infinitivo + terminaciones |
| `futur_simple` | `parlerai`, `parlerons`, `parleront` | Infinitivo + terminaciones |
| `subjonctif_present` | `parle`, `parlions`, `parliez` | En consulta, la presentación añade `que` al sujeto |
| `passe_compose` | `ai parlé`, `avons parlé`, `ont parlé` | `avoir` en presente + participio |
| `plus_que_parfait` | `avais parlé`, `avions parlé`, `avaient parlé` | `avoir` en imparfait + participio |
| `conditionnel_passe` | `aurais parlé`, `aurions parlé`, `auraient parlé` | `avoir` en conditionnel présent + participio |
| `futur_anterieur` | `aurai parlé`, `aurons parlé`, `auront parlé` | `avoir` en futur simple + participio |
| `subjonctif_passe` | `aie parlé`, `ayons parlé`, `aient parlé` | `avoir` en subjonctif présent + participio |
| `participe_present` | `parlant` | Sin fila de sujeto |
| `gerondif_present` | `en parlant` | `en` + participe présent |

## Metadatos propuestos (no producción)

- Lema canónico: `parler`.
- Grupo: `first`.
- Familia: `first_regular`.
- Patrón previsto: `first_er_regular` / `first_group_regular_er` versión 1.
- Construcción: `parler.non_pronominal`.
- Auxiliar pedagógico COQ: `avoir`.
- Política de participio: `invariable`, según la regla COQ para `avoir`.
- Regularidad: `regular`; sin alternancia ortográfica.

El mapeo para `on` es una regla de sujeto/conjugación de COQ: las formas personales usan la forma verbal de tercera persona singular, y los tiempos compuestos conservan los contextos de género/número definidos por L-06. La fuente de conjugación no presenta un renglón independiente para `on`; no se documentará como si lo hiciera.

## Qué demuestra la prueba incluida

`backend/tests/test_parler_pilot_review.py` ejercita las 13 formas por la ruta HTTP real y el motor Python, usando registros aprobados **sintéticos e internos al test**. También prueba las cantidades de filas de consulta, el mapeo de `on` y los contextos de `vous` de cortesía y plural, manteniendo `parlé` invariable en los tiempos compuestos con `avoir`.

Esos fixtures no son datos de producción ni evidencia de aprobación. No se cambia `data/catalogs/verbs.jsonl`, `patterns.jsonl`, ni `scopes.jsonl`. El patrón y el verbo deben permanecer pendientes hasta revisar las pruebas y recibir la aprobación lingüística explícita.

## Formas excluidas

No se añaden `passé simple`, `passé antérieur`, `subjonctif imparfait`, formas pasivas ni la construcción pronominal a la selección COQ de 13 formas. Aunque la fuente documenta tiempos adicionales, quedan fuera del alcance v1 acordado.

## Registro declarativo LR-041

`LR-041` registra `parler` como decisión de metadatos del lema dentro de la cola de revisión. `forms_review_status` permanece en `pending` y `approved_for_production` es `false`. La decisión conserva evidencia de consulta puntual de la Académie française, pero no incorpora una tabla copiada en masa, no crea un `VerbRecord`, no cambia el estado de `first_er_regular` y no desbloquea la API de producción. Las pruebas de regresión usan registros sintéticos; prueban el comportamiento del código, no constituyen por sí solas aprobación lingüística de las 13 formas.
