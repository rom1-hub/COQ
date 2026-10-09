# Contratos lingüísticos — COQ

**Estado: reglas base aprobadas parcialmente por el responsable lingüístico el 9 de octubre de 2026; decisiones adicionales registradas el mismo día.** La validación de cada verbo y de sus formas concretas sigue siendo obligatoria. Las formas no verificadas no se usarán para evaluar ejercicios.

Este documento es la fuente de verdad lingüística del proyecto. La decisión pedagógica aprobada tiene prioridad dentro de COQ, pero no debe presentarse como una regla normativa de la Académie française cuando simplifique la norma general.

## L-01. Fuente de referencia

- **Fuente principal elegida:** Académie française, portal digital del *Dictionnaire de l’Académie française*.
- Portal: <https://www.dictionnaire-academie.fr/>.
- Presentación del sistema de conjugación: <https://www.dictionnaire-academie.fr/presentation.html>.
- Ayuda sobre los cuadros de conjugación y las formas dobles: <https://www.dictionnaire-academie.fr/aide-en-ligne>.
- Cada forma o regla excepcional revisada debe poder vincularse, cuando sea posible, con la entrada de referencia consultada y con el estado de revisión interno.
- **Pendiente técnico:** comprobar las condiciones de uso y la viabilidad de cualquier importación automatizada. La existencia del portal no autoriza a asumir que sus datos pueden copiarse masivamente.

## L-02. Inventario temporal

La aplicación trabaja con estos 11 tiempos, clasificados así:

### Simples (6)

1. Présent de l'indicatif
2. Impératif présent
3. Imparfait
4. Conditionnel présent
5. Futur simple
6. Subjonctif présent

### Compuestos (5)

7. Passé composé
8. Plus-que-parfait
9. Conditionnel passé
10. Futur antérieur
11. Subjonctif passé

IDs internos propuestos: `present_indicatif`, `imperatif_present`, `imparfait`, `conditionnel_present`, `futur_simple`, `subjonctif_present`, `passe_compose`, `plus_que_parfait`, `conditionnel_passe`, `futur_anterieur`, `subjonctif_passe`.

Los nombres visibles son etiquetas; no se usan como identificadores internos. `Tous les temps` es un filtro, no un duodécimo tiempo.

### Dos formas no personales incluidas en consulta y ejercicios

Además de los 11 tiempos/modos anteriores, COQ incorpora estas dos formas, que **no cuentan como tiempos adicionales**:

- **Participe présent** — ID `participe_present`. Ejemplo: `parler` → `parlant`. Se muestra como forma verbal no personal, sin filas de sujeto. Para los ejercicios, se pide y se introduce únicamente el participe présent (`parlant`).
- **Gérondif présent** — ID `gerondif_present`. Se forma con `en` + participe présent: `parler` → `en parlant`. En la consulta se muestra la forma completa; en el ejercicio se introduce la forma completa, incluido `en` (`en parlant`).

En esta fase se incluye el gérondif con `en` y el participe présent correspondiente; no se incorpora un gérondif passé ni se consideran equivalentes las locuciones históricas sin `en`. El participe présent se almacena como forma verbal, diferenciado de adjetivos homógrafos o de ortografía distinta (por ejemplo, participe présent `convainquant` frente al adjetivo `convaincant`).

