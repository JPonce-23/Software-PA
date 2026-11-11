Fecha: 2026-10-29. Base original `683ff75613768de28a7127c7e33a6e2ef4fc40ff`; base candidata dev `e2699fe5c043996f7338bd63af3221957699bd65`; PR #5 observado `42ef451847dea8286c0f8d395b0d91675e62b69b`. SSALFER es el frontend oficial. **0 ramas y 0 commits creados; ningún push/PR/merge/despliegue.**

# Incidencias vigentes de conciliación y formato QA

INT001 acoplamiento React SS09: **resuelto localmente en la copia**, 25 tests PASS; falta comprobar futuroSHA/build, no cierre SS09. INT002 transporte Compose: **resuelto por combinación explícita en copia**, backend/env idénticos al local; sin merge real. INT003 sandbox map-performance: resuelto con repetición autorizada11 PASS. INT004 seis dependencias/pruebas nativas: pendientesQA, no PASS. INT005 límites HTTP: permanece pendiente; no se aceptó101m global. INT006 selección PR5: TLS/UID/workers/rate/CSP/deps/bajas pospuestos con fundamento, fuera del alcance conciliado; coordinación antes de superponer commits.

Distinguir prioridad de integración de severidad de vulnerabilidad. PASS/FAIL/BLOCKED/NOTRUN no son estados de cierreSS. No se observaron incidencias institucionales porque no se accedió aQA. Usar nuevocommit autorizado para correcciones futuras, sin reescribir historia ni modificar PR4/5 automáticamente.

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
