# Sprint 3 - Plan de ejecución basado en el análisis local

## 1. Resumen ejecutivo

El proyecto ya cerró una base funcional sólida para los dos primeros sprints:

- el worker local procesa documentos de punta a punta;
- existe integración real con LlamaParse vía `llama_cloud`;
- el pipeline genera artefactos y decide entre `Processed`, `Review`, `Error` y duplicados;
- las pruebas locales actuales pasan con `python3 -m unittest discover -s tests -q`.

El siguiente sprint debe enfocarse en cerrar la brecha entre una POC funcional en filesystem y una POC operable con persistencia real en IRIS.

## 2. Hallazgos del análisis local

### Lo que ya está implementado y utilizable

- orquestación completa del flujo en [src/adjuntos_worker/orchestrator.py](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/orchestrator.py);
- repositorio real para IRIS en [src/adjuntos_worker/repositories/iris.py](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/repositories/iris.py);
- esquema físico base en [sql/001_init.sql](/Users/christian/vscode/adjuntos101/sql/001_init.sql);
- configuración por `.env` en [src/adjuntos_worker/config.py](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/config.py);
- pruebas unitarias para config, fingerprint, normalización, worker y cliente LlamaParse.

### Brechas reales observadas

1. No existe transacción por documento en IRIS.
   El repositorio hace `commit()` después de casi cada operación, por lo que una falla intermedia puede dejar estados parciales persistidos.
   Referencia: [src/adjuntos_worker/repositories/iris.py#L69](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/repositories/iris.py#L69), [src/adjuntos_worker/repositories/iris.py#L97](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/repositories/iris.py#L97), [src/adjuntos_worker/repositories/iris.py#L114](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/repositories/iris.py#L114), [src/adjuntos_worker/repositories/iris.py#L173](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/repositories/iris.py#L173), [src/adjuntos_worker/repositories/iris.py#L260](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/repositories/iris.py#L260).

2. `doc_exception` existe en SQL pero no en la implementación del worker.
   La tabla está creada, pero no hay métodos en el protocolo del repositorio ni uso desde el orquestador.
   Referencia: [sql/001_init.sql#L60](/Users/christian/vscode/adjuntos101/sql/001_init.sql#L60), [src/adjuntos_worker/repositories/base.py](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/repositories/base.py), [src/adjuntos_worker/orchestrator.py#L246](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/orchestrator.py#L246).

3. El manejo de error actual es reactivo, pero no deja trazabilidad operacional suficiente en base.
   Hoy se intenta marcar `ERROR` y registrar un evento, pero no queda una excepción formal con etapa, severidad y motivo.
   Referencia: [src/adjuntos_worker/orchestrator.py#L246](/Users/christian/vscode/adjuntos101/src/adjuntos_worker/orchestrator.py#L246).

4. No hay reintentos controlados para fallas transitorias de parser o base de datos.
   Esto sigue alineado con la deuda ya documentada para Sprint 3.

5. No hay pruebas de integración contra IRIS real.
   Las pruebas que pasan hoy cubren bien la lógica local, pero no validan conectividad, commit, rollback, DDL ni compatibilidad DB-API real.

6. Falta un paquete mínimo de operación.
   No existen consultas SQL operativas, script de bootstrap del esquema ni guía reproducible para una corrida de demo con IRIS.

7. Hay un riesgo de higiene de configuración que conviene corregir al inicio del sprint.
   `.env.example` contiene valores concretos sensibles y específicos del entorno local.
   Referencia: [.env.example#L1](/Users/christian/vscode/adjuntos101/.env.example#L1), [.env.example#L12](/Users/christian/vscode/adjuntos101/.env.example#L12), [.env.example#L15](/Users/christian/vscode/adjuntos101/.env.example#L15).

## 3. Objetivo del sprint

Dejar el pipeline funcionando contra IRIS real, con persistencia consistente por documento, excepciones registradas, validación de rollback y soporte operativo mínimo para demo y troubleshooting.

## 4. Entregables comprometidos

- conexión real a IRIS validada desde el worker;
- ejecución reproducible del DDL en la instancia objetivo;
- `IrisRepository` con soporte explícito para transacción por documento;
- persistencia de `doc_exception`;
- manejo consistente de `ERROR`, `REVIEW`, `PROCESSED` y `DUPLICATE`;
- pruebas de integración mínimas para IRIS;
- set de consultas SQL operativas;
- evidencia de una corrida real extremo a extremo.

## 5. Backlog propuesto del sprint

### P0. Cierre de integración real con IRIS

- confirmar host, puerto, namespace, usuario y credenciales de la instancia objetivo;
- instalar y validar `intersystems-irispython` en el entorno operativo;
- ejecutar [sql/001_init.sql](/Users/christian/vscode/adjuntos101/sql/001_init.sql) sobre la instancia real;
- verificar conexión desde `IrisRepository.from_settings()`;
- documentar un procedimiento corto de bootstrap local.

### P0. Transacción por documento y consistencia

- extender el contrato del repositorio con `begin`, `commit` y `rollback`, o encapsular una unidad de trabajo equivalente;
- evitar `commit()` por operación y mover el cierre transaccional al nivel del documento;
- definir qué eventos se escriben dentro de la transacción y qué evidencia debe sobrevivir a un rollback;
- probar fallas parciales en persistencia de parse y normalización.

### P0. Excepciones operacionales

- agregar métodos para abrir y cerrar `doc_exception`;
- registrar etapa, severidad, `reason_code` y detalle de error;
- actualizar el orquestador para abrir excepción al fallar parse, normalización o persistencia;
- asegurar que un documento con error quede consultable sin ambigüedad.

### P1. Reintentos acotados y errores transitorios

- definir qué errores son reintentables en parser y DB;
- implementar reintentos con límite y logging;
- distinguir error transitorio versus error terminal en eventos y excepciones.

### P1. Operación y observabilidad mínima

- crear un `query pack` con consultas para:
  - documentos por estado;
  - documentos en `Review`;
  - errores abiertos;
  - últimos eventos por documento;
  - intentos de parse recientes;
- documentar una corrida de demo con comandos y evidencia esperada;
- dejar una guía de troubleshooting mínima.

### P1. Pruebas de integración y evidencia

- agregar pruebas de integración opcionales para IRIS real o contenedor dedicado;
- validar inserción de `doc_document`, `doc_event`, `doc_parse_attempt`, `doc_normalized` y `doc_exception`;
- validar rollback ante falla inducida;
- correr al menos un documento real con `DATABASE_MODE=iris` y guardar evidencia.

### P2. Higiene y endurecimiento rápido

- reemplazar valores sensibles de `.env.example` por placeholders seguros;
- revisar nombres y mensajes de estados para mantener consistencia operacional;
- evaluar si conviene agregar script de smoke test para conexión a IRIS.

## 6. Secuencia sugerida de ejecución

### Semana 1

- cerrar acceso al ambiente IRIS;
- ejecutar DDL y validar conexión;
- refactorizar `IrisRepository` para manejar transacciones;
- probar flujo feliz con inserciones reales.

### Semana 2

- implementar `doc_exception`;
- cubrir rollback y errores parciales;
- agregar query pack y guía operativa;
- ejecutar demo real con evidencia final.

## 7. Criterios de aceptación del sprint

- el worker procesa al menos un documento real usando `DATABASE_MODE=iris`;
- un documento exitoso deja registros coherentes en `doc_document`, `doc_event`, `doc_parse_attempt` y `doc_normalized`;
- una falla inducida deja rollback consistente o excepción abierta según la política definida;
- `doc_exception` queda poblada para errores reales del pipeline;
- operación puede consultar revisión, errores y últimas corridas sin depender del filesystem;
- existe evidencia reproducible para demo y soporte.

## 8. Riesgos y mitigación inmediata

- dependencia del ambiente IRIS:
  mitigar confirmando acceso y credenciales antes de arrancar desarrollo.

- ambigüedad de diseño transaccional:
  mitigar definiendo desde el primer día la frontera exacta de la transacción por documento.

- falta de casos reales:
  mitigar seleccionando uno o dos documentos base para prueba feliz y prueba con error.

- exposición de secretos en configuración ejemplo:
  mitigar reemplazando placeholders y rotando cualquier credencial real usada durante la POC.

## 9. Definición de terminado del sprint

El sprint se considera cerrado cuando:

- IRIS real está conectado y validado;
- la persistencia es consistente ante éxito y error;
- las excepciones quedan registradas;
- la operación dispone de consultas básicas;
- existe una demo reproducible del flujo real con evidencia.
