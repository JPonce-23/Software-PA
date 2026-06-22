Role: Senior Fullstack Developer & Systems Architect.

Context: Project development and validation based on @[Description.md], @[Estructura Datos.md], @[requirements.md], and @[design-mod.md]. The system must strictly align with @[Descripción proceso.md] as the primary source of truth.

Exact Task: Perform a comprehensive cross-audit between @[requirements.md] and @[design-mod.md] to verify that:

1. Requirements accurately describe the system behavior and logic.
2. The design correctly implements those requirements.
3. Both are fully aligned with @[Descripción proceso.md], @[Estructura Datos.md], and @[Description.md].

Objectives:

* Validate bidirectional traceability (requirements ↔ design).
* Detect mismatches, omissions, or inconsistencies.
* Ensure data structures align with @[Estructura Datos.md] and @[Descripción proceso.md].
* Confirm that no logic is implemented in design without being defined in requirements.
* Confirm that no requirement lacks representation in design.

Constraints:

* Do not write code or implement changes.
* Do not assume undefined behavior; explicitly flag gaps.
* @[Descripción proceso.md] is the ultimate source of truth and overrides all other documents.
* Focus on correctness, completeness, and implementation readiness.

Output Format:

* Section 1: Requirements → Design Traceability

  * For each requirement:

    * Is it implemented in @[design-mod.md]? (Yes/No/Partial)
    * Reference to design section
    * Observations

* Section 2: Design → Requirements Validation

  * For each major design component:

    * Is it backed by a requirement? (Yes/No)
    * If not, flag as overdesign or undocumented logic

* Section 3: Alignment with Sources of Truth

  * Deviations from @[Descripción proceso.md]
  * Inconsistencies with @[Estructura Datos.md]
  * Misalignment with @[Description.md]

* Section 4: Data Model Consistency

  * Validation of entities, relationships, and constraints
  * Conflicts between design and data structure definition

* Section 5: Gaps and Issues

  * Missing requirements
  * Missing design elements
  * Ambiguities or conflicting definitions

* Section 6: Implementation Readiness Assessment

  * Ready / Not Ready
  * Clear justification based on findings

* Section 7: Required Actions

  * Minimal set of changes needed to reach implementation readiness
  * Clearly categorized as:

    * Critical (blocking)
    * Non-critical (recommended)

-------------------------------------------------------------------------------------------------------------------------------------------


Role: Senior Fullstack Developer & Systems Architect.

Context: Project development and prior audit results based on the inconsistencies and required improvements have already been identified.

Exact Task: Apply the approved improvements to @[requirements.md] and @[design-mod.md], ensuring full alignment with @[Descripción proceso.md] as the single source of truth.

Constraints:
- Do not introduce new logic beyond the previously identified improvements.
- Preserve existing structure and naming conventions unless a change was explicitly required.
- Maintain consistency across all related sections and documents.
- Do not modify @[Descripción proceso.md].
- Ensure all changes are traceable to a previously identified inconsistency or improvement.

Output Format:
- Section 1: Summary of applied changes (grouped by document).
- Section 2: Detailed modifications (before vs after for each change).
- Section 3: Traceability mapping (each change linked to its original inconsistency or improvement).
- Section 4: Validation checklist confirming alignment with @[Descripción proceso.md].

-------------------------------------------------------------------------------------------------------------------------------------------
## Rol: Senior Software Architect, Backend/Data Architect y QA Auditor independiente, con experiencia avanzada en:

* Diseño de sistemas web multiusuario.
* PostgreSQL, PostGIS y modelado relacional.
* Auditoría de requisitos funcionales y no funcionales.
* Integridad referencial, reglas de negocio y trazabilidad.
* Sistemas gubernamentales o jurídicos con alta exigencia documental.
* Validación de documentación técnica antes de desarrollo.

Tu función no es ayudar a “hacer que parezca correcto”, sino actuar como **gatekeeper estricto de implementación**. Debes detectar contradicciones, reglas débiles, ambigüedades, huecos de diseño, riesgos de implementación y cualquier comportamiento no documentado.

---

## Contexto

