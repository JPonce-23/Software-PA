# Diseño técnico propuesto — modelo objetivo simplificado

> **Estado:** diseño propuesto; NO implementado.  
> **Fecha:** 2026-08-24.  
> **Arquitectura vigente:** ver `docs/Arquitectura_Actual.md`.

## 1. Principios

- Modelo mínimo necesario para representar Excel + flujo.
- Integridad relacional sin máquinas de estados innecesarias.
- Geoespacial desacoplado de la fuente de verdad administrativa.
- Navegación orientada a Proyecto → Núcleo.
- Parcela central en individuales.
- Afectación colectiva sin parcela.
- Convenio como registro repetible/normalizado.
- Migración reversible hasta CONTRACT.

## 2. Modelo lógico objetivo

```text
Proyecto
  1 ── N ProyectoNucleo
ProyectoNucleo
  N ── 1 NucleoAgrario
  1 ── N ActividadCampo
  1 ── N Afectacion

NucleoAgrario
  1 ── N ORV
  1 ── N PadronHistorial
  1 ── N Parcela

Parcela
  1 ── N ParcelaTitular
  1 ── N Afectacion individual

Afectacion
  1 ── N Asamblea
  1 ── N Convenio

Convenio
  1 ── N TramiteFifonafe
  1 ── N PagoIndemnizacion
```

## 3. `proyecto_nucleo`

Propuesta:

```text
id_proyecto_nucleo PK
id_proyecto FK NOT NULL
id_nucleo FK NOT NULL
consecutivo
residencia
responsable_nombre
responsable_telefono
clave_tramo_referencia NULL
numero_tramo_referencia NULL
observaciones
activo
auditoría
UNIQUE(id_proyecto, id_nucleo)
```

No contiene geometría.

## 4. `trazo_proyecto`

El trazo puede separarse de `franja_derecho_via` para evitar semántica de ancho/superficie que ya no se necesita.

```text
id_trazo
id_proyecto
version
geometria_linea MULTILINESTRING 4326
fuente
fecha_vigencia
activo
```

Una alternativa válida es simplificar/reutilizar `franja_derecho_via` conservando únicamente su geometría lineal de proyecto. La decisión se toma en implementación según costo de migración.

## 5. `actividad_campo`

Objetivo:

```text
id_actividad
id_proyecto_nucleo
id_afectacion NULL
id_convenio NULL
tipo_actividad
contexto
fecha_programada
fecha_realizada
resultado
observaciones
soporte
```

`contexto` describe el hecho (`inicial`, `superficie_adicional`, `obras_complementarias`, `ampliacion`, etc.); no crea una máquina de estados.

## 6. `parcela`

Conservar campos actuales y añadir, si falta:

```text
no_parcela
geometria_poligono MULTIPOLYGON 4326 NULL
fuente_geometria NULL
fecha_fuente_geometria NULL
```

No calcular `superficie_afectada` a partir de esa geometría.

## 7. `afectacion`

Objetivo:

```text
id_afectacion
id_proyecto_nucleo
tipo_afectacion colectivo|individual
id_parcela NULL
destino_superficie
no_parcela_solar
superficie_preliminar_ha NULL
superficie_afectada_ha NULL
situacion_juridica NULL
condicion_especial NULL
observaciones
activo
```

Regla:

- individual → `id_parcela` requerido;
- colectivo → `id_parcela` no requerido.

No requiere `id_tramo_nucleo`.

## 8. `asamblea`

Debe depender de `id_afectacion` y, si se requiere, referenciar directamente el convenio que autoriza.

Se conservan los campos actuales de convocatorias y RAN.

No requiere `id_ciclo_afectacion`.

## 9. `convenio`

Se conserva como entidad central.

Campos principales:

```text
id_convenio
id_afectacion
id_asamblea_autorizacion NULL
tipo_convenio
consecutivo/version
id_convenio_padre NULL
fecha_firma
monto_90
monto_100
monto_bdt
superficie_ha
ingreso_ran_fecha
numero_solicitud_ingreso
calificacion_registral
convenio_inscrito_fecha_ran
documentación
observaciones
```

