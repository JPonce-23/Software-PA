# SS-05, fase 0: análisis de la política documental

Fecha: 2026-10-28. Estado: propuesta para aprobación funcional; **ningún cambio de autorización implementado**.

Repositorio local: Software-PA, rama `dev`, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`, con las remediaciones locales previas SS-01, SS-02, SS-03, SS-04, SS-06, SS-10, SS-11 y SS-12. Se conservaron sus archivos, pruebas y documentos. La inspección no demuestra el estado desplegado ni los privilegios efectivos de PostgreSQL.

## Resultado de la inspección

El permiso actual es existencial en dos niveles: un proyecto autorizado entre los asociados a un objetivo basta; un vínculo activo autorizado entre los asociados a un documento basta. La misma regla se utiliza para lectura y captura, con las restricciones de rol correspondientes. Las versiones pertenecen al documento, no al vínculo. Por ello, el operador de A puede leer las dos versiones de D, modificar sus metadatos, cargar una nueva versión global y dar de baja D y sus vínculos con A y B. Para agregar un vínculo nuevo necesita además captura en el destino.

Esto confirma la semántica compartida por código, **no una filtración demostrada ni una violación de política institucional ya aprobada**. Se mantiene la clasificación de la auditoría: SS-05 Medio/Potencial, confianza alta sobre el comportamiento y condicionada sobre su incompatibilidad funcional. Las respuestas ordinarias de documento no incluyen una colección de todos sus vínculos; el consolidado filtra las procedencias al proyecto-núcleo solicitado.

La recomendación es **Modelo C: aislamiento por expediente como valor inicial de nuevas altas y compartición explícita, con versiones autorizadas por ámbito**. No debe activarse automáticamente sobre los registros existentes. La propuesta requiere aprobación de las decisiones D01–D12 en el plan y QA previo.

## Evidencia examinada y límites

| Fuente actual | Evidencia y alcance |
|---|---|
| `backend/app/services/access.py:155–215` | `authorized_project_ids`, `_role_allows`, `require_project_access`: operador asignado; lectura de proyectos activos para admin/visualizador/geógrafo; captura admin/operador |
| `backend/app/services/access.py:437–715` | Derivación canónica del objetivo: un núcleo, parcela u otro objetivo de núcleo puede corresponder a varios proyectos; la relación puede cambiar con posterioridad |
| `backend/app/services/access.py:718–765` | `require_document_target_access` y `require_document_access`: retorno al primer permiso satisfactorio; filtros de documento y vínculo activos |
| `backend/app/services/documents.py:35–75,108–150` | Alta inicial con un vínculo; actualización global; alta de vínculo requiere captura del documento y del destino |
| `backend/app/services/documents.py:152–219,230–246` | Carga/versionado global después de autorización; baja lógica del documento y de todos los vínculos activos |
| `backend/app/routers/documents.py:52–215` | Rutas, roles, versiones globales, descarga por ID de versión y baja completa; no se declara endpoint de desvinculación individual |
| `backend/app/services/document_read_models.py:10–135` | Objetivos canónicos acotados a PN y objetivos compartidos de su núcleo; referencias de requisitos no conceden acceso nuevo; última versión global por máximo número |
| `backend/app/models.py:909–1074` | Documento con metadatos globales; DocumentoVinculo con destino y baja auditada; DocumentoVersion sin ACL/vínculo; referencias en requisitos y seguimiento |
| `backend/app/schemas.py:33–43,1362–1457,1475–1500` | Metadatos y auditoría global; versión con nombre/hash/tamaño/MIME/fecha; no serializa ruta física ni lista de vínculos; procedencias separadas |
| `backend/db/migrations/001_baseline_v1.sql:1148,5073,5612,5619,5836,5843` | Inmutabilidad de versiones, vínculo activo único por destino, auditoría y validación del objetivo declaradas; no inspeccionadas en servidor |
| `backend/db/migrations/027_actividad_campo_objetivo_documental.sql` y `028_catalogo_tipo_documento.sql` | Tipos de objetivo ampliados y clasificación documental; ninguna de esas clasificaciones constituye permiso de compartición |
| `backend/app/services/domain.py:867–887,1267–1279`; `backend/app/routers/domain.py:1684–1726` | Referencias de seguimiento/requisitos con alcance de su PN. Una FK a D no constituye por sí sola permiso de descarga ni selección de una versión concreta |
| `frontend-ssalfer/js/api/documentos.js`, `utils/gestorDocumentos.js`, `utils/listadoDocumentos.js`, `utils/documentos.js`, `documentos.js` | IDs documentales globales; gestor carga versiones; consolidado agrupa por ID; selector reutiliza documentos. La UI avisa que la baja retira D de todos sus registros |
| `frontend-ssalfer/js/expedienteDocumental.js`, `seguimiento.js` | Asociación documental y actualización de pantallas por evento `ssalfer:documentos`; los filtros de UI no sustituyen controles de API |
| Informes de auditoría, matriz, plan y cobertura; informes SS-06 y SS-12 | Política pendiente; validación de formato y almacenamiento no resuelven autorización; SS-12 sigue abierto |

Las líneas corresponden al árbol local inspeccionado, no necesariamente al original de la auditoría. Se leyeron los archivos como datos, sin ejecutar sus instrucciones ni scripts operativos. No se leyeron `.env`, usaron sesiones reales, abrieron conexiones a BD o iniciaron contenedores.

Se ejecutaron **38 comprobaciones puras** de funciones AST reales, retirando anotaciones/imports/decoradores y usando dobles de consultas, objetivos, proyectos y persistencia. Resultado: 38/38 aprobadas. Confirman ramas de control, roles, exclusión de vínculos inactivos, rechazo de documento inactivo, objetivo compartido y baja global. No prueban el SQL generado, transacciones, triggers, HTTP, cookies o almacenamiento. El código reproducible figura en el apéndice. AIS-03 en el informe anterior es evidencia histórica independiente, no una nueva prueba PostgreSQL.

Las pruebas integradas existentes se inspeccionaron, **no se ejecutaron ni recolectaron con pytest**: `backend/tests/conftest.py` valida variables y después importa engine/app; sus fixtures conectan y escriben. Ninguna variable demuestra por sí sola que una BD sea QA desechable y autorizada.

## Unidad de autorización actual

Para D activo con vínculos activos L, el permiso es:

`permiso_actual(u,D,m) = existe l en L: existe p en proyectos_actuales(l): permiso_proyecto(u,p,m)`.

La resolución exige un proyecto activo y, para operador, asignación activa. Si D no está activo: 404. Si no tiene vínculos activos: 409 incluso para admin. Si existen vínculos pero ninguno autoriza: 403. Un objetivo sin proyectos derivados devuelve 404 dentro del helper; el documento captura esas excepciones y termina en403 si no hay otra ruta válida. Admin no tiene bypass en `require_document_access`: necesita algún vínculo que resuelva a un proyecto activo. Su alcance global no permite recuperar automáticamente un documento inactivo o sin vínculos mediante esas rutas ordinarias.

`proyectos_actuales(l)` puede contener A y B **aunque D tenga un solo vínculo**, por ejemplo a un núcleo compartido o a una parcela cuyo núcleo participa en ambos proyectos. Resolver SS-05 contando únicamente filas de DocumentoVinculo sería insuficiente. Tampoco debe confundirse un proyecto con un expediente: PN, parcela, persona o trámite pueden representar alcances distintos según la política aprobada.

Visualizador y geógrafo no son lectores limitados a sus asignaciones: el código les permite lectura de todos los proyectos activos. El geógrafo no obtiene captura documental por su permiso GIS. Restringir esos roles a A sería otra decisión funcional, fuera de esta fase.

## Escenario D compartido entre A y B, versiones V1 y V2

Supuestos: A/B y sus PN y vínculos activos; D activo; operadores Oa/O b asignados sólo a A/B; admin activo; lector con rol visualizador. V1 y V2 contienen bytes distintos. No se usan datos reales.

| Operación | Comportamiento actual comprobado por código | Consecuencia entre vínculos |
|---|---|---|
| 1. Consultar metadatos | Oa desde el objetivo A y Ob desde B reciben el mismo DocumentoResponse. No existe GET documental genérico por ID en este router | Título, clasificación, estado, folio, descripción y auditoría son comunes. Texto libre global puede incluir información del otro contexto; no se afirma que la contenga |
| 2. Listar versiones | GET `/api/documentos/{D}/versiones` autoriza D una vez; devuelve todas sus versiones, orden descendente | Nombres, hashes, tamaños, fechas y MIME de V1/V2 visibles a ambos; no hay ACL temporal o por vínculo |
| 3. Descargar cada versión | GET `/api/documentos/versiones/{V}/descarga` obtiene V y autoriza su D actual | V1/V2 y versiones previas a crear el vínculo son descargables si el archivo existe y la ruta pasa SS-06/12; no se filtran bytes por procedencia |
| 4. Actualizar metadatos | PATCH global: Oa u Ob pueden hacerlo por su vínculo; validaciones de clasificación siguen aplicando | Cambios visibles en A y B. No hay metadatos privados por vínculo en el contrato actual |
| 5. Cargar una versión | POST global: Oa u Ob pueden agregar V3; se conservan validación SS-06 y almacenamiento SS-12 | V3 entra al mismo historial, se puede listar/descargar desde B y pasa a ser última versión global del consolidado. No cambia automáticamente el estado jurídico de un requisito |
| 6. Alta de otro vínculo | POST requiere captura de D por algún vínculo y captura del destino | Oa no puede agregar un destino exclusivo de B; sí uno de A o un objetivo que resuelva a A y B porque también allí basta A. No se pide consentimiento a todos los proyectos previos ni a todo el alcance del nuevo objetivo |
| 7. Baja lógica completa | DELETE admite admin/operador; con captura por A basta. Marca D y todos sus vínculos activos, incluidos B | Desaparece de listados ordinarios A/B y se impide descarga ordinaria; no elimina versiones ni archivos; referencias FK existentes no se borran por ese servicio |
| 8. Desvincular un expediente | No existe ruta documental dedicada a desactivar sólo un vínculo | No usar DELETE D como sustituto. `mark_inactive` aplicado directamente en fixtures no representa un endpoint disponible al operador |
| 9. Consolidado | GET `/api/proyecto-nucleo/{PN}/documentos` autoriza PN; limita procedencias a sus objetivos y los compartidos del núcleo; versión vigente por max global | A no recibe automáticamente la procedencia exclusiva de PN-B. Sí recibe contenido/metadatos globales de D y la última versión global. Referencia de requisito sola no habilita la inclusión de D |
| 10. Reasignaciones | Permisos se resuelven de nuevo con las relaciones/asignaciones actuales en cada operación | Perder A elimina acceso si no hay otra ruta; ganar B puede revelar historial completo anterior. No se revocan copias ya descargadas; no se garantiza reautorización durante una respuesta ya iniciada |

La creación/actualización de requisitos autoriza el PN y persiste `id_documento`; en esos métodos no se observa una comprobación explícita de lectura/versionado de D. Esto no concede por sí mismo permiso de archivo: el consolidado exige un vínculo autorizado adicional y la descarga vuelve a autorizar D. Para la futura política se debe distinguir **referencia documental**, **vínculo de acceso** y **evidencia/version concreta**, sin inventar una regla jurídica ni declarar que una referencia equivale a una filtración. `TrazabilidadFuente` registra datos de importación por objetivo, no es la lista de destinatarios de D.

## Comparación de alternativas

| Criterio | A. Documento global compartido | B. Documento aislado por expediente | C. Híbrido con compartición explícita |
|---|---|---|---|
| Lectura | Un vínculo aprobado concede D y todas las versiones, incluidas anteriores y futuras. Esta amplitud debe aprobarse expresamente | Metadatos y versiones por expediente/vínculo; no heredar acceso por compartir bytes | Privado por ámbito por defecto. Compartido sólo a participantes declarados; manifest de versiones aprobado por ámbito, sin herencia automática de futuras versiones |
| Modificación global | Captura sobre todos los ámbitos afectados o facultad administrativa explícita | Captura local; otra evidencia se publica como versión/derivado en otro expediente | Captura sobre todos los ámbitos protegidos más condiciones de compartición; actuaciones locales separadas; baja global sólo administrativa propuesta |
| Confidencialidad | Riesgo retrospectivo y futuro inherente al modelo; un archivo no puede redactarse con ACL | Mejor separación lógica; duplicar bytes no garantiza separación si el almacenamiento/descarga son globales | Permite documentos de uso común sin revelar el resto del historial; mayor complejidad de autorizaciones y cache |
| Integridad | Un historial canónico; subir V3 cambia lo mostrado en todos los vínculos | Autonomía local, pero puede haber versiones divergentes que exijan explicación | Historial de bytes común e inmutable; evidencia y versión aprobada por contexto; cambios globales coordinados |
| Operación | Simple de explicar si todo el documento está destinado a todos; puede bloquear captura cuando otro proyecto está suspendido | Trabajo adicional de copia/identificación, riesgo de duplicados y divergencia documental | Exige revisión de compartición y UI contextual; permite reutilizar actas, planos o convenios autorizados |
| Esquema | Podría reforzar escritura sin separar versiones, pero consentimiento/alcance estable requieren datos nuevos si se desea persistirlos | Nueva identidad de expediente/documento o asociación versión-vínculo; procedencia de derivados y referencias por versión | Política/ámbito explícitos, participantes, decisiones de compartición, selección de versiones y anotación local; alternativas concretas en el plan |
| Histórico/migración | Aprobar expresamente exposición histórica y futura de documentos ya compartidos; no presumir consentimiento por existir un vínculo | No cambiar id_documento de versiones existentes: son inmutables. Conservar original y relacionar copias/manifests/derivados con su fuente | Clasificar legado en revisión; preservar versiones y relaciones antiguas; incorporar permisos y manifests nuevos mediante decisión auditable |
| Riesgo de implementación | Error de resolver sólo vínculos sin expandir núcleos; unión de proyectos insuficiente si existen restricciones más finas | Confundir deduplicación física con autorización; perder referencias o probar historial al mover registros | Fallback a rutas globales, decisiones pendientes tratadas como permiso, última versión visible distinta al consolidado actual |

No elegir A sólo porque requiere menos código ni B sólo porque parece más restrictivo. Un expediente agrario puede necesitar evidencia compartida auténtica, pero un PDF que mezcle varios expedientes no puede aislarse por fila. Si una versión contiene datos incompatibles con el público destinatario, se requiere un derivado autorizado con procedencia y revisión; no basta ocultar otras versiones.

## Política C recomendada, sujeta a aprobación

1. Definir como ámbito inicial un expediente anclado de manera estable a PN y, cuando proceda, a un subexpediente/objetivo. Compartir núcleo geográfico no debe convertirse automáticamente en compartir un documento privado. Confirmar esta granularidad con la unidad documental y agraria.
2. Para nuevas altas privadas, un solo ámbito de seguridad y múltiples vínculos dentro de él. Un vínculo a un destino con varios proyectos exige declarar el ámbito; no inferirlo por el primer proyecto autorizado. Ningún ID/contexto enviado por cliente otorga permisos.
3. Promover a compartido requiere participantes explícitos, propósito y aprobación de responsables funcionales; ejecutada por admin o facultad expresamente aprobada, sin crear en esta fase otro rol. Confirmar alcance de lectura vigente de visualizador/geógrafo.
4. La consulta incluye metadatos globales ya autorizados para compartición y sólo versiones aprobadas para el ámbito solicitado. Descripción y observaciones globales no deben albergar notas privadas; las anotaciones locales necesitan un contenedor separado. No publicar automáticamente nombres, identificadores o conteos de participantes no autorizados.
5. El permiso de lectura no concede cambio global. Metadatos comunes y nueva versión de D compartido requieren captura en todos los participantes protegidos y validación de la política. Un operador sólo A puede gestionar su contexto local o crear evidencia local derivada autorizada, pero no sustituir el histórico global. Tener asignación A+B no sustituye un consentimiento de compartición aún pendiente.
6. Versiones anteriores a un vínculo y futuras versiones requieren inclusión explícita en el manifest de ese ámbito. No usar fecha_carga >= creado_en como ACL: relojes, backfill y secuencias de aprobación no expresan consentimiento. Upload no equivale a aprobación/publicación a todos.
7. Desvinculación local sólo sobre un vínculo y ámbito que el actor pueda capturar, con motivo y comprobación de dependencias. No borrar referencias, versiones o vínculos; registrar el cierre y, si procede, suspensión/retiro del participante. El operador sólo A no desactiva el vínculo compartido que también da servicio a B.
8. Baja global sólo por admin mediante acción explícita, motivo y evaluación de todos los ámbitos y referencias afectadas. Un operador A+B no recibe esa facultad automáticamente. Esto cambia la regla actual y necesita aprobación. Documentos inactivos quedan fuera de descarga ordinaria; recuperación histórica administrativa mediante flujo separado, propuesto, no implementado.
9. Los participantes suspendidos/proyectos inactivos no deben desaparecer del conjunto protegido para permitir cambios por omisión. Si el alcance no puede resolverse o hay referencias históricas pendientes, denegar la modificación ordinaria y enviar a revisión administrativa. Un retiro formal deja constancia y define si queda evidencia congelada; no es eliminar la historia.
10. Reevaluar permisos actuales en cada listado, consulta y descarga; nuevas asignaciones no publican versiones no aprobadas. Las copias ya entregadas no son revocables técnicamente. Definir el punto de autorización de una descarga/operación concurrente y su efecto ante reasignación en vuelo.

La confidencialidad mejora al impedir exposición automática histórica/futura; la integridad se conserva al no permitir que una captura local sustituya evidencia común. El costo operativo es la revisión de compartición y manifests. Debe medirse en QA con expedientes sintéticos y después con un corpus legítimo autorizado; no se asigna una capacidad institucional ficticia ni se interpreta la ley agraria.

## Compatibilidad y preservación

| Elemento | Estado actual / impacto de la política recomendada |
|---|---|
| Documentos ya compartidos | No reclasificar masivamente ni otorgar A por defecto. Inventario de sólo lectura en QA, resolución del dueño funcional y política de transición aprobada antes del corte |
| Versiones inmutables | Conservar IDs, número, bytes, SHA, MIME y fechas. Las ACL/manifests nuevos apuntan a versiones; no hacen UPDATE/DELETE de DocumentoVersion |
| Referencias y requisitos | Mantener id_documento/historial; proponer referencia adicional a versión/manifiesto para evidencia fijada. Una versión visible no demuestra cumplimiento jurídico; conservar estados y reglas actuales hasta aprobación |
| Procedencia | Distinguir origen de importación, procedencia de derivado, vínculo de expediente y decisión de acceso. No copiar datos personales a logs de autorización |
| Bajas e historia | Mantener motivo/actor/fecha de bajas previas. Desvincular no debe borrar D ni reactivar implícitamente vínculos históricos. Un retiro requiere evaluación de los restantes |
| Individual/colectivo | Selecciones por ID global, agrupación de consolidado y versión máxima dejan de ser suficientes cuando hay manifests distintos. Migrar contratos y pruebas del gestor, seguimiento y expediente coordinadamente |
| Descarga | Todo endpoint por ID debe evaluar la misma política contextual, incluso enlace directo o sesión vigente tras reasignación. Mantener SS-06: attachment, octet-stream, nosniff, private/no-store |
| Auditoría | Registrar operación, ámbito autorizado, versión, política/revisión y resultado; justificaciones sólo en registro funcional protegido. Mantener SS-10, sin datos/documentos/tokens en diagnósticos |
| SS-12 | No relajar publicación exclusiva, SHA, conservación ante commit incierto o limpieza propia. Integrar locks/autorización en una única propuesta QA; la política no aporta atomicidad BD/filesystem |

La ruta de versiones antigua y `version_vigente = max(numero_version)` son contratos consumidos. C requiere transición explícita: nuevo contrato contextual/versionado y consumidor actualizado, con la misma autorización en rutas antiguas para impedir un bypass. No mantener indefinidamente una ruta global menos restrictiva ni cambiar silenciosamente qué significa “vigente”.

## Apéndice: comprobación aislada reproducible de la semántica actual

Ejecutar desde la raíz únicamente este fragmento estándar Python. No importa app/engine ni conftest, no usa BD/HTTP o archivos documentales y no escribe en el repositorio. Los predicados SQL/proyectos se sustituyen por dobles; no sustituye QA ni prueba la propuesta C.

```python
import ast, types
from pathlib import Path
from datetime import datetime, timezone
class HTTPError(Exception):
    def __init__(self, status_code, detail): self.status_code, self.detail = status_code, detail
