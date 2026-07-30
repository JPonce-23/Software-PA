# Ejecución de migraciones de base de datos

## Reglas de seguridad

- Ejecuta los comandos desde la raíz del repositorio.
- Crea un respaldo antes de migrar una base con datos.
- No copies directamente el directorio interno de PostgreSQL ni el volumen
  `postgres_data`.
- Usa `ON_ERROR_STOP=on`; así `psql` devuelve error ante la primera sentencia
  fallida.
- No ejecutes `002`, `003` o `004` a ciegas. No todas son idempotentes.
- No uses `docker compose down -v` sobre una base que necesites conservar.

## Identificar el estado

Comprueba los objetos que distinguen cada línea base:

```bash
docker compose exec db sh -lc \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
  SELECT
    to_regclass('\''public.proyecto'\'') AS proyecto,
    to_regclass('\''public.usuario_tramo'\'') AS usuario_tramo,
    to_regclass('\''public.frente'\'') AS frente,
    to_regclass('\''public.schema_migrations'\'') AS control_migraciones;"'
```

Si existe `schema_migrations`, consulta las versiones registradas:

```bash
docker compose exec db sh -lc \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT version, descripcion, aplicada_en FROM schema_migrations ORDER BY version;"'
```

Interpretación:

| Estado | Acción |
| --- | --- |
| Volumen nuevo; `001` acaba de crear `proyecto` y `usuario_tramo`; no existe `frente` | Crear administrador y aplicar únicamente `004` |
| `schema_migrations` contiene `004` | No volver a ejecutar `004` |
| Existe `frente` y no existe `proyecto` | Base heredada anterior a `003`; requiere evaluación y respaldo |
| Existen `proyecto` y `usuario_tramo`, no existe `frente`, pero falta `004` | Crear/verificar usuario activo y aplicar `004` |

`001_init_schema.sql` es una línea base consolidada: ya contiene la
reestructuración territorial de `003`. Por eso `003` no debe aplicarse sobre
una instalación nueva.

## Respaldo obligatorio para una base existente

Crea una carpeta local ignorada por Git y genera un respaldo en formato
personalizado de PostgreSQL:

```bash
mkdir -p backups
docker compose exec -T db sh -lc \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > backups/pre_migracion.dump
```

Verifica que el archivo exista y no esté vacío:

```bash
test -s backups/pre_migracion.dump
```

El respaldo contiene datos sensibles. No debe confirmarse en Git ni
transferirse sin cifrado.

## Adoptar `.env` con un volumen existente

Las variables `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB` se usan para
inicializar un volumen vacío. No cambian los roles ni las contraseñas de una
base que ya existe.

Para adoptar el nuevo Compose sin interrumpir el acceso:

1. Configura temporalmente `.env` con el usuario, contraseña y base que ya
   utiliza el volumen. No confirmes ese archivo.
2. Valida con `docker compose config --quiet` y crea el respaldo indicado
   arriba.
3. Rota la contraseña de forma interactiva para que no quede en el historial
   del shell:

   ```bash
   docker compose exec db sh -lc \
     'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
     -c "\password $POSTGRES_USER"'
   ```

4. Actualiza `DB_PASSWORD` en `.env` con el mismo valor nuevo.
5. Recrea los servicios para cargar las variables actualizadas:

   ```bash
   docker compose up -d --force-recreate db backend alertas_scheduler
   ```

6. Verifica `docker compose ps` y los logs. Recrear contenedores no elimina el
   volumen; no agregues `-v`.

Cambiar también el nombre del rol o de la base requiere una migración SQL
específica y no debe hacerse únicamente editando `.env`.

## Instalación nueva

1. Inicia PostgreSQL y el backend:

   ```bash
   docker compose up -d --build db backend
   docker compose ps
   ```

2. Confirma que `db` esté saludable. `001_init_schema.sql` ya se ejecutó
   automáticamente al inicializar el volumen vacío:

   ```bash
   docker compose exec db sh -lc \
     'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
   ```

3. Crea el administrador técnico requerido por la auditoría de la migración:

   ```bash
   docker compose exec backend python scripts/create_admin.py
   ```

   Antes de usar un entorno compartido, sustituye las credenciales de
   desarrollo definidas actualmente en ese script.

4. Aplica `004` una sola vez:

   ```bash
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/004_adaptaciones_fase2.sql
   ```

5. Verifica el registro:

   ```bash
   docker compose exec db sh -lc \
     'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
     -c "SELECT version, aplicada_en FROM schema_migrations ORDER BY version;"'
   ```

6. Inicia todos los servicios:

   ```bash
   docker compose up -d
   docker compose ps
   ```

7. Opcionalmente carga datos de prueba:

   ```bash
   docker compose exec backend python scripts/seed_mock.py
   ```

## Base heredada

Las migraciones heredadas cumplen funciones distintas:

- `002_apply_audit_fixes.sql` ajusta auditoría y tablas de la línea base
  anterior.
- `003_add_proyecto_drop_frente.sql` migra desde `frente` hacia `proyecto` y
  `usuario_tramo`. Requiere al menos un usuario activo.
- `004_adaptaciones_fase2.sql` requiere que `003` ya esté representada en el
  esquema, crea `schema_migrations` y registra la versión `004`.

Antes de ejecutar `002` o `003`, compara el esquema real con sus
precondiciones. Esas migraciones no registran su versión y contienen cambios
no idempotentes; repetirlas puede fallar. Si la base todavía tiene `frente`,
la secuencia esperada es `002` (solo si faltan sus cambios), `003` y `004`,
siempre con respaldo y validación entre pasos.

Ejecuta cada archivo aprobado con este patrón:

```bash
docker compose exec -T db sh -lc \
  'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < backend/db/migrations/<ARCHIVO_APROBADO>.sql
```

## Restauración

La restauración debe hacerse en una base vacía y controlada. No sobrescribas
una base existente sin confirmar primero el destino.

```bash
docker compose exec -T db sh -lc \
  'pg_restore --exit-on-error --clean --if-exists \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < backups/pre_migracion.dump
```

`--clean` elimina objetos de la base destino antes de restaurarlos. Es
destructivo para esa base; valida el proyecto Compose y el nombre de la base
antes de ejecutarlo.
