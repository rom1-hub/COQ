# Auditoría inicial de fuentes de datos lingüísticos

**Estado:** fuente de nombres de verbos seleccionada solo para crear un inventario de candidatos; no se ha importado ninguna conjugación y no existe todavía un catálogo lingüístico aprobado.

## 1. Académie française: autoridad de verificación, no fuente para scraping

La presentación oficial del Dictionnaire de l’Académie française indica que su módulo de conjugación contiene más de 425.000 formas flexionadas y conjuga aproximadamente 7.000 verbos; también señala que sus tablas cubren particularidades como verbos defectivos, pronominales, auxiliares y participios invariables. Fuente: <https://www.dictionnaire-academie.fr/presentation.html>.

Sus condiciones generales de uso, apartados 5 y 6, prohíben el uso de sistemas automatizados para aspirar o extraer datos del sitio y declaran protegidos sus contenidos, estructura y bases de datos; para la reproducción o transformación se requiere autorización expresa y previa, salvo excepciones legales específicas. Fuente: <https://www.dictionnaire-academie.fr/CGU>.

**Decisión:** COQ no desarrollará un scraper ni copiará de manera masiva las tablas de conjugación de la Académie. La usaremos como referencia lingüística mediante consultas puntuales y enlaces directos de procedencia. Si más adelante se pretende reutilizar una cantidad sustancial de esas tablas, primero se solicitará autorización al titular. La consulta pública no se interpretará como licencia de reutilización masiva.

## 2. Alternativas de datos abiertos encontradas

### Verbiste

Verbiste es un sistema de conjugación francés con una lista de más de 6.000 verbos y modelos de conjugación, distribuido bajo GPL (la fuente Debian revisada indica GPL; algunas versiones/documentación especifican GPL v2 o posterior). Referencias:

- Fuente del paquete Debian: <https://sources.debian.org/src/verbiste/0.1.49-1/LISEZMOI>
- Descripción y licencia: <https://manpages.ubuntu.com/manpages/questing/fr/man3/verbiste.3.html>

Es una opción técnica para investigar porque usa modelos, pero antes de integrar sus datos o código hay que determinar la compatibilidad de la licencia con la licencia que finalmente adopte COQ, revisar la cobertura de las 13 formas/tiempos seleccionadas y contrastar sus reglas con las simplificaciones pedagógicas aprobadas. No se copia ni integra en la fase actual.

### Lista de infinitivos MIT — seleccionada solo como semilla de candidatos

Se ha seleccionado `einenlum/french-verbs-list` para generar un inventario preliminar de nombres candidatos, no como autoridad lingüística ni motor de conjugación: <https://github.com/einenlum/french-verbs-list>. El repositorio declara licencia MIT (<https://github.com/einenlum/french-verbs-list/blob/6fee12e56eb6b5863f3410644b4164491267fb7e/LICENSE>) y su README advierte que el listado es un trabajo en curso.

Versión fijada: commit `6fee12e56eb6b5863f3410644b4164491267fb7e` (`Release 0.0.2`). El script `scripts/import_candidate_infinitives.py` comprueba los SHA de los objetos Git de `verbs.json` y `LICENSE` antes de importarlos, conserva el aviso MIT y registra hashes/manifiesto. Esto hace reproducible la importación y evita identificar contenido diferente como si fuera esa versión.

El importador genera `candidate-infinitives.jsonl`: tokens candidatos, ID estable, sugerencias de grupo de la fuente y estado `candidate`. **No incorpora formas conjugadas, no confirma que un token sea un infinitivo válido, no aprueba las sugerencias de grupo y no alimenta la consulta ni los ejercicios.** La lista de origen puede incluir omisiones, duplicados, errores, lemas no canónicos o clasificaciones discutibles; se debe revisar antes de convertir un candidato en `VerbRecord`.

La descarga del listado aún debe ejecutarse en la máquina de desarrollo con acceso a Internet. El resultado no está preincluido en el proyecto hasta superar la verificación de los objetos fijados.

### `mlconjug3` — comparador técnico, no fuente aprobada

