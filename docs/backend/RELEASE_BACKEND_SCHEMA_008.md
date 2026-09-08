# Candidato de release backend — esquema 008

## Referencia candidata

- Rama de preparación: `feature/backend-logica`.
- Base compatible: ledger exacto 001–008.
- API: SOFTWARE-PA `2.0.0`.
- Contrato generado: `docs/backend/openapi-backend-schema-008.json`.
- Migraciones 007 y 008 son forward-only e inmutables una vez registradas.

### Ledger de migraciones 001–008 (SHA-256 verificado)

| Versión | Nombre | Checksum SHA-256 |
|---|---|---|
| `001` | `baseline_v1` | `242ffc787beb2886d36b6fb3031c25a8baddd23ce669e78488672e274c4ad7c7` |
| `002` | `cierre_fuentes_excel` | `ef1165711cc6054f26921062fd4e8202ce3dc0f7623ddb8f7eac1daa8639577e` |
| `003` | `reporting_fuentes_excel` | `807279889979c3e7d55e849738f2361483e8e20810614f068515e8f95aa053ba` |
| `004` | `seguimiento_funcional_excel` | `7c1a470e2429b6ec6ff3bc003ae9e3324ce3d552a984904760d0deb57381de12` |
| `005` | `reporting_cierre_excel` | `a35faa802c5f43a3c906aae6c62b5bac4ef842f610e87a178a2e8524ed494c76` |
| `006` | `ajustes_reporting_post_auditoria` | `e1a603fd2015615671c0cd072a0a795f50e92e8c21e838f26d88abec25dddee4` |
| `007` | `convenios_impactos_precision` | `adabd7775fb8165a1db8be04a93e7971fe207e745b410c57eb6fc76cc3a7e4f7` |
| `008` | `fifonafe_evolucion_forward_only` | `95bf328f18112933481488c59763df6a6467d8fd3db354bb7e5465c727c8f012` |

La referencia estable será el commit resultante de la publicación autorizada;
el HEAD publicado anterior no incluye los cierres locales y no debe usarse como
referencia de integración.

## Alcance funcional disponible

ProyectoNucleo es la raíz de aislamiento. El backend cubre ORV y representación
histórica, padrón, afectaciones y unidades agrarias, Asambleas, Convenios e
impactos, RAN por ciclos, FIFONAFE v1/v2, indemnización y Pago como identidades
separadas, documentos/requisitos, seguimiento y reporting periódico/snapshot.

Los cambios 007/008 y endpoints relevantes se resumen en
`docs/backend/API_CONTRATO_FRONTEND_V1.md`; OpenAPI es el contrato mecánico de
campos, métodos y respuestas. Las limitaciones de procedencia y revisión
documental permanecen descritas en `PREPARACION_007_CONVENIOS.md` y
`PREPARACION_008_FIFONAFE.md`. Los Excel originales no son dependencia de
ejecución ni del frontend.

## Instalación reproducible desde una base vacía

1. Preparar variables a partir de `.env.example`, fuera del control de versiones,
   con secretos propios. Son obligatorios los usuarios/contraseñas owner y
   runtime, `SECRET_KEY` y la configuración del entorno. En producción usar
   `APP_ENV=production`, cookie segura y orígenes CORS HTTPS exactos.
2. Ejecutar `docker compose config --quiet`.
3. Iniciar `docker compose up -d --build db`. En un PGDATA vacío, los scripts de
   init crean roles y el runner aplica, en orden, 001–008. El runner usa una
   transacción por migración, calcula SHA-256 y rechaza archivos aplicados que no
   coinciden con el ledger.
4. Cargar el catálogo territorial oficial con el comando documentado en README.
5. Ejecutar `backend/scripts/utils/set_runtime_credentials.sh`, iniciar backend y
   verificar `/health`; debe responder `schema: 8`.
6. Crear el primer administrador con `backend/scripts/create_admin.py`, mediante
   bootstrap owner explícito y una contraseña inyectada o capturada sin persistirla.
7. Ejecutar los contratos SQL 002–008 y la suite backend contra una base aislada
   antes de promover el ambiente.

