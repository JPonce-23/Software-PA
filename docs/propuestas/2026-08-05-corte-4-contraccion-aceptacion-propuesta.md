# Propuesta técnica — Corte 4: contracción bearer y aceptación operativa

Fecha: 2026-08-05; decisiones F-01/F-03 incorporadas el 2026-08-10
Estado: propuesta corregida y viable; prerrequisitos locales validados,
aceptación TLS/E2E pendiente hasta disponer del staging HTTPS

## 1. Trabajo vigente identificado

`ESTADO_PROYECTO.md` (sección 10, líneas 961–975) establece que el próximo
paso operativo es completar la **contracción y aceptación operativa del
Corte 4 de autenticación formal**. El incremento principal (migraciones 008
y 009, backend dual cookie+bearer, frontend cookie, pruebas Corte 4) ya fue
implementado y validado técnicamente.

Los tres pendientes explícitos antes de declarar Corte 4 terminado son:

1. **Inventariar consumidores del bearer heredado** y aprobar la fecha de
   contracción antes de dejar de emitir/aceptar JWT.
2. **Validar cookie `Secure`**, host/origen y proxy confiable detrás del TLS
   real.
3. **Ejecutar aceptación funcional E2E** de login, quinto fallo, desbloqueo,
   expiración, logout y RBAC/territorio en navegadores soportados.

No se reabren los Subcortes 2A–2C, no se alteran reglas de liberación, no se
incorpora el Corte 5 y no se modifica el flujo de dominio.

## 2. Estado actual verificado

Las subsecciones 2.1 y 2.2 conservan la fotografía de diseño previa a la
contracción. La contracción bearer/JWT fue implementada y validada el 6 de
agosto de 2026; el estado operativo posterior se registra en 2.4 y prevalece
para la aceptación pendiente.

### 2.1 Auditoría del sistema de autenticación implementado

| Capa | Estado |
|------|--------|
| Migración 008 | Aplicada. Crea `sesion_usuario`, `evento_acceso`, `estado_autenticacion_usuario` con FK, CHECK, triggers de inmutabilidad, protección contra DELETE y redacción de secretos en bitácora. |
| Migración 009 | Aplicada. Auditoría veraz de expiraciones automáticas sin atribuir actor humano ficticio; limita la excepción a campos de revocación correlacionados con evento `sesion_expirada`. |
| `schema_migrations` | Registra 004, 005, 006, 007, 008, 009. |
| ORM (`models.py`) | `SesionUsuario`, `EventoAcceso`, `EstadoAutenticacionUsuario` correctamente mapeados. |
| Schemas (`schemas.py`) | `AuthSessionResponse`, `AuthUserResponse`, `AuthActionRequest`, `AuthOperationResponse` para flujo cookie. El schema legacy `Token` (`access_token`, `token_type`, `user`) sigue presente. |
| Servicio (`services/authentication.py`) | 411 líneas. Login transaccional con bloqueo FOR UPDATE, dummy hash, 5 fallos, CSPRNG para tokens, SHA-256 en DB, expiración por inactividad (30 min) y absoluta (8 h), revocación, desbloqueo, eventos. Completamente cookie-based. |
| Router (`routers/authentication.py`) | 178 líneas. Endpoints `POST /auth/sesiones`, `GET /auth/sesion`, `POST /auth/logout`, `POST /auth/logout-todas`, `POST /usuarios/{id}/desbloquear`, `POST /usuarios/{id}/revocar-sesiones`. Gestión de cookies `__Host-pa_session` / `pa_session_dev` y CSRF `__Host-pa_csrf` / `pa_csrf_dev`. |
| `auth.py` | 127 líneas. Modo dual: `get_current_user()` acepta cookie (preferente) o bearer JWT, rechaza si ambos presentes. `get_session_context()` sólo cookie. `create_access_token()` y `_get_bearer_user()` son código legacy activo. |
| Middleware CSRF | En `main.py` (líneas 102–137). Valida Origin, cookie CSRF, header `X-CSRF-Token` y hash en DB para escrituras con sesión cookie. Salta requests bearer (sin cookie de sesión). |
| CORS | Orígenes exactos desde `AUTH_SETTINGS.allowed_origins`, `allow_credentials=True`, headers explícitos `["Authorization", "Content-Type", "X-CSRF-Token"]`. |
| Config (`config.py`) | `AuthSettings` frozen. Producción exige `cookie_secure=true`, rechaza wildcards en CORS. Cookie `__Host-` prefix en producción. Proxy IPs validados. |
| Frontend | **100% migrado a cookies.** Cero `localStorage`, cero bearer, cero `Authorization` header. `AuthContext.jsx` restaura sesión desde servidor. `axios.js` usa `withCredentials: true` y CSRF automático. |
| Pruebas Corte 4 (`test_auth_corte4.py`) | 6 tests (342 líneas): ciclo cookie+CSRF+logout, quinto fallo concurrente, bloqueo/desbloqueo admin, constraints DB, expiración (inactividad/absoluta), privacidad de identidad inexistente. |
| Pruebas legacy (`test_auth.py`) | 12 tests de login bearer, protección de rutas y hardening Corte 3. Usa `admin_headers` fixture con bearer. |

### 2.2 Inventario completo de consumidores bearer

Tras búsqueda exhaustiva en todo el repositorio:

#### Frontend: CERO consumidores

El frontend no contiene ninguna referencia a `localStorage`, `sessionStorage`,
`Bearer`, `Authorization` ni `access_token`. La migración a cookies está
completa.

#### Backend: el endpoint legacy + infraestructura JWT

