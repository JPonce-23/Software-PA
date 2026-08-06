# Validación TLS/E2E - Corte 4

Este checklist se ejecuta sólo en un ambiente con HTTPS real. No reemplaza la
suite automatizada local ni debe usarse para declarar validado un entorno HTTP.

## 1. Requisitos externos

| Requisito | Fuente | Obligatorio |
| --- | --- | --- |
| Origen público HTTPS exacto | Operación/infraestructura | Sí |
| Certificado TLS válido para el origen | Operación/infraestructura | Sí |
| Navegador soportado | Equipo de aceptación | Sí |
| Usuario admin activo de prueba | Base aislada o ambiente de aceptación | Sí |
| Topología de proxy y balanceador | Operación/infraestructura | Sí, si se confía en `X-Forwarded-For` |

No registrar contraseñas, cookies, hashes, tokens ni capturas que expongan
secretos.

## 2. Configuración esperada

| Variable o ajuste | Valor esperado |
| --- | --- |
| `APP_ENV` | `production` en ambiente expuesto. |
| `AUTH_COOKIE_SECURE` | `true`. |
| `CORS_ORIGINS` | Origen HTTPS exacto, sin wildcard. |
| `AUTH_TRUSTED_PROXY_IPS` | Sólo IPs exactas de proxies confiables, cuando aplique. |
| `TEST_ADMIN_EMAIL` | Admin activo de prueba, no productivo. |
| `TEST_ADMIN_PASSWORD` | Contraseña del admin de prueba, no persistida en repositorio. |

Antes de publicar cambios:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

Verificar migraciones en la base objetivo sin aplicar cambios:

```bash
docker compose exec -T db sh -lc \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select version from schema_migrations order by version"'
```

La versión esperada para Corte 4 es:

```text
004
005
006
007
008
009
```

## 3. Pruebas de navegador

| Caso | Resultado esperado |
| --- | --- |
| Login correcto por HTTPS | `POST /api/auth/sesiones` responde 200 y crea sesión. |
| Cookies de producción | Cookie de sesión con `HttpOnly`, `Secure`, `Path=/`, sin `Domain`; cookie CSRF con `Secure`. |
| Restauración de sesión | Recargar la aplicación mantiene identidad desde `GET /api/auth/sesion`. |
| CSRF faltante | Escritura autenticada sin `X-CSRF-Token` falla 403. |
| CSRF inválido | Escritura con token distinto al cookie falla 403. |
| Origin no permitido | Escritura desde origen distinto falla 403. |
| Quinto fallo | Cinco fallos consecutivos bloquean al usuario y registran evento. |
| Desbloqueo admin | Admin desbloquea y el usuario puede volver a iniciar sesión. |
| Logout | Logout revoca sesión y borra cookies. |
| Logout total | Revoca sesiones del usuario. |
| Inactividad | Sesión expirada por inactividad se revoca y registra evento sin actor humano. |
| Límite absoluto | Sesión vencida por límite absoluto se revoca. |
| RBAC/territorio | Un usuario no consulta ni modifica recursos de tramos no asignados. |
| Bearer retirado | Request con `Authorization: Bearer ...` no autentica. |

## 4. Evidencia mínima

Registrar fuera del repositorio:

```text
Fecha:
Ambiente:
Origen HTTPS:
Navegador y versión:
Commit o hash de imagen:
schema_migrations:
Resultado por caso:
Incidencias:
Responsable:
```

Las capturas deben ocultar credenciales, cookies, direcciones internas y
valores sensibles.
