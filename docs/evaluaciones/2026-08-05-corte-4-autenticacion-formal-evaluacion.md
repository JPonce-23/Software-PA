# Evaluación técnica — Corte 4: autenticación formal

Fecha: 2026-08-05

Propuesta evaluada: `docs/propuestas/2026-08-05-corte-4-autenticacion-formal-propuesta.md`

Estado: evaluación, corrección e incremento principal implementados

## 1. **Trabajo vigente identificado**

El responsable confirmó que antes de estos prompts ya había rotado la
contraseña de PgAdmin, la contraseña del rol PostgreSQL y `SECRET_KEY`. Con
esa continuidad, el trabajo vigente es **Corte 4 — Autenticación formal**:

1. retirar JWT de `localStorage`;
2. usar cookie HttpOnly o equivalente;
3. implementar sesiones, revocación y logout real;
4. registrar accesos exitosos y fallidos;
5. bloquear después de cinco fallos consecutivos;
6. aplicar expiración e inactividad de 30 minutos;
7. ampliar pruebas de autenticación y autorización.

No se incluyeron Corte 5, cambios financieros/geoespaciales ni la reducción de
privilegios del rol PostgreSQL.

## 2. **Resumen de la propuesta evaluada**

La propuesta recomendó una sesión opaca de 256 bits en cookie HttpOnly, sólo
SHA-256 del token en PostgreSQL, eventos de acceso inmutables, bloqueo con lock
de fila, protección CSRF, logout/revocación y transición expand/contract para
retirar bearer.

La dirección fue aprobada, pero la versión inicial colocaba el contador en
`usuario`, no resolvía la auditoría previa al login y dejaba sin cerrar
bloqueo, lifetime, actividad, sesiones concurrentes y recuperación admin. La
propuesta se corrigió antes de implementar.

## 3. **Hallazgos de auditoría**

### Hallazgos críticos y resolución

| Hallazgo | Evidencia inicial | Resolución implementada |
| --- | --- | --- |
| Fallos en `usuario` atribuirían el ataque a la víctima o fallarían sin `app.current_user_id`. | `trg_audit_usuario`, `bitacora.id_usuario NOT NULL` y `fn_audit_log()` obligatorio. | Estado separado en `estado_autenticacion_usuario`; cada UPDATE exige en DB un `evento_acceso` objetivo de la misma transacción y admite actor NULL. |
| `fn_audit_log()` fotografiaba `contrasena_hash`. | Función activa usaba `to_jsonb(NEW)`/`row_to_json(OLD)` sin redacción. | 008 redacta `contrasena_hash`, `token_hash` y `csrf_hash` en OLD y NEW. |
| Inactividad y crecimiento de auditoría no estaban definidos. | RNF-9 sólo confirma 30 minutos. | Actividad significa request autenticado aceptado; cada request actualiza y audita sesión. No hay heartbeat por movimiento local. |
| Bloqueo/lifetime/sesiones no estaban cerrados. | RNF-10 confirma cinco fallos, no duración. | Bloqueo 15 minutos, lifetime 8 horas, 30 minutos inactivos y múltiples sesiones concurrentes. |
| Único admin podía quedar bloqueado. | Base activa tenía una sola cuenta. | Endpoint admin de desbloqueo y CLI `unlock_admin.py` con evento `desbloqueo_recuperacion`. |
| Cookie segura dependía de TLS no documentado. | Nginx/Compose prueban HTTP interno; no el terminador externo. | Producción obliga cookie Secure y origen explícito; proxy sólo se confía por IP exacta. Validación detrás del TLS real sigue pendiente. |
| Consumidores bearer externos no son verificables. | Frontend/tests internos estaban inventariados; externos no. | El frontend migró a cookie; bearer permanece temporalmente hasta inventario y contracción. |
| Una expiración automática podía atribuir la actualización genérica de sesión a la víctima. | `fn_audit_log()` exigía actor aun cuando el evento `sesion_expirada` correctamente no lo tenía. | 009 exige evento de sistema sin actor, misma sesión/transacción y permite únicamente los tres campos de revocación; no genera bitácora con actor falso. |