| Archivo | Líneas | Qué hace |
|---------|--------|----------|
| `main.py` | 1382–1407 | `POST /api/auth/login` — endpoint legacy que emite JWT. No registra eventos, no verifica bloqueo, no crea sesión, no incrementa contador de fallos. Diferencia respuesta entre usuario inactivo (400) y credenciales inválidas (401), facilitando enumeración. |
| `auth.py` | 3, 7, 41–44, 52–60, 62–79 | `from jose import jwt`, `OAuth2PasswordBearer`, `create_access_token()`, `_get_bearer_user()` — infraestructura JWT completa. |
| `auth.py` | 95–117 | `get_current_user()` — modo dual que acepta bearer como fallback. |
| `schemas.py` | 14–17 | `Token` — schema de respuesta bearer (`access_token`, `token_type`, `user`). |

#### Suite de tests: el único consumidor funcional restante

| Archivo | Uso bearer | Detalle |
|---------|-----------|---------|
| `conftest.py` L57–72 | `admin_headers` fixture | Login vía `POST /api/auth/login`, retorna `{"Authorization": f"Bearer {token}"}`. **Fixture de sesión usado por ~50+ tests en todo el proyecto.** |
| `test_auth.py` L18–68 | `TestLogin` (4 tests) | Prueba directa del endpoint legacy `/api/auth/login`. |
| `test_auth.py` L86–96 | `TestProteccionRutas` (2 tests) | Usa `admin_headers` + bearer falso. |
| `test_auth.py` L109–116 | `TestRutasPublicas` (2 tests) | Usa `admin_headers`. |
| `test_auth_corte4.py` L22–40 | `auth_user` fixture | Usa `admin_headers` (bearer) para crear/limpiar usuario de test. |
| `test_auth_corte4.py` L105 | `test_quinto_fallo` | Usa `admin_headers` para desbloqueo admin. |
| `test_crud_ciclo_vida.py` | ~30 tests | Todos usan `admin_headers`. |
| `test_fase2_adaptaciones.py` | ~20 tests | Todos usan `admin_headers`. |
| `test_reglas_negocio.py` | ~15 tests | Todos usan `admin_headers`. |
| `test_reportes_y_endpoints_especiales.py` L80–128 | 3 tests | Login propio vía `/api/auth/login`. |
| `test_subcorte_2a.py` | Tests 2A | Usa `admin_headers`. |
| `test_subcorte_2b.py` L516–521 | Operador headers | Login bearer propio para test de autorización. |
| `test_subcorte_2c.py` L366–370 | Operador headers | Login bearer propio para test de autorización. |
| `test_zzz_limpieza.py` | Cleanup | Usa `admin_headers`. |

**Conclusión del inventario:** no existen consumidores externos (mobile, otro
frontend, API pública). El único consumidor bearer es la suite de pruebas.

### 2.3 Infraestructura TLS y proxy

- Docker Compose no define terminador TLS; asume proxy externo
  (nginx/caddy/cloud LB).
- `docker-compose.prod.yml` fuerza `AUTH_COOKIE_SECURE: "true"` y exige
  `CORS_ORIGINS` explícito.
- No se usa `TrustedHostMiddleware`.
- `AUTH_TRUSTED_PROXY_IPS` controla `X-Forwarded-For` confiable.
- Cookie `__Host-` prefix (producción) exige HTTPS, `Secure`, `Path=/`, sin
  `Domain`.
- No hay documentación de la topología TLS del ambiente real.

### 2.4 Precondiciones operativas verificadas el 10 de agosto de 2026

- La base activa registra 004, 005, 006, 007, 008, 009, 010 y 011.
- F-01A restauró para el usuario 1 la fila exacta encontrada en un respaldo:
  contador cero, sin bloqueo y último acceso conservado. La misma transacción
  registró `desbloqueo_recuperacion` sin actor.
- Todos los usuarios locales tienen exactamente un estado de autenticación.
- El Compose local es HTTP y no constituye evidencia de aceptación TLS.
- Se aprobó un staging HTTPS dedicado sin proxy. El origen HTTPS exacto sigue
  pendiente porque el ambiente todavía no existe; es un dato de despliegue,
  no una decisión funcional abierta.
- La migración 011 fue endurecida y validada sobre una restauración completa
  antes de aplicarse a la base activa.

## 3. Reglas funcionales confirmadas

1. El frontend ya no es consumidor bearer; la contracción no lo afecta.
2. Los tests son el único consumidor bearer; migrarlos es prerequisito y
   suficiente para la contracción.
3. El endpoint legacy `POST /api/auth/login` es una superficie de riesgo: no
   registra eventos, no verifica bloqueo, diferencia inactivo/inválido y
   emite JWT sin sesión revocable.
4. Retirar bearer no cambia reglas de dominio, autorización territorial ni
   auditoría de datos operativos.
5. Cookie `Secure` con prefix `__Host-` falla cerrado sin HTTPS; no degradar
   automáticamente en producción.
6. La suite debe seguir cubriendo toda la matriz de autenticación, RBAC y
   territorio después de la contracción.
7. No se eliminan las migraciones 008/009 ni las tablas de sesión/eventos.
8. `set_audit_context` se sigue exigiendo para escrituras de dominio;
   la autenticación cookie lo proporciona correctamente.
9. Una cuenta activa debe tener exactamente un estado de autenticación; la
   ausencia se trata como inconsistencia de datos y el login debe fallar
   cerrado.
