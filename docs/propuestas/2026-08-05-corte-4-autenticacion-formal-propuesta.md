# Propuesta técnica — Corte 4: autenticación formal

Fecha: 2026-08-05
Estado: propuesta corregida e implementada parcialmente; incremento principal
validado con corrección 009, pendiente de contracción bearer y aceptación
HTTPS/E2E

## 1. **Trabajo vigente identificado**

`ESTADO_PROYECTO.md` indica que el Corte 4 comienza después de cerrar la
rotación operativa de secretos. El responsable del proyecto confirmó el 5 de
agosto de 2026 que, antes de solicitar esta auditoría, ya había cambiado:

- la contraseña de la cuenta de PgAdmin;
- la contraseña del rol PostgreSQL usado por la base;
- `SECRET_KEY` del backend.

Con esta continuidad nueva, el siguiente trabajo vigente es el **Corte 4 —
Autenticación formal**. Su alcance aprobado es:

1. Sustituir el JWT almacenado en `localStorage`.
2. Adoptar cookie HttpOnly o estrategia equivalente.
3. Implementar sesiones revocables y logout real.
4. Registrar accesos exitosos y fallidos.
5. Bloquear la cuenta después de cinco intentos fallidos consecutivos.
6. Aplicar expiración e inactividad.
7. Agregar pruebas de autenticación y autorización.

La rotación ya realizada se toma como hecho operativo reportado, no se
rediseña ni se ejecuta otra vez. Tampoco se reabren los Subcortes 2A–2C, se
alteran reglas de liberación ni se incorpora el Corte 5.

## 2. **Estado actual verificado**

Esta sección conserva la línea base de la auditoría previa: en esa etapa la
revisión fue de sólo lectura y no se ejecutaron migraciones ni escrituras en
PostgreSQL. El resultado posterior está documentado en la evaluación asociada.

### Fuentes y límites

- Se leyó completo `ESTADO_PROYECTO.md` y se siguió el orden documental
  indicado: descripción funcional, flujo, estructura de datos, diccionario,
  requerimientos, migraciones 001–006, propuesta 2A y diseño. También se
  contrastaron la migración 007 y la propuesta previa de Corte 3.
- `flujograma propiedad social.pdf` no está presente en el repositorio y no se
  sustituyó por otro PDF.
- `docs/Diccionario_Datos_SSALFER.md` aún describe 004 y partes de
  `docs/Descripción proceso.md` presentan 2C como pendiente. El esquema activo
  004–007 y `ESTADO_PROYECTO.md` prevalecen.
- La rotación fue confirmada por el responsable. La inspección actual puede
  comprobar configuración no placeholder y servicios saludables, pero no
  reconstruir por sí sola el rechazo de valores anteriores porque no se
  conservaron ni deben conservarse secretos previos.

### Auditoría por capa

| Capa | Estado actual verificado |
| --- | --- |
| Modelo de datos | `usuario` tiene correo, hash bcrypt, rol, estado y ciclo de vida. No contiene contador de intentos, bloqueo ni último acceso. No existen tablas de sesión, estado de autenticación o eventos de acceso. `bitacora.id_usuario` es obligatorio, por lo que no representa un intento fallido de identidad inexistente. |
| Migraciones | La base activa registra 004, 005, 006 y 007. Ninguna migración modela sesiones, revocación, intentos o accesos. Los triggers de `usuario` están activos. |
| ORM | `models.Usuario` refleja el esquema actual. No existen `SesionUsuario` ni `EventoAcceso`. |
| Contratos | `schemas.Token` expone `access_token`, `token_type` y un `dict` de usuario. `UsuarioCreate.contrasena` no declara una política Pydantic; `UsuarioUpdate` no cambia contraseña ni bloqueo. |
| Autenticación | `auth.py` usa JWT HS256 de 30 minutos, bcrypt y `OAuth2PasswordBearer`. El token sólo identifica correo y rol; `get_current_user` vuelve a consultar usuario activo. No existe sesión servidor. |
| Login | `POST /api/auth/login` consulta el correo, verifica bcrypt y entrega bearer token. No usa comparación dummy para usuario inexistente, no registra accesos, no bloquea y responde distinto para usuario inactivo (`400`) y credenciales inválidas (`401`). |
| Logout/revocación | No hay endpoint. El frontend borra `localStorage`, pero el JWT continúa válido hasta expirar. Cambiar rol o contraseña tampoco revoca JWT ya emitidos. |
| Autorización | `RoleChecker` consulta el usuario actual y `services/access.py` aplica pertenencia mediante `usuario_tramo`. Esta autorización territorial debe conservarse sin confiar en IDs del cliente. |
| Frontend | `AuthContext.jsx` confía en `localStorage.user` y `localStorage.token`; Axios añade `Authorization: Bearer`. Recargar restaura el usuario sin verificar inmediatamente la sesión contra backend. Logout es sólo local. |
| Cookies/CORS/CSRF | No hay cookie de autenticación ni defensa CSRF para escrituras autenticadas por cookie. Compose configura `CORS_ORIGINS`, pero la transición deberá exigir orígenes exactos y credenciales. |
| Auditoría | `fn_audit_log()` exige `app.current_user_id` y guarda fotografías completas. Si se actualiza `usuario` para intentos o último acceso, atribuiría el fallo a un usuario autenticado inexistente —o falsamente a la víctima— e incluiría `contrasena_hash` en `valor_anterior/nuevo`. |
| Pruebas | `test_auth.py` cubre login válido/inválido, token inventado y rutas protegidas. No cubre cookie, CSRF, sesiones concurrentes, revocación, logout, cinco intentos, inactividad o expiración. `conftest.py` conserva credenciales fallback conocidas. |
| Infraestructura activa | PostgreSQL 15.4 usa SCRAM-SHA-256. DB, backend, scheduler y PgAdmin estaban saludables. El healthcheck raíz del backend no consulta DB. |
| Datos activos | Base `db_trenes`, cero afectaciones/convenios/ciclos y una cuenta admin activa. El rol DB actual es dueño del esquema y superusuario; es un riesgo de infraestructura separado, no una decisión de autenticación web. |

