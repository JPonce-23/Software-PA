Fecha: 2026-10-29. Base original `683ff75613768de28a7127c7e33a6e2ef4fc40ff`; base candidata dev `e2699fe5c043996f7338bd63af3221957699bd65`; PR #5 observado `42ef451847dea8286c0f8d395b0d91675e62b69b`. SSALFER es el frontend oficial. **0 ramas y 0 commits creados; ningún push/PR/merge/despliegue.**

# Plan actualizado de commits del candidato conciliado

**No se crean commits/ramas ni se descargan refs en esta intervención.** El espacio es un directorio de fuentes sin .git. Los SHA de commits nuevos no existen. La autorización futura para obtener referencias y crear commits es independiente de la autorización de conciliación actual.

1. Revisar matriz/diff/fuentes seleccionadas y aceptar exclusiones PR5; asegurar paquete /tmp antes de limpieza. Original de 752 archivos y 100 candidatos no se toca.
2. Reconsultar dev/PR4/PR5 por lectura. Si cambian `e2699fe5c043996f7338bd63af3221957699bd65`/`42ef451847dea8286c0f8d395b0d91675e62b69b`, recalcular hunks; no aplicar ciegamente el candidato ni asumir aprobación de todo PR5.
3. Autorizar expresamente obtener dev vigente en **otro repositorio/directorio Git aislado**, sin fetch/pull/merge/rebase/reset sobre el original. Crear rama security/ss01-ss12-qa sólo allí, basada en dev verificado y sin reutilizar la rama que alimenta PR4/5. No se ejecutan comandos de descarga o switch ahora.
4. Comparar todas las fuentes no sensibles del nuevo dev con base-dev/manifest de esta entrega; .env.example ausente de la proyección queda intacta en el clon real. Verificar primero el diff acumulado nuevo CANDIDATO-CONCILIADO.patch con git apply --check; **no es ninguno de los 10 patches históricos**. Aplicación futura sólo con autorización al clon nuevo y validación de base exacta. Nunca aplicar patches archivados en serie.
5. Usar staging explícito por archivo/grupo, revisar contenido staged y procedencia, sin git add . ni datos/outputs/capturas nuevas. Revisar hooks antes de ejecutarlos; no saltarlos. Mantener tests/docs de cada control y dependencias sin commits intermedios rotos.

| Grupo propuesto, no commit real | Alcance coherente | Dependencias |
|---|---|---|
| C1 SS04+SS10 fundamento |request_origin/authentication/main/database/safe_logging/logging.json/4CLI/runtime Dockerfile+Compose compartidos; tests respectivos; config HTTPS y docs producción seleccionados |Incluye plumbing REPORT/DOCUMENT/IMPORT en Compose, documentarlo como integración compartida; no UID/2 workers/TLS |
| C2 SS02+SS03 GIS |ingestion/limits/archives/imports/reconciliation +tests/docs |C1; no worker fuerte ni cambios de CRS/RBAC |
| C3 SS06+SS12 documental |validation/storage/documents/router, fixtures/tests QA/docs |C1 logs, preservar publicación conservadora y autorización actual; sin lock/esquema nuevos |
| C4 SS11 |reporting/report_limits/contrato Node/docs |C1; sin API de tiles/paginación geométrica |
| C5 SS01 |mapa.js/tooltip test/evidencia |Sin CSP enforcement |
| C6 SS08+selección PR5 publicación |nginx/Dockerfile SSALFER/.dockerignore/gitignore seguro/test_http +hunks de test_reconciled_candidate que sean coherentes |C1, C3, C5; no 101m global. Probar todos6 tests de conciliación al cerrar serie |
| C7 SS07 |auditoría SQL/preparador/tests/docs |Sin permisos efectivos alterados |
| C8 SS09 conciliado |ignore backend/verificador/perfiles/inventario/vendors/test_supply_chain |C6; legado opcional, SSALFER obligatorio; hashes locales no autenticidad |
| C9 SS05 |tres diseños de política |Ningún cambio de autorización |
| C10 Evidencia/entrega |auditoría, archivos históricos originales, redacción puntual rendimiento y docs vigentes/conciliación |Último; registrar SHAs reales cuando existan |

No separar artificialmente archivos compartidos reconstruyendo código. El test de conciliación puede ir como grupo final si depende de varios grupos; no crear un test intermedio roto. Un archivo se agrega una sola vez en el grupo conjunto explicado. Nunca commits vacíos o títulos que afirmen cierre de controles ausentes.

6. La inspección amplia de whitespace mostró192 avisos heredados en15 documentos/parches sin cambios; revisar y clasificar antes de staging. Mantener rigor en código/config nuevo. No normalizar evidencia histórica para ocultar avisos ni usar --no-verify. Si política/hooks rechazan esos artefactos, acordar tratamiento de archivo/evidencia con mantenedor antes de commit. git apply con --whitespace=error-all rechazaría esos archivos históricos aunque no haya incompatibilidad de código; no presentarlo como prueba de la corrección.
7. Tras cada grupo autorizado revisar commit/alcance/SHA y pruebas pertinentes; al final repetir toda suite aislada, inventario y diff. Si falla, detener y corregir con nueva autorización/commit, sin reescribir historial para esconder resultados. Registrar SHAs reales en PR/guía, conservar snapshot.
8. Solicitar autorización aparte para push/crear un **nuevo Draft PR** a dev. No cerrar, fusionar, actualizar ni empujar al origen compartido de PR4/5; resolver coordinación de hunks solapados con mantenedores. No ejecutar despliegue. QA valida sólo SHA exacto en su entorno existente.

El candidato pasa a A para creación futura de commits por resolver la incompatibilidad verificable SS09/dev y preservar controles del alcance elegido. QA, publicación, integración y cierre de hallazgos son decisiones separadas; pendientes del mapa, privilegios, worker, locks, antimalware y limitación login no se convierten enPASS. Los cambios de infraestructura PR5 requieren revisión independiente, no se consideran requisito implícito de este subconjunto.
