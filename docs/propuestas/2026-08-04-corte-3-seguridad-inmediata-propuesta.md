# Propuesta técnica - Corte 3: Seguridad inmediata

Fecha: 2026-08-04

## 1. **Trabajo vigente identificado**

`ESTADO_PROYECTO.md` mantiene como siguiente paso operativo la validacion
funcional del Subcorte 2C, pero el usuario informa en esta conversacion que
dicha implementacion ya fue validada y aprobada. Con ese hecho nuevo, el
siguiente trabajo vigente del plan principal es el **Corte 3 - Seguridad
inmediata**, cuyo estado documentado es parcial.

Alcance vigente tomado de `ESTADO_PROYECTO.md`:

1. Rotar credenciales y `SECRET_KEY` que ya estuvieron en commits.
2. Crear el `.env` local de cada entorno y documentar configuracion y
   recuperacion.
3. No copiar credenciales actuales a documentacion nueva.

Este corte no debe absorber el Corte 4 completo. La autenticacion formal
permanece pendiente como trabajo posterior: reemplazo de JWT en `localStorage`,
cookie HttpOnly o estrategia equivalente, sesiones, revocacion, logout real,
registro de accesos exitosos/fallidos, bloqueo por cinco intentos, expiracion
e inactividad y pruebas de autenticacion/autorizacion. Sin embargo, esta
propuesta define una frontera incremental para no dejar el Corte 3 como un
procedimiento manual fragil.

## 2. **Estado actual verificado**

Documentos consultados en el orden indicado por `ESTADO_PROYECTO.md`:

- `ESTADO_PROYECTO.md`
- `docs/Descripción proceso.md`
- `docs/Flujo liberacion derechos.md`
- `docs/Estructura Datos.md`
- `docs/Diccionario_Datos_SSALFER.md`
- `docs/requirements.md`
- Migraciones `001` a `007`
- `docs/propuestas/2026-07-31-subcorte-2a-propuesta.md`
- `docs/design.md`
- `docs/historico/Adaptaciones 2.0 - Implementación.md`, solo como registro
  historico cuando fue necesario contrastar Adaptaciones 2.0.

Estado verificado por capa:

| Capa | Estado |
| --- | --- |
| Modelo de datos | `usuario` contiene `correo`, `contrasena_hash`, `rol`, `activo`, `fecha_alta` y ciclo de vida. No contiene campos de bloqueo, contador de intentos, cambio obligatorio de contrasena ni version de secreto. `bitacora` existe para auditoria forense de escrituras de dominio. No existe tabla de sesiones ni tabla explicita de eventos de acceso. |
| Migraciones | `001` crea `usuario`, `usuario_tramo` y `bitacora`; `002` corrige auditoria; `003` migra a Proyecto y `usuario_tramo`; `004` a `007` conservan el patron de auditoria con `SET LOCAL app.current_user_id`. Ninguna migracion vigente agrega controles de sesion, revocacion o bloqueo de login. |
| ORM | `backend/app/models.py` refleja el modelo actual de `Usuario` sin metadatos de seguridad operativa adicionales. No hay modelo `SesionUsuario`, `EventoAcceso` ni equivalente. |
| Contratos | `schemas.Token` devuelve `access_token`, `token_type` y `user`. `UsuarioCreate` acepta contrasena en claro para hash en backend, sin reglas Pydantic de longitud o complejidad visibles. `UsuarioUpdate` no permite modificar `activo`, lo cual conserva baja logica por endpoint dedicado. |
| Servicios | `backend/app/auth.py` usa bcrypt, JWT HS256, expiracion de 30 minutos y `SECRET_KEY` obligatoria por entorno. `RoleChecker` valida solo rol. La pertenencia territorial se implementa en `services/access.py` y se usa de forma amplia en recursos operativos. |
| Endpoints | `/api/auth/login` valida usuario/contrasena y devuelve bearer token. No registra intento exitoso/fallido, no bloquea usuario, no crea sesion revocable y distingue `Usuario inactivo` con `400`. `/api/usuarios` es admin-only y auditable. No existe `/api/auth/logout`, `/api/auth/me`, `/api/auth/refresh` ni endpoint de revocacion. |
| Autorizacion | Hay RBAC por roles y filtro territorial por `usuario_tramo`. El rol `geografo` aun aparece en varias escrituras no estrictamente geoespaciales heredadas; esto ya fue identificado en evaluaciones previas, pero no es el alcance minimo del Corte 3 salvo que afecte gestion de secretos/sesiones. |
| Frontend | `frontend/src/contexts/AuthContext.jsx` y `frontend/src/api/axios.js` guardan token y usuario en `localStorage`, anexan `Authorization: Bearer` y hacen logout solo local. Este punto pertenece formalmente al Corte 4, pero condiciona la mitigacion de secretos porque un JWT robado no se puede revocar hoy. |
| Docker/configuracion | `docker-compose.yml` exige `DB_USER`, `DB_PASSWORD`, `SECRET_KEY` y credenciales de PgAdmin mediante `.env`; publica puertos en `127.0.0.1`. `.env.example` usa placeholders `change_me`. `README.md` y `docs/migraciones.md` ya documentan creacion de `.env` y rotacion de password de PostgreSQL en volumen existente. |
| Bootstrap/seed | `backend/scripts/create_admin.py` crea una cuenta admin de desarrollo con credenciales fijas y deshabilita triggers de `usuario` temporalmente. `backend/db/seed.sql` tambien incluye el usuario admin y un hash conocido. El README advierte revisar y sustituir credenciales antes de usar el script en entornos compartidos, pero el repositorio todavia contiene credenciales de desarrollo funcionales. |
| Pruebas | `backend/tests/test_auth.py` cubre login valido/invalido, rutas protegidas y token invalido. `conftest.py` depende de credenciales fijas de desarrollo. No hay pruebas para rotacion de secretos, bloqueo por intentos, logout real, cookies, revocacion ni auditoria de login. |

