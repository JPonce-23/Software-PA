# Derechos colectivos: referencia para frontend

> **Alcance de la referencia:** La verificación original y las ubicaciones de código siguientes corresponden al corte del 2 de octubre de 2026. La divergencia de linaje relatada es histórica; el inventario canónico actual llega a 028. Esta actualización revisa sólo backend y documentación, sin comprobar el frontend. El contrato vigente está en [API.md](API.md).

Verificado en `feature/backend-logica`, commit `49f12f747a1eda4fc75930d78e0f23dd00baf422`, el 2 de octubre de 2026. Base de referencia: `software_pa_test`.

**Sí existe implementación de derechos colectivos en el backend.** Se representa mediante entidades del expediente `ProyectoNucleo`, con `tipo_afectacion = "colectivo"` y `ambito = "colectivo"`. No hay una tabla o endpoint independiente llamado `derechos_colectivos`.

## Tablas e implementación

| Función | Tablas | Modelo |
|---|---|---|
| Expediente | `proyecto_nucleo`, `nucleo_agrario` | `backend/app/models.py:217`, `:247` |
| Afectaciones colectivas | `afectacion` | `backend/app/models.py:484` |
| Tierras y destinos afectados | `unidad_agraria`, `afectacion_unidad_agraria` | `backend/app/models.py:519`, `:561` |
| Representación y padrón | `orv`, `orv_integrante`, `padron_historial` | `backend/app/models.py:353`, `:382`, `:410` |
| Actividades previas | `actividad_campo` | `backend/app/models.py:463` |
| Asambleas | `asamblea`, `asamblea_convocatoria` | `backend/app/models.py:577`, `:615` |
| Convenios colectivos | `convenio`, `convenio_afectacion`, `convenio_compareciente` | `backend/app/models.py:634`, `:681`, `:697` |
| Registro RAN | `tramite_ran`, `tramite_ran_evento` | `backend/app/models.py:719`, `:743` |
| FIFONAFE | `tramite_fifonafe`, `tramite_fifonafe_evento`, `tramite_fifonafe_afectacion`, `tramite_fifonafe_interviniente` | `backend/app/models.py:765` en adelante |
| Indemnización y pago | `indemnizacion`, `pago` | `backend/app/models.py:862`, `:879` |

Las tablas colectivas revisadas existen en `software_pa_test`. Sus migraciones `001`–`019` coinciden por checksum con la rama. Su historial desde `020` incluye cambios geoespaciales distintos del `020` de esta rama; no se presume equivalencia total de esquema.

## Endpoints principales

Todas las rutas incluyen `/api`. En esta tabla, `{pn}` corresponde al parámetro `id_proyecto_nucleo`; los demás nombres abreviados representan el identificador de la entidad.

| Función | Método | Ruta |
|---|---|---|
| Obtener expedientes del proyecto | GET | `/api/proyectos/{id_proyecto}/nucleos` |
| Obtener expediente | GET | `/api/proyecto-nucleo/{pn}` |
| Listar exclusivamente afectaciones colectivas | GET | `/api/proyecto-nucleo/{pn}/afectaciones?tipo=colectivo` |
| Crear afectación colectiva | POST | `/api/proyecto-nucleo/{pn}/afectaciones` |
| Obtener / editar / dar de baja afectación | GET, PATCH, DELETE | `/api/afectaciones/{id_afectacion}` |
| Listar / crear unidades agrarias | GET, POST | `/api/proyecto-nucleo/{pn}/unidades-agrarias` |
| Listar / asociar unidades a afectación | GET, POST | `/api/afectaciones/{id_afectacion}/unidades-agrarias` |
| Listar / crear ORV | GET, POST | `/api/proyecto-nucleo/{pn}/orv` |
| Listar / agregar integrantes | GET, POST | `/api/orv/{id_orv}/integrantes` |
| Listar / crear padrón | GET, POST | `/api/proyecto-nucleo/{pn}/padrones` |
| Listar / crear actividades | GET, POST | `/api/proyecto-nucleo/{pn}/actividades` |
| Listar / crear asambleas | GET, POST | `/api/proyecto-nucleo/{pn}/asambleas` |
| Editar asamblea | PATCH | `/api/asambleas/{id_asamblea}` |
| Listar / crear convocatorias | GET, POST | `/api/asambleas/{id_asamblea}/convocatorias` |
| Listar / crear convenios | GET, POST | `/api/afectaciones/{id_afectacion}/convenios` |
| Obtener / editar convenio | GET, PATCH | `/api/convenios/{id_convenio}` |
| Listar / agregar comparecientes | GET, POST | `/api/convenios/{id_convenio}/comparecientes` |
| Listar / agregar afectaciones a convenio | GET, POST | `/api/convenios/{id_convenio}/afectaciones` |
| Crear trámite RAN | POST | `/api/tramites-ran` |
| Listar RAN del expediente | GET | `/api/proyecto-nucleo/{pn}/tramites-ran` |
| Listar RAN del acta | GET | `/api/asambleas/{id_asamblea}/tramites-ran` |
| Listar RAN del convenio | GET | `/api/convenios/{id_convenio}/tramites-ran` |
| Listar / crear eventos RAN | GET, POST | `/api/tramites-ran/{id_tramite_ran}/eventos` |
| Listar / crear FIFONAFE | GET, POST | `/api/proyecto-nucleo/{pn}/fifonafe` |
| Editar FIFONAFE | PATCH | `/api/fifonafe/{id_tramite_fifonafe}` |
| Listar / crear eventos FIFONAFE | GET, POST | `/api/fifonafe/{id_tramite_fifonafe}/eventos` |
| Listar / crear intervinientes FIFONAFE | GET, POST | `/api/fifonafe/{id_tramite_fifonafe}/intervinientes` |
| Obtener / crear indemnización | GET, POST | `/api/afectaciones/{id_afectacion}/indemnizacion` |
| Listar / registrar pagos | GET, POST | `/api/indemnizaciones/{id_indemnizacion}/pagos` |
| Listar / crear documentos de una entidad | GET, POST | `/api/documentos/objetivos/{entidad_tipo}/{entidad_id}` |
| Listar / registrar requisitos documentales | GET, POST | `/api/proyecto-nucleo/{pn}/requisitos-documentales` |
| Listar / registrar seguimiento | GET, POST | `/api/proyecto-nucleo/{pn}/seguimiento` |
| Obtener catálogos para formularios | GET | `/api/catalogos/operativos/{tipo_catalogo}` |
| Reporte de convenios colectivos por destino | GET | `/api/reportes/convenios/colectivos-destino` |
| Avance colectivo | GET | `/api/reportes/avance-periodo?id_proyecto={id_proyecto}&ambito=colectivo` |
| Resumen colectivo | GET | `/api/reportes/resumen-actual?id_proyecto={id_proyecto}&ambito=colectivo` |

