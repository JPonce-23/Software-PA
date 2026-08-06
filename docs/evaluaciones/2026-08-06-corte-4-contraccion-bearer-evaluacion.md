# Evaluación técnica — Corte 4: contracción bearer

Fecha: 6 de agosto de 2026
Propuesta evaluada: `docs/propuestas/2026-08-05-corte-4-contraccion-aceptacion-propuesta.md`
Fuente de verdad: `ESTADO_PROYECTO.md` (secciones 6 Corte 4 y 10 Instrucción)

## 1. Trabajo vigente identificado

`ESTADO_PROYECTO.md` líneas 21–26 y 961–975 definen el próximo paso:

> Completar la contracción y aceptación operativa del Corte 4 de autenticación
> formal: validar cookies `Secure` detrás del TLS real, inventariar consumidores
> bearer, retirar JWT cuando sea compatible y ejecutar aceptación funcional en
> navegador.

Pendientes explícitos (líneas 861–865):

1. Inventariar consumidores externos y retirar login bearer/JWT heredado.
2. Validar cookie `Secure`, host/origen y proxy confiable detrás del TLS real.
3. Ejecutar aceptación funcional E2E en navegadores soportados.

Restricción vinculante (línea 975):

> No declarar Corte 4 terminado mientras bearer siga habilitado.

**Alcance realizable en esta sesión:** los puntos 1 y 5 (inventario, migración
de tests y retiro de código bearer/JWT). Los puntos 2, 3 y 4 requieren
infraestructura TLS real no disponible localmente.

## 2. Resumen de la propuesta evaluada

La propuesta de 2026-08-05 propone:

1. Inventario exhaustivo de consumidores bearer (ya redactado).
2. Migrar la suite de tests de bearer a cookie (nuevo fixture `admin_session`).
3. Eliminar endpoint legacy `POST /api/auth/login`, código JWT de `auth.py`,
   schemas `Token`/`TokenData`, dependencia `python-jose`.
4. Retirar `"Authorization"` de CORS, `WWW-Authenticate: Bearer` de servicios.
5. Validación TLS y E2E documentada como pendiente operativo (D5).
6. Plan de 7 pasos con criterios de avance y 15 criterios de aceptación.

## 3. Hallazgos de auditoría

### H1: Cookie jar compartido rompe tests con múltiples roles (CRÍTICO)

La propuesta sugiere que `admin_session` retorne headers CSRF y que el
`TestClient` compartido (`client`, scope session) persista las cookies del
admin. Esto funciona para tests que sólo usan admin.

**Pero los tests 2B (L515-522) y 2C (L365-370) crean un operador, hacen login
con bearer propio y ejecutan requests como operador usando el MISMO `client`
compartido.** Con bearer esto funciona porque el operador usa
`Authorization: Bearer <token>` sin tocar cookies. Con cookies, el login del
operador en el `client` compartido **sobrescribiría** la cookie de sesión del
admin, rompiendo los tests siguientes.

**Corrección:** Los tests 2B y 2C deben usar un `TestClient` separado para el
operador (como ya hace `test_auth_corte4.py` con `with TestClient(app) as
browser:`). El admin sigue en el `client` compartido. Las requests del
operador se ejecutan en el `TestClient` separado.

### H2: `test_reportes_y_endpoints_especiales.py` usa login legacy para obtener `id_usuario`

Los tests `test_asignar_usuario_a_tramo`, `test_remover_usuario_de_tramo` y
`test_reactivar_asignacion` (L79-86, L100-107, L127-134) hacen
`POST /api/auth/login` no para autenticarse sino para obtener el `id_usuario`
del admin. Post-contracción, deben obtener el `id_usuario` de
`GET /api/auth/sesion` (que retorna `AuthSessionResponse` con `user.id_usuario`).

### H3: Notación incorrecta de `python-jose` en requirements

La propuesta dice eliminar `python-jose[cryptography]` pero el archivo real
tiene `python-jose==3.5.0` (línea 36 de requirements.txt). `cryptography`
es una dependencia separada (L10) que NO debe eliminarse.

### H4: `SECRET_KEY` es exclusiva de JWT