`id_convenio_padre` permite linaje de modificatorios cuando corresponda y sustituye parte del propósito técnico de `afectacion_ciclo`.

## 10. FIFONAFE

`tramite_fifonafe` se relaciona directamente con `convenio` y/o `afectacion`, evitando `id_ciclo_afectacion`.

Debe conservar:

- tipo de trámite;
- estatus;
- resultado/no conflictos;
- cuatro números de oficio;
- cuatro fechas;
- observaciones;
- evidencia.

## 11. Pago

El pago debe relacionarse con el convenio/trámite de indemnización correspondiente.

Las reglas financieras pueden mantener validaciones básicas de no negatividad e integridad, pero no deben depender de superficie GIS.

## 12. Eliminación de `afectacion_ciclo`

Se retira sólo cuando:

- convenio tiene tipo/linaje suficiente;
- actividad puede asociarse al proyecto-núcleo, afectación o convenio;
- asamblea puede asociarse a afectación/convenio;
- FIFONAFE y pagos pueden relacionarse directamente;
- vistas/dashboard ya no lo consultan;
- migración histórica queda validada.

## 13. Eliminación de `tramo_nucleo`

Sus responsabilidades se distribuyen:

| Responsabilidad actual | Destino objetivo |
|---|---|
| proyecto/tramo/núcleo | `proyecto_nucleo` |
| consecutivo | `proyecto_nucleo` |
| clave/número tramo | referencia opcional |
| geometría segmento | se elimina como requisito |
| expropiación/no uso común | `afectacion` o `proyecto_nucleo` según alcance real |
| actividades | `proyecto_nucleo` / afectación / convenio |
| expediente | navegación Proyecto–Núcleo |

## 14. Seguridad

Propuesta mínima:

```text
usuario_proyecto
- id_usuario
- id_proyecto
- permisos/rol si aplica
```

El rol global continúa existiendo. `usuario_tramo` se mantiene sólo durante compatibilidad.

## 15. API objetivo

Ejemplos:

```text
GET  /proyectos/{id}/nucleos
POST /proyectos/{id}/nucleos/{id_nucleo}/seguimiento

GET  /proyectos/{id}/nucleos/{id_nucleo}
GET  /proyectos/{id}/nucleos/{id_nucleo}/actividades

GET  /nucleos/{id}/orvs
GET  /nucleos/{id}/padrones
GET  /nucleos/{id}/parcelas

POST /proyectos-nucleos/{id}/afectaciones
POST /afectaciones/{id}/asambleas
POST /afectaciones/{id}/convenios

GET/POST /convenios/{id}/fifonafe
GET/POST /convenios/{id}/pagos
```

## 16. Frontend objetivo

```text
Dashboard
Mapa
Proyectos
  → Proyecto
     → Entidades
        → Municipios
           → Núcleos
              → Resumen
              → ORV
              → Padrón
              → Sensibilización
              → Caminamiento
              → Colectivos
              → Parcelas
```

No exponer `AfectacionCiclo`.

## 17. Mapa

Capas:

1. trazo del proyecto;
2. núcleos agrarios;
3. parcelas con geometría.

La selección cartográfica abre la entidad administrativa correspondiente.

## 18. Consultas del Dashboard

Los KPI deben salir de hechos:

- `COUNT(DISTINCT proyecto_nucleo.id_nucleo)`;
- actividades por tipo y fechas;
- asambleas por fechas/RAN;
- convenios por `tipo_convenio`;
- parcelas afectadas distintas;
- RAN por fechas de ingreso/inscripción;
- FIFONAFE por oficios/estatus;
- superficies por SUM de campos capturados.

No usar `ST_Area` para KPI oficiales.

## 19. Compatibilidad

Durante SWITCH, endpoints antiguos pueden traducir temporalmente IDs de `tramo_nucleo` a `proyecto_nucleo`.

No crear nuevas dependencias en `tramo_nucleo` o `afectacion_ciclo`.

## 20. Fuera de alcance inicial

- cálculo automático de superficie por GIS;
- inferencia automática de afectaciones;
- creación automática de expediente por intersección;
- segmentación de trazo por tramo;
- reconstrucción de parcelas individuales desde capas de zona parcelada.