10. La reparación F-01A sólo puede ejecutarse después de un respaldo y una
    investigación que descarte un estado recuperable. Debe ser atómica,
    auditable y no modifica la migración 008. Reutiliza el evento existente
    `desbloqueo` con motivo `desbloqueo_recuperacion`, sin crear un tipo nuevo.
11. La aceptación se ejecutará exclusivamente en staging HTTPS dedicado, con
    certificado válido, cuentas no productivas y al menos dos territorios
    controlados: uno permitido y otro denegado.
12. El staging aprobado no usa proxy. `AUTH_TRUSTED_PROXY_IPS` debe permanecer
    vacío; cualquier cambio de topología requiere reevaluación.
13. La matriz mínima aprobada es Chromium y Firefox. Safari/WebKit queda fuera
    mientras no se declare oficialmente soportado.
14. “Contracción validada” y “Corte 4 aceptado” son estados distintos. El
    segundo exige completar todos los gates TLS/E2E.

## 4. Hallazgos y contradicciones

| ID | Hallazgo | Impacto | Resolución propuesta |
|----|----------|---------|---------------------|
| C4C-01 | Endpoint legacy `/api/auth/login` no registra eventos ni verifica bloqueo. | Superficie de ataque bypass: se puede intentar brute force sin tocar `estado_autenticacion_usuario`. | Retirar endpoint en la contracción. |
| C4C-02 | Endpoint legacy diferencia inactivo (400) de inválido (401). | Enumeración de cuentas. | Retirar endpoint. |
| C4C-03 | JWT emitido por legacy no tiene sesión revocable. | Un JWT comprometido es válido 30 minutos sin remedio (salvo rotar `SECRET_KEY`). | Retirar emisión de JWT. |
| C4C-04 | `admin_headers` fixture en `conftest.py` usa login legacy. | Bloquea la contracción hasta que se migre. | Migrar fixture a cookie. |
| C4C-05 | `test_auth.py::TestLogin` prueba el endpoint legacy como feature. | Las pruebas deben validar el flujo actual, no el deprecated. | Reescribir tests para probar flujo cookie o marcar como test de contracción que valide que el endpoint ya no existe. |
| C4C-06 | `test_subcorte_2b.py` y `test_subcorte_2c.py` crean sus propios bearer headers para operador. | Requieren helper de sesión cookie para operador. | Crear fixture reutilizable con sesión cookie por rol. |
| C4C-07 | `test_reportes_y_endpoints_especiales.py` hace login bearer propio. | Similar a C4C-06. | Migrar a fixture cookie. |
| C4C-08 | CORS `allow_headers` incluye `"Authorization"`. | Necesario durante expansión; retirar en contracción. | Quitar `"Authorization"` de allow_headers al contraer. |
| C4C-09 | `auth.py` conservará `SECRET_KEY` para firma; ya no necesaria para JWT. | `SECRET_KEY` sigue siendo útil si se usa para firmar otros tokens futuros, pero la validación agresiva puede relajarse. | Conservar `SECRET_KEY` y validación; usada operativamente y podría servir para otros propósitos. |
| C4C-10 | No hay documentación de la topología TLS real. | Sin ella, `cookie Secure` y `__Host-` prefix no pueden validarse operativamente. | Exigir documento de topología o checklist de validación antes de declarar Corte 4 terminado. |
| C4C-11 | `get_current_user()` tiene branch para bearer que queda muerto post-contracción. | Código muerto. | Eliminar branch bearer. |
| C4C-12 | `WWW-Authenticate: Bearer` en headers de error de `services/authentication.py` L99. | Vestigio bearer en servicio cookie. | Retirar header de autenticación bearer en errores; las respuestas no deben anunciar un mecanismo retirado. |
| C4C-13 | El middleware CSRF salta requests sin cookie de sesión (`if not session_token: return await call_next(request)`). | Post-contracción, una request sin cookie es simplemente no autenticada; `get_current_user` la rechazará 401. No hay bypass. | Sin cambio; comportamiento correcto. |
| C4C-14 | El único usuario activo carecía de `estado_autenticacion_usuario`. | Login imposible; reparar a cero podía borrar un bloqueo desconocido. | Resuelto: se recuperó la fila exacta de un respaldo y se registró el evento en la misma transacción. |
| C4C-15 | La base activa no registraba 011, aunque continuidad afirmaba que estaba aplicada. | El esquema no representaba completamente el HEAD documentado. | Resuelto localmente: 011 transaccional, restauración completa, aplicación activa y guarda de repetición verificadas. |
| C4C-16 | El staging fue aprobado, pero su origen HTTPS exacto no está definido. | TLS/E2E no puede ejecutarse todavía. | Registrar el origen cuando se aprovisione staging; no bloquea la viabilidad del diseño ni el desarrollo local. |

## 5. Diseño propuesto

### 5.1 Estrategia de contracción

La contracción es el paso final de la expansión documentada en la propuesta
anterior. El frontend ya migró; sólo resta:

```text
FASE 1: Migrar la suite de tests a cookie-based auth
FASE 2: Retirar endpoint legacy y código JWT del backend
FASE 3: Validar TLS/cookie Secure y aceptación E2E
FASE 4: Cerrar documentación
```

### 5.2 Flujo de autenticación post-contracción

```text
Único mecanismo:
  POST /api/auth/sesiones → cookie HttpOnly + CSRF cookie
  GET  /api/auth/sesion   → usuario actual
  POST /api/auth/logout   → revoca sesión + borra cookies

No existe:
  POST /api/auth/login  (eliminado)
  Authorization: Bearer (rechazado)
  OAuth2PasswordBearer  (eliminado)
  JWT encode/decode     (eliminado)
```

