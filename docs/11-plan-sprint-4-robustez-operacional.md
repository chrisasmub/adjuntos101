# Sprint 4 - Robustez operacional sobre IRIS real

## Objetivo

Cerrar las brechas que todavía separan una POC funcional de una POC confiable para demo, soporte y evaluación técnica.

El foco ya no es "conectar a IRIS", porque eso quedó resuelto. El foco ahora es garantizar consistencia, manejo de errores y evidencia real con el parser productivo.

## Contexto de partida

El proyecto ya cuenta con:

- conexión real a `iris105`;
- esquema SQL aplicado en `USER`;
- usuario `admin` con permisos DML sobre las tablas de la POC;
- worker validado extremo a extremo contra IRIS usando `PARSER_MODE=mock`;
- bootstrap reproducible y smoke test documentados.

## Objetivos concretos del sprint

- asegurar transacción por documento;
- registrar excepciones operacionales en `doc_exception`;
- definir rollback y consistencia ante fallas parciales;
- cubrir errores transitorios con reintentos acotados;
- dejar consultas operativas básicas;
- validar una corrida real con `PARSER_MODE=llamaparse` más IRIS.

## Backlog priorizado

### P0. Consistencia transaccional

- agregar soporte de `begin`, `commit` y `rollback` en el repositorio `iris`;
- mover el control transaccional al nivel del documento;
- revisar el orden de persistencia entre `doc_document`, `doc_parse_attempt`, `doc_normalized` y `doc_event`;
- validar qué evidencia queda dentro de la transacción y qué evidencia queda fuera.

### P0. Excepciones operacionales

- extender el contrato del repositorio para abrir y cerrar `doc_exception`;
- persistir `stage`, `severity`, `reason_code` y `reason_detail`;
- registrar excepciones desde el bloque de error del orquestador;
- asegurar que `ERROR` y `REVIEW` queden consultables con contexto suficiente.

### P1. Reintentos controlados

- identificar errores transitorios del parser;
- identificar errores transitorios de DB;
- implementar reintentos con límite y logging claro;
- distinguir en eventos si el error fue reintentado o terminal.

### P1. Operación y consultas

- crear un query pack para:
  - documentos por estado;
  - pendientes de `Review`;
  - errores abiertos;
  - últimos eventos por documento;
  - intentos recientes de parse;
- documentar comandos de operación diaria sobre `iris105`.

### P1. Validación real con LlamaParse

- ejecutar una corrida de prueba con `PARSER_MODE=llamaparse` y `DATABASE_MODE=iris`;
- verificar persistencia real de `provider_job_id`, artefactos y normalizado;
- guardar evidencia mínima para demo y troubleshooting.

### P2. Higiene de configuración

- reemplazar secretos y paths reales en `.env.example`;
- dejar placeholders seguros para IRIS y LlamaParse;
- revisar README y docs para que el flujo recomendado sea reproducible.

## Secuencia sugerida

### Semana 1

- refactor transaccional en `IrisRepository`;
- integración de `doc_exception`;
- prueba inducida de error y rollback.

### Semana 2

- reintentos controlados;
- query pack operativo;
- corrida real con LlamaParse más IRIS;
- documentación final de evidencia.

## Riesgos principales

- que el control transaccional en IRIS obligue a ajustar el orden actual del orquestador;
- que errores de parser y persistencia requieran políticas distintas;
- que la corrida real con LlamaParse exponga casos nuevos de `Review` o excepciones no cubiertas.

## Criterios de aceptación

- existe transacción por documento comprobada;
- `doc_exception` se registra ante fallas reales;
- una falla parcial no deja el documento en estado ambiguo;
- hay al menos una corrida exitosa con LlamaParse e IRIS;
- la operación puede consultar estado, errores y revisión sin inspección manual del filesystem.
