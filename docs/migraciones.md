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

## Rotación de secretos por ambiente

La rotación debe ejecutarse por ambiente y sin documentar valores reales:

1. Crea respaldo de la base si el ambiente contiene datos que deben
   conservarse.
2. Rota la contraseña del rol PostgreSQL dentro de PostgreSQL con `\password`
   o un procedimiento equivalente interactivo.
3. Actualiza `DB_PASSWORD` en `.env` con el nuevo valor.
4. Genera un nuevo `SECRET_KEY` fuera del repositorio, por ejemplo con
   `openssl rand -hex 32`, y actualiza `.env`.
5. Rota `PGADMIN_DEFAULT_PASSWORD` y revisa credenciales guardadas dentro de
   PgAdmin si aplica.
6. Recrea backend y scheduler para cargar el nuevo `SECRET_KEY`:

   ```bash
   docker compose up -d --force-recreate backend alertas_scheduler
   ```

7. Verifica que un token emitido antes de rotar `SECRET_KEY` ya no sea
   aceptado y que un inicio de sesión nuevo funcione.
8. Registra sólo evidencia operativa: fecha, ambiente, responsable,
   servicios recreados y resultado de validaciones. No registres secretos.

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

3. Crea el administrador técnico requerido por la auditoría de la migración.
   Define y exporta antes las variables no sensibles `ADMIN_EMAIL`,
   `ADMIN_NOMBRE`, `ADMIN_APELLIDO_PATERNO` y, si aplica,
   `ADMIN_APELLIDO_MATERNO`. Pásalas explícitamente al contenedor y captura la
   contraseña por prompt interactivo, sin eco:

   ```bash
   docker compose exec \
     -e ADMIN_EMAIL="$ADMIN_EMAIL" \
     -e ADMIN_NOMBRE="$ADMIN_NOMBRE" \
     -e ADMIN_APELLIDO_PATERNO="$ADMIN_APELLIDO_PATERNO" \
     -e ADMIN_APELLIDO_MATERNO="$ADMIN_APELLIDO_MATERNO" \
     backend python scripts/create_admin.py
   ```

   El script no contiene credenciales predeterminadas y rechazará placeholders.
   Para automatizaciones controladas puede pasarse `ADMIN_PASSWORD` como
   variable temporal del proceso; no la dejes persistente en archivos
   compartidos, historial de shell, logs ni capturas.

4. Aplica `004`–`022` en orden, una sola vez cada una. Detén backend y
   scheduler antes de cada migración y conserva `ON_ERROR_STOP`:

   ```bash
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/004_adaptaciones_fase2.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/005_subcorte_2a_integridad_afectaciones.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/006_subcorte_2b_secuencia_estados.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/007_subcorte_2c_navegacion_documental.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/008_corte4_autenticacion_formal.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/009_corte4_auditoria_sistema_sesion.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/010_corte5_franja_derecho_via.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/011_pago_suficiente.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/012_regularizacion_corte5.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/013_auditoria_integridad_franja.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/014_auditoria_integridad_nucleo.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/015_administracion_territorial.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/016_corregir_trigger_geometria_padre_015.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/017_importacion_territorial_geojson.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/018_nucleo_nombre_unico_importacion.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/019_franja_autoridad_territorial.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/020_importador_geoespacial_seguro.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/021_alcance_identidad_externa.sql
   docker compose exec -T db sh -lc \
     'psql --set ON_ERROR_STOP=on -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
     < backend/db/migrations/022_identidad_externa_territorio_resuelto.sql
   ```

   La 011 exige 010, toma un bloqueo asesor, ejecuta su preflight y se
   confirma en una sola transacción. Reemplaza únicamente
   `vw_afectacion_ciclo_estado`; no elimina ni reduce los contratos de las
   vistas superiores. Si existe 011 en `schema_migrations`, no la repitas.

   La 012 exige 010 y 011, corrige la integridad y auditoría de las franjas,
   completa únicamente las versiones iniciales inequívocas y sustituye el
   búfer espacial heredado en la validación de afectaciones. Su preflight
   aborta ante historiales parciales, versiones duplicadas o geometrías no
   válidas. Si existe 012 en `schema_migrations`, no la repitas.

   La 013 exige 012, aborta si existen fuentes vacías o versiones fuera de
   orden cronológico y refuerza ambas reglas en PostgreSQL sin reescribir el
   historial. Si existe 013 en `schema_migrations`, no la repitas.

   La 014 exige 013 y agrega la validación PostgreSQL de geometrías de núcleo
   presentes sin volver obligatorias las geometrías históricas nulas. Aborta si
   encuentra una geometría vacía, inválida, con SRID distinto de 4326 o que no
   sea `MULTIPOLYGON`. Si existe 014 en `schema_migrations`, no la repitas.

   La 015 exige 014 y protege correo normalizado, geometrías, jerarquía activa,
   asociaciones espaciales, dependencias de bajas lógicas y la existencia de
   al menos un administrador activo. Su preflight aborta, entre otros casos, si
   encuentra una franja activa con tramo inactivo. No corrijas esos datos por
   inferencia: concílialos con el responsable funcional, crea un respaldo nuevo
   y vuelve a ejecutar la auditoría. Si existe 015 en `schema_migrations`, no la
   repitas.

   La 016 exige 015 y corrige el trigger de geometría padre. La 017 exige 016,
   agrega geometría territorial de parcelas y protege los cruces operativos
   activos. La 018 exige 017 y evita núcleos activos duplicados por municipio,
   tipo y nombre normalizado. Su preflight aborta si ya existen duplicados: no
   los elimines ni fusiones por inferencia; concílialos antes de reintentar.

   La 019 exige 018, agrega el índice espacial de franjas y convierte la
   franja activa en autoridad territorial. La franja debe intersectar la línea
   del tramo y cada relación tramo-núcleo activa debe tener superficie positiva
   dentro de ella.

   La 020 exige 019 y crea el staging auditable, perfiles de mapeo, alias
   territoriales y procedencia externa de núcleos. La 021 exige 020 y hace
   explícito si una clave externa de núcleo es global o territorial; evita
   tratar como duplicadas claves que una fuente reutiliza en municipios
   distintos. Ambas migraciones son expansivas y abortan si no encuentran su
   versión precedente.

   La 022 exige 021 y reemplaza únicamente el índice territorial de 021. Usa el
   municipio interno previamente resuelto como contexto estable, incluso cuando
   la fuente no proporciona claves propias de entidad o municipio. Su preflight
   aborta ante identidades territoriales activas duplicadas.

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

