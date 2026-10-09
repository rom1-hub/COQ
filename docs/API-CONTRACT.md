# Contrato preliminar de API

Estado: esqueleto de estado del servicio solamente. El contrato funcional aún no está aprobado.

## Convenciones

- Prefijo: `/api/v1`.
- JSON UTF-8.
- Identificadores internos estables, separados de etiquetas presentacionales.
- Los modelos Pydantic validan entradas y salidas.
- Los errores usarán códigos estables; el frontend no analizará mensajes internos de excepciones.

## Endpoint implementado

### `GET /api/v1/health`

Devuelve estado técnico y deja explícito que los contratos lingüísticos no están aprobados y que el motor no está disponible.

## Operaciones futuras (no implementadas)

- Obtener metadatos de tiempos/modos, formas no personales y filtros.
- Buscar verbos y sugerencias.
- Consultar la conjugación de un verbo para uno o varios tiempos/modos o formas no personales.
- Generar un conjunto de ejercicios con tiempos/modos o formas no personales, respetando las formas disponibles de cada verbo.
- Evaluar respuesta e intentos.

No se fijan todavía rutas, nombres de campos ni códigos funcionales definitivos hasta validar las historias de usuario y el contrato lingüístico.