## 3. **Reglas funcionales confirmadas**

1. Todo acceso protegido exige identidad autenticada y usuario activo.
2. Los roles vigentes son `admin`, `operador`, `visualizador` y `geografo`.
3. RBAC no sustituye pertenencia territorial; `usuario_tramo` debe seguir
   validándose en cada recurso.
4. Una sesión debe poder revocarse inmediatamente sin cambiar `SECRET_KEY`.
5. Logout real revoca la sesión servidor y elimina la cookie del navegador.
6. Cinco fallos consecutivos bloquean la cuenta; un acceso válido reinicia el
   contador sólo si la cuenta no está bloqueada.
7. La inactividad máxima confirmada por RNF-9 es 30 minutos.
8. Accesos exitosos, fallidos, bloqueados, logout y revocaciones deben quedar
   registrados con fecha, resultado y contexto técnico seguro.
9. Un fallo para correo inexistente también debe registrarse, sin requerir un
   `id_usuario` falso ni revelar si la identidad existe.
10. Contraseña, cookie de sesión, token opaco, hash de sesión, CSRF y
    `contrasena_hash` nunca se devuelven ni se registran en logs/bitácora.
11. Toda escritura de dominio auditable usa `set_audit_context` antes de
    `commit`; los eventos de acceso necesitan un mecanismo forense propio
    porque pueden ocurrir antes de autenticar un usuario.
12. No hay bajas físicas de usuarios, sesiones o eventos de seguridad.
13. La sesión no altera rol ni asignaciones; éstos se consultan de la fuente
    actual para que cambios administrativos surtan efecto.
14. Las respuestas de login deben ser genéricas y no exponer usuario
    inexistente, contraseña incorrecta, inactividad o detalles internos.
15. La transición debe ser expansiva y permitir despliegue backend/frontend
    coordinado antes de retirar bearer JWT.
16. El requerimiento 25.6 exige auditoría estricta desde PostgreSQL también
    para accesos de usuario; una excepción sólo en Python no es suficiente.

## 4. **Hallazgos y contradicciones**