### 5.3 Migración de la suite de tests

#### Nuevo fixture `admin_session` (reemplaza `admin_headers`)

```python
@pytest.fixture(scope="session")
def admin_session(client, admin_credentials):
    """Crea sesión cookie y devuelve headers CSRF para tests."""
    email, password = admin_credentials
    origin = "http://testserver"
    login = client.post(
        "/api/auth/sesiones",
        data={"username": email, "password": password},
        headers={
            "Origin": origin,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert login.status_code == 200, f"Login falló: {login.text}"
    # Las cookies se almacenan automáticamente en el TestClient
    # Extraer CSRF del cookie para headers de escritura
    csrf = login.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    return {"Origin": origin, "X-CSRF-Token": csrf}
```

**Nota técnica:** Starlette `TestClient` persiste cookies entre requests
cuando se usa en la misma instancia, por lo que la sesión se mantiene
automáticamente para GET y para POST (con CSRF header).

#### Impacto: renombrar `admin_headers` → `admin_session`

Todos los tests que usan `admin_headers` con `headers=admin_headers` seguirán
funcionando si el fixture retorna los headers CSRF correctos. Para GET, no
necesitan el header CSRF (el middleware lo salta); para POST/PUT/DELETE, el
header CSRF se enviará automáticamente.

La clave es que `TestClient` con `cookies` persiste la sesión internamente
después del login inicial. Los headers CSRF se pasan por cada request de
escritura.

#### Fixture de operador para 2B/2C

```python
@pytest.fixture
def operator_session(client, admin_session, ...):
    """Crea usuario operador con sesión cookie propia."""
    # Crear usuario operador vía API con admin_session
    # Login del operador vía /api/auth/sesiones
    # Retornar headers CSRF del operador
```

### 5.4 Código a retirar

| Archivo | Líneas | Qué se retira |
|---------|--------|---------------|
| `main.py` | 1382–1407 | `login_for_access_token()` — endpoint legacy completo. |
| `auth.py` | 3 | `from jose import JWTError, jwt` |
| `auth.py` | 7 | `from fastapi.security import OAuth2PasswordBearer` |
| `auth.py` | 41–44 | `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `oauth2_scheme` |
| `auth.py` | 52–60 | `create_access_token()` |
| `auth.py` | 62–79 | `_get_bearer_user()` |
| `auth.py` | 95–117 | Branch bearer en `get_current_user()` — simplificar a sólo cookie. |
| `schemas.py` | 14–20 | `Token` y `TokenData` schemas. |
| `main.py` | 98 | `"Authorization"` de `allow_headers` CORS. |
| `services/authentication.py` | L99 | `headers={"WWW-Authenticate": "Bearer"}` en `_credentials_error`. |

**No se retiran:**
- `SECRET_KEY` y su validación — sigue siendo útil para la aplicación.
- `verify_password()` y `get_password_hash()` — usados por el servicio de
  sesión y gestión de usuarios.
- Dependencia `bcrypt` — sigue en uso.

### 5.5 Dependencia `python-jose` se puede eliminar

`python-jose` ya no será necesaria. Eliminar de `requirements.txt`:

```diff
-python-jose[cryptography]
```

Verificar que ningún otro módulo la importe.

### 5.6 Recuperación y aceptación operativa corregidas

Estados autorizados:

```text
contracción validada
  -> preflight de esquema y usuario-estado
  -> respaldo verificado
  -> investigación de estado recuperable
  -> recuperación F-01A atómica y auditable, sólo si no es recuperable
  -> staging HTTPS configurado con origen exacto
  -> fixtures no productivos de territorio permitido/denegado
  -> E2E Chromium + Firefox
  -> Corte 4 aceptado
