# Guia de sincronizacion local al estado actual

Fecha: 10 de agosto de 2026

Esta guia reemplaza la guia previa creada para
`db_trenes_export_limpia.dump`. Ese dump anterior no debe usarse para
sincronizar equipos: fue generado antes de corregir la migracion 011 y falla
en restauracion estricta por datos huerfanos.

Usar este archivo:

```text
backups/db_trenes_export_estado_actual_20260810.dump
```

El dump fue generado desde la base local actual y validado en una base temporal
con restauracion estricta. Incluye las migraciones `004` a `011`; por tanto,
despues de restaurarlo no se debe aplicar `011_pago_suficiente.sql` otra vez.

## Alcance

Procedimiento para un ambiente local de desarrollo que puede reemplazar sus
datos actuales. Si el equipo receptor tiene datos que necesita conservar, debe
detenerse aqui y hacer una migracion controlada en lugar de restaurar este
dump.

No usar en produccion.

## Requisitos

- Estar en la rama `feature/backend-logica` actualizada.
- Tener Docker Compose disponible como `docker compose`.
- Tener un `.env` local valido. No copiar secretos de otro ambiente.
- Colocar el dump en `backups/db_trenes_export_estado_actual_20260810.dump`.

## 1. Actualizar codigo

Desde la raiz del repositorio:

```bash
git fetch origin
git checkout feature/backend-logica
git pull origin feature/backend-logica
```

## 2. Resguardar o descartar la base local anterior

Si hay datos locales que quieran conservarse, generar un respaldo antes de
seguir:

```bash
mkdir -p backups
docker compose exec -T db sh -lc \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > backups/pre_sincronizacion_local.dump
chmod 600 backups/pre_sincronizacion_local.dump
```

Para un equipo que solo tiene datos locales de prueba y quiere reemplazarlos,
detener servicios:

```bash
docker compose down
```

Si se requiere una base completamente limpia, eliminar los volumenes locales
despues del respaldo. Confirmar primero los nombres reales:

```bash
docker volume ls
```

Ejemplo habitual si el proyecto Compose se llama `software-pa`:

```bash
docker volume rm software-pa_postgres_data software-pa_pgadmin_data
```

Si los nombres son distintos, usar los nombres que muestre `docker volume ls`.
No ejecutar este paso si hay datos que deban conservarse.

## 3. Levantar PostgreSQL

```bash
docker compose up -d --build db
docker compose ps
```

Esperar a que `db` este `healthy`. Verificar conectividad:

```bash
docker compose exec db sh -lc \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## 4. Restaurar el dump validado

Ejecutar desde la raiz del repositorio:

```bash
test -s backups/db_trenes_export_estado_actual_20260810.dump

docker compose exec -T db sh -lc \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
   -1 --clean --if-exists --exit-on-error' \
  < backups/db_trenes_export_estado_actual_20260810.dump
```

La restauracion debe terminar con codigo `0`. No debe mostrar errores de claves
foraneas ni errores `FATAL`.

## 5. Verificar estado de migraciones

```bash
docker compose exec db sh -lc \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
   -c "SELECT version FROM schema_migrations ORDER BY version;"'
```

Resultado esperado:

```text
004
005
006
007
008
009
010
011
```

No ejecutar `backend/db/migrations/011_pago_suficiente.sql` despues de restaurar
este dump. Ya esta aplicada.

## 6. Verificar integridad minima

```bash
docker compose exec db sh -lc \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
   -c "SELECT COUNT(*) AS usuarios_sin_estado
         FROM usuario u
         LEFT JOIN estado_autenticacion_usuario e
           ON e.id_usuario = u.id_usuario
        WHERE e.id_usuario IS NULL;" \
   -c "SELECT COUNT(*) AS alertas_orfanas
         FROM alertas_vistas av
         LEFT JOIN usuario u
           ON u.id_usuario = av.id_usuario
        WHERE u.id_usuario IS NULL;" \
   -c "SELECT COUNT(*) AS trigger_pago
         FROM pg_trigger
        WHERE tgname = '\''trg_2b_validar_suficiencia_pago'\''
          AND NOT tgisinternal
          AND tgenabled = '\''O'\'';"'
```

Resultados esperados:

```text
usuarios_sin_estado = 0
alertas_orfanas = 0
trigger_pago = 1
```

## 7. Levantar el sistema

```bash
docker compose up -d --build
docker compose ps
```

Verificar logs basicos:

```bash
docker compose logs --tail=80 backend
docker compose logs --tail=80 alertas_scheduler
```

## 8. Crear un administrador local propio

No depender de credenciales de otro equipo ni de usuarios incluidos en el dump.
Crear un administrador local:

```bash
docker compose exec backend python scripts/create_admin.py
```

Seguir el prompt interactivo. No registrar contrasenas en documentos, commits,
capturas ni logs.

## 9. Validacion final minima

Backend:

```bash
docker compose exec backend pytest
```

Frontend:

```bash
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
```

Acceso local esperado:

```text
Frontend: http://localhost:5173
Backend health: http://localhost:8000/health
PgAdmin: http://localhost:5050
```

## Evidencia de validacion del dump

En el equipo origen, el dump
`backups/db_trenes_export_estado_actual_20260810.dump` fue validado mediante:

```bash
docker compose exec -T db sh -lc \
  'dropdb -U "$POSTGRES_USER" --if-exists sync_package_validate_20260810;
   createdb -U "$POSTGRES_USER" sync_package_validate_20260810;
   pg_restore -U "$POSTGRES_USER" -d sync_package_validate_20260810 \
     -1 --clean --if-exists --exit-on-error' \
  < backups/db_trenes_export_estado_actual_20260810.dump
```

Resultado validado:

```text
schema_migrations: 004, 005, 006, 007, 008, 009, 010, 011
usuarios_sin_estado: 0
alertas_orfanas: 0
trg_2b_validar_suficiencia_pago habilitado: 1
```
