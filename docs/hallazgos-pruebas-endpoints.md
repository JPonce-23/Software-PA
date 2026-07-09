## Bug: geometria_wkt regresa null en POST y PUT (todos los módulos geoespaciales)

**Alcance**: afecta a tramos, frentes, núcleos, tramo_nucleo y afectaciones.

**Descripción**: los endpoints GET (listar y por ID) devuelven correctamente
la geometría en formato WKT gracias a `.ST_AsText().label('geometria_wkt')`
en el query. Sin embargo, los endpoints POST y PUT de estos 5 módulos 
fuerzan `resp["geometria_wkt"] = None` en la respuesta, en vez de convertir 
la geometría recién guardada.

**Impacto**: cualquier flujo de frontend que dependa de la respuesta 
inmediata de un POST/PUT (por ejemplo, para dibujar en el mapa sin 
tener que recargar con un GET) va a recibir null aunque el dato se 
haya guardado correctamente.

**Fix sugerido**: en vez de `resp["geometria_wkt"] = None`, hacer una 
consulta adicional con ST_AsText después del commit, o usar 
geoalchemy2.shape.to_shape() sobre el objeto recién refrescado.


## Mejora necesaria: GET /api/nucleos - parámetro "tramo" ambiguo

**Estado actual:** el filtro funciona (probado con tramo=Tramo de 
prueba manual, regresa el núcleo correcto), pero su diseño genera 
riesgo a futuro:

1. Recibe un string que debe coincidir EXACTO con nombre_tramo 
   (sensible a mayúsculas, acentos, espacios). Cualquier variación 
   de captura del nombre rompe la búsqueda silenciosamente 
   (no da error, solo regresa vacío).
2. Calcula la relación con ST_Intersects en vez de usar la tabla 
   tramo_nucleo, que ya existe para esto. Si algún día la geometría 
   del núcleo o el tramo se edita (ej. se corrige un polígono mal 
   capturado), este endpoint podría dejar de encontrar relaciones 
   que sí están registradas oficialmente en tramo_nucleo, o viceversa.

**Sugerencia concreta:** cambiar el parámetro de "tramo: str" a 
"id_tramo: int", y filtrar mediante JOIN mediante tramo_nucleo 
en vez de ST_Intersects. Esto es más rápido, más confiable, y 
consistente con cómo se relacionan las demás entidades en el sistema.