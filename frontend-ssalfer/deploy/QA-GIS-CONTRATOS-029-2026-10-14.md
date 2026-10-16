# Revisión frontend GIS 029 — 14 de octubre de 2026

Rama: `feature/integracion-mq-deploy`. Se conservaron los cambios locales anteriores. Sin commit, push, despliegue, reconstrucción Docker, migraciones ni cambios de datos QA.

## Qué cambió

- El diagnóstico registrado por backend es la explicación principal del resultado. Los códigos tienen etiquetas comprensibles y la evidencia se puede desplegar en el detalle o en el listado de elementos sin coincidencia.
- Los históricos sin diagnóstico muestran «Diagnóstico no disponible para este resultado histórico», sin atribuirles causas actuales. Cuando el campo es null se conserva la orientación anterior en la vista actual, compatible con respuestas antiguas.
- El buscador encuentra mensaje, código, campos evaluados y evidencia. El CSV añade ciclo, origen, códigos, campos y evidencia, conservando valores originales y protección contra fórmulas.
- El universo administrativo actual y el utilizado por la conciliación aparecen separados. Null se muestra como «No disponible»; 0 conserva su significado. La disponibilidad parcial describe información histórica demostrable, no falta de registros. Sólo se indican cambios cuando dos conteos conocidos difieren.
- Cada elemento usa su propio id de ciclo para resolver propuestas. El modal histórico presenta el universo y diagnóstico del ciclo consultado, sin sustituirlos por los actuales.
- El historial incluye el filtro Disponibilidad: Sólo activas, Activas y dadas de baja, Sólo dadas de baja. La consulta histórica utiliza el parámetro backend en todas las lecturas dependientes.
- Administradores y geógrafos pueden solicitar la baja de una carga activa previsualizada o con error. El formulario requiere motivo de 3–500 caracteres y confirmación. El servidor decide si hay dependencias protegidas; el frontend conserva su error y no promete que la baja siempre será posible.
- Una baja exitosa actualiza historial y panel abierto. Las cargas inactivas tienen identificación visible y son de sólo lectura, incluido su mapa temporal. No hay reactivación, borrado físico ni restauración de versiones.
- Se conserva DDV. Trazo del proyecto sigue oculto para nuevas cargas y en el mapa; sus cargas anteriores continúan consultables en el historial.

## Archivos de implementación

- `js/api/geoespacial.js`: lecturas históricas compatibles y baja mediante ClienteAPI/CSRF.
- `js/conciliacionGeoespacial.js`: diagnósticos, universos, CSV, ciclo propio y protección de inactivas.
- `js/gestionGeoespacial.js`: filtros de disponibilidad, baja, refresco y protección de previsualización antigua.
- `js/mapa.js` y `js/utils/mapaConciliacion.js`: consulta explícita de geometrías históricas sin alterar el mapa vigente.
- `pages/gestionGeoespacial.html` y `styles/conciliacionGeoespacial.css`: filtro, estados históricos y presentación adaptable de universos.

Se actualizó `PENDIENTES-BACKEND-GESTION-GEOESPACIAL.md` para distinguir observaciones anteriores de capacidades ya disponibles.

## Pruebas ejecutadas

Desde la raíz del repositorio:

```powershell
node frontend-ssalfer/deploy/qa-gis-contratos-029.cjs
node frontend-ssalfer/deploy/qa-conciliacion-orientacion.cjs
node frontend-ssalfer/deploy/qa-mapa-coincidencias.cjs
node frontend-ssalfer/deploy/qa-mapa-ux-2026-10-13.cjs
git diff --check
```

Las cuatro suites finalizaron con código 0. Se ejecutó además `node --check` para los cinco JavaScript de implementación modificados y el nuevo script QA. La revisión UTF-8 no encontró BOM, caracteres de sustitución ni patrones de mojibake en los archivos tocados.

Las suites usan Edge sin interfaz visible, archivos del working tree y respuestas interceptadas. No ejecutan su flujo contra datos QA. La suite nueva bloquea toda conexión que no tenga una respuesta local simulada. Se verificaron:

1. Diagnósticos registrados, históricos, ausentes y códigos futuros; escape de texto recibido como HTML.
2. Evidencia con null y 0, diferencias de formato y conservación literal de 016.
3. Búsqueda y CSV de diagnósticos, conservando paginación y accesibilidad existentes.
4. Universo actual frente al histórico; no comparar null con cero; explicar diferencias demostradas.
5. Elemento perteneciente al ciclo 6 aunque exista un ciclo global 7; propuestas filtradas por su ciclo.
6. Parámetro histórico en importación, resumen, elementos, candidatos, decisiones, geometrías y ciclos; mapa individual y mapa de coincidencias.
7. Ausencia de controles de escritura en inactivas y rechazo de eventos de botones obsoletos.
8. Baja cancelada sin POST, motivo demasiado corto sin envío, CSRF, errores 403/404/409/422 conservados y éxito con refresco del panel y listado.
9. Permisos de administrador, geógrafo, visualizador y operador; confirmación conjunta sigue exclusiva de administrador en frontend.
10. Regresiones: 997 parcelas en listado/CSV, filtros sobre 205 cargas, cierre protegido, confirmación conjunta, errores parciales y respuestas tardías.
11. Mapa: selección reversible, ampliación, capas, resumen, limpieza al cambiar proyecto y móvil sin desbordamiento.

Evidencia visual: `qa-gis-universos-029-movil.png`. Usa datos simulados. La etiqueta literal `<b>Texto literal</b>` demuestra que el contenido recibido se escapa; no es texto del producto ni de registros reales.

## Límites y contrato

No se encontraron contradicciones que requieran cambios de backend. El diagnóstico se refiere a la comparación original; no reemplaza decisiones posteriores. Los códigos futuros muestran el mensaje del servidor. Las variantes con ceros iniciales son indicios y no generan equivalencias, candidatos ni decisiones.

El backend restringe la baja a estados y dependencias que puede validar; algunos pipelines antiguos no permiten una baja segura. No se replican esas reglas completas en frontend. El resumen actual se recalcula en backend y el utilizado corresponde al último ciclo global; el detalle del elemento conserva su ciclo propio.

Los filtros de estado, tipo y fecha siguen aplicándose sobre todas las páginas descargadas del historial. El filtrado por servidor para historiales muy grandes sigue siendo una mejora pendiente, al igual que una eventual operación conjunta restringida por backend a administrador. No se inventaron endpoints para estas mejoras.

Las pruebas acreditan el comportamiento del frontend frente al contrato simulado y las regresiones locales. No sustituyen una validación integrada de escritura con el backend desplegado; no se hicieron escrituras reales, según las restricciones de esta ronda.
