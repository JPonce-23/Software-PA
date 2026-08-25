# Propuesta de refactorización — modelo de seguimiento basado en Excel y proceso agrario

> **Fecha:** 2026-08-24  
> **Estado:** propuesta aprobada conceptualmente; pendiente de implementación técnica.  
> **Objetivo:** simplificar SOFTWARE-PA manteniendo el 100 % de la información útil de los Excel y del flujo institucional.

## 1. Motivo

La arquitectura implementada actualmente utiliza `Tramo`, `SeccionDerechoVia`, `TramoNucleo` y `AfectacionCiclo` como piezas estructurales del proceso. La auditoría de los Excel muestra que el seguimiento real se organiza principalmente por Proyecto, Núcleo Agrario, derechos colectivos, parcelas, convenios, RAN y FIFONAFE.

El modelo actual contiene reglas geoespaciales y de secuencia que superan lo que requiere el producto descrito en `docs/Description.md`.

## 2. Evidencia de los Excel auditados

### Seguimiento individual México–Querétaro

Archivo auditado: `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` (versión sanitizada para análisis).

Hoja principal `PROPUESTA`:

- 683 filas de seguimiento individual;
- 71 núcleos agrarios distintos;
- 657 filas con número de parcela PPT;
- 683 filas con nombre de titular;
- 565 con certificado parcelario;
- 454 con constancia de vigencia;
- 378 con folio de derechos;
- 460 con COP firmado;
- 407 con ingreso del COP al RAN;
- 345 con inscripción del COP en el RAN;
- 118 con ampliación;
- 272 con información en el primer oficio FIFONAFE;
- `NÚMERO DE TRAMO`: 0 filas con dato;
- `CLAVE DEL TRAMO`: 567 filas con dato, usado como referencia repetitiva y no como eje del seguimiento.

### Seguimiento colectivo México–Querétaro

Archivo auditado: `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` (versión sanitizada para análisis).

Hoja `INFORME M-Q`:

- 96 filas de seguimiento colectivo;
- 74 núcleos agrarios distintos;
- 70 núcleos coinciden también con la hoja individual;
- 68 filas con destino de superficie;
- sólo 19 con número de parcela/solar;
- 45 registros de `TIERRAS DE USO COMÚN`;
- también aparecen superficies a favor del núcleo, parcela escolar, UAIM, canales, derechos de paso y solares;
- 86 filas con sensibilización programada y 86 con sensibilización realizada;
- 86 con caminamiento programado y 86 con caminamiento realizado;
- 75 con asamblea realizada;
- 60 con ingreso del acta al RAN;
- 44 con acta inscrita;
- 58 con COP firmado;
- 54 con ingreso del COP al RAN;
- 41 con COP inscrito;
- 26 con primer oficio FIFONAFE;
- `CLAVE DEL TRAMO`: 0 filas con dato;
- `NÚMERO DE TRAMO`: 0 filas con dato.

### Excel general

`PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx` muestra que la salida principal esperada es un reporte por Proyecto con métricas de:

- núcleos agrarios;
- sensibilización;
- caminamiento;
- asambleas;
- RAN;
- COP colectivos;
- modificatorios;
- superficie adicional;
- obras complementarias;
- retiro de fondos;
- expropiación directa;
- parcelas afectadas y COP individuales.

## 3. Conclusión de cardinalidad

Los Excel respaldan:

```text
Proyecto
  ↓
Proyecto_Nucleo
  ↓
NucleoAgrario
```

y, dentro del núcleo:

```text
Colectivo:
Núcleo → Afectación colectiva → Asamblea / Convenio → RAN → FIFONAFE → Pago

Individual:
Núcleo → Parcela → Afectación individual → Convenio → RAN → FIFONAFE → Pago
```

No respaldan que `Tramo` sea propietario del expediente.

## 4. Arquitectura objetivo

