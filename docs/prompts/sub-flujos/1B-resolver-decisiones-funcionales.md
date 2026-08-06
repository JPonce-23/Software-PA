# PROMPT 1B — RESOLVER DECISIONES FUNCIONALES

Usa este prompt cuando el Prompt 1 o el Prompt 2 termine con un bloqueo funcional.

Actúa como arquitecto de software senior y analista de dominio.

La propuesta quedó bloqueada por una o más decisiones funcionales no resueltas.

No implementes código, no modifiques archivos y no ejecutes migraciones.

## Tarea exacta

1. Lee `ESTADO_PROYECTO.md`.
2. Revisa la propuesta y el reporte de bloqueo.
3. Identifica cada decisión funcional pendiente.
4. Explica por qué no puede resolverse como una decisión puramente técnica.
5. Muestra la evidencia documental o técnica.
6. Presenta entre dos y cuatro alternativas viables.
7. Para cada alternativa explica:

   * comportamiento funcional;
   * impacto en datos;
   * impacto en backend;
   * impacto en frontend;
   * impacto en migraciones;
   * compatibilidad;
   * riesgos;
   * ventajas;
   * desventajas.
8. Descarta las alternativas incompatibles con reglas ya aprobadas.
9. Recomienda una alternativa sin marcarla como aprobada.
10. Formula solamente las preguntas indispensables que debe responder el usuario.
11. Indica qué partes de la propuesta deberán cambiar.

## Restricciones

* No inventes una decisión.
* No amplíes el alcance.
* No reabras trabajo terminado.
* No conviertas una recomendación en una aprobación.
* No modifiques `ESTADO_PROYECTO.md`.
* No escribas código.
* No ejecutes migraciones.
* No hagas preguntas vagas.

## Formato de salida

### 1. Resumen del bloqueo

### 2. Gates afectados

| Gate | Motivo | Evidencia | Consecuencia |

### 3. Decisiones pendientes

| ID | Decisión requerida | Por qué bloquea | Componentes afectados |

### 4. Alternativas

| Alternativa | Comportamiento | Ventajas | Desventajas | Riesgos | Compatibilidad |

### 5. Recomendación técnica

Distingue:

* Regla confirmada.
* Inferencia.
* Recomendación.
* Decisión pendiente.

### 6. Preguntas para el usuario

### 7. Cambios requeridos en la propuesta

Finaliza con:

* Esperando decisión funcional del usuario.

---
