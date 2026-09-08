# Preparación 007 — convenios

Estado actual para handoff: 007 fue aplicada y validada en QA; la migración es
inmutable y quedó publicada en `feature/backend-logica`. Este documento conserva
las decisiones de preparación y las reglas funcionales de Convenios. Los campos
007 ya forman parte del ORM/API/OpenAPI del esquema 008.

## Decisiones cerradas

| Dato | Dueño | Regla |
|---|---|---|
| Superficie física vigente | `afectacion` y `afectacion_unidad_agraria` | Se reporta por afectación/unidad física, no sumando instrumentos. |
| Superficie declarada | `convenio.superficie_ha` | Es literal del instrumento; no implica adición. |
| Impacto superficial | `convenio_afectacion` | Efecto y delta firmado por relación; pendiente conserva `NULL`. |
| Montos declarados | `convenio.monto_90`, `monto_100`, `monto_bdt` | Tres universos paralelos, nunca un total aditivo entre sí. |
| Impacto económico | `convenio` | Una vez por instrumento/concepto; no se une a la relación N:M. |
| Antecedente | `convenio` | `no_aplica`, `vinculado`, `referido_sin_soporte` o `pendiente_identificar`; un padre sólo existe con FK real. |
| Firma | `expediente_requisito` + Documento | Fecha y referencia no acreditan firma completa. El backfill sólo crea `pendiente_validacion`. |
| Comparecencia colectiva | `convenio_compareciente` | Reutiliza Persona y acreditación; ORV se valida contra núcleo y fecha del acto. Un externo puede usar acreditación documental sin ORV. |

Los efectos admitidos son `adicion`, `sustitucion`, `correccion`, `sin_cambio`
y `pendiente`. No se derivan de `tipo_convenio`. `sustitucion` y `correccion`
pueden tener delta firmado positivo, cero o negativo; si no está demostrado, el
efecto sigue pendiente y el valor permanece `NULL`.

## Backfill y compatibilidad

- Cambiar escala de superficies a `NUMERIC(15,7)` conserva exactamente los
  valores ya almacenados; no recupera decimales perdidos.
- Todo efecto histórico inicia `pendiente`, con impactos `NULL`.
- Sólo un `id_convenio_padre` existente produce `estado_antecedente=vinculado`.
  Un derivado sin padre queda `pendiente_identificar`, nunca enlazado por nombre,
  fecha o consecutivo.
- Una `fecha_firma` histórica sin requisito genera una revisión documental
  pendiente; no se marca firma disponible ni representación acreditada.
- Las seis vistas preexistentes dependientes (`vw_proyecto_nucleo_resumen` y las
  cinco vistas efectivas de reporting 006) guardan definición, comentario,
  propietario y ACL; se retiran en orden explícito y se recrean sin alterar sus
  indicadores. No hay `DROP CASCADE`.
- Los indicadores nuevos tienen clave, universo, unidad y cobertura propia:
  valor declarado por instrumento; impacto por relación superficial o por
  instrumento/concepto económico; periodo sólo con firma acreditada; cobertura
  con contadores de clasificados, pendientes y sin firma acreditada.

## Casos preparados, sin resolver evidencia pendiente