### Estado inicial verificado

- Base activa con migraciones 004–007, una cuenta activa y cero datos
  operativos de afectaciones/convenios/ciclos.
- Sin tablas de sesión, eventos o bloqueo.
- Frontend con token/usuario en `localStorage` y logout sólo local.
- Pruebas con bearer y credenciales fallback; base compartida.
- Rol DB de aplicación superusuario, riesgo preexistente fuera del alcance.

## 4. **Matriz de evaluación**

| Área | Resultado | Evidencia | Ajuste requerido |
| --- | --- | --- | --- |
| Alcance Corte 4 | Aprobada | Coincide con `ESTADO_PROYECTO.md`, RNF-9 y RNF-10. | Mantener fuera Corte 5. |
| Sesión opaca | Aprobada | Token CSPRNG; sólo hash en DB; revocación inmediata. | Ninguno para el incremento. |
| Estado de bloqueo | Aprobada con ajustes | Tabla separada, CHECK 0–5 y evento DB correlacionado. | Medir denegación de servicio en operación. |
| Auditoría | Aprobada | Eventos append-only y redacción de hashes verificados por SQL/tests. | Vigilar crecimiento permanente. |
| Cookie/CSRF | Aprobada con ajustes | HttpOnly, CSRF ligado a sesión, header y Origin exacto. | Smoke detrás del TLS público. |
| Concurrencia | Aprobada | Cinco fallos paralelos producen contador 5 y un solo quinto fallo. | Ninguno. |
| ORM/contratos | Aprobada | Tres modelos y respuestas tipadas sin tokens. | Ninguno. |
| Servicio/endpoints | Aprobada | Servicio transaccional y router dedicado sin rutas duplicadas. | Ninguno. |
| RBAC/territorio | Aprobada | Reutiliza usuario, `RoleChecker` y `services/access.py` actuales. | E2E funcional final. |
| Frontend | Aprobada | Sin `localStorage`; bootstrap servidor, CSRF y logout real. | E2E de navegadores. |
| Contraseñas de usuarios | Aprobada | `UsuarioCreate` alineado con bootstrap. | Gestión/cambio de contraseña sigue fuera de este incremento. |
| Migración 008 | Aprobada | Ensayo desde cero y COMMIT activo con backup/preflight. | Replicar por ambiente. |
| Migración 009 | Aprobada | Ensayo sobre esquema 008, prueba DB adversarial y COMMIT activo con respaldo. | Aplicar inmediatamente después de 008 por ambiente. |
| Pruebas | Aprobada con ajustes | 117 backend, lint y build pasan. | Falta E2E HTTPS real. |
| Compatibilidad bearer | Pendiente de validación | Se conserva sólo durante expansión. | Inventario y fecha de retiro. |

## 5. **Resultado de los gates**

| Gate | Resultado después de correcciones | Evidencia |
| --- | --- | --- |
| Funcional | Superado para incremento expand | Valores/estados cerrados y siete pruebas nuevas. |
| Datos | Superado | FK, CHECK, triggers, no DELETE, evento correlacionado y lock de fila. |
| Seguridad | Superado para entorno local/expand | Cookie/CSRF, mensajes genéricos, dummy bcrypt, redacción y fail-closed de producción. |
| Arquitectura | Superado | Router/servicio/config separados; RBAC/territorio reutilizados. |
| Migración | Superado | 008 y 009 ensayadas en bases aisladas; respaldos válidos, cero transacciones y ambos COMMIT activos. |
| Pruebas | Superado técnicamente | 117 pruebas, Oxlint, build y verificaciones SQL. |

El gate de cierre total de Corte 4 permanece pendiente por TLS/E2E real y
contracción bearer; no impidió el incremento expansivo compatible.

## 6. **Propuesta corregida**

Decisiones adoptadas:

