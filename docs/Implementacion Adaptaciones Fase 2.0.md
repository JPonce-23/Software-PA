# Implementación — Adaptaciones Fase 2.0

**Fecha:** 28 de julio de 2026  
**Estado:** Cortes A, B y C construidos; 004 aplicada a la base activa limpia.

> **Ubicación en el plan maestro:** esta implementación fue una adaptación
> adicional realizada entre el Corte principal 1 y el Corte principal 2. Los
> nombres Corte A, B y C de este documento no equivalen a los cortes numerados
> del proyecto. El plan maestro y el punto de continuación se encuentran en
> `ESTADO_PROYECTO.md`.

## 1. Fuente ejecutable de la migración

La única fuente ejecutable del Corte A es:

`backend/db/migrations/004_adaptaciones_fase2.sql`

El SQL no se duplica dentro de este documento para impedir divergencias entre
la documentación y el archivo que realmente se ejecuta.

La migración implementa:

- Control de versión mediante `schema_migrations`.
- Bloqueo transaccional para impedir ejecuciones concurrentes.
- Prerrequisito explícito de la migración 003.
- Usuario técnico resuelto desde los usuarios activos.
- Triggers de auditoría con la PK correcta.
- Migración conservadora de nombres sin fusionar homónimos.
- Verificaciones de paridad antes del `COMMIT`.
- Rechazo explícito de una segunda ejecución.

## 2. Resultado del modelo

### 2.1 Identidad y calidad agraria

`persona` contiene únicamente atributos de identidad y contacto.

`persona_nucleo` contiene la relación con el núcleo y la calidad agraria. Esto
evita asumir que una persona tiene la misma calidad en todos los núcleos.

`persona_fuente_legacy` conserva:

- Tabla de origen.
- PK del registro de origen.
- Campo de origen.
- Texto original.
- Texto normalizado para encontrar candidatos.
- Indicador de revisión.

Cada aparición heredada crea una identidad provisional distinta. Una futura
operación de conciliación podrá elegir la identidad canónica y reasignar sus
relaciones sin perder el origen.

#### Qué significa conciliar identidades

Conciliar no significa borrar nombres repetidos ni asumir que dos textos
iguales son la misma persona. Significa revisar los candidatos con evidencia
como CURP, RFC, núcleo, parcela, cargo, vigencia y documentos; después:

1. Elegir la persona canónica.
2. Completar sus datos de identidad.
3. Reasignar a ella los cargos ORV, titularidades y demás relaciones.
4. Marcar las identidades provisionales como inactivas, indicando el motivo.
5. Conservar `persona_fuente_legacy` para saber de qué celda o registro salió
   cada nombre.

La fusión puede automatizarse únicamente cuando existe un identificador fuerte
coincidente —por ejemplo, la misma CURP válida—. Las coincidencias solo por
nombre requieren revisión humana por el riesgo de homónimos.

### 2.2 ORV

`orv_integrante` incluye `id_nucleo`. Sus FK compuestas garantizan:

- Que el ORV pertenece al núcleo indicado.
- Que la persona tiene vínculo con ese mismo núcleo.

Un índice único parcial permite un solo integrante activo por cargo, pero no
impide conservar titulares históricos ni registrar una sustitución después de
la baja lógica.

### 2.3 Parcelas

`parcela_titular` sustituye el diseño de un único `id_titular`.

Soporta:

- Titular.
- Cotitular.
- Posesionario.
- Participación porcentual opcional.
- Vigencia temporal.
- Historial por baja lógica.

La función `fn_validar_parcela_individual()` fue actualizada para exigir al
menos un titular y una persona activos.

### 2.4 Minutas y acuerdos

Una `minuta` pertenece a un `tramo_nucleo` y puede relacionarse con una
`actividad_campo` del mismo expediente.

Un `acuerdo` pertenece a una minuta y exige exactamente uno de:

- Persona responsable.
- Usuario interno responsable.
- Responsable externo descrito.

Si el acuerdo está `cumplido`, debe tener `fecha_cumplimiento`.

