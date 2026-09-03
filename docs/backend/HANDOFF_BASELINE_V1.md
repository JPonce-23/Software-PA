# Handoff implementación Baseline V1

## Estado Git
- rama: `feature/backend-logica`;
- HEAD inicial: `d9d88688d6bfa6eace6fd5bf3eec5e487f34d814`;
- HEAD actual: sin commit nuevo;
- working tree: implementación completa sin confirmar; consultar `git status --short`.

## Objetivo
Baseline limpio de base de datos y backend, instalado directamente con `backend/db/migrations/001_baseline_v1.sql`, sin concatenar la historia 001–039 y sin tocar frontend.

## Trabajo completado
- `backend/db/migrations/001_baseline_v1.sql`: 51 tablas funcionales, cuatro vistas, catálogos, integridad, auditoría, índices y ACL canónicos.
- `backend/scripts/run_migrations.sh`: registro SHA-256 e inmutabilidad de archivos aplicados.
- `backend/db/init/`: bootstrap de roles y aplicación del runner separados de contraseñas.
- `backend/app/models.py`, `schemas.py`, `routers/domain.py`, `services/domain.py`, `services/access.py`: retirado BienAfectado y contratos legacy.
- `backend/db/seed.sql` y `backend/scripts/seed_objective_demo.py`: seed canónico e idempotente.
- `backend/db/tests/001_*`: contratos de esquema y ACL/runtime.
- documentación activa y contrato para frontend actualizados.
- migraciones y contratos históricos retirados de la ruta activa; Git conserva el historial.

## Trabajo parcialmente completado
Ningún archivo de implementación quedó parcialmente escrito. La adaptación de `frontend/` está fuera de alcance y documentada en `docs/backend/API_CAMBIOS_BASELINE_V1.md`.

## Trabajo pendiente
1. Revisión humana del diff.
2. Adaptación frontend por su desarrollador responsable.
3. Autorizar en otra instrucción el reset de `db_pruebas_alfredo`.
4. Crear la futura migración `002` sólo cuando exista un cambio nuevo de esquema.

## Baseline SQL
- existe: sí;
- secciones completas: PostGIS, parámetros seguros, schema_migrations, tablas, catálogos, constraints, funciones, triggers, índices, vistas y ACL;
- secciones faltantes: ninguna;
- tablas incluidas: 51 funcionales;
- legacy eliminado: `bien_afectado` y todos los campos acordados;
- constraints/triggers/vistas pendientes: ninguno.

## Backend
- `models.py`: 51 tablas mapeadas, cero diferencias de columnas con PostgreSQL temporal.
- `schemas.py`: entradas canónicas con campos desconocidos prohibidos.
- services: dominio y acceso alineados; `create_affected_asset` retirado.
- routers: endpoints `/bienes` retirados.
- `access.py`: target `bien_afectado` retirado.
- `reporting.py`: consume vistas canónicas; sin cambio requerido.
- `main.py`: `/health` informa schema 1; sin cambio requerido.
- seeds/scripts DB: runner, bootstrap, fixture y seed validados.

## Legacy
- `bien_afectado`: eliminado.
- campos legacy de Asamblea: eliminados.
- campos RAN de Convenio: eliminados.
- campos legacy ORV: eliminados; `orv.id_estado_registral` conservado.
- campos FIFONAFE: ocho campos planos eliminados.
- campos legacy ProyectoNucleo: eliminados.
- endpoints `/bienes`: eliminados.
- BienAfectado ORM/schemas: eliminados.
- triggers legacy: eliminados.

## Tests
- tests ejecutados: contrato SQL, ACL/runtime, pytest backend, mappers/OpenAPI, comparación ORM–BD, checksum y `/health`.
- tests que pasan: 98/98 pytest; contratos SQL y ACL aprobados.
- tests que fallan: ninguno.
- error literal o causa resumida: no aplica; una advertencia de deprecación Starlette/httpx no afecta el resultado.
- tests todavía no ejecutados: frontend/E2E, fuera de alcance.

## Base temporal
- fue creada: sí;
- nombre: `software_pa_baseline_final_test`;
- baseline fue aplicado: sí, desde el único archivo activo;
- resultado: 001 con SHA-256, 51 tablas funcionales, cuatro vistas SOFTWARE-PA y 99 triggers de usuario;
- NO tocar `db_pruebas_alfredo`: continúa intacta.

## Comandos necesarios para continuar
```bash
docker compose exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d software_pa_baseline_final_test -X -v ON_ERROR_STOP=1' < backend/db/tests/001_baseline_v1_contract.sql
DB_NAME=software_pa_baseline_final_test backend/db/tests/001_runtime_privileges.sh
docker compose run --rm --no-deps -e APP_ENV=test -e DB_NAME=software_pa_baseline_final_test -e TEST_ALLOW_DATABASE=software_pa_baseline_final_test -e TEST_ADMIN_EMAIL -e TEST_ADMIN_PASSWORD backend pytest -q
docker compose run --rm --no-deps -e APP_ENV=test -e DB_NAME=software_pa_baseline_final_test backend python -c "from fastapi.testclient import TestClient; from app.main import app; r=TestClient(app).get('/health'); print(r.status_code, r.json())"
```

## Decisiones que NO deben cambiarse
- no modificar `frontend/`;
- mantener `tramite_ran.id_proyecto_nucleo`;
- mantener `tramite_ran.id_nucleo`;
- mantener `orv.id_estado_registral`;
- eliminar `bien_afectado`;
- usar fuentes canónicas;
- no preservar datos de desarrollo;
- no destruir todavía `db_pruebas_alfredo`;
- roles/runtime separados del baseline SQL.

## Próximo paso exacto
Revisar `git diff` y solicitar autorización explícita antes del reset de `db_pruebas_alfredo`; no repetir la implementación.
