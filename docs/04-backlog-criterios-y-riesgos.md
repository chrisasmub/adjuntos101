# Backlog, criterios y riesgos

## 1. Backlog priorizado

### Prioridad P0

- Crear estructura del proyecto Python.
- Implementar scanner por intervalo.
- Implementar verificación de archivo estable.
- Implementar claim atomico.
- Implementar fingerprint y hash.
- Crear esquema IRIS con 5 tablas e indices minimos.
- Implementar acceso DB-API a IRIS.
- Registrar `doc_document` y `doc_event`.
- Detectar duplicados por hash.

### Prioridad P1

- Integrar LlamaParse v2 por upload.
- Implementar polling y timeout configurables.
- Guardar `doc_parse_attempt`.
- Persistir artefactos crudos en `Archive`.
- Implementar clasificación preliminar por reglas.
- Implementar normalizador a JSON canónico.
- Implementar validador por tipo documental.
- Enviar casos incompletos a `Review`.

### Prioridad P2

- Implementar `doc_exception`.
- Implementar reintentos transitorios.
- Generar consultas operacionales iniciales.
- Crear scripts de setup local.
- Crear pruebas end to end con lote de muestra.
- Ajustar reglas de clasificación y confianza.

### Prioridad P3

- Mejorar clasificación con heurísticas adicionales.
- Agregar métricas agregadas por tipo y estado.
- Diseñar backlog de fase 2.

## 2. Criterios de aceptación globales

La POC completa debe cumplir lo siguiente:

- Todo archivo procesado queda con estado final explicito.
- Todo documento posee trazabilidad suficiente para auditoría básica.
- Un mismo hash no se procesa dos veces.
- Los errores no dejan residuos operacionales ambiguos.
- Los casos incompletos se separan en `Review` y no se pierden.
- La evidencia del parse y normalización queda almacenada por hash.
- IRIS permite consultar volumen, errores y revisión sin depender del filesystem.

## 3. Definición de terminado

Un entregable se considera terminado cuando:

- está implementado en el repositorio;
- tiene configuración documentada;
- posee logging suficiente;
- fue probado al menos en el flujo esperado;
- deja evidencia reproducible de resultado;
- no introduce huecos de operación conocidos sin registrar.

## 4. Estrategia de pruebas

### 4.1 Pruebas unitarias

Cubrir:

- hash y fingerprint;
- detección de archivo estable;
- clasificación preliminar;
- validación de campos mínimos;
- normalización de estructuras esperadas.

### 4.2 Pruebas de integración

Cubrir:

- conexión DB-API con IRIS;
- creación de documentos y eventos;
- inserción de intentos de parse;
- rollback y commit por documento;
- integración con LlamaParse usando documentos controlados.

### 4.3 Pruebas end to end

Cubrir al menos estos escenarios:

- documento valido que termina en `Processed`;
- documento incompleto que termina en `Review`;
- documento duplicado que termina en `DUPLICATE`;
- documento corrupto o fallido que termina en `Error`.

## 5. Casos de prueba minimos sugeridos

- factura simple en PDF;
- boleta en imagen;
- estado de cuenta de tarjeta con tabla;
- cartola bancaria con periodos;
- documento ruidoso o incompleto para revisión;
- archivo duplicado exacto;
- archivo corrupto o truncado.

## 6. Riesgos y mitigaciones

### Riesgo: sincronización incompleta

Mitigación:
edad mínima, doble lectura de tamano y scanner por intervalo.

### Riesgo: parse lento o timeout

Mitigación:
polling controlado, timeout, reintentos acotados y registro de excepción.

### Riesgo: normalización inconsistente

Mitigación:
mapping explicito por tipo y pruebas con lote representativo.

### Riesgo: esquema insuficiente para consultas

Mitigación:
mantener tabla maestra, intentos, normalizado, excepciones y eventos desde el inicio.

### Riesgo: crecimiento de alcance

Mitigación:
mantener fuera de fase 1 el detalle transaccional y webhooks.

## 7. Decisiones pendientes para el arranque

Aunque la arquitectura base ya esta decidida, aun conviene cerrar estas definiciones al inicio de Sprint 1:

- namespace final de IRIS para la POC;
- path exacto de carpetas en el Mac mini;
- lote inicial de documentos de prueba;
- convención de severidad para excepciones;
- regla exacta para enrutar `cost_effective` versus `agentic`.

## 8. Preguntas que NO bloquean el inicio

Se pueden resolver en paralelo sin frenar Sprint 1:

- si luego se expondrá API o UI;
- si IRIS correrá en Docker o instalación local;
- si en fase 2 se incorporará detalle transaccional;
- si se usará webhook en lugar de polling en una segunda versión.

## 9. Recomendación de governance para la POC

- mantener backlog corto y priorizado;
- demo al cierre de cada sprint;
- registrar decisiones técnicas en documentos vivos;
- medir éxito por confiabilidad operativa y trazabilidad, no por cantidad de features.
