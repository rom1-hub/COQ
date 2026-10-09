# Registro de decisiones

| ID | Tema | Estado | Decisión/criterio |
|---|---|---|---|
| D-001 | Repositorio remoto | Pendiente de crear en GitHub | Proyecto nuevo, sin copiar código, datos ni módulos ejecutables del repositorio anterior. |
| D-002 | Interfaz | Acordado | HTML/CSS/JavaScript estáticos en `frontend/`. |
| D-003 | Backend | Acordado | Python + FastAPI + Pydantic. |
| D-004 | Autoridad lingüística | Acordado | Académie française como fuente principal; registrar evidencias cuando sea posible. |
| D-005 | Alcance de tiempos/modos | Acordado | 11 tiempos/modos en el inventario: 6 simples y 5 compuestos, según la clasificación pedagógica COQ. |
| D-006 | Auxiliares | Acordado como regla pedagógica COQ | Auxiliar único por construcción para práctica estándar; lista aprobada de `être` y resto `avoir`, con las excepciones explícitas registradas en el contrato. Auditar y documentar discrepancias con la fuente. |
| D-007 | Concordancia con auxiliares | Acordado como regla pedagógica | Con `avoir`, participio invariable en COQ (simplificación didáctica). Con `être` no pronominal, concordancia con el sujeto en género y número; las excepciones o formas particulares deben verificarse individualmente. |
| D-008 | Pronominales | Acordado para conjugación aislada | Registrar por verbo/construcción el comportamiento de concordancia validado; por ejemplo, `se réveiller` concuerda y `se parler` queda invariable. No evaluar concordancia que dependa de frases o complementos en esta sección; pertenece a «Grammaire». |
| D-009 | Variantes válidas | Acordado | Mostrar todas las formas verificadas en consulta y aceptarlas en ejercicios. |
| D-010 | Sujetos y género/número | Acordado | Nueve sujetos; el contexto explícito de género/número se usa en tiempos compuestos; `on`: masculino singular, masculino plural y femenino plural; `vous` admite singular de cortesía y plural. |
| D-011 | Familias | Acordado | Mantener categorías existentes y añadir otras justificadas por el inventario. |
| D-012 | Impersonales y defectivos | Acordado | Etiquetar; consulta muestra solo formas existentes y ejercicios filtran conjugaciones realmente disponibles. |
| D-013 | Almacenamiento | Pendiente técnico | Evaluar JSON y SQLite según necesidades reales del catálogo, trazabilidad y consultas. |
| D-014 | Fuente de datos | Pendiente técnico | Investigar vías de consulta/verificación de la Académie française; no asumir permiso de importación masiva ni reutilizar el catálogo anterior. |
| D-015 | Motor de conjugación | Pendiente | No implementar hasta cerrar los contratos lingüísticos y establecer casos de referencia verificados. |
| D-016 | Publicación frontend | Preparado, no publicado | GitHub Actions publica `frontend/conjugacion.html` y genera `index.html` solo en el artefacto de Pages para redirigir la raíz. |
| D-017 | Publicación backend | Preparado, no publicado | Render Blueprint; requiere repositorio remoto, cuenta/autoridad de despliegue y configuración de CORS. |
| D-018 | UI de subjuntivo e imperativo | Acordado | Consulta de subjuntivo muestra la construcción completa (`que je sois`); en ejercicios se escribe solo la forma verbal (`sois`, o `aie mangé` en tiempo compuesto). Incluir impératif pronominal con pronombre enclítico y guion. |
| D-019 | Corrección escrita | Acordado | Exigir acentos correctos. Normalizar mayúsculas, espacios y apóstrofo recto/tipográfico, sin quitar diacríticos. Las variantes lingüísticas solo se aceptan si están verificadas. |
| D-020 | Alcance de ejercicios | Acordado | Práctica repetitiva de conjugaciones aisladas. No se evalúan reglas gramaticales dependientes de frases o complementos; se reservan para la sección «Grammaire». Los detalles técnicos del flujo los resuelve la arquitectura. |
| D-021 | Deuxième / troisième groupe | Acordado como método de clasificación | Verificar cada verbo con la Académie française; usar `-ir` + participe présent en `-issant` como indicador del deuxième groupe y revisar el patrón de `nous` en `-issons`. Mantener una lista auditada de verbos en `-ir` del troisième groupe. |

| D-022 | Formas no personales | Acordado | Añadir `participe présent` y `gérondif présent` tanto a «Ver conjugación» como a los ejercicios. No cuentan como tiempos adicionales. Consulta: `parlant` y `en parlant`; ejercicio: escribir `parlant` para participe présent y `en parlant` completo para gérondif. No incluir gérondif passé por ahora. Referencia: Académie française, artículos «Participe» y «Gérondif». |

| D-023 | Controles de consulta frente a práctica | Acordado | «Ver conjugación» solo muestra la búsqueda del infinitivo y el selector de tiempo/forma verbal («Todos los tiempos verbales», 11 tiempos/modos y `participe présent`/`gérondif présent`). Los filtros de grupo/familia, construcción y auxiliar solo aparecen en «Practicar». El botón de reinicio también queda reservado para el modo de práctica. |


| D-024 | Estado de consulta y práctica | Acordado e implementado en UI | «Ver conjugación» y «Practicar» usan formularios, entradas, selectores y resultados independientes. Cambiar de modo no copia ni borra los valores del otro. |
| D-025 | Filtros dependientes de verbo específico | Prototipo limitado | Cuando existe un perfil verificado del catálogo, grupo/familia, construcción y auxiliar se completan y bloquean; el tiempo/forma permanece seleccionable. Hasta que el catálogo/API exista, solo `parler` es un fixture explícito de interfaz, no una fuente lingüística. No deducir perfiles desconocidos. |
| D-026 | Selector de grupo/familia en práctica | Acordado e implementado en UI | Un único menú, en este orden: Todos los grupos y familias; encabezado Grupos verbales; Primer grupo con Verbos regulares, GER, CER, ELER, ETER, YER y E(É) + consonne + ER; Segundo grupo; Tercer grupo con IR, DRE, AINDRE/EINDRE/OINDRE, UIRE, OIR/OIRE, 100 verbos más comunes (por definir) y otras familias (por definir). Se usarán opciones con prefijo visual para representar subfamilias en el selector nativo. La pertenencia concreta se asigna desde catálogo auditado. |
| D-027 | Acción «Practicar este verbo» desde consulta | Pendiente expresamente para fase posterior | No implementar aún el botón ni el traspaso desde «Ver conjugación». Cuando se construya, deberá enviar únicamente el verbo consultado y después aplicar el perfil verificado en el formulario independiente de práctica. |