Estoy desarrollando un sistema web de seguimiento para la **liberación de derechos de vía de un proyecto ferroviario que afecta propiedad social**, incluyendo ejidos, comunidades, derechos colectivos de uso común y derechos individuales parcelarios.

El sistema reemplazará matrices de Excel y deberá funcionar como dashboard/reporteador multiusuario, con captura operativa, control de roles, visualización geográfica, tableros de avance, auditoría y seguimiento de convenios, asambleas, RAN, ORV, padrón, FIFONAFE, indemnizaciones y documentación soporte.

La tecnología prevista incluye:

* Backend web con API REST.
* PostgreSQL + PostGIS.
* Modelo relacional normalizado.
* Geometrías de Tramos como MultiLineString.
* Geometrías de afectación como Polygon/MultiPolygon cuando aplique.
* Cálculos de avance por superficie liberada.
* Auditoría mediante triggers o mecanismo equivalente.
* Soft deletes en registros jurídicos/operativos.
* Dashboard con métricas por Tramo, Frente, Núcleo Agrario, tipo de afectación y estatus RAN.

Los documentos que debes auditar son:

* @Descripción proceso.md: fuente de verdad del proceso operativo y jurídico.
* @requirements.md: requisitos funcionales y no funcionales.
* @design-mod.md: diseño técnico, arquitectura, modelo de datos, reglas SQL, vistas y triggers.
* @Estructura Datos.md: estructura de matrices originales y campos requeridos.
* @Description.md: descripción general del sistema esperado.

Trata @Descripción proceso.md como la **fuente de verdad absoluta**. Si cualquier otro documento contradice ese proceso, debes marcarlo como problema.

---

## Tarea exacta

Audita todos los documentos para determinar si el sistema está **listo o no para iniciar desarrollo**.

Debes validar, como mínimo:

1. **Consistencia entre documentos**

   * Que @requirements.md refleje correctamente @Descripción proceso.md.
   * Que @design-mod.md implemente correctamente los requisitos.
   * Que @Estructura Datos.md esté completamente cubierta por requisitos y diseño.
   * Que no existan contradicciones entre proceso, requisitos, diseño y modelo de datos.

2. **Completitud de requisitos**

   * Identifica requisitos faltantes.
   * Detecta reglas de negocio ambiguas.
   * Verifica que los criterios de aceptación sean implementables y verificables.
   * Revisa si los requisitos distinguen correctamente derechos colectivos e individuales.

3. **Validación del diseño técnico**

   * Evalúa si la arquitectura propuesta es suficiente.
   * Revisa si el diseño introduce supuestos no documentados.
   * Detecta sobreingeniería o diseño insuficiente.
   * Verifica que los flujos de Asamblea, Convenio, RAN, FIFONAFE, ORV y Padrón estén correctamente modelados.

4. **Validación del modelo de datos**

   * Revisa llaves primarias, llaves foráneas, constraints, triggers y vistas.
   * Valida integridad referencial.
   * Verifica que existan reglas para:

     * afectaciones individuales con parcela válida;
     * convenios colectivos con Asamblea válida;
     * modificatorios colectivos con padre válido;
     * Padrón-Asamblea-Núcleo;
     * ORV vigente calculado;
     * geometrías de afectación;
     * soft deletes;
     * auditoría completa;
     * documentación soporte sin referencias huérfanas.
   * Detecta si alguna FK compuesta no funcionaría en PostgreSQL.

5. **Validación geoespacial**

   * Verifica si Tramos, Frentes, Núcleos y Afectaciones están modelados correctamente.
   * Revisa SRID, tipo geométrico, validación PostGIS, índices GiST y cálculo de superficies.
   * Evalúa si el sistema puede calcular correctamente superficie afectada, liberada y pendiente.
   * Revisa si el tratamiento de geometrías históricas migradas desde Excel es consistente con los requisitos.

6. **Validación de dashboards y reportes**

   * Verifica si las vistas calculan correctamente:

     * superficie total afectada;
     * superficie liberada;
     * superficie pendiente;
     * porcentaje de avance;
     * conteos de convenios formalizados;
     * desglose individual/colectivo;
     * estatus de digitalización espacial.
   * Revisa si el cálculo evita inflar superficies por modificatorios.

