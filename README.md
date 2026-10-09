# COQ

Proyecto nuevo e independiente para una plataforma de francés. La primera sección en desarrollo es **Conjugación**; después se añadirán la página principal, vocabulario, gramática y otros módulos. No contiene ni importa código del proyecto experimental anterior.

## Estado actual

- [x] Estructura base independiente para COQ.
- [x] Prototipo interactivo de la sección de conjugación en `frontend/conjugacion.html`.
- [x] «Ver conjugación»: solo búsqueda por infinitivo y selector de tiempo o forma verbal.
- [x] «Practicar»: filtros de grupo/familia, construcción y auxiliar, con reinicio.
- [x] Formas *participe présent* y *gérondif présent* en consulta y práctica.
- [x] API mínima FastAPI con comprobación de estado.
- [x] Contratos lingüísticos y registro de decisiones.
- [x] Pruebas automatizadas y workflow de publicación.
- [x] Contrato técnico Pydantic y JSON Schema para el catálogo verbal.
- [x] Registros iniciales versionados de 14 patrones y 19 scopes, todos pendientes de validación lingüística/miembros.
- [x] Validador de catálogos para comprobar IDs únicos y referencias cruzadas.
- [x] Contrato de API para separar filtros de scope y perfil de verbo específico.
- [x] Auditoría inicial de restricciones de las fuentes y alternativas licenciadas.
- [x] Selección de una fuente MIT fijada para una cola auxiliar de lemas candidatos (no conjugaciones).
- [x] Ejecutar el importador fijado (7.075 candidatos en el entorno de desarrollo Windows).
- [x] Crear una auditoría heurística reproducible para priorizar la revisión de lemas; sus alertas no aprueban ni rechazan verbos.
- [ ] Decidir la licencia general de COQ y la fuente licenciada de conjugaciones para producción.
- [ ] Construir el catálogo canónico `verbs.jsonl` con metadatos, formas y evidencias revisadas.
- [ ] Catálogo verbal auditado y validado.
- [ ] Motor de conjugación Python.
- [ ] Integración entre interfaz y API.

**Límite actual:** los controles de la interfaz funcionan, pero todavía no se calculan conjugaciones ni se generan o corrigen ejercicios. El motor y el catálogo validado son la siguiente fase.

## Estructura

```text
.
├── .github/workflows/       # pruebas y publicación GitHub Pages
├── backend/                 # FastAPI y pruebas
├── data/                    # futuro catálogo y reglas validadas
├── docs/                    # contratos, arquitectura y decisiones
├── frontend/                # aplicación web estática
└── render.yaml              # configuración preparada para desplegar la API
```

## Ejecutar localmente en Windows

Requisitos: Python 3.12 o superior, Node.js para comprobar la sintaxis de JavaScript y un navegador moderno.

Desde la carpeta raíz del proyecto, ejecuta el frontend:

```powershell
py -m http.server 8080 --directory frontend
```

Abre `http://localhost:8080/conjugacion.html`.

Para ejecutar la API en otra ventana de PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r backend/requirements-dev.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload
```

Estado de la API: `http://127.0.0.1:8000/api/v1/health`  
Documentación técnica: `http://127.0.0.1:8000/docs`

La API aún no contiene endpoints de conjugación.

## GitHub

Repositorio: [rom1-hub/COQ](https://github.com/rom1-hub/COQ)

La URL prevista para probar la sección de conjugación después de publicar con GitHub Pages es:

`https://rom1-hub.github.io/COQ/conjugacion.html`

La URL no se considera publicada hasta que el código esté en el repositorio y el workflow de GitHub Actions termine correctamente. En la configuración de GitHub, la fuente de Pages debe ser **GitHub Actions**. El workflow genera temporalmente una página de entrada que redirige a `conjugacion.html`; cuando se construya la página principal de COQ, esta entrada se reemplazará por la página de inicio real.

GitHub Pages solo aloja archivos estáticos. FastAPI necesita un servicio de backend independiente; `render.yaml` es una configuración inicial para ese despliegue, no un servicio ya publicado.

## Principios

1. COQ es el nombre del proyecto completo; «Conjugación» es un módulo.
2. La fuente de referencia lingüística definida es la Académie française; los casos dudosos se revisan individualmente.
3. Las decisiones pedagógicas aprobadas no se cambian silenciosamente.
4. Los datos describen las formas; el motor Python es la autoridad para generarlas y evaluarlas.
5. Las formas inexistentes no se inventan y las variantes aprobadas quedan registradas.
6. Cada corrección lingüística importante incorpora una prueba de regresión.

Consulta `docs/CONTRATS-LINGUISTIQUES.md`, `docs/DATA-CONTRACT.md`, `docs/DATA-SOURCE-AUDIT.md`, `docs/CANDIDATE-AUDIT-GUIDE.md`, `docs/DECISIONS.md` y `docs/ARCHITECTURE.md` antes de implementar el motor.

Para regenerar JSON Schema: `$env:PYTHONPATH = "backend"; py scripts/export_data_contract_schemas.py`.

### Inventario auxiliar de lemas candidatos

Desde la raíz de COQ y con acceso a Internet, ejecutar `py scripts/import_candidate_infinitives.py` para generar la cola de infinitivos candidatos. Después ejecutar `py scripts/audit_candidate_infinitives.py`, que produce JSONL, CSV y resumen con señales heurísticas para priorizar revisiones. Esas señales **no** aprueban ni rechazan verbos: no reemplazan la revisión lingüística, y la ausencia de alertas no demuestra que un lema sea correcto. Finalmente, ejecutar `py scripts/validate_catalog.py` y las pruebas. La fuente de conjugaciones de producción sigue pendiente de selección.


## Prueba de independencia y filtros (prototipo UI v0.4)

Servir `frontend/` por HTTP y abrir `/conjugacion.html`. Cada modo conserva sus propios campos. En «Practicar», el menú «Grupo o familia verbal» contiene directamente los grupos y las familias. Escribe `parler` para verificar el ejemplo demostrativo: el selector de grupo, la construcción y el auxiliar se rellenan y bloquean; el tiempo permanece habilitado. Es un fixture de interfaz, no el catálogo definitivo. Para resetear, usa «Reiniciar práctica» dentro de ese modo.
