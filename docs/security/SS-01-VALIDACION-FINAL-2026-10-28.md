# Validación final de SS-01 — Software-PA / SSALFER

Fecha: 2026-10-28. Rama `dev`; HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`.

## Dictamen: PENDIENTE DE VALIDACIÓN EN NAVEGADOR REAL

La corrección de código y sus regresiones aisladas son conformes con el objetivo SS-01: el texto no confiable llega como un elemento DOM a Leaflet, en lugar de una cadena interpretada como HTML. **No se cierra el hallazgo como aprobado definitivamente**, porque no se localizó un navegador utilizable para verificar apertura, cierre, posición y representación real. No se detectó una regresión reproducible dentro de la cobertura ejecutada. No hay motivo demostrado para rechazar o reimplementar la corrección.

No se modificó `mapa.js`, la prueba existente, los informes previos ni el patch. Esta ejecución sólo añade este documento y su evidencia JSON. No hubo instalación, acceso de red/backend/BD, cambios de dependencias, migraciones, commits, pushes, merges ni despliegues. No se avanzó a otros hallazgos.

## Estado inspeccionado y evidencia de código

El diff actual conserva una sola modificación funcional localizada en `frontend-ssalfer/js/mapa.js:2148–2161`: crea un span, asigna la etiqueta con textContent y entrega ese mismo elemento a capa.bindTooltip con sticky:true. Los nombres alternativos y el callback click de la capa permanecen iguales. El diff respecto a HEAD es de 7 inserciones y 2 eliminaciones. El árbol ya contenía la corrección, su prueba y documentación sin seguimiento antes de esta validación.

La cadena revisada en Leaflet 1.9.4 local (`frontend-ssalfer/js/vendor/leaflet-1.9.4/leaflet.js:5`, minificada) es:

1. bindTooltip recibe el argumento y llama a _initOverlay.
2. La implementación de capa de _initOverlay entrega el argumento a setContent.
3. setContent guarda el objeto en _content sin convertirlo en cadena y llama a update.
4. _updateContent usa innerHTML sólo cuando el contenido es una cadena; para el span elimina los hijos previos del contenedor y hace appendChild con el mismo elemento.

Esto sustenta que el span se usa efectivamente como contenido por la API de Leaflet. La prueba inspeccionada ejecuta agregarFeature real con bindTooltip simulado, captura ese elemento y después ejecuta el método _updateContent real del vendor con DOM simulado. Verifica identidad del elemento, texto exacto, sólo nodos de texto dentro del span y contentupdate; falla ante escritura en innerHTML. **No ejecuta el ciclo de vida completo de Leaflet con un DOM de navegador**, ni prueba su layout: no se presenta ese alcance como una prueba end-to-end.

La etiqueta publicada procede de properties.nombre (número de parcela, nombre de núcleo y versión DDV); cuando el valor es vacío/nulo/ausente conserva tipoLegible. La rama de trazos sigue excluida. La previsualización de coincidencias (`mapa.js:3756`) ya utiliza span/textContent; la individual (`mapa.js:3774`) sólo entrega mensajes constantes. No se encontró otro uso de bindPopup/setPopupContent en los JS propios revisados.

## Regresiones reejecutadas

Se inspeccionaron los scripts y el helper source.cjs antes de ejecutarlos. Utilizan datos GeoJSON sintéticos, VM y dobles de DOM/API. No se ejecutó la página institucional ni se solicitó ninguna tesela externa. La suite de carga sólo necesita lectura local de una versión Git histórica; sus opciones de escritura de evidencias se desactivaron.

| Archivo | Aprobadas | Fallos finales | Cobertura |
|---|---:|---:|---|
| tests/frontend-ssalfer/map-tooltip-security.cjs | 33 | 0 | Texto literal, tres tipos publicados, valores alternativos, renderer Leaflet, geometrías, índices/capas, clic y errores, descarte de proyecto obsoleto y previsualizaciones |
| tests/frontend-ssalfer/map-gis-rbac.cjs | 4 | 0 | Separación de mapa publicado y gestión interna, roles e histórico, cambios de proyecto |
| tests/frontend-ssalfer/gis-bootstrap-rbac.cjs | 10 | 0 | Inicialización de gestión tras sesión y ausencia de trabajo DOM/API al denegar |
| tests/frontend-ssalfer/map-performance.cjs | 11 | 0 | Carga geográfica, indicadores, respuestas tardías, fallos parciales y código de carga/paginación conservado |
| **Total** | **58** | **0** | **Regresión local aislada; sin navegador** |

Casos de etiquetas: texto legítimo, acentos/Unicode, &, <, >, comillas, entidades literales, marcado HTML inerte, espacios, cadena vacía, null y propiedad ausente. El marcado se comprueba como texto exacto sin nodos de elemento adicionales dentro del span simulado. Las geometrías y propiedades no se modifican; se conservan estilos, registro por capa, sticky:true y eventos click. Los casos vacíos conservan «Parcela», «Núcleo agrario» o «Derecho de vía vigente». Los espacios mantienen el comportamiento previo: no se añade trim.

Comandos ejecutados:

```sh
node --check frontend-ssalfer/js/mapa.js
node --check tests/frontend-ssalfer/map-tooltip-security.cjs
node --test --experimental-test-isolation=none --test-reporter=spec tests/frontend-ssalfer/map-tooltip-security.cjs tests/frontend-ssalfer/map-gis-rbac.cjs tests/frontend-ssalfer/gis-bootstrap-rbac.cjs
env -u F05_EVIDENCE_DIR -u F05_BASELINE_ONLY node --test --experimental-test-isolation=none --test-reporter=spec tests/frontend-ssalfer/map-performance.cjs
git diff --check
git apply --reverse --check --whitespace=error-all docs/security/SS-01-CORRECCION-2026-10-28.patch
```

La suite map-performance no pudo iniciar inicialmente por `spawnSync git EPERM` dentro del sandbox. Tras el permiso solicitado se reejecutó fuera del sandbox con 11/11 pruebas aprobadas, sin red/BD y sin escritura de evidencias. Es una limitación inicial de ejecución, no una regresión del producto. La comprobación inversa del patch usa --check: no aplica ni revierte cambios.

## Disponibilidad de navegador

No se localizaron ejecutables chromium/chromium-browser/google-chrome/firefox/playwright en PATH ni Chromium/Chrome en ubicaciones estándar revisadas. Node no resuelve playwright, @playwright/test, playwright-core, puppeteer o puppeteer-core desde raíz, frontend o /tmp. Python no tiene playwright. No hay PLAYWRIGHT_BROWSERS_PATH configurado ni caché ms-playwright utilizable. La carpeta ms-playwright-go/1.57.0 existe pero está vacía. Las cachés npm _npx inspeccionadas no proporcionaron un paquete utilizable. No se invocó npx ni ningún instalador/descargador.

Este resultado describe las ubicaciones inspeccionadas; no es un inventario exhaustivo de todo el host. No se lanzó navegador, no hay capturas ni un reporte Playwright y no se afirma haber aprobado una validación visual.

## Matriz de aceptación y límites

| Requisito | Evidencia actual | Resultado |
|---|---|---|
| Span/textContent llega a Leaflet | Flujo real del vendor y prueba del renderer con elemento capturado | Conforme en código y prueba aislada |
| Texto especial/marcado inerte literal | Texto exacto y ausencia de elementos internos en DOM simulado | Conforme en prueba aislada; DOM de navegador pendiente |
| Valores alternativos | Casos vacíos/nulos/ausentes de los tres tipos | Conforme en prueba aislada |
| Estilos, capas y eventos originales | Callback de estilo, coordenadas, índices, click y flujo de errores; único hunk de código | Conforme en cobertura aislada |
| Apariencia visual | Revisión de .leaflet-tooltip en styles/mapa.css:361; CSS sin cambios | Pendiente de navegador; CSS sin cambios no prueba identidad visual |
| Apertura y cierre real | bindTooltip/interacciones revisados estáticamente | Pendiente; las pruebas no ejercitan mouseover/mouseout en navegador |
| Posición sticky y puntero | Se conserva sticky:true y el vendor registra mousemove | Pendiente de layout e interacción real |
| Pan/zoom y anclaje | Passthrough de geometría y pruebas de carga | Pendiente de motor cartográfico real |

No se detectó un fallo reproducible que permita cambiar la lógica en este turno. La confianza es alta en el tratamiento del contenido como texto y en los invariantes cubiertos; la validación integral de interacción/visual sigue pendiente.

## Prueba pendiente para cerrar SS-01

Cuando haya navegador disponible y autorizado, usar un contexto efímero con toda solicitud de red bloqueada. Inyectar desde archivos locales Leaflet JS/CSS y las funciones reales del mapa en una página de ensayo; no cargar la página institucional ni sus scripts de sesión, servicios de mapas externos o backend. Crear únicamente capas vectoriales GeoJSON sintéticas, sin tileLayer externo. No descargar herramientas durante esa prueba sin autorización.

Verificar mediante el DOM real que el contenido del tooltip es el mismo span, que textContent coincide exactamente y que su interior sólo contiene texto, incluso con marcado HTML inerte. Para cada tipo y etiqueta alternativa comprobar hover, movimiento sticky, salida/cierre y reapertura, clic con un receptor de detalle sintético, pan/zoom y cambios de capas. Verificar posición respecto a geometría/puntero y estilos computados, sin cambios de coordenadas ni eventos. Registrar resultado, versión del navegador y evidencia sintética. Aprobar definitivamente sólo al completar esos casos sin regresiones.

## Evidencia y conservación

Evidencia estructurada: [SS-01-VALIDACION-FINAL-2026-10-28.json](SS-01-VALIDACION-FINAL-2026-10-28.json).

| Archivo validado | SHA-256 conservado |
|---|---|
| `frontend-ssalfer/js/mapa.js` | `2d051e4204701a9bb63775422bc882f11b10c138f7ee8f577c0a9d94b229bfab` |
| `tests/frontend-ssalfer/map-tooltip-security.cjs` | `1ae6ad7471ef4a565a65d39d3ed84a8165a2511ae08279f365e224f528b0d192` |
| `docs/security/SS-01-CORRECCION-2026-10-28.patch` | `00d04c2e9e5bb5bf4456b766caa04c900ac1f71d40f674ae397b9f47c056c0bf` |

Los hashes se compararon antes y después de las pruebas; los documentos previos también se conservaron. El índice Git no cambió. Se detiene esta fase con dictamen **pendiente de validación en navegador real**, conservando íntegra la corrección actual.
