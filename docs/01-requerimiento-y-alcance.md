# Requerimiento y alcance

## 1. Resumen ejecutivo

Se requiere una POC capaz de procesar documentos recibidos en una carpeta sincronizada de Google Drive sobre un Mac mini. El sistema debe detectar archivos nuevos, esperar estabilidad de sincronización, reclamar el archivo para evitar doble procesamiento, parsearlo con LlamaParse, normalizar su contenido a un esquema canónico y persistir trazabilidad operacional en InterSystems IRIS Community.

La solución debe privilegiar simplicidad, trazabilidad e idempotencia. La meta de la POC no es resolver todos los casos documentales posibles, sino demostrar un flujo confiable, operable y auditable.

## 2. Objetivos

### Objetivo general

Construir una POC de procesamiento documental que permita recibir, clasificar, parsear, normalizar y registrar documentos con un nivel suficiente de robustez para evaluación funcional y técnica.

### Objetivos específicos

- Procesar automáticamente archivos soportados desde una carpeta `In`.
- Evitar doble procesamiento mediante `sha256` como clave de idempotencia.
- Usar LlamaParse v2 por upload como parser principal.
- Unificar la salida en un JSON canónico de negocio.
- Persistir estados, intentos, excepciones y eventos en IRIS.
- Disponer de bandejas operativas claras: `Processed`, `Review`, `Error` y duplicados.

## 3. Problema que resuelve

Hoy el procesamiento de adjuntos financieros o administrativos suele ser manual, poco trazable y sensible a fallas de sincronización, duplicados o parsing inconsistente. La POC busca validar una arquitectura liviana donde:

- Python concentra inteligencia y control de flujo;
- LlamaParse resuelve parsing documental;
- IRIS actúa como repositorio relacional, historial y consulta operacional.

## 4. Decisiones de arquitectura ya tomadas

### Decisión 1

Usar un worker Python externo ejecutándose en el Mac mini.

### Decisión 2

Usar InterSystems IRIS Community como capa relacional y bitácora operacional.

### Decisión 3

No usar Embedded Python dentro de IRIS en la POC inicial.

### Decisión 4

No usar un watcher de filesystem puro como motor principal; se usará scanner programado cada 30 a 60 segundos.

### Decisión 5

No almacenar blobs pesados en IRIS durante la primera etapa; se almacenarán en filesystem bajo `Archive/` y se persistirán rutas en base de datos.

## 5. Alcance funcional incluido

La POC sí incluye:

- detección de archivos nuevos en carpeta sincronizada;
- verificación de estabilidad por antiguedad y tamano estable;
- claim atomico moviendo el archivo a `Processing/<uuid>/`;
- fingerprint del documento;
- validación de duplicado por hash;
- clasificación preliminar por reglas;
- integración con LlamaParse v2 por `/parse/upload`;
- normalización a un JSON canónico;
- validación de campos mínimos por tipo documental;
- persistencia de metadata, intentos, normalizado, eventos y excepciones en IRIS;
- movimiento del archivo a `Processed`, `Review`, `Error` o duplicados;
- archivo de artefactos de proceso en `Archive/YYYY/MM/DD/<sha256>/`.

## 6. Fuera de alcance para esta POC

No forma parte del MVP:

- extracción detallada de movimientos linea por linea;
- uso de webhooks de LlamaParse;
- multiworker avanzado con coordinación distribuida;
- UI de operación;
- ingestion desde email en forma nativa;
- OCR alternativo o fallback con otro proveedor;
- reglas complejas de negocio dentro de IRIS;
- almacenamiento de PDF binario en tablas;
- Embedded Python, producciones Interoperability o BPM dentro de IRIS.

## 7. Tipos documentales objetivo

La POC apunta inicialmente a:

- facturas;
- boletas;
- estados de cuenta de tarjeta;
- cartolas bancarias;
- estados o cartolas de fondos mutuos.

## 8. Requerimientos funcionales

### RF-01 Detección

El sistema debe escanear la carpeta `In` a intervalos configurables y detectar archivos candidatos con extensiones permitidas.

### RF-02 Estabilidad

El sistema debe descartar temporalmente archivos que aun se esten sincronizando.

### RF-03 Claim

El sistema debe tomar propiedad exclusiva del archivo mediante un move atomico a `Processing`.

### RF-04 Idempotencia

El sistema no debe reprocesar archivos ya registrados con el mismo `attachment_hash`.

### RF-05 Parsing

El sistema debe enviar archivos a LlamaParse y recuperar resultado estructurado y markdown.

### RF-06 Normalización

El sistema debe transformar la respuesta del parser a un esquema canónico comun.

### RF-07 Validación

El sistema debe validar campos mínimos por tipo documental y decidir si el documento se procesa o pasa a revisión.

### RF-08 Persistencia

El sistema debe registrar estados, intentos, datos normalizados, eventos y excepciones en IRIS.

### RF-09 Trazabilidad

El sistema debe poder reconstruir la historia de procesamiento de cada documento.

### RF-10 Gestión operacional

El sistema debe separar físicamente documentos exitosos, duplicados, revisables y fallidos.

## 9. Requerimientos no funcionales

- Robustez frente a sincronización parcial de Google Drive.
- Trazabilidad completa por documento.
- Idempotencia determinista.
- Operación simple en un único host.
- Configuración por variables de entorno.
- Logging estructurado en JSON.
- Reintentos acotados para fallas transitorias.
- Facilidad de depuración por artefactos persistidos en filesystem.

## 10. Supuestos

- El Mac mini tiene acceso local estable a la carpeta sincronizada de Google Drive.
- El volumen inicial es bajo o moderado.
- Existe conectividad de red desde el Mac mini hacia LlamaParse e IRIS.
- IRIS Community estará disponible en local o red cercana.
- Se contará con credenciales validas para LlamaParse.
- La carpeta sincronizada sera la fuente inicial de documentos.

## 11. Riesgos principales

### Riesgo 1

Archivos aun en sincronización son capturados demasiado pronto.

Mitigación:
scanner por intervalo, edad mínima del archivo y validación de tamano estable.

### Riesgo 2

LlamaParse entrega salidas inconsistentes según tipo documental.

Mitigación:
normalizador desacoplado, validación por tipo y bandeja `Review`.

### Riesgo 3

Documentos con estructura compleja bajan la calidad del parse.

Mitigación:
usar `cost_effective` como default y habilitar `agentic` para documentos complejos en reglas de clasificación.

### Riesgo 4

La operación pierde auditabilidad ante errores.

Mitigación:
persistir eventos y excepciones en IRIS, ademas de guardar artefactos locales.

### Riesgo 5

La POC crece de alcance demasiado rapido.

Mitigación:
mantener foco en cabecera documental, saldos, clasificación y trazabilidad.

## 12. Criterios de éxito de la POC

La POC se considerará exitosa si logra:

- procesar extremo a extremo al menos un lote representativo de documentos reales;
- detectar duplicados por hash sin reproceso;
- enviar a `Review` los casos incompletos en lugar de fallar silenciosamente;
- registrar la historia del documento en IRIS;
- permitir consultas operacionales basicas sobre lo procesado y lo fallado;
- dejar una base clara para iterar hacia version 2.