### 2.5 Documentos

`documento_version` almacena una fila inmutable por carga:

- Número de versión.
- SHA-256.
- Tamaño.
- Nombre original.
- Ruta de almacenamiento.
- MIME detectado.
- Usuario y fecha de carga.

`documentacion_soporte.url_archivo` queda temporalmente como legado. No se
eliminará hasta migrar los archivos físicos existentes.

### 2.6 Pagos

`pago_indemnizacion` referencia solamente `tramite_fifonafe`.

El trigger `fn_validar_pago_indemnizacion()` exige que:

- El trámite exista y esté activo.
- Sea de tipo `indemnizacion`.
- Tenga convenio.
- El convenio esté activo.
- El convenio tenga `monto_100`.
- Los COP originales y las ampliaciones tengan `monto_bdt`, aunque su valor
  capturado pueda ser cero.
- La suma de pagos activos no exceda el paquete económico autorizado.

La regla financiera es:

```text
valor de la tierra       = monto_100
bienes distintos tierra = monto_bdt
límite pagable           = monto_100 + monto_bdt
```

`monto_90` representa un anticipo o etapa de pago incluida en `monto_100`; por
lo tanto no se suma nuevamente. En obras complementarias, donde BDT no aplica,
el límite es solamente `monto_100`.

Se permite un solo pago `total` activo por trámite. Los pagos `anticipo`,
`parcial` y `total` se acumulan contra el mismo límite. También se impide
reducir los montos de un convenio por debajo de lo ya pagado o darlo de baja
mientras conserve pagos activos.

### 2.7 Alertas

El trigger cubre inserciones y cambios de vigencia del ORV.

La función:

```sql
fn_generar_alertas_orv_vencidos(p_id_usuario INTEGER)
```

cubre el paso del tiempo y debe ejecutarse diariamente. No se instala
`pg_cron` automáticamente porque la infraestructura actual no declara esa
extensión.

Ejemplo de ejecución programada:

```sql
BEGIN;
SELECT fn_generar_alertas_orv_vencidos(1);
COMMIT;
```

El identificador debe pertenecer a un usuario técnico activo configurado por
el entorno; no debe quedar fijo en el código de producción.

## 3. Contratos del backend

Los nuevos endpoints deben conservar las convenciones actuales:

```python
current_user: models.Usuario = Depends(
    auth.RoleChecker(["admin", "operador"])
)
```

Los modelos y schemas se referencian con sus módulos:

```python
models.Persona
schemas.PersonaCreate
schemas.PersonaResponse
```

No debe utilizarse `require_roles`, ni clases sin prefijo, porque esas
convenciones no existen en el backend vigente.

### 3.1 Organización

`main.py` registrará routers, pero no contendrá toda la lógica nueva:

```python
# backend/app/main.py
from .routers import personas, minutas, documentos, pagos, alertas

app.include_router(personas.router, prefix="/api")
app.include_router(minutas.router, prefix="/api")
app.include_router(documentos.router, prefix="/api")
app.include_router(pagos.router, prefix="/api")
app.include_router(alertas.router, prefix="/api")
```

Cada router delegará operaciones compuestas a un servicio. Los servicios son
responsables de validar entidades activas, iniciar la auditoría y confirmar una
sola transacción.

### 3.2 Schemas

Los catálogos deben utilizar `Literal` y el dinero `Decimal`:

```python
class PagoIndemnizacionCreate(AuditableCreate):
    id_tramite_fifonafe: int
    monto_pagado: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    fecha_pago: date
    tipo_pago: Literal["anticipo", "parcial", "total"]
    medio_pago: Optional[
        Literal["transferencia", "cheque", "deposito", "otro"]
    ] = None
    id_persona_beneficiaria: Optional[int] = None
    beneficiario_externo: Optional[str] = None
```

Los campos calculados de documentos pertenecen únicamente a la respuesta:

