# IRIS105 - Bootstrap y smoke test

## Objetivo

Dejar reproducible la preparacion minima de `iris105` para esta POC:

- aplicar el esquema SQL en `USER`;
- conceder permisos DML al usuario de aplicacion;
- ejecutar una corrida de humo del worker contra IRIS real.

## Supuestos actuales

- contenedor: `iris105`;
- instancia IRIS: `IRIS`;
- namespace de trabajo: `USER`;
- usuario de aplicacion configurado en `.env`: `admin`.

## 1. Bootstrap del esquema y permisos

Script disponible:

[`scripts/bootstrap_iris_user.py`](/Users/christian/vscode/adjuntos101/scripts/bootstrap_iris_user.py)

Ejemplo:

```bash
.venv/bin/python scripts/bootstrap_iris_user.py --env-file .env --container iris105
```

Qué hace:

- toma el DDL desde [sql/001_init.sql](/Users/christian/vscode/adjuntos101/sql/001_init.sql);
- lo ejecuta dentro del contenedor usando `iris sql`;
- concede `SELECT`, `INSERT`, `UPDATE` y `DELETE` al usuario configurado en `IRIS_USERNAME`.

## 2. Smoke test del worker contra IRIS

Script disponible:

[`scripts/smoke_test_iris_worker.py`](/Users/christian/vscode/adjuntos101/scripts/smoke_test_iris_worker.py)

Ejemplo:

```bash
.venv/bin/python scripts/smoke_test_iris_worker.py --env-file .env
```

Qué hace:

- crea un runtime temporal en `/tmp`;
- genera un documento de prueba en `In/`;
- fuerza `DATABASE_MODE=iris`;
- fuerza `PARSER_MODE=mock`;
- corre `--run-once`;
- consulta IRIS y muestra el resumen persistido.

## 3. Resultado esperado

Una corrida exitosa debe mostrar al menos:

- `current_status=PROCESSED`;
- `parse_provider=mock`;
- `parse_outcome=COMPLETED`;
- `document_type=invoice`;
- `event_count` mayor que cero.