| ID | Hallazgo | Estado | Impacto |
| --- | --- | --- | --- |
| AUTH-01 | JWT se guarda en `localStorage`. | Implementado, por retirar | Cualquier XSS puede leerlo. |
| AUTH-02 | Logout sólo borra estado local. | Implementado, insuficiente | El token sigue válido hasta 30 minutos. |
| AUTH-03 | No existe identidad de sesión servidor. | Pendiente | No hay revocación selectiva, listado ni cierre inmediato. |
| AUTH-04 | Login no registra éxito/fallo ni bloquea. | Contradice RNF-10 | Ataques de fuerza bruta no quedan controlados ni trazados. |
| AUTH-05 | Usuario inexistente e inactivo tienen rutas/tiempos/respuestas distintas. | Pendiente | Facilita enumeración de cuentas. |
| AUTH-06 | Actualizar `usuario` auditaría `contrasena_hash`. | Pendiente crítico | Intentos/último acceso ampliarían exposición del hash en bitácora. |
| AUTH-07 | `bitacora.id_usuario NOT NULL` no admite fallos sin identidad válida. | Diseño incompatible | Se requiere una tabla de eventos de acceso separada. |
| AUTH-08 | No hay CSRF porque hoy se usa bearer manual; al migrar a cookie aparecerá este riesgo. | Riesgo de transición | No debe activarse cookie sin protección de escrituras. |
| AUTH-09 | `conftest.py` conserva fallback conocido. | Deuda de Corte 3 | Las pruebas pueden depender accidentalmente de una cuenta predecible. |
| AUTH-10 | `UsuarioCreate` no impone la política segura del bootstrap. | Contradicción | Un admin puede crear claves más débiles que el primer administrador. |
| AUTH-11 | No se definió duración absoluta de sesión ni duración del bloqueo. | Requiere aprobación | “Expiración” y “bloqueo” no están completamente especificados. |
| AUTH-12 | El diseño histórico recomienda refresh JWT, pero `ESTADO_PROYECTO.md` sólo exige una estrategia formal revocable. | Propuesta histórica | No obliga a implementar refresh token/JWT. |
| AUTH-13 | El rol DB de aplicación es superusuario. | Riesgo separado | Agrava un compromiso, pero cambiar ownership no debe mezclarse con sesiones web. |
| AUTH-14 | La propuesta original ubicaba contador/bloqueo en `usuario`. | Corregido | Se implementó `estado_autenticacion_usuario` y evento DB correlacionado; nunca se usa a la víctima como actor. |
| AUTH-15 | La propuesta no definía cómo auditar `ultima_actividad` sin escribir y auditar cada request. | Corregido con riesgo aceptado | Cada request autenticado actualiza y audita la sesión; se conserva medición futura de crecimiento. |
| AUTH-16 | El repositorio sólo demuestra HTTP entre frontend y Nginx/backend; el terminador TLS y proxies confiables del despliegue real no están documentados. | Mitigado, pendiente operativo | Producción falla cerrado sin cookie Secure/origen exacto; resta validación detrás del TLS real. |
| AUTH-17 | La semántica de “inactividad” no estaba cerrada. | Corregido | Actividad significa request autenticado aceptado por el servidor; no se envían heartbeats por movimiento local. |
| AUTH-18 | No hay inventario verificable de consumidores bearer externos. | Pendiente compatible | Bearer se conserva durante expansión; no se declara Corte 4 terminado hasta inventario/contracción. |

## 5. **Diseño propuesto**

### 5.1 Estrategia recomendada

Usar **sesiones opacas almacenadas en PostgreSQL** y una cookie HttpOnly. No
guardar JWT ni identificadores de sesión en `localStorage`.

```text
Login válido
  → generar 256 bits aleatorios
  → guardar sólo SHA-256(token) en sesion_usuario
  → enviar token original en cookie HttpOnly
  → cada request resuelve sesión + usuario + rol + territorio
  → logout/revocación marca la sesión revocada
```

Esta estrategia se prefiere sobre refresh JWT porque satisface revocación e
inactividad con menos estados criptográficos y encaja con PostgreSQL ya
disponible. El valor opaco nunca se persiste en claro.

### 5.2 Modelo propuesto

#### `sesion_usuario`

- `id_sesion BIGSERIAL` PK.
- `id_usuario INTEGER` FK obligatoria.
- `token_hash CHAR(64)` único; SHA-256 hexadecimal.
- `csrf_hash CHAR(64)` para vincular protección CSRF sin guardar el valor en
  claro.
- `fecha_creacion TIMESTAMPTZ`.
- `ultima_actividad TIMESTAMPTZ`.
- `expira_en TIMESTAMPTZ` para límite absoluto.
- `revocada_en TIMESTAMPTZ`, `id_usuario_revoca`, `motivo_revocacion`.
- `ip_creacion INET`, `user_agent_creacion TEXT` con longitud limitada.
- ciclo de vida sin DELETE físico.

La FK usa `ON DELETE RESTRICT`. PostgreSQL debe exigir
`expira_en > fecha_creacion`, `ultima_actividad >= fecha_creacion` y metadatos
de revocación completos o totalmente nulos.

Una sesión está activa cuando no está revocada, su usuario está activo, no
superó `expira_en` y `ultima_actividad` no es anterior a 30 minutos.

#### `evento_acceso`

Registro append-only independiente de `bitacora`:

