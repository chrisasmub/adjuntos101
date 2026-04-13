# Adjuntos101

POC para procesamiento documental sobre una carpeta sincronizada en Google Drive, con un worker Python externo ejecutándose en un Mac mini, LlamaParse para parsing documental e InterSystems IRIS Community como repositorio relacional y bitácora operacional.

## Objetivo de la POC

Demostrar un flujo robusto y trazable que:

1. detecta documentos nuevos en una carpeta sincronizada;
2. evita reprocesos con idempotencia por hash;
3. clasifica y parsea documentos con LlamaParse;
4. normaliza el resultado a un JSON canónico;
5. persiste metadata, estados, eventos e incidencias en IRIS;
6. separa correctamente documentos exitosos, duplicados, en revisión y con error.

## Decisión arquitectónica principal

La POC se construirá con:

- Capa 3: worker Python externo en el Mac mini
- Capa 4: InterSystems IRIS Community como persistencia relacional

No se utilizará Embedded Python dentro de IRIS en esta primera etapa. La lógica de negocio, validación, clasificación y orquestación quedará concentrada en Python.

## Documentación disponible

- [Resumen de requerimientos y alcance](docs/01-requerimiento-y-alcance.md)
- [Arquitectura de la POC](docs/02-arquitectura-poc.md)
- [Plan de implementación por sprints](docs/03-plan-sprints.md)
- [Backlog, criterios y riesgos](docs/04-backlog-criterios-y-riesgos.md)
- [Operación técnica de Sprint 1](docs/05-sprint-1-operacion.md)
- [Operación técnica de Sprint 2](docs/06-sprint-2-operacion.md)
- [Prueba LlamaParse con SDK](docs/07-prueba-llamaparse-sdk.md)
- [Estado actual y próximo sprint](docs/08-estado-actual-y-proximo-sprint.md)
- [Plan de ejecución de Sprint 3](docs/09-plan-sprint-3-ejecucion.md)
- [Bootstrap y smoke test sobre iris105](docs/10-iris105-bootstrap-y-smoke-test.md)
- [Plan de Sprint 4 sobre robustez operacional](docs/11-plan-sprint-4-robustez-operacional.md)
- [Cierre Sprint 4 y plan de Sprint 5](docs/12-cierre-sprint-4-y-plan-sprint-5-web-console.md)
- [Entorno IRIS canónico](docs/13-entorno-iris-canonico.md)
- [Query pack operativo sobre IRIS](sql/010_operational_queries.sql)

## Entorno IRIS canónico

La referencia operativa oficial de este proyecto es:

- contenedor Docker: `iris105`
- host: `localhost`
- puerto superserver: `1972`
- namespace: `USER`
- schema SQL: `SQLUser`

DSN esperado:

```text
localhost:1972/USER
```

Nota importante:
en la máquina puede existir otro contenedor llamado `iris` publicado en `11972`, pero ese no es el target por defecto de `adjuntos101`.

## Resultado esperado al cierre

Al terminar los sprints definidos, el proyecto debería contar con:

- estructura base del worker Python;
- esquema físico de IRIS para documentos, intentos, normalizados, eventos y excepciones;
- integración funcional con LlamaParse v2 por upload;
- procesamiento extremo a extremo de documentos reales de la POC;
- documentación operativa suficiente para demo, soporte y siguiente iteración.

## Sprint 1 implementado

El repo ya incluye la base técnica del primer sprint:

- worker Python con modo `--run-once` o ciclo continuo;
- scanner por carpeta y validación de estabilidad;
- claim atomico en `Processing/<uuid>/`;
- hash SHA-256 e idempotencia;
- persistencia del documento y eventos en repositorio;
- backend `iris` real y backend `noop` para desarrollo local;
- DDL inicial en [sql/001_init.sql](sql/001_init.sql);
- pruebas mínimas del flujo base.

### Ejecución local rápida

```bash
cp .env.example .env
PYTHONPATH=src python3 -m adjuntos_worker --env-file .env --run-once
```

Para validación sin IRIS, cambiar `DATABASE_MODE=noop` en `.env`.

### Consola web

Para consultar documentos ya persistidos en IRIS desde navegador:

```bash
PYTHONPATH=src python3 -m adjuntos_worker.webapp --env-file .env --host 127.0.0.1 --port 8080
```

O usando el script instalado:

```bash
adjuntos-web --env-file .env --host 127.0.0.1 --port 8080
```

La app expone:

- `/` listado filtrable de documentos;
- `/documents/<id>` detalle con normalizado, parse attempts, eventos, excepciones y artefactos;
- `/documents/<id>/artifacts/<name>` para abrir artefactos del bundle archivado, por ejemplo `original`, `parse_raw`, `parse_markdown` o `normalized_json`.

## Sprint 2 implementado

El pipeline ya incluye:

- clasificación preliminar y selección de tier;
- cliente `mock` y cliente `llamaparse`;
- parseo con persistencia de `doc_parse_attempt`;
- normalización a JSON canónico;
- validación de campos mínimos;
- archivado de artefactos en `Archive/`;
- enrutamiento a `Processed` o `Review`.

La integración principal con LlamaParse usa el SDK oficial `llama_cloud`, igual que la prueba manual del proyecto.

Los scripts Python del proyecto usan `.env` como fuente principal de configuración. Si un valor no se pasa por CLI, se toma desde ese archivo.

## Próximo foco

El siguiente sprint queda orientado a cerrar la consola operacional sobre IRIS:

- resolver el error de detalle en `/documents/<id>`;
- robustecer la capa de lectura para la web;
- exponer mejor parse attempts, eventos, excepciones y artefactos desde navegador.