```python
class DocumentoVersionResponse(BaseModel):
    id_documento_version: int
    id_documento: int
    numero_version: int
    hash_sha256: str
    tamano_bytes: int
    nombre_archivo_original: str
    tipo_mime: Optional[str]
    fecha_carga: datetime

    model_config = ConfigDict(from_attributes=True)
```

CURP, RFC y correo deben normalizar cadenas vacías a `None`. CURP y RFC se
guardan en mayúsculas.

### 3.3 Carga segura de documentos

La carga será `async`, limitada por tamaño y procesada por bloques:

```python
import hashlib

sha256 = hashlib.sha256()
total = 0

while chunk := await file.read(1024 * 1024):
    total += len(chunk)
    if total > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande")
    sha256.update(chunk)
    destination.write(chunk)
```

La secuencia correcta es:

1. Validar documento, extensión y MIME real.
2. Reservar el siguiente número de versión con bloqueo de fila.
3. Escribir a un archivo temporal.
4. Calcular hash y tamaño durante la escritura.
5. Mover atómicamente a una ruta que incluya documento y versión.
6. Insertar `documento_version`.
7. Confirmar la transacción.
8. Eliminar el temporal si ocurre un error.

Nunca se reutiliza `doc_{id}.{ext}` ni se aceptan hash/tamaño desde el cliente.

### 3.4 Alertas no vistas

El endpoint del indicador debe devolver un conteo calculado con
`alertas_vistas`:

```text
GET /api/alertas/no-vistas/count
```

No debe contar todas las alertas activas. Marcar una alerta como vista mantiene
la alerta global y crea o reactiva la relación de lectura del usuario.

## 4. Transición de columnas heredadas

Después de aplicar 004 y antes de reanudar escrituras:

1. Desplegar el backend que escribe en las tablas normalizadas.
2. Mantener los campos de texto únicamente en respuestas de compatibilidad.
3. Actualizar ORV y afectación individual en el frontend.
4. Ejecutar el reporte de conciliación.
5. Resolver personas duplicadas con revisión humana.
6. Verificar que no haya consumidores de las columnas antiguas.

No se deben mantener indefinidamente dos campos editables para el mismo dato.

## 5. Pruebas del Corte A

La migración fue ejecutada sobre una copia de la base activa con este
resultado:

```text
personas migradas:        22
fuentes legacy:           22
integrantes ORV:          12
titulares de parcela:     10
migración registrada:      1
```

Las 22 personas se conservan separadas intencionalmente; existen nombres
repetidos que requieren conciliación, pero no es seguro fusionarlos
automáticamente.

También se verificó:

- Paridad completa de ORV y parcelas.
- Cero titulares activos sin persona activa.
- Cero alertas ORV activas duplicadas.
- Rechazo de pago asociado a un trámite incorrecto.
- Rechazo de pagos acumulados superiores a `monto_100 + monto_bdt`.
- Protección contra reducción del convenio por debajo de lo pagado.
- Rechazo de hash inválido.
- Rechazo de acuerdo cumplido sin fecha.
- Rollback de las pruebas negativas.
- Rechazo explícito de una segunda ejecución de 004.

## 6. Aplicación controlada

La aplicación controlada se realizó el 28 de julio de 2026. Se creó una base
limpia y se conservaron únicamente:

- El usuario administrador.
- 32 entidades federativas.
- 2,478 municipios.
- El proyecto Tren Maya.
- Siete tramos del Tren Maya con geometría.
- La asignación del administrador a los siete tramos.

La base anterior quedó preservada temporalmente como
`db_trenes_pre_reinicio_20260728`.

Para futuras instalaciones o despliegues se mantiene el siguiente
procedimiento:

Antes de aplicar en la base activa:

1. Crear respaldo verificable.
2. Detener temporalmente escrituras del backend.
3. Ejecutar:

   ```bash
   psql -v ON_ERROR_STOP=1 \
     -d <base> \
     -f backend/db/migrations/004_adaptaciones_fase2.sql
   ```

4. Confirmar que `schema_migrations` contiene `004`.
5. Ejecutar consultas de paridad.
6. Desplegar el backend compatible.
7. Habilitar escrituras.
8. Configurar la tarea diaria de alertas.

