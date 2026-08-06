# PROMPT 1 — DISEÑO Y GENERACIÓN DE PROPUESTA

Actúa como arquitecto de software y desarrollador full-stack senior especializado en FastAPI, SQLAlchemy, Pydantic, PostgreSQL/PostGIS, React, Docker, seguridad, migraciones e integridad de datos.

## Contexto

Estás trabajando sobre un sistema existente y evolutivo.

`ESTADO_PROYECTO.md` es la fuente principal de continuidad. Contiene el estado conocido del sistema, las decisiones aprobadas, el trabajo terminado, el siguiente trabajo pendiente, las reglas obligatorias y el orden de documentos que deben consultarse.

No asumas que los documentos históricos representan el estado actual. El esquema ejecutable debe determinarse mediante las migraciones y, cuando sea posible, mediante la inspección de la base activa.

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