El auditor de auth confirmó que `SECRET_KEY` se usa exclusivamente para
`jwt.encode` (L59) y `jwt.decode` (L69) en `auth.py`. Post-contracción,
la validación de arranque (L13-39) exigirá una variable de entorno que ya no
se consume operativamente. La propuesta dice conservarla (D6).

**Ajuste:** Conservar `SECRET_KEY` y su validación es defensivo y correcto
como decisión de diseño (puede servir para futuros mecanismos). No bloquea.

### H5: `OAuth2PasswordRequestForm` tiene dos consumidores

- `main.py` L18/L1384 — endpoint legacy (eliminar)
- `routers/authentication.py` L2/L64 — endpoint de sesiones (CONSERVAR)

El import en `main.py` L18 debe eliminarse junto con el endpoint.
`routers/authentication.py` tiene su propio import y no se afecta.

### H6: El import de `timedelta` en main.py tiene otro consumidor

`main.py` L11 importa `timedelta` que se usa tanto en el endpoint legacy
(L1395) como en otros endpoints (verificar). No eliminar el import.

### H7: `test_auth.py::TestHardeningCorte3` no depende de bearer

Los tests de hardening (L121-142) prueban `_is_insecure_secret_key` y
`validate_admin_config`, funciones que no cambian en la contracción.
Estos tests se conservan sin modificación.

### H8: Middleware CSRF salta requests sin cookie — correcto

El middleware CSRF (main.py L114-116) salta requests sin cookie de sesión.
Post-contracción, esos requests se rechazan por `get_current_user` con 401.
No hay bypass.

## 4. Matriz de evaluación

| Área | Resultado | Evidencia | Ajuste requerido |
|------|-----------|-----------|-----------------|
| Inventario bearer | Aprobado | Auditoría independiente confirma frontend 0%, tests únicos consumidores. | Ninguno. |
| Migración fixture `admin_headers` | Aprobada con ajustes | TestClient persiste cookies (Starlette 1.3.1). | Renombrar a `admin_session`. Agregar `Origin` header para que CORS y CSRF funcionen en escrituras. |
| Migración tests 2B/2C (operador) | Aprobada con ajustes | L515-522 y L365-370 usan bearer de operador en `client` compartido. | Operador necesita `TestClient` separado para aislar cookie jar (H1). |
| Migración `test_reportes` | Aprobada con ajustes | L79-86 usa login legacy para obtener `id_usuario`. | Reemplazar por `GET /api/auth/sesion` (H2). |
| Eliminación endpoint legacy | Aprobada | Sin auditoría, sin bloqueo, sin eventos. Riesgo de seguridad activo. | Eliminar `OAuth2PasswordRequestForm` import en main.py (H5). |
| Eliminación código JWT en auth.py | Aprobada | L3, L7, L41-44, L52-60, L62-79. | Simplificar `get_current_user` a solo cookie. Conservar `SECRET_KEY` (H4). |
| Eliminación schemas Token/TokenData | Aprobada | Dead code post-contracción. L14-20. | Ninguno. |
| Eliminación `python-jose` | Aprobada con ajustes | L36 en requirements.txt. | Notación correcta: `python-jose==3.5.0`, no `[cryptography]` (H3). |
| Retiro `"Authorization"` de CORS | Aprobada | Post-contracción no se usa. L98 main.py. | Ninguno. |
| Retiro `WWW-Authenticate: Bearer` | Aprobada | Vestigio en services/authentication.py L99 y auth.py L66, L116. | Eliminar de ambos archivos. |
| Reescritura `test_auth.py` | Aprobada | Tests de login legacy se reescriben para cookie; hardening se conserva. | Conservar TestHardeningCorte3 sin cambios (H7). |
| Validación TLS/E2E | Pendiente operativo | No hay infraestructura TLS local. | Documentar como pendiente, no declarar Corte 4 terminado. |
| Concurrencia | Aprobada | No se introducen nuevas condiciones de carrera. | Ninguno. |
| Integridad de datos | Aprobada | Sin migración SQL. Tablas de sesión no cambian. | Ninguno. |
| Autorización territorial | Aprobada | `RoleChecker` depende de `get_current_user`, que post-contracción usa cookie. | Verificar con tests 2B/2C. |
| Auditoría | Aprobada | `set_audit_context` no cambia. Eventos no cambian. | Ninguno. |
| Frontend | Aprobada | Ya 100% migrado. Sin cambios necesarios. | Verificar build. |