1. `estado_autenticacion_usuario`, no campos nuevos en `usuario`;
2. `evento_acceso` con usuario objetivo y actor nullable;
3. token opaco y CSRF aleatorios; sólo hashes SHA-256 en DB;
4. cookie de sesión HttpOnly y cookie CSRF no HttpOnly ligada a sesión;
5. 30 minutos de inactividad, 8 horas absolutas y bloqueo 15 minutos;
6. actividad sólo por request servidor y auditada;
7. múltiples sesiones concurrentes y revocación actual/total/admin;
8. eventos permanentes y cero DELETE físico;
9. baja lógica de usuario revoca sesiones en la misma transacción;
10. bearer temporal sin uso por el frontend nuevo.

## 7. **Decisión de viabilidad**

La propuesta corregida fue considerada viable para una implementación
expansiva. Se permitió implementar porque los riesgos críticos quedaron
resueltos mediante reglas deterministas y protección PostgreSQL, sin exigir la
contracción incompatible de bearer.

## 8. **Plan final de implementación**

Plan ejecutado:

1. registrar Git y preservar los dos documentos sin seguimiento;
2. crear migración 008 y modelos/contratos;
3. implementar servicio transaccional, dependencia dual y endpoints;
4. implementar CSRF/Origin, configuración fail-closed y recuperación admin;
5. migrar frontend fuera de `localStorage`;
6. probar 008 y reglas en bases aisladas;
7. ejecutar regresión completa, lint y build;
8. respaldar, detener escritores, aplicar 008 y 009 y reiniciar;
9. verificar esquema, triggers, salud y OpenAPI;
10. actualizar documentación y continuidad.

Pendiente: E2E detrás de TLS, inventario/contracción bearer y aceptación
funcional de usuarios.

## 9. **Cambios realizados**

| Archivo o componente | Cambio | Justificación |
| --- | --- | --- |
| `backend/db/migrations/008_corte4_autenticacion_formal.sql` | Tablas, constraints, triggers, redacción y revocación por baja. | Integridad y auditoría en PostgreSQL. |
| `backend/db/migrations/009_corte4_auditoria_sistema_sesion.sql` | Excepción DB estricta para expiración automática sin actor y sin cambios colaterales. | Evitar atribución falsa sin debilitar la integridad. |
| `backend/app/config.py` | Config auth validada por ambiente. | Producción falla cerrado. |
| `backend/app/models.py` | ORM de sesión, evento y estado. | Paridad de datos. |
| `backend/app/schemas.py` | Contratos auth y política de contraseña. | No exponer tokens; validar entradas. |
| `backend/app/services/authentication.py` | Login, bloqueo, sesión, expiración, eventos y revocación. | Atomicidad y concurrencia. |
| `backend/app/auth.py` | Dependencia cookie con bearer transitorio. | Migración compatible. |
| `backend/app/routers/authentication.py` | Sesión/logout/desbloqueo/revocación. | API formal separada. |
| `backend/app/main.py` | Router, CORS exacto y guard CSRF. | Protección global de escrituras cookie. |
| `frontend/src/api/axios.js` | Cookies/CSRF; retira bearer local. | Evitar token accesible a JavaScript. |
| `frontend/src/contexts/AuthContext.jsx` | Bootstrap servidor y logout real. | Estado confiable y revocación. |
| `backend/scripts/create_admin.py` | Sólo desactiva trigger de auditoría inicial. | Mantener integridad/estado auth. |
| `backend/scripts/unlock_admin.py` | Recuperación auditable. | Evitar bloqueo irreversible del único admin. |
| `backend/tests/*` | Sin fallback y siete pruebas Corte 4. | Suite aislada y reglas críticas. |
| Compose, `.env.example`, README y migraciones | Configuración/runbook. | Despliegue reproducible sin secretos. |

No se hizo commit ni push.

## 10. **Migraciones y compatibilidad**

- Backup activo: `backups/software-pa-db_trenes_pre_008_20260805.dump`, formato
  custom válido y modo `0600`.
- Backup correctivo: `backups/software-pa-db_trenes_pre_009_20260805.dump`,
  formato custom válido y modo `0600`.
- Backend y scheduler se detuvieron; se verificaron cero transacciones activas.
- 008 y 009 se aplicaron con `ON_ERROR_STOP=1` y `COMMIT`.
- La base activa registra 004, 005, 006, 007, 008 y 009.
- El usuario existente recibió estado cero; no se crearon sesiones/eventos
  históricos ni se infirieron relaciones.
