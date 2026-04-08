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