7. **Riesgos de implementación**

   * Identifica riesgos que puedan provocar reportes falsos, pérdida de trazabilidad, registros jurídicamente inválidos o inconsistencias de avance.
   * Clasifica cada riesgo como:

     * Bloqueante;
     * Alto;
     * Medio;
     * Bajo.

8. **Veredicto final**

   * Determina si el sistema está:

     * GO para desarrollo;
     * GO condicionado;
     * NO-GO.
   * El veredicto debe estar justificado con evidencia concreta de los documentos.

---

## Restricciones

* No generes código de implementación.
* No propongas soluciones vagas.
* No asumas comportamiento que no esté documentado.
* No suavices problemas críticos.
* No declares GO si existen contradicciones, reglas jurídicas ambiguas, cálculos de avance incompletos o integridad referencial débil.
* No trates `design-mod.md` como fuente de verdad si contradice `Descripción proceso.md`.
* No ignores requisitos no funcionales.
* No omitas problemas de migración desde Excel.
* No omitas riesgos relacionados con RAN, Asamblea, ORV, Padrón, FIFONAFE o superficies liberadas.
* Cada hallazgo debe incluir:

  * documento afectado;
  * explicación del problema;
  * severidad;
  * impacto;
  * corrección mínima requerida.

---

## Formato de salida

Entrega el análisis en español con esta estructura exacta:

### 1. Resumen Ejecutivo

* Calidad general de la documentación.
* Estado de preparación.
* Veredicto: GO, GO condicionado o NO-GO.
* Justificación breve.

### 2. Auditoría de Consistencia entre Documentos

Para cada hallazgo:

| ID | Severidad | Documentos afectados | Problema | Evidencia | Impacto | Corrección requerida |
| -- | --------- | -------------------- | -------- | --------- | ------- | -------------------- |

### 3. Validación de Requirements

Incluye:

* Requisitos completos.
* Requisitos ambiguos.
* Requisitos faltantes.
* Requisitos contradictorios.
* Requisitos no verificables.

### 4. Validación de Diseño Técnico

Incluye:

* Arquitectura.
* Reglas de negocio.
* Triggers.
* Vistas.
* Auditoría.
* Soft deletes.
* Seguridad.
* Migración.
* Riesgos de sobreingeniería o subdiseño.

### 5. Validación del Modelo de Datos

Incluye:

* Tablas.
* Relaciones.
* FKs.
* Constraints.
* Normalización.
* Integridad referencial.
* Campos faltantes.
* Validaciones condicionales.
* Posibles errores SQL/PostgreSQL/PostGIS.

### 6. Validación Geoespacial

Incluye:

* Tramos.
* Frentes.
* Núcleos Agrarios.
* Afectaciones.
* Geometrías históricas vs nuevas.
* SRID.
* Índices espaciales.
* Cálculo de áreas.
* Riesgo de superficies incorrectas.

### 7. Validación de Dashboards y Reportes

Incluye si el diseño permite calcular correctamente:

* Convenios individuales formalizados.
* Convenios colectivos formalizados.
* Superficie afectada.
* Superficie liberada.
* Superficie pendiente.
* Porcentaje de avance.
* Desglose individual/colectivo.
* Estatus de digitalización espacial.
* Avance por Tramo y Frente.

### 8. Riesgos de Implementación

Tabla obligatoria:

| Riesgo | Severidad | Causa | Consecuencia | Mitigación mínima |
| ------ | --------- | ----- | ------------ | ----------------- |

### 9. Issues Bloqueantes

Lista priorizada de todo lo que impide iniciar desarrollo.

Cada issue debe indicar:

* Qué documento debe corregirse.
* Qué regla debe agregarse, eliminarse o aclararse.
* Si bloquea desarrollo backend, base de datos, frontend, dashboard, migración o QA.

### 10. Veredicto Final

Debe incluir:

* GO, GO condicionado o NO-GO.
* Razón principal.
* Condiciones mínimas para avanzar.
* Nivel de confianza del veredicto: Alto / Medio / Bajo.

No cierres con frases genéricas. El resultado debe servir como decisión real de arranque o bloqueo de desarrollo.
