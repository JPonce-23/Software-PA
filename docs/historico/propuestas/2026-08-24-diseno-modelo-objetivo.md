# Diseño modelo objetivo - Propuesta alineada

> Fecha de alineación: 2026-08-25.

## Centro del diseño

El diseño objetivo gira alrededor de Proyecto, ProyectoNucleo, NúcleoAgrario, Parcela, Afectación, Asamblea, Convenio, RAN, FIFONAFE, Indemnización, Pago, Documento y Dashboard.

## Esquema conceptual

```text
Proyecto
├── Trazo ferroviario (representación cartográfica)
└── ProyectoNucleo
    └── Núcleo Agrario
        ├── Datos generales
        ├── ORV
        ├── Padrón
        ├── Sensibilización
        ├── Caminamiento
        ├── Derechos colectivos
        │   └── Afectación colectiva
        │       ├── Avalúo simple, cuando exista
        │       ├── Asamblea -> RAN del Acta
        │       └── Convenio(s) -> RAN del Convenio -> FIFONAFE -> Indemnización -> Pago
        └── Derechos individuales
            └── Parcela
                └── Afectación individual
                    └── Convenio(s) -> RAN -> FIFONAFE -> Indemnización -> Pago
```

## Relaciones clave

- Proyecto 1-N ProyectoNucleo.
- NúcleoAgrario 1-N ProyectoNucleo.
- NúcleoAgrario 1-N Parcela.
- ProyectoNucleo 1-N Afectacion.
- Parcela 0/1-N Afectacion individual.
- Afectacion 1-N Convenio.
- Convenio N-M Afectacion sólo por excepción documentada.
- Afectacion colectiva 0-N Asamblea.
- Asamblea 0-1 RAN del acta.
- Convenio 0-1 RAN del convenio.
- Convenio/Afectacion 0-N FIFONAFE, Indemnizacion y Pago según corresponda.

## Geoespacial

PostGIS se conserva para trazo, núcleo y parcela opcional. La geometría no es gate administrativo y no genera superficies oficiales. Los cálculos espaciales pueden apoyar validación visual o diagnóstico, no reemplazar datos capturados.

## UI objetivo

La captura ordinaria entra por Núcleo. Derechos colectivos y Parcelas/Derechos individuales son pestañas hermanas. La UI normal no obliga al usuario a pensar en ciclos; las variantes se eligen como tipo de convenio.

## Compatibilidad

TramoNucleo, AfectacionCiclo y usuario_tramo pueden requerir adaptación técnica durante migración, pero no son piezas objetivo. Cualquier vista de compatibilidad deberá estar documentada como transitoria.