```

Cada transición falla cerrado. Un preflight fallido, un respaldo inválido, un
estado recuperable, la ausencia del origen exacto o la discrepancia de 011
impiden avanzar y no se corrigen silenciosamente.

## 6. Cambios por capa

### Backend — `conftest.py`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| `admin_headers` usa login bearer. | Crear `admin_session` con login cookie `POST /api/auth/sesiones`. Renombrar fixture. El fixture retorna headers CSRF; las cookies de sesión se persisten internamente por `TestClient`. | Prerequisito para retirar bearer. | Endpoint `/api/auth/sesiones` existente. | Tests que pasen `headers=admin_headers` deben pasar con `admin_session`. Diferencia: GET requests no necesitan CSRF; para POST/PUT/DELETE el header CSRF se envía. | Toda la suite pasa sin regresiones. |

### Backend — `test_auth.py`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| `TestLogin` prueba endpoint legacy que se va a retirar. | Reescribir: (a) tests de login exitoso/fallido apuntan a `/api/auth/sesiones` y validan cookie/CSRF en vez de `access_token`; (b) agregar test que verifica que `/api/auth/login` retorna 404/405 post-contracción. | Las pruebas deben validar el flujo actual. | Contracción del endpoint. | Cobertura podría bajar temporalmente si no se reescribe bien. | Suite completa pasa. |
| `test_token_invalido` prueba bearer falso. | Reescribir: verificar que cookie inventada retorna 401. | Flujo actual. | Simplificación de `get_current_user`. | Ninguno. | 401 sin detalle interno. |

### Backend — `test_subcorte_2b.py` y `test_subcorte_2c.py`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| Crean bearer headers propios para operador. | Usar `operator_session` fixture con login cookie. | Consistencia y prerequisito. | Fixture nuevo. | Autorización territorial debe seguir validándose correctamente. | Tests 2B/2C pasan con cookie. |

### Backend — `test_reportes_y_endpoints_especiales.py`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| Login bearer propio dentro de tests. | Refactorizar a fixture cookie o helper compartido. | Consistencia. | Fixture nuevo. | Ninguno adicional. | Tests pasan. |

### Backend — `auth.py`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| Código JWT y bearer activo. | Eliminar imports de `jose`, `OAuth2PasswordBearer`, `create_access_token`, `_get_bearer_user`. Simplificar `get_current_user` a sólo cookie. | Superficie de ataque reducida. | Tests migrados. | Regresión si algún consumidor no se identificó. | Inventario completo realizado; suite completa. |
| `get_current_user` tiene lógica dual compleja. | Simplificar a: leer cookie → autenticar → retornar o 401. | Código más claro y seguro. | Retiro de bearer. | Ninguno. | Suite. |

### Backend — `main.py`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| Endpoint legacy `POST /api/auth/login`. | Eliminar función `login_for_access_token` y su decorador. | Riesgo de seguridad activo: bypass de bloqueo/eventos. | Tests migrados. | Consumidor no descubierto quedaría roto. | Inventario completo. |
| `"Authorization"` en `allow_headers` CORS. | Eliminar. | Post-contracción no se usa. | Retiro de bearer. | Ninguno; Origin y CSRF sí se conservan. | Suite y E2E. |

### Backend — `schemas.py`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| `Token` y `TokenData` son dead code post-contracción. | Eliminar ambos schemas. | Limpieza; no crear contratos fantasma. | Retiro de endpoint login. | Ninguno. | Suite y OpenAPI inspection. |

### Backend — `services/authentication.py`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| `WWW-Authenticate: Bearer` en `_credentials_error`. | Retirar header. | No anunciar mecanismo eliminado. | Contracción. | Ninguno funcional. | Suite. |

### Backend — `requirements.txt`

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| `python-jose[cryptography]` ya no necesario. | Eliminar del requirements. | Dependencia muerta reduce superficie. | Retiro de JWT code. | Verificar que no haya otro import. | `pip install`, suite. |

### Documentación

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| `README.md` y `docs/migraciones.md` mencionan login bearer. | Actualizar para reflejar flujo cookie exclusivo. | Documentación precisa. | Contracción validada. | Docs anticipan código. | Revisión post-implementación. |
| No hay checklist TLS operativo. | Crear checklist de validación TLS en `docs/`. | Cierre operativo Corte 4. | Topología real. | Sin topología no se puede completar. | Validación in situ. |

### Base de datos y recuperación F-01A

| Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
|----------|----------|---------------|--------------|--------|------------|
| Usuario activo sin estado auth. | Se ejecutó preflight, respaldo e investigación; después se restauró el estado recuperable y el evento en una sola transacción. | Restablecer la invariante sin reparación silenciosa. | F-01A y respaldo restaurable. | Restaurar una fila que no correspondiera. | Mismo usuario verificado; exactamente un estado; evento correlacionado; login y bloqueo funcionan. |
| Esquema activo sin 011. | Se endureció y aplicó 011 después de una restauración completa. | Evitar validar una combinación código/esquema divergente. | Respaldo, preflight y migración 011 corregida. | DDL parcial o reducción de vistas. | `schema_migrations`, catálogo, pruebas financieras, restauración y repetición verificadas. |

### Frontend y staging

No se propone cambio funcional de frontend. La aceptación usará el frontend
existente en staging HTTPS y comprobará cookies, restauración de sesión,
errores genéricos y aislamiento territorial en Chromium y Firefox.

## 7. Migración y compatibilidad

### 7.1 Sin cambio de esquema para F-01A

F-01A no cambia tablas, columnas, constraints ni triggers y no modifica 008.
La reparación de datos debe materializarse como operación controlada,
idempotente, transaccional y auditable, separada de las migraciones de esquema.
No se ejecutará hasta validar respaldo e investigación.

La evidencia se registra en `evento_acceso` con `tipo_evento = 'desbloqueo'`,
`motivo_codigo = 'desbloqueo_recuperacion'`, actor nulo conforme al mecanismo
de recuperación existente y detalle saneado que no contenga secretos. El
evento y el nuevo estado deben compartir la misma transacción.

La contradicción de 011 es otro flujo: antes de aceptar el HEAD debe existir
una migración 011 segura, ordenada y verificada. No se autoriza aplicar el
archivo actual como parte de F-01A.

### 7.2 Compatibilidad con datos existentes

- Las sesiones existentes (si las hay) no se alteran.
- Los eventos de acceso existentes no se alteran.
- Los estados de autenticación existentes no se alteran.
- La base activa tiene exactamente un estado por usuario después de F-01A.
- F-01A restauró únicamente el estado recuperable y agregó la evidencia de
  recuperación; no creó sesiones ni cambió contraseña, rol, actividad o
  territorio.

### 7.3 Despliegue de la contracción

```text
1. Desplegar backend con endpoint legacy eliminado
   + frontend existente (ya usa cookie)
   = Inmediatamente funcional; JWT pendientes expiran en ≤30 min

2. No hay ventana de incompatibilidad frontend/backend porque el
   frontend ya fue migrado en el incremento principal.

3. Si un JWT válido intenta autenticarse post-contracción:
   - get_current_user ya no lee Authorization header
   - Request es tratado como no autenticado → 401
   - Impacto: ninguno porque el frontend no envía bearer

4. Rollback: reintroducir el endpoint y código JWT si se descubre
   un consumidor no inventariado.