`Ars-Linguistica/mlconjug3` declara licencia MIT para el proyecto y ofrece un modelo de aprendizaje automático que predice conjugaciones incluso para verbos desconocidos. Referencias: <https://github.com/Ars-Linguistica/mlconjug3>, <https://github.com/Ars-Linguistica/mlconjug3/blob/691b199c60c523edcc3f0753390f02fbd8714e0b/LICENSE> y versión revisada `4.0.1`/commit `691b199c60c523edcc3f0753390f02fbd8714e0b`.

No se adopta como fuente de verdad: el proyecto incluye modelos entrenados y recursos de conjugación (`conjugation-fr.json` y XML), pero la auditoría realizada aún no demuestra la procedencia/licencia independiente de cada recurso ni que sus salidas cumplan las reglas pedagógicas de COQ (participio con `avoir`, concordancia de pronominales, inventario reducido de formas y variantes). Además, el propio README registra que pueden variar las predicciones entre versiones. COQ no importará sus recursos ni ejecutará esas salidas como respuestas correctas. En una fase posterior podría usarse como comparador separado sobre un conjunto de prueba aprobado, siempre que se registre la versión y no se confunda coincidencia con verificación lingüística.

### Conjugações derivadas automáticamente de la Académie

Se encontró un repositorio que afirma contener miles de conjugaciones extraídas del diccionario de la Académie: <https://github.com/ShingZhanho/verbe-conjugaison-academie-francaise>. No se debe tomar como una vía de elusión de las condiciones originales de la Académie. Solo se consideraría después de revisar la licencia del repositorio y confirmar que su responsable tiene derecho a redistribuir los datos.

## 3. Estrategia recomendada para COQ

1. Mantener el contrato y motor propios, con IDs y pruebas independientes.
2. Usar la lista MIT fijada únicamente para crear candidatos; no considerar sus grupos como hechos verificados.
3. Registrar patrones y familias de COQ de forma explícita y revisable.
4. Verificar formas y particularidades manualmente contra la Académie, enlazando cada registro a la página consultada; no usar automatización para extraer tablas del sitio.
5. Considerar una fuente de conjugación con licencia compatible solo tras una auditoría de licencia/calidad y un pequeño corpus de comparación. `mlconjug3` queda limitado a posible comparador experimental, no fuente aprobada.
6. No cambiar el estado a `approved` a partir de una mera importación ni practicar con registros pendientes.

## 4. Preguntas legales/técnicas aún abiertas

- La licencia que adoptará el proyecto COQ no se ha definido. Esto debe resolverse antes de integrar conjuntos de datos con licencias copyleft como GPL.
- No se ha obtenido autorización para reutilizar masivamente el corpus de la Académie française.
- La cobertura real y tasa de error de cualquier fuente alternativa debe medirse con un corpus de verbos regulares, alteraciones ortográficas, irregulares, pronominales, impersonales y defectivos.
- La fuente de conjugaciones de producción sigue abierta. La lista MIT solo crea una cola de revisión de lemas.
- Los recursos de `mlconjug3` no se reutilizarán hasta verificar la procedencia concreta de sus modelos/datasets; la licencia MIT declarada del repositorio no se toma como prueba suficiente de la licencia de todos los datos derivados.


## 5. Triage heurístico de los candidatos importados

`scripts/audit_candidate_infinitives.py` genera tres informes desde `candidate-infinitives.jsonl`: `candidate-infinitives-audit.jsonl`, `candidate-infinitives-audit.csv` y `candidate-infinitives-audit-summary.json`. Las señales incluyen posible contradicción entre terminación y grupo sugerido, terminaciones infrecuentes, múltiples grupos sugeridos y lemas con espacios/guiones/apóstrofos. Son indicios para priorizar una revisión manual, no diagnósticos lingüísticos: los casos válidos pueden generar alertas y los inválidos pueden no generar ninguna. Todos los candidatos siguen sin aprobarse.

La lista importada fijada a un commit produjo 7.075 tokens candidatos en el entorno de desarrollo. Ese recuento no debe interpretarse como 7.075 verbos canónicos confirmados.
