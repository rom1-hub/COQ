# Arquitectura preliminar

## Objetivo

Construir una implementación nueva de conjugación francesa a partir de requisitos revisados, sin importar archivos, módulos, JSON ni lógica ejecutable del proyecto anterior.

## Límites de responsabilidad

- `frontend/`: interfaz, accesibilidad, estado visual y presentación.
- `backend/app/api/`: validación HTTP y traducción de errores a respuestas de API.
- `backend/app/domain/`: modelos y reglas del dominio una vez aprobados.
- `backend/app/services/`: casos de uso: consulta y generación de ejercicios.
- `data/`: catálogos del proyecto nuevo, cuando su estructura y fuente hayan sido aprobadas.
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

## Catálogo de datos: decisión pendiente

No se ha decidido JSON frente a SQLite. Se compararán ambos tras inventariar el contenido necesario, su tamaño real, los casos de búsqueda, el flujo de edición, la validación de referencias y la publicación.

## Web publicada

La página de origen es `frontend/conjugacion.html`, acompañada de `styles.css` y `app.js`. GitHub Pages publicará estos archivos mediante GitHub Actions; el workflow genera `index.html` únicamente en el artefacto de publicación para redirigir la raíz del sitio a `conjugacion.html`. FastAPI necesita un servicio de backend independiente, preparado inicialmente con `render.yaml`. No se marcará el sistema como integrado hasta probar conectividad, CORS y respuestas reales desde la web pública.

## Regla de cambios

No iniciar la generación lingüística hasta que los contratos estén aprobados. Toda modificación estructural deberá actualizar documentación y pruebas en la misma unidad de cambio.