```

## 8. Seguridad, autorización e integridad

### 8.1 Mejoras de seguridad por la contracción

1. **Elimina bypass de bloqueo**: el endpoint legacy no verifica
   `estado_autenticacion_usuario`, permitiendo brute force sin
   incrementar contadores ni registrar eventos.
2. **Elimina enumeración**: el endpoint legacy devuelve 400 para usuario
   inactivo vs. 401 para credenciales inválidas.
3. **Elimina JWT no revocable**: post-contracción, toda sesión es revocable
   inmediatamente.
4. **Reduce superficie**: elimina `python-jose`, código de firma/verificación
   JWT y `OAuth2PasswordBearer`.

### 8.2 Autorización territorial sin cambios

- `RoleChecker` sigue dependiendo de `get_current_user` (ahora sólo cookie).
- `services/access.py` y `usuario_tramo` no cambian.
- Los roles `admin`, `operador`, `geografo`, `visualizador` no cambian.
- El rol se consulta de `usuario` en cada request, no de la cookie ni del JWT.
- Staging tendrá identidades no productivas y dos territorios controlados. La
  identidad restringida podrá acceder al asignado y recibirá 403 o 404, según
  el contrato vigente, para el territorio denegado.

### 8.3 Auditoría sin cambios

- `set_audit_context` sigue exigiéndose para escrituras de dominio.
- `evento_acceso` sigue siendo append-only e inmutable.
- La redacción de secretos en bitácora sigue activa.
- La excepción es la recuperación F-01A: debe agregar evidencia explícita del
  evento de recuperación en la misma transacción que inserta el estado.

### 8.4 Validación TLS

Para declarar Corte 4 terminado se requiere verificar en el staging HTTPS
dedicado. El staging no usa proxy y el origen exacto aún está pendiente:

| Verificación | Criterio |
|--------------|----------|
| Cookie `Secure` | Navegador rechaza enviarla por HTTP. |
| Cookie `__Host-` prefix | Navegador rechaza si no es HTTPS, tiene `Domain`, o `Path` ≠ `/`. |
| `Origin` exacto | CORS y middleware CSRF rechazan origen distinto del público. |
| `X-Forwarded-For` | No confiar en cabeceras reenviadas; lista de proxies vacía. |
| TLS termination | Certificado válido, HSTS recomendado. |
| Navegadores | Toda la matriz pasa en Chromium y Firefox. |

Si no existe ambiente TLS disponible, la verificación se documenta como
pendiente operativo sin bloquear la contracción de código.

## 9. Plan incremental de implementación

### Paso 1: Migrar fixture `admin_headers` a cookie

- Crear `admin_session` fixture que haga login vía `/api/auth/sesiones`.
- Adaptar `TestClient` para que las cookies de sesión se persistan.
- Mantener `admin_headers` como alias temporal que llame al nuevo.
- Verificar que toda la suite pasa con el fixture nuevo.
- **Criterio de avance:** 117+ tests pasan con autenticación cookie.

### Paso 2: Migrar tests con bearer propio

- `test_subcorte_2b.py`: refactorizar bearer de operador a cookie.
- `test_subcorte_2c.py`: ídem.
- `test_reportes_y_endpoints_especiales.py`: ídem.
- Crear helper/fixture reutilizable para sesión cookie por rol.
- **Criterio de avance:** todos los tests pasan sin ningún uso de
  `/api/auth/login` ni `Authorization: Bearer`.

### Paso 3: Reescribir `test_auth.py`

- `TestLogin`: reescribir para probar `/api/auth/sesiones` (cookie).
- `TestProteccionRutas`: cambiar de bearer a cookie.
- Agregar test de que `/api/auth/login` retorna 404 o 405
  (verificación de contracción).
- **Criterio de avance:** suite pasa; cobertura de autenticación mantenida.

### Paso 4: Contracción de código backend

- Eliminar endpoint `login_for_access_token` de `main.py`.
- Eliminar código JWT de `auth.py`.
- Simplificar `get_current_user()` a sólo cookie.
- Eliminar `Token` y `TokenData` de `schemas.py`.
- Retirar `"Authorization"` de `allow_headers` CORS.
- Retirar `WWW-Authenticate: Bearer` de servicios.
- Eliminar `python-jose[cryptography]` de `requirements.txt`.
- **Criterio de avance:** suite completa pasa, `grep -r "Bearer\|jwt\|jose"
  backend/app/` no retorna resultados (excepto comentarios documentales).

### Paso 5: Validación integral

- Ejecutar suite backend completa.
- `npx oxlint src` en frontend.
- Build de producción frontend.
- Auditoría de rutas duplicadas.
- OpenAPI: verificar que `/api/auth/login` no aparece.
- **Criterio de avance:** validación técnica completa.

### Paso 5A: Precondiciones de datos y esquema

**Estado local: completado y validado el 10 de agosto de 2026.**

- Resolver la contradicción de 011 por su flujo técnico independiente.
- Ejecutar preflight usuario-estado y validar respaldo restaurable.
- Investigar si existe estado de autenticación recuperable.
- Si no existe, ejecutar F-01A en una única transacción con evento auditable.
- **Criterio de avance:** esquema alineado, un estado por usuario, evidencia de
  recuperación y regresión auth aprobada.

### Paso 6: Checklist TLS y E2E en staging

- Recibir y registrar el origen HTTPS exacto sin credenciales.
- Validar cookie `Secure` detrás de TLS real y certificado válido.
- Validar Origin público exacto y lista de proxies vacía.
- Crear cuentas y fixtures no productivos para territorio permitido/denegado.
- Aceptación E2E: login, quinto fallo, desbloqueo, expiración, logout,
  RBAC/territorio en Chromium y Firefox.
- **Criterio de avance:** ambos navegadores aprueban toda la matriz.

### Paso 7: Documentación y cierre

- Actualizar `README.md`, `docs/migraciones.md`.
- Crear checklist TLS si no existe.
- Preparar actualización de `ESTADO_PROYECTO.md` (no aplicar aún).
- **Criterio de avance:** diff revisado, listo para commit.

## 10. Matriz de pruebas

### Tests que deben existir post-contracción

| Caso | Resultado esperado | Archivo |
|------|--------------------|---------|
| Login cookie exitoso | 200, cookies seteadas, `access_token` NO en body. | `test_auth_corte4.py` (ya existe) |
| Login correo inexistente/clave errónea/inactivo | 401 genérico uniforme. | `test_auth.py` (reescribir) |
| Cookie ausente | 401. | `test_auth.py` (reescribir) |
| Cookie inventada | 401. | `test_auth.py` (reescribir) |
| CSRF ausente en escritura | 403. | `test_auth_corte4.py` (ya existe) |
| CSRF incorrecto/Origin no permitido | 403. | `test_auth_corte4.py` (agregar) |
| Quinto fallo concurrente | Bloqueo, evento, admin desbloquea. | `test_auth_corte4.py` (ya existe) |
| Expiración inactividad/absoluta | 401, evento sin actor humano. | `test_auth_corte4.py` (ya existe) |
| Logout actual/todas | Revoca, cookies borradas. | `test_auth_corte4.py` (ya existe) |
| Revocación admin | Sesiones objetivo inválidas. | `test_auth_corte4.py` (ya existe) |
| Constraints DB (estado sin evento) | Error de trigger. | `test_auth_corte4.py` (ya existe) |
| Constraints DB (cambio colateral en expiración) | Error de trigger. | `test_auth_corte4.py` (ya existe) |
| Identidad inexistente no guarda PII | NULL sin correo. | `test_auth_corte4.py` (ya existe) |
| Redacción de `contrasena_hash` en bitácora | No aparece. | `test_auth_corte4.py` (ya existe) |
| **`POST /api/auth/login` post-contracción** | **404 o 405.** | **`test_auth.py` (nuevo)** |
| **Bearer header post-contracción** | **401.** | **`test_auth.py` (nuevo)** |
| Rutas protegidas sin auth | 401 sin detalle interno. | `test_auth.py` (conservar) |
| RBAC por rol | 403 para rol no permitido. | Tests de dominio (conservar) |
| Territorio (`usuario_tramo`) | Aislamiento por tramo. | Tests 2B/2C (conservar) |
| Suite completa 2A–2C | Sin regresiones. | Archivos existentes |
| Preflight usuario-estado | Detecta toda cuenta sin estado y no escribe. | SQL/runbook de recuperación |
| Investigación recuperable | Documenta respaldo/eventos examinados sin exponer secretos. | Evidencia operativa |
| Recuperación F-01A | Inserción y evento son atómicos; rollback no deja ninguno. | Integración PostgreSQL |
| Cardinalidad posterior | Exactamente un estado por usuario; cero huérfanos. | Integración PostgreSQL |
| Territorio permitido | Usuario no productivo accede sólo al tramo asignado. | E2E Chromium y Firefox |
| Territorio denegado | El mismo usuario no consulta ni modifica el otro tramo. | E2E Chromium y Firefox |
| Sin proxy confiable | `AUTH_TRUSTED_PROXY_IPS` vacío; no se confía en XFF. | Configuración y E2E |

### Tests que se eliminan

| Test actual | Razón |
|-------------|-------|
| `test_login_exitoso_devuelve_token_y_datos_usuario` | Endpoint eliminado; reemplazado por test cookie. |
| Tests que validan `access_token` en respuesta. | JWT ya no se emite. |

## 11. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Consumidor bearer no descubierto. | Baja (inventario exhaustivo, frontend 100% migrado). | Se rompe si existe. | Grep completo, rollback inmediato si aparece. |
| `TestClient` no persiste cookies como se espera. | Media. | Tests fallan. | Verificar comportamiento de `TestClient` de Starlette con cookies; si no persiste automáticamente, pasar cookies manualmente o usar session de `httpx`. |
| Fixtures `admin_session` rompen tests existentes. | Media. | Regresión de suite. | Migración incremental; primero alias, luego rename. |
| Ambiente real no tiene TLS. | Alta (no documentado). | Cookie `Secure` no se puede validar; Corte 4 no se cierra. | Documentar checklist; permitir cierre de contracción de código independiente de TLS. |
| La eliminación de `python-jose` afecta otra dependencia. | Muy baja. | Fallo de import. | `pip install` y suite. |
| Bitácora crece por actividad de tests. | Baja. | Lentitud de tests. | Base aislada por suite. |
| Operadores existentes con JWT vivo quedan sin sesión. | Baja (base local sin datos operativos). | 30 min de interrupción máxima. | JWT expira en 30 min; el usuario hace login cookie normalmente. |
| El estado recuperado no correspondiera al usuario actual. | Mitigada. | Estado de seguridad incorrecto. | Se verificó el mismo `id_usuario`, rol activo y metadatos del respaldo antes de restaurar. |
| Origen HTTPS sigue pendiente. | Confirmada hasta crear staging. | CORS/CSRF y cookies no pueden aceptarse externamente. | Tratarlo como entrada de despliegue; no usar un valor provisional como evidencia final. |
| 011 se ejecutara de nuevo o quedara parcial. | Mitigada. | DDL divergente. | Transacción, bloqueo asesor, guardas 010/011, restauración completa y prueba de repetición. |
| Fixtures dejan trazas permanentes. | Media. | Contaminación de auditoría de staging. | Identidades no productivas, baja lógica y etiquetado explícito de evidencia. |

## 12. Criterios de aceptación

1. `POST /api/auth/login` retorna 404 o 405.
2. `Authorization: Bearer <jwt>` retorna 401.
3. Ningún archivo en `backend/app/` importa `jose` ni `OAuth2PasswordBearer`.
4. `python-jose` eliminado de `requirements.txt`.
5. `schemas.Token` y `schemas.TokenData` eliminados.
6. `CORS allow_headers` no incluye `"Authorization"`.
7. Suite backend completa (117+ tests) pasa con autenticación cookie.
8. `grep -r "admin_headers" backend/tests/` retorna cero (o alias temporal
   documentado).
9. Cero uso de `/api/auth/login` en tests (excepto test de contracción que
   valida 404/405).
10. OpenAPI no documenta `/api/auth/login`.
11. Frontend pasa oxlint y build sin cambios (no requiere modificación).
12. La base objetivo está alineada con el HEAD y la contradicción de 011 está
    resuelta con evidencia de respaldo, orden y aplicación segura.
13. El preflight usuario-estado pasa; si se ejecutó F-01A, estado y evento se
    confirmaron atómicamente y la investigación quedó documentada.
14. Documentación actualizada sin secretos ni credenciales.
15. El origen HTTPS exacto está definido; cookie `Secure`, prefix `__Host-`,
    certificado, CORS y rechazo de Origin distinto están validados.
16. `AUTH_TRUSTED_PROXY_IPS` permanece vacío mientras el staging no use proxy.
17. Login, bloqueo, desbloqueo, expiración, logout y RBAC/territorio pasan en
    Chromium y Firefox con cuentas y fixtures no productivos.
18. Los estados “contracción validada” y “Corte 4 aceptado” se reportan por
    separado; no se declara el segundo con evidencia pendiente.

## 13. Actualizaciones previstas para `ESTADO_PROYECTO.md`

Después de implementar y validar la contracción:

1. **Fecha y próximo trabajo funcional:** actualizar al siguiente paso
   (replicación de migraciones en otros ambientes + Corte 5 o pendientes
   transversales).
2. **Corte 4:** cambiar de "incremento principal implementado" a
   "terminado" si TLS y E2E están validados, o "contracción implementada,
   pendiente TLS/E2E" si sólo se completó la contracción de código.
3. **Sección 2 (Stack y rutas):** retirar `POST /api/auth/login` de la
   lista de contratos HTTP.
4. **Sección 4 (Reglas):** confirmar que toda autenticación es por cookie
   opaca revocable; no existe JWT.
5. **Sección 6 (Trabajo realizado):** agregar evidencia de contracción,
   inventario completo, suite migrada y validación técnica.
6. **Sección 9 (Trabajo transversal):** actualizar pendientes de TLS y
   replicación.
7. **Sección 10 (Instrucción):** actualizar al siguiente trabajo.

No modificar `ESTADO_PROYECTO.md` durante la implementación.

## 14. Registro de decisiones

Las decisiones D1-D7 de la propuesta original quedaron materializadas o
resueltas durante la contracción validada del 6 de agosto de 2026 y no se
reabren.

| ID | Decisión incorporada | Estado | Consecuencia |
|----|----------------------|--------|--------------|
| F-01 | Reparación controlada F-01A. | Ejecutada y validada localmente. | Se restauró la fila exacta del respaldo y se registró el evento atómicamente, sin modificar 008. |
| F-02 | Staging HTTPS dedicado, sin proxy, cuentas y fixtures no productivos. | Aprobada. | El origen exacto se incorpora al aprovisionar staging; no se acepta HTTP, certificado autofirmado ni producción sin autorización específica. |
| F-03 | Chromium y Firefox como matriz mínima. | Aprobada. | Ambos deben aprobar toda la aceptación; Safari/WebKit queda fuera. |
| T-011 | Conciliar documentación, migración y esquema activo. | Resuelta localmente. | 011 está registrada; transacción, vistas, trigger, funciones, restauración y repetición fueron verificadas. |

## 15. Gates de diseño tras incorporar decisiones

| Gate | Resultado | Condición pendiente |
|------|-----------|---------------------|
| Funcional | Aprobado | Staging, ausencia de proxy y navegadores están definidos; el origen es entrada de despliegue. |
| Datos | Aprobado | F-01A, cardinalidad usuario-estado y auditoría FK verificadas. |
| Seguridad | Aprobado para diseño/local | Recuperación auditable validada; cookies/Origin requieren staging real. |
| Autorización | Aprobado para diseño | Fixtures permitido/denegado autorizados; E2E requiere staging. |
| Arquitectura | Aprobado | No cambia dominio ni responsabilidades existentes. |
| Migración | Aprobado | 011 aplicada con recuperación de estado parcial, rollback y guarda de repetición. |
| Pruebas | Aprobado para evaluación | 119 backend, build y lint sin errores; E2E Chromium/Firefox pendiente. |

La propuesta pasa los gates de diseño y queda lista para evaluación. Esto no
declara Corte 4 aceptado: el cierre continúa condicionado al origen HTTPS real
y a la matriz E2E completa en staging.
