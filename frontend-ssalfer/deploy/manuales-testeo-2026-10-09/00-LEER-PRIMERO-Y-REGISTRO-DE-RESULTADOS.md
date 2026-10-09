# Manuales de testeo de SSALFER — guía de ejecución

Preparados el **9 de octubre de 2026**, sobre los cambios del cierre frontend del 8 de octubre. Se entregan los tres bloques completos para asignarlos a distintos testers o ejecutarlos en días diferentes.

## Qué debe testearse

| Bloque | Contenido | Casos |
|---|---|---|
| [1. Acceso, navegación y consulta](01-ACCESO-NAVEGACION-Y-CONSULTA.md) | Inicio de sesión, enlaces protegidos, dashboard, barra lateral, roles, Excel/CSV y auditoría. | A01–A13 |
| [2. Personas, ORV y documentos](02-PERSONAS-ORV-Y-DOCUMENTOS.md) | Búsquedas, integrantes, filtros, bajas/reactivaciones, documentos, clasificación y actividades. | B01–B20 |
| [3. Mapa, geoespacial y RAN](03-MAPA-GEOESPACIAL-Y-CATALOGO-RAN.md) | Capas, archivos, conciliación, publicación, revisiones, páginas y vinculación de núcleos. | C01–C18 |

Son **51 casos principales**, algunos con variantes por rol, filtro o cantidad de registros. Cada manual explica qué debe verse, cómo entrar, qué hacer y qué resultado esperar. No es necesario leer código ni utilizar herramientas de desarrollo para ejecutarlos.

## Documento para evaluar los permisos

Consultar la [Propuesta de accesos, acciones y privilegios por rol](04-PROPUESTA-DE-ACCESOS-ACCIONES-Y-PRIVILEGIOS.md). Incluye pantallas, acciones, límites y decisiones pendientes para administrador, operador, visualizador y geógrafo. Es una propuesta para discusión; no modifica los permisos actuales ni añade casos al conteo de 51 pruebas.

## Preparación del responsable de QA

- Dirección del entorno: `http://127.0.0.1:5184`, si se prueba en esta misma máquina. Para otro equipo, proporcionar su dirección autorizada; 127.0.0.1 siempre se refiere al equipo donde se abre el navegador.
- Cuentas de prueba y rol. Entregar contraseñas por el medio acordado, no escribirlas en el reporte.
- Proyectos asignados a cada cuenta y nombres de los núcleos, personas, órganos, integrantes, actividades y documentos preparados.
- Archivos documentales y geoespaciales válidos, problemáticos y versionados para los casos indicados.
- Referencias de cantidades, nombres y geometrías esperadas. No basta con que la pantalla se vea bien: hay que compararla con datos conocidos.
- Registros sobre los que se permite guardar, dar de baja, reactivar o confirmar, y responsable de revisarlos después.

Si falta un registro, archivo o cuenta, marcar **No ejecutado** y explicar qué falta. No aprobar un caso poblado sólo porque su lista apareció vacía.

## Orden sugerido

1. Comenzar con A01–A11 y A13 para comprobar acceso, navegación y cuentas.
2. Ejecutar el manual 2. Después de B18, regresar a A12 para comprobar la clasificación documental en Auditoría.
3. Ejecutar el manual 3. Si C12 necesita vincular un núcleo, realizar C17 antes de repetir la conciliación.
4. Repetir las pantallas principales en ventana angosta y cerrar con la revisión de resultados.

Puede repartirse un bloque por tester. Coordinar modificaciones sobre un mismo registro para no confundir el trabajo de otro tester con una falla.

## Aclaraciones respecto del ejemplo de dashboard

- Actualmente existen **Exportar dashboard (Excel)** y **CSV de respaldo**. Un CSV puede abrirse en Excel, pero no es un libro con varias hojas y gráficos.
- Auditoría permite al administrador filtrar movimientos por usuario; no está limitada automáticamente a sus propios movimientos.
- Los accesos dependen del rol, el proyecto y la pantalla. El menú del dashboard del administrador tiene tres accesos; las pantallas interiores pueden ofrecer sólo cambio de contraseña y cierre de sesión.
- Las cantidades se comparan con el proyecto de prueba, no con cifras fijas de una captura antigua.

## Ficha para registrar cada resultado

Copiar esta ficha por caso y variante relevante:

**Caso y título:**  
**Fecha y hora:**  
**Tester:**  
**Navegador y tamaño de pantalla/dispositivo:**  
**Cuenta de prueba y rol, sin contraseña:**  
**Proyecto, núcleo y registro utilizados:**  
**Datos o archivo de prueba:**  
**Pasos realizados:**  
**Resultado esperado según el manual:**  
**Resultado observado:**  
**Estado: Aprobado / Falló / No ejecutado:**  
**¿Se repite después de recargar o volver a entrar?:**  
**Captura o video:**  
**¿Se guardaron cambios? ¿Cuáles?:**  
**Observaciones o preparación faltante:**

Capturar título de pantalla, filtros y aviso relevante, sin contraseñas ni información personal ajena a la prueba. Si falla una descarga, conservar el archivo de QA y anotar qué botón se utilizó.

## Hoja de control

| Caso | Estado | Evidencia/observación |
|---|---|---|
| A01 | Pendiente | |
| A02 | Pendiente | |
| A03 | Pendiente | |
| A04 | Pendiente | |
| A05 | Pendiente | |
| A06 | Pendiente | |
| A07 | Pendiente | |
| A08 | Pendiente | |
| A09 | Pendiente | |
| A10 | Pendiente | |
| A11 | Pendiente | |
| A12 | Pendiente | |
| A13 | Pendiente | |
| B01 | Pendiente | |
| B02 | Pendiente | |
| B03 | Pendiente | |
| B04 | Pendiente | |
| B05 | Pendiente | |
| B06 | Pendiente | |
| B07 | Pendiente | |
| B08 | Pendiente | |
| B09 | Pendiente | |
| B10 | Pendiente | |
| B11 | Pendiente | |
| B12 | Pendiente | |
| B13 | Pendiente | |
| B14 | Pendiente | |
| B15 | Pendiente | |
| B16 | Pendiente | |
| B17 | Pendiente | |
| B18 | Pendiente | |
| B19 | Pendiente | |
| B20 | Pendiente | |
| C01 | Pendiente | |
| C02 | Pendiente | |
| C03 | Pendiente | |
| C04 | Pendiente | |
| C05 | Pendiente | |
| C06 | Pendiente | |
| C07 | Pendiente | |
| C08 | Pendiente | |
| C09 | Pendiente | |
| C10 | Pendiente | |
| C11 | Pendiente | |
| C12 | Pendiente | |
| C13 | Pendiente | |
| C14 | Pendiente | |
| C15 | Pendiente | |
| C16 | Pendiente | |
| C17 | Pendiente | |
| C18 | Pendiente | |

## Cuándo cerrar un bloque

Todos los casos aplicables deben tener resultado y evidencia para los cambios relevantes y cada falla. Los No ejecutados quedan pendientes con su causa; no equivalen a aprobación. Una escritura que no se comprobó después de recargar debe quedar expresamente pendiente.

Las pruebas automatizadas anteriores comprobaron varios comportamientos con datos simulados, sin guardar información real de negocio. Estos manuales permiten comprobar recorridos con cuentas y datos de prueba autorizados, incluyendo permanencia de los cambios tras recargar.

Reportar cada falla como diferencia entre lo esperado y lo observado. No pedir al tester que adivine si se trata de pantalla o servidor; el equipo técnico determinará su origen con la evidencia entregada.
