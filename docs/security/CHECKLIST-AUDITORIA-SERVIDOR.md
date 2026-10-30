# Checklist posterior de auditoría del servidor

Fecha: 2026-10-27. Referencia de código: dev / 683ff75613768de28a7127c7e33a6e2ef4fc40ff.

**PROPUESTO, NO EJECUTADO.** Esta fase no usó SSH, Docker, base de datos, API ni servidor. Los comandos de este archivo se proponen para una fase expresamente autorizada, ejecutada por el administrador desde una consola ya disponible. No son instrucciones para conectarse ahora. No iniciar/parar/recrear contenedores, no instalar herramientas, no ejecutar migraciones, tests de escritura, logins ni scripts de bootstrap.

Recopilar resultados como cumple/no cumple/pendiente y metadatos saneados. No guardar contraseñas, Config.Env, cadenas de conexión, cookies, cabeceras de autenticación, claves privadas, filas de negocio ni logs íntegros. No usar `docker inspect` completo, `docker compose config` completo, `env`, `printenv`, volcado de .env, pg_shadow, pg_authid, docker logs ni cat de archivos de claves. Si un comando necesita privilegios, lo debe ejecutar el administrador autorizado; no solicitar elevación en la fase de diagnóstico ya concluida.

## Registro de verificación

| Área | Estado actual | Evidencia que falta | Criterio de aceptación |
|---|---|---|---|
| Sistema Ubuntu/parches | No verificado | Versión, soporte, parches pendientes y reinicio | SO soportado, proceso de actualización y ventanas documentadas |
| SSH | No verificado | Config efectiva, usuarios/grupos autorizados y llaves administradas | Sin root/password según política, acceso limitado y llaves revocables |
| Firewall/sockets | No verificado | Listeners, reglas IPv4/IPv6/NAT/cloud | Sólo entrada necesaria, BD/pgAdmin/backend no expuestos públicamente |
| Docker daemon | No verificado | Versión, contexto, socket, grupo, opciones | Sin API daemon pública; acceso administrativo mínimo y logging seguro |
| Contenedores | Declaración parcial | Digest/UID/caps/mounts/red/cuotas efectivos | Worker GIS mínimo, sin secretos/red/volúmenes ajenos, cuotas verificadas |
| Composición | No verificado | Archivos realmente usados, frontend servido, APP_ENV/HTTPS | SSALFER y modo production inequívocos, sin override dev/reload |
| Nginx/entrada | No verificado | Config efectiva y headers de error/éxito | Confianza IP correcta, límites, CSP y protección de marcos/nosniff/caché |
| TLS | No verificado | Terminación real, certificados/protocolos | Cadena válida, hostname, renovación, redirección/HSTS según política |
| API/docs | Código observado | Ruta real de /docs/OpenAPI/health y errores | Exposición deliberada y minimizada; ningún dato sensible en health/error |
| PostgreSQL | Scripts observados | Roles/ACL/owner/TEMP/search_path/hba/TLS/timeouts | Mínimo privilegio verificado, ledger canónico 001–030, actor auditable |
| Backups/restore | Documentación parcial | Existencia, cifrado, separación, restore BD+volumen | RPO/RTO institucional medidos en clon; evidencia sanitizada |
| GitHub/build | No verificado | Branch protections/rulesets/CI/SBOM/digest/proveniencia | Revisión obligatoria, permisos mínimos y artefacto ligado al SHA |
| Logs/datos | Código parcial | Acceso/retención/exportación/clasificación | Sin secretos/PII en trazas, capturas/fixtures clasificadas |

## Ubuntu, SSH y firewall — comandos de sólo lectura propuestos

```sh
cat /etc/os-release
uname -r
uptime
test -e /var/run/reboot-required && echo 'Reinicio pendiente'
apt list --upgradable 2>/dev/null
ss -lntp
stat -c '%a %U %G %n' /var/run/docker.sock
getent group docker
```

`apt list` usa la caché existente, no actualiza índices; una caché antigua no prueba ausencia de parches. Revisar acceso de miembros Docker sin publicar sus nombres. `ss` debe contrastarse con firewall de host, reglas Docker y controles cloud; enlazar a loopback no garantiza ausencia de otra publicación/proxy.

Sólo el administrador autorizado, en consola, puede obtener estas lecturas privilegiadas:

```sh
sudo sshd -T | awk '$1 ~ /^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|authenticationmethods|maxauthtries|maxstartups|allowusers|allowgroups|x11forwarding|allowtcpforwarding)$/ {print}'
sudo ufw status verbose
sudo nft list ruleset
```

