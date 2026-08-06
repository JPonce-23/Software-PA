# PROMPT 1C — RESOLVER CONTRADICCIONES

Usa este prompt cuando existan contradicciones entre documentación, migraciones, código o base de datos.

Actúa como arquitecto de software senior y auditor de requisitos.

No implementes cambios.

## Tarea exacta

1. Lee completamente `ESTADO_PROYECTO.md`.
2. Revisa la propuesta y el reporte de contradicciones.
3. Identifica cada contradicción entre:

   * fuentes funcionales;
   * documentación vigente;
   * documentos históricos;
   * migraciones;
   * esquema real;
   * modelos;
   * API;
   * frontend;
   * pruebas.
4. Clasifica cada afirmación como:

   * vigente;
   * histórica;
   * implementada;
   * propuesta;
   * contradictoria;
   * no verificable.
5. Aplica la jerarquía de fuentes definida en el proyecto.
6. Resuelve contradicciones técnicas cuando exista evidencia suficiente.
7. No resuelvas contradicciones funcionales mediante inferencias.
8. Indica las decisiones que requieren aprobación del usuario.
9. Propón qué documentación deberá corregirse después.

## Formato de salida

| ID | Fuente A | Fuente B | Contradicción | Evidencia | Resolución |

Después incluye:

1. Reglas vigentes resultantes.
2. Elementos históricos descartados.
3. Decisiones pendientes.
4. Cambios requeridos en la propuesta.

Finaliza con uno:

* Contradicciones resueltas; propuesta puede actualizarse.
* Requiere decisión funcional.
* Requiere verificar el entorno.

---
