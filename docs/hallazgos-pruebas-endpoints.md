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