No copiar llaves, authorized_keys ni usuarios personales al informe. `sshd -T` sin contexto Match no refleja necesariamente cada regla de usuario/origen: revisar Match y, si procede, usar la variante `-C` con valores sintéticos/reales mantenidos localmente. Verificar firewall IPv6, reglas legacy/iptables, DNAT y restricciones del proveedor cuando existan; ufw por sí solo no acredita exposición Docker. No probar conexión por SSH durante esta fase.

## Docker y despliegue — salidas selectivas

Usar nombres concretos de contenedor ya identificados, sin descubrir ni imprimir secretos:

```sh
docker version --format '{{.Server.Version}}'
docker context show
docker info --format '{{json .SecurityOptions}}'
docker ps --format 'table {{.Names}}	{{.Image}}	{{.Ports}}	{{.Status}}'
```

Para cada contenedor autorizado reemplazar CONTENEDOR por su nombre. Son lecturas; no `exec`, restart, up, down, build ni pull.

```sh
docker inspect --format 'image={{.Image}} user={{.Config.User}} readonly={{.HostConfig.ReadonlyRootfs}} privileged={{.HostConfig.Privileged}}' CONTENEDOR
docker inspect --format 'capdrop={{json .HostConfig.CapDrop}} capadd={{json .HostConfig.CapAdd}} security={{json .HostConfig.SecurityOpt}}' CONTENEDOR
docker inspect --format 'memory={{.HostConfig.Memory}} nanocpus={{.HostConfig.NanoCpus}} pids={{.HostConfig.PidsLimit}} restart={{.HostConfig.RestartPolicy.Name}}' CONTENEDOR
docker inspect --format '{{range .Mounts}}{{.Type}} {{.Destination}} rw={{.RW}} {{println}}{{end}}' CONTENEDOR
docker inspect --format '{{json .NetworkSettings.Ports}}' CONTENEDOR
docker inspect --format '{{json .HostConfig.LogConfig}}' CONTENEDOR
docker inspect --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}' CONTENEDOR
docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' CONTENEDOR
```

No guardar rutas host/IP internas sin clasificación. Revisar, sin volcar env, que APP_ENV sea production, Secure sea efectivo, CORS coincida con origen y el backend no tenga owner/migrador como credencial. El administrador registra únicamente booleanos o valores no sensibles permitidos. Para detectar reload revisar la orden efectiva localmente y registrar sólo presente/ausente: las órdenes arbitrarias pueden contener secretos, no copiarlas completas al informe.

`Config.User` vacío requiere interpretar la imagen base; no basta para probar el UID efectivo de todos los workers Nginx. El backend Dockerfile no cambia USER: contrastar con la configuración efectiva. Revisar aislamiento de red de worker: estar en la red por defecto permite alcanzar servicios y no es equivalente a deny egress. Comprobar docker.sock/host mounts ausentes y mínimos permisos de directorios de cargas. No cambiar permisos durante inspección.