No ejecutar 004 desde una interfaz que ignore errores o continúe después de
una sentencia fallida. `ON_ERROR_STOP=1` es obligatorio.

## 7. Resultado del Corte B

El backend del Corte B se implementó con routers y servicios por dominio:

```text
backend/app/routers/
├── personas.py
├── minutas.py
├── documentos.py
├── pagos.py
└── alertas.py

backend/app/services/
├── common.py
├── personas.py
├── minutas.py
├── documentos.py
└── pagos.py
```

`main.py` conserva el ensamblaje de la aplicación y los módulos heredados que
aún no forman parte de este corte. Se retiraron de él las rutas duplicadas de
ORV, parcelas, archivos, bajas documentales y lectura de alertas.

La transición con el frontend actual funciona así:

- Los endpoints nuevos de personas, integrantes y titulares escriben en las
  tablas normalizadas.
- Los formularios heredados de ORV y parcela mantienen temporalmente una doble
  escritura atómica para no interrumpir la operación.
- `documentacion_soporte.url_archivo` ya no se acepta en escrituras de API; las
  cargas crean versiones inmutables.
- Las bajas que romperían relaciones activas se rechazan con `409`.
- Los conflictos de CURP, cargo y referencia bancaria se traducen a `409`.

La carga documental valida extensión, MIME y firma, limita tamaño, calcula
SHA-256 por bloques, usa movimiento atómico y bloquea el documento para
reservar versiones concurrentes. Los pagos usan `Decimal` en la API y conservan
en PostgreSQL la validación definitiva del límite
`monto_100 + monto_bdt`.

La regresión se ejecutó sobre
`db_trenes_codex_test_20260728`, una copia temporal exacta de la base activa:

```text
87 pruebas aprobadas
0 rutas duplicadas
0 columnas ORM faltantes en la base
```

La copia temporal fue eliminada después de las pruebas. La base activa conservó
un usuario, un proyecto, siete tramos y cero registros operativos de prueba.

## 8. Resultado del Corte C

El expediente incorpora módulos cargados bajo demanda para:

- Buscar o registrar personas y crear parcelas con titularidad normalizada.
- Registrar ORV con uno a seis integrantes y cargos no repetidos.
- Crear minutas, acuerdos y marcar compromisos cumplidos.
- Consultar trámites de indemnización y registrar pagos.
- Crear documentos, cargar versiones y descargar evidencia autenticada.
- Consultar y marcar alertas no vistas desde la barra superior.

Se agregaron operaciones compuestas para evitar que la UI deje relaciones
parciales:

```text
POST /api/parcelas/con-titular
POST /api/orvs/con-integrantes
```

La validación del frontend terminó con cero advertencias de `oxlint`. El build
de producción quedó dividido por ruta y por módulo; ningún chunk supera
500 kB.

Esos resultados son validaciones técnicas y no sustituyen una prueba funcional
de todos los recorridos. Durante la actualización documental posterior se
detectó que `DocumentosPanel.jsx` envía
`entidad_relacionada_tipo = 'tramo_nucleo'`, mientras que
`documentacion_soporte` sólo admite `nucleo_agrario`, `afectacion`, `convenio`
u `orv`. La creación desde ese panel debe considerarse pendiente y corregirse
en el Corte principal 2 para usar la afectación abierta.

La ejecución diaria de alertas se implementó como servicio independiente:

```text
backend/app/jobs/alertas_scheduler.py
docker compose: alertas_scheduler
```

El servicio reutiliza la imagen del backend, ejecuta una vez al iniciar y luego
cada 86,400 segundos. El 28 de julio de 2026 quedó activo y su primer ciclo
terminó correctamente con cero alertas por generar.

## 9. Trabajo aún pendiente

Los siguientes cortes y tareas permanecen pendientes:

- Validación funcional y de experiencia de usuario con usuarios finales.
- Conciliación de identidades migradas únicamente cuando existan datos
  heredados reales que lo requieran.