- `id_evento BIGSERIAL` PK.
- `id_usuario INTEGER NULL` para identidades no encontradas.
- `id_sesion BIGINT NULL`.
- `tipo_evento`: `login_exitoso`, `login_fallido`, `cuenta_bloqueada`,
  `logout`, `sesion_expirada`, `sesion_revocada`, `desbloqueo`.
- `motivo_codigo` controlado, nunca texto de excepción.
- `fecha_hora TIMESTAMPTZ`, `ip_origen INET`, `user_agent TEXT` limitado.

Los tipos de evento y motivos se limitan mediante `CHECK` o catálogo
controlado.

Para una identidad inexistente se conserva `id_usuario = NULL` y no se guarda
el correo ni un SHA-256 enumerable. PostgreSQL debe bloquear `UPDATE` y
`DELETE` en esta tabla. Es el mecanismo forense de accesos, no una tabla que
vuelva a auditarse a sí misma.

#### `estado_autenticacion_usuario`

La corrección separa el estado técnico del registro operativo `usuario`:

- `id_usuario INTEGER` PK/FK obligatoria hacia `usuario`.
- `intentos_fallidos SMALLINT NOT NULL DEFAULT 0` con `CHECK 0..5`.
- `bloqueado_hasta TIMESTAMPTZ NULL` o estado equivalente, según duración
  aprobada.
- `ultimo_acceso_en TIMESTAMPTZ NULL`.

No usar `activo = false` como bloqueo: `activo` conserva su significado de
baja lógica. Los cambios de esta tabla y su `evento_acceso` deben producirse
en una única función/transacción protegida en PostgreSQL. La forma de
representar auditoría sin actor autenticado se resolvió con
`evento_acceso.id_usuario_actor NULL` y un trigger que exige evento objetivo
de la misma transacción. No se reutiliza como actor al usuario objetivo ni se
desactiva el trigger genérico silenciosamente.

### 5.3 Estados y transiciones

```text
Cuenta activa
  ├── fallo 1..4 → activa con contador
  ├── fallo 5    → bloqueada
  ├── éxito      → contador 0 + sesión activa
  └── baja lógica → inactiva + revocar todas las sesiones

Sesión activa
  ├── actividad válida → actualizar ultima_actividad
  ├── 30 min inactiva  → expirada
  ├── límite absoluto  → expirada
  ├── logout            → revocada
  ├── revocación admin  → revocada
  └── usuario inactivo  → inválida + revocación lógica
```

El desbloqueo no reactiva usuarios dados de baja ni recupera sesiones
anteriores; sólo permite un login nuevo.

### 5.4 Cookie y CSRF

- Producción: cookie `__Host-pa_session`, `HttpOnly`, `Secure`, `Path=/`, sin
  `Domain`, `SameSite=Lax` o `Strict` según integración aprobada.
- Desarrollo HTTP: nombre separado y `Secure=false` sólo con configuración
  explícita de ambiente; nunca degradar producción automáticamente.
- La cookie de sesión no contiene datos de usuario ni JWT.
- El token CSRF se entrega en una segunda cookie `Secure`, `Path=/`, sin
  `Domain` y no HttpOnly; Axios copia su valor a `X-CSRF-Token`. El servidor
  compara el hash con `sesion_usuario.csrf_hash`. La cookie CSRF no autentica.
- Toda operación insegura (`POST`, `PUT`, `PATCH`, `DELETE`) autenticada por
  cookie exige token CSRF ligado a la sesión y header `X-CSRF-Token`, además
  de validación de `Origin` contra lista exacta.
- CORS debe usar orígenes explícitos y `allow_credentials=true`; nunca `*`.

### 5.5 Endpoints

```text
POST /api/auth/sesiones              login y creación de cookie
GET  /api/auth/sesion                usuario/sesión actual
POST /api/auth/logout                revoca sesión actual
POST /api/auth/logout-todas          revoca sesiones propias
POST /api/usuarios/{id}/desbloquear  admin-only
POST /api/usuarios/{id}/revocar-sesiones admin-only
```

El login bearer actual se conserva temporalmente y continúa emitiendo JWT sólo
durante la expansión para no romper el frontend/consumidores antiguos; el
frontend nuevo usa `/api/auth/sesiones`. Después de migrarlo y confirmar que no
existen consumidores externos, se deja de emitir y aceptar bearer. Mientras
bearer siga habilitado, el Corte 4 no se considera terminado.

### 5.6 Concurrencia y transacciones

