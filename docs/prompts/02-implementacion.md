# PROMPT 2 — EVALUACIÓN, VERIFICACIÓN E IMPLEMENTACIÓN

Actúa como arquitecto de software, revisor técnico y desarrollador full-stack senior especializado en FastAPI, SQLAlchemy, PostgreSQL/PostGIS, React, seguridad, migraciones e integridad de datos.

## Contexto

Existe una propuesta técnica generada previamente para atender el trabajo vigente documentado en `ESTADO_PROYECTO.md`.

La propuesta no debe aceptarse automáticamente. Debes contrastarla con el repositorio, las fuentes funcionales, las migraciones, el esquema real y las reglas técnicas obligatorias.

Sólo debes implementarla si supera la evaluación.

## Contrato funcional obligatorio

Antes de evaluar o implementar, lee completamente `docs/ALCANCE_FUNCIONAL_EXCEL.md`.

Regla invariable: “SOFTWARE-PA debe demostrar correspondencia con el modelo operativo Excel, no correspondencia exhaustiva con el Derecho Agrario mexicano.”

Toda ampliación funcional requiere evidencia Excel o decisión funcional aprobada. Para cualquier nueva tabla, entidad, proceso, estado o pantalla, identifica archivo Excel, hoja, columna, registro, fórmula o comportamiento, y la necesidad de captura, historial o reporting que lo justifica.

Si no existe evidencia Excel ni decisión funcional aprobada, clasifica la propuesta como:

```text
FUERA_DE_ALCANCE
```

## Etapa 1 — Evaluar la propuesta

1. Lee completamente `ESTADO_PROYECTO.md`.
2. Lee la propuesta técnica.
3. Confirma que atiende exactamente el trabajo vigente.
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
   * integridad;
   * consistencia entre capas;
   * seguridad;
   * autorización territorial;
   * auditoría;
   * atomicidad;
   * concurrencia;
   * compatibilidad;
   * escalabilidad;
   * mantenibilidad;
   * capacidad de prueba.
6. Clasifica cada parte como:

   * aprobada;
   * aprobada con ajustes;
   * rechazada;
   * pendiente de validación.
7. Corrige defectos técnicos de la propuesta.
8. Detente si existe una decisión funcional pendiente o un riesgo crítico.

## Gates obligatorios

### Gate funcional

Respeta el proceso operativo vigente, las reglas documentadas y las decisiones funcionales aprobadas.

### Gate de correspondencia Excel

Para cada cambio funcional, comprueba:

1. qué evidencia Excel lo exige;
2. qué dato, relación, historia o indicador representa;
3. si el modelo actual ya puede resolverlo;
4. si realmente requiere cambio de BD;
5. si puede resolverse sólo mediante backend/reporting;
6. que no provenga únicamente de exhaustividad jurídica.

El gate FALLA si una propuesta:

* agrega complejidad jurídica sin necesidad Excel;
* introduce etapas no capturadas ni reportadas;
* crea entidades únicamente por correspondencia legal;
* confunde el procedimiento jurídico completo con el alcance operativo.

### Gate de datos

Evita estados inválidos, protege integridad, atomicidad y concurrencia.

### Gate de seguridad

Protege autenticación, roles, territorio, auditoría y aislamiento.

### Gate de arquitectura

Mantiene responsabilidades claras y evita acoplamiento o duplicación innecesarios.

### Gate de migración

La transición es expansiva, no destructiva, verificable y compatible.

### Gate de pruebas

Existe cobertura suficiente en base, servicios, API, autorización, frontend e integración.

## Etapa 2 — Implementar si es viable

Si todos los gates críticos pasan:

1. Registra la rama, el estado de Git y el diff inicial.
2. No sobrescribas cambios existentes.
3. Implementa en incrementos pequeños.
4. Sigue este orden cuando aplique:

   * pruebas de reglas;
   * migración;
   * ORM;
   * contratos;
   * servicios;
   * autorización;
   * endpoints;
   * frontend;
   * integración;
   * documentación.
5. Revisa el diff después de cada incremento.
6. Ejecuta las pruebas relevantes.
7. Corrige regresiones antes de continuar.
8. Ejecuta la validación completa.
9. Actualiza `ESTADO_PROYECTO.md` solamente con trabajo implementado y comprobado.
10. No hagas commit ni push.

## Restricciones

* No implementes una propuesta inviable.
* No inventes el alcance.
* No ejecutes migraciones destructivas.
* No corrijas datos ambiguos silenciosamente.
* No elimines compatibilidad sin transición.
* No dependas solamente del frontend o Pydantic para reglas críticas.
* Protege reglas críticas en PostgreSQL.
* Mantén transacciones atómicas.
* Considera concurrencia.
* Mantén autorización territorial.
* Usa el contexto de auditoría.
* No uses `float` para dinero.
* No realices `DELETE` físico.
* No reveles secretos.
* No desactives pruebas o restricciones.
* No declares validaciones no ejecutadas.
* No amplíes el alcance.
* No amplíes el alcance por exhaustividad jurídica.
* No conviertas legislación o flujograma en generadores automáticos del modelo.
* Prefiere resolver mediante modelo existente, catálogo, backend o reporting antes de proponer nueva estructura.

## Formato de salida

### Antes de implementar

1. Trabajo vigente.
2. Resumen de la propuesta.
3. Hallazgos.
4. Matriz de evaluación.

| Área | Resultado | Evidencia | Ajuste requerido |

5. Resultado de gates.
6. Propuesta corregida.
7. Decisión de viabilidad.
8. Plan final.

### Después de implementar

9. Cambios realizados.

| Archivo | Cambio | Justificación |

10. Migraciones y compatibilidad.
11. Validaciones.

| Validación | Comando | Resultado | Estado |

12. Riesgos restantes.
13. Actualización de `ESTADO_PROYECTO.md`.
14. Estado final.

Estados finales permitidos:

* Propuesta no viable.
* Propuesta bloqueada por decisión funcional.
* Validación bloqueada por falta de entorno.
* Propuesta viable, implementación no iniciada.
* Implementación parcial.
* Implementación completa pendiente de validación.
* Implementación completa y validada.

---
