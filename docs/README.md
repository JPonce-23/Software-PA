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

## Modelo funcional objetivo canónico

- `docs/Description.md`
- `docs/Descripción proceso.md`
- `docs/requirements.md`
- `docs/contexto/contexto_funcional_liberacion_propiedad_social_v2.md`

`docs/Descripción proceso.md` es el **documento funcional canónico**. Sus definiciones prevalecen sobre descripciones funcionales anteriores.

## Diseño técnico objetivo canónico

- `docs/design.md`
- `docs/propuestas/2026-08-25-diseno-reestructuracion-bd.md`
- `docs/propuestas/2026-08-24-matriz-trazabilidad-excel-modelo.md`

`docs/propuestas/2026-08-25-diseno-reestructuracion-bd.md` es el **DISEÑO TÉCNICO CANÓNICO** implementado por las migraciones 031-033; la migración 034 separa owner y runtime sin cambiar ese dominio. Si existe una contradicción con una propuesta anterior, prevalece el diseño del 25 de agosto. Cualquier propuesta no incluida en esta sección sirve sólo como antecedente y no es normativa para la implementación.

## Implementación real actual

- `docs/Arquitectura_Actual.md`
- `docs/Diccionario_Datos_SSALFER.md`
- `backend/`
- `frontend/`
- `backend/db/migrations/`

Estos documentos y artefactos describen la implementación vigente del esquema 035 y se validan conjuntamente. La operación owner/runtime se documenta en `docs/migraciones.md`.

## Históricos

- `docs/historico/*`

Sirven como memoria de decisiones y trabajos previos. Los documentos históricos **NO son fuente normativa para implementar**.