- Login bloquea `estado_autenticacion_usuario FOR UPDATE`, verifica también
  `usuario.activo`, incrementa o reinicia contador, inserta evento y, si
  procede, sesión dentro de una sola transacción.
- Logout/revocación bloquea la sesión y es idempotente.
- La autenticación de cada request compara hash en tiempo constante y valida
  sesión, usuario, rol y territorio actuales. Cada request aceptado actualiza
  y audita `ultima_actividad`; no se considera actividad el movimiento local
  que no llega al servidor.
- Índices parciales soportan sesiones activas por usuario y búsquedas por
  `token_hash`.

## 6. **Cambios por capa**

| Archivo o componente | Problema | Solución | Justificación | Dependencias | Riesgo | Validación |
| --- | --- | --- | --- | --- | --- | --- |
| `backend/db/migrations/008_corte4_autenticacion_formal.sql` | No hay sesiones, eventos ni bloqueo. | Crear `sesion_usuario`, `evento_acceso` y `estado_autenticacion_usuario`, FK/CHECK/índices/triggers; definir función atómica de intentos; redactar secretos en `fn_audit_log`. | Integridad, concurrencia y auditoría también en PostgreSQL. | 007, respaldo, decisiones 1–9. | Auditoría sin actor aún no aprobada. | Aplicación en restauración aislada, catálogo, constraints, concurrencia y rollback ante fallo. |
| `backend/db/migrations/009_corte4_auditoria_sistema_sesion.sql` | La expiración automática no tiene actor humano y no debe atribuirse a la víctima. | Exigir evento sin actor de la misma sesión/transacción y limitar la excepción a campos de revocación. | Auditoría veraz sin abrir un bypass de integridad. | 008 aplicada. | Uso indebido del contexto técnico. | Expiración normal y UPDATE adversarial con cambio colateral. |
| `backend/app/models.py` | ORM incompleto. | Agregar `SesionUsuario`, `EventoAcceso` y `EstadoAutenticacionUsuario`; no agregar contadores a `Usuario`. | Separa seguridad previa a login del dominio auditable con actor. | Migración 008. | Divergencia ORM/DB. | Inspección y tests ORM. |
| `backend/app/schemas.py` | Contrato devuelve bearer y `dict`. | Contratos tipados para login por sesión, usuario actual, logout, desbloqueo y revocación; nunca token de sesión. | Evita filtrar secretos y estabiliza API. | Servicios auth. | Romper consumidor actual. | OpenAPI y tests de respuesta. |
| `backend/app/services/authentication.py` nuevo | Login está en controlador. | Centralizar login transaccional, bloqueo, sesión, CSRF, actividad, revocación y eventos. | Reglas críticas en una capa comprobable. | Modelos, config y auditoría. | Carreras o bloqueo incorrecto. | Unit/integración/concurrencia. |
| `backend/app/auth.py` | Sólo valida JWT bearer. | Agregar dependencia por cookie opaca; durante transición aceptar mecanismos separados y eliminar bearer al contraer. | Migración incremental. | Servicio de sesión. | Ambigüedad si una request trae ambos. | Rechazar credenciales múltiples o aplicar precedencia explícita probada. |
| `backend/app/main.py` / router auth | Endpoints incompletos. | Mover auth a router dedicado e implementar sesiones/logout/desbloqueo/revocación con errores genéricos. | Reduce controlador heredado. | Contratos/servicio. | Duplicar método/path. | Auditoría de rutas y OpenAPI. |
| `backend/app/config.py` o equivalente | Config de cookies dispersa. | Validar nombre, Secure, SameSite, duración absoluta, inactividad, orígenes y proxies confiables por ambiente. | Falla cerrado. | Topología TLS y decisiones de duración. | Desarrollo HTTP mal configurado. | Tests de configuración por ambiente. |
| `backend/app/services/access.py` | Autorización territorial ya funciona. | Conservarla y alimentarla con usuario resuelto desde sesión; no copiar rol/territorio a cookie. | Cambios administrativos tienen efecto inmediato. | Nueva dependencia auth. | Regresión de acceso. | Matriz RBAC/territorio. |
| `frontend/src/contexts/AuthContext.jsx` | Confía en `localStorage`. | Eliminar token/user persistidos; al cargar consultar `/auth/sesion`, usar `credentials`, mantener sólo estado React. | Sesión no accesible a JavaScript. | API cookie. | Parpadeo/loops de navegación. | Reload, expiración y logout E2E. |
| `frontend/src/api/axios.js` | Inyecta bearer. | Usar `withCredentials`, header CSRF en escrituras y manejo central de 401/403; no leer token local. | Compatibilidad cookie/CSRF. | Entrega de CSRF. | CSRF faltante rompe escrituras. | Tests de GET/POST y origen inválido. |
| `frontend/src/pages/Login.jsx` | Sólo maneja token bearer. | Consumir login de sesión, mensajes genéricos y estado de bloqueo sin enumeración. | UX compatible y segura. | AuthContext. | Mensajes poco accionables. | E2E de éxito/fallo/bloqueo. |
| `frontend/src/App.jsx` | Logout local. | Esperar `/auth/logout`, limpiar estado incluso si la respuesta ya está expirada y redirigir. | Logout real e idempotente. | Endpoint. | Sesión queda activa si se ignora fallo de red. | E2E y reintento seguro. |
| `backend/tests/conftest.py` | Fallback conocido y BD compartida. | Exigir secretos de test o bootstrap efímero en base aislada. | No depender de credenciales operativas. | Infra de tests. | Más configuración local. | Fallo temprano y suite aislada. |
| `backend/tests/test_auth.py` y nuevas pruebas | Cobertura sólo bearer. | Matriz completa de cookies, CSRF, bloqueo, eventos, expiración, concurrencia y revocación. | Criterio de cierre. | Fixture temporal/control de reloj. | Pruebas frágiles por tiempo. | Reloj inyectable y DB aislada. |
| `docker-compose.yml`, `.env.example`, proxy frontend | Falta config cookie/CSRF. | Variables sin secretos reales, HTTPS/origen exacto y proxy same-origin donde aplique. | Cookie segura por ambiente. | Infra TLS. | Cookie Secure no funciona en HTTP. | Smoke test local y producción. |
| `README.md`, `docs/migraciones.md` | Documentación sólo JWT/rotación. | Runbook de 008, despliegue expand/contract, invalidación global y recuperación admin. | Operación reproducible. | Implementación validada. | Docs anticipan código. | Revisión después de pruebas. |