Para comprobar sólo servicios/imágenes declarados sin resolver ni mostrar secretos, desde la copia de despliegue autorizada:

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.ssalfer.yml config --services
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.ssalfer.yml config --images
```

Estos comandos no prueban que esa combinación sea la ejecutada; contrastar labels/digests y registros de despliegue. No ejecutar `config` sin filtro ni compartir YAML interpolado. La configuración declarada incluye React y SSALFER por separado: identificar cuál sirve el proxy y si el otro es alcanzable antes de decidir retirada. Obtener SBOM/versions de imagen mediante herramientas ya autorizadas, sin instalar ni ejecutar la imagen durante esta fase de lectura.

## Nginx, TLS, HTTP y cadena IP

Desde consola del proxy administrado, validar sintaxis sin recarga:

```sh
sudo nginx -t
```

Revisión local selectiva de configuración efectiva: server/location de entrada, proxy_pass y headers; cadena real_ip/set_real_ip_from y forwarded-allow-ips de Uvicorn; sobrescritura de XFF en entrada frente a concatenación. No publicar `nginx -T` completo: puede incluir claves, tokens o endpoints privados. Confirmar Host/Origin de la aplicación, redirección HTTPS, límites client_max_body_size/client_body_timeout/proxy_*_timeout/limit_req/limit_conn y su compatibilidad con cargas de 25 MiB/100 MiB más overhead. Una limitación del proxy debe aplicarse también a acceso directo que exista.

Lecturas HTTP anónimas de baja intensidad, sólo si esa fase autoriza contactar el origen; sustituir host por el origen aprobado y no seguir destinos ajenos. No enviar cookies ni crear sesiones:

```sh
curl -sSI --max-time 10 https://HOST_AUTORIZADO/Index.html
curl -sSI --max-time 10 https://HOST_AUTORIZADO/pages/mapa.html
openssl s_client -connect HOST_AUTORIZADO:443 -servername HOST_AUTORIZADO -brief </dev/null
```

No interpretar HEAD 405 como ausencia del control; el administrador puede revisar respuesta GET anónima con cuerpo descartado si se autoriza. No ejecutar pruebas de carga, escaneos TLS agresivos ni payloads. Confirmar en respuestas que correspondan CSP/frame-ancestors, X-Frame-Options si procede, nosniff, Referrer-Policy y HSTS en HTTPS. Validar también headers de respuesta 4xx/5xx y archivo autorizado con una fixture QA, no mediante sesión real institucional.

TLS: registrar emisor, vigencia, hostname/renovación y protocolos/cifrados permitidos desde configuración. No copiar clave privada ni cadenas de credenciales. La conexión s_client propuesta no es un escaneo de todos los cifrados. Frontend interno HTTP es compatible con terminación externa correcta; falta verificar el punto donde se añaden headers y que se preserve HTTPS de forma confiable.

Cookies: comprobar atributos en una futura sesión sintética de QA; HttpOnly, Secure, SameSite, Path=/, ausencia Domain, __Host-. No registrar valores Set-Cookie. Comprobar si /docs, /redoc, /openapi.json y /health se exponen por otro proxy; el Nginx SSALFER visible no reenvía esas rutas fuera de /api.

La IP registrada debe provenir de una cadena normalizada, no del primer valor arbitrario de XFF. Pruebas con XFF sintético sólo en clon/control de proxy autorizado; nunca usar cabeceras falsas para alterar registros reales durante diagnóstico.

## PostgreSQL — consultas de metadatos propuestas, no ejecutadas

Usar canal de administración ya autorizado y autenticación sin contraseña en argumentos/historial. No proporcionar una URL de conexión con secretos al reporte. Abrir una transacción READ ONLY para metadatos; no importar scripts contractuales ni invocar funciones de dominio:

```sql
BEGIN TRANSACTION READ ONLY;
SELECT version();
SELECT current_database(), current_user;
SELECT extname, extversion FROM pg_extension ORDER BY extname;
SELECT version, nombre, checksum_sha256 FROM public.schema_migrations
ORDER BY version::integer;
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls, rolinherit
FROM pg_roles ORDER BY rolname;
SELECT pg_get_userbyid(roleid) AS grupo, pg_get_userbyid(member) AS miembro,
       admin_option FROM pg_auth_members;
SELECT nspname, pg_get_userbyid(nspowner) AS owner, nspacl
FROM pg_namespace WHERE nspname='public';
SELECT c.relname, c.relkind, pg_get_userbyid(c.relowner) AS owner,
       c.relrowsecurity, c.relforcerowsecurity, c.relacl
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' ORDER BY c.relname;
SELECT p.oid::regprocedure AS funcion, pg_get_userbyid(p.proowner) AS owner,
       p.prosecdef, p.proconfig, p.proacl
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' AND p.prosecdef ORDER BY 1;
SELECT c.relname, t.tgname, t.tgenabled
FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2;
SELECT defaclrole::regrole, defaclnamespace::regnamespace,
       defaclobjtype, defaclacl FROM pg_default_acl;
SELECT name, setting, unit, source FROM pg_settings
WHERE name IN ('listen_addresses','port','ssl','password_encryption',
 'search_path','statement_timeout','lock_timeout',
 'idle_in_transaction_session_timeout','max_connections',
 'log_statement','log_min_error_statement','log_parameter_max_length',
 'log_parameter_max_length_on_error');
ROLLBACK;
```

Estas consultas no muestran hashes de contraseñas ni filas de negocio. Revisar ACL por heredados/PUBLIC y no sólo relacl explícita. Reemplazar RUNTIME_LOCAL por el nombre del rol runtime en consultas selectivas, sin escribir una contraseña:

```sql
BEGIN TRANSACTION READ ONLY;
SELECT has_database_privilege('RUNTIME_LOCAL',current_database(),'CREATE') AS create_db,
       has_database_privilege('RUNTIME_LOCAL',current_database(),'TEMP') AS temp,
       has_schema_privilege('RUNTIME_LOCAL','public','CREATE') AS create_public;