La instalación limpia no se volvió a ejecutar durante este gate porque no estaba
autorizado crear otra base. El orden y las garantías del runner sí fueron
auditados; QA demuestra la actualización completa hasta 008.

## Actualización de una instalación existente

1. Detener escrituras, verificar sesiones y obtener un `pg_dump -Fc` único;
   comprobar SHA-256 y `pg_restore -l` sin restaurarlo.
2. Comparar cada fila de `schema_migrations` con el archivo correspondiente.
   Cualquier diferencia bloquea el runner y se concilia antes de continuar.
3. Publicar exactamente la referencia candidata y ejecutar una sola vez
   `backend/scripts/run_migrations.sh` con el rol migrador, nunca SQL parcial ni
   ediciones manuales del ledger.
4. Verificar ledger 001–008, propietarios, ACL, triggers habilitados, contratos
   SQL, `/health`, regresiones y rollback operativo documentado.

`db_pruebas_alfredo` no está autorizada para actualización: su 006 registrada no
coincide con el archivo publicable. No se deben ejecutar 007/008 hasta resolver
esa divergencia mediante un procedimiento aprobado y un respaldo nuevo.

## QA, demostración y aislamiento

La cuenta QA y su credencial viven fuera del repositorio. Las pruebas se ejecutan
con `~/.local/bin/software-pa-qa-pytest -q`, que inyecta las variables de manera
local y limita la base a `software_pa_test`. No se distribuyen la cuenta, claves,
backups ni almacenes cifrados con el release.

QA contiene fixtures sintéticas históricas. Los proyectos cerrados lógicamente
no entran en las vistas operativas actuales. Existen además fixtures anteriores
bajo proyectos activos; para una demostración se debe usar un proyecto elegido y
el filtro `id_proyecto`, documentar su carácter sintético y evitar totales QA
globales. No se aplicará un filtro oculto por prefijo y no se usará QA como
sustituto de producción.

## Respaldo y recuperación

Antes de cualquier actualización se requiere un dump custom verificable y un
registro de su base, instante, tamaño, permisos, SHA-256 y catálogo. Si una
migración falla, su `--single-transaction` debe dejar esquema y ledger sin esa
versión; se conservan logs y se diagnostica antes de reintentar. Si una migración
quedó registrada, no se modifica: la corrección será una evolución forward-only
autorizada. La restauración es una operación separada, controlada y previamente
ensayada; nunca se ejecuta automáticamente sobre el ambiente operativo.

## Exclusiones del paquete

No se incluyen `.env`, credenciales, claves privadas, backups, uploads, archivos
temporales, fuentes Excel ni `cierre_006_ran_preparado*`. Este último es un
paquete local duplicado; sus fuentes vigentes ya están en `backend/tests` y
`docs/backend`.

## Evidencia del gate de release (2026-09-08)

- Selección transversal: 78 aprobadas.
- Suite backend: 203 aprobadas; una advertencia de deprecación Starlette/httpx.
- Contratos SQL 002–008 y regresiones SQL 007/008: aprobados.
- QA: ledger 001–008 coincidente, runtime `pa_runtime`, propietarios `pa_app`,
  permisos de lectura runtime y triggers de integridad/auditoría habilitados.
- OpenAPI generado: 106 paths, 161 operaciones, 134 schemas; SHA-256
  `d7d14a7a05323bf63a51724cf36d738cf7f963df828bc1de0c2d23b6b1a0aa2f`.

El contenedor de desarrollo persistente continúa apuntando a la principal con
esquema 6. No es el endpoint de integración del candidato 008. La integración
debe levantar el backend con configuración explícita hacia una base compatible
001–008, sin cambiar ni reutilizar secretos de producción.

## Publicación propuesta

Se recomiendan dos commits: primero código/esquema/pruebas, después contrato y
documentación. Deben excluirse expresamente `cierre_006_ran_preparado*` y todos
los archivos ignorados. Tras repetir el gate sobre los commits resultantes, la
referencia candidata es el tag anotado `backend-v2.0.0-schema008-rc1`.

La publicación del código no autoriza actualizar `db_pruebas_alfredo`. Esa
promoción tiene un gate separado: conciliación auditada de 006, respaldo nuevo y
preflight completo antes de ejecutar el runner.
