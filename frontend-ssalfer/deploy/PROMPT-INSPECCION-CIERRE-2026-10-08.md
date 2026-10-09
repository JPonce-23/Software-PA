# Prompt de inspección: cierre frontend SSALFER contra backend schema 028

Inspecciona el resultado de la integración realizada el 8 de octubre de 2026 en `C:\Proyectos\Software-PA-integracion-mq`, rama `feature/integracion-mq-deploy`, base `8b47139`. Backend integrado: `feature/backend-logica` / `d408ed1`. El objetivo es comprobar que el frontend quedó listo para QA manual, capacitación y posterior deploy productivo.

## Alcance y reglas

Trabaja sobre `frontend-ssalfer/`. Puedes leer backend, tests, migraciones y documentación para comprobar contratos, pero no los modifiques. No hagas commit ni push. Conserva las modificaciones existentes, incluida `.gitattributes`, y no alteres `.qa-backups/`. No utilices credenciales guardadas en archivos: recibe las de una cuenta de QA autorizada mediante variables de entorno. No escribas datos reales de negocio durante pruebas sin identificar y autorizar previamente el caso de prueba.

Backend QA: `http://127.0.0.1:8010`; frontend QA: `http://127.0.0.1:5184`. Comprueba `/health` y el OpenAPI real antes de evaluar errores. El estado esperado es schema 28. Prioridad: respuesta real/OpenAPI, código integrado, tests backend, migraciones, documentación. Las listas antiguas de bloqueos no sustituyen la evidencia actual.

Lee primero `deploy/QA-CIERRE-2026-10-08.md`, `deploy/PROPUESTA-ROLES-PANTALLAS-2026-10-08.md` y los JSON de resultados `qa-cierre-*`, `qa-proteccion-resultados.json` y `qa-despliegue-cierre-resultados.json`. El inventario `qa-cierre-archivos.json` distingue los archivos tocados en esta ronda del resto de cambios anteriores sin commit.

## Cambios realizados y qué revisar

### 1. Protección de pantallas y retorno al iniciar sesión

Se agregó `js/utils/proteccion.js` al dashboard y a las 34 pantallas de `pages/`, con comprobación central de sesión en `api/auth.js` y espera de autorización previa a las solicitudes de negocio en `api/cliente.js`. `Index.html` conserva un destino local seguro mediante `return_to`.

- En una ventana sin sesión, pegar directamente la URL de ORV, mapa, auditoría, documentos y las demás pantallas. Deben pedir inicio de sesión sin mostrar datos ni enviar consultas de negocio.
- Tras entrar, regresar a la pantalla solicitada y conservar su contexto.
- Rechazar retornos a dominios externos o rutas fuera de las pantallas locales admitidas.
- Probar sesión vencida, 401 de negocio, 403 al comprobar sesión y pérdida de red. El fallo de red debe ofrecer reintento sin dejar contenido privado visible ni errores JavaScript sin manejar.
- Comprobar recarga y navegación atrás/adelante después de cerrar sesión.
- La protección visual no sustituye la autorización de la API. Verificar cuentas y proyectos realmente asignados antes de producción.

### 2. Roles y propuesta de pantallas

Existen `admin`, `operador`, `visualizador` y `geografo`. La tabla entregada es demostrativa, no una creación de roles o permisos nuevos. Revisar con usuarios la asignación propuesta. Comprobar que operador captura información administrativa/documental, visualizador consulta, geógrafo gestiona GIS y administrador accede a administración y auditoría, siempre sujeto al permiso real de cada endpoint y del proyecto.

### 3. Mapa publicado y derecho de vía

`mapa.js`, `mapa.html` y `mapa.css` incorporan DDV como capa independiente con control, estilo, selección y detalle. Se retiró el aviso incorrecto de que lo confirmado no se publica. Se corrigió el mensaje vacío que seguía visible al seleccionar geometrías.

- Consumir el FeatureCollection del proyecto para trazo, DDV, núcleos y parcelas. No consultar geometrías globales para sustituir el mapa del proyecto.
- Activar/desactivar trazo y DDV por separado, con ratón y teclado; revisar leyenda, detalle y ausencia del mensaje vacío al seleccionar.
- Verificar geometría vigente después de confirmar mediante un caso backend autorizado y su fallback legacy según respuesta del servidor.
- Cambiar rápidamente de proyecto: no deben mezclarse capas ni aceptarse respuestas tardías.
- Mantener diferenciada la previsualización naranja. No calcular ni sobrescribir superficies administrativas con JavaScript.

