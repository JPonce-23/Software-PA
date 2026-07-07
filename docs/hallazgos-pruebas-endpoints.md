Bug: GET/POST/PUT de /api/afectaciones fuerzan geometria_wkt = None 
en la respuesta (líneas ~406, ~414, y presumiblemente en get_afectacion_by_id),
en vez de convertir la columna geometria_afectacion a texto WKT como sí 
se hace en otros endpoints (tramos, frentes, núcleos).

Impacto: cualquier pantalla que dependa de leer la geometría de una 
afectación (ej. Mapa.jsx) va a recibir null aunque el dato exista 
correctamente en la base de datos.

Fix sugerido: aplicar el mismo patrón de conversión WKT que usan 
los demás endpoints geoespaciales.