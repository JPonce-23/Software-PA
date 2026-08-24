# Implementación del plan de alineación de SOFTWARE-PA

## 1. Preflight

- Rama: `feature/backend-logica`.
- Base de datos: `db_pruebas_alfredo`, PostgreSQL 15.4 y PostGIS 3.3.4.
- Migración inicial: `028` (`Trazo lineal sin inferencia de ancho y secciones espaciales explícitas`).
- Cambios locales detectados: ninguno; el árbol estaba limpio antes de iniciar.
- Respaldo: `backups/pre_029_alineacion_fuentes_20260822.dump`, formato custom, no vacío y con 732 entradas verificadas mediante `pg_restore -l`.
- Diferencias respecto al plan: D01-D10 continúan sin decisión funcional. Se ejecutó sólo el primer incremento independiente señalado por el propio plan. La migración `028` real corresponde al trazo lineal; la restricción global de oficios estaba en el esquema base y seguía activa.
- Estado: preflight aprobado. No se sobrescribió trabajo local ajeno.

## 2. Fases ejecutadas

| Fase | Estado | Cambios | Gate |
|---|---|---|---|
| Preflight | COMPLETA | Git, DB, esquema, FK, triggers, geometrías, conteos y respaldo | APROBADO |
| Modelo e integridad | COMPLETA para el incremento seguro | Migraciones 029 y 030 de FIFONAFE | APROBADO |
| ORM | SIN CAMBIO REQUERIDO | Las columnas objetivo ya existían y coinciden con el esquema | APROBADO |
| Schemas y API | COMPLETA para B05, B06, B12, B16-B19, B22-B23 | Contratos, validaciones y alcance territorial | APROBADO |
| Flujo de negocio | PARCIAL | Captura progresiva y regla documental por tipo; no se resolvieron D02-D09 | APROBADO en alcance |
| Frontend y UX | COMPLETA para el incremento seguro | Formularios críticos, padrón, ORV y terminología | APROBADO |
| Conciliación | COMPLETA sin escrituras | Reporte SQL reproducible | APROBADO |
| Pruebas y despliegue local | COMPLETA | Backend, SQL, lint, build, E2E y salud HTTP | APROBADO |
| Alineación integral | BLOQUEADA PARCIALMENTE | Restan decisiones D01-D10 y las fases dependientes | NO APLICA todavía |

## 3. Base de datos

### Migraciones creadas

| Migración | Objetivo | Resultado |
|---|---|---|
| `029_fifonafe_oficios_por_tipo_expand.sql` | Agregar `chk_029_informe_completo_requiere_resultado_y_oficios` como `NOT VALID` y validarlo sin retirar la regla anterior | Aplicada y validada |
| `030_fifonafe_oficios_por_tipo_switch.sql` | Verificar informes completos y retirar sólo `chk_estatus_completo_requiere_oficios` | Aplicada; datos históricos preservados |

### Cambios estructurales

| Entidad | Cambio |
|---|---|
| `tramite_fifonafe` | Un informe completo exige resultado, cuatro oficios y cuatro fechas |
| `tramite_fifonafe` | Una indemnización ya no necesita duplicar los oficios del informe enlazado |
| `schema_migrations` | Versiones `029` y `030` registradas |

No se agregaron tablas, columnas, geometrías ni relaciones. No hubo backfill ni
eliminación de valores. Los 18 informes y 18 indemnizaciones completos
conservaron todos sus datos después de las migraciones.

## 4. Backend

| Archivo | Cambio | Motivo |
|---|---|---|
| `backend/app/schemas.py` | Campos completos de convenio/ORV, números no negativos, resultado de actividad, fechas coherentes y estados FIFONAFE tipados | Captura y validación end-to-end |
| `backend/app/services/access.py` | Filtro territorial reutilizable por núcleo | Evitar exposición entre tramos |
| `backend/app/main.py` | Alcance territorial de padrón, validación de fechas y validación progresiva de informe | Integridad y mensajes antes del commit |
| `backend/app/routers/personas.py` | Alcance territorial en ORV, padrón indirecto, parcelas y vínculos con núcleo | Cerrar rutas que omitían `usuario_tramo` |
| `backend/tests/test_alineacion_fuentes.py` | Pruebas de contratos nuevos | Evidencia directa del incremento |
| `backend/tests/test_subcorte_2b.py` | Indemnización sin oficios duplicados y aislamiento ORV/padrón | Regresión de flujo y seguridad |

