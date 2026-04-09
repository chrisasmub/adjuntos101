# Plan de implementación por sprints

## 1. Enfoque general

La recomendación es ejecutar la POC en **4 sprints**. Con esto se mantiene foco, se acota riesgo y se llega a una demo completa sin dispersar esfuerzo.

Cadencia sugerida:

- 4 sprints de 1 a 2 semanas cada uno;
- demo funcional al cierre de cada sprint;
- revisión de riesgo y backlog al inicio del siguiente sprint.

## 2. Estrategia de entrega

La entrega se construye de adentro hacia afuera:

1. base operativa y persistencia;
2. parsing y normalización;
3. robustez operacional y excepciones;
4. hardening, evidencia y demo.

## 3. Sprint 1 - Fundaciones y columna vertebral

### Objetivo

Dejar operativo el esqueleto del sistema y la persistencia base para registrar documentos y estados sin aun depender del parsing completo.

### Resultado esperado

Un worker capaz de escanear, reclamar archivos, calcular hash, registrar el documento en IRIS y moverlo por las carpetas operativas basicas.

### Alcance

- estructura del proyecto Python;
- configuración por `.env`;
- scanner por intervalo;
- reglas de estabilidad de archivo;
- claim atomico a `Processing/<uuid>/`;
- fingerprint por `sha256`, MIME y tamano;
- conexión a IRIS por DB-API;
- DDL inicial de tablas e indices;
- repositorio con `create_document_stub`, `exists_by_hash`, `update_status`, `append_event`;
- carpetas operativas y utilidades de filesystem;
- logging estructurado.

### Historias o tareas principales

- definir layout del proyecto y dependencias;
- crear esquema físico inicial en IRIS;
- implementar `scanner.py`, `claimer.py`, `fingerprint.py`;
- implementar `repository.py` basico;
- implementar pipeline minimo sin parse;
- registrar eventos de transición;
- mover duplicados a ruta dedicada.

### Criterios de aceptación

- el worker detecta archivos estables y reclama uno a la vez;
- se crea registro maestro en IRIS;
- el hash evita reproceso;
- cada cambio de estado deja evidencia en `doc_event`;
- los archivos duplicados no vuelven a procesarse.

### Riesgo que reduce

Valida primero la operación local, que es el mayor punto de fragilidad en entornos con carpetas sincronizadas.

## 4. Sprint 2 - Integración con LlamaParse y normalización

### Objetivo

Conectar el pipeline con LlamaParse y obtener una primera salida canónica confiable para los tipos documentales objetivo.

### Resultado esperado

Documentos parseados y normalizados con persistencia de intento y artefactos crudos.

### Alcance

- `parse_client.py` con upload, polling y recuperación de resultados;
- persistencia de `doc_parse_attempt`;
- guardado de `parse_raw.json` y `parse.md` en `Archive`;
- `classifier.py` por reglas simples;
- `normalizer.py` para esquema canónico;
- `validator.py` con campos mínimos por tipo;
- enrutamiento a `Processed` o `Review`.

### Historias o tareas principales

- parametrizar tiers `cost_effective` y `agentic`;
- definir mapping de salida LlamaParse a JSON canónico;
- implementar clasificación preliminar y fallback conservador;
- guardar `normalized.json`;
- marcar `review_required` cuando falten datos críticos.

### Criterios de aceptación

- el worker sube documentos reales a LlamaParse;
- se guarda intento con `provider_job_id` y outcome;
- se genera JSON canónico consistente;
- los casos incompletos terminan en `Review`;
- los artefactos quedan accesibles por hash.

### Riesgo que reduce

Valida el corazon funcional de la POC: parsing externo y normalización.

## 5. Sprint 3 - Integración real con IRIS y robustez operacional

### Objetivo

Conectar el pipeline a una instancia real de IRIS y cerrar el flujo transaccional, manejo de errores y visibilidad operacional para operar la POC con confianza.

### Resultado esperado

Pipeline funcionando contra IRIS real, con estados completos, persistencia verificable, excepciones abiertas, reintentos controlados y consultas operacionales basicas.

