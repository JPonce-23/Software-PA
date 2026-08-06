# PROMPT 3F — CIERRE TÉCNICO

Usa este prompt cuando la auditoría termine con:

* Implementación aprobada con riesgos menores.
* Implementación completa y validada.

Actúa como arquitecto de software senior responsable del cierre técnico.

## Tarea exacta

1. Lee `ESTADO_PROYECTO.md`.
2. Revisa:

   * propuesta aprobada;
   * reporte de implementación;
   * auditoría final;
   * diff actual.
3. Confirma que no existan hallazgos críticos o altos.
4. Revisa los riesgos menores.
5. Comprueba que todos los archivos modificados pertenezcan al alcance.
6. Busca:

   * secretos;
   * credenciales;
   * archivos temporales;
   * logs;
   * datos de prueba;
   * código comentado;
   * `TODO`;
   * `FIXME`;
   * pruebas deshabilitadas;
   * migraciones destructivas;
   * cambios accidentales.
7. Ejecuta nuevamente las validaciones finales.
8. Comprueba que `ESTADO_PROYECTO.md` coincida con el estado real.
9. Prepara un resumen técnico para revisión humana.
10. Genera una propuesta de commits.
11. Genera instrucciones de despliegue o aplicación de migraciones.
12. Genera un procedimiento de rollback.
13. No hagas commit ni push.

## Restricciones

* No rediseñes la funcionalidad.
* No amplíes el alcance.
* No ocultes pruebas fallidas.
* No ejecutes migraciones destructivas.
* No elimines volúmenes.
* No uses `docker compose down -v`.
* No muestres secretos.
* No declares listo algo no validado.

## Formato de salida

### 1. Estado recibido

### 2. Riesgos aceptados

| Riesgo | Severidad | Motivo de aceptación | Seguimiento |

### 3. Validaciones finales

| Validación | Comando | Resultado | Estado |

### 4. Revisión del diff

### 5. Estado de `ESTADO_PROYECTO.md`

### 6. Propuesta de commits

Para cada commit indica:

* Título.
* Propósito.
* Archivos.
* Dependencias.
* Orden.

No ejecutes los commits.

### 7. Procedimiento de despliegue

Indica:

* prerrequisitos;
* respaldo;
* migraciones;
* orden de servicios;
* validación posterior.

### 8. Procedimiento de rollback

### 9. Veredicto

* Requiere correcciones.
* Listo para revisión humana.
* Listo para commit.
* Listo para despliegue controlado.

---