## 5. Resultado de los gates

| Gate | Resultado | Justificación |
|------|-----------|---------------|
| Funcional | ✅ Pasa | Atiende exactamente lo pendiente del Corte 4. No reabre decisiones cerradas. |
| Datos | ✅ Pasa | Sin migración SQL. Sin cambios a tablas. Sin estados inválidos posibles. |
| Seguridad | ✅ Pasa | Elimina superficie de ataque (bypass bloqueo, enumeración, JWT no revocable). |
| Arquitectura | ✅ Pasa | Reduce acoplamiento. Elimina código muerto. Responsabilidades claras. |
| Migración | ✅ Pasa | Expansión ya implementada (008/009). Contracción sólo elimina código. |
| Pruebas | ✅ Pasa con ajustes | Requiere corrección del cookie jar compartido (H1) y obtención de `id_usuario` (H2). |

## 6. Propuesta corregida

La propuesta original es viable con las siguientes correcciones:

1. **H1:** Tests 2B y 2C deben usar `TestClient` separado para el operador.
2. **H2:** Tests de reportes deben obtener `id_usuario` de `GET /api/auth/sesion`.
3. **H3:** Eliminar `python-jose==3.5.0` (no `python-jose[cryptography]`).
4. **H5:** Eliminar import `OAuth2PasswordRequestForm` de `main.py` L18.
5. **H4/D6:** Conservar `SECRET_KEY` y validación como decisión defensiva.

## 7. Decisión de viabilidad

**Propuesta viable. Implementación autorizada con correcciones.**

Las decisiones D1-D7 de la propuesta se resuelven como:
- D1: **Aprobada (a)** — retirar `/api/auth/login`.
- D2: **Aprobada (a)** — rename directo `admin_headers` → `admin_session`.
- D3: **Aprobada (a)** — 404 por eliminación natural.
- D4: **Aprobada (a)** — eliminar `python-jose==3.5.0`.
- D5: **Aprobada (b)** — separar código de TLS.
- D6: **Aprobada (a)** — conservar `SECRET_KEY`.
- D7: **Resuelta** — TestClient persiste cookies automáticamente (confirmado).

## 8. Plan final de implementación

### Paso 1: Migrar fixture `admin_headers` → `admin_session`

Actualizar `conftest.py`:
- Login vía `POST /api/auth/sesiones` con Origin.
- Retornar headers `{"Origin": ..., "X-CSRF-Token": ...}`.
- Las cookies de sesión se persisten en el `client` compartido.

### Paso 2: Renombrar `admin_headers` → `admin_session` en TODOS los tests

Buscar-reemplazar en 11 archivos de tests.

### Paso 3: Migrar tests con bearer propio

- `test_subcorte_2b.py`: Crear `TestClient` separado para operador.
- `test_subcorte_2c.py`: Ídem.
- `test_reportes_y_endpoints_especiales.py`: Obtener `id_usuario` de
  `GET /api/auth/sesion`.

### Paso 4: Reescribir `test_auth.py`

- `TestLogin` → tests de sesión cookie.
- `TestProteccionRutas` → sin auth devuelve 401.
- Agregar test post-contracción (login legacy → 404, bearer → 401).
- Conservar `TestHardeningCorte3` sin cambios.

### Paso 5: Contracción de código backend

- Eliminar endpoint legacy `login_for_access_token` de `main.py`.
- Eliminar import `OAuth2PasswordRequestForm` de `main.py`.
- Eliminar código JWT de `auth.py` (imports, constantes, funciones).
- Simplificar `get_current_user()` a sólo cookie.
- Eliminar `Token`, `TokenData` de `schemas.py`.
- Retirar `"Authorization"` de CORS `allow_headers`.
- Retirar `WWW-Authenticate: Bearer` de `services/authentication.py`.
- Eliminar `python-jose==3.5.0` de `requirements.txt`.

### Paso 6: Ejecutar suite y validar

- `pytest backend/tests/ -v`
- Verificar OpenAPI sin `/api/auth/login`.
- `grep -r "Bearer\|jose\|access_token" backend/app/` — sin resultados operativos.

### Paso 7: Actualizar `ESTADO_PROYECTO.md`