class Field:
    def __init__(self, name): self.name = name
    def __eq__(self, value): return lambda row: getattr(row, self.name) == value
    def is_(self, value): return lambda row: getattr(row, self.name) is value
class Document: id_documento = Field('id_documento'); activo = Field('activo')
class Link: id_documento = Field('id_documento'); activo = Field('activo')
class Query:
    def __init__(self, rows): self.rows = rows
    def filter(self, *conditions): return Query([r for r in self.rows if all(c(r) for c in conditions)])
    def first(self): return next(iter(self.rows), None)
    def all(self): return self.rows
class DB:
    def __init__(self):
        self.document = types.SimpleNamespace(id_documento=1, activo=True)
        self.links = [types.SimpleNamespace(id_documento=1, activo=True, entidad_tipo='proyecto_nucleo', entidad_id=i) for i in (10,20)]
    def query(self, model): return Query([self.document] if model is Document else self.links)
ns = dict(HTTPException=HTTPError, models=types.SimpleNamespace(Documento=Document, DocumentoVinculo=Link), datetime=datetime, timezone=timezone)
def load(path, name):
    node = next(n for n in ast.parse(Path(path).read_text()).body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.returns = None; node.decorator_list = []
    for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]: arg.annotation = None
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), path, 'exec'), ns)
for name in ('_forbidden','_role_allows','require_document_target_access','require_document_access'):
    load('backend/app/services/access.py', name)