Los modelos SQLAlchemy no se modificaron: ya declaraban los campos y relaciones
utilizados. Se conservaron `AuditableMixin`, bajas lógicas y cascadas existentes.

## 5. Frontend

| Archivo | Cambio | Motivo |
|---|---|---|
| `frontend/src/components/fase2/PadronPanel.jsx` | Alta, consulta y edición del padrón histórico | La DB no tenía una UI operativa |
| `frontend/src/components/fase2/OrvPanel.jsx` | Número, acta RAN y soporte documental | Completar datos fuente de ORV |
| `frontend/src/components/fase2/FlujoLiberacionPanel.jsx` | Actividad completa y FIFONAFE progresivo por tipo | Evitar fechas/oficios fabricados |
| `frontend/src/pages/FormAsamblea.jsx` | Padrón y cuatro hitos RAN; payload de alta/edición separado | Captura registral y contrato correcto |
| `frontend/src/pages/FormConvenio.jsx` | Superficie, montos y RAN según variante; payload discriminado | No enviar campos incompatibles ocultos |
| `frontend/src/pages/ExpedienteDetail.jsx` | Padrón junto a representación y nombre funcional | Organizar por responsabilidad del núcleo |
| `frontend/src/pages/AfectacionSubexpediente.jsx` | Terminología funcional y layout móvil | No exponer “subexpediente” ni desbordar |
| `frontend/src/pages/ExpedientesList.jsx` | Encabezado por proyecto, tramo y núcleo | Navegación comprensible |
| `frontend/src/App.jsx` | Títulos visibles de expediente y afectación | Ocultar el concepto técnico `tramo_nucleo` |
| `frontend/src/index.css` | Layout responsivo de afectación | Gate móvil de Playwright |
| `frontend/tests/e2e/expedientes.spec.js` | Navegación de expediente, representación, padrón, flujo y afectación | Gate funcional no destructivo |

## 6. Flujo funcional implementado

```text
Proyecto
→ Tramo
→ Núcleo agrario dentro del tramo
→ Expediente del núcleo en el tramo (tramo_nucleo interno)
→ Sensibilización/caminamiento
   → fecha programada
   → fecha realizada
   → resultado
   → antecedente común o ciclo colectivo posterior
→ Afectación confirmada existente
→ Ciclo
→ Asamblea colectiva
   → padrón histórico
   → convocatoria/realización/resultado
   → ingreso, solicitud, calificación e inscripción RAN
→ Convenio por variante
   → superficie aplicable
   → montos aplicables
   → soporte documental
   → seguimiento RAN progresivo
→ Informe FIFONAFE de no conflictos
   → programado/pendiente
   → resultado y oficios al completar
→ Indemnización enlazada al informe favorable
   → pago suficiente
   → completar sin duplicar oficios
```

No se cambió el nacimiento de `afectacion`, los gates de liberación ni las
salidas terminales porque dependen de D02, D04-D09.

## 7. Conciliación de datos

| Estado | Registros |
|---|---:|
| Migrados automáticamente | 36 |
| Revisión manual | 157 |
| No migrables | 0 |

El término “migrados” incluye registros que ya cumplían la regla nueva y fueron
validados sin reescritura. La revisión manual comprende 18 indemnizaciones con
oficios históricos preservados, 72 ORV sin integrantes normalizados, 23
asambleas completas sin padrón, 43 convenios firmados con información económica
incompleta según el reporte y una actividad realizada sin toda la evidencia de
captura. El inventario reproducible está en
`backend/db/reports/030_conciliacion_alineacion_fuentes.sql`.

## 8. Seguridad e integridad

* RBAC: se conservaron roles de lectura/escritura existentes.
* Autorización territorial: padrón, ORV, integrantes, parcelas y vínculos con núcleo aplican `usuario_tramo` mediante `require_nucleo_access` o `filter_by_user_nucleos`.
* Auditoría: las escrituras siguen fijando contexto antes del commit; las migraciones no reescribieron datos.
* Constraints: la regla FIFONAFE por tipo está validada en PostgreSQL y replicada en Pydantic/API.
* Triggers: no se retiró ningún trigger de auditoría, secuencia, pago, geometría o baja lógica.
* Bajas lógicas: no hubo `DELETE` físico ni cascada destructiva nueva.

## 9. Pruebas ejecutadas

