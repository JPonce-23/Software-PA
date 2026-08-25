# Refactor modelo seguimiento Excel - Propuesta alineada

> Fecha de alineación: 2026-08-25.  
> Estado: propuesta documental aprobada para diseño de migración; no implementa código.

## Conclusión de auditoría

Los Excel locales muestran que el seguimiento real se organiza por proyecto, núcleo agrario, actividades, derechos colectivos, parcelas, convenios, RAN, FIFONAFE, indemnización, pago y soporte documental. No muestran necesidad funcional de convertir Tramo en expediente, ni de exigir `afectacion_ciclo` al usuario.

## Modelo objetivo

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

## Decisiones aprobadas

- Tramo se conserva sólo como referencia histórica/opcional cuando venga en Excel.
- ProyectoNucleo es contexto mínimo, no expediente geoespacial complejo.
- Parcela es entidad central de individuales.
- Derechos colectivos no requieren parcela.
- Convenio es entidad central y repetible.
- Permuta se maneja como modalidad/excepción, no como tipo ordinario de COP.
- Un convenio puede asociarse excepcionalmente con varias afectaciones.
- Avalúo se modela como campos simples en afectación.
- RAN del acta y RAN del convenio se separan.
- Superficies oficiales son capturas administrativas, no cálculos `ST_Area`.
- FIFONAFE conserva los cuatro oficios sin depender de `afectacion_ciclo`.

## Normalización propuesta

Los bloques horizontales del Excel se convierten en filas de convenio por tipo. Las columnas derivables (`TRIMESTRE`, `POR NA`, totales de reporte) se calculan en dashboard. Las observaciones y soportes se preservan como documentación, no como módulos nuevos salvo que tengan cardinalidad y ciclo de vida propios.

## Casos excepcionales observados

- `1 COP FIRMADO (PERMUTA)`: COP original con `modalidad_especial = permuta` y observación literal.
- `1 COP PARA DOS SOLARES, DUDA`: convenio asociado excepcionalmente a más de una afectación/superficie mediante `convenio_afectacion` y observación.
- Expropiación directa, comunidad indígena y no afectación de uso común: condiciones registrables sin terminalidad global automática.

## Criterio de aceptación

La refactorización posterior será correcta si reconstruye los indicadores del Excel general desde datos capturados, sin exigir TramoNucleo, sin exponer AfectacionCiclo, sin geometría como gate y sin superficies oficiales derivadas por `ST_Area`.