## 3. **Reglas funcionales confirmadas**

1. El sistema debe autenticar antes de otorgar acceso.
2. Los roles vigentes son `admin`, `operador`, `visualizador` y `geografo`.
3. La pertenencia territorial se controla por `usuario_tramo`; no se debe
   confiar en IDs enviados por cliente.
4. Toda escritura auditable debe ejecutar `set_audit_context(db,
   current_user.id_usuario)` antes del `commit`.
5. No se debe exponer `str(exc)`, secretos ni errores internos al cliente.
6. Los passwords deben almacenarse como hash, no en claro.
7. `SECRET_KEY`, password de PostgreSQL y password de PgAdmin deben provenir
   del entorno, no del repositorio.
8. `.env` debe permanecer ignorado por Git y cada ambiente debe tener valores
   propios.
9. La rotacion de password de PostgreSQL en un volumen existente requiere
   cambiar el rol dentro de PostgreSQL y despues actualizar `.env`; editar
   `POSTGRES_PASSWORD` no cambia una base ya inicializada.
10. El Corte 3 no debe reimplementar el flujo 2A/2B/2C ni alterar reglas de
    dominio de propiedad social.

## 4. **Hallazgos y contradicciones**

| ID | Hallazgo | Severidad | Estado |
| --- | --- | --- | --- |
| S3-01 | `create_admin.py` contiene credenciales de desarrollo reales y puede crear una cuenta insegura en entornos compartidos. | Alta | Pendiente |
| S3-02 | `seed.sql` contiene un usuario admin y hash conocido. Aunque sea semilla, puede habilitar acceso predecible si se usa fuera de pruebas. | Alta | Pendiente |
| S3-03 | No hay procedimiento completo para rotar `SECRET_KEY`: al cambiarla se invalidan tokens existentes, pero no hay checklist por ambiente ni verificacion posterior. | Alta | Pendiente |
| S3-04 | No existe mecanismo de revocacion de tokens ni logout servidor. Esto esta en Corte 4, pero deja a Corte 3 con mitigacion parcial si algun JWT fue expuesto. | Media | Pendiente por Corte 4 |
| S3-05 | Login no registra accesos exitosos/fallidos ni bloquea tras cinco intentos, contradiciendo RNF-10. | Media | Pendiente por Corte 4 |
| S3-06 | `localStorage` conserva JWT accesible a JavaScript, contradiciendo el objetivo futuro de `docs/design.md` y lo pendiente en Corte 4. | Media | Pendiente por Corte 4 |
| S3-07 | `UsuarioCreate.contrasena` no muestra validacion de longitud/complejidad en Pydantic; bcrypt protege almacenamiento, no calidad de secreto. | Media | Proponer ahora o diferir con Corte 4 |
| S3-08 | Algunas escrituras siguen permitiendo rol `geografo` fuera de operaciones puramente geoespaciales heredadas. | Media | Fuera del minimo Corte 3, revisar en matriz de autorizacion |
| S3-09 | `bitacora` guarda escrituras de dominio, pero no eventos de autenticacion ni IP/user-agent porque la auditoria actual depende de filas operativas con trigger. | Media | Pendiente por Corte 4 o subcorte 3B |
| S3-10 | Las pruebas de autenticacion dependen de credenciales fijas conocidas. Cambiar bootstrap sin adaptar fixtures romperia la suite. | Media | Requiere transicion compatible |