| Prueba | Resultado |
|---|---|
| Backup `pg_restore -l` | 732 entradas; válido |
| Migraciones 029/030 sobre base activa | APROBADO |
| Constraint SQL en transacción revertida | Indemnización sin oficios permitida; informe incompleto rechazado |
| Backend focalizado | 13 aprobadas |
| Backend completo | 190 aprobadas, 13 omitidas, 0 fallidas |
| Frontend lint | 0 advertencias, 0 errores |
| Frontend build | APROBADO, 201 módulos |
| Playwright escritorio/móvil | 4 aprobadas |
| Salud Docker/HTTP | DB, backend, frontend y scheduler saludables |
| `git diff --check` | APROBADO |

La primera ejecución completa tuvo dos fallos porque la base aislada sólo
contenía un municipio; tras cargar un segundo municipio de catálogo, ambos casos
pasaron y la suite completa quedó verde. `seed.sql` no pudo utilizarse en la base
limpia porque intenta crear un `tramo_nucleo` sin sección espacial después de la
migración 019; la integridad no se relajó.

## 10. Validación contra estructura_datos_propiedad_social_fuente.md

| Requisito | Implementación | Resultado |
|---|---|---|
| Sensibilización/caminamiento: programación, realización y resultado | `actividad_campo` + formulario | CUMPLE en alcance |
| ORV: vigencia, identificación, acta y documentos | Campos existentes + `OrvPanel` | CUMPLE en nuevas capturas |
| Integrantes ORV | Relación `orv_integrante` existente | CUMPLE; 72 legacy en revisión |
| Padrón histórico | `padron_historial`, panel y selector de asamblea | CUMPLE en nuevas capturas |
| Asamblea: convocatorias, resultado, padrón y RAN | Schema y formulario ampliados | CUMPLE en captura |
| Convenios colectivos/individuales por variante | Payload y superficie discriminados | CUMPLE en captura; obligatoriedad pendiente D05 |
| Montos 90/100/BDT | Se muestran sólo cuando aplican | CUMPLE en captura; 43 legacy en revisión |
| RAN progresivo | Campos existentes en asamblea/convenio | CUMPLE; aviso/verificación separados pendientes D03 |
| FIFONAFE: informe y oficios | Regla por tipo, API y UI progresiva | CUMPLE |
| Pago | Lógica previa conservada | CUMPLE implementación previa; alcance fuente pendiente D10 |
| E/C | Sin significado inequívoco | PENDIENTE D01 |
| Avalúo/análisis/acercamiento | No existe evidencia mínima definida | PENDIENTE D08 |
| Comunidad indígena | Booleano existente; sin nueva automatización | PENDIENTE D04 |
| Geometrías y SRID | PostGIS 4326 e índices existentes, sin cambios | CUMPLE esquema actual |

## 11. Validación contra flujo_liberacion_propiedad_social_fuente.md

| Etapa/Regla | Implementación | Resultado |
|---|---|---|
| Proyecto → tramo → núcleo | Rutas y relaciones actuales | CUMPLE |
| Sensibilización antes de caminamiento | Trigger existente y captura completa | CUMPLE |
| Alta de afectación sólo al confirmar | No se adelantó el alta | PARCIAL; gate exacto pendiente D05 |
| Ruta colectiva e individual | Tipos, ciclos y formularios discriminados | PARCIAL; decisiones D06-D09 |
| Asamblea y autorización colectiva | Selección por afectación/ciclo y anuencia otorgada | PARCIAL; semántica de conciliación pendiente D06 |
| Firma y seguimiento RAN | Captura progresiva por convenio/asamblea | CUMPLE en datos existentes |
| Aviso/verificación de inscripción | No se inventaron campos | PENDIENTE D03 |
| Informe de no conflictos | Resultado/oficios exigidos al completar | CUMPLE |
| Convergencia a integración/pago | Regla previa preservada | PENDIENTE D02 |
| Pago suficiente | Trigger y servicio existentes; regresión verde | CUMPLE implementación previa |
| Retiro de fondos y liberación | Regla previa preservada | PENDIENTE D07 |
| Expropiación directa | Doble alcance existente no migrado | PENDIENTE D09 |

## 12. Problemas encontrados durante la implementación

| Problema | Severidad | Solución/Estado |
|---|---|---|
| Constraint global exigía oficios también a indemnización | ALTA | Corregido con 029/030 |
| Padrón y ORV sin aislamiento territorial consistente | CRÍTICA | Corregido y probado |
| Formularios omitían campos existentes o enviaban campos incompatibles | ALTA | Corregido por variante/etapa |
| UI forzaba informe completo y `hay_conflictos=false` | ALTA | Captura progresiva implementada |
| Vista móvil de afectación desbordaba | MEDIA | Layout responsivo y E2E corregidos |
| `seed.sql` incompatible con regla espacial de migración 019 | MEDIA | Documentado; no se relajó constraint |
| Datos legacy incompletos/no normalizados | ALTA | Reporte; 157 revisiones manuales |

