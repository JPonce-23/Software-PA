# Auditoría final local - Corte 4: contracción bearer

Fecha: 2026-08-06
Rama: `feature/backend-logica`
Fuente de continuidad: `ESTADO_PROYECTO.md`

## 1. Alcance

Esta auditoría cierra el bloqueo local de la contracción bearer/JWT del Corte 4.
No valida infraestructura HTTPS real ni aceptación manual en navegador porque
el Compose local no incluye terminador TLS público.

## 2. Implementación encontrada

| Área | Estado verificado |
| --- | --- |
| Login legacy | `POST /api/auth/login` retirado del backend local. |
| JWT | Emisión y validación JWT retiradas de `backend/app/auth.py`. |
| Bearer | `Authorization: Bearer` ya no es mecanismo aceptado por `get_current_user`. |
| Schemas | `Token` y `TokenData` retirados. |
| Dependencias | `python-jose` retirado de `backend/requirements.txt`. |
| Tests | La suite usa cookie de sesión y CSRF mediante `admin_session`. |
| Configuración de pruebas | `.env.example` y `docker-compose.yml` exponen `TEST_ADMIN_EMAIL` y `TEST_ADMIN_PASSWORD` vacíos para inyección local. |

## 3. Validaciones ejecutadas

| Validación | Resultado | Evidencia |
| --- | --- | --- |
| Docker Compose | Aprobada | Servicios `db`, `backend`, `frontend`, `alertas_scheduler` y `pgadmin` saludables. |
| Migraciones | Aprobada | `schema_migrations` registra `004`, `005`, `006`, `007`, `008` y `009`. |
| Backend sin `python-jose` | Aprobada | Importación en contenedor confirmó `jose_installed=False`. |
| Suite backend completa | Aprobada | `docker compose exec -T ... backend python -m pytest -v`: `119 passed, 1 warning in 14.46s`. |
| Frontend lint | Aprobada | `npx oxlint src` ejecutado sin errores ni advertencias. |
| Frontend build | Aprobada | `npm run build` ejecutado correctamente. |
| Diff | Aprobada | `git diff --check` sin errores. |

La suite backend se ejecutó con un administrador efímero de auditoría creado en
la base local mediante `scripts/create_admin.py`. La contraseña no fue mostrada
ni guardada. Para repetir la validación se debe crear o seleccionar un admin
activo de una base aislada y exportar `TEST_ADMIN_EMAIL` y
`TEST_ADMIN_PASSWORD` en la sesión que ejecute pytest.

## 4. Bloqueos resueltos

| Bloqueo previo | Resolución |
| --- | --- |
| Faltaban `TEST_ADMIN_EMAIL` y `TEST_ADMIN_PASSWORD`. | Variables documentadas en `.env.example`, expuestas al backend por Compose y validadas con suite completa. |
| No existía reporte final de auditoría bloqueada como archivo. | Este documento registra el cierre local y las validaciones ejecutadas. |

## 5. Bloqueo externo restante

| Bloqueo | Motivo | Evidencia requerida |
| --- | --- | --- |
| TLS/E2E real | Requiere origen HTTPS público, certificado válido, navegador soportado y topología de proxy. No puede demostrarse con el Compose local actual. | Ejecutar `docs/validacion-tls-e2e-corte-4.md` en el ambiente real y anexar evidencias sin secretos. |

## 6. Veredicto local

Contracción bearer/JWT local validada. Corte 4 completo sigue pendiente de la
validación TLS/E2E real documentada en `docs/validacion-tls-e2e-corte-4.md`.