Contradicciones o tensiones:

- `ESTADO_PROYECTO.md` ubica logout real, sesiones, bloqueo e intentos en
  Corte 4, pero tambien exige rotar secretos expuestos en Corte 3. La rotacion
  de `SECRET_KEY` invalida JWT por efecto criptografico, pero no equivale a
  una estrategia de sesion revocable.
- `README.md` dice que las credenciales no se documentan en el repositorio,
  pero `create_admin.py`, `seed.sql` y tests contienen credenciales de
  desarrollo. Deben quedar confinadas a pruebas locales o reemplazarse por
  variables obligatorias.
- La auditoria forense existente protege escrituras de datos, pero el login
  fallido no modifica una entidad operativa y por tanto no queda registrado.

## 5. **Diseño propuesto**

> Corrección posterior a auditoría técnica: el alcance implementable sin una
> aprobación adicional es únicamente el Subcorte 3A de repositorio: eliminar
> credenciales fijas de bootstrap, rechazar placeholders de `SECRET_KEY`,
> separar datos semilla de credenciales operativas, adaptar pruebas y
> documentar la rotación. La rotación real de secretos por ambiente requiere
> custodia y valores externos al repositorio; debe ejecutarse operativamente y
> no puede declararse completada por un cambio de código. El Subcorte 3B queda
> diferido al Corte 4 salvo aprobación explícita.

Dividir el Corte 3 en dos subcortes incrementales:

### Subcorte 3A - Rotacion y bootstrap seguro

Objetivo: retirar credenciales funcionales del flujo de instalacion,
estandarizar rotacion por ambiente y dejar verificable que ningun servicio
arranca con secretos placeholder.

Comportamiento esperado:

1. Cada ambiente define `DB_PASSWORD`, `SECRET_KEY`,
   `PGADMIN_DEFAULT_PASSWORD` y credenciales iniciales de administrador fuera
   de Git.
2. `create_admin.py` no contiene password fijo. Lee variables obligatorias en
   modo compartido o permite prompt interactivo sin eco cuando se ejecuta
   manualmente.
3. Una instalacion nueva puede crear el primer admin sin desactivar auditoria
   de forma permanente ni dejar credenciales conocidas.
4. Las pruebas conservan un camino controlado para crear fixtures de usuario,
   idealmente con helper de test o variables de test, no con secreto operativo.
5. La documentacion indica como rotar `SECRET_KEY`, password del rol
   PostgreSQL, PgAdmin y cuenta admin sin revelar valores.
6. Despues de rotar `SECRET_KEY`, se asume cierre global de sesiones JWT
   existentes; usuarios deben autenticarse de nuevo.

### Subcorte 3B - Preparacion minima para autenticacion formal

Estado tras auditoría: **diferido / pendiente de aprobación**. No forma parte
de la implementación inicial del Corte 3 porque introduce decisiones propias
del Corte 4: política formal de contraseñas, metadatos de bloqueo, endpoints
de sesión y transición del frontend.

