# Documentación SOFTWARE-PA

> Fecha de actualización: 2026-08-25.

## Fuentes locales no versionadas

`fuentes_locales/excel/*.xlsx`

Estos archivos son fuentes operativas de consulta y conciliación. No forman parte del producto, no deben subirse a GitHub y están excluidos por `.gitignore` mediante `fuentes_locales/`.

Ver `docs/fuentes_locales.md`.

## Fuentes literales versionadas

- `docs/contexto/estructura_datos_propiedad_social_fuente.md`
- `docs/contexto/flujo_liberacion_propiedad_social_fuente.md`

Son transcripciones/fuentes literales. No se reescriben para coincidir con la arquitectura técnica.

## Modelo funcional objetivo

- `docs/Description.md`
- `docs/Descripción proceso.md`
- `docs/requirements.md`
- `docs/contexto/contexto_funcional_liberacion_propiedad_social_v2.md`

`docs/Descripción proceso.md` es el documento canónico del proceso objetivo.

## Diseño objetivo

- `docs/design.md`
- `docs/propuestas/2026-08-24-refactor-modelo-seguimiento-excel.md`
- `docs/propuestas/2026-08-24-matriz-trazabilidad-excel-modelo.md`
- `docs/propuestas/2026-08-24-requisitos-modelo-objetivo.md`
- `docs/propuestas/2026-08-24-diseno-modelo-objetivo.md`
- `docs/propuestas/2026-08-24-plan-migracion-refactor.md`

Una propuesta histórica no prevalece sobre el modelo objetivo vigente.

## Implementación real actual

- `docs/Arquitectura_Actual.md`
- `docs/Diccionario_Datos_SSALFER.md`
- código en `backend/` y `frontend/`
- migraciones en `backend/db/migrations/`

Estos documentos y artefactos describen la implementación vigente hasta que exista una migración aprobada.

## Históricos

`docs/historico/*`

Sirven como memoria de decisiones y trabajos previos. No son fuente normativa si contradicen el modelo objetivo actual.