## 13. Decisiones funcionales pendientes

| Decisión | Impacto | Bloquea |
|---|---|---|
| D01: significado y naturaleza de E/C | Campo y presentación | Datos generales |
| D02: evidencia que permite iniciar integración para pago | Regla crítica | FIFONAFE/pago |
| D03: aviso y verificación RAN como hitos separados | Modelo/contrato | Migración registral |
| D04: efecto de comunidad indígena/no uso común | Estados | Salidas y UX |
| D05: mínimos de afectación, firma y cierre RAN | Obligatoriedad | Constraints y gates |
| D06: asamblea que autoriza cada convenio colectivo | Integridad | Bifurcación colectiva |
| D07: aplicabilidad del retiro de fondos | Liberación | Estado final colectivo |
| D08: evidencia de análisis, acercamiento y avalúo | Nuevas responsabilidades | Investigación/negociación |
| D09: expropiación por afectación o por cruce | Alcance | Estados y migración |
| D10: detalle obligatorio de pagos | Alcance funcional | Reportes financieros |

## 14. Elementos legacy pendientes de retirar

| Elemento | Consumidores actuales | Momento recomendado |
|---|---|---|
| Cargos ORV en columnas de texto | Compatibilidad API y 72 ORV sin integrantes | Tras conciliación y observación |
| `parcela.nombre_titular` | Endpoints compatibles y datos previos | Tras validar `parcela_titular` |
| Nombre técnico `subexpediente` en rutas/archivos backend | Deep links y contratos | Sólo con redirección/versionado posterior |
| Oficios históricos en indemnización | 18 registros | No retirar sin evidencia manual |
| Campos/rutas legacy de flujo | Consumidores no inventariados completamente | Fase CONTRACT independiente |

## 15. Archivos modificados

1. `backend/app/main.py`
2. `backend/app/routers/personas.py`
3. `backend/app/schemas.py`
4. `backend/app/services/access.py`
5. `backend/db/migrations/029_fifonafe_oficios_por_tipo_expand.sql`
6. `backend/db/migrations/030_fifonafe_oficios_por_tipo_switch.sql`
7. `backend/db/reports/030_conciliacion_alineacion_fuentes.sql`
8. `backend/tests/test_alineacion_fuentes.py`
9. `backend/tests/test_subcorte_2b.py`
10. `frontend/src/App.jsx`
11. `frontend/src/components/fase2/FlujoLiberacionPanel.jsx`
12. `frontend/src/components/fase2/OrvPanel.jsx`
13. `frontend/src/components/fase2/PadronPanel.jsx`
14. `frontend/src/index.css`
15. `frontend/src/pages/AfectacionSubexpediente.jsx`
16. `frontend/src/pages/ExpedienteDetail.jsx`
17. `frontend/src/pages/ExpedientesList.jsx`
18. `frontend/src/pages/FormAsamblea.jsx`
19. `frontend/src/pages/FormConvenio.jsx`
20. `frontend/tests/e2e/expedientes.spec.js`
21. `docs/propuestas/2026-08-22-implementacion-alineacion-fuentes-propiedad-social.md`

## 16. Estado de Git

* Archivos modificados: backend, frontend y pruebas listados en la sección 15.
* Archivos nuevos: migraciones 029/030, reporte SQL, pruebas de alineación, panel de padrón y este informe.
* Migraciones: 029 y 030 creadas, aplicadas en la base activa y en la base aislada.
* Cambios no relacionados preservados: no había cambios al iniciar; no se revirtieron archivos ajenos.
* Commit: no creado, porque no fue solicitado.

## 17. Veredicto final

`IMPLEMENTACIÓN PARCIAL — EXISTEN DECISIONES FUNCIONALES PENDIENTES`

## 18. Próximo paso

1. Resolver D01-D10 con responsable funcional, evidencia y fecha.
2. Revisar manualmente los 157 registros reportados, sin inferencias por nombre o fecha.
3. Corregir `backend/db/seed.sql` para crear una sección espacial antes de `tramo_nucleo` en esquemas posteriores a 019.
4. Ejecutar las fases dependientes: gates de afectación, bifurcación colectiva/individual, hitos RAN, convergencia de pago y cierre.
5. Realizar UAT jurídica y operativa antes de cualquier migración CONTRACT.
