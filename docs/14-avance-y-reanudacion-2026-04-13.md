# Avance y reanudación - 2026-04-13

Este documento deja el estado real del proyecto al cierre de esta sesión y fija los elementos de conexión necesarios para retomar sin pérdida de tiempo.

## 1. Estado actual del proyecto

El proyecto ya está operando contra:

- Google Drive local sincronizado como cola `In`
- IRIS real en Docker
- LlamaParse real vía `llama_cloud`
- consola web local para consulta de documentos y artefactos

Capacidades ya validadas:

- procesamiento real desde `In/` con `PARSER_MODE=llamaparse`
- persistencia real en IRIS con `DATABASE_MODE=iris`
- consulta web de listado y detalle de documentos
- acceso web a artefactos archivados:
  - original
  - `parse_raw.json`
  - `parse.md`
  - `normalized.json`
- reproceso manual de documentos ya parseados para mejorar normalización sin re-subir a LlamaParse

## 2. Entorno de conexión canónico

### IRIS

- contenedor Docker: `iris105`
- host: `localhost`
- superserver: `1972`
- portal web IRIS: `52773`
- namespace: `USER`
- schema SQL: `SQLUser`
- usuario de aplicación validado en la sesión: `admin`
- password operativo: revisar `.env` local

DSN esperado:

```text
localhost:1972/USER
```

Referencia complementaria:

- [Entorno IRIS canónico](docs/13-entorno-iris-canonico.md)

### LlamaParse

- modo activo al cierre: `PARSER_MODE=llamaparse`
- SDK instalado en `.venv`: `llama_cloud 2.3.0`
- endpoint usado por el proyecto: `https://api.cloud.llamaindex.ai/api/v2`
- API key operativa: revisar `.env` local

### Google Drive

- base dir operativo:

```text
/Users/christian/Library/CloudStorage/GoogleDrive-christian@casmuss.com/My Drive/ADJUNTOS
```

Carpetas relevantes:

- `In`
- `Processing`
- `Processed`
- `Review`
- `Error`
- `Archive`

### Consola web

Comando recomendado:

```bash
PYTHONPATH=src .venv/bin/python -m adjuntos_worker.webapp --env-file .env --host 127.0.0.1 --port 8091
```

URL recomendada:

```text
http://127.0.0.1:8091/
```

Nota:
usar `8091` evita chocar con el `webapp` Docker publicado en `8080`.

### Entorno Python

- virtualenv operativo: `.venv`
- los comandos del proyecto deben ejecutarse con `PYTHONPATH=src`

## 3. Configuración local requerida para retomar

Archivo fuente de verdad local:

```text
.env
```

Variables relevantes al cierre:

```env
ADJUNTOS_BASE_DIR=/Users/christian/Library/CloudStorage/GoogleDrive-christian@casmuss.com/My Drive/ADJUNTOS
DATABASE_MODE=iris
IRIS_HOST=localhost
IRIS_PORT=1972
IRIS_NAMESPACE=USER
IRIS_USERNAME=admin
PARSER_MODE=llamaparse
LLAMAPARSE_BASE_URL=https://api.cloud.llamaindex.ai/api/v2
LLAMAPARSE_DEFAULT_TIER=cost_effective
LLAMAPARSE_COMPLEX_TIER=agentic
LLAMAPARSE_VERSION=latest
```

Secretos no duplicados en docs:

- `IRIS_PASSWORD`
- `LLAMAPARSE_API_KEY`

Ambos están presentes en el `.env` local operativo.

## 4. Validaciones técnicas vigentes

Pruebas locales:

```bash
python3 -m unittest discover -s tests -q
```

Estado al cierre:

- `18` tests pasando

Smoke tests y validaciones reales ejecutadas en esta sesión:

- procesamiento real de `invoice_109300.pdf` con `llamaparse`
- procesamiento real de `cartola_mensual_marzo.pdf` con `llamaparse`
- procesamiento real de `pdf_boleta_v225575851jmch_01.pdf` con `llamaparse`
- validación de consola web contra IRIS real
- validación de detalle y artefactos por documento

## 5. Documentos reales procesados y corregidos en esta sesión

### Documento 13

- archivo: `invoice_109300.pdf`
- `document_id=13`
- parser: `llamaparse`
- `provider_job_id=pjb-sxqugodpvcczwojr0so2sraf6xdb`
- estado final: `PROCESSED`

Campos validados:

