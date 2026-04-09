# Prueba LlamaParse con SDK oficial

Se agregó una prueba de integración basada en el ejemplo compartido, usando el SDK oficial `llama_cloud` y `AsyncLlamaCloud`.

Archivo:

- [scripts/test_llamaparse_sdk.py](/Users/christian/vscode/adjuntos101/scripts/test_llamaparse_sdk.py)

## Qué hace

1. toma un archivo local;
2. lo sube con `client.files.create(..., purpose="parse")`;
3. invoca `client.parsing.parse(...)`;
4. solicita `expand=["markdown_full"]`;
5. imprime `file_id`, `parse_job_id` y markdown, o lo guarda a disco.

## Dependencia

La dependencia opcional quedó declarada en [pyproject.toml](/Users/christian/vscode/adjuntos101/pyproject.toml):

```toml
[project.optional-dependencies]
llamacloud = ["llama-cloud>=1.6.0"]
```

## Ejecución

1. Instalar dependencia:

```bash
python3 -m pip install -e '.[llamacloud]'
```

2. Configurar `.env`.

El script ahora lee por defecto:

- `LLAMAPARSE_API_KEY`
- `LLAMAPARSE_COMPLEX_TIER`
- `LLAMAPARSE_VERSION`

desde el archivo `.env`.

3. Opcionalmente, exportar una API key para sobreescribir `.env`:

```bash
export LLAMA_CLOUD_API_KEY='tu_api_key'
```

4. Ejecutar la prueba:

```bash
python3 scripts/test_llamaparse_sdk.py ./my_document.pdf --output-file /tmp/llamaparse.md
```

## Notas

- El script acepta `LLAMA_CLOUD_API_KEY` o `LLAMAPARSE_API_KEY`.
- Si no pasas `--tier` o `--version`, usa `.env`.
- También acepta `--env-file` para apuntar a otro archivo de configuración.
- Si `markdown_full` no viene en la respuesta, hace fallback a `markdown`.

## Fuente base usada

El script sigue el patrón compartido por el usuario y coincide con el SDK oficial actual `llama_cloud` publicado en PyPI:

- https://pypi.org/project/llama-cloud/
