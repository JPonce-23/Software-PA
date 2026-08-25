# Contexto funcional liberación propiedad social v2

> Estado: contexto interpretativo alineado al modelo objetivo.  
> Fecha de actualización: 2026-08-25.  
> `docs/Descripción proceso.md` es el modelo funcional objetivo canónico.

## Lectura de fuentes

Los Excel locales son la fuente primaria para campos de captura. Los documentos `*_fuente.md` conservan el flujo y la estructura literal originales. Las fuentes institucionales de Procuraduría Agraria, RAN, Ley Agraria y Reglamento de la Ley Agraria en Materia de Ordenamiento de la Propiedad Rural ayudan a interpretar asambleas, convenios, núcleos, parcelas y trámites, pero no crean datos inexistentes en el seguimiento.

## Enfoque del sistema

SOFTWARE-PA se concentra en capturar y consultar hechos administrativos: ProyectoNucleo, núcleo, ORV, padrón, actividades, afectaciones, asambleas, convenios, RAN, FIFONAFE, indemnización, pago, soporte y observaciones.

La geometría no es requisito para crear o confirmar una afectación. Sirve para mapa, visualización, navegación y consulta territorial.

## Etapas del flujograma

Las etapas del flujograma que no generan datos necesarios en Excel se conservan como contexto institucional. No deben convertirse en módulos objetivo de análisis preliminar, revisión social, revisión jurídica, revisión registral general, acercamiento inicial o identificación preliminar.

## Rutas funcionales

La ruta colectiva y la ruta individual pueden coexistir o no aplicar de manera independiente. Expropiación directa, comunidad indígena y no afectación de uso común se registran como condiciones; no implican automáticamente salida terminal global.

Una afectación colectiva no exige parcela. Una parcela individual no exige geometría.

## Convenios, RAN y FIFONAFE

Los convenios son repetibles y tipificados. RAN del acta se separa de RAN del convenio. FIFONAFE conserva los cuatro oficios del seguimiento Excel. `afectacion_ciclo` no es concepto funcional objetivo.

## Superficies y avalúo

Las superficies se capturan desde documentación administrativa. Se separan preliminar, real afectada y superficie propia del convenio. `AVALÚO MAESTRO (INDAABIN) $` se documenta como campo simple de afectación.

## Relación con implementación actual

La implementación vigente puede contener Tramo, TramoNucleo, AfectacionCiclo, `usuario_tramo` y validaciones espaciales. Esos elementos no prevalecen sobre el modelo objetivo y deberán tratarse en una fase posterior de diseño/migración.