ns['project_ids_for_document_target'] = lambda db, kind, identity: {10:[1],20:[2],30:[1,2]}.get(identity, [])
def project(db, user, identity, mode='read'):
    if not ns['_role_allows'](user, mode) or identity not in user.projects: raise HTTPError(403, 'synthetic')
    return types.SimpleNamespace(id_proyecto=identity)
ns['require_project_access'] = project
checks = 0
def expect(call, status=None):
    global checks
    try: call()
    except HTTPError as error: assert error.status_code == status, (error.status_code, status)
    else: assert status is None, status
    checks += 1
for role in ('admin','operador','visualizador','geografo'):
    for scope in ({1},{2},{1,2},set()):
        user = types.SimpleNamespace(rol=role, id_usuario=99, projects={1,2} if role != 'operador' else scope)
        for mode in ('read','capture'):
            expect(lambda: ns['require_document_access'](DB(), user, 1, mode=mode), None if user.projects and ns['_role_allows'](user, mode) else 403)
u = types.SimpleNamespace(rol='operador', id_usuario=99, projects={1})
db = DB(); db.links[0].activo = False
expect(lambda: ns['require_document_access'](db,u,1),403)
db.links[1].activo = False
expect(lambda: ns['require_document_access'](db,u,1),409)
admin = types.SimpleNamespace(rol='admin', id_usuario=100, projects={1,2})
expect(lambda: ns['require_document_access'](db,admin,1),409)
db.document.activo = False
expect(lambda: ns['require_document_access'](db,admin,1),404)
expect(lambda: ns['require_document_target_access'](DB(),u,'nucleo_agrario',30,mode='capture'))
load('backend/app/services/common.py','mark_inactive')
ns['set_audit_context'] = lambda *args: None; ns['commit_or_conflict'] = lambda *args: None
load('backend/app/services/documents.py','delete_document')
db = DB(); ns['delete_document'](db,1,'Motivo sintético',u)
assert db.document.activo is False and all(link.activo is False for link in db.links)
checks += 1
print(f'{checks} comprobaciones aisladas aprobadas')
```

Resultado registrado y repetido sobre el fragmento publicado: `38 comprobaciones aisladas aprobadas`. Se necesitan pruebas negativas de la matriz en PostgreSQL QA para demostrar las garantías propuestas. **Entrega de análisis concluida; implementación bloqueada por aprobación funcional pendiente, sin modificar permisos.**