```text
PROYECTO
│
├── TRAZO
│     sólo representación cartográfica
│
└── PROYECTO_NUCLEO
      ↓
   NÚCLEO AGRARIO
      ├── ORV
      ├── Padrón
      ├── Sensibilización
      ├── Caminamiento
      │
      ├── AFECTACIÓN COLECTIVA
      │      ├── Asamblea
      │      │      └── RAN Acta
      │      └── Convenios
      │             ├── COP
      │             ├── Modificatorio
      │             ├── Superficie adicional
      │             └── Obras complementarias
      │                    ↓
      │                   RAN
      │                    ↓
      │                FIFONAFE
      │                    ↓
      │              Indemnización
      │                    ↓
      │                  Pago
      │
      └── PARCELAS
             ↓
          PARCELA
             ├── titular(es)
             ├── certificado
             ├── folio
             ├── constancia
             ├── geometría opcional
             └── AFECTACIÓN INDIVIDUAL
                    └── Convenios
                           ├── COP
                           ├── Modificatorio
                           ├── Ampliación
                           └── Ampliación remanente
                                  ↓
                                 RAN
                                  ↓
                              FIFONAFE
                                  ↓
                            Indemnización
                                  ↓
                                Pago
```

## 5. Decisiones funcionales

1. `Tramo` deja de ser entidad funcional obligatoria.
2. `TramoNucleo` deja de ser expediente maestro.
3. Se introduce un contexto mínimo `ProyectoNucleo`.
4. Parcela es central para derechos individuales, no para colectivos.
5. Una afectación colectiva no exige parcela.
6. Convenio es la unidad principal para las variantes COP.
7. `AfectacionCiclo` queda marcado para eliminación si la migración demuestra cobertura total sin pérdida.
8. Sensibilización/caminamiento iniciales pertenecen a Proyecto–Núcleo.
9. Actuaciones adicionales de superficie adicional/obras/ampliación se relacionan con la afectación/convenio correspondiente.
10. La geometría no determina hechos administrativos.
11. La superficie oficial procede de captura documental.
12. PostGIS se conserva para trazo, núcleos y parcelas.
13. Geometría de parcela es opcional.
14. RAN de Acta y RAN de Convenio se mantienen separados.
15. FIFONAFE conserva los cuatro oficios y fechas de los Excel.
16. Las columnas auxiliares de Excel (`TRIMESTRE`, `POR NA`) se derivan, no se almacenan.

## 6. Elementos actuales a mantener

- `proyecto`
- `entidad_federativa`
- `municipio`
- `nucleo_agrario`
- `persona`
- `persona_nucleo`
- `orv`
- `orv_integrante`
- `padron_historial`
- `parcela`
- `parcela_titular`
- `afectacion` (simplificada)
- `asamblea`
- `convenio`
- `tramite_fifonafe` (simplificado si procede)
- `pago_indemnizacion`
- soporte documental/versionado útil
- auditoría/baja lógica proporcional a los datos críticos

## 7. Elementos actuales bajo CONTRACT

- `tramo`
- `tramo_nucleo`
- `seccion_derecho_via`
- `candidato_tramo_nucleo`
- `usuario_tramo`
- `afectacion_ciclo`
- reglas geoespaciales que actúan como gates de negocio
- cálculo espacial de superficies oficiales/liberadas

Ninguno debe eliminarse antes de migrar y validar sus dependencias.

## 8. Modelo geoespacial objetivo

```text
trazo_proyecto
- id_proyecto
- geometria_linea
- fuente
- version

nucleo_agrario
- geometria_poligono
- fuente_datos

parcela
- geometria_poligono NULL
- fuente_geometria NULL
```

No se requiere `SeccionDerechoVia` para decidir afectaciones.

## 9. Dashboard como prueba de aceptación

La refactorización debe considerarse correcta sólo si el nuevo modelo puede reconstruir los indicadores del Excel general sin usar `TramoNucleo` o `AfectacionCiclo` y sin calcular superficies desde geometría.

## 10. Referencias de dominio

- `docs/contexto/estructura_datos_propiedad_social_fuente.md`
- `docs/contexto/flujo_liberacion_propiedad_social_fuente.md`
- Procuraduría Agraria: https://www.pa.gob.mx/normatecapa/lineamientos.html
- Lineamientos/modelos de COP: https://www.pa.gob.mx/normatecapa/lineamientos/lineamientos_en_materia_de_convenios.pdf
- Ley Agraria: https://www.diputados.gob.mx/LeyesBiblio/pdf/LAgra.pdf
- Datos Abiertos RAN: https://datos.ran.gob.mx/conjuntoDatosPublico.php
