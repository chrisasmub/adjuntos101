# Estado actual y próximo sprint

## Estado actual del proyecto

Al cierre de los primeros dos sprints, la POC ya cuenta con una base funcional real y validada para el flujo documental.

### Avances completados

- estructura base del proyecto Python lista para evolución;
- configuración centralizada por `.env`;
- scanner por carpeta con validación de estabilidad;
- claim atómico hacia `Processing/<uuid>/`;
- fingerprint con `sha256`, MIME y metadata base;
- idempotencia por hash;
- persistencia base de documentos y eventos en repositorio;
- DDL inicial para IRIS en [sql/001_init.sql](/Users/christian/vscode/adjuntos101/sql/001_init.sql);
- integración con LlamaParse mediante SDK oficial `llama_cloud`;
- script de prueba manual con SDK en [scripts/test_llamaparse_sdk.py](/Users/christian/vscode/adjuntos101/scripts/test_llamaparse_sdk.py);
- clasificación preliminar por heurísticas;
- normalización a JSON canónico;
- validación mínima por tipo documental;
- archivado de artefactos en `Archive/`;
- enrutamiento a `Processed`, `Review`, `Error` y duplicados.

### Validaciones realizadas

- pruebas unitarias del fingerprint;
- pruebas del flujo base del worker;
- pruebas de normalización y validación;
- prueba unitaria del cliente LlamaParse con shape real del SDK;
- prueba real del script manual contra LlamaParse;
- prueba end-to-end del worker usando `PARSER_MODE=llamaparse` y `DATABASE_MODE=noop`.

### Resultado técnico actual

Hoy el sistema ya puede:

1. detectar un archivo;
2. reclamarlo;
3. parsearlo con LlamaParse;
4. generar `parse_raw.json`, `parse.md` y `normalized.json`;
5. decidir si el documento termina en `Processed` o `Review`.

## Qué queda pendiente

Todavía no está cerrada la integración real con IRIS en ambiente operativo.

Pendientes principales:

- conexión real a IRIS Community usando `intersystems-irispython`;
- ejecución del DDL en la instancia objetivo;
- persistencia real de `doc_document`, `doc_event`, `doc_parse_attempt` y `doc_normalized`;
- verificación de transacciones por documento;
- manejo operacional de errores y `doc_exception`;
- consultas SQL iniciales para operación.

## Próximo sprint

El siguiente sprint queda enfocado explícitamente en **conectar el worker a IRIS real**.

### Objetivo del próximo sprint

Dejar el pipeline funcionando contra una instancia real de IRIS, con persistencia transaccional y trazabilidad consultable.

### Alcance propuesto

- instalar y validar el driver `intersystems-irispython`;
- configurar conexión real desde `.env`;
- ejecutar [sql/001_init.sql](/Users/christian/vscode/adjuntos101/sql/001_init.sql) en IRIS;
- probar inserciones y lecturas reales desde `IrisRepository`;
- correr el worker con `DATABASE_MODE=iris`;
- validar persistencia de documentos, eventos, intentos y normalizados;
- preparar consultas SQL operativas básicas;
- dejar evidencia de una corrida real extremo a extremo con IRIS.

### Criterios de aceptación del próximo sprint

- el worker procesa al menos un documento real contra IRIS;
- `doc_document` refleja el estado final del documento;
- `doc_event` registra la secuencia operacional;
- `doc_parse_attempt` guarda el intento real de parse;
- `doc_normalized` guarda el resultado normalizado;
- el flujo deja evidencia reproducible para demo y soporte.

## Recomendación operativa

Antes de arrancar el próximo sprint conviene confirmar:

- host, puerto, namespace y credenciales de IRIS;
- si IRIS correrá en Docker o instalación local;
- si el esquema se aplicará sobre `USER` o `DOCSPOC`;
- qué documento real se usará como caso base de validación.