### Alcance

- conexión real a IRIS vía DB-API;
- validación del esquema físico en la instancia objetivo;
- máquina de estados formalizada;
- manejo centralizado de excepciones;
- persistencia de `doc_exception`;
- reintentos transitorios para parse y DB;
- archivado final consistente en `Archive`;
- consultas SQL operativas iniciales;
- métricas basicas de volumen, error y review;
- scripts de inicialización y operación local.

### Historias o tareas principales

- validar `IrisRepository` contra instancia real;
- correr `sql/001_init.sql` en IRIS;
- implementar y verificar transacción por documento;
- asegurar transacción por documento;
- crear query pack para operación;
- registrar `ERROR`, `REVIEW` y `DUPLICATE` de forma consistente;
- validar rollback ante fallas parciales.

### Criterios de aceptación

- el worker procesa al menos un documento real contra IRIS;
- las tablas objetivo reflejan la corrida real del documento;
- cualquier error deja documento y base en estado consistente;
- las excepciones quedan registradas con etapa y severidad;
- la operación puede listar pendientes de revisión y errores abiertos;
- el archivado de evidencia es completo y repetible.

### Riesgo que reduce

Evita una demo frágil o poco auditable.

## 6. Sprint 4 - Hardening, pruebas de negocio y demo de cierre

### Objetivo

Preparar la POC para evaluación formal con documentos de prueba representativos, documentación operativa y criterios claros de siguiente paso.

### Resultado esperado

POC lista para demo, con evidencia, pruebas y backlog priorizado para una fase 2.

### Alcance

- batería de pruebas sobre documentos representativos;
- tuning de reglas de clasificación y validación;
- ajuste de thresholds y tiers;
- guía de despliegue local;
- guía operativa;
- checklist de demo;
- reporte de resultados de la POC;
- backlog v2.

### Historias o tareas principales

- ejecutar pruebas de extremo a extremo con lote controlado;
- documentar accuracy funcional por tipo;
- identificar outliers y casos para `Review`;
- preparar demo script;
- consolidar ADR y decisiones tomadas.

### Criterios de aceptación

- existe evidencia de procesamiento sobre set representativo;
- la demo recorre casos exitosos, review, duplicado y error;
- la documentación permite repetir la instalación y la operación;
- queda definida una propuesta de fase 2 realista.

### Riesgo que reduce

Evita terminar con una implementación aislada sin narrativa de negocio ni camino siguiente.

## 7. Dependencias externas por sprint

### Sprint 1

- acceso a IRIS Community;
- definición de estructura de carpetas del Mac mini.

### Sprint 2

- credenciales activas de LlamaParse;
- documentos de prueba representativos.

### Sprint 3

- estabilización del flujo base ya funcionando;
- instancia IRIS accesible y credenciales confirmadas;
- reglas de severidad y manejo operacional acordadas.

### Sprint 4

- lote de validación de negocio;
- disponibilidad de stakeholders para demo y feedback.

## 8. Hitos de control

### Hito 1

Fin Sprint 1: operación local e idempotencia demostradas.

### Hito 2

Fin Sprint 2: parse y normalización funcionando.

### Hito 3

Fin Sprint 3: conexión real a IRIS, trazabilidad y manejo de errores cerrados.

### Hito 4

Fin Sprint 4: POC presentable y lista para evaluación.

## 9. Equipo minimo sugerido

- 1 perfil backend Python;
- 1 perfil con conocimiento de IRIS y SQL;
- 1 apoyo funcional para validar documentos y reglas.

En una POC chica, dos personas pueden cubrirlo si una de ellas combina backend e integración de datos.

## 10. Recomendación final de planificación

No abrir frentes paralelos innecesarios. El orden correcto es:

1. robustez de filesystem e idempotencia;
2. parsing y normalización;
3. persistencia y observabilidad;
4. demo y aprendizaje.

Ese orden maximiza probabilidad de éxito en 4 sprints sin sobrediseñar la solución.
