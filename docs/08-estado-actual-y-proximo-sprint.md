# Estado actual y próximo sprint

## Estado actual del proyecto

Al cierre de esta sesión, la POC ya dejó de ser solo una integración local con persistencia simulada y quedó conectada a una instancia real de IRIS.

## Avances completados

- worker Python funcional para escaneo, claim, parse, normalización y routing final;
- integración real con LlamaParse mediante `llama_cloud`;
- backend `iris` operativo vía `intersystems-irispython`;
- conexión validada contra `iris105` en `localhost:1972`;
- namespace operativo confirmado: `USER`;
- esquema SQL aplicado en IRIS a partir de [sql/001_init.sql](/Users/christian/vscode/adjuntos101/sql/001_init.sql);
- permisos DML concedidos al usuario de aplicación `admin`;
- script reproducible de bootstrap en [scripts/bootstrap_iris_user.py](/Users/christian/vscode/adjuntos101/scripts/bootstrap_iris_user.py);
- script reproducible de smoke test en [scripts/smoke_test_iris_worker.py](/Users/christian/vscode/adjuntos101/scripts/smoke_test_iris_worker.py);
- guía operativa inicial en [docs/10-iris105-bootstrap-y-smoke-test.md](/Users/christian/vscode/adjuntos101/docs/10-iris105-bootstrap-y-smoke-test.md).

## Validaciones realizadas

- conexión DB-API directa usando `iris.connect(...)` con `admin / 123`;
- conexión del proyecto usando `IrisRepository.from_settings()`;
- aplicación real del DDL en `USER`;
- validación de lectura sobre `doc_document`, `doc_parse_attempt`, `doc_normalized`, `doc_exception` y `doc_event`;
- corrida real del worker con `DATABASE_MODE=iris` y `PARSER_MODE=mock`;
- persistencia confirmada de documento, intento de parse, normalizado y eventos;
- generación de artefactos reales en `Archive/`;
- re-ejecución exitosa del bootstrap sin errores fatales sobre objetos ya existentes;
- smoke test reusable ejecutado con resultado `PROCESSED`.

## Resultado técnico actual

Hoy el sistema ya puede:

1. detectar un archivo;
2. reclamarlo;
3. parsearlo;
4. generar `parse_raw.json`, `parse.md` y `normalized.json`;
5. persistir en IRIS real;
6. dejar el archivo final en `Processed` o `Review`;
7. repetir un smoke test operativo sin depender del filesystem productivo.

## Evidencia de la última validación real

En la prueba más reciente del smoke test contra `iris105`:

- `document_id=4`;
- `current_status=PROCESSED`;
- `parse_provider=mock`;
- `parse_outcome=COMPLETED`;
- `document_type=invoice`;
- `review_required=False`;
- `event_count=7`.

## Qué queda pendiente

Todavía no está cerrada la parte de robustez operacional y consistencia transaccional del flujo.

Pendientes principales:

- transacción por documento en `IrisRepository`;
- persistencia real de `doc_exception`;
- política de rollback ante fallas parciales;
- reintentos acotados para parser y base de datos;
- pruebas de integración automatizadas contra IRIS real;
- consultas SQL operativas iniciales;
- limpieza de valores sensibles en `.env.example`;
- evidencia equivalente usando `PARSER_MODE=llamaparse` contra IRIS real.

## Próximo sprint

El siguiente sprint queda enfocado en **cerrar la robustez operacional sobre IRIS real**.

### Objetivo del próximo sprint

Dejar el pipeline consistente ante éxito y error, con excepciones registradas, rollback verificable y evidencia real usando LlamaParse más IRIS.

### Alcance propuesto

- refactorizar `IrisRepository` para manejar transacción por documento;
- eliminar `commit()` por operación y definir frontera transaccional explícita;
- implementar apertura y cierre de `doc_exception`;
- distinguir fallas terminales versus fallas reintentables;
- agregar reintentos controlados para parser y DB;
- preparar un set de queries operativas básicas;
- ejecutar al menos una corrida real con `PARSER_MODE=llamaparse` y `DATABASE_MODE=iris`;
- corregir `.env.example` para reemplazar valores sensibles por placeholders.

### Criterios de aceptación del próximo sprint

- una corrida exitosa deja persistencia coherente sin estados parciales;
- una falla inducida deja rollback o excepción abierta según política definida;
- `doc_exception` queda poblada para errores reales del pipeline;
- operación puede consultar documentos en `Review`, errores y últimos intentos;
- existe evidencia reproducible de una corrida real con LlamaParse e IRIS.
