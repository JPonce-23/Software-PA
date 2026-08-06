# PROMPT 2C — PREPARAR ENTORNO PARA IMPLEMENTACIÓN O VALIDACIÓN

Actúa como ingeniero DevOps y desarrollador full-stack senior.

La evaluación, implementación o validación quedó bloqueada por falta de entorno.

No corrijas todavía la funcionalidad.

## Tarea exacta

1. Lee `ESTADO_PROYECTO.md`.
2. Lee el reporte de bloqueo.
3. Identifica todas las validaciones no ejecutadas.
4. Verifica:

   * Docker;
   * Docker Compose;
   * contenedores;
   * PostgreSQL;
   * variables de entorno;
   * migraciones;
   * backend;
   * frontend;
   * dependencias;
   * puertos;
   * redes;
   * volúmenes.
5. Obtén los comandos reales desde el repositorio.
6. No inventes valores sensibles.
7. Levanta los servicios necesarios.
8. Verifica healthchecks, logs y conectividad.
9. Confirma las migraciones aplicadas.
10. Si existe una migración pendiente:

    * no la apliques sin respaldo;
    * ejecuta su prevalidación;
    * comprueba su orden;
    * informa el riesgo.
11. Ejecuta una validación mínima del sistema.
12. No corrijas defectos funcionales todavía.
13. No hagas commit ni push.

## Restricciones

* No elimines volúmenes.
* No uses `docker compose down -v`.
* No restablezcas la base.
* No muestres secretos.
* No inventes un `.env`.
* No marques como listo un componente no verificado.

## Formato de salida

### Motivo del bloqueo

| Validación | Requisito faltante | Evidencia |

### Estado del entorno

| Componente | Estado | Acción |

### Configuración requerida

| Variable o archivo | Estado | Fuente | Acción |

No muestres valores secretos.

### Acciones ejecutadas

| Comando | Resultado |

### Validación mínima

| Validación | Resultado | Evidencia |

### Veredicto

* Entorno listo para evaluación.
* Entorno listo para auditoría.
* Entorno parcialmente preparado.
* Bloqueado por configuración.
* Bloqueado por credenciales.
* Bloqueado por infraestructura.

Cuando esté listo, vuelve al prompt que quedó bloqueado.

---