Objetivo: agregar las piezas pequenas que reducen riesgo inmediato sin
adelantar todo el Corte 4.

Comportamiento esperado:

1. Validar politicas minimas de contrasena al crear o cambiar usuarios:
   longitud minima, mayuscula, minuscula, numero y simbolo, sin devolver
   detalles internos.
2. Agregar endpoint `/api/auth/me` para que el frontend valide el usuario
   actual contra servidor, evitando confiar solo en `localStorage.user`.
3. Agregar endpoint `/api/auth/logout` inicialmente idempotente. En 3A/3B
   puede devolver exito y limpiar cliente; en Corte 4 se conectara a
   revocacion real.
4. Preparar, si se aprueba, migracion expansiva para metadatos de seguridad en
   `usuario`: `ultimo_acceso_at`, `intentos_fallidos`, `bloqueado_hasta`,
   `password_cambiado_at`, `requiere_cambio_contrasena`. Estos campos son
   compatibles aunque Corte 4 implemente sesiones posteriormente.

Estados y transiciones propuestas para usuario:

```text
activo
  -> requiere_cambio_contrasena
  -> bloqueado_temporalmente
  -> activo
  -> inactivo (baja logica existente)
```

Reglas de negocio:

1. `activo = false` sigue siendo baja logica y no debe confundirse con bloqueo
   temporal.
2. Bloqueo temporal no elimina asignaciones territoriales.
3. Un admin puede desbloquear y forzar cambio de contrasena, siempre auditado.
4. Password temporal generado o capturado para un usuario debe marcar
   `requiere_cambio_contrasena = true`.
5. Un usuario no puede autenticarse si esta inactivo o bloqueado.
6. Los mensajes de login deben ser genericos para usuario inexistente,
   password incorrecto, inactivo o bloqueado, salvo que se apruebe un mensaje
   funcional distinto.

## 6. **Cambios por capa**

