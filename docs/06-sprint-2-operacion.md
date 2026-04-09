# Sprint 2 - Parsing, normalización y Review

## Qué quedó implementado

Sprint 2 agrega el flujo documental principal sobre la base del Sprint 1:

- clasificación preliminar por nombre y keywords;
- cliente de parse con dos modos:
  - `mock` para desarrollo local y pruebas;
  - `llamaparse` para integración real con API v2;
- almacenamiento de artefactos en `Archive/YYYY/MM/DD/<sha256>/`;
- persistencia de `doc_parse_attempt`;
- normalización a JSON canónico;
- validación de campos mínimos;
- decisión automática entre `Processed` y `Review`.

## Nuevos módulos

```text
src/adjuntos_worker/
  classifier.py
  normalizer.py
  validator.py
  parse_clients/
    mock.py
    llamaparse.py
```

## Artefactos persistidos

Por cada documento parseado se genera un bundle en `Archive` con:

```text
Archive/YYYY/MM/DD/<sha256>/
  original.ext
  parse_raw.json
  parse.md
  normalized.json
```

`doc_document.archive_path` ahora apunta al directorio del bundle en `Archive`.

## Modo local recomendado

Para validar el pipeline sin depender de red:

1. Copiar `.env.example` a `.env`
2. Configurar:

```env
DATABASE_MODE=noop
PARSER_MODE=mock
```

3. Ejecutar:

```bash
PYTHONPATH=src python3 -m adjuntos_worker --env-file .env --run-once
```

## Modo LlamaParse real

Configurar:

```env
PARSER_MODE=llamaparse
LLAMAPARSE_API_KEY=...
LLAMAPARSE_BASE_URL=https://api.cloud.llamaindex.ai/api/v2
LLAMAPARSE_DEFAULT_TIER=cost_effective
LLAMAPARSE_COMPLEX_TIER=agentic
LLAMAPARSE_VERSION=latest
```

El worker usa:

- `POST /parse/upload` para subir el archivo;
- `GET /parse/{job_id}?expand=markdown,items` para polling y resultado.

## Notas de alcance de Sprint 2

- La normalización es heurística y deliberadamente conservadora.
- Cuando faltan campos clave, el documento se envía a `Review` en vez de forzar una falsa extracción.
- Todavía no se implementa `doc_exception`; eso queda para Sprint 3.
- Aún no hay reintentos específicos de parse o DB; también queda para Sprint 3.