SELECT has_table_privilege('RUNTIME_LOCAL','public.bitacora','INSERT') AS bitacora_insert,
       has_table_privilege('RUNTIME_LOCAL','public.bitacora','UPDATE') AS bitacora_update,
       has_table_privilege('RUNTIME_LOCAL','public.bitacora','DELETE') AS bitacora_delete,
       has_table_privilege('RUNTIME_LOCAL','public.bitacora','TRUNCATE') AS bitacora_truncate;
SELECT has_table_privilege('RUNTIME_LOCAL','public.schema_migrations','UPDATE') AS ledger_update,
       has_table_privilege('RUNTIME_LOCAL','public.revision_cambio_gis_decision','UPDATE') AS decision_update;
ROLLBACK;
```

No confundir falta de atributos superuser con ausencia de membresía en un propietario. Comprobar que runtime no sea owner ni miembro de owner, y que grants a PUBLIC no recuperen facultades revocadas. Comparar checksum canónico completo, no sólo max(version). La función efectiva de decisiones debe ser la de 030; el máximo 030 no garantiza su cuerpo/triggers intactos. Para cotejo de definición el administrador puede leer pg_get_functiondef del nombre concreto y resumir el resultado, sin incluir datos. Search_path de SECURITY DEFINER necesita evaluación con pg_temp y ACL TEMP; el ensayo de shadowing es una prueba de escritura **exclusiva de un clon desechable**, no del servidor auditado.

pg_hba.conf/pg_hba_file_rules: el administrador revisa métodos sin trust externo, alcance de redes, SCRAM y TLS; no copiar usuarios/direcciones completas al informe público. No ejecutar funciones de aplicación, set_config del actor para suplantar identidades, DML, grants, EXPLAIN ANALYZE de consultas costosas ni tests de runtime durante esta fase de lectura.

## Backups, logs, cadena de suministro y GitHub

Lecturas propuestas de archivos de respaldo ya identificados, con rutas concretas autorizadas (sin expandir comodines ni mostrar contenido):

```sh
stat -c '%a %U %G %s %y' RESPALDO_AUTORIZADO
pg_restore --list RESPALDO_AUTORIZADO
```

Guardar sólo existencia, fecha, permisos, tamaño y conclusión de integridad de catálogo. El listado puede incluir nombres de objetos/propietarios: no adjuntarlo sin saneamiento. Un catálogo válido no demuestra restauración, cifrado ni consistencia con uploads. La restauración completa requiere otra fase en entorno aislado, base nueva y volumen coherente, con RPO/RTO medidos y datos protegidos. Verificar copia externa/inmutable, acceso separado, cifrado y recuperación de claves sin leerlas ni mostrarlas.

Logs: no recolectar docker logs/journal completos. Confirmar destino, rotación, retención, acceso y filtros; redactar parámetros SQL, datos personales, cookies y credenciales. Un administrador puede inspeccionar localmente un evento autorizado y registrar sólo si aparecen categorías sensibles. La prueba activa con marcadores se hace en QA. Revisar clasificación de capturas, docs/examples y fixtures, no publicar más información para demostrar la exposición.

Imágenes/dependencias: obtener digest, plataforma, versiones apt/GDAL/PROJ/Nginx/PostgreSQL y SBOM del artefacto real. Contrastar con advisories primarios por rango y condición; no diagnosticar CVE sólo por etiqueta. El acceso a un feed de vulnerabilidades no autoriza cargar código/datos a un scanner externo. Herramientas adicionales requieren autorización y revisión de efectos.

GitHub (API administrativa o consola por una persona con permiso): leer protecciones de main/dev **y rulesets de repositorio/organización**, reglas de inclusión/exclusión y bypass, revisión mínima, checks obligatorios, protección de force-push/borrado y permisos de Actions/GITHUB_TOKEN. Leer configuración no cambia reglas. `protected:false` histórico no demuestra ausencia de rulesets actuales. No solicitar ni copiar tokens. Revisar quién puede publicar imágenes/artefactos y si el digest está ligado al SHA revisado.

## Cierre de la fase posterior

Registrar área, fecha, operador autorizado, objeto/digest/SHA, comando/lectura aplicada, resultado saneado y desviación vinculada a SS-01…SS-12. No convertir un pendiente en cumple por falta de acceso. Toda remediación, cambio de configuración, restauración o reproducción de vulnerabilidad necesita la autorización de la siguiente fase. **Este archivo sólo documenta lo pendiente; no acredita que se haya ejecutado ninguno de sus comandos.**