| Archivo o componente | Problema | Solucion | Justificacion | Dependencias | Riesgo | Validacion |
| --- | --- | --- | --- | --- | --- | --- |
| `backend/scripts/create_admin.py` | Password fijo y correo fijo de desarrollo. Deshabilita triggers para resolver bootstrap. | Leer `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NOMBRE`, `ADMIN_APELLIDO` desde entorno o pedir password interactivo. Rechazar placeholders y passwords debiles. Establecer `fecha_alta` con zona. Mantener ruta especial solo para primer usuario, documentada. | Evita crear credenciales conocidas y mantiene instalacion repetible. | Politica de password y documentacion. | Romper instalaciones locales que dependen del default. | Test/script manual en base limpia; verificar que sin variables falle con mensaje seguro; verificar admin creado y login exitoso. |
| `backend/db/seed.sql` | Inserta admin con hash conocido. | Retirar usuario admin del seed operativo o moverlo a fixture de pruebas claramente no operativo. Semillas de catalogo deben quedar separadas de credenciales. | Reduce riesgo de acceso predecible. | Ajustar docs y tests que dependan de ese usuario. | Usuarios locales deberan crear admin por script. | Base nueva con `001` + create_admin + migraciones; test de que seed no crea usuarios si se define asi. |
| `.env.example` | Placeholders correctos, pero no contempla credenciales bootstrap ni validacion de placeholders. | Agregar variables opcionales/obligatorias para bootstrap admin y comentario de no usar defaults. Mantener solo placeholders. | Hace reproducible una instalacion segura. | `create_admin.py`. | Confusion si se mezclan variables temporales con operacion diaria. | `docker compose config --quiet`; documentacion revisada sin secretos. |
| `README.md` | Ya advierte revisar `create_admin.py`, pero queda una instruccion manual debil. | Sustituir advertencia por procedimiento exacto de bootstrap seguro y rotacion posterior. | Baja probabilidad de error humano. | Cambios en script. | Documentacion desactualizada si se implementa parcialmente. | Revision de comandos en ambiente limpio. |
| `docs/migraciones.md` | Documenta rotacion DB, no rotacion completa de secretos. | Agregar seccion "Rotacion de secretos por ambiente": respaldo, cambio de password PostgreSQL, cambio de `.env`, recreacion de servicios, rotacion `SECRET_KEY`, verificacion de 401 para token viejo y login nuevo. | Cumple Corte 3 sin revelar secretos. | Acceso operativo a cada ambiente. | Cambiar `SECRET_KEY` corta sesiones existentes. | Checklist ejecutado por ambiente; logs sin errores. |
| `backend/app/auth.py` | JWT stateless sin version/revocacion; validacion actual no contempla bloqueo. | En 3A mantener; en 3B agregar validacion de campos de bloqueo si se aprueba migracion. No implementar cookie HttpOnly aun salvo decision de adelantar Corte 4. | Mantiene alcance incremental. | Migracion 008 si hay campos nuevos. | Doble trabajo si Corte 4 cambia estrategia por completo. | Tests de login activo/inactivo/bloqueado. |
| `backend/app/main.py` `/api/auth/login` | No registra intentos ni usa mensajes plenamente uniformes. | Para 3A solo no tocar salvo bootstrap. Para 3B envolver en servicio `auth_service.login`, actualizar contadores si hay campos, usar errores genericos. | Reduce logica en controlador y prepara Corte 4. | Modelo/migracion de metadatos. | Cambiar respuestas que tests esperan. | Tests de 401 generico, contador y bloqueo. |
| `backend/app/main.py` `/api/auth/me`, `/api/auth/logout` | Frontend confia en estado local; no hay endpoint de cierre. | Agregar `GET /api/auth/me` protegido y `POST /api/auth/logout` idempotente. Logout real quedara en Corte 4 si no hay tabla de sesiones. | Mejora consistencia sin redisenar autenticacion. | Frontend AuthContext. | Falsa percepcion de revocacion si se comunica mal. | Tests 200 con token, 401 sin token, logout idempotente. |
| `backend/app/schemas.py` | `UsuarioCreate.contrasena` no explicita politica. | Agregar validador Pydantic o funcion de dominio para contrasenas. | Evita nuevos usuarios debiles tras rotacion. | Aprobacion de politica minima. | Puede bloquear passwords actuales solo al cambiarlos, no al leerlos. | Tests de passwords invalidos/validos. |
| `backend/app/models.py` `Usuario` | No hay metadatos para bloqueo/cambio de password. | Migracion expansiva nullable/default compatible y columnas ORM si se aprueba 3B. | Prepara RNF-9/RNF-10 sin tabla de sesiones aun. | Migracion 008. | Campo `intentos_fallidos` puede no ser suficiente para auditoria forense completa. | Inspeccion de columnas; tests de transicion. |
| `frontend/src/contexts/AuthContext.jsx` | Persiste `user` y token en `localStorage`; logout solo local. | En 3B consultar `/auth/me` al iniciar y usar `/auth/logout` al cerrar. Mantener token en `localStorage` hasta Corte 4 si no se aprueba cookie. | Evita mostrar usuario obsoleto y reduce confusion. | Endpoints nuevos. | Sigue expuesto a XSS hasta Corte 4. | Pruebas manuales: reload con token valido/invalido; logout redirige. |
| `frontend/src/api/axios.js` | Authorization desde `localStorage`. | Sin cambio en 3A. En 3B conservar interceptor pero centralizar limpieza y preparar `withCredentials` para Corte 4 si se aprueba. | Mantiene compatibilidad. | Estrategia Corte 4. | Cambio prematuro podria romper API actual. | Oxlint y smoke test de login/rutas protegidas. |
| `backend/tests/test_auth.py` y `conftest.py` | Dependen de credenciales fijas. | Crear fixture de admin via helper seguro o variables de test; adaptar expectativas de errores genericos y nuevos endpoints. | Permite retirar secretos de bootstrap. | Script/servicio de creacion de usuario. | Fragilidad si tests corren contra BD compartida. | Suite backend completa. |
| Docker/operacion | Servicios ya reciben secretos por env, pero no hay validacion de placeholder en runtime. | Agregar validacion backend para rechazar `SECRET_KEY` placeholder y, opcionalmente, check de longitud minima. | Evita arranque inseguro accidental. | `auth.py` o modulo config. | Locales con `.env` no actualizado fallaran al arrancar. | Test unitario de config; `docker compose up` con placeholder debe fallar claramente. |

