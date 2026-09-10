# Alcance funcional Excel - SOFTWARE-PA

> Autoridad: contrato canónico de alcance funcional.
> Función: define qué fuentes tienen autoridad y cómo deben interpretarse.
> Este documento no es fuente de datos; los Excel operativos siguen siendo la fuente funcional primaria del contenido operativo.

## Regla invariable

SOFTWARE-PA debe demostrar correspondencia con el modelo operativo Excel, no correspondencia exhaustiva con el Derecho Agrario mexicano.

El objetivo del sistema es sustituir los archivos Excel de seguimiento por una aplicación estructurada, práctica, trazable y capaz de generar sus reportes.

## Fuente funcional primaria

Los Excel operativos determinan principalmente:

1. qué datos deben capturarse;
2. qué relaciones necesitan conservarse;
3. qué eventos o cambios deben historizarse;
4. qué excepciones operativas deben representarse;
5. qué indicadores deben calcularse;
6. qué reportes debe poder generar el sistema.

Toda ampliación funcional debe tener evidencia Excel o decisión funcional aprobada. La evidencia puede ser archivo, hoja, columna, registro, fórmula o comportamiento observado que demuestre una necesidad de captura, relación, historial, excepción, indicador o reporting.

## Fuentes interpretativas

La legislación, reglamentos, lineamientos, flujogramas, presentaciones y demás documentos institucionales sirven para interpretar correctamente los conceptos presentes en las fuentes operativas, pero no amplían por sí solos el alcance funcional.

No debe crearse un módulo, tabla, pantalla, estado, etapa, proceso o requisito sólo porque jurídicamente exista.

## Precedencia documental

1. `docs/ALCANCE_FUNCIONAL_EXCEL.md`: autoridad canónica sobre el alcance y las reglas para interpretar fuentes.
2. Archivos Excel operativos: fuente funcional primaria para determinar datos, relaciones, comportamientos, excepciones e indicadores.
3. `docs/Descripción proceso.md`, `docs/requirements.md`, `docs/Description.md` y `docs/contexto/contexto_funcional_liberacion_propiedad_social_v2.md`: modelo funcional documentado, siempre subordinado a este contrato.
4. `docs/Arquitectura_Actual.md`, `docs/Diccionario_Datos_SSALFER.md`, diseño técnico, migraciones y código: implementación técnica vigente.
5. Flujogramas, documentos PA, legislación, reglamentos, RAN, FIFONAFE, INDAABIN, INPI y demás fuentes institucionales: fuentes de interpretación y contexto; no generadores automáticos de alcance.
6. `docs/historico/*`: antecedentes y trazabilidad; no fuente normativa de implementación.

## Criterio de correspondencia

La correspondencia con el modelo operativo Excel se evalúa por:

1. captura sin pérdida;
2. conservación de relaciones;
3. historial necesario;
4. excepciones reales;
5. indicadores;
6. reporting;
7. trazabilidad.

Una tabla más normalizada o jurídicamente exhaustiva no es automáticamente mejor. La estructura objetivo debe ser la mínima necesaria para capturar sin pérdida, conservar relaciones, preservar historia relevante, manejar excepciones observadas y generar correctamente los reportes.

## Reglas negativas

Datos como X, trimestre, mes, año, vigencia calculable, conversiones de unidad y otros derivados no deben convertirse automáticamente en campos persistidos.

NULL, desconocido o error de fuente no equivalen a cero.

Los procesos observados pueden ser no lineales.

Expropiación directa, comunidad indígena, no afectación, suspensión, reapertura, cancelación, reprogramación o cambio de alcance no deben recibir consecuencias jurídicas automáticas salvo que la información registrada lo demuestre.

No debe crearse un módulo jurídico completo de expropiación, consulta indígena, negociación, avalúo u otro procedimiento únicamente porque exista jurídicamente.

Reporting forma parte central del criterio de correspondencia.
