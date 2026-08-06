# PROMPT 1B.2 — INCORPORAR DECISIONES APROBADAS

Usa este prompt después de responder las preguntas funcionales.

Actúa como arquitecto de software senior.

Incorpora a la propuesta técnica las siguientes decisiones funcionales aprobadas por el usuario:

```text
[PEGAR AQUÍ LAS DECISIONES APROBADAS]
```

## Tarea exacta

1. Verifica que las decisiones no contradigan `ESTADO_PROYECTO.md`.
2. Actualiza únicamente las secciones afectadas de la propuesta.
3. Resuelve los bloqueos identificados.
4. Ajusta:

   * reglas funcionales;
   * estados y transiciones;
   * modelo de datos;
   * backend;
   * frontend;
   * migración;
   * autorización;
   * pruebas;
   * criterios de aceptación.
5. Ejecuta nuevamente los gates de diseño.
6. No implementes código.

## Formato de salida

1. Decisiones incorporadas.
2. Cambios respecto de la propuesta anterior.
3. Propuesta técnica corregida.
4. Resultado de cada gate.
5. Riesgos restantes.
6. Veredicto.

El veredicto debe ser uno:

* Propuesta todavía bloqueada.
* Propuesta viable y lista para evaluación.

---
