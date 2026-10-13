# Diagnósticos GIS — contrato para SSALFER, entrega 1

Requiere esquema 029 y backend con esta entrega. No incorpora cambios de
frontend, baja de importaciones, nuevos endpoints ni nuevas reglas de matching.

## Consumo

1. Consultar `GET /api/importaciones/{id}/features` con los filtros y paginación
   actuales. Cada fila añade `id_ciclo_conciliacion` y `diagnostico` opcionales.
2. Si `diagnostico=null`, no hay una proyección diagnóstica en esa respuesta.
   Si `origen=no_disponible`, existe resultado histórico sin diagnóstico registrado.
3. Si `origen=registrado`, utilizar `codigos` para presentación estable y
   `mensaje` como explicación disponible. Una feature admite varios códigos.
4. Para historia, consultar `/conciliaciones/{id_ciclo}`: cada item de `features`
   lleva el diagnóstico de ese ciclo, sin recurrir al catálogo actual.
5. Mantener `estado_conciliacion` como estado actual. `estado_matching` histórico
   es el resultado inicial del algoritmo; `estado_resultado` incluye decisiones.
   El diagnóstico permanece asociado al matching original, incluso tras confirmar.

Un diagnóstico registrado con `codigos=[]` significa que no se observó una
causa de fallo ni ambigüedad: hubo un candidato compatible. No es confirmación
automática. Los candidatos pueden seguir requiriendo selección, revisión y
confirmación explícita. No asociar todas las filas al último ciclo global:
una reconciliación puede reevaluar sólo algunas features.

Las nuevas propiedades son opcionales; las anteriores, paginación,
`X-Total-Count`, permisos y endpoints se conservan. Las respuestas POST de
decisiones pueden mantener las nuevas propiedades en null; refrescar el GET.

## Catálogo V1

| Código | Interpretación verificable |
|---|---|
| `UNIVERSO_DESTINOS_VACIO` | No hay destinos administrativos elegibles del tipo de importación. |
| `IDENTIDAD_NUCLEO_INSUFICIENTE` | Falta clave oficial y nombre utilizable; no se inventa identidad. |
| `CLAVE_SIN_COINCIDENCIA_EN_UNIVERSO` | Con núcleos vinculados disponibles, ninguna clave coincide bajo la fuente oficial admitida. No afirma inexistencia global. |
| `NOMBRE_SIN_COINCIDENCIA_EN_UNIVERSO` | Con contexto nuclear disponible y sin clave oficial, ningún nombre coincide según la normalización vigente. |
| `MUNICIPIO_INCOMPATIBLE` | Un nombre coincidente fue descartado al comprobar municipio. |
| `ENTIDAD_INCOMPATIBLE` | Un nombre coincidente fue descartado al comprobar entidad, después de superar municipio cuando se aportó. |
| `TIPO_NUCLEO_INCOMPATIBLE` | Un nombre coincidente fue descartado al comprobar tipo, después de superar los criterios anteriores aportados. |
| `NUMERO_PARCELA_AUSENTE` | Ninguna de PARCELA, Num_parcela o no_parcela aporta un valor utilizable. |
| `PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO` | Hay núcleo compatible en el contexto vinculado, pero ningún destino parcelario generado. No afirma que la parcela no exista en el catálogo. |
| `VARIANTE_FORMATO_PENDIENTE_REVISION` | Sin candidatos, se observó un número distinto únicamente por ceros iniciales respecto a una parcela elegible del núcleo compatible. No declara equivalencia. |
| `MULTIPLES_DESTINOS_COMPATIBLES` | El matching generó más de un candidato. No se selecciona ninguno. |
| `ID_ADMINISTRATIVO_SIN_COINCIDENCIA_EN_UNIVERSO` | El mapeo técnico legado no encontró destino elegible; no utiliza identidad textual. |
| `DIAGNOSTICO_HISTORICO_NO_DISPONIBLE` | Exclusivo de origen no_disponible; el resultado no conservó diagnóstico. |

