# Diseño del Subcorte 2A — Integridad de afectaciones

> Estado: implementado y aplicado el 2026-07-31 mediante la migración 005.
> Sus fuentes funcionales son `Flujo liberacion derechos.md`, `Descripción
> proceso.md` y el alcance aprobado en `ESTADO_PROYECTO.md`.

## Objetivo y límite

El Subcorte 2A elimina la ambigüedad entre derecho colectivo y derecho
parcelario, sin cambiar la secuencia de liberación.

```text
Afectación colectiva  = derecho del núcleo agrario
                         no usa parcela normalizada

Afectación individual = derecho parcelario confirmado
                         usa una parcela del mismo núcleo
                         la parcela puede ser individual o copropiedad
```

La afectación se sigue creando sólo después de sensibilización, caminamiento y
confirmación de superficie, geometría, situación jurídica y sujetos. No se
agregan etapas, entidades ni responsabilidades de otras instituciones.

Quedan fuera de 2A: la secuencia obligatoria de convenio, RAN, FIFONAFE y
pago; las salidas terminales; liberado; padrones nominales; firmantes;
participantes de asamblea; rutas de detalle por afectación y documentos. Son
trabajos de los Subcortes 2B y 2C.

## Propiedad de los datos

| Dato o actuación | Entidad dueña | Decisión del Subcorte 2A |
| --- | --- | --- |
| Investigación, sensibilización y caminamiento previos | `tramo_nucleo` | Se conservan como antecedentes compartidos del expediente maestro. |
| Derecho y superficie confirmados | `afectacion` | Abre el subexpediente y define ruta colectiva o individual. |
| Parcela y titulares | `parcela`, `parcela_titular` | Sólo respaldan una afectación individual. |
| ORV y padrón | `nucleo_agrario` | No se mueven ni duplican. |
| Asamblea | `tramo_nucleo` en el modelo actual | No se rediseña en 2A. |
| Convenio, RAN, FIFONAFE y pago | Entidades actuales ligadas a `afectacion` | Sin cambio funcional. |

```text
Proyecto → Tramo → Tramo_Núcleo (expediente maestro)
                         ├── afectación colectiva
                         └── afectación individual → parcela → titulares
```

## Invariantes de integridad

La API debe validar estas reglas para dar mensajes claros, pero PostgreSQL las
debe imponer también ante scripts, importaciones y concurrencia.

1. La relación entre tipo de afectación y parcela es exclusiva y bidireccional.

   ```sql
   CHECK (
       (tipo_afectacion = 'colectivo' AND id_parcela IS NULL)
       OR
       (tipo_afectacion = 'individual' AND id_parcela IS NOT NULL)
   )
   ```

2. La parcela individual pertenece al mismo núcleo que la afectación y su
   `tramo_nucleo`. Se conserva la FK compuesta existente; no se reemplaza por
   una validación exclusiva de aplicación.

3. Para crear o reactivar una afectación individual, la parcela debe estar
   activa, tener `no_parcela_ppt` no vacío y tener soporte o justificación
   registral. Con los campos existentes, hay soporte si existe certificado
   parcelario, folio de derechos, constancia de vigencia o documentación
   declarada disponible. Si no está disponible, `documentacion_faltante` debe
   explicar lo pendiente.

4. La parcela usada por una afectación individual activa debe tener al menos
   una relación activa en `parcela_titular`. Si es `copropiedad`, debe tener al
   menos dos. Los tipos de derecho vigentes (`titular`, `cotitular`,
   `posesionario` u `otro`) no cambian.

5. No puede inactivarse una parcela mientras tenga una afectación individual
   activa. Tampoco puede inactivarse una relación de titularidad si deja a una
   parcela referida por debajo del mínimo de uno o, para copropiedad, de dos.

6. `afectacion.no_parcela_solar` no identifica una parcela. La ruta individual
   no lo captura ni duplica `parcela.no_parcela_ppt`; queda temporalmente para
   las referencias textuales heredadas de matrices colectivas.

7. Tipo, núcleo, `tramo_nucleo` y parcela son identidad del subexpediente
   confirmado y no se editan. Una corrección de clasificación requiere baja
   lógica justificada y una nueva afectación, preservando trazabilidad de
   convenios y trámites.

