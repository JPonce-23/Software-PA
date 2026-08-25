# Fuentes locales no versionadas

> Fecha de actualización: 2026-08-25.

## Ubicación esperada

`fuentes_locales/excel/`

Archivos esperados:

- `PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx`
- `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx`
- `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx`

## Naturaleza

Estos Excel son fuentes operativas de consulta, auditoría y conciliación. No forman parte del producto SOFTWARE-PA, no se versionan y no deben subirse automáticamente a GitHub.

`fuentes_locales/` debe permanecer en `.gitignore`.

## Uso documental

Los Excel sirven para validar campos reales, columnas, cardinalidades, KPI de dashboard, excepciones y diferencias entre seguimiento colectivo e individual.

Documentos derivados versionados:

- `docs/propuestas/2026-08-24-matriz-trazabilidad-excel-modelo.md`
- `docs/propuestas/2026-08-25-diseno-reestructuracion-bd.md`
- `docs/requirements.md`
- `docs/design.md`

No se deben generar copias de estos Excel dentro de directorios versionados.
