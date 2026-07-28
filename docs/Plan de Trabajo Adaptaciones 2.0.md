# Plan de Trabajo Técnico — Adaptaciones Fase 2.0

## Objetivo

Incorporar cinco capacidades al sistema sin perder información ni romper la
operación existente:

1. Identidad normalizada de sujetos agrarios y titulares.
2. Minutas y seguimiento de acuerdos.
3. Versiones documentales verificables mediante SHA-256.
4. Pagos de indemnización vinculados de forma íntegra al trámite FIFONAFE.
5. Alertas automáticas por vencimiento de ORV.

La jerarquía territorial vigente no cambia:

**Proyecto → Tramo → Tramo_Núcleo → Afectación → flujo colectivo o individual**

La migración multiproyecto y el retiro de Frente pertenecen a la migración
003 y son prerrequisito de esta fase.

## Principios de implementación

- **Expandir, migrar, verificar y retirar:** las columnas heredadas no se
  eliminan hasta que backend y frontend utilicen exclusivamente el modelo
  nuevo.
- **Una sola fuente de verdad después del corte:** durante la transición se
  preservan los textos heredados únicamente para lectura y conciliación.
- **No deduplicar personas por nombre:** las coincidencias sin CURP se marcan
  para revisión manual porque pueden ser homónimos.
- **Integridad en la base de datos:** las reglas de linaje se protegen con FK,
  restricciones, índices parciales y triggers; no dependen solamente de la UI.
- **Auditoría obligatoria:** toda tabla operativa nueva utiliza baja lógica,
  prohibición de DELETE y `fn_audit_log` indicando su PK.
- **Dinero con `NUMERIC`/`Decimal`:** nunca se representa con `float`.
- **Versiones documentales inmutables:** una nueva carga crea una fila y una
  ruta nuevas; nunca sobrescribe la evidencia previa.
- **Migraciones repetibles en entornos, no reejecutables en una base:** cada
  versión se registra en `schema_migrations` y debe aplicarse una sola vez.

## Modelo de datos aprobado

### Personas y propiedad social

```text
persona
├── persona_nucleo ──> nucleo_agrario
├── orv_integrante ──> orv
└── parcela_titular ──> parcela
```

- `persona` almacena identidad y contacto.
- `persona_nucleo` almacena la calidad agraria contextual y temporal.
- `orv_integrante` asigna cargos dentro de un ORV.
- `parcela_titular` soporta uno o varios titulares y copropiedad.
- `persona_fuente_legacy` conserva el origen exacto de cada texto migrado.

### Minutas y acuerdos

```text
tramo_nucleo
└── minuta
    └── acuerdo
```

Una minuta puede vincularse opcionalmente a una actividad de campo del mismo
expediente. Cada acuerdo tiene exactamente un responsable: sujeto agrario,
usuario interno o responsable externo descrito.

### Documentación

```text
documentacion_soporte
└── documento_version
```

El hash, tamaño, nombre original, ruta, usuario y fecha pertenecen a la
versión. Esos campos son calculados por el servidor y nunca se aceptan desde
el cliente.

### Pagos

```text
tramite_fifonafe(tipo = indemnizacion, convenio obligatorio)
└── pago_indemnizacion
```

El pago guarda solamente `id_tramite_fifonafe`. El convenio y la afectación se
derivan del trámite, evitando dos FK que puedan contradecirse.

El límite económico se calcula así:

```text
límite pagable = monto_100 + monto_bdt
```

`monto_90` es un anticipo comprendido dentro de `monto_100`; no constituye un
tercer concepto y no se suma al límite. En obras complementarias `monto_bdt`
debe ser nulo, por lo que el límite corresponde solamente a `monto_100`.

### Alertas

Se reutilizan `alertas` y `alertas_vistas`.

- Un trigger sincroniza la alerta cuando un ORV se inserta o actualiza.
- Una tarea diaria invoca `fn_generar_alertas_orv_vencidos(id_usuario)` para
  detectar ORV que vencieron sin ser modificados.
- La interfaz muestra alertas no vistas por el usuario, no el total global.

## Cortes de trabajo

### Corte A — Expansión y migración de datos

Archivo ejecutable:
`backend/db/migrations/004_adaptaciones_fase2.sql`

Acciones:

1. Validar que 003 esté aplicada y tomar un bloqueo transaccional.
2. Resolver un usuario técnico activo para la auditoría.
3. Crear las tablas nuevas, restricciones, índices y triggers.
4. Migrar cada valor heredado con su referencia de origen.
5. Actualizar la validación de parcelas individuales.
6. Generar las alertas vencidas existentes.
7. Comparar conteos heredados contra relaciones migradas.
8. Registrar la versión 004 y confirmar la transacción.