Si no existen núcleos vinculados, no se añade una causa de clave o nombre
incompatible: el universo está vacío y no hay comparaciones que la sustenten.
La presencia de clave oficial impide atribuir errores de nombre o territorio.
Con varios núcleos homónimos pueden coexistir distintos descartes probados.
Los descartes territoriales sólo son causas de fallo cuando no queda núcleo
compatible; la evidencia puede contener contadores de otros descartes.

## Estructura

`diagnostico` es un objeto tipado con `version="1"`, `origen`, `codigos`,
`mensaje`, `campos_evaluados` y `evidencia`. Ejemplo completo registrado:
[API §12](API.md#12-diagnósticos-de-conciliación-gis-entrega-1-esquema-029).

`campos_evaluados` conserva los nombres de las columnas reconocidas utilizadas
en las comprobaciones (incluida presencia de número). En mapeo técnico conserva
la columna configurada en `mapeo.id_destino`: `record_id`, `id_destino`,
`id_parcela` o `id_nucleo`, con la caja configurada. No sustituye esos nombres
por la clave interna normalizada `id_destino`. Esto se aplica también a los
nuevos ciclos de reconciliación. Los diagnósticos históricos anteriores a la
corrección conservan el texto registrado; no se modifican retroactivamente.
Si un llamador interno no aporta el nombre del campo, no se inventa uno.
La evidencia incluye:

- `destinos_evaluados`: destinos distintos del universo aplicable al ciclo.
- `nucleos_evaluados`: contexto nuclear autorizado comprobado; cero cuando el
  mapeo técnico sustituye esa comprobación.
- `nucleos_compatibles`: vínculos de núcleos compatibles con la identidad.
- `parcelas_evaluadas`: parcelas elegibles de núcleos compatibles; con mapeo
  técnico, los destinos parcelarios del universo.
- `candidatos`: cantidad generada realmente por el algoritmo.
- `descartes_territoriales`: contadores municipio/entidad/tipo_nucleo del primer
  criterio fallido por núcleo; nunca se atribuyen criterios posteriores.
- `variantes_formato`: columna, regla y cantidad de destinos observados.

La regla de observación es
`DIFERENCIA_CEROS_INICIALES_SEGMENTO_NUMERICO`: sólo números ASCII o
`P-<dígitos>` con el mismo prefijo. `016`/`16` y `P-016`/`P-16` son diferencias
observables, pero siguen sin coincidir. La excepción vigente
`P.-<dígitos>`/`P-<dígitos>` permanece. No se equiparan sufijos, `P/16`/`P-16`,
prefijos distintos o identificadores que contienen zonas y polígonos.
No se consultan parcelas de otros proyectos ni el catálogo global.

Histórico sin registro:

```json
{
  "version": "1",
  "origen": "no_disponible",
  "codigos": ["DIAGNOSTICO_HISTORICO_NO_DISPONIBLE"],
  "mensaje": "No se registró un diagnóstico para este resultado histórico.",
  "campos_evaluados": [],
  "evidencia": {
    "destinos_evaluados": null,
    "nucleos_evaluados": null,
    "nucleos_compatibles": null,
    "parcelas_evaluadas": null,
    "candidatos": null,
    "descartes_territoriales": null,
    "variantes_formato": []
  }
}
```

Los contadores desconocidos son null, no cero. El objeto se proyecta en lectura;
el histórico sigue almacenado como SQL NULL. No hay backfill ni reconstrucción.

## Advertencia administrativa existente

En staging, `reporte.registros_administrativos == 0` permite mostrar:
“No hay destinos administrativos elegibles para esta importación”. En parcelas
conviene explicar que tener núcleos o parcelas de catálogo no demuestra vínculos
activos de afectación con el proyecto. No llamar “proyecto vacío” a ese caso.

El GET `/resumen` calcula el universo actual; `reporte` conserva el último
resumen persistido y puede cambiar después de decisiones/reconciliaciones.
Para evidencia histórica usar ciclo y diagnóstico guardados. No declarar
universo incompleto ni porcentaje de carga sin una regla funcional aprobada.