## 7. **Migración y compatibilidad**

### Migración 008 expansiva

1. `BEGIN`, bloqueo asesor y preflight de 007/ausencia de 008.
2. Establecer actor técnico activo para DDL/DML auditable.
3. Prevalidar usuarios y posibles correos duplicados sin normalizarlos por
   inferencia.
4. Crear `estado_autenticacion_usuario` y una fila compatible por cada usuario,
   con contador cero y sin inferir bloqueos históricos.
5. Crear `sesion_usuario` y `evento_acceso`.
6. Crear restricciones, índices y triggers de no DELETE/append-only.
7. Redactar `contrasena_hash` en fotografías futuras de `usuario`, conservando
   detalle no sensible del cambio.
8. Registrar 008 sólo al final y `COMMIT`.

No se crean sesiones a partir de JWT existentes: no existe una relación
segura que inferir. Usuarios existentes reciben estado con contador cero, sin
bloqueo y sin sesiones. El primer login por cookie crea la sesión explícita.

### Despliegue expand/contract

```text
008 + backend dual
  → frontend cookie
  → pruebas/telemetría
  → dejar de emitir JWT
  → deshabilitar bearer
  → retirar código/localStorage legado
```

No eliminar columnas heredadas de dominio. La contracción sólo afecta el
contrato de autenticación y se realiza cuando no existan consumidores bearer.

Un rollback de frontend puede usar temporalmente backend dual. Después de
deshabilitar bearer no se reactivan JWT comprometidos como recuperación; se
corrige el flujo cookie.

## 8. **Seguridad, autorización e integridad**

- Token de sesión y CSRF se generan con CSPRNG; sólo sus hashes se almacenan.
- Cookies de producción son HttpOnly/Secure y no contienen PII.
- Comparaciones de hashes son constantes; login de usuario inexistente ejecuta
  una verificación bcrypt dummy para reducir diferencias temporales.
- Todas las respuestas de autenticación usan códigos/mensajes controlados y
  registran internamente la causa.
- User-agent se trunca; IP se obtiene sólo de proxy confiable configurado, no
  de cualquier `X-Forwarded-For`.
- El cambio de rol, baja lógica o revocación surte efecto en servidor sin
  esperar expiración de cookie.
- Admin puede desbloquear/revocar, pero no leer tokens ni hashes.
- Operadores y geógrafos no administran sesiones ajenas.
- `usuario_tramo` se sigue verificando para recursos territoriales.
- `evento_acceso` es inmutable y admite `id_usuario NULL`; `bitacora` conserva
  escrituras atribuibles sin hashes. El mecanismo DB para cambios previos a
  autenticación debe aprobarse antes de implementar.
