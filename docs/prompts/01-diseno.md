# PROMPT 1 — DISEÑO Y GENERACIÓN DE PROPUESTA

Actúa como arquitecto de software y desarrollador full-stack senior especializado en FastAPI, SQLAlchemy, Pydantic, PostgreSQL/PostGIS, React, Docker, seguridad, migraciones e integridad de datos.

## Contexto

Estás trabajando sobre un sistema existente y evolutivo.

`ESTADO_PROYECTO.md` es fuente de continuidad histórica y técnica. Contiene el estado conocido del sistema, decisiones registradas, trabajo terminado, trabajo pendiente y orden de documentos que deben consultarse. No define el alcance funcional vigente cuando contradiga `docs/ALCANCE_FUNCIONAL_EXCEL.md`, `docs/Descripción proceso.md` o `docs/requirements.md`.

No asumas que los documentos históricos representan el estado actual. El esquema ejecutable debe determinarse mediante las migraciones y, cuando sea posible, mediante la inspección de la base activa.

## Contrato funcional obligatorio

Antes de diseñar, lee completamente `docs/ALCANCE_FUNCIONAL_EXCEL.md`.

Regla invariable: “SOFTWARE-PA debe demostrar correspondencia con el modelo operativo Excel, no correspondencia exhaustiva con el Derecho Agrario mexicano.”

Toda ampliación funcional propuesta requiere evidencia previa. Para cualquier nueva tabla, entidad, proceso, estado o pantalla, identifica:

* archivo Excel;
* hoja;
* columna, registro, fórmula o comportamiento;
* necesidad de captura, historial o reporting que lo justifica.

Si no existe evidencia Excel ni decisión funcional aprobada, clasifica la propuesta como:

```text
FUERA_DE_ALCANCE
```

## Tarea exacta

1. Lee completamente `ESTADO_PROYECTO.md`.
2. Identifica el siguiente trabajo vigente allí documentado.
3. Recupera el contexto funcional y técnico siguiendo el orden documental indicado.
4. Audita las partes del repositorio relacionadas:

   * base de datos;
   * migraciones;
   * modelos ORM;
   * contratos;
   * servicios;
   * endpoints;
   * autorización;
   * frontend;
   * pruebas.
5. Distingue:

   * implementado;
   * parcial;
   * pendiente;
   * histórico;
   * contradictorio;
   * no verificable.
6. Genera una propuesta técnica incremental, mantenible y compatible con el sistema actual.
7. Define:

   * reglas funcionales;
   * estados y transiciones;
   * cambios por capa;
   * estrategia de migración;
   * compatibilidad con datos existentes;
   * seguridad;
   * autorización;
   * auditoría;
   * pruebas;
   * riesgos;
   * criterios de aceptación.
8. Indica qué secciones de `ESTADO_PROYECTO.md` deberán actualizarse después de una implementación validada.
9. Detente antes de modificar código, archivos, migraciones o base de datos.

## Restricciones

* No inventes el alcance.
* No amplíes el alcance por exhaustividad jurídica.
* No conviertas legislación o flujograma en generadores automáticos del modelo.
* Prefiere resolver mediante modelo existente, catálogo, backend o reporting antes de proponer nueva estructura.
* No reimplementes trabajo terminado.
* No conviertas decisiones históricas en vigentes.
* No elimines estructuras existentes sin una transición compatible.
* Prefiere migraciones expansivas y no destructivas.
* No infieras relaciones ambiguas.
* Protege reglas críticas también en PostgreSQL.
* Mantén operaciones compuestas en una sola transacción.
* Conserva autorización por rol y pertenencia territorial.
* Usa el mecanismo de auditoría existente.
* No uses `float` para dinero.
* No realices bajas físicas de entidades operativas.
* No expongas secretos ni errores internos.
* No modifiques todavía `ESTADO_PROYECTO.md`.
* No implementes nada: este prompt sigue siendo exclusivamente de diseño.

## Formato de salida

1. Trabajo vigente identificado.
2. Estado actual verificado.
3. Reglas funcionales confirmadas.
4. Hallazgos y contradicciones.
5. Diseño propuesto.
6. Cambios por capa.
7. Estrategia de migración y compatibilidad.
8. Seguridad, autorización e integridad.
9. Plan incremental.
10. Matriz de pruebas.
11. Riesgos y mitigaciones.
12. Criterios de aceptación.
13. Actualizaciones previstas para `ESTADO_PROYECTO.md`.
14. Decisiones pendientes.

Finaliza con uno de estos estados:

* Propuesta viable y lista para evaluación.
* Propuesta bloqueada por decisión funcional.
* Propuesta bloqueada por contradicción.
* Análisis bloqueado por falta de entorno.

No implementes nada.

---
