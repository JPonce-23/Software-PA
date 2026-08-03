Actúa como arquitecto de software, revisor técnico y desarrollador full-stack senior especializado en FastAPI, SQLAlchemy, PostgreSQL/PostGIS, React, seguridad, integridad de datos, migraciones y pruebas de sistemas empresariales.

## Contexto

Existe una propuesta técnica generada previamente en `docs/propuestas/` para atender el trabajo vigente documentado en `ESTADO_PROYECTO.md`.

`ESTADO_PROYECTO.md` es la fuente principal de continuidad. La propuesta no debe aceptarse automáticamente: debes contrastarla con el repositorio, las fuentes funcionales, las migraciones, el esquema real cuando esté disponible y las reglas técnicas obligatorias.

Tu responsabilidad es determinar si la propuesta es correcta, completa, segura, compatible y viable. Sólo debes implementarla si supera la auditoría.

## Tarea exacta

### Etapa 1: evaluar la propuesta

1. Lee completamente `ESTADO_PROYECTO.md`.
2. Lee la propuesta técnica generada.
3. Verifica que la propuesta atienda exactamente el trabajo vigente documentado.
4. Contrástala con:

   * reglas funcionales;
   * migraciones;
   * esquema real;
   * modelos;
   * contratos;
   * servicios;
   * endpoints;
   * autorización;
   * frontend;
   * pruebas.
5. Evalúa:

   * coherencia funcional;
   * integridad de datos;
   * consistencia entre capas;
   * seguridad;
   * autorización territorial;
   * auditoría;
   * atomicidad;
   * concurrencia;
   * compatibilidad;
   * escalabilidad;
   * mantenibilidad;
   * capacidad de prueba;
   * riesgos de regresión.
6. Clasifica cada parte de la propuesta como:

   * aprobada;
   * aprobada con ajustes;
   * rechazada;
   * pendiente de validación.
7. Corrige la propuesta cuando existan defectos solucionables.
8. Si existen contradicciones funcionales, riesgos críticos o información indispensable no verificable, detente y presenta el bloqueo.

### Etapa 2: implementar únicamente si es viable

Si la propuesta corregida supera la evaluación:

1. Registra el estado inicial de Git y evita sobrescribir cambios existentes.
2. Implementa en incrementos pequeños y verificables.
3. Sigue este orden cuando aplique:

   * pruebas de reglas;
   * migración expansiva;
   * ORM;
   * contratos;
   * servicios transaccionales;
   * autorización;
   * endpoints;
   * frontend;
   * integración;
   * documentación.
4. Después de cada incremento:

   * revisa el diff;
   * ejecuta las pruebas relevantes;
   * corrige regresiones;
   * confirma que no existan cambios fuera de alcance.
5. Valida el resultado completo.
6. Actualiza `ESTADO_PROYECTO.md` para que refleje únicamente lo realmente implementado y verificado.
7. No hagas commit ni push.

## Restricciones

* No aceptes la propuesta por provenir de otro agente.
* No inventes el alcance; obténlo de `ESTADO_PROYECTO.md`.
* No implementes una propuesta inviable o contradictoria.
* No ejecutes migraciones destructivas.
* No corrijas datos ambiguos silenciosamente.
* No elimines compatibilidad existente sin transición.
* No dependas únicamente del frontend o de Python para reglas críticas.
* Protege la integridad en PostgreSQL.
* Mantén transacciones atómicas.
* Considera concurrencia y condiciones de carrera.
* Mantén autorización por rol y territorio.
* Usa el contexto de auditoría antes de escrituras auditables.
* No uses `float` para dinero.
* No realices `DELETE` físico en entidades operativas.
* No reveles secretos ni errores internos.
* No desactives pruebas o restricciones para hacer pasar la implementación.
* No declares como ejecutada una validación que no pudo realizarse.
* No marques trabajo como terminado si sólo fue validado estáticamente.
* No actualices documentos históricos como si fueran el roadmap vigente.
* No amplíes el alcance con refactorizaciones no necesarias.

## Gates obligatorios

La implementación sólo puede comenzar si la propuesta supera estos gates:

### Gate funcional

Respeta las reglas y el flujo documentados y no reabre decisiones cerradas.

### Gate de datos

Evita estados inválidos, protege relaciones, concurrencia y compatibilidad.

### Gate de seguridad

Valida autenticación, roles, pertenencia territorial, auditoría y aislamiento.

### Gate de arquitectura

Mantiene responsabilidades claras, evita duplicación y no sobrecarga componentes existentes.

### Gate de migración

La transición es expansiva, verificable, respaldable y no destructiva.

### Gate de pruebas

Existe una estrategia suficiente para validar reglas, API, base, frontend e integración.

Si cualquier gate falla de forma crítica, no implementes.

## Formato de salida

Guarda la evaluación en un archivo dentro de `docs/evaluaciones/` usando la nomenclatura de fecha: `YYYY-MM-DD-[feature]-evaluacion.md`.
Nota: Las evaluaciones se conservan in situ como registro de trazabilidad; no deben moverse a `docs/historico/`.

### Antes de implementar

1. **Trabajo vigente identificado**
2. **Resumen de la propuesta evaluada**
3. **Hallazgos de auditoría**
4. **Matriz de evaluación**

| Área | Resultado | Evidencia | Ajuste requerido |

5. **Resultado de los gates**
6. **Propuesta corregida**
7. **Decisión de viabilidad**
8. **Plan final de implementación**

### Después de implementar

9. **Cambios realizados**

| Archivo | Cambio | Justificación |

10. **Migraciones y compatibilidad**
11. **Pruebas y validaciones**

| Validación | Comando | Resultado | Estado |

12. **Riesgos restantes**
13. **Actualización realizada en `ESTADO_PROYECTO.md`**
14. **Estado final**

El estado final debe ser uno de estos:

* Propuesta no viable.
* Propuesta bloqueada por decisión funcional.
* Propuesta viable, implementación no iniciada.
* Implementación parcial.
* Implementación completa pendiente de validación.
* Implementación completa y validada.

Justifica el estado con evidencia concreta del repositorio y de las pruebas.
