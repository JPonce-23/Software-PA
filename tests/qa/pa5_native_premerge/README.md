# PA5-QA: campañas nativas históricas 001–034 y corrección 035

Estas herramientas son material QA nuevo; el código de aplicación probado procede exclusivamente de **f715b55b964517aa4f859e9d20cbdcdee51a36ea**. No cambian ese commit, las migraciones ni la imagen congelada. `source-sha256.json` fija42 archivos del candidato. El Engine admitido por esta campaña es **9efbaf92-7703-4fa0-9192-31b975794366**; cambiarlo requiere otra autorización/revisión, no sólo editar el argumento.

Ejecutar en PA5-QA, con acceso a su socket Unix y al Python3.12/stdlib ya instalados. La distribución del proyecto original no es un destino válido. El launcher comprueba el ID antes de cada operación Docker y no hace pull/build, instala paquetes ni crea redes. Sólo crea contenedores propios sin red/puertos, raíz RO y tmpfs; al terminar los elimina, sin tocar imágenes ni recursos ajenos.

Preparar un árbol fuente nuevo usando `git archive f715b55…` del repositorio autorizado y transferirlo a PA5-QA, sin copiar .git, .env ni uploads. Como mínimo incluir las42 rutas del manifiesto. Copiar esta carpeta QA aparte: **no está en el commit candidato**. Usar rutas absolutas y un destino de evidencia que aún no exista:

```sh
python3 /ruta/qa/run.py \
  --source /ruta/source-f715b55 \
  --assets /ruta/qa \
  --evidence /tmp/pa5-pr8-evidence-NUEVO \
  --approved-engine-id 9efbaf92-7703-4fa0-9192-31b975794366
```

Para no repetir el smoke ya aprobado al investigar regresiones de DB, añadir `--database-only`. Cada ejecución crea un clúster NUEVO y privado, con software_pa_test y marcador pa5-pr8-f715b55. Ni el nombre de DB ni una variable bastan para dirigirlo a una base existente: el launcher inicia PGDATA nuevo dentro del contenedor y sólo usa su socket privado. Owner/runtime tienen claves aleatorias efímeras generadas dentro; no pasan a Docker Config.Env ni se imprimen. El servidor PostgreSQL no escucha TCP.

## Dependencia Python del smoke original

La imagen +pa5 no contiene python3. El smoke original falla127 sin ese prerrequisito. El launcher monta `/usr/bin/python3.12` y `/usr/lib/python3.12` del host QA como **RO** bajo `/qa-python`, fija PYTHONHOME/PATH y registra versión y SHA-256 del binario y todos los archivos de stdlib. No instala paquetes, no reemplaza bibliotecas de la imagen y no introduce GDAL externo. Se ejecuta completo el script original sin cambios, con sus hashes/paquetes/ctypes-GDAL-MEM/PostGIS/raster/LLVM-JIT. Si el helper no es compatible, la ejecución falla; no hay fallback que omita verificaciones.

El helper usado fue Python3.12.3, paquetes Ubuntu3.12.3-1ubuntu0.16. Una actualización del host cambia su manifiesto y exige nueva revisión/repetición. El workflow remoto existente no monta automáticamente este helper: no se declara corregido ni aprobado su suministro remoto con este ensayo local. Su futura adopción requiere un helper revisado/fijado y un commit de verificador aprobado.

## Pruebas y estados

`database.sh` reutiliza bootstrap/migrador y `backend/db/tests/001_runtime_privileges.sql` canónicos. `ledger.py` compara los34 nombres/checksums; el segundo pase exige34 verificaciones, cero reaplicaciones y ledger idéntico. Los SQL adicionales usan sólo fixtures sintéticos y transacciones:

- `negative.sql`:16 operaciones prohibidas, que deben producir42501; no acepta cualquier error como prueba de denegación.
- `034.sql`: append/retirada/auditoría; UPDATE runtime debe producirP0001 y el mensaje exacto, DELETE runtime42501; rollback de etiquetas y bitácora.
- `034-owner.sql`: UPDATE y DELETE con privilegio suficiente deben activar realmente el triggerP0001; rollback final.
- `temp.sql`: comprueba creación temporal, sin modificar ACL.
- `temp-shadow.sql`: detecta si el trigger de auditoría escribe en una bitácora temporal en lugar de public.bitacora; registra conteos y revierte todo.

**Resultado histórico de la campaña 001–034: FAIL de seguridad.** La regresión temporal reprodujo persistent=0, temporary=1. Un exit0 de un SQL de diagnóstico significa que se midió la condición, no que sea segura. `run.py` clasifica el hallazgo como FAIL y termina con código1 aunque los contratos de ledger/ACL/034 aprueben. Si sólo se permiten temporales sin desvío, clasifica PARTIAL para la prohibición literal de crear cualquier objeto. No se cambiaron permisos ni migraciones para ocultarlo.

El backend GDAL3.13.3 ABI39 todavía no se ejecutó. Seguir el procedimiento `BACKEND-PENDIENTE.md` del expediente antes de autorizar suministro/build. No conectar estas pruebas a patrenes o a bases previamente creadas.


## Corrección 035: campaña actual

La fuente añade exclusivamente `035_endurecer_auditoria_search_path.sql` al snapshot anterior; `source035-sha256.json` verifica43 archivos sin cambiar el manifiesto histórico. Se reutilizan `database-common.sh`, ledger, seed, contratos de roles y034. Los escenarios siempre crean clúster/DB nuevos; upgrade instala primero001–034 y seed, reproduce los dos FAIL esperados y aplica únicamente035. Fresh instala001–035 directamente.

```sh
python3 /ruta/qa/run.py --source /ruta/source-035 --assets /ruta/qa \
  --source-manifest source035-sha256.json --database-script database-035.sh \
  --scenario upgrade --database-only --evidence /tmp/pa5-035-upgrade-NUEVO \
  --approved-engine-id 9efbaf92-7703-4fa0-9192-31b975794366
```

Repetir con `--scenario fresh` y otro directorio de evidencia. `--database-only` evita repetir el smoke nativo intacto. La prueba estricta `audit-persistence.sql` mantiene la tabla temporal presente: falla antes y exige public=2/temp=0 después. `audit-origin.sql` exige rechazo de un trigger temporal que reutiliza la función privilegiada; `audit-auth.sql` comprueba actor/secretos/heartbeat/evento real frente a uno temporal falso. Los mismos bytes se usan antes/después, sin cambiar expectativas.

Con la035, ambos escenarios aprobaron, incluyendo35 nombres/checksums,35 verificaciones sin reaplicación, OID/owner/ACL/datos preservados, roles y034 con rollback. TEMP se conserva y ya no se usa el diagnóstico histórico como criterio para esta campaña segura. El backend ABI39 permanece bloqueado; no se hizo build ni se considera probado por los resultados SQL.
