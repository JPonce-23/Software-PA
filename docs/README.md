# Índice de Documentación Canónica — SOFTWARE-PA

> **Árbol documental consolidado de SOFTWARE-PA.**  
> Este repositorio cuenta con una documentación pequeña, clara, verificable y estrictamente alineada con el código fuente y la base de datos real (esquema **015**).

---

## 1. Documentos Canónicos del Repositorio

El árbol de documentación técnica y funcional vigente se compone exclusivamente de los siguientes documentos en `docs/`:

1. **[MODELO_FUNCIONAL.md](MODELO_FUNCIONAL.md):**  
   **Documento canónico del modelo funcional.** Define el propósito del sistema, el alcance sobre propiedad social, el principio *Excel-first*, la estructura jerárquica (`Proyecto → ProyectoNucleo → Núcleo Agrario`), la bifurcación estricta entre derechos colectivos y derechos individuales, los procedimientos ante RAN y FIFONAFE, la cadena financiera de pagos, los eventos de seguimiento, las reglas geoespaciales y las decisiones funcionales pendientes.

2. **[FUENTES_Y_COBERTURA_EXCEL.md](FUENTES_Y_COBERTURA_EXCEL.md):**  
   **Matriz de cobertura funcional de columnas, bloques, relaciones, comportamientos y excepciones relevantes observadas en los Excel.** Documenta los cinco libros Excel auditados (clasificando los cuatro operativos y señalando `BD-PA_v2-geo(1).xlsx` / `BD-PA_v2-geo.xlsx` como referencia/prototipo de modelado sin autoridad operativa sobre liberación), define los tratamientos de ingeniería (`PERSISTIR`, `DERIVAR`, `REFERENCIA`, `DOCUMENTAR`, `REVISAR`, `NO IMPLEMENTAR`) y detalla la correspondencia funcional hacia el modelo de datos.

3. **[ARQUITECTURA.md](ARQUITECTURA.md):**  
   **Arquitectura técnica del sistema.** Describe lo que existe e interactúa hoy en el repositorio: stack tecnológico (FastAPI, PostgreSQL 15/PostGIS, React 19, Docker), separación backend/frontend vía REST HTTP JSON, autenticación por cookies seguras, protección CSRF, autorización por proyecto (`UsuarioProyecto`), auditoría append-only, subsistema documental, motor de eventos y arquitectura de reporting en dos capas.

4. **[DICCIONARIO_DATOS.md](DICCIONARIO_DATOS.md):**  
   **Diccionario de datos físico y lógico.** Especifica de forma exhaustiva las tablas de dominio, campos, tipos de datos PostgreSQL, nulabilidad, llaves foráneas, restricciones, catálogos operativos y vistas de reporting (read-models), verificado contra `backend/app/models.py` y las migraciones vigentes.

5. **[MIGRACIONES.md](MIGRACIONES.md):**  
   **Gestión del esquema de base de datos.** Detalla el historial inmutable de las migraciones `001` a `015`, sus hashes criptográficos SHA-256 verificados, el esquema activo (**015**), el procedimiento oficial de ejecución mediante `run_migrations.sh` y la política forward-only (siguiente migración: `016`).

6. **[API.md](API.md):**  
   **Contrato de integración backend/frontend.** Define la interacción cliente-servidor, endpoints de autenticación y sesiones, reglas no expresadas directamente en OpenAPI (catálogos dinámicos, semántica de hitos RAN, no aditividad de montos multidestino, precisión de 7 decimales), administración de usuarios y estados de salud del servicio.

7. **[openapi.json](openapi.json):**  
   **Contrato OpenAPI 3.1.0 formal.** Archivo exportado automáticamente desde FastAPI que describe la firma de todas las rutas, parámetros y esquemas JSON del backend vigente. *No debe editarse manualmente.*

---

## 2. Precedencia Documental y Jerarquía de Autoridad

En caso de divergencia conceptual o técnica entre artefactos, rige la siguiente jerarquía de precedencia:

```text
1. Archivos Excel operativos + docs/MODELO_FUNCIONAL.md
   └── Determinan el alcance funcional, datos a capturar y reglas de negocio.
       │
2. docs/FUENTES_Y_COBERTURA_EXCEL.md
   └── Demuestra la trazabilidad y tratamiento de cada dato de fuente.
       │
3. Código ejecutable backend + migraciones 001–015
   └── Define la realidad técnica en ejecución.
       │
4. docs/ARQUITECTURA.md + docs/DICCIONARIO_DATOS.md
   └── Documentan la implementación del sistema y la estructura de datos.
       │
5. docs/API.md + docs/openapi.json
   └── Gobiernan la integración y consumo entre interfaces.
```