## 7. **Migración y compatibilidad**

Subcorte 3A no requiere migracion de base si se limita a rotar secretos,
bootstrap y documentacion.

Si se aprueba Subcorte 3B con metadatos de seguridad, crear migracion
expansiva `008_corte_3_seguridad_inmediata.sql`:

```sql
ALTER TABLE usuario
  ADD COLUMN IF NOT EXISTS ultimo_acceso_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS intentos_fallidos INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS bloqueado_hasta TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS password_cambiado_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS requiere_cambio_contrasena BOOLEAN NOT NULL DEFAULT FALSE;
```

Restricciones sugeridas:

```sql
ALTER TABLE usuario
  ADD CONSTRAINT chk_usuario_intentos_fallidos_no_negativo
  CHECK (intentos_fallidos >= 0);
```

Compatibilidad:

1. Usuarios existentes siguen activos, sin bloqueo y sin requerir cambio hasta
   que el admin lo marque.
2. Tokens firmados con `SECRET_KEY` anterior quedan invalidos al rotar la
   clave; el comportamiento esperado es nuevo login.
3. No se eliminan columnas ni tablas existentes.
4. La migracion debe usar `schema_migrations`, `ON_ERROR_STOP=1`, respaldo
   previo, transaccion unica y actor tecnico de auditoria si dispara triggers.
5. No se modifica `bitacora`; si se requieren eventos de acceso detallados, se
   recomienda tabla nueva en Corte 4 para no sobrecargar auditoria de dominio.

## 8. **Seguridad, autorización e integridad**

Seguridad:

- Rechazar secretos placeholder o demasiado cortos al arrancar backend.
- Rotar `SECRET_KEY` por ambiente y registrar fecha operativa fuera del repo.
- Rotar password del rol PostgreSQL dentro de la base y despues en `.env`.
- Rotar password de PgAdmin y revisar usuarios guardados dentro de PgAdmin si
  aplica.
- Reemplazar credenciales iniciales conocidas por bootstrap seguro.
- No registrar passwords, tokens ni secretos en logs.
- Mantener respuestas genericas en login.

Autorizacion:

- La gestion de usuarios y asignaciones `usuario_tramo` sigue siendo
  exclusiva de `admin`.
- La rotacion de password de una cuenta operativa debe ser accion admin
  auditable o flujo de cambio propio autenticado.
- No se debe relajar RBAC ni pertenencia territorial ya implementada.

Integridad:

- Cualquier cambio en `usuario` debe conservar auditoria con
  `set_audit_context`.
- Bloqueo temporal e inactividad son estados distintos.
- No hacer baja fisica de usuarios ni asignaciones.
- No modificar datos operativos de expedientes durante rotacion de secretos.

Auditoria:

- En 3A, documentar evidencia externa de rotacion: fecha, ambiente, operador,
  servicios recreados y validaciones, sin incluir valores.
- En 3B, si se agregan campos a `usuario`, sus cambios quedaran en
  `bitacora` por trigger existente.
- Los eventos de login exitoso/fallido requieren decision: usar una tabla
  `evento_acceso` nueva en Corte 4 o insertar eventos especiales en
  `bitacora`. Se recomienda tabla separada porque `bitacora` exige
  `id_usuario`, y un login fallido puede no tener usuario valido.

## 9. **Plan incremental de implementación**

1. Preparacion sin codigo:
   - Inventariar ambientes: local, pruebas, servidor y cualquier copia.
   - Confirmar quien custodia secretos por ambiente.
   - Hacer respaldo de bases compartidas antes de rotar DB.

