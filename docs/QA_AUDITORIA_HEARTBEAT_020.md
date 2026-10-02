# QA: auditoría de actividad de sesión — migración 020

Fecha: 2026-10-01. Rama: `fix/auditoria-heartbeat-sesion`.

## Diagnóstico

Tras actualizar las referencias remotas, `origin/feature/backend-logica` sigue en
`cf07d7e`, con migraciones hasta 019. La rama de trabajo contiene esa referencia
más el commit previo `7809b96` del generador ERD; esos cambios previos no se editaron.

`authenticate_session()` establece `app.current_user_id`, actualiza
`sesion_usuario.ultima_actividad` y confirma la transacción. La función de
migración 011 elimina secretos de los snapshots pero conserva `ultima_actividad`;
por ello cada petición autenticada produce un UPDATE auditable.

Se comparó exactamente el cuerpo instalado de `fn_audit_log()` en la QA local
`software_pa_erd_019` con el de 011: son idénticos. Se verificaron también las
versiones y checksums instalados 001–019. La QA existente se consultó solamente.
La base local `software_pa_test` está en 023 y no se utilizó ni modificó.

## Cambio

`020_auditoria_heartbeat_sesion.sql` redefine únicamente `fn_audit_log()` mediante
`CREATE OR REPLACE FUNCTION`, partiendo del cuerpo de 011. Requiere 019 con su
checksum exacto y se registra mediante el runner oficial.

El único cambio dentro de la función es esta excepción, situada después de
validar el actor y antes de redactar los snapshots:

```sql
IF TG_TABLE_NAME = 'sesion_usuario'
   AND to_jsonb(OLD) - 'ultima_actividad'
       IS NOT DISTINCT FROM to_jsonb(NEW) - 'ultima_actividad' THEN
    RETURN NEW;
END IF;
```

La comparación incluye todos los demás campos, incluidos `token_hash` y
`csrf_hash`. Actividad más cambio de un secreto sigue generando auditoría con
snapshots redactados. Se conserva la supresión preexistente de cambios sólo de
secretos, siempre tras validar el actor.

La ruta especial de expiración permanece idéntica: exige evento correlacionado
por usuario, sesión, tipo, motivo, ausencia de actor y `txid_current()`, además de
restringir los campos modificados. Se mantienen `SECURITY DEFINER`, `search_path`,
redacción de `contrasena_hash`, `token_hash` y `csrf_hash`, y privilegios append-only.
No cambia la API ni el servicio de autenticación. No hay UPDATE, DELETE ni TRUNCATE
de bitácora en la migración.

## Archivos

- `backend/db/migrations/020_auditoria_heartbeat_sesion.sql`: corrección forward-only.
- `backend/tests/test_audit_api.py`: 18 casos nuevos y comprobación adicional de la auditoría de revocación administrativa.
- `backend/tests/test_auth_rbac.py`: `/health` debe reportar esquema 20.
- `docs/MIGRACIONES.md`: versión vigente 020, siguiente 021 e inventario con checksum.
- Este informe.

Las referencias 019 de fixtures y pruebas históricas permanecen: identifican
migraciones, contratos o ejemplos concretos. El diccionario describe estructuras
que esta corrección no altera.

## Aislamiento y pruebas

Se utilizaron contenedores PostgreSQL 15.4 / PostGIS 3.3 independientes, sin puertos
publicados y sin compartir volúmenes con las bases existentes. Dentro de cada uno,
la base se llama `software_pa_test` para respetar la protección de `conftest.py`.
Los runners backend efímeros utilizan el checkout montado como sólo lectura,
credenciales sintéticas fuera del repositorio, `APP_ENV=test`,
`TEST_ALLOW_DATABASE=software_pa_test` y un usuario runtime sin privilegios de owner.

Primera QA: `software-pa-heartbeat-qa-20261001`.
Segunda QA completa: `software-pa-heartbeat-qa-complete-20261001`.

