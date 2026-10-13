# Revisión final: benchmark sintético GIS 029

Se compara la Entrega 1 implementada, antes de estas correcciones, con el
parche final. No se compara con la versión anterior a la incorporación de
diagnósticos. Snapshot previo: `/tmp/software-pa-gis029-revision-before`.

## Metodología ejecutada

Script: `backend/scripts/benchmark_gis_diagnostics_029.py`. Python 3.11.17 en
contenedor temporal. Datos íntegramente sintéticos en memoria; tres muestras
por medición, mediana, carga previa de módulos y ejecución previa de ambas
versiones. Los mismos datos se reutilizan en ambos lados.

Se miden por separado:

1. `matching_diagnostic()` completo, incluida validación/serialización Pydantic.
2. `build_candidates()` y diagnóstico, con construcción real de modelos y
   estado, sustituyendo sólo la sesión de persistencia y el lookup geométrico
   por objetos en memoria. No se modifican predicados ni clasificaciones.

Los escenarios oficiales evalúan una clave en el universo. Los textuales usan
núcleos homónimos con municipio, entidad y tipo coincidentes, para ejercitar
los descartes/variantes cuando muchas parcelas siguen siendo elegibles.
Las tres columnas fuente contienen `00016`, `000016` y `0000016`; los destinos
contienen segmentos numéricos sin ese relleno. Se provoca un residual válido y
observaciones de formato, nunca una equivalencia automática.

El script exige configuración explícita de test y tiene una guarda que falla
ante cualquier ejecución SQL. Verifica igualdad exacta de estados, candidatos
y diagnósticos antes/después en estos escenarios. No incluye lectura GDAL,
subida de archivos, latencia de PostgreSQL, inserción JSONB, locks ni commits.

## Resultados

Tiempos en segundos, medianas de tres muestras:

| Features | Destinos | Núcleos | Identidad | Diagnóstico antes | Diagnóstico después | Procesamiento antes | Procesamiento después |
|---:|---:|---:|---|---:|---:|---:|---:|
| 200 | 1.000 | 40 | Oficial | 0,0617 | 0,0391 | 0,2154 | 0,1964 |
| 200 | 1.000 | 40 | Textual, homónimos | 1,2769 | 0,5073 | 4,1847 | 3,3345 |
| 500 | 2.000 | 80 | Textual, homónimos | 6,4769 | 3,2209 | 20,0657 | 17,1995 |

Reducción observada del tiempo diagnóstico: 36,6%, 60,3% y 50,3%.
Reducción observada del procesamiento en memoria: 8,8%, 20,3% y 14,3%.
Son mediciones orientativas: el host comparte carga con servicios de desarrollo
y parte de las pruebas pytest; no hay afinidad CPU ni aislamiento estadístico.
No son una garantía de throughput de staging en producción.

Todas las comparaciones de contenido fueron iguales y el benchmark ejecutó
cero consultas SQL. [Muestras completas](benchmarks/gis_diagnostics_029_final_review.json).

## Cambios puntuales evaluados

- El lookup de columnas se construye una vez por diagnóstico, conservando
  precedencia de aliases, caja y tratamiento de valores vacíos.
- Las parcelas elegibles se normalizan una vez para la observación de variantes,
  compartiendo ese resultado entre las tres columnas. No se persiste ningún
  identificador canónico nuevo ni se cambia el matching.
- El universo y sus objetos ORM se siguen cargando/reutilizando por intento.
  La complejidad de recorrido de destinos de `build_candidates()` no cambia.

La prueba `test_diagnostic_generation_reuses_universe_without_feature_queries`
usa 20 features y 6 destinos reales sintéticos en `software_pa_test`. Comprueba
que cada invocación diagnóstica hace cero SQL y recibe las mismas listas de
universo/contexto. La reutilización parcelaria hace tres consultas de carga en
bloque: vista de vínculos, parcelas y relación `selectin` existente; no repite
la carga nuclear. Preview mantiene el mismo número de consultas para páginas
de 1 y 20 filas, con una única consulta de resultados diagnósticos por página.

## Reproducción

Desde el checkout original con Compose configurado:

```bash
docker compose run --rm --no-deps \
  -v /tmp/software-pa-gis-diagnosticos-20261013/backend:/app:ro \
  -v /tmp/software-pa-gis029-revision-before:/benchmark-baseline:ro \
  -e APP_ENV=test -e DB_NAME=software_pa_test \
  -e TEST_ALLOW_DATABASE=software_pa_test -e PYTHONDONTWRITEBYTECODE=1 \
  backend python scripts/benchmark_gis_diagnostics_029.py \
  --baseline-dir /benchmark-baseline --repetitions 3
```

El snapshot previo es necesario para comparar exactamente contra Entrega 1;
no utilizar el commit auditado sin diagnósticos como sustituto. Una futura
medición de capacidad completa deberá incluir GDAL y la persistencia en una
base de pruebas con tamaño representativo, sin ampliar esta corrección.