- JWT existentes no se convierten. Bearer continúa durante la expansión.
- Las bases temporales de validación se eliminaron al terminar; ambos respaldos
  activos se conservan para recuperación.

## 11. **Pruebas y validaciones**

| Validación | Comando | Resultado | Estado |
| --- | --- | --- | --- |
| Sintaxis Python | `python3 -m compileall` con pycache en `/tmp` | Sin errores. | Aprobada |
| Auth Corte 4 | `pytest -q tests/test_auth_corte4.py` en DB aislada | 7 aprobadas dentro de la ejecución completa. | Aprobada |
| Regresión backend | `pytest -q` en DB aislada | 117 aprobadas, 1 warning Starlette. | Aprobada |
| Frontend lint | `npm run lint` | Sin errores. | Aprobada |
| Frontend build | `npx vite build --outDir /tmp/...` | Build correcto, 165 módulos. | Aprobada |
| Build estándar | `npm run build` | No pudo limpiar `frontend/dist` por propiedad previa del contenedor. | Limitación de entorno, código validado en `/tmp` |
| Compose | `docker compose config --quiet` y merge prod | Válido; producción conserva variables y fuerza Secure. | Aprobada |
| Migraciones aisladas | `psql -v ON_ERROR_STOP=1 < 008...sql` y `< 009...sql` | COMMIT desde sus predecesoras. | Aprobada |
| Quinto fallo concurrente | 5 TestClient paralelos | Cinco 401, contador 5, un evento `quinto_fallo`. | Aprobada |
| Integridad DB | UPDATE directo sin evento | PostgreSQL lo rechazó. | Aprobada |
| Expiración DB adversarial | Evento correlacionado + cambio colateral de `token_hash` | PostgreSQL lo rechazó; la expiración normal quedó sin actor y sin bitácora falsa. | Aprobada |
| Auditoría sensible | Consulta agregada | 0 filas con hashes de contraseña/sesión/CSRF. | Aprobada |
| Bootstrap primero | Script en DB vacía + consulta | 1 usuario, 1 estado, trigger audit activo. | Aprobada |
| Estado activo | SQL y Docker health | 009, 1 estado, 0 sesiones/eventos iniciales; servicios healthy. | Aprobada |
| OpenAPI | GET local y búsqueda de paths | Seis rutas nuevas presentes. | Aprobada |
| E2E HTTPS/navegadores | No disponible en repositorio/entorno. | Pendiente. | No ejecutada |

## 12. **Riesgos restantes**

- Bearer JWT continúa aceptado hasta inventariar consumidores y contraer.
- Falta validar cookie `Secure` y origen detrás del terminador TLS real.
- Cada request cookie genera una actualización auditada; medir crecimiento y
  contención con carga real de 50 usuarios.
- Bloqueo por cuenta puede usarse para denegación de servicio; se mitiga con
  desbloqueo admin, expiración 15 minutos y CLI de recuperación.
- El rol DB sigue siendo superusuario; corregirlo en trabajo separado.
- El contenedor frontend heredado publicado en `0.0.0.0:5173` no pertenece al
  Compose actual y debe revisarse operativamente fuera de este alcance.

## 13. **Actualización realizada en `ESTADO_PROYECTO.md`**

Se actualizó únicamente con hechos verificados:

- fecha y siguiente paso;
- rotación local reportada, sin valores;
- historial y aplicación de 008 y 009;
- reglas de autenticación implementadas;
- 117 pruebas, lint/build y estado activo;
- pendientes de TLS/E2E y contracción bearer.

Corte 4 figura como incremento principal implementado, no como terminado.

## 14. **Estado final**

**Implementación parcial.**

Los hallazgos críticos quedaron corregidos y el incremento expansivo está
implementado, migrado y validado. El estado no es “completo” porque bearer
sigue activo por compatibilidad y faltan validación HTTPS/E2E y aceptación
funcional en el ambiente real.