### 4. Lectura y paginación GIS

Se usan `usuario_revision_nombre`, `creado_por_nombre`, `usuario_nombre`, `revision.destino` y `ciclo.universo_destinos`. Se eliminaron búsquedas auxiliares de usuarios y consultas por cada núcleo/parcela candidato. Se agregaron variantes paginadas en `api/geoespacial.js` y metadatos optativos en `ClienteAPI`.

- Mostrar nombres históricos aunque el actor esté inactivo; si son nulos, usar texto humano sin IDs visibles.
- Mostrar destino de revisiones desde `destino` y candidatos mediante la pareja proyecto-núcleo/parcela en `universo_destinos`. Vigilar la pestaña Red para descartar N+1.
- Importaciones, elementos, ciclos y revisiones deben usar `X-Total-Count`. Probar 0, 25, 26 y más de 50 resultados; primera, intermedia y última página.
- Verificar total filtrado por estado de conciliación y filtros de revisiones por estado, capa y tipo de cambio. No usar `importacion.total_features` como total filtrado.
- Comprobar que `ClienteAPI` conserva JSON normal por defecto, blob, 204, errores, CSRF y señales de cancelación. `conMetadatos` es optativo.
- Repetir decisiones, confirmación, conflictos 409/422, idempotencia y cambio de proyecto; distinguir pruebas interceptadas de persistencia real.

### 5. Documentos consolidados y clasificación 028

El listado usa `GET /proyecto-nucleo/{id}/documentos`, agrupa por documento, conserva procedencias y utiliza `version_vigente`. El gestor se abre bajo demanda. El catálogo de tipos llega de `/catalogos/tipos-documento`; se muestra `clasificacion.nombre` o el texto legacy.

- Verificar un mismo documento con varios vínculos y requisitos: una fila con todas sus procedencias, sin IDs como mecanismo operativo.
- Carga inicial sin recorrer todos los destinos ni pedir versiones por documento. El historial de versiones sí puede consultarse al abrirlo.
- Ver/descargar, historial, documento sin archivo, vacío, 403/404 y recarga tras cambios.
- Alta: enviar `estado` e `id_tipo_documento`; nunca simultáneamente el texto legacy. OTRO requiere descripción.
- Legacy: mantener texto libre, editar metadatos sin forzar clasificación y permitir clasificación explícita.
- Catalogado: editar metadatos sin enviar clasificación nula; reclasificar sólo si el usuario lo elige.
- Tipo histórico inactivo visible, pero no elegible como nueva clasificación. No inferir FK por texto.
- En auditoría, mostrar el nombre del tipo documental cuando el catálogo lo permita, preservando el detalle técnico completo.

### 6. Personas

El directorio incorpora búsqueda autorizada `GET /personas` por exactamente un criterio: nombre (`q`), CURP o RFC. El directorio del núcleo sigue disponible bajo demanda; seleccionar no crea asociaciones.

- Validar nombre de 2–300 caracteres, CURP hasta 18 sin exigir longitud completa y RFC hasta 13 sin asumir unicidad.
- Conservar acentos y tratar %, _ y barra invertida como texto literal; no ofrecer coincidencia difusa inexistente.
- Usar limit/skip; resultados mínimos con nombre, CURP y RFC; selección por contexto sin IDs manuales.
- Un 200 con lista vacía sólo indica ausencia de coincidencias autorizadas. No afirmar que la persona no existe globalmente.
- Administrador/operador pueden registrar; roles de lectura no deben ver esa acción. POST 409 debe orientar a buscar la persona o revisar acceso.
- Probar integración con ORV, comparecientes e intervinientes; sin precargar un padrón global.

### 7. Integrantes de ORV

Se eliminaron bajas almacenadas únicamente en memoria. La lista consulta `incluir_historico` e `incluir_bajas`, usa `vigente`, `activo`, `fecha_baja` y `motivo_baja` del backend y conserva filtros en la URL.

- false/false: vigentes activos; true/false: histórico activo; false/true: vigentes incluyendo bajas; true/true: todo lo autorizado.
- Baja visible tras F5 con el filtro adecuado; fechas dd-mm-yyyy y motivo legible.
- Reactivar no borra `fecha_fin`: una participación finalizada debe seguir finalizada.
- Finalizar, editar y reactivar deben refrescar desde el servidor; revisar 409 y permisos.
- FIFONAFE y directorio contextual consultan histórico activo con true/false, excluyendo bajas administrativas.

