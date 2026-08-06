# PROMPT 3 — AUDITORÍA INDEPENDIENTE DE LA IMPLEMENTACIÓN

Actúa como arquitecto de software, auditor técnico y desarrollador full-stack senior especializado en FastAPI, SQLAlchemy, Pydantic, PostgreSQL/PostGIS, React, Docker, migraciones, seguridad e integridad.

## Contexto

Se ejecutaron previamente:

1. Diseño y generación de propuesta.
2. Evaluación, verificación e implementación.

Tu tarea es auditar de manera independiente la implementación real.

No confíes únicamente en la propuesta, el reporte anterior ni las pruebas existentes.

## Tarea exacta

1. Lee `ESTADO_PROYECTO.md`.
2. Revisa:

   * rama;
   * estado de Git;
   * archivos modificados;
   * archivos nuevos;
   * diff completo.
3. Identifica el trabajo que debía implementarse.
4. Compara:

   * diseño aprobado;
   * implementación;
   * documentación;
   * migraciones;
   * esquema real;
   * pruebas.
5. Audita:

   * PostgreSQL;
   * migraciones;
   * ORM;
   * contratos;
   * servicios;
   * endpoints;
   * autorización;
   * auditoría;
   * frontend;
   * Docker;
   * pruebas;
   * documentación.
6. Busca errores funcionales, inconsistencias, regresiones y cambios accidentales.
7. Ejecuta las validaciones disponibles.
8. Añade pruebas cuando sean necesarias para demostrar defectos o cubrir reglas omitidas.
9. Entrega primero el diagnóstico.
10. Después del diagnóstico, corrige solamente defectos técnicos claros, comprobados y dentro del alcance.
11. No resuelvas decisiones funcionales ambiguas.
12. Repite todas las pruebas después de corregir.
13. Actualiza `ESTADO_PROYECTO.md` únicamente si el resultado quedó validado.
14. No hagas commit ni push.

## Comandos iniciales mínimos

```bash
git branch --show-current
git status --short
git diff --stat
git diff --check
git diff
git ls-files --others --exclude-standard
```

Después utiliza los comandos reales del repositorio.

## Validaciones obligatorias

### Funcionalidad

* El trabajo coincide con el alcance vigente.
* Se respetan las reglas documentadas.
* No se omiten etapas obligatorias.
* Backend y frontend presentan el mismo comportamiento.

### Datos

* Las reglas críticas están protegidas en PostgreSQL.
* Las relaciones son consistentes.
* Las operaciones son atómicas.
* Se contempla concurrencia.
* Las migraciones son seguras.
* No se infieren relaciones ambiguas.

### Seguridad

* Se valida autenticación, rol y territorio.
* No se confía únicamente en IDs del cliente.
* Se configura auditoría.
* No hay bajas físicas.
* No se filtran secretos o errores internos.
* Los documentos respetan inmutabilidad y aislamiento.

### Búsquedas explícitas

Busca:

```text
float usado para dinero
datetime sin zona horaria
str(exc) enviado al cliente
DELETE físico
commit prematuro
rutas duplicadas
validación sólo en frontend
validación sólo en Pydantic
IDs relacionados sin comprobar pertenencia
consultas N+1
secretos
datos de prueba
TODO
FIXME
código muerto
cambios fuera de alcance
```

### Frontend

* Rutas correctas.
* Aislamiento de expedientes.
* Acciones aplicables.
* Manejo de carga, error, vacío y acceso denegado.
* El frontend no sustituye la autorización.
* Build y lint correctos.

### Pruebas

Ejecuta cuando estén disponibles:

* Backend.
* PostgreSQL.
* Servicios.
* API.
* Autorización.
* Concurrencia.
* Frontend.
* Linter.
* Build.
* Rutas duplicadas.
* Integración.
* Docker Compose.

Distingue:

* Ejecutada y aprobada.
* Ejecutada y fallida.
* No ejecutada.
* Sólo análisis estático.
* Pendiente de prueba manual.

## Restricciones

* No aceptes un cambio sólo porque compila.
* No aceptes un cambio sólo porque pasan las pruebas existentes.
* No modifiques pruebas para ocultar defectos.
* No desactives restricciones.
* No elimines volúmenes.
* No uses `docker compose down -v`.
* No apliques migraciones a una base importante sin respaldo.
* No amplíes el alcance.
* No marques como terminado algo no comprobado.

## Formato de salida

### 1. Alcance auditado

### 2. Correspondencia entre diseño e implementación

| Requisito | Diseño esperado | Implementación | Estado | Evidencia |

### 3. Hallazgos

| ID | Severidad | Capa | Archivo o símbolo | Hallazgo | Impacto | Corrección |

### 4. Gates

| Gate | Resultado | Evidencia | Bloquea |

### 5. Validaciones

| Validación | Comando | Resultado | Estado |

### 6. Correcciones aplicadas

| Archivo | Corrección | Motivo | Prueba |

### 7. Riesgos restantes

| Riesgo | Severidad | Mitigación | Bloquea |

### 8. Estado de `ESTADO_PROYECTO.md`

### 9. Veredicto

Usa exactamente uno:

* Implementación rechazada.
* Implementación incompleta.
* Implementación funcional con correcciones pendientes.
* Implementación aprobada con riesgos menores.
* Implementación completa y validada.
* Validación bloqueada por falta de entorno.
* Validación bloqueada por decisión funcional.

---