## Migración expansiva propuesta

Se agregará `backend/db/migrations/005_subcorte_2a_integridad_afectaciones.sql`.
Será transaccional, registrará `005` en `schema_migrations` sólo al final y no
eliminará datos, columnas, tablas ni rutas.

Orden de la migración:

1. Confirmar las tablas y la migración 004; tomar un bloqueo asesor de
   migración y establecer el contexto de auditoría con un usuario activo.
2. Ejecutar prevalidaciones. Cualquier fila incompatible aborta la transacción.
3. Sustituir sólo `chk_individual_requiere_parcela` por
   `chk_afectacion_tipo_parcela`, con la regla bidireccional.
4. Crear funciones y triggers de protección.
5. Registrar `005` y confirmar.

La migración no reclasifica, completa, desactiva ni crea titulares de forma
silenciosa. Antes de modificar el esquema debe encontrar cero filas en estas
consultas, como mínimo:

```sql
-- Contradicciones de tipo y parcela.
SELECT id_afectacion
FROM afectacion
WHERE (tipo_afectacion = 'colectivo' AND id_parcela IS NOT NULL)
   OR (tipo_afectacion = 'individual' AND id_parcela IS NULL);

-- Parcelas activamente usadas que no cumplen la futura regla.
SELECT a.id_afectacion, p.id_parcela
FROM afectacion a
JOIN parcela p ON p.id_parcela = a.id_parcela
WHERE a.activo = TRUE
  AND a.tipo_afectacion = 'individual'
  AND (
      p.activo = FALSE
      OR NULLIF(BTRIM(p.no_parcela_ppt), '') IS NULL
      OR (COALESCE(p.documentacion_disponible, FALSE) = FALSE
          AND NULLIF(BTRIM(p.documentacion_faltante), '') IS NULL)
      OR NOT EXISTS (
          SELECT 1 FROM parcela_titular pt
          WHERE pt.id_parcela = p.id_parcela AND pt.activo = TRUE
      )
      OR (p.tipo_parcela = 'copropiedad' AND 2 > (
          SELECT COUNT(*) FROM parcela_titular pt
          WHERE pt.id_parcela = p.id_parcela AND pt.activo = TRUE
      ))
  );
```

La verificación de la base activa queda como prerrequisito: el contenedor local
detectado no usa las credenciales de `.env.example`, por lo que no se simuló ni
se asumió su estado real.

### Restricciones y triggers

Se mantienen las FKs compuestas de afectación, convenio y trámite FIFONAFE, y
los mecanismos existentes de auditoría y baja lógica. Como un `CHECK` no puede
consultar otras tablas, la migración incorpora una función privada única, por
ejemplo `fn_validar_parcela_para_afectacion(id_parcela)`, que:

1. toma `pg_advisory_xact_lock` por parcela;
2. bloquea y lee la parcela;
3. valida estado, PPT y soporte o justificación;
4. cuenta titulares activos;
5. exige el mínimo según `tipo_parcela`.

Los triggers reutilizan esa función, sin duplicar reglas:

| Tabla | Evento | Efecto |
| --- | --- | --- |
| `afectacion` | Antes de insertar o reactivar una individual | Valida su parcela. |
| `parcela` | Antes de inactivar | Impide baja con afectación individual activa. |
| `parcela` | Después de cambiar tipo o campos registrales | Revalida afectaciones individuales dependientes. |
| `parcela_titular` | Después de alta o cambio de actividad/parcela | Revalida la parcela anterior y la nueva. |

Todos los triggers de una parcela usan el mismo bloqueo asesor. Así, dos
transacciones concurrentes no pueden dejar una afectación individual activa con
menos titulares de los exigidos. No se crea un contador denormalizado: el
conteo proviene de `parcela_titular`, la fuente normalizada.

## Contratos de API y servicios

Se incorporan contratos Pydantic discriminados y rutas explícitas:

```text
POST /api/afectaciones/colectivas
POST /api/afectaciones/individuales
PUT  /api/afectaciones/colectivas/{id_afectacion}
PUT  /api/afectaciones/individuales/{id_afectacion}
```

`AfectacionColectivaCreate` no declara `id_parcela`; conserva los datos
colectivos confirmados, incluidos `destino_superficie` y, temporalmente, la
referencia textual `no_parcela_solar`.