7. Opcionalmente carga datos de prueba general:

   ```bash
   docker compose exec backend python scripts/seed_mock.py
   ```

   Para preparar UAT usa una base aislada cuyo nombre contenga `uat` o `test`.
   El fixture rechaza otros ambientes y exige una contraseña distinta para cada
   rol mediante `UAT_ADMIN_PASSWORD`, `UAT_OPERADOR_PASSWORD`,
   `UAT_GEOGRAFO_PASSWORD` y `UAT_VISUALIZADOR_PASSWORD`:

   ```bash
   docker compose exec \
     -e APP_ENV=test \
     -e UAT_ADMIN_PASSWORD="$UAT_ADMIN_PASSWORD" \
     -e UAT_OPERADOR_PASSWORD="$UAT_OPERADOR_PASSWORD" \
     -e UAT_GEOGRAFO_PASSWORD="$UAT_GEOGRAFO_PASSWORD" \
     -e UAT_VISUALIZADOR_PASSWORD="$UAT_VISUALIZADOR_PASSWORD" \
     backend python -m scripts.seed_uat
   ```

   No uses la base UAT para la suite automatizada ni confirmes esas credenciales
   en archivos del repositorio.

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

### Migraciones 008 y 009 y operación de autenticación

`008_corte4_autenticacion_formal.sql` exige 007 y aborta si una fotografía de
bitácora contiene `contrasena_hash`. No sanea ese historial silenciosamente:
si el preflight falla, detén el despliegue y aprueba primero un procedimiento
de saneamiento con evidencia.

Antes de desplegar el backend nuevo:

1. respalda la base con permisos `0600` y verifica el archivo con
   `pg_restore -l`;
2. detén backend y scheduler y confirma cero transacciones activas ajenas;
3. aplica 008 con `ON_ERROR_STOP=1`;
4. aplica inmediatamente 009 con `ON_ERROR_STOP=1`;
5. verifica ambas versiones, las tres tablas de autenticación y sus triggers;
6. configura `APP_ENV=production`, `AUTH_COOKIE_SECURE=true` y
   `CORS_ORIGINS` con el origen HTTPS exacto del ambiente de aceptación
   interno o público;
7. configura `AUTH_TRUSTED_PROXY_IPS` sólo con IPs exactas de proxies bajo
   control; vacío ignora `X-Forwarded-For`;
8. reinicia servicios y valida OpenAPI, login, CSRF, logout y logs.

`009_corte4_auditoria_sistema_sesion.sql`. La 009 exige 008 y corrige la
atribución de expiraciones automáticas: el evento forense queda sin actor y el
trigger sólo permite modificar los campos de revocación de la misma sesión en
la misma transacción.

Valores vigentes: 30 minutos de inactividad, 8 horas absolutas, bloqueo de 15
minutos tras cinco fallos y múltiples sesiones concurrentes. No borres filas
de sesión ni eventos; revoca lógicamente.

Si la única cuenta administradora queda bloqueada, un operador autorizado con
acceso al backend puede ejecutar, sin registrar contraseñas:

```bash
docker compose exec backend python scripts/unlock_admin.py \
  --email "$ADMIN_EMAIL" \
  --reason "Motivo institucional documentado"
```

El script sólo acepta un administrador activo y registra
`desbloqueo_recuperacion` en `evento_acceso`. No reactiva usuarios dados de
baja ni recupera sesiones previas.

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
