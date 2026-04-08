# Sprint 1 - Operación técnica

## Qué quedó implementado

Sprint 1 deja lista la columna vertebral del worker:

- escaneo secuencial de `In/`;
- verificación de estabilidad por edad mínima y tamano estable;
- claim atomico a `Processing/<uuid>/`;
- fingerprint con `sha256`, MIME y tamano;
- idempotencia por hash;
- persistencia del documento y eventos en repositorio;
- movimiento final a `Processed`, `Processed/Duplicates` o `Error`;
- DDL inicial de IRIS para las 5 tablas objetivo.

## Estructura creada

```text
src/adjuntos_worker/
  cli.py
  orchestrator.py
  config.py
  scanner.py
  claimer.py
  fingerprint.py
  filesystem.py
  models.py
  repositories/
    base.py
    iris.py
    noop.py

sql/
  001_init.sql

tests/
  test_fingerprint.py
  test_worker.py
```

## Cómo ejecutar en modo local sin IRIS

1. Copiar `.env.example` a `.env`
2. Cambiar `DATABASE_MODE=noop`
3. Ajustar `ADJUNTOS_BASE_DIR`
4. Ejecutar:

```bash
PYTHONPATH=src python3 -m adjuntos_worker --env-file .env --run-once
```

## Cómo ejecutar contra IRIS

1. Instalar dependencia opcional:

```bash
python3 -m pip install -e '.[iris]'
```

2. Crear el esquema ejecutando [sql/001_init.sql](/Users/christian/vscode/adjuntos101/sql/001_init.sql)
3. Configurar `.env` con `DATABASE_MODE=iris`
4. Ejecutar el worker:

```bash
PYTHONPATH=src python3 -m adjuntos_worker --env-file .env --run-once
```

## Notas de alcance de Sprint 1

- Aun no existe integración con LlamaParse.
- Aun no existe normalización ni validación documental.
- `archive_path` hoy apunta al archivo final en `Processed/`; el esquema ya queda listo para separar `Archive/` en el Sprint 2.
- La trazabilidad de excepciones detalladas se completará en Sprint 3 con `doc_exception`.