2. Subcorte 3A:
   - Cambiar `create_admin.py` para eliminar credenciales fijas.
   - Separar semilla operativa de semilla de pruebas, retirando admin conocido
     de rutas de instalacion.
   - Validar `SECRET_KEY` contra placeholders y longitud minima.
   - Actualizar `README.md`, `.env.example` y `docs/migraciones.md` con
     bootstrap y rotacion.
   - Adaptar fixtures de pruebas.
   - Ejecutar suite backend, oxlint y build frontend.
   - Rotar secretos reales ambiente por ambiente siguiendo checklist.

3. Validacion de 3A:
   - Token viejo devuelve 401 despues de rotar `SECRET_KEY`.
   - Login nuevo funciona con credenciales rotadas.
   - PostgreSQL acepta conexion con password nuevo y rechaza el anterior
     cuando sea verificable sin exponerlo.
   - No aparecen secretos en Git, docs ni logs.

4. Decision de alcance 3B:
   - Aprobar o diferir metadatos de usuario, `/auth/me`, `/auth/logout` y
     politica de password.
   - Si se aprueba, crear migracion 008 expansiva y endpoints minimos.
   - Si se difiere, registrar como entrada directa del Corte 4.

5. Cierre:
   - Revisar diff.
   - Confirmar que no se tocaron reglas de 2A/2B/2C.
   - Actualizar `ESTADO_PROYECTO.md` solo despues de implementacion validada.

## 10. **Matriz de pruebas**

| Prueba | Capa | Objetivo |
| --- | --- | --- |
| Backend arranca sin `SECRET_KEY` | Config | Debe fallar con mensaje seguro ya existente. |
| Backend rechaza `SECRET_KEY` placeholder | Config | Evitar despliegues con `.env.example` sin editar. |
| `create_admin.py` sin variables en modo no interactivo | Script | Debe fallar sin crear usuario inseguro. |
| `create_admin.py` con variables validas | Script/API/DB | Debe crear admin con hash bcrypt y permitir login. |
| Password debil en creacion de usuario | API | Debe devolver 400/422 sin crear usuario. |
| Password fuerte en creacion de usuario | API/DB | Debe crear usuario auditable y sin guardar texto plano. |
| Login con credenciales correctas | API | Debe devolver token o cookie segun alcance aprobado. |
| Login con credenciales incorrectas | API | Debe devolver error generico y no filtrar existencia. |
| Usuario inactivo | API | Debe impedir login. |
| Token firmado con `SECRET_KEY` anterior | API | Debe devolver 401 tras rotacion. |
| Rutas protegidas sin token | API | Deben seguir devolviendo 401. |
| Rutas admin-only con operador | API | Deben seguir devolviendo 403. |
| Usuario sin `usuario_tramo` | API | No debe acceder a recursos territoriales ajenos. |
| `/api/auth/me` con token valido | API | Debe devolver usuario actual sin campos sensibles, si se aprueba 3B. |
| `/api/auth/logout` | API/Frontend | Debe ser idempotente; en 3B limpia cliente, en Corte 4 revoca sesion. |
| Reload frontend con token invalido | Frontend | Debe limpiar estado local y redirigir a login. |
| Oxlint | Frontend | Cero errores y advertencias. |
| Build frontend | Frontend | Build de produccion exitoso. |
| Suite backend completa | Backend/DB | No regresion de 2A/2B/2C ni autorizacion territorial. |
| Revision de secretos | Repo | `rg` no debe encontrar passwords operativos ni secretos reales. |

## 11. **Riesgos y mitigaciones**

| Riesgo | Mitigacion |
| --- | --- |
| Rotar `SECRET_KEY` cerrara sesiones JWT existentes. | Ejecutarlo en ventana comunicada; comportamiento esperado es re-login. |
| Cambiar `DB_PASSWORD` solo en `.env` no cambia el volumen PostgreSQL. | Seguir `docs/migraciones.md`: `\password`, actualizar `.env`, recrear servicios. |
| Retirar credenciales fijas rompe pruebas. | Adaptar fixtures para crear usuarios de prueba con helper seguro. |
| Confundir Corte 3 con Corte 4 y redisenar auth completa. | Mantener 3A como obligatorio y 3B sujeto a aprobacion explicita. |
| Bloqueo por intentos sin tabla de eventos dificulta auditoria. | Si se implementa bloqueo, registrar cambios en `usuario`; para eventos detallados usar tabla separada en Corte 4. |
| Usuarios locales quedan sin admin tras cambiar bootstrap. | Documentar recuperacion controlada y script idempotente para primer admin. |
| Logs pueden capturar variables o tokens accidentalmente. | No imprimir secretos; revisar comandos y scripts antes de ejecutar en servidor. |
| Diferencias entre ambientes. | Checklist por ambiente con version de migraciones, respaldo y validaciones. |