`AfectacionIndividualCreate` no declara `no_parcela_solar` y recibe una de dos
referencias de parcela:

```json
{ "modo": "existente", "id_parcela": 42 }
```

```json
{
  "modo": "nueva",
  "tipo_parcela": "copropiedad",
  "no_parcela_ppt": "PPT-42",
  "certificado_parcelario": "...",
  "documentacion_disponible": true,
  "titulares": [
    { "id_persona": 7, "tipo_derecho": "titular" },
    { "id_persona": 9, "tipo_derecho": "cotitular" }
  ]
}
```

Las personas de una parcela nueva deben existir. La operación asegura su
vínculo con el núcleo mediante el modelo normalizado, sin crear identidades
paralelas ni fusionar personas por nombre. Parcela, relaciones de titularidad
y afectación se confirman juntas o se revierten juntas.

La lógica vive en un servicio de afectaciones, no en controladores ni React:

```text
Validar contrato → abrir transacción y auditoría → validar Tramo_Núcleo
→ resolver/crear parcela y titulares → validar parcela → crear afectación
→ confirmar o revertir todo
```

Las actualizaciones sólo aceptan datos editables de la ruta correspondiente y
no aceptan la identidad señalada en la regla 7. PostgreSQL sigue validando aun
si la API fue evadida. Las violaciones de contrato se devuelven como 400/422 y
los conflictos de integridad como 409, sin exponer SQL.

Los GET actuales se conservan. El POST genérico `/api/afectaciones` queda
temporalmente deprecado y delega a la misma validación, pero el frontend nuevo
no lo utiliza. Sólo se retirará en un CONTRACT posterior, cuando no tenga
consumidores.

## Frontend

El expediente maestro conserva ambas acciones de alta. Cada formulario usa su
contrato específico.

- El formulario colectivo elimina los subtipos `individual` y `copropiedad`,
  la selección de parcela y cualquier número normalizado de parcela.
- El individual muestra la parcela, su tipo, su PPT y titulares activos. No
  vuelve a capturar el PPT en la afectación.
- Una parcela nueva individual exige un titular; una copropiedad exige al menos
  dos antes de habilitar el alta.
- La creación de una parcela nueva usa la operación atómica; no encadena
  llamadas independientes que puedan dejar registros parciales.
- En edición se muestran tipo y parcela como identidad no editable.

No se agrega todavía detalle por afectación, aislamiento documental ni estados
de proceso.

## Pruebas de aceptación

| Caso | Resultado esperado |
| --- | --- |
| Colectiva sin parcela | Alta correcta. |
| Colectiva con parcela | Rechazo por restricción de base y API. |
| Individual sin parcela o de otro núcleo | Rechazo. |
| Individual con parcela inactiva, sin PPT o sin soporte/justificación | Rechazo. |
| Individual sin titular activo | Rechazo. |
| Individual con parcela individual y un titular | Alta correcta. |
| Copropiedad con un titular | Rechazo. |
| Copropiedad con dos titulares | Alta correcta. |
| Baja de parcela o titular que rompe una afectación activa | Rechazo por API y trigger directo. |
| Alta atómica con error en el segundo titular | No persiste ningún registro parcial. |
| Cambios concurrentes de titulares | Nunca violan el mínimo aplicable. |
| Historial incompatible en migración | Migración aborta sin modificar esquema ni datos. |
| Convenios y trámites existentes | Conservan FKs y regresiones pasan. |

## Despliegue y criterio de inicio

1. Configurar acceso a la base activa, respaldarla y ejecutar las
   prevalidaciones en modo lectura.
2. Corregir operativamente cualquier fila encontrada; 005 no la corregirá.
3. Aplicar la migración, luego backend y finalmente frontend.
4. Ejecutar la matriz de pruebas y revisar bitácora y consumidores del endpoint
   legado antes de planear su retiro.

Antes de implementar debe confirmarse que la definición de soporte o
justificación registral anterior refleja la regla operativa y que se acepta la
compatibilidad temporal del POST genérico. Una vez confirmado, la
implementación queda limitada a migración, servicio, contratos, formularios y
pruebas de este documento, sin adelantar Subcortes 2B o 2C.
