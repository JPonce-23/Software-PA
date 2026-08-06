# PROMPT 1D — PREPARAR ENTORNO PARA EL DISEÑO

Usa este prompt cuando el análisis del Prompt 1 no pueda comprobar el esquema o el entorno.

Actúa como ingeniero DevOps y desarrollador senior.

El análisis técnico quedó bloqueado porque no fue posible verificar el entorno ejecutable.

No implementes funcionalidad.

## Tarea exacta

1. Lee `ESTADO_PROYECTO.md`.
2. Revisa el reporte de bloqueo.
3. Identifica qué información no pudo verificarse.
4. Localiza:

   * `.env.example`;
   * archivos Compose;
   * Dockerfiles;
   * documentación;
   * scripts de migración;
   * scripts de pruebas.
5. Verifica:

   * Docker;
   * Docker Compose;
   * contenedores;
   * PostgreSQL;
   * variables de entorno;
   * dependencias;
   * migraciones aplicadas;
   * puertos;
   * volúmenes.
6. Prepara únicamente el entorno necesario para el análisis.
7. No inventes secretos.
8. Cuando falte un valor, indica su nombre, ubicación, propósito y fuente.
9. No apliques migraciones nuevas sin respaldo y prevalidación.
10. Realiza una comprobación mínima:

    * conexión a PostgreSQL;
    * estado de migraciones;
    * importación del backend;
    * conectividad entre servicios.

## Restricciones

* No elimines datos.
* No elimines volúmenes.
* No uses `docker compose down -v`.
* No restablezcas la base.
* No expongas secretos.
* No corrijas todavía la funcionalidad.

## Formato de salida

### Motivo del bloqueo

| Verificación | Requisito faltante | Evidencia |

### Estado del entorno

| Componente | Estado | Problema | Acción |

### Acciones ejecutadas

| Paso | Comando | Resultado |

### Veredicto

* Entorno listo para análisis.
* Entorno parcialmente preparado.
* Bloqueado por configuración.
* Bloqueado por credenciales.
* Bloqueado por infraestructura.

Cuando el entorno esté listo, vuelve a ejecutar el Prompt 1.

---
