## Bug: geometria_wkt regresa null en POST y PUT (todos los módulos geoespaciales)

**Estado: RESUELTO** (corregido en feature/backend-logica, verificado 
en tramos, frentes, núcleos, tramo_nucleo y afectaciones — también se 
corrigieron los GET by ID que usaban get_entity_by_id genérico).

**Alcance**: afectaba a tramos, frentes, núcleos, tramo_nucleo y afectaciones.

**Descripción**: los endpoints GET (listar y por ID) devuelven correctamente
la geometría en formato WKT gracias a `.ST_AsText().label('geometria_wkt')`
en el query. Sin embargo, los endpoints POST y PUT de estos 5 módulos 
forzaban `resp["geometria_wkt"] = None` en la respuesta, en vez de convertir 
la geometría recién guardada.

**Impacto**: cualquier flujo de frontend que dependiera de la respuesta 
inmediata de un POST/PUT (por ejemplo, para dibujar en el mapa sin 
tener que recargar con un GET) recibía null aunque el dato se 
hubiera guardado correctamente.

**Fix aplicado**: se reemplazó `resp["geometria_wkt"] = None` por una 
consulta con ST_AsText después del commit, filtrando por el ID del 
registro recién creado/actualizado.

---

## Mejora necesaria: GET /api/nucleos - parámetro "tramo" ambiguo

**Estado: PENDIENTE**

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

---

## Bug crítico: GET /api/nucleos regresa un campo "estatus" aleatorio, no real

**Estado: PENDIENTE — prioridad alta**

**Descripción:** el endpoint calcula el campo "estatus" así:

```python
random.seed(r.id_nucleo)
estatus = random.choices(['liberado', 'en_proceso', 'problema'], 
                          weights=[0.6, 0.2, 0.2])[0]
```

Este campo no sale de ningún dato real de la base de datos — es 
aleatorio, aunque estable por id_nucleo gracias al seed. Se implementó 
originalmente como placeholder para mostrar cifras de ejemplo en el 
dashboard, pero nunca se reemplazó por el cálculo real.

**Impacto:** cualquier pantalla que muestre este estatus (dashboard, 
mapa) está presentando información simulada como si fuera real. Puede 
llevar a decisiones basadas en datos falsos.

**Sugerencia:** definir con el equipo la regla de negocio real para 
calcular el estatus (por ejemplo, basada en si el núcleo tiene 
convenios firmados y activos para todas sus afectaciones relacionadas) 
y reemplazar el cálculo aleatorio por una consulta real contra las 
tablas `afectacion` y `convenio`.

---

## Bug: validación de superficie en convenios incompleta en el backend

**Estado: PENDIENTE — módulo probado a fondo, mapeo completo confirmado**

**Descripción:** la validación en Python (regla RN-5, en la función 
`create_convenio`) asume una regla genérica: "colectivo usa 
superficie_real_afectada_ha, individual usa superficie_total_ha". Sin 
embargo, la constraint real en base de datos 
(`chk_superficie_exclusiva_estricta`) exige un mapeo más específico 
según la combinación exacta de `tipo_convenio` + `tipo_afectacion`. 
Esto provoca que combinaciones aparentemente válidas según la regla de 
Python truenen con error 500 (violación de constraint) en vez de un 
error 400 claro y anticipado.

**Tabla de mapeo correcto, confirmada empíricamente probando los 6 
tipos de convenio uno por uno:**

| tipo_convenio | tipo_afectacion | campo de superficie correcto |
|---|---|---|
| cop_original | colectivo | superficie_real_afectada_ha |
| cop_original | individual | superficie_total_ha |
| ampliacion | individual | superficie_ampliacion_ha |
| ampliacion_remanente | individual | superficie_ampliacion_ha |
| superficie_adicional | colectivo | superficie_adicional_ha |
| obras_complementarias | colectivo | superficie_real_afectada_ha |
| modificatorio (individual) | individual | ninguno — solo permite fecha_firma, monto_90, monto_100 |

**Sugerencia:** expandir la validación en Python para cubrir esta 
tabla completa de combinaciones válidas, en vez de la regla genérica 
actual basada solo en tipo_afectacion. Esto evitaría errores 500 y 
daría mensajes de error claros y específicos al usuario.

---

## Módulos probados sin hallazgos (para referencia — evitar retrabajo)

- **Asambleas**: POST (los 5 tipos), GET (listado y por ID), PUT, 
  DELETE (soft delete) — todo correcto, sin bugs encontrados.
- **Núcleos Agrarios**: POST, PUT, DELETE, GET by ID — correctos. 
  Solo el GET de listado tiene los 2 bugs ya documentados arriba.
- **Convenios**: los 6 tipos de convenio (cop_original, ampliacion, 
  modificatorio, obras_complementarias, superficie_adicional, 
  ampliacion_remanente) probados y funcionando, una vez aplicado el 
  mapeo correcto de campos de superficie documentado arriba.