Regla de despliegue: aplicar en una ventana sin escrituras hasta desplegar el
backend del Corte B. Si no se puede garantizar esa ventana, primero se deben
implementar mecanismos temporales de doble escritura.

### Corte B — Backend

1. Mapear `Persona`, `PersonaNucleo`, `PersonaFuenteLegacy`,
   `OrvIntegrante`, `ParcelaTitular`, `Minuta`, `Acuerdo`,
   `DocumentoVersion` y `PagoIndemnizacion`.
2. Separar rutas por dominio:

   ```text
   backend/app/routers/personas.py
   backend/app/routers/minutas.py
   backend/app/routers/documentos.py
   backend/app/routers/pagos.py
   backend/app/routers/alertas.py
   ```

3. Usar `models.*`, `schemas.*` y `auth.RoleChecker`, conforme al código
   vigente.
4. Hacer transaccionales las operaciones compuestas.
5. Normalizar cadenas vacías a `NULL` y CURP/RFC a mayúsculas.
6. Devolver conflictos de CURP/cargo/referencia como 409.
7. Calcular hash y tamaño por bloques al guardar archivos.
8. Crear nuevas versiones documentales sin sobrescribir archivos.
9. Proporcionar un endpoint de alertas no vistas para el usuario autenticado.
10. Mantener temporalmente los campos heredados solo para compatibilidad de
    lectura; las escrituras nuevas se realizan sobre el modelo normalizado.

### Corte C — Frontend

1. Crear un selector accesible de personas con búsqueda paginada.
2. Refactorizar ORV para administrar cargos normalizados.
3. Refactorizar la afectación individual para seleccionar parcela y titulares.
4. Incorporar pantallas de minuta y acuerdos.
5. Integrar registro y consulta de pagos desde el trámite de indemnización.
6. Mostrar historial de versiones documentales y verificación de hash.
7. Mostrar alertas no vistas y permitir marcarlas como leídas.
8. Extraer estilos reutilizables; evitar componentes monolíticos con lógica de
   API, modal y presentación en un solo archivo.

### Corte D — Contracción

Después de validar producción:

1. Confirmar que no existen lecturas/escrituras de los campos heredados.
2. Confirmar paridad y resolver candidatos duplicados.
3. Crear una migración 005 que elimine:
   - Las seis columnas de nombres en `orv`.
   - `parcela.nombre_titular`.
   - `documentacion_soporte.url_archivo`, después de migrar todos los archivos.
4. Consolidar el esquema final en `001_init_schema.sql` para instalaciones
   nuevas.

## Pruebas obligatorias

### Migración

- Aplicación sobre copia de la base activa.
- Segunda ejecución rechazada de forma explícita.
- Paridad ORV y titulares.
- Rollback completo ante cualquier error.
- Camino limpio `001 actualizado + seed`.
- Camino de actualización `001 anterior → 003 → 004`.

### Integridad

- No vincular una persona al ORV o parcela de otro núcleo.
- Permitir reemplazo de cargo tras baja lógica.
- Rechazar afectación individual sin titular activo.
- Rechazar minuta vinculada a una actividad de otro expediente.
- Rechazar acuerdo cumplido sin fecha de cumplimiento.
- Rechazar hash SHA-256 inválido o versión duplicada.
- Rechazar pago sobre trámite que no sea indemnización.
- Rechazar pagos cuya suma activa exceda `monto_100 + monto_bdt`.
- Rechazar que un convenio reduzca su límite por debajo de lo ya pagado.
- Rechazar segundo pago total activo y referencias bancarias duplicadas.

### API y frontend

- Autorización por rol.
- Operaciones compuestas atómicas.
- Búsquedas de personas paginadas.
- Concurrencia en CURP, cargos, versiones y pagos.
- Archivos grandes sin cargarlos completamente en memoria.
- Navegación por teclado y foco correcto en selectores y modales.

## Criterio de salida de la Fase 2.0

La fase se considera lista cuando:

- 004 fue validada sobre una copia real y aplicada en el entorno objetivo.
- Backend y frontend utilizan el modelo nuevo.
- Las pruebas de regresión e integridad pasan.
- Las alertas tienen ejecución diaria configurada.
- Existe respaldo previo y procedimiento de restauración probado.
- Las columnas heredadas están sin uso y listas para retirarse mediante 005.
