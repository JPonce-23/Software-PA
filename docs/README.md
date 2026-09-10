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

- `docs/ALCANCE_FUNCIONAL_EXCEL.md`
- `docs/Description.md`
- `docs/Descripción proceso.md`
- `docs/requirements.md`
- `docs/contexto/contexto_funcional_liberacion_propiedad_social_v2.md`

`docs/ALCANCE_FUNCIONAL_EXCEL.md` es la **autoridad canónica del alcance funcional**: define qué fuentes tienen autoridad y cómo deben interpretarse. No sustituye a los Excel como fuente de datos.

Los Excel operativos locales son la **fuente funcional primaria del contenido operativo**: determinan qué datos se capturan, qué relaciones se conservan, qué eventos o cambios se historizan, qué excepciones se representan, qué indicadores se calculan y qué reportes debe generar el sistema.

`docs/Descripción proceso.md` sigue siendo el **documento canónico del proceso/modelo funcional**, siempre subordinado al contrato de alcance definido en `docs/ALCANCE_FUNCIONAL_EXCEL.md`. `docs/Description.md`, `docs/requirements.md` y `docs/contexto/contexto_funcional_liberacion_propiedad_social_v2.md` documentan el modelo funcional vigente bajo esa misma subordinación.

Regla invariable: **SOFTWARE-PA debe demostrar correspondencia con el modelo operativo Excel, no correspondencia exhaustiva con el Derecho Agrario mexicano.**

El flujograma y las fuentes institucionales son fuentes interpretativas. La legislación, reglamentos, lineamientos, presentaciones, RAN, FIFONAFE, INDAABIN, INPI y demás documentos institucionales pueden explicar conceptos, pero no generan automáticamente módulos, tablas, pantallas, estados, etapas, procesos ni requisitos.

La implementación técnica vigente describe lo construido, pero no puede ampliar el dominio por sí sola. `docs/historico/*` sirve como antecedente y trazabilidad; no tiene autoridad funcional vigente.

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
