# Descripción proceso - Modelo funcional objetivo

> Estado: documento canónico del proceso objetivo.  
> Fecha de actualización: 2026-08-25.  
> Alcance: especificación funcional; no describe todavía la base de datos implementada.

## Principio rector

SOFTWARE-PA representa los hechos administrativos que aparecen en los Excel de seguimiento. El flujograma y la normativa ayudan a interpretar el orden y significado, pero no autorizan crear pantallas, módulos o etapas sin datos reales que capturar.

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

La navegación administrativa objetivo es `Proyecto -> Entidad Federativa -> Municipio -> Núcleo Agrario`. Dentro del núcleo se muestran Resumen, Datos generales, ORV, Padrón, Sensibilización, Caminamiento, Derechos colectivos y Parcelas/Derechos individuales.

La ruta individual es `Proyecto -> Entidad -> Municipio -> Núcleo -> Parcela -> Convenios`. La ruta colectiva es `Proyecto -> Entidad -> Municipio -> Núcleo -> Afectación colectiva -> Asamblea / Convenios`.

## Secuencia colectiva

1. Crear o resolver ProyectoNucleo.
2. Registrar datos generales del núcleo, ORV y padrón.
3. Capturar sensibilización y caminamiento cuando existan.
4. Crear una afectación colectiva sin exigir parcela.
5. Registrar avalúo simple si existe en fuente.
6. Registrar asamblea y RAN del acta.
7. Registrar uno o más convenios: COP original, modificatorio, superficie adicional u obras complementarias.
8. Registrar RAN del convenio, FIFONAFE, indemnización y pago.

Una ruta colectiva puede no aplicar por no afectación de uso común sin bloquear automáticamente una ruta individual.

## Secuencia individual

1. Crear o resolver ProyectoNucleo.
2. Crear o resolver parcela como entidad central de la ruta individual.
3. Registrar titulares, certificado parcelario, folio de derechos y constancia de vigencia.
4. Crear afectación individual con superficie administrativa capturada.
5. Registrar convenios: COP original, modificatorio, ampliación o ampliación remanente.
6. Registrar RAN del convenio, FIFONAFE, indemnización y pago.

La parcela puede no tener geometría. Esa ausencia no impide seguimiento, consulta ni captura documental.

## Convenios y excepciones

Los convenios son registros repetibles. Las columnas repetidas del Excel se convierten en filas y no en nuevas entidades por cada variante.

Permuta se conserva como modalidad especial del COP original, salvo que el instrumento real demuestre que debe clasificarse como `otro`. El caso de un convenio relacionado con dos solares o varias afectaciones se resuelve con `convenio_afectacion` y observación, sin complicar la captura ordinaria.

## Superficies y fechas

Las superficies son datos administrativos: preliminar, real afectada, superficie del convenio, superficie adicional, ampliación y ampliación remanente. No se derivan oficialmente por `ST_Area`.

Las fechas programadas no se mezclan: firma programada, ingreso RAN programado, ingreso real, inscripción y firma son hechos distintos.

## RAN, FIFONAFE, indemnización y pago

RAN del acta y RAN del convenio se separan. En individuales sólo se registra RAN del convenio.

FIFONAFE conserva los cuatro oficios observados en Excel. Indemnización registra estatus; pago registra el hecho financiero.

## Lo que no genera módulos objetivo

No crear módulos objetivo para análisis preliminar, revisión social, revisión jurídica, revisión registral general, acercamiento inicial, identificación preliminar u otras etapas del flujograma sin campos necesarios de captura en los Excel.

`afectacion_ciclo` pertenece a la implementación vigente y no es requisito funcional objetivo. El linaje se preserva con tipo de convenio, consecutivo/version, `id_convenio_padre`, contexto de actividad y relaciones directas entre afectación, asamblea y convenio.

## Geoespacial

El mapa muestra trazo, núcleo y parcelas opcionales. Sirve para apoyo territorial y navegación. No crea afectaciones, no bloquea por falta de intersección y no determina montos ni pagos.

## Casos especiales

Expropiación directa, comunidad indígena y no afectación de uso común se registran como condiciones. No implican automáticamente salida terminal global de todo el núcleo ni cancelan rutas que puedan seguir siendo aplicables.