- Evaluación de `persona_fuente_legacy`: es trazabilidad de transición, no una
  tercera tabla maestra de identidad. Puede retirarse en una base limpia si
  ningún proceso de importación necesita ese linaje.
- Migración de contracción de columnas heredadas, después del Corte principal
  2. No asumir que seguirá siendo la versión 005.
- Corrección y prueba integral del panel documental para relacionarlo con
  `afectacion`, no con el tipo inválido `tramo_nucleo`.
- Consolidación posterior de `001_init_schema.sql`.

## 10. Continuidad con el plan maestro

### 10.1 Trabajo ya terminado

```text
Corte principal 1
└── Proyecto + Tramo + retiro de Frente + usuario_tramo

Adaptaciones 2.0
├── Corte A: migración 004
├── Corte B: backend modular
└── Corte C: frontend
```

Commits de referencia:

```text
d80983a feat: agregar tabla proyecto y eliminar tabla frente
05919de feat: preparar adaptaciones estructurales fase 2
f6f7073 feat(backend): implementar adaptaciones fase 2
e65010d feat(frontend): integrar flujo operativo fase 2
```

### 10.2 Próximo trabajo: Corte principal 2

La decisión funcional posterior a esta adaptación es convertir
`afectacion` en la identidad del expediente operativo, manteniendo
`tramo_nucleo` como agrupador territorial.

Situación implementada actualmente:

```text
/expedientes
└── lista registros tramo_nucleo

/expedientes/:id_tramo_nucleo
├── afectaciones colectivas
├── afectaciones individuales
├── asambleas
├── ORV
├── minutas
├── pagos
└── documentos
```

Arquitectura objetivo:

```text
/expedientes
└── lista afectaciones

/expedientes/:id_afectacion
├── identidad colectiva o individual
├── acercamiento y sensibilización
├── caminamiento
├── BDT
├── actividades y minutas
├── asamblea, cuando corresponda
├── convenio
├── FIFONAFE y pagos
├── documentos
└── cierre
```

La sensibilización no se elimina: es la actividad social previa al
caminamiento. El caminamiento delimita la superficie, confirma la geometría e
identifica los bienes distintos a la tierra. `monto_bdt` conserva el total
económico acordado; todavía no hay una tabla de inventario detallado por bien.

El Corte principal 2 debe empezar con una auditoría, no con una migración:

1. Localizar modelos, schemas, endpoints y componentes que usan
   `id_tramo_nucleo`.
2. Determinar cuáles registros pertenecen a una afectación concreta.
3. Mantener como compartidos los catálogos, personas, núcleo y ORV.
4. Definir backfill sólo donde la relación sea inequívoca.
5. Proponer una migración expansiva antes de retirar columnas o rutas.
6. Agregar un endpoint agregado por `id_afectacion`.
7. Cambiar navegación y filtros del frontend.
8. Probar que dos afectaciones del mismo cruce no compartan accidentalmente
   minutas, pagos, documentos o estados.
9. Corregir `DocumentosPanel.jsx` para enviar
   `entidad_relacionada_tipo = 'afectacion'` y el `id_afectacion` abierto.

Si el Corte principal 2 requiere cambios de esquema, la recomendación es usar
la versión 005 para expansión y posponer la contracción de Adaptaciones 2.0 a
006. Esta numeración debe confirmarse al aprobar el diseño.

### 10.3 Cortes principales posteriores

```text
Corte 3 — Seguridad inmediata
  Hecho: handler global sin fuga y escape XSS del mapa.
  Pendiente: .env, retirar secretos literales y rotarlos.

Corte 4 — Autenticación formal
  Pendiente: abandonar localStorage, sesiones, revocación, intentos fallidos
  e inactividad.

Corte 5 — Importación y reportes
  Pendiente: endurecer GeoJSON y producir dashboard/reportes por proyecto y
  afectación.
```

No deben repetirse el módulo Proyecto ni las Adaptaciones A–C. Para el estado
completo, reglas de migración y orden de lectura consultar
`ESTADO_PROYECTO.md`.