### 8. Documentos de actividad de campo

Se añadió `actividad_campo` al contexto documental y un botón Documentos por actividad, usando `id_actividad` internamente. El rótulo utiliza tipo, fecha, resultado y observaciones reales.

- Desde una actividad: consultar, registrar, vincular, subir/descargar versiones y revisar procedencia según rol.
- Verificar la presencia de esos documentos en el consolidado del núcleo.
- Confirmar 403/404 humanos y ausencia de IDs manuales. No simular una relación que el backend no admita.

### 9. Catálogo RAN

La búsqueda conserva acentos y pide al servidor entidad/municipio/q con máximo 100 resultados. No agrega paginación inexistente ni descarga todo el catálogo.

- Acentos, combinación de filtros, vacío y nombres humanos.
- A 100 resultados, pedir que se refine la búsqueda; no enviar skip ni pedir una página 2.
- Seleccionar correctamente y mantener claramente separada el alta excepcional/manual existente.

### 10. Regresión y pruebas técnicas

Ejecutar los scripts relevantes de `frontend-ssalfer/deploy/`, con `QA_USER` y `QA_PASSWORD` en el entorno, sin escribir esas credenciales en los archivos:

- `qa-cierre-2026-10-08.cjs`
- `qa-cierre-gis-orv-2026-10-08.cjs`
- `qa-cierre-adicional-2026-10-08.cjs`
- `qa-proteccion-2026-10-08.cjs`
- `qa-despliegue-cierre-2026-10-08.cjs`
- `qa-geoespacial-conciliacion.cjs`, `qa-gis-ux-2026-10-06.cjs`, `qa-mapa-aislamiento.cjs`, `qa-ronda6.cjs`
- `qa-ux-documentos-proyectos.cjs`, `qa-marco.cjs`, `qa-ronda6-reportes.cjs`, `qa-dashboard-excel-2026-10-06.cjs`

Los scripts usan Edge/Playwright disponible en esta máquina. `qa-mapa-aislamiento.cjs` permite `QA_LOCAL_FILES=1` y `QA_PLAYWRIGHT`. El smoke de despliegue usa exclusivamente los archivos servidos por el contenedor.

Verificar `node --check`, UTF-8 y `git diff --check`. Probar menús a 1440 y 390 px, teclado, formularios, reportes CSV y Excel cliente. Preservar el trabajo de rondas anteriores. No cambies una aserción para esconder una regresión; documenta los cambios de contrato que justifiquen actualizar fixtures.

El frontend ya fue construido y recreado en QA; si se cambia código, repetir únicamente build/recreate de `frontend_ssalfer` con los compose y `.env.qa-local` existentes. No reconstruir backend, bajar servicios ni tocar base de datos. Volver a comprobar hashes de archivos servidos y `/health`.

## Límites de la evidencia disponible

Las lecturas reales verificaron HTTP 200 y totales del backend. El proyecto QA consultado no tenía geometría publicada ni documentos consolidados; sus escenarios poblados se validaron con respuestas interceptadas. Las escrituras de negocio y las presentaciones de otros roles se probaron con fixtures. No equivalen a un recorrido real de persistencia ni a una validación completa de asignaciones con cuentas de cada rol. Esa validación corresponde a la inspección manual autorizada.

## Fuera de alcance / etapa 2

No convertir en bloqueos de este cierre: proyecto completado, número de empleado, responsable como FK de usuario, exportación XLSX del backend, cálculo oficial de área GIS o endpoint de configuración de tiles, si siguen ausentes del contrato. Mantener la exportación Excel cliente existente. No resucitar bloqueos históricos que el backend actual ya resolvió.

## Entrega de la inspección

Entregar una matriz por caso con: aprobado/fallido/no ejecutado, pantalla, rol, precondiciones, endpoint, petición, respuesta, esperado, obtenido, captura y tipo de evidencia (real o interceptada). Para cada defecto reproducible indicar si pertenece al frontend o backend; redactar una lista separada de incidencias backend con evidencia, sin inferir bugs de una respuesta vacía autorizada.

Terminar con **READY FOR MANUAL QA** o **NOT READY**. No afirmar que está desplegado en producción ni que se probaron escrituras reales si sólo hubo fixtures. Adjuntar los riesgos pendientes de validación manual y el inventario exacto de archivos modificados.
