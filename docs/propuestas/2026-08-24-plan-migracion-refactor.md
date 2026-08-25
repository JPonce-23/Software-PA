# Plan de migración — refactor Proyecto–Núcleo / Parcela

> **Fecha:** 2026-08-24  
> **Estrategia:** EXPAND → MIGRATE → SWITCH → CONTRACT.  
> **Regla:** ninguna eliminación antes de validar cobertura de datos y compatibilidad.

## 1. Baseline

Antes de cualquier migración:

- congelar inventario de tablas, FKs, triggers, vistas y endpoints dependientes de `tramo`, `tramo_nucleo` y `afectacion_ciclo`;
- contar filas activas e históricas;
- obtener casos donde un mismo Proyecto+Núcleo tenga múltiples `tramo_nucleo`;
- comparar afectaciones, actividades, asambleas, convenios, FIFONAFE, pagos, documentos y estados;
- generar export de control.

## 2. EXPAND

Crear sin retirar estructuras actuales:

- `proyecto_nucleo`;
- `usuario_proyecto` o equivalente;
- campos de relación nuevos en `actividad_campo`, `afectacion`, `asamblea`, `convenio`, `tramite_fifonafe`, pagos y documentación;
- geometría opcional y procedencia de `parcela` si faltan;
- entidad/trazo de proyecto simplificado si se decide no reutilizar `franja_derecho_via`.

No hacer `NOT NULL` de inmediato en relaciones nuevas.

## 3. MIGRATE — Proyecto–Núcleo

Para cada `tramo_nucleo`:

1. resolver `id_proyecto` desde su tramo;
2. crear/obtener `proyecto_nucleo(id_proyecto,id_nucleo)`;
3. migrar consecutivo/responsable/referencias históricas;
4. registrar mapa `id_tramo_nucleo → id_proyecto_nucleo`.

Si existen varios `tramo_nucleo` para el mismo Proyecto+Núcleo, no fusionar silenciosamente datos conflictivos. Crear reporte de conflicto y reglas de consolidación.

## 4. MIGRATE — Actividades

- actividades iniciales sin ciclo → `id_proyecto_nucleo`;
- actividades asociadas a un ciclo posterior → vincular a la afectación y/o convenio equivalente;
- conservar fechas, resultado, contexto y documentación.

## 5. MIGRATE — Afectaciones

- reemplazar dependencia de `id_tramo_nucleo` por `id_proyecto_nucleo`;
- mantener `id_nucleo` durante compatibilidad si ayuda a validar;
- conservar colectiva/individual;
- conservar parcela sólo para individual;
- conservar superficies capturadas sin recalcular.

## 6. MIGRATE — `afectacion_ciclo`

Construir un reporte por ciclo:

- tipo;
- afectación;
- actividades;
- asambleas;
- convenio base;
- modificatorios;
- FIFONAFE;
- pagos.

Para cada ciclo debe existir un destino claro en el modelo nuevo.

Tipos:

- `cop_original` → convenio COP original;
- `superficie_adicional` → convenio superficie adicional;
- `obras_complementarias` → convenio obras complementarias;
- `ampliacion` → convenio ampliación;
- `ampliacion_remanente` → convenio ampliación remanente.

Si un ciclo existe sin convenio, conservar sus actuaciones mediante afectación/contexto y marcarlo para revisión; no perderlo.

## 7. MIGRATE — Asambleas

- asociar a afectación colectiva;
- asociar al convenio autorizado cuando sea determinable;
- conservar RAN del Acta;
- no mezclarlo con RAN del Convenio.

## 8. MIGRATE — Convenios

- conservar cada fila;
- trasladar tipo;
- crear `id_convenio_padre` para modificatorios cuando pueda demostrarse;
- conservar montos, superficies y RAN;
- retirar `id_ciclo_afectacion` sólo después de validar.

## 9. MIGRATE — FIFONAFE y pagos

- asociar trámite al convenio/afectación correcto;
- conservar cuatro oficios y fechas;
- conservar resultado de no conflictos;
- conservar cada pago y beneficiario;
- validar totales antes/después.

## 10. MIGRATE — Seguridad

- convertir `usuario_tramo` a alcance por Proyecto cuando sea posible;
- si un usuario tenía varios tramos del mismo Proyecto, generar una sola relación;
- no ampliar permisos por accidente entre proyectos.

## 11. SWITCH backend

Cambiar servicios y routers para usar IDs nuevos.

Orden sugerido:

1. consultas lectura;
2. altas de Proyecto–Núcleo;
3. actividades;
4. afectaciones;
5. asambleas;
6. convenios;
7. RAN/FIFONAFE;
8. pagos;
9. documentos;
10. dashboard/reportes;
11. mapa;
12. permisos.

## 12. SWITCH frontend

Nueva navegación:

```text
Proyecto → Entidad → Municipio → Núcleo
```

Dentro de Núcleo:

```text
Resumen | ORV | Padrón | Sensibilización | Caminamiento | Colectivos | Parcelas
```

No mostrar Tramo ni Ciclo como requisito de captura.

## 13. GIS

Desactivar como gates de negocio:

- intersección obligatoria para crear afectación;
- cálculo de superficie oficial por `ST_Area`;
- creación automática de expediente por intersección.

Conservar:

- validación técnica de geometría (SRID/validez);
- mapa de trazo;
- mapa de núcleos;
- mapa de parcelas opcionales.

## 14. Validaciones de paridad

Comparar antes/después:

- número de proyectos;
- núcleos por proyecto;
- parcelas;
- afectaciones colectivas/individuales;
- actividades;
- asambleas;
- convenios por tipo;
- ingresos/inscripciones RAN;
- trámites FIFONAFE;
- pagos y totales;
- superficies capturadas;
- documentos;
- KPI del Excel general.

Toda diferencia debe explicarse.

## 15. CONTRACT

Sólo después de paridad y UAT:

- eliminar FKs nuevas/antiguas de compatibilidad;
- retirar vistas basadas en `tramo_nucleo`;
- retirar `candidato_tramo_nucleo`;
- retirar `seccion_derecho_via` si ya no tiene función cartográfica requerida;
- retirar `afectacion_ciclo`;
- retirar `tramo_nucleo`;
- retirar `usuario_tramo`;
- retirar `tramo` si no queda necesidad histórica/cartográfica;
- actualizar `Arquitectura_Actual.md` y `Diccionario_Datos_SSALFER.md`.

## 16. Gates

No pasar a CONTRACT si:

- existe un ciclo sin destino;
- se pierde un convenio;
- se pierde RAN/FIFONAFE/pago;
- cambia una superficie capturada;
- el dashboard no reproduce los conteos esperados;
- hay permisos sin equivalencia;
- un Proyecto+Núcleo se fusionó con datos conflictivos no resueltos.
