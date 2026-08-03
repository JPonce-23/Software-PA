Actúa como arquitecto de software y desarrollador full-stack senior especializado en FastAPI, SQLAlchemy, Pydantic, PostgreSQL/PostGIS, React, Docker, seguridad, migraciones y sistemas con reglas de negocio críticas.

## Contexto

Estás trabajando sobre un repositorio existente y evolutivo. El archivo `ESTADO_PROYECTO.md` es la fuente principal de continuidad: contiene el estado real conocido, las decisiones aprobadas, el trabajo terminado, el siguiente trabajo pendiente, las reglas obligatorias y el orden de documentos que deben consultarse.

Debes leerlo completo antes de analizar código. Después, revisa las fuentes funcionales, migraciones, modelos, servicios, endpoints, frontend y pruebas que resulten relevantes para el trabajo vigente allí documentado.

No asumas que los documentos históricos representan el estado actual. El esquema ejecutable se determina por las migraciones aplicadas y, cuando sea posible, por la inspección de la base activa.

## Tarea exacta

1. Lee `ESTADO_PROYECTO.md` y determina cuál es el siguiente trabajo vigente.
2. Recupera el contexto funcional y técnico siguiendo el orden documental indicado en ese archivo.
3. Audita la implementación actual relacionada con ese trabajo:

   * modelo de datos;
   * migraciones;
   * ORM;
   * contratos;
   * servicios;
   * endpoints;
   * autorización;
   * frontend;
   * pruebas.
4. Identifica reglas ya implementadas, pendientes, contradictorias o no verificables.
5. Diseña una propuesta técnica completa, incremental y compatible con el sistema actual.
6. Define:

   * comportamiento esperado;
   * reglas de negocio;
   * estados y transiciones;
   * cambios por capa;
   * estrategia de migración;
   * compatibilidad con datos existentes;
   * seguridad y autorización;
   * auditoría;
   * pruebas;
   * riesgos;
   * criterios de aceptación;
   * actualización futura de `ESTADO_PROYECTO.md`.
7. Detente antes de editar código, ejecutar migraciones o modificar la base.

## Restricciones

* No inventes el alcance: obténlo de `ESTADO_PROYECTO.md`.
* No reimplementes trabajo ya terminado.
* No conviertas propuestas históricas en decisiones vigentes.
* No elimines estructuras existentes sin una transición compatible.
* Prefiere migraciones expansivas y no destructivas.
* No infieras relaciones ambiguas entre datos.
* Protege la integridad también en PostgreSQL.
* Mantén operaciones compuestas en una sola transacción.
* Conserva autorización por rol y pertenencia territorial.
* Toda escritura auditable debe usar el mecanismo de auditoría existente.
* No uses `float` para dinero.
* No realices bajas físicas de entidades operativas.
* No expongas errores internos ni secretos.
* No hagas cambios fuera del alcance vigente.
* No modifiques todavía `ESTADO_PROYECTO.md`; sólo indica qué secciones deberán actualizarse después de una implementación validada.

## Formato de salida

Guarda la propuesta en un archivo dentro de `docs/propuestas/` usando la nomenclatura de fecha: `YYYY-MM-DD-[feature]-propuesta.md`.
Nota: Las propuestas se conservan in situ como registro de trazabilidad; no deben moverse a `docs/historico/`.

Entrega la propuesta con esta estructura:

1. **Trabajo vigente identificado**
2. **Estado actual verificado**
3. **Reglas funcionales confirmadas**
4. **Hallazgos y contradicciones**
5. **Diseño propuesto**
6. **Cambios por capa**
7. **Migración y compatibilidad**
8. **Seguridad, autorización e integridad**
9. **Plan incremental de implementación**
10. **Matriz de pruebas**
11. **Riesgos y mitigaciones**
12. **Criterios de aceptación**
13. **Actualizaciones previstas para `ESTADO_PROYECTO.md`**
14. **Decisiones que requieren aprobación**

Para cada cambio propuesto indica archivo o componente, problema, solución, justificación, dependencias, riesgo y forma de validarlo.

No implementes nada en esta etapa.
