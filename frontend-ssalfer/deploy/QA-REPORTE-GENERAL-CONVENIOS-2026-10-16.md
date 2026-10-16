# QA — Reporte general de convenio — 16/10/2026

## Implementación
Se incorporó localmente el commit publicado 24eb4c7, sin crear commit ni hacer push. Se conectaron los tres endpoints documentados. La nueva pestaña consulta estados con registros del proyecto, muestra individuales paginados y exporta ambas categorías mediante la consulta completa. No hay consultas por convenio para construir este reporte.

Se agregó SheetJS CE 0.20.3 local, con licencia Apache 2.0. Se mantienen las otras cuatro pestañas y su exportación CSV. Las pestañas esperan la carga inicial de catálogos para evitar que una selección temprana sea reemplazada por la inicialización.

## Correspondencia Excel
- Dos hojas: Convenios individuales y Convenios colectivos; doce columnas cada una.
- Individuales: una fila por convenio, números de parcelas reunidos en una celda, sin perder ceros iniciales. Montos 90% y 100% independientes, sin calcular porcentajes ni repetir montos por parcela.
- Colectivos: una fila por destino. El número de convenio puede repetirse. Los pares de fechas RAN de asamblea y convenio se conservan separados con los encabezados solicitados.
- Fechas como fechas Excel; montos y superficies como números cuando la precisión de Excel lo permite. Decimales que exceden esa precisión se guardan como texto exacto.
- Datos ausentes quedan vacíos, no se convierten a cero. Superficie individual pendiente de definición: no se reemplaza por superficie afectada o declarada. Superficies colectivas incompletas no se completan con subtotales.
- Se incluyen instrumentos administrativamente activos; no implica obligaciones económicas vigentes. Fechas RAN corresponden a primeros hitos históricos.
- Se rechaza respuesta completa inconsistente o límite de 10,000 convenios: no se descarga un reporte parcial.

## Evidencias
Prueba con API simulada basada en el ejemplo del contrato: descarga nativa XLSX, filtro estatal aplicado a exportación, proyecto con solo colectivos, categorías vacías, 403, 413 y respuesta incompleta sin descarga, vuelta a las cuatro pestañas CSV, sin errores JavaScript.

Prueba real de solo lectura en 5184, después del inicio de sesión: México-Querétaro (3), 0 individuales y 66 colectivos, 3 entidades disponibles. Descarga real con dos hojas. La hoja colectiva tiene 80 filas de datos porque algunos convenios tienen varios destinos. No se modificaron registros.

Verificación independiente con openpyxl: los tres archivos de evidencia son XLSX válidos con dos hojas y doce columnas. Se verificaron los pares de encabezados RAN y ausencia de fórmulas en el ejemplo sintético.

Archivos en outputs/reporte-convenios-2026-10-16:
- Reporte-general-Mexico-Queretaro.xlsx
- Convenios-QA-integracion.xlsx y Convenios-QA-solo-colectivos.xlsx
- reporte-general-MQ.png y reporte-general-integrado.png
- qa-real.json y qa-simulada.json

Scripts reproducibles en deploy: qa-convenios-real-2026-10-16.cjs (credenciales por variables de entorno) y qa-convenios-integracion-2026-10-16.cjs.

## Cómo probar
Ruta: México-Querétaro → Reportes → Convenios → Reporte general de convenio.
1. Seleccionar México-Querétaro. Debe aparecer 0 individuales y 66 colectivos con la base QA actual.
2. Abrir Estado: debe mostrar Todos los estados y solo las tres entidades con registros.
3. Exportar Excel. Abrir ambas hojas: individuales sin registros; colectivos con destinos y fechas disponibles. No confundir filas por destino con cantidad de convenios.
4. Elegir un estado y exportar nuevamente. Ambas hojas deben respetar ese filtro.
5. Volver a Valores declarados, Impactos, Impactos por periodo y Cobertura de impactos: mantienen CSV.

## Límites y observaciones
La prueba con individuos se hizo con datos sintéticos porque México-Querétaro no tiene individuos. No se ejecutaron de nuevo las 100 pruebas del equipo backend. La captura real conserva un aviso de referencias faltantes originado por la consulta anterior de Valores declarados; no impidió consultar ni exportar el reporte general. Su revisión pertenece a esa consulta anterior.

El frontend QA fue reconstruido. Una segunda reconstrucción falló por DNS de Docker Hub; se copió únicamente el último ajuste de carga inicial al contenedor local. El archivo fuente queda preparado para la siguiente reconstrucción. No se hizo despliegue remoto.

## Ajuste de vista previa solicitado el 16/10/2026
Selector Individuales / Colectivos junto a la paginación, con encabezados y navegación correspondientes a cada grupo. Se conserva Individuales como selección inicial. México-Querétaro muestra sus filas al elegir Colectivos. Fechas de asamblea y convenio se distinguen también en la tabla.

Búsqueda habilitada sobre la página visible, sin distinguir mayúsculas ni acentos. El texto informa su alcance: no modifica la exportación completa. Limpiar filtros restablece estado y búsqueda. Consultar reporte se oculta solo en esta pestaña, donde los cambios consultan automáticamente.

Observaciones traducidas a español natural: superficie individual sin definición, asamblea celebrada no vinculada, clasificación incompleta, falta de afectaciones/unidades activas, fechas históricas de varios trámites RAN. La nota técnica extensa ya no encabeza el flujo. No cambia la información ni las reglas de exportación.

Prueba simulada adicional: cambio a colectivos, encabezados de destinos, búsqueda sin coincidencias y recuperación al borrar texto, botón Consultar oculto, descarga y retorno a CSV.
