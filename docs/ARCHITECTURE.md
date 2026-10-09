# Arquitectura preliminar

## Objetivo

Construir una implementación nueva de conjugación francesa a partir de requisitos revisados, sin importar archivos, módulos, JSON ni lógica ejecutable del proyecto anterior.

## Límites de responsabilidad

- `frontend/`: interfaz, accesibilidad, estado visual y presentación.
- `backend/app/api/`: validación HTTP y traducción de errores a respuestas de API.
- `backend/app/domain/`: modelos y reglas del dominio una vez aprobados.
- `backend/app/services/`: casos de uso: consulta y generación de ejercicios.
- `data/`: JSONL curado y catálogos versionados, validados por Pydantic; no incluir entradas pendientes en ejercicios.
- `backend/tests/`: pruebas unitarias, de integración, integridad de datos y regresión lingüística.

## Flujo esperado

```text
Web JavaScript
    -> solicitud HTTP tipada
    -> FastAPI / Pydantic
    -> servicio de aplicación
    -> repositorio/catálogos de verbos
    -> motor lingüístico Python
    -> respuesta estructurada
    -> presentación JavaScript
```

El frontend no calcula auxiliares, terminaciones, participios ni concordancias. La API y el motor tampoco contienen reglas de presentación visual.

## Dependencias

La lógica del dominio no debe depender de FastAPI, del navegador, de archivos HTML ni del mecanismo de almacenamiento. La capa de repositorio adapta la fuente de datos elegida al modelo del dominio.

## Contrato y almacenamiento del catálogo verbal

El contrato Pydantic está definido en `backend/app/domain/verb_contracts.py` y documentado en `docs/DATA-CONTRACT.md`. La fuente de verdad elegida es JSON Lines (JSONL), un registro por línea, con un esquema JSON exportado desde Pydantic. El backend valida los registros al cargarlos y puede indexarlos en memoria; los patrones, scopes y registros de verbos viven en catálogos independientes y versionados.

No se mantendrán a mano dos fuentes de verdad. Solo se añadirá SQLite como almacén/indexador derivado si una prueba de rendimiento sobre el catálogo real lo justifica. La consulta y la práctica nunca leerán el fixture de interfaz `frontend/verb-profiles.demo.json` como datos de producción.

La Académie française sigue siendo la autoridad de referencia para comprobaciones manuales puntuales, pero sus CGU prohíben la extracción automatizada de datos y protegen la base de datos. No se construirá un scraper ni se importará masivamente ese corpus sin autorización expresa. Véase `docs/DATA-SOURCE-AUDIT.md`.

## Web publicada

La página de origen es `frontend/conjugacion.html`, acompañada de `styles.css` y `app.js`. GitHub Pages publicará estos archivos mediante GitHub Actions; el workflow genera `index.html` únicamente en el artefacto de publicación para redirigir la raíz del sitio a `conjugacion.html`. FastAPI necesita un servicio de backend independiente, preparado inicialmente con `render.yaml`. No se marcará el sistema como integrado hasta probar conectividad, CORS y respuestas reales desde la web pública.

## Regla de cambios

No iniciar la generación lingüística hasta que los contratos estén aprobados. Toda modificación estructural deberá actualizar documentación y pruebas en la misma unidad de cambio.


## Estado independiente de los modos (UI v0.4)

Los módulos «Ver conjugación» y «Practicar» tienen formularios HTML separados. No se reutilizan inputs, selects, objetos `FormData` ni resúmenes entre modos. Cambiar de pestaña oculta un panel y muestra el otro, conservando los campos de ambos. El futuro botón «Practicar este verbo» no forma parte de esta fase.

En práctica, el menú «Grupo o familia verbal» agrupa los tres grupos y las familias morfológicas en un solo select. Al reconocer un perfil proveniente del catálogo, la capa de presentación deberá rellenar y bloquear grupo/familia, construcción y auxiliar, dejando habilitado el tiempo/forma. `frontend/verb-profiles.demo.json` solo contiene el perfil demostrativo `parler`: no es un catálogo ni debe ser utilizado por el motor de conjugación en producción. Se reemplazará por el contrato/respuesta del catálogo validado, evitando inferencias por terminación.