- No se usa `float`, no se modifican importes y no se toca el flujo agrario.

## 9. **Plan incremental de implementación**

1. **Decisiones adoptadas:** auditoría sin actor mediante evento correlacionado,
   8 horas absolutas, bloqueo 15 minutos, actividad por request, sesiones
   concurrentes, SameSite Lax y transición bearer expansiva.
2. **Preparar 008:** preflight, respaldo protegido y ensayo en restauración
   aislada.
3. **Implementar backend expand:** modelos, configuración, servicio
   transaccional, cookies, CSRF, eventos y endpoints, conservando bearer.
4. **Implementar frontend:** eliminar `localStorage`, consultar sesión,
   credenciales cookie, CSRF y logout servidor.
5. **Validar:** suite backend, pruebas PostgreSQL, concurrencia, E2E, RBAC,
   territorio, lint/build y escaneo de seguridad.
6. **Desplegar controladamente:** 008, backend dual, frontend; observar fallos
   sin registrar secretos.
7. **Contraer:** dejar de emitir JWT, deshabilitar bearer y retirar código
   legado tras confirmar consumidores.
8. **Cerrar:** aceptación funcional, revisión del diff y actualización de
   `ESTADO_PROYECTO.md`; no hacer commit ni push sin una solicitud posterior.

## 10. **Matriz de pruebas**

| Caso | Resultado esperado |
| --- | --- |
| Login correcto | Cookie segura, sesión hash en DB, evento exitoso y contador cero. |
| Correo inexistente / clave errónea / usuario inactivo | Respuesta externa equivalente; evento con causa interna segura. |
| Fallos 1–4 | 401, contador consistente, sin sesión. |
| Quinto fallo concurrente | Una transición a bloqueado; contador no supera 5. |
| Login correcto durante bloqueo | Rechazo sin crear sesión. |
| Desbloqueo admin | Auditado, no reactiva usuario ni sesiones anteriores. |
| Cookie ausente/inventada | 401 sin detalle interno. |
| Token guardado en DB | Sólo SHA-256; nunca valor de cookie. |
| CSRF ausente/incorrecto/origen no permitido | 403 en escritura; GET seguro no se rompe. |
| Logout | Revoca sesión, borra cookie e invalida reutilización. |
| Logout repetido | Idempotente. |
| Revocar todas/admin | Sesiones objetivo dejan de funcionar inmediatamente. |
| Dos sesiones concurrentes | Se comportan según política aprobada; revocación selectiva no mezcla usuarios. |
| Inactividad de 30 minutos | Sesión rechazada y evento de expiración único. |
| Límite absoluto | Requiere nuevo login aunque haya actividad. |
| Usuario dado de baja | Todas sus sesiones quedan inválidas; no hay DELETE físico. |
| Cambio de rol/asignación | Siguiente request usa permisos actuales. |
| `contrasena_hash` en bitácora | Nunca aparece tras 008. |
| Evento de correo inexistente | Se registra sin inventar `id_usuario` ni guardar correo claro. |
| Bearer durante expansión | Funciona sólo en ventana documentada. |
| Bearer después de contracción | 401; no se emiten JWT nuevos. |
| Reload frontend | Restaura sesión desde servidor, no `localStorage`. |
| XSS/localStorage | No existe token de autenticación legible. |
| RBAC y `usuario_tramo` | Matriz 401/403 y aislamiento territorial sin regresión. |
| PostgreSQL directo inválido | CHECK/FK/triggers rechazan estados imposibles y DELETE. |
| Suite 2A–2C | Sin regresiones del flujo operativo. |
| Logs y errores | Sin cookies, passwords, hashes, JWT ni excepciones internas. |

Las pruebas temporales deben usar reloj controlable y una base aislada; no la
base activa.

## 11. **Riesgos y mitigaciones**

