# Plan de migración refactor - Documento objetivo

> Fecha de alineación: 2026-08-25.  
> Este documento no crea migraciones; define el orden recomendado para una fase posterior.

## Fase 1. Inventario

Congelar dependencias actuales de Tramo, TramoNucleo, AfectacionCiclo, usuario_tramo, validaciones espaciales, vistas de dashboard y endpoints. Comparar contra la matriz Excel-modelo.

## Fase 2. Modelo expansivo

Agregar estructuras objetivo sin borrar datos: ProyectoNucleo simple, Parcela reforzada, afectación colectiva/individual simplificada, convenio repetible, RAN separado, FIFONAFE sin ciclo, indemnización, pago, documentos y relación excepcional convenio_afectacion.

## Fase 3. Migración de datos

Migrar referencias de tramo como campos históricos. Convertir ciclos y columnas paralelas en convenios. Separar superficies preliminar, real afectada y superficie propia del convenio. Llevar solicitudes RAN a los campos correctos.

## Fase 4. Conciliación

Reconstruir KPI del Excel general desde los hechos migrados. Validar Mexico-Queretaro con los Excel detallados y documentar proyectos del Excel general sin fuente detallada local equivalente.

## Fase 5. UI y API

Cambiar navegación a Proyecto -> Entidad -> Municipio -> Núcleo. Exponer pestañas de núcleo, colectivos y parcelas. Ocultar ciclo técnico y quitar intersección espacial como gate.

## Fase 6. Contract

Sólo después de conciliación completa, retirar dependencias objetivo de TramoNucleo, AfectacionCiclo y usuario_tramo. Mantener vistas de compatibilidad únicamente si un consumidor externo lo requiere.

## Reglas de no regresión

No perder soporte ni observaciones. No colapsar superficies. No confundir indemnización con pago. No convertir excepciones en catálogo ordinario sin evidencia documental.