La primera QA reprodujo el fallo de la regresión en 019: la primera petición
incrementó la bitácora de sesión. El runner verificó los checksums históricos y
aplicó 020. Una comparación MD5 del JSON ordenado de toda la bitácora confirmó
que el histórico no cambió antes/después de la migración. El cuerpo instalado en
020 también se comparó exactamente contra el archivo nuevo.

El grupo de auditoría, autenticación/RBAC, credenciales, administración de usuarios
y permisos runtime terminó con **50 aprobadas, 1 omitida** (la prueba preexistente
de último administrador exige sólo un admin activo).

Las regresiones verifican:

- Cinco GET autenticados consecutivos actualizan `ultima_actividad` estrictamente; la bitácora global, los snapshots históricos de sesión y los eventos de acceso permanecen iguales.
- Un UPDATE de actividad sin actor falla y deja el timestamp intacto.
- Actividad más cambios de expiración, agente de usuario, token, CSRF o revocación añade exactamente una fila de auditoría, sin exponer secretos.
- Expiración absoluta e inactividad producen 401, revocación y un único evento de sistema; no añaden auditoría de sesión ni duplican el evento al repetir la petición.
- Logout y revocación administrativa conservan sus filas de auditoría y eventos de acceso.
- Se rechazan eventos de expiración de otra transacción, sesión incorrecta, actor no nulo, tipo o motivo incorrectos, y cambios adicionales de actividad o secretos. Un heartbeat no puede aprovechar la ruta de sistema.
- Las pruebas existentes mantienen cambios de contraseña/correo, bloqueo, desbloqueo, redacción y permisos append-only.

La primera ejecución general dio **355 aprobadas, 4 fallidas, 1 omitida**. Los
fallos revelaron dependencias de preparación de QA: catálogo RAN con al menos
100 filas, cinco registros históricos ORV migrados desde 017 entre los primeros
IDs, y el ejecutable `git` para una prueba ERD sin base de datos. Los tres fallos
iniciales de los casos nuevos se corrigieron ajustando los hashes sintéticos de
32 a 64 caracteres, conforme al esquema; no requirieron cambios en la migración.

La segunda QA se preparó desde 001–017, creó cinco integrantes ORV históricos,
aplicó 018–019 con el runner oficial y comprobó su clasificación `sin_clasificar`.
Se añadieron cien núcleos RAN sintéticos. Un único administrador administrado por
pytest permite ejecutar también la prueba del último administrador. Después se
aplicó 020 y se comprobó nuevamente la conservación íntegra de la bitácora.

Las seis pruebas ERD sin base se ejecutaron en el host mediante:

```sh
python3 -m unittest discover -s backend/tests -p test_generate_db_erd.py -v
```

Resultado: **6 aprobadas**. Conservan sus ejemplos históricos de 019.

En el runner conectado a la segunda QA se ejecutó:

```sh
python -m pytest --ignore=tests/test_generate_db_erd.py -o cache_dir=/tmp/pytest-cache -q
```

Resultado final: **354 aprobadas**, sin fallos ni omisiones, en 168.78 segundos.
Sumadas a las seis pruebas ERD sin base, **360 pruebas aprobadas**. Sólo queda
la advertencia preexistente de deprecación Starlette/httpx.

## Evidencias y estado

Diff completo: `/tmp/software-pa-heartbeat-020.diff`.
Log final QA: `/tmp/software-pa-heartbeat-qa-complete/full020.log`.

Logs y scripts locales de ejecución: `/tmp/software-pa-heartbeat-qa/` y
`/tmp/software-pa-heartbeat-qa-complete/`. Los archivos `.env` contienen únicamente
credenciales sintéticas y no forman parte del diff ni del repositorio.

La corrección queda pendiente de revisión. No se ha realizado push ni merge.
No se modificaron frontend, despliegues, servidores productivos ni migraciones
históricas. Las bases QA creadas se conservan para inspección.
