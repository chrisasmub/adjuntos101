# Cierre Sprint 4 y plan de Sprint 5

## Estado actual al cierre

El proyecto ya superó la etapa de POC solamente local y hoy cuenta con:

- persistencia real en IRIS sobre `USER`;
- flujo transaccional por documento;
- registro de excepciones operacionales en `doc_exception`;
- reintentos controlados iniciales para errores transitorios de parser;
- query pack operativo para consulta sobre IRIS;
- al menos una corrida real completa con `PARSER_MODE=llamaparse` y `DATABASE_MODE=iris`;
- una primera consola web para explorar documentos persistidos.

## Avances concretos logrados

### 1. Robustez operacional cerrada en el worker

Quedó implementado:

- control transaccional por documento en el repositorio `iris`;
- rollback ante fallas intermedias;
- registro de error operativo en `doc_exception`;
- persistencia consistente de `doc_document`, `doc_parse_attempt`, `doc_normalized` y `doc_event`;
- reintentos básicos para errores transitorios del parser.

## 2. Validación real con documento productivo

Se ejecutó una corrida real usando el archivo:

- `cloudflare-invoice-2026-04-09.pdf`

Resultado validado en IRIS:

- `document_id=10`;
- `current_status=PROCESSED`;
- `provider=llamaparse`;
- `provider_job_id=pjb-348kofqpi3e5xu238zjrumw343zd`;
- `document_type=invoice`;
- `issuer_name=Cloudflare, Inc.`;
- `issue_date=2026-04-09`;
- `currency=USD`;
- `total_amount=0.0`;
- `review_required=False`;
- `event_count=7`;
- `open_exceptions=0`.

Esto demuestra que la POC ya procesa un documento real extremo a extremo con:

1. claim del archivo;
2. parse real vía LlamaParse;
3. normalización;
4. validación;
5. persistencia en IRIS;
6. archivo final en `Processed`.

## 3. Consulta operacional

Quedó agregado un query pack operativo en:

- [sql/010_operational_queries.sql](/Users/christian/vscode/adjuntos101/sql/010_operational_queries.sql)

Incluye consultas para:

- últimos documentos;
- bandeja `Review`;
- errores abiertos;
- últimos eventos;
- intentos recientes de parse;
- volumen diario por estado;
- volumen diario por tipo;
- historial detallado por `document_id`.

## 4. Consola web inicial

Quedó creada una primera consola web en:

- [src/adjuntos_worker/webapp.py](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/webapp.py)

Objetivo de esta consola:

- listar documentos persistidos;
- filtrar por estado;
- buscar por archivo, emisor o tipo;
- mostrar detalle con parse attempts, eventos, excepciones y `normalized.json`.

## Brecha abierta al cierre

La consola web **no quedó cerrada** para detalle de documento.

Bug abierto reproducido:

- `GET /documents/10` devuelve `500`;
- mensaje observado:
  - `<COMMUNICATION LINK ERROR> Cursor closed; Details: DataRow is inaccessible and/or Cursor is closed`

Observación:

- el listado principal `/` sí responde;
- el error aparece al abrir el detalle de un documento;
- ya existe una hipótesis fuerte de que la causa está en el manejo del cursor/`DataRow` del driver de IRIS dentro de la vista de detalle, pero no se cerró completamente en esta sesión.

## Evaluación del sprint

### Objetivo cumplido

Sí, el objetivo principal del sprint quedó cumplido:

- el pipeline real con LlamaParse e IRIS funciona y procesa documentos reales.

### Objetivo parcialmente cumplido

Sí, la capa de consulta quedó parcial:

- hay query pack operativo usable;
- existe consola web inicial;
- la vista de detalle web sigue fallando y debe tratarse como trabajo pendiente del siguiente sprint.

## Próximo sprint propuesto

### Nombre sugerido

Sprint 5 - Consola operacional y cierre de consulta sobre IRIS

### Objetivo

Cerrar la capa de consulta y operación diaria sobre la POC, estabilizando la consola web y ampliando la trazabilidad visible para soporte y demo.

## Backlog priorizado

### P0. Corregir detalle web por documento

- reproducir y aislar el error de `DataRow`/cursor en `GET /documents/<id>`;
- refactorizar la capa de lectura para materializar resultados de IRIS sin depender del cursor vivo;
- agregar prueba automatizada para el caso de detalle.

### P0. Endurecer capa de lectura para la consola

- separar consultas de listado y detalle en funciones más pequeñas;
- evitar reutilización riesgosa de cursor en cascada;
- definir una pequeña capa DTO para resultados de lectura;
- manejar mejor errores de lectura para que la UI no caiga completa.

### P1. Mejorar experiencia de la consola web

- agregar links visibles a `parse.md`, `parse_raw.json` y `normalized.json`;
- mostrar resumen superior con contadores por estado;
- resaltar `provider_job_id`, hash y rutas de artefactos;
- mejorar navegación entre listado y detalle.

### P1. Endpoints o vistas auxiliares

- agregar vista o endpoint JSON para documento individual;
- exponer una vista simple para errores abiertos;
- exponer una vista simple para documentos en `Review`.

### P1. Reintentos y robustez residual

- revisar si conviene incorporar reintentos específicos para errores DB transitorios;
- distinguir con más claridad en eventos cuando un fallo fue reintentado versus terminal;
- validar comportamiento de la consola frente a caídas temporales de IRIS.

### P2. Operación de despliegue local

- documentar puerto recomendado para la consola cuando `8080` esté ocupado;
- definir comando recomendado de arranque para desarrollo local;
- evaluar si conviene un script dedicado `run_web_console.sh` o similar.

## Secuencia sugerida

### Semana 1

- cerrar bug de `/documents/<id>`;
- agregar pruebas de la consola;
- estabilizar la capa de lectura desde IRIS.

### Semana 2

- agregar links a artefactos y vistas auxiliares;
- mejorar ergonomía del dashboard;
- revisar reintentos DB y observabilidad residual.

## Criterios de aceptación del Sprint 5

- la ruta `/documents/<id>` funciona sin error para documentos reales ya persistidos;
- la consola muestra parse attempts, eventos y excepciones de un documento;
- la consola permite llegar fácilmente a artefactos archivados;
- existe al menos una prueba automatizada sobre la vista de detalle;
- la operación puede usar navegador + query pack sin depender de inspección manual en tablas.

## Recomendación práctica para retomar

Al iniciar la próxima sesión, el orden recomendado es:

1. reproducir el `500` de `/documents/10`;
2. aislar el acceso a `DataRow` y cursor en la capa de lectura;
3. dejar prueba de regresión;
4. recién después mejorar UI y links a artefactos.
