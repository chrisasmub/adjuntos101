# Entorno IRIS canónico del proyecto

Este documento fija la referencia operativa oficial de IRIS para `adjuntos101`.

## Fuente de verdad

Para esta POC, el entorno correcto es:

- contenedor Docker: `iris105`
- host de conexión desde el proyecto: `localhost`
- puerto superserver: `1972`
- puerto web IRIS Management Portal: `52773`
- namespace de trabajo: `USER`
- schema SQL donde viven las tablas de la POC: `SQLUser`

DSN esperado por el worker:

```text
localhost:1972/USER
```

## Aclaración importante

En la máquina existe más de un contenedor IRIS. Eso generó dudas antes porque también aparece un contenedor llamado `iris` publicado en `11972:1972`.

Para `adjuntos101`, **ese no es el target operativo**.

El target correcto es:

- `iris105` escuchando en `0.0.0.0:1972->1972/tcp`

El contenedor `iris` en `11972` pertenece a otro stack y no debe usarse como referencia por defecto para esta POC.

## Configuración esperada en `.env`

```env
DATABASE_MODE=iris
IRIS_HOST=localhost
IRIS_PORT=1972
IRIS_NAMESPACE=USER
```

El usuario y password pueden variar por entorno, pero deben corresponder a un usuario con permisos DML sobre las tablas de `SQLUser`.

## Ubicación de tablas

Las tablas de la POC están creadas en el namespace `USER` y se consultan bajo el schema SQL `SQLUser`.

Tablas principales:

- `SQLUser.doc_document`
- `SQLUser.doc_parse_attempt`
- `SQLUser.doc_normalized`
- `SQLUser.doc_exception`
- `SQLUser.doc_event`

En muchas consultas del repo se usa el nombre corto de tabla sin prefijo de schema. Eso funciona porque la conexión entra al namespace `USER`, donde el schema por defecto resuelve correctamente a `SQLUser`.

## Verificaciones rápidas

Verificar contenedor y puertos:

```bash
docker ps
```

Debe verse al menos esta referencia:

```text
iris105 ... 0.0.0.0:1972->1972/tcp ... 0.0.0.0:52773->52773/tcp
```

Verificar bootstrap y smoke test del proyecto:

```bash
.venv/bin/python scripts/bootstrap_iris_user.py --env-file .env --container iris105
.venv/bin/python scripts/smoke_test_iris_worker.py --env-file .env
```

## Regla de documentación

Si otro documento del repo contradice este archivo respecto a contenedor, puerto, namespace o schema, la referencia correcta es esta:

- `iris105`
- `localhost:1972`
- namespace `USER`
- schema `SQLUser`