| Riesgo | Mitigación |
| --- | --- |
| CSRF al pasar de bearer a cookie. | Token ligado a sesión, validación Origin y SameSite. |
| Robo de cookie. | HttpOnly, Secure, TLS, token opaco, expiración y revocación. |
| Carrera en quinto intento. | `SELECT FOR UPDATE`, una transacción y CHECK DB. |
| Bitácora crece por actividad. | Aprobar primero si cada actualización técnica es auditable; luego medir 50 usuarios y, si se exceptúa, hacerlo con mecanismo DB explícito, no sólo en Python. |
| Sesión expira mientras se escribe. | Validar antes de la transacción de dominio y devolver 401 consistente. |
| Backend dual prolonga JWT inseguro. | Fecha de contracción y criterio “sin consumidores bearer”. |
| Cookies Secure fallan localmente. | Config explícita por ambiente; producción falla cerrado sin HTTPS. |
| Evento de acceso filtra correo. | Para identidad inexistente no guardar correo ni hash enumerable; usar `id_usuario` sólo cuando exista. |
| Bloqueo permite denegación de servicio. | Duración/desbloqueo aprobado, mensajes genéricos y futura limitación por IP. |
| Único admin queda bloqueado. | Procedimiento de recuperación auditado y prueba previa. |
| Cambio afecta autorización territorial. | Reutilizar `services/access.py` y regresión completa. |
| Rol DB superusuario. | Trabajo separado de mínimo privilegio; no mezclar ownership con Corte 4. |

## 12. **Criterios de aceptación**

1. Ningún token o usuario de autenticación se persiste en `localStorage`.
2. Producción autentica con cookie HttpOnly/Secure y sesión opaca revocable.
3. PostgreSQL almacena sólo hash del token y estados válidos protegidos.
4. Logout actual, logout total y revocación admin invalidan inmediatamente.
5. Cinco fallos consecutivos bloquean de forma transaccional según política
   aprobada; el éxito válido reinicia el contador.
6. Inactividad de 30 minutos y expiración absoluta funcionan en servidor.
7. Accesos exitosos/fallidos y transiciones quedan en registro append-only sin
   secretos ni identidades inventadas.
8. `contrasena_hash` no aparece en nuevas filas de bitácora.
9. CSRF y Origin protegen todas las escrituras por cookie.
10. Mensajes no enumeran cuentas ni exponen errores internos.
11. Cambios de rol, territorio o baja lógica surten efecto en sesiones activas.
12. Bearer JWT deja de emitirse y aceptarse al cerrar la contracción.
13. RBAC y `usuario_tramo` pasan la matriz completa.
14. No se modifica ningún dato/regla de expedientes, pagos o geometrías.
15. Migraciones 008 y 009, suite backend, pruebas DB/E2E, oxlint y build pasan en base
    aislada.
16. Documentación y logs no contienen secretos.
17. Aceptación funcional confirma login, bloqueo, recuperación, expiración y
    logout antes de declarar Corte 4 terminado.

## 13. **Actualizaciones previstas para `ESTADO_PROYECTO.md`**

Después de implementar y validar:

1. Actualizar fecha y próximo trabajo funcional al Corte 5.
2. Registrar la rotación previa como completada según la continuidad aportada,
   sin valores sensibles.
3. Agregar migraciones 008/009, despliegue y compatibilidad en historial.
4. Documentar modelo de sesión, eventos, bloqueo, CSRF, expiraciones y
   contracción bearer.
5. Cambiar Corte 4 de pendiente a terminado sólo después de retirar bearer.
6. Añadir resultados de suites, E2E, seguridad y aceptación funcional.
7. Mantener como pendientes separados mínimo privilegio DB y otras deudas no
   incluidas.
8. Actualizar la instrucción de continuidad para iniciar Corte 5.

No modificar `ESTADO_PROYECTO.md` durante esta propuesta.

## 14. **Decisiones adoptadas y pendientes operativos**

Adoptadas para el incremento implementado:

1. `evento_acceso` es la pista estricta de accesos sin actor autenticado; el
   estado sólo cambia con evento correlacionado en la misma transacción.
2. La actividad se renueva por request autenticado aceptado y se audita.
3. Límite absoluto de 8 horas e inactividad de 30 minutos.
4. Bloqueo de 15 minutos tras cinco fallos consecutivos; al vencer inicia una
   secuencia nueva. Existe desbloqueo admin y recuperación CLI auditable.
5. Se permiten múltiples sesiones concurrentes, revocables individualmente o
   en conjunto.
6. Cookie `SameSite=Lax`; producción obliga `Secure`, `Path=/`, sin `Domain`.
7. Cookie CSRF separada, hash ligado a sesión, header y `Origin` exacto.
8. Eventos permanentes y sesiones sin DELETE físico.
9. `UsuarioCreate` usa la misma política mínima del bootstrap.

Pendiente operativo antes del cierre total:

1. documentar y validar terminación TLS, origen público y proxies confiables
   del ambiente real;
2. inventariar consumidores bearer y aprobar fecha de deshabilitación;
3. medir crecimiento de bitácora por actividad y particionar/archivar sin
   pérdida de trazabilidad si el volumen real lo exige;
4. obtener aceptación funcional E2E en navegadores soportados.