Referencia de la fuente seleccionada: [Académie française, « Participe »](https://www.dictionnaire-academie.fr/article/A9P0772) y [« Gérondif »](https://www.dictionnaire-academie.fr/article/A9G0646).

## L-03. Estructura de los tiempos compuestos

- Passé composé: auxiliar en présent de l'indicatif + participe passé.
- Plus-que-parfait: auxiliar en imparfait + participe passé.
- Conditionnel passé: auxiliar en conditionnel présent + participe passé.
- Futur antérieur: auxiliar en futur simple + participe passé.
- Subjonctif passé: auxiliar en subjonctif présent + participe passé.

## L-04. Auxiliar: regla pedagógica COQ aprobada

Para la práctica estándar, cada construcción verbal tendrá un único auxiliar asignado. No se generarán preguntas que alternen de auxiliar según el sentido o la transitividad.

La lista de construcciones no pronominales que usan `être` queda sujeta a la lista pedagógica aprobada en las decisiones previas:

`aller`, `venir`, `arriver`, `partir`, `monter`, `descendre`, `entrer`, `sortir`, `rester`, `passer`, `tomber`, `retourner`, `apparaître`, `naître`, `mourir`, `décéder`.

Según la regla acordada, las demás construcciones no pronominales usan `avoir`, incluidos explícitamente `accourir`, `éclore`, `déchoir` y `trépasser`.

Las construcciones pronominales se modelan de forma separada y usan `être`, por ejemplo, `agenouiller` frente a `s'agenouiller`. No se debe inferir la regla de una forma pronominal únicamente a partir del auxiliar asignado al infinitivo no pronominal.

**Aviso de rigor:** esta es una convención didáctica específica de COQ y puede simplificar alternancias reconocidas por las fuentes. No se atribuirá automáticamente a la Académie française. Los casos concretos de la lista se auditarán contra la fuente para registrar la diferencia sin cambiar silenciosamente la regla aprobada.

## L-05. Participio pasado y concordancia

### Con `avoir`

**Regla pedagógica COQ aprobada:** el participio pasado no concuerda con el sujeto ni con el complemento directo antepuesto. Se mantiene invariable en las respuestas que siguen esta regla.

Esta es una simplificación didáctica deliberada; no debe presentarse como una descripción exhaustiva de la norma francesa general.

### Con `être` en construcciones no pronominales

Regla base de COQ: en las construcciones no pronominales asignadas a `être`, el participio pasado concuerda con el sujeto en género y número. Toda forma fija, variante o excepción registrada en la fuente se verificará individualmente; no se inferirán excepciones sin evidencia.

### En construcciones pronominales

La concordancia se registrará por verbo/construcción, con evidencia lingüística revisada. Ejemplos aprobados como criterio:

- `je me suis réveillé(e)` — concordancia con el sujeto.
- `je me suis parlé` — participio invariable.

En esta sección no se enseñan ni se evalúan reglas gramaticales dependientes de una frase o un complemento. Los ejercicios trabajan con conjugaciones aisladas y no presentarán contextos como `je me suis lavé les mains` para decidir la función del pronombre. Cuando no se pueda establecer una forma aislada fiable sin información gramatical adicional, esa cuestión se reserva para la sección «Grammaire» y no se convierte en un ejercicio de conjugación. El catálogo no debe inventar una regla por analogía: cada comportamiento pronominal debe quedar documentado por verbo/construcción.

## L-06. Sujetos y contexto

Filas de consulta:

`je`, `tu`, `il`, `elle`, `on`, `nous`, `vous`, `ils`, `elles`.

Para `impératif présent`: `tu`, `nous`, `vous`.

En ejercicios, el contexto explícito de género/número se utiliza para los tiempos compuestos, no para los simples. Para `on`, las opciones acordadas son:

- masculino singular;
- masculino plural;
- femenino plural.

No se ofrecerá femenino singular para `on` en esta primera definición. Se distinguirá la persona gramatical de la concordancia semántica cuando corresponda. Para `vous`, se distinguen tanto el singular de cortesía como el plural; el género y número de la concordancia se resuelven con el contexto semántico del ejercicio. En la consulta compacta se podrá usar `vous êtes parti(e)` para el singular de cortesía y `vous êtes parti(e)(s)` para representar la variación de género/número del plural.

## L-07. Familias morfológicas

Se conservan las categorías pedagógicas definidas y se podrán añadir familias cuando el inventario real lo justifique.

Familias iniciales:

- Premier groupe: `-ER` regular, `-GER`, `-CER`, `-ELER`, `-ETER`, `-YER`, alternancias `E/È` y otras alteraciones ortográficas pertinentes.
- Deuxième groupe: `-IR` con el comportamiento característico del segundo grupo.
- Troisième groupe: familias en `-IR`, `-DRE`, `-EINDRE`, `-AINDRE`, `-OINDRE`, `-UIRE` y otras familias irregulares.
- Etiquetas adicionales para construcciones pronominales, impersonales y defectivas.

Para el deuxième groupe, se parte de los verbos en `-ir` cuyo participe présent termina en `-issant`; se comprobará además su patrón de conjugación, incluida la forma de `nous` en `-issons`. La clasificación se verificará verbo por verbo contra la Académie française. Mantendremos un inventario explícito de los verbos en `-ir` del troisième groupe para evitar clasificarlos solo por la terminación del infinitivo.

La Académie française distingue, por ejemplo, los verbos del segundo grupo en `-ir` mediante el participe présent en `-issant`, y señala que el tercer grupo también contiene verbos en `-ir`, como `partir` y `dormir` (véase [«Verbes en -ir ou -ire»](https://www.dictionnaire-academie.fr/article/DNP0828)).

La pertenencia a una familia no se decidirá únicamente por las letras finales del infinitivo. Si un verbo no encaja bien en una familia compartida, podrá usar un patrón propio en vez de forzarlo a una clasificación artificial.

## L-08. Variantes válidas y corrección

- Si la fuente seleccionada valida dos formas conjugadas, **la consulta mostrará ambas** y **los ejercicios aceptarán ambas**.
- La aplicación no inventará variantes por analogía: cada forma aceptada debe estar documentada o aprobada explícitamente.
- La corrección será estricta con la ortografía conjugada: los acentos diacríticos y ortográficos exigidos por la forma deben estar presentes. Por ejemplo, no se aceptará una respuesta sin el acento que aparece en formas como `j'achète` o `je gèle`.
- Se permite normalizar mayúsculas/minúsculas, espacios al inicio/final y espacios duplicados. Los apóstrofos rectos (`'`) y tipográficos (`’`) se tratarán como equivalentes.
- No se eliminarán ni se neutralizarán los acentos. La tolerancia tipográfica no puede cambiar una forma conjugada ni sustituir una variante que deba estar documentada.

## L-09. Verbos impersonales y defectivos

Cada entrada podrá marcarse como **verbo impersonal** o **verbo defectivo**. Se adopta la grafía española «defectivo» para la etiqueta de interfaz; si «deflexivo» pretendía designar otra categoría, se corregirá el contrato.

- En «Ver conjugación» se muestran únicamente las formas y los tiempos que existan o estén documentados para el verbo.
- En los ejercicios solo entran conjugaciones existentes, aprobadas y disponibles para el tiempo seleccionado.
- Si una persona o un tiempo no existe, no se inventa la forma ni se genera una pregunta para ella.
- Los estados de datos distinguen, como mínimo, `verified`, `draft`, `not_attested`, `not_supported` y `rare_or_literary`.
- Las categorías «impersonal» y «defectivo» son etiquetas descriptivas; no sustituyen el inventario concreto de personas y tiempos permitidos.

## L-10. Consulta y ejercicios

- La vista de consulta representa las formas válidas de cada uno de los 11 tiempos/modos y de las dos formas no personales (`participe présent`, `gérondif présent`). Las variantes aceptadas y verificadas se muestran juntas.
- En los dos tiempos de subjuntivo, la consulta muestra la construcción completa, por ejemplo `que je sois`, `qu'il vienne` o `que j'aie mangé`.
- En los ejercicios de subjuntivo, la consigna puede mostrar `que je ___`, pero el alumno introduce solo la forma verbal: `sois`; en el subjonctif passé, introduce el grupo verbal conjugado, por ejemplo `aie mangé`, sin escribir `que`.
- En los ejercicios de participe présent, la respuesta es solo el participio (`parlant`). En los de gérondif présent, la respuesta incluye `en` (`en parlant`). Ninguna de estas dos formas utiliza una fila de sujeto; se genera una pregunta directa a partir del infinitivo.
- En tiempos simples, se escribe la forma conjugada requerida. En tiempos compuestos, se escribe el grupo verbal conjugado (auxiliar + participio pasado). En las formas pronominales se incluye el pronombre pronominal que forma parte de la conjugación, pero no se vuelve a escribir el sujeto que ya aparece en la consigna.
- El impératif présent pronominal se incluye en consulta y práctica, con los pronombres y guiones ortográficos correspondientes: `lève-toi`, `levons-nous`, `levez-vous`.
- Los ejercicios practican formas conjugadas aisladas de manera repetitiva; no presentan frases para evaluar reglas gramaticales o complementos. La gramática contextual pertenece a la sección «Grammaire».
- La selección de ejercicios filtra por las formas existentes y revisadas; nunca rellena huecos con una forma inferida sin respaldo.
- El motor no debe depender de la interfaz para resolver auxiliares, terminaciones, variantes ni perfiles de concordancia.

## L-11. Evidencia y precedencia

Orden de precedencia dentro de COQ:

1. Decisión lingüística explícita aprobada y versionada.
2. Forma o regla revisada contra la fuente elegida.
3. Patrón morfológico aprobado.
4. Motor Python.
5. Contrato de consulta o ejercicio.
6. Presentación visual.

Cada regla tendrá formulación, condiciones, contraejemplos y pruebas. Cada forma aprobada tendrá trazabilidad al registro de referencia o una revisión lingüística documentada. Un cambio de código no puede alterar una regla lingüística por conveniencia técnica.
