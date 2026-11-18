# Publicación inicial controlada de +pa5

Preparado el 18/11/2026. Alcance: PR independiente hacia `main`; el propietario ejecuta todas las operaciones remotas. No acredita disponibilidad en GHCR, CI remoto ni producción.

## Qué se ha preparado

Workflow `.github/workflows/publish-pa5-ghcr.yml`, verificadores en `publisher/pa5`, pruebas en `tests/publisher` y evidencia local en esta carpeta. No cambia archivos históricos de main ni integra dev. Base de main comprobada mediante consulta remota: `469375ddd8ac6eb4dd4055d56ca533db628675dd`. PR #8 comprobado abierto, draft, sin merge, head `ae9cd6021b15d45f4091ab9854d394348cacfbc0`.

El workflow sólo admite `workflow_dispatch` desde main y el repositorio exacto. Checkout usa el SHA del evento de main, con credenciales no persistentes; nunca ejecuta scripts de un PR. No hay PAT, contraseñas personales, apt, pip ni descarga de ejecutables. Python y Docker son herramientas del runner administrado `ubuntu-24.04`; se registran sus versiones y la versión de imagen del runner. Ese entorno de ejecución no está fijado por digest; no se utiliza para recompilar bibliotecas. Las dos Actions oficiales están fijadas por SHA.

Los jobs son:

1. `prepare`: `contents: read`, `actions: read`, ningún permiso de paquetes. Descarga el archivo autorizado, verifica su hash y layout, deriva el candidato y ejecuta smoke nativo sin red sobre un runner efímero. Publica informes de preparación como artifacts, nunca paquetes.
2. `publish`: depende de prepare y de un digest explícito; environment `pa5-publish`. Único job con `packages: write`; también `contents: read` y `actions: read` para consultar la protección. Repite las verificaciones offline, exige identidad aprobada, comprueba ausencia de la etiqueta, transfiere bytes OCI con GITHUB_TOKEN y verifica digest, privacidad y vinculación. No ejecuta procesos del contenedor.
3. `consume`: runner GitHub-hosted nuevo, `contents: read`, `packages: read`. Consulta el manifiesto/config reales y descarga por digest con Docker; comprueba rootfs, identidad, metadatos, bibliotecas, paquetes, PostgreSQL/PostGIS, LLVM JIT y GDAL MEM. Conserva los resultados en artifacts.

Una primera ejecución sin `approved_digest` ejecuta sólo prepare. Un job omitido, pendiente o fallido no cuenta como PASS.

## Reproducibilidad e identidades

No se puede garantizar un rebuild idéntico de F2-E1 en Actions. Las recetas usan la base local `software-pa-residual-postgis:20261110`, apt Debian/PGDG sin snapshot completo, herramientas/dependencias de compilación sin lock exhaustivo y changelog/tiempos de build. Las tres fuentes Debian sí tienen checksums y verificación gpgv; eso no fija todo el entorno. Los tres .deb, la base histórica y el expediente completo de ejecución no están distribuidos por Git. Los hashes de paquetes no prueban disponibilidad remota.

