# Operación de migraciones y credenciales PostgreSQL

> Esquema vigente: 035. Las migraciones 001-034 permanecen inmutables.

## Identidades

- `POSTGRES_ADMIN_USER`/`POSTGRES_ADMIN_PASSWORD`: owner/bootstrap. Se usan sólo en inicialización, migraciones, respaldo y operaciones administrativas explícitas.
- `software_pa_app`: rol `NOLOGIN` que contiene el contrato DML de la aplicación.
- `DB_RUNTIME_USER`/`DB_RUNTIME_PASSWORD`: LOGIN usado exclusivamente por FastAPI; por defecto `pa_runtime`. Hereda sólo `software_pa_app` y no posee schema ni tablas.

El servicio `backend` recibe únicamente `DB_RUNTIME_*`. El servicio `db` recibe las credenciales bootstrap como `POSTGRES_*` y las credenciales runtime para que los scripts de provisión las lean sin incluirlas en SQL ni argumentos de `psql`.

## Volumen existente en 033

`docker-entrypoint-initdb.d` no se vuelve a ejecutar. El orden obligatorio es:

```bash
set -a; source .env; set +a
docker compose stop backend
docker compose up -d --force-recreate db

# Genera y verifica aquí el respaldo restorable de la base 033.
docker compose exec -T db sh -lc \
  'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -' \
  < backend/db/migrations/034_separacion_usuario_runtime_postgresql.sql

backend/scripts/utils/set_runtime_credentials.sh
docker compose up -d --force-recreate backend
curl --fail http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/health
```

`set_runtime_credentials.sh` se ejecuta después de 034. Valida que 034 esté registrada, crea o ajusta el LOGIN indicado por `DB_RUNTIME_USER`, fuerza atributos no administrativos, elimina membresías/privilegios directos, concede sólo `software_pa_app` y prueba autenticación TCP. No imprime la contraseña.

## Instalación limpia

1. `docker compose up -d db` crea PGDATA y ejecuta 001 más `002_create_runtime.sh`.
2. Crear el primer administrador mediante `scripts/create_admin.py` con `ADMIN_DATABASE_MODE=owner` y credenciales owner inyectadas sólo al contenedor one-off.
3. Aplicar la secuencia real 004-030 con el owner.
4. Cargar `backend/db/fixtures/001_catalogo_territorial_inegi.sql`.
5. Generar y verificar el respaldo pre-031.
6. Aplicar 031, 032, 033, 034 y 035 con el owner y los gates destructivos requeridos por 031/032.
7. Ejecutar `backend/scripts/utils/set_runtime_credentials.sh`.
8. Arrancar backend y verificar `/health` y `SELECT current_user` desde `app.database.engine`.

No se deben ejecutar 002/003 ni reordenar 004-030: `001` es la baseline real del entrypoint y la historia posterior comienza en 004.

## Migraciones futuras

Las migraciones se ejecutan como el owner configurado en `POSTGRES_ADMIN_USER`. La 034 instala para ese `current_user` default privileges que conceden a `software_pa_app` sólo `SELECT`, `INSERT`, `UPDATE` en tablas y `USAGE`, `SELECT` en secuencias. No concede `DELETE`, `TRUNCATE`, DDL, ownership ni `GRANT ALL`.

Antes de arrancar FastAPI, ejecutar:

```bash
set -a; source .env; set +a
backend/db/tests/034_runtime_privileges.sh
```

El contrato crea como owner una tabla probe futura, verifica sus default privileges, se conecta por TCP como runtime, prueba DML permitido, exige SQLSTATE `42501` para operaciones destructivas y elimina el probe como owner.

## Completitud operativa 035

`035_completitud_seguimiento_operativo.sql` es aditiva y registra únicamente datos de seguimiento inequívocos: contexto del proceso de Asamblea, acuse FIFONAFE, entrega del expediente SICT–PA y fecha/folio documental. Se ejecuta como owner después de un respaldo verificable y conserva sin cambios el contrato restringido de `pa_runtime`.
