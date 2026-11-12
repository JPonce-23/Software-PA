# Registro y formato de incidencias de ciberseguridad QA

Fecha: 2026-10-29. Alcance: SSALFER oficial. Base local 683ff75613768de28a7127c7e33a6e2ef4fc40ff, remoto observado e2699fe5c043996f7338bd63af3221957699bd65. Rama candidata aún no creada; 0 commits nuevos. Este registro no acredita ejecución integrada de QA.

## Clasificación y decisiones

Separar severidad del hallazgo original de prioridad/severidad de la incidencia. Crítico/Alto/Medio/Bajo/Informativo sólo con impacto/prerrequisitos justificados; no inventar CVSS. Tipo: regresión de código, integración/configuración, limitación del entorno, diseño/no implementado, evidencia insuficiente o falso positivo descartado. Un BLOCKED de infraestructura no es automáticamente una vulnerabilidad.

Resultados de prueba: PASS/FAIL/BLOCKED/NOT RUN. Estados de incidencia: abierta, triage, corrección autorizada, corregida pendiente retest, resuelta para alcance, aceptada como residual o descartada con evidencia. No cerrar el hallazgo SS completo por resolver una incidencia puntual.

## Incidencias detectadas en la consolidación

| ID | SS / tipo | Evidencia observada | Esperado vs observado | Severidad/prioridad de incidencia | Estado/decisión |
|---|---|---|---|---|---|
| INT-001 |SS-09/integración |GitHub dev=e2699fe…, local dev/origin-dev=683ff75…; remoto retira frontend/ y cambia Compose |Herramientas del candidato deben funcionar para SSALFER/target real; SS-09 exige fuente retirada y proyección falla con código 2 por frontend/package.json |Medio / bloqueante de publicación; no exploit demostrado |Abierta. Detener Git writes; coordinar nueva base y adaptación de herramientas con autorización. No reinstaurar React ni exigir su QA funcional |
| INT-002 |SS-04/08/09/10 / configuración |Compose base/override tienen cambios locales y remotos; bloques env múltiples SS |Transportar todos controles sin arranque accidental legado; no se ensayó integración textual/semántica real |Medio / bloqueante de consolidación hasta revisión |Abierta, relacionada INT-001. No copiar archivos remotos sobre locales ni resolver con merge automático |
| INT-003 |Prueba local/entorno sandbox |map-performance: spawnSync git EPERM al intentar git show histórico |Prueba puramente local debe poder leer baseline |Informativo / no bloqueante tras retest |Resuelta para ejecución: permiso explícito, 11/11 PASS; sin código cambiado ni red/DB/writes |
| INT-004 |SS-10/12/07 / cobertura |6 pruebas omitidas por Starlette/SQLAlchemy/psycopg2/pglast ausentes |Validación nativa requerida para su alcance; aquí no disponible |Informativo / pendiente QA del alcance |NOT RUN local; no instalar paquetes aquí, no marcar PASS. Compañero registra dependencias disponibles y ejecución autorizada |
| INT-005 |SS-08 / riesgo residual de configuración |client_max_body_size no declarado en server local |Uploads API de 25/100 MiB pueden necesitar presupuesto HTTP mayor por ruta; valor QA efectivo no observado |Medio original / confirmar en QA, no fallo institucional demostrado |Abierta como riesgo conocido; reportar 413 real y pedir corrección revisada si se reproduce, sin ampliar login por reflejo |

No existen incidencias QA institucionales observadas ni se enviaron mensajes al compañero. Los registros anteriores son hallazgos de preparación estática/aislada con base sin commits nuevos.

## Plantilla para cada incidencia futura

```text
ID: QA-SEC-____
Hallazgo(s) SS: ____
Fecha/hora/zona: ____
Reporta / responsable QA: ____
URL Draft PR y rama: ____
SHA exacto candidato: ____
SHA/base dev contra la que se validó: ____
Componente y versión/digest realmente observado: ____
Caso QA-01..10 y subcaso: ____
Tipo: regresión / configuración-integración / entorno / no implementado / evidencia
Severidad original SS: ____
Severidad de incidencia y fundamento: ____
Prioridad / bloquea Draft-Ready-integración-despliegue: ____
Autorización/alcance de prueba y dataset sintético: ____
Precondiciones verificadas (sin credenciales): ____
Comando/procedimiento sanitizado: ____
Pasos mínimos de reproducción:
1. ____
2. ____
Resultado esperado (política actual o control implementado): ____
Resultado observado: ____
Resultado: PASS / FAIL / BLOCKED / NOT RUN
Impacto / proyectos-recursos sintéticos afectados: ____
Evidencia protegida, ID/referencia y resumen redactado: ____
Qué no se pudo observar / limitación del entorno: ____
Relación con otros SS/incidencias: ____
Responsable de triage/corrección: ____
Decisión: corregir / pedir evidencia / aceptar residual / aplazar / descartar
Autorización funcional/técnica requerida: ____
Estado y motivo: ____
SHA real de corrección cuando exista: ____
Retest: fecha, mismo dataset/precondiciones, resultado y evidencia ____
Regresiones adicionales ejecutadas: ____
Cierre de incidencia por responsable: ____
¿Cambia estado de cierre del SS? Sí/No; fundamento separado: ____
```

Si el candidato aún no tiene SHA, declarar “sin commit, snapshot local” y enlazar el inventario; no fabricar un SHA candidato con el de base o un hash de archivo. Para INT-001 usar SHA remoto observado y técnica de proyección, no afirmar que se probó un merge real.

## Evidencia segura y retest

No adjuntar .env, claves, cookies/tokens reales, hashes de contraseña, DSN, cuerpos de documentos/personas, respaldos o capturas institucionales. Reproducir con sentinelas/datos sintéticos. En logs indicar códigos/correlación/SQLSTATE cuando sea seguro, no parámetros SQL ni str(exc). Revisar metadatos/URLs/headers de capturas y archivos antes de compartir; conservar lo completo sólo en el espacio autorizado de QA.

Un fallo de SQL/puerto/guard por configuración no autorizada se reporta como BLOCKED y no se “corrige” forzando nombres de BD, removiendo guardas o cambiando un rol. No restaurar/eliminar datos o temporales ajenos para limpiar un test. Un archivo publicado tras commit incierto requiere revisión de estado, no unlink automático.

Las correcciones posteriores van a la misma rama de seguridad cuando exista, mediante nuevos commits revisados y autorización correspondiente, sin reescribir historia para ocultar fallos. Cada commit menciona ID de incidencia/SS y añade prueba mínima de regresión; repetir el caso fallido y las suites afectadas. No hacer merge hasta resolver bloqueantes y aprobaciones imprescindibles. Ninguna corrección incidental productiva se realiza en esta preparación.