## 12. **Criterios de aceptación**

Subcorte 3A:

1. No existe password operativo fijo en `create_admin.py`.
2. `seed.sql` no crea una cuenta admin con credenciales conocidas en rutas
   operativas, o queda explicitamente segregado como fixture no desplegable.
3. `.env.example` contiene solo placeholders y documenta variables de
   bootstrap sin valores reales.
4. `README.md` y `docs/migraciones.md` documentan rotacion completa sin
   secretos.
5. Backend rechaza ausencia de `SECRET_KEY` y placeholders obvios.
6. Se pueden crear admin y hacer login en una base limpia con credenciales
   provistas por entorno o prompt.
7. Tests backend pasan sin depender de credenciales operativas fijas.
8. No se modifica flujo 2A/2B/2C.
9. No se ejecutan bajas fisicas ni cambios destructivos.
10. Revision del repositorio no muestra secretos reales nuevos.

Subcorte 3B, si se aprueba:

1. `GET /api/auth/me` devuelve usuario autenticado sin `contrasena_hash`.
2. `POST /api/auth/logout` existe y es idempotente.
3. La politica minima de contrasena se aplica a usuarios nuevos y cambios de
   contrasena.
4. Si se agregan campos de bloqueo, la migracion es expansiva, reejecutable en
   preflight y registrada en `schema_migrations`.
5. Login no revela si el correo existe.
6. Cambios en `usuario` quedan auditados.

## 13. **Actualizaciones previstas para `ESTADO_PROYECTO.md`**

Despues de una implementacion validada, actualizar:

1. Encabezado:
   - `Última actualización`.
   - `Proximo trabajo funcional`.
2. Seccion 6, `Trabajo realizado`:
   - Agregar "Corte 3 - Seguridad inmediata" con alcance implementado,
     validaciones y evidencia.
3. Seccion 8:
   - Cambiar Corte 3 de `parcial` a `terminado` o `parcial con 3A terminado`,
     segun decision de 3B.
   - Mantener Corte 4 como pendiente si no se implementan sesiones/cookies.
4. Seccion 9:
   - Tachar rotacion de secretos solo despues de completarla en todos los
     ambientes objetivo.
   - Agregar pendientes residuales si queda 3B o Corte 4.
5. Seccion 10:
   - Reemplazar el paso de 2C por el siguiente trabajo real: Corte 4 o Corte 5,
     segun aprobacion.

No actualizar `ESTADO_PROYECTO.md` antes de implementar, probar y validar.

## 14. **Decisiones que requieren aprobación**

1. Confirmar si el Corte 3 debe cerrarse solo con rotacion/bootstrap seguro
   (3A) o si tambien se aprueba 3B.
2. Definir politica minima de contrasena: longitud, complejidad y si se exige
   cambio al primer login para cuentas creadas por admin.
3. Decidir si `seed.sql` debe eliminar por completo la creacion de admin o si
   se conserva en un archivo exclusivo de pruebas no usado por despliegue.
4. Aprobar si se crea migracion 008 con metadatos de bloqueo en `usuario`.
5. Decidir donde registrar eventos de acceso: tabla nueva `evento_acceso` en
   Corte 4 o extension controlada de `bitacora`.
6. Definir custodio y procedimiento operativo para secretos por ambiente.
7. Confirmar si se adelanta la sustitucion de `localStorage` a cookie HttpOnly
   en este corte o se mantiene estrictamente en Corte 4.
8. Confirmar si la matriz de permisos del rol `geografo` se corrige dentro de
   seguridad inmediata o se agenda como hardening posterior de autorizacion.