Los endpoints administrativos están en `backend/app/routers/domain.py`; los reportes en `backend/app/routers/reporting.py`; los documentos en `backend/app/routers/documents.py`. El prefijo `/api` se registra en `backend/app/main.py`.

## Ejemplos mínimos para integrar

Crear afectación colectiva, sin necesidad de parcela:

```http
POST /api/proyecto-nucleo/123/afectaciones
Content-Type: application/json
```

```json
{
  "tipo_afectacion": "colectivo",
  "superficie_preliminar_ha": "3.5000000",
  "superficie_afectada_ha": "3.2500000"
}
```

Crear un COP en esa afectación:

```http
POST /api/afectaciones/456/convenios
Content-Type: application/json
```

```json
{
  "tipo_instrumento": "convenio",
  "tipo_convenio": "cop_original",
  "consecutivo": 1
}
```

El backend deriva `ambito = "colectivo"` de la afectación: no se envía `ambito` en el alta del convenio. Este payload representa un instrumento pendiente de completar, no una firma acreditada.

Crear un trámite FIFONAFE pendiente para afectaciones colectivas del mismo expediente:

```http
POST /api/proyecto-nucleo/123/fifonafe
Content-Type: application/json
```

```json
{
  "ids_afectacion": [456],
  "estatus": "pendiente"
}
```

El backend deriva el ámbito de las afectaciones incluidas. El GET de FIFONAFE no declara filtro `ambito`: seleccionar en frontend los registros cuya respuesta tenga `ambito === "colectivo"`.

Los identificadores son ilustrativos. Los endpoints necesitan sesión y acceso al proyecto. Los POST/PATCH/DELETE con sesión usan protección CSRF (`X-CSRF-Token` y origen permitido). Captura: `admin`/`operador`; lectura también admite `visualizador`/`geografo`.

## Contratos y detalles de integración

- `backend/app/schemas.py`: `AfectacionCreate` en línea 691, `UnidadAgrariaCreate` en 646, `AsambleaCreate` en 771, `ConvenioCreate` en 833 y `TramiteFifonafeCreate` en 1108.
- Las asambleas reciben IDs catalogados (`id_tipo_asamblea`, `id_contexto_asamblea`); consultar catálogos antes de construir el payload.
- Los tipos jurídicos colectivos actuales son `cop_original`, `modificatorio` y `obras_complementarias`. `superficie_adicional` es legado normalizado a `modificatorio` en `016`; `ADICIONAL`/`2A_ADICIONAL` se conservan como clasificación operativa de la afectación. No enviar `superficie_adicional` como tipo del convenio al contrato actual.
- En el reporte por destino, el monto declarado pertenece al convenio y puede aparecer en varias filas. No sumarlo entre destinos del mismo convenio.
- El flujo FIFONAFE v2 tiene eventos/evidencias/ciclos; completar cuatro oficios del legado no basta para declarar completo un trámite v2.
- Contrato estático: `docs/openapi.json`. Contrato publicado: `http://localhost:8000/openapi.json`. Swagger: `http://localhost:8000/docs`.
- Prueba específica del reporte colectivo: `backend/tests/test_convenios_colectivos_destino.py`, con casos A–J.

La verificación identifica implementación, contratos publicados y objetos existentes en PostgreSQL. No sustituye pruebas funcionales autenticadas de cada operación.

El inventario ampliado con enlaces a líneas de implementación está en `docs/INFORME_DERECHOS_COLECTIVOS_2026-10-02.md`.

## Consulta documental consolidada vigente

`GET /api/proyecto-nucleo/{id_proyecto_nucleo}/documentos` permite leer el soporte
documental del expediente en una llamada, conservando entidad, ID, origen y
procedencia de cada relación, DocumentoResponse y versión de mayor numero_version.
Respeta las autorizaciones y objetivos compartidos del núcleo existentes; no
publica procedencias de otro ProyectoNucleo. Es un read-model, sin duplicar
documentos ni crear carpetas o reglas nuevas. Las rutas documentales por objetivo
se mantienen. Véase [API.md §11.2](API.md#112-documentos-por-proyectonucleo).