| Caso/celda ya auditada | Clase | Expectativa 007 |
|---|---|---|
| Individuales `PROPUESTA`, AD65/BP65, El Muerto–Ignacio Pérez P-201 | Hechos literales: `00-16-68.079`; sólo hay soporte referido del modificatorio | Con autorización de corrección, normalizar exactamente `0.1668079`; una afectación física y efecto no aditivo. No fabricar padre, titular ni fecha/contenido del original. |
| Individuales `PROPUESTA`, fila 353, San Pedrito P-111 | Dato sin soporte de convenio | No crear convenio; la incorporación de parcela no acredita instrumento. |
| Colectivos `INFORME M-Q`, filas 85–90; REV filas 70–73, Pueblo Nuevo de Jasso | Contradicción/revisión documental | Efectos, padre, firma y montos controvertidos permanecen pendientes. |
| REV `ASAMBLEAS PENDIENTES`, BP15/BX15, San Clemente | Hechos literales (`00-14-03.761`) y soporte registral pendiente | Tras autorización, conservar `0.1403761`. Una asamblea puede autorizar varios destinos/convenios; no multiplica superficies ni montos. |
| REV `ASAMBLEAS PENDIENTES`, fila 78, San Sebastián de las Barrancas | Hechos literales más falta de soporte de calificación | Asamblea compartida; firma, ingreso, calificación e inscripción siguen siendo hitos distintos. |
| Individuales `PROPUESTA`, P-15 fila 733, AD733/AT733/BF733 | Hechos literales de tres superficies (`00-94-43.113`, `00-39-78.597`, `00-41-28.559`) con linaje por conciliar | Tras autorización, conservar `0.9443113`, `0.3978597` y `0.4128559`; sólo clasificar adición y linaje con soporte. |

Las contradicciones permanecen en `trazabilidad_fuente` con tratamiento de
revisión. Los datos literales, normalizados y su archivo/hoja/fila/columna se
conservan ahí; no se duplican columnas de procedencia en las tablas de negocio.

## Activación validada y compatibilidad

1. La migración se aplica únicamente mediante el runner y queda registrada con
   checksum `adabd7775fb8165a1db8be04a93e7971fe207e745b410c57eb6fc76cc3a7e4f7`.
2. El contrato `backend/db/tests/007_convenios_impactos_precision_contract.sql`
   y la regresión `backend/db/tests/007_convenios_impactos_regression.sql` son
   la verificación canónica.
3. El typmod ORM de las superficies usa `Numeric(15,7)`; los schemas mantienen
   `Decimal` y serializan valores exactos, nunca `float`.
4. Los efectos se exponen por endpoints escalares y por el endpoint hijo de
   `convenio_afectacion`; los comparecientes se administran sólo en endpoints
   hijos. Un
   representante externo se crea en revisión, se vincula su Documento disponible
   y sólo entonces puede cerrarse la revisión; no se le exige pertenecer a ORV.
5. El contrato frontend vigente está en `API_CONTRATO_FRONTEND_V1.md` y el
   contrato mecánico en `openapi-backend-schema-008.json`.

Regresiones QA de cobertura:

- comparar esquema, filas y agregados de las seis vistas históricas antes/después
  de 007, permitiendo sólo el aumento de escala decimal;
- probar ORV vigente, ORV fuera de vigencia y representante externo con/sin
  Documento disponible, comprobando que `es_beneficiario_pago` no cambia;
- probar efectos válidos e inválidos para los cinco estados, incluyendo deltas
  negativos de corrección/sustitución y pendientes `NULL`;
- ejecutar los casos trazados P-201, San Pedrito, Pueblo Nuevo, San Clemente,
  Barrancas y P-15 sin completar datos documentales pendientes.

## Rollback operativo

007 es forward-only y QA sólo puede aplicarse sobre `software_pa_test`.
Inmediatamente antes debe generarse un `pg_dump -Fc` de esa misma base, restringido
en permisos, comprobarse que no esté vacío y validar su catálogo con `pg_restore
-l`. Deben registrarse checksum, hora, base origen y HEAD. `db_pruebas_alfredo` no
es destino de QA, respaldo alterno ni base de recuperación.

Si la validación falla: detener los escritores hacia `software_pa_test`, guardar
logs y un dump diagnóstico del estado fallido, cerrar/terminar sus conexiones,
eliminar únicamente `software_pa_test`, recrear ese mismo nombre con propietario
`pa_app` y restaurar el respaldo previo verificado. Un `pg_restore --clean` sobre
el esquema modificado no es suficiente, porque podría dejar objetos exclusivos de
007. Después se verifican checksums 001–006, contratos y conectividad antes de
reabrir escritores. No se crea una tercera base y no se restaura un golden. No se
ofrece SQL inverso: bajar escala podría perder precisión y eliminar
impactos/antecedentes capturados. Tampoco se borra la fila 007 ni se editan
checksums para simular rollback.