Se verificaron localmente los 23 build_inputs contra el commit aprobado: `fuentes-verificadas.json`. Las fuentes, preparadores y parches completos se consultan por ese commit en [backend/native/postgis](https://github.com/JPonce-23/Software-PA/tree/ae9cd6021b15d45f4091ab9854d394348cacfbc0/backend/native/postgis). `publisher/pa5/Dockerfile.f2e1-reference` es la receta histórica exacta, conservada para auditoría; NO es una receta de reconstrucción reproducible ni es ejecutada por el workflow. No se necesitan nuevas fuentes compilables para la ruta de transferencia elegida.

Ruta A implementada: importar el archivo previamente validado desde un asset de Release autorizado por el dueño, seleccionado por ID numérico del mismo repositorio y autenticado con GITHUB_TOKEN. Se exige el hash fijo antes de extraer nada. No se usa una URL arbitraria ni un tag mutable para seleccionar bytes.

| Objeto | Identidad |
| --- | --- |
| Commit de origen | `ae9cd6021b15d45f4091ab9854d394348cacfbc0` |
| Archivo fuente | SHA-256 `4099c542cf891338320396fca45fac0bc47bd1064217e70b331259981ad025b2`, 263294464 bytes |
| Índice F2-E1 / Image ID registrado | `sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c` |
| Manifiesto linux/amd64 original | `sha256:27e9ca0702414c9515cf205df5635af7ad7509385dffcf7dcf6fb048c185f9b7` |
| Config original | `sha256:dfe80e1feb214799ba101b037f0b72e2499de606a63ef88497f4e13bb1ed3f19` |
| Biblioteca libgdal36 | SHA-256 `10c9bc0c0bbafe2f16b51c130ad5f4ba2030c204cbbac5a271a79e6418abadeb` |
| Config del candidato con etiquetas | `sha256:96377c4ff49bb164e961b42d684e3a605b01848e518d32f65bc834f32826cdad` |
| Manifiesto candidato calculado localmente | `sha256:08cb9799c6f9d8f616264bbddeee73b0010b06cbdd219e544a196e504190fea0` |

El candidato añade source, revision, version y el índice de procedencia a los Labels del config. Cambia config/manifiesto y publica un manifiesto OCI único linux/amd64; no se publica el índice original ni se atribuye su attestation al candidato. No cambia ninguna capa, diff_id, entrypoint, comando, variable, historial o biblioteca. La igualdad de todas las capas conserva exactamente los binarios y ABI de F2-E1. Los 23 gates nativos previos son evidencia histórica de esos bytes; no se declaran repetidos en esta preparación.

**La identidad nueva requiere aprobación explícita**, aunque no haya recompilación. Su digest local no es evidencia de existencia remota. El digest resultante se consulta realmente a GHCR después del PUT y en otro runner. `candidate.json` y `source-verification.json` conservan la derivación local. La versión OCI es `3.10.3+dfsg-1+pa5`; el tag es `3.10.3-dfsg-1-pa5` porque un tag de registro no admite `+`.

Ruta B, si se desea recompilar: preparar otro candidato con snapshots, base y toolchain fijados, ejecutar la campaña completa de ABI/componentes/regresiones nativas, conservar sus resultados y pedir aprobación de su NUEVA identidad. Este workflow no implementa ni acepta ese atajo. Un rebuild que termina correctamente no satisface la identidad fija del archivo.

## Pasos exactos para JPonce-23

### 1. Revisar y crear el PR, manualmente

La rama local preparada es `release/pa5-ghcr-publisher`, en `/tmp/software-pa-pa5-publisher`. Antes de salir de la máquina, guardar una copia duradera o el bundle/patch de entrega; `/tmp` es temporal. Desde ese worktree:

```sh
git status --short --branch
git diff origin/main...HEAD --stat
git diff origin/main...HEAD -- .github/workflows publisher tests/publisher docs/pa5-publicacion
python3 -B -m unittest discover -s tests/publisher -v
```

Revisar `PR.md` y la evidencia. Volver a comprobar que main no avanzó desde la base indicada; si avanzó, conciliar esta rama exclusivamente sobre main y repetir revisión. El propietario, cuando lo decida, ejecuta:

```sh
git push -u origin release/pa5-ghcr-publisher
gh pr create --repo JPonce-23/Software-PA --base main --head release/pa5-ghcr-publisher --title 'Preparar publicación manual de +pa5 en GHCR con aprobación de identidad' --body-file docs/pa5-publicacion/PR.md
```

Revisar y fusionar únicamente ese PR publicador hacia main, de forma manual. No fusionar dev ni el PR #8 para habilitar el botón de ejecución. GitHub sólo descubre workflow_dispatch cuando el archivo está en la rama predeterminada.

### 2. Autorizar y distribuir el archivo fuente

El archivo local comprobado es `/tmp/etapa4r/pa5-validated-image.tar`; no se incluye en Git ni en el diff. Antes de distribuirlo, comprobar tamaño y SHA-256 de la tabla. El dueño debe autorizar expresamente su distribución y subir **sólo ese archivo** como asset de una Release de Software-PA. Las Releases/assets de un repositorio público son públicamente accesibles: mantener privado GHCR no vuelve privado el archivo fuente. Si el dueño requiere que también el archivo fuente sea privado, **no usar una Release pública**: falta una fuente privada autorizada compatible y deberá adaptarse/revisarse el mecanismo de descarga antes de ejecutarlo. No existe una fuente remota autorizada o probada en esta entrega.

En GitHub, Releases → Draft a new release, elegir un tag dedicado al expediente (no una rama de código), adjuntar `pa5-validated-image.tar`, revisar contenido y publicar manualmente. Esa operación remota no la realiza el agente. Obtener el ID numérico del asset:

```sh
gh api repos/JPonce-23/Software-PA/releases --jq '.[] | .assets[] | select(.name=="pa5-validated-image.tar") | {id,name,size,url}'
```

Confirmar cuál es el asset autorizado y crear una variable de Actions del repositorio `PA5_SOURCE_ASSET_ID` con ese ID. El hash obligatorio seguirá rechazando cualquier otro contenido, aunque se cambie la variable. No configurar la misma variable con un valor distinto en el environment.

### 3. Proteger el environment antes de habilitar publicación

Settings → Environments → New environment → `pa5-publish`:

- Required reviewers: únicamente `JPonce-23` para esta primera publicación. Los revisores tienen semántica OR; agregar otro permitiría aprobar sin el propietario.
- Deployment branches and tags: Selected branches and tags; una sola regla de tipo **branch**, nombre exacto `main`.
- Desactivar el bypass administrativo. El API no garantiza exponer ese ajuste; el dueño debe verificarlo en la interfaz. Cuando el API lo expone como habilitado, el código también lo rechaza.
- Si JPonce-23 dispara y aprueba su propia ejecución, dejar desactivado Prevent self-review; activarlo exigiría que otra persona dispare el workflow para que JPonce-23 pueda aprobarlo.
- Comprobar que el plan/visibilidad del repo permite Required reviewers. Si no está disponible, detenerse; una variable no sustituye esa aprobación.

El workflow consulta los revisores y la política main mediante GET antes de solicitar y después de recibir aprobación. Si faltan permisos de lectura, no relajar la protección ni añadir un PAT: resolver la configuración de Actions. Un environment creado implícitamente por el YAML carece de protección y se rechaza.

Congelar otros escritores del paquete/etiqueta durante la publicación. Crear en **este environment** `PA5_EXCLUSIVE_WRITER=confirmed` sólo después de confirmar esa exclusividad. El cliente comprueba ausencia dos veces, rechaza etiquetas existentes incluso con el mismo digest, usa `If-None-Match: *`, y concurrency serializa este workflow. GHCR no ofrece aquí una garantía comprobada de creación atómica de tags frente a escritores externos; no se presenta esa cabecera como una garantía. La exclusividad es una condición operativa necesaria. No se publica `latest`.

### 4. Preparar y revisar, sin publicar

Actions → Publish reviewed PA5 to GHCR → Run workflow, branch `main`:

```text
version: 3.10.3+dfsg-1+pa5
source_commit: ae9cd6021b15d45f4091ab9854d394348cacfbc0
approved_digest: [vacío]
```

Esperar `prepare` verde. Descargar `pa5-preparation-<attempt>`, revisar hashes/config/source-verification, `native.log`, `inspect.json`, `packages-and-linkage.txt` y el resumen. El digest debe coincidir con el candidato de la tabla; si difiere, detenerse. Verificar PostgreSQL 15.19, PostGIS 3.6.4, GDAL 3.10.3 ABI36 y paquetes +pa5, así como los cinco hashes protegidos. No considerar una ejecución omitida como prueba nativa.

### 5. Aprobar la identidad y publicar

Ejecutar nuevamente el workflow con la misma versión/commit y:

```text
approved_digest: sha256:08cb9799c6f9d8f616264bbddeee73b0010b06cbdd219e544a196e504190fea0
```

La nueva preparación debe aprobar. JPonce-23 revisa **esa ejecución**, el commit de main y sus artifacts, y aprueba el deployment `pa5-publish` sólo cuando acepta explícitamente la nueva identidad. El job no ejecuta Docker ni el código de un PR con el token escritor.

Si se detecta una etiqueta existente, no borrarla, no sobrescribirla y no reintentar a ciegas. Revisar identidad y disponibilidad; este workflow es para primera publicación. Si el PUT tuvo éxito pero una comprobación posterior falló, puede existir el paquete aunque el job sea rojo: inspeccionarlo antes de cualquier otro intento. El workflow no cambia permisos ni visibilidad y no hace rollback destructivo.

### 6. Comprobar publicación y consumo reales

Exigir `publish` y `consume` verdes. Conservar URLs de ambos jobs, commit ejecutado, run/attempt, JSONs de evidencia, logs nativos e inventario. En el paquete del usuario JPonce-23 → `software-pa-native-postgis` → Package settings comprobar:

- Visibility **Private** y conexión a `JPonce-23/Software-PA`.
- Manage Actions access: Software-PA con acceso suficiente para publicación y lectura; el consumidor sólo recibe `packages: read`.
- Versión, commit, linux/amd64 y digest de manifiesto **realmente recibido**.
- Pull por `ghcr.io/jponce-23/software-pa-native-postgis@sha256:08cb9799c6f9d8f616264bbddeee73b0010b06cbdd219e544a196e504190fea0`, sin usar el tag para seleccionar el contenedor.

La creación inicial de un paquete de contenedor es privada por defecto. La herencia de permisos del repositorio no equivale a herencia de visibilidad. El API del workflow exige privacidad y vinculación y falla si no puede demostrarlas. Fuentes: [Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry), [acceso y visibilidad](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).

## Revisión del acceso a metadatos con GITHUB_TOKEN

La revisión local del PR #9 sustituye la consulta `/users/JPonce-23/packages/...`, documentada para paquetes públicos, por `GET /user/packages/container/software-pa-native-postgis`, la ruta del usuario autenticado que admite tokens de instalación. Se utiliza el mismo `GITHUB_TOKEN` del job: `packages: write` sólo en publish y `packages: read` en consume, sin PAT ni permisos adicionales. La respuesta debe identificar el paquete container exacto, su propietario `JPonce-23` (independiente de quién dispara el workflow), visibilidad private y asociación real con `JPonce-23/Software-PA`. El label OCI source se comprueba por separado y no sustituye la asociación que devuelve GitHub.

Los errores 401/403, límites y fallos del servicio detienen la operación. Un 404 previo sigue siendo «ausente o no legible», nunca prueba de privacidad; después de publicar es fatal. No se consulta una ruta pública como fallback, no se eleva el token ni se cambian permisos. Las verificaciones de manifiesto, config, tag, procedencia, plataforma y rootfs permanecen obligatorias. Referencias: [GET package autenticado](https://docs.github.com/en/rest/packages/packages#get-a-package-for-the-authenticated-user), [GET package público de un usuario](https://docs.github.com/en/rest/packages/packages#get-a-package-for-a-user).

La suite actual contiene 24 pruebas unitarias, incluidas regresiones de metadatos y de integridad/procedencia del consumidor. Sus respuestas HTTP son simuladas: la compatibilidad operativa y el acceso real con el GITHUB_TOKEN de Software-PA siguen pendientes de ejecución remota autorizada. El mecanismo y la autorización pendiente de distribución del archivo Docker no cambian. La evidencia local inicial de 16 pruebas se conserva como registro histórico.

## Inventario de permisos y acceso posterior de DrMannx

| Identidad | Permiso y finalidad | Estado actual |
| --- | --- | --- |
| JPonce-23 | Owner/Admin, revisa PR, fuente, environment e identidad | Operaciones pendientes del dueño |
| GITHUB_TOKEN prepare | contents:read, actions:read; sin packages | Declarado en YAML |
| GITHUB_TOKEN publish | contents:read, actions:read, packages:write; environment | Declarado; acceso real pendiente |
| GITHUB_TOKEN consume | contents:read, packages:read | Declarado; pull real pendiente |
| Software-PA en Manage Actions access | Acceso del repositorio al paquete vinculado | Verificar tras primera publicación |
| DrMannx | Ningún permiso nuevo concedido por este trabajo | Write posterior y manual |

Después de demostrar la primera publicación, JPonce-23 abre Package settings → Manage access → Invite teams or people → `DrMannx` → **Write**. Si el paquete hereda permisos y la interfaz no permite granularidad, el propietario debe revisar/desactivar la herencia antes de asignar el permiso, conservando Software-PA en Manage Actions access. No conceder Admin ni cambiar visibilidad para resolver acceso. [Permisos de paquetes](https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages).

## Relación con PR #8 y criterios de cierre

El catálogo/verificador actual del PR #8 exige el config y conjunto de manifiestos originales. **No aceptará automáticamente este candidato con metadatos nuevos.** Este PR publicador no cambia ese contrato, su rama ni su SHA. Después de publicación/consumo reales, el propietario deberá autorizar por separado la conciliación del catálogo/verificador de integración con la identidad aprobada, manteniendo las mismas capas/payloads; no basta con introducir el nuevo digest en una variable. Este trabajo no declara desbloqueado el gate de suministro de #8.

Evidencia local: 16 pruebas unitarias de identidad, controles, rechazo de errores/etiquetas y protección de credenciales; validación real de 33 blobs/29 capas y paquetes/payloads, verificación de 23 entradas de fuente, generación determinista del candidato y archivo Docker clásico, sintaxis YAML/shell/Python. Las pruebas con respuestas HTTP simuladas comprueban comportamiento del cliente, no disponibilidad GHCR.

Límite local: el Engine principal rechazó acceso; el daemon rootless aislado no pudo iniciar por falta de `newuidmap`. No se modificó el Engine del proyecto. **Importación Docker y smoke nativo de este candidato no ejecutados localmente**; los jobs remotos los exigen antes de publicación y tras descarga. El archivo Docker generado sí se verificó offline contra los diff_ids. Aún faltan fuente remota autorizada, configuración real del environment, aprobación de identidad, publicación privada y consumo independiente. No hay resultados remotos simulados ni afirmación de producción aprobada.

Sólo después de obtener y revisar toda la evidencia remota podrá informarse disponibilidad GHCR para este candidato. Las reglas de environment se documentan en [GitHub environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments); la lectura de su configuración usa [GET environment](https://docs.github.com/en/rest/deployments/environments) y [branch policies](https://docs.github.com/en/rest/deployments/branch-policies).