- `document_type=invoice`
- `issuer_name=Sharetribe Ltd`
- `issue_date=2026-04-08`
- `due_date=2026-05-08`
- `period_from=2026-04-08`
- `period_to=2026-05-08`
- `currency=USD`
- `total_amount=39.0`
- `account_ref_last4=4361`
- `document_number=109300`

### Documento 14

- archivo: `cartola_mensual_marzo.pdf`
- `document_id=14`
- parser: `llamaparse`
- `provider_job_id=pjb-1dskbc3pjeu9v60r48j6aasdv43a`
- estado final: `PROCESSED`

Campos validados:

- `document_type=bank_statement`
- `issuer_name=Alpaca / Fintual`
- `period_from=2026-03-01`
- `period_to=2026-03-31`
- `currency=USD`
- `balance_amount=713.14`
- `account_ref_last4=1620`

### Documento 15

- archivo: `pdf_boleta_v225575851jmch_01.pdf`
- `document_id=15`
- parser: `llamaparse`
- `provider_job_id=pjb-zjm7kt3jdf51lsr8gq3ckng2whrd`
- estado final: `PROCESSED`

Campos validados:

- `document_type=receipt`
- `issuer_name=CENCOSUD RETAIL S.A.`
- `issuer_tax_id=81201000-K`
- `issue_date=2026-04-08`
- `currency=CLP`
- `total_amount=137269.0`

## 6. Mejoras implementadas en el normalizador

Archivo tocado:

- [src/adjuntos_worker/normalizer.py](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/normalizer.py)

Mejoras ya incorporadas:

- invoices:
  - `Invoice Date`
  - `Invoice #`
  - `Invoice Amount`
  - `Billing Period`
  - emisor desde cabecera
- bank statements:
  - período mensual tipo `MARCH - 2026`
  - emisor desde logos/cabecera
  - `Account No` a últimos 4 dígitos
  - `Total Market Value` o `Ending Value` como `balance_amount`
- receipts:
  - emisor corporativo en cabecera
  - fecha con año corto `dd/mm/yy`
  - `TOTAL` correcto sin confundir `SUB TOTAL`
  - montos chilenos con separador de miles

Pruebas agregadas/extendidas:

- [tests/test_normalizer.py](/Users/christian/vscode/adjuntos101/tests/test_normalizer.py)

## 7. Consola web

Archivo principal:

- [src/adjuntos_worker/webapp.py](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/webapp.py)

Estado al cierre:

- listado funciona contra IRIS real
- detalle funciona contra IRIS real
- artefactos accesibles por navegador
- las rutas largas en tarjetas se muestran truncadas al final para no romper el layout

Rutas útiles:

- `/`
- `/documents/<id>`
- `/documents/<id>/artifacts/original`
- `/documents/<id>/artifacts/parse_raw`
- `/documents/<id>/artifacts/parse_markdown`
- `/documents/<id>/artifacts/normalized_json`

## 8. Comandos útiles para la próxima sesión

### Levantar la consola web

```bash
PYTHONPATH=src .venv/bin/python -m adjuntos_worker.webapp --env-file .env --host 127.0.0.1 --port 8091
```

### Ejecutar pruebas

```bash
python3 -m unittest discover -s tests -q
```

### Procesar un archivo puntual desde `In/`

Usar el patrón ya ocupado en esta sesión:

```bash
PYTHONPATH=src .venv/bin/python
```

Luego instanciar `WorkerApp` y llamar `app._process_candidate(path)` con un `Path` explícito.

### Consultar un documento en IRIS desde el read model

```bash
PYTHONPATH=src .venv/bin/python
```

Luego:

```python
from adjuntos_worker.config import load_config
from adjuntos_worker.webapp import IrisReadModel

config = load_config(".env")
detail = IrisReadModel(config).get_document_detail(<document_id>)
```

## 9. Siguiente punto recomendado

Documentos candidatos en `In/` para seguir ampliando cobertura:

- `pdf_ticketCambio_v225575851jmch_01.pdf`
- `confirmacion_transacciones_2026-04-09.pdf`
- `G151212545.pdf`
- `CartolaCuentaCorrienteNacionalMensual.pdf`
- `CartolaCuentaCorrienteExtranjeraMensual.pdf`

Recomendación:

1. seguir con `pdf_ticketCambio_v225575851jmch_01.pdf` para afinar otro comprobante corto;
2. después volver a una cartola bancaria distinta para validar generalización;
3. si un nuevo documento cae en `Review`, primero inspeccionar `parse.md` y luego ajustar el normalizador antes de volver a subir más documentos.
