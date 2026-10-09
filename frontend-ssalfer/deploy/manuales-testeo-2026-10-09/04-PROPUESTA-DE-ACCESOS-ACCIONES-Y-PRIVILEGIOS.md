# Propuesta de accesos, acciones y privilegios por rol — SSALFER

**Fecha:** 9 de octubre de 2026.  
**Estado:** propuesta para revisión con las áreas usuarias. No constituye una política aprobada ni modifica los permisos del sistema.

## Propósito

Se propone organizar el acceso de acuerdo con cuatro funciones: administrar el sistema, capturar información operativa, consultar avances y gestionar cartografía. Cada persona tendría uno de los roles existentes —administrador, operador, visualizador o geógrafo— y acceso a los proyectos que le correspondan.

El objetivo es que los usuarios encuentren las pantallas necesarias para su trabajo y puedan reconocer qué acciones les corresponden. **Acceder a una pantalla no significa poder modificar todo lo que contiene.** Por ejemplo, todos pueden consultar un mapa autorizado, pero sólo administrador y geógrafo deben cargar y modificar cartografía en Gestión geoespacial.

Esta propuesta amplía el listado demostrativo del 8 de octubre. Se basa en los permisos del código integrado revisado, pero las decisiones organizativas que se señalan al final siguen abiertas a evaluación. No certifica que todos los botones actuales ya se presenten exactamente como aquí se propone.

## 1. Privilegios comunes a los cuatro roles

Se propone que administrador, operador, visualizador y geógrafo puedan:

- Iniciar sesión, cerrar su sesión y **cambiar su propia contraseña**.
- Ver su nombre y el rol con el que trabajan.
- Entrar al dashboard y consultar los proyectos autorizados para su cuenta.
- Abrir fichas, usar filtros, buscar registros y recorrer páginas dentro de ese alcance.
- Consultar el mapa de sus proyectos, activar o desactivar capas y revisar sus detalles.
- Consultar documentos y descargar los archivos que estén autorizados para esa cuenta.
- Consultar reportes y utilizar las exportaciones disponibles sobre información autorizada, sujeto a la decisión pendiente sobre descargas y datos financieros.

Cambiar la contraseña propia no equivale a restablecer la de otra persona. Administrar cuentas, asignar roles, restablecer contraseñas de terceros y revocar accesos serían funciones del administrador.

El rol por sí solo no debe otorgar acceso indiscriminado a proyectos o datos de otras áreas. Operador, visualizador y geógrafo trabajarían sobre sus proyectos asignados. El alcance institucional del administrador debe quedar establecido por la organización y seguir las restricciones que aplique el servidor.

## 2. Administrador

### Finalidad del rol

Mantener la organización del sistema, las cuentas, los proyectos y los catálogos; atender correcciones administrativas y supervisar la información. Tener este rol no implica que deba realizar toda la captura diaria.

### Pantallas propuestas

Dashboard; fichas de proyectos; Nuevo proyecto; Usuarios y permisos; Catálogos operativos; Auditoría; núcleos; personas; ORV; padrones; parcelas y unidades agrarias; afectaciones; asambleas; actividades; convenios; trámites RAN y FIFONAFE; documentos y expediente documental; indemnización, estado financiero y seguimiento; derechos colectivos y reportes; Mapa; Gestión geoespacial; Cambiar contraseña.

### Acciones y privilegios propuestos

- Crear y actualizar proyectos; administrar su baja cuando proceda y exista la operación.
- Crear, actualizar, dar de baja y reactivar usuarios; asignarles rol y proyectos mediante las funciones disponibles.
- Atender desbloqueos, restablecimientos de contraseña y revocación de sesiones de otras cuentas.
- Mantener opciones de catálogos operativos. La consulta del catálogo de tipos documentales no implica que exista una pantalla para crear tipos nuevos.
- Crear o corregir la ficha general de un núcleo y atender altas excepcionales permitidas. Distinguir esta acción de vincular un núcleo existente a un proyecto.
- Capturar y corregir información administrativa y documentos, dentro de las operaciones disponibles.
- Dar de baja o reactivar personas e integrantes de ORV cuando corresponda. Una reactivación de integrante no debe borrar su fecha de término de participación.
- Cargar, revisar, conciliar y confirmar cartografía, igual que el geógrafo, respetando validaciones y restricciones del proyecto.
- Consultar Auditoría para conocer quién realizó los cambios y cuándo. **Consultar auditoría no otorga permiso para editar o borrar su historial.**

### Límites propuestos

El administrador no debe saltarse validaciones ni transformar un rechazo del sistema en una autorización. No se propone eliminación definitiva general de documentos, versiones, decisiones o historiales. Las operaciones no disponibles no se consideran concedidas por el hecho de ser administrador.

## 3. Operador

### Finalidad del rol

Registrar y mantener la información administrativa y documental de los proyectos asignados. Es el perfil de trabajo cotidiano para captura y seguimiento.

### Pantallas propuestas

Dashboard y fichas de proyectos; núcleos del proyecto; personas; ORV; padrones; parcelas y unidades agrarias; afectaciones; asambleas; actividades; nuevo convenio y ficha de convenio; trámites RAN y FIFONAFE; documentos y expediente; indemnización, estado financiero y seguimiento; derechos colectivos y reportes; Mapa; Gestión geoespacial en consulta; Cambiar contraseña.

### Acciones y privilegios propuestos

- Buscar núcleos en el catálogo RAN, vincular un núcleo existente al proyecto autorizado y actualizar los datos de esa relación que correspondan a captura.
- Buscar, registrar y actualizar personas. Seleccionar una persona no debe crear una relación hasta guardar el formulario correspondiente.
- Registrar y actualizar órganos e integrantes de ORV; finalizar una participación conforme a sus fechas y motivo.
- Capturar padrones, asambleas, actividades, parcelas, unidades, afectaciones, convenios, trámites y seguimiento según los formularios disponibles.
- Registrar documentos, clasificarlos, corregir sus datos, vincular documentos existentes, subir nuevas versiones y registrar procedencia.
- Actualizar requisitos y situación documental del expediente mediante las acciones disponibles.
- Capturar indemnizaciones y pagos donde el sistema lo permita. Este permiso de captura **no debe presentarse como facultad de autorizar un pago o aprobar una operación financiera**, porque son decisiones diferentes.
- Consultar mapas, estado de cargas y revisiones geoespaciales, sin modificar cartografía.
- Consultar y exportar sus reportes autorizados.

### Acciones que no se proponen para este rol

Crear proyectos; administrar usuarios o asignaciones; cambiar catálogos; consultar la auditoría administrativa global; dar de baja o reactivar personas e integrantes de ORV; cargar, modificar o confirmar cartografía; cambiar el sistema de coordenadas.

Algunas bajas de relaciones operativas sí están permitidas al operador por el código actual. Por eso no se propone una regla ambigua de “el operador puede borrar todo” o “nunca puede dar de baja nada”. La delimitación de esas bajas debe decidirse por tipo de registro, como se plantea en el apartado de evaluación.

## 4. Visualizador

### Finalidad del rol

Consultar información y avances de los proyectos autorizados, sin modificar registros. Puede servir para seguimiento, supervisión y usuarios que necesitan información pero no realizan captura.

### Pantallas propuestas

Dashboard y fichas de proyectos; núcleos; personas; ORV; padrones; parcelas y unidades; afectaciones y sus detalles; asambleas; actividades; fichas de convenios; trámites RAN y FIFONAFE; documentos y expediente; estado financiero e información de indemnizaciones autorizada; seguimiento; derechos colectivos y reportes; Mapa; Gestión geoespacial en consulta; Cambiar contraseña.

### Acciones y privilegios propuestos

- Buscar, filtrar, ordenar cuando la pantalla lo permita y consultar registros existentes.
- Consultar vigencias, históricos y bajas que la pantalla y su acceso permitan conocer.
- Abrir documentos, descargar archivos autorizados y consultar su historial de versiones.
- Consultar capas, detalles del mapa, importaciones y estados de revisión geoespacial.
- Consultar y exportar reportes autorizados, si se aprueba mantener descargas para este perfil.
- Cambiar únicamente su propia contraseña y cerrar sesión.

### Acciones que no se proponen para este rol

Crear, editar, vincular, dar de baja, reactivar, cargar archivos, subir versiones, guardar decisiones de conciliación o confirmar geometrías. Tampoco administrar usuarios, proyectos, catálogos o auditoría global.

Se propone que no aparezcan formularios de alta como Nuevo proyecto o Nuevo convenio. La información de un convenio existente se consultaría en su ficha. La búsqueda de personas es una consulta; no concede permiso de registrarlas ni de crear relaciones.

## 5. Geógrafo

### Finalidad del rol

Gestionar la cartografía de los proyectos asignados y consultar la información administrativa necesaria para identificar correctamente núcleos, parcelas y destinos.

### Pantallas propuestas

Dashboard y fichas de proyectos; Mapa; Gestión geoespacial; núcleos, parcelas y unidades agrarias; afectaciones; y las pantallas administrativas, documentos, seguimiento y reportes autorizados en modo consulta. Cambiar contraseña estaría disponible para su propia cuenta.

### Acciones y privilegios propuestos

- Cargar los archivos geoespaciales admitidos para trazo, derecho de vía, núcleos y parcelas.
- Revisar previsualizaciones, advertencias y resultados de las importaciones.
- Seleccionar destinos, confirmar o rechazar propuestas e ignorar elementos conforme al flujo disponible.
- Ejecutar nuevas conciliaciones, consultar sus historiales y registrar motivos.
- Confirmar una versión de derecho de vía o finalizar una conciliación cuando se cumplan las validaciones.
- Consultar revisiones geoespaciales y registrar las decisiones Revisado, No aplica o Aplicado que ofrezca el sistema.
- Configurar el sistema de coordenadas donde esté permitido. No modificarlo cuando las reglas del proyecto lo impidan.
- Consultar y descargar documentos autorizados que le ayuden a revisar la cartografía.
- Consultar reportes y cambiar su propia contraseña.

### Acciones que no se proponen para este rol

Administrar usuarios o proyectos, editar catálogos, crear personas, capturar convenios o pagos, cambiar vigencias de ORV, registrar documentos administrativos o subir nuevas versiones documentales.

**Subir un archivo geoespacial y subir un documento son permisos distintos.** El geógrafo puede cargar cartografía en Gestión geoespacial; eso no le concede automáticamente captura en Documentos. Tampoco debe modificar superficies administrativas sólo porque cambie una geometría.

## 6. Matriz propuesta de pantallas y acciones

**Consultar:** ver, buscar y filtrar información autorizada. Las descargas se rigen por la propuesta común y las decisiones pendientes.  
**Capturar:** crear y actualizar mediante las funciones disponibles; no incluye automáticamente bajas, reactivaciones o autorizaciones financieras.  
**Gestionar GIS:** cargar cartografía y realizar las revisiones/decisiones geoespaciales permitidas.  
**Sin acceso:** no se propone mostrar ni habilitar esa función a ese rol.

| Pantalla o conjunto de pantallas | Administrador | Operador | Visualizador | Geógrafo |
|---|---|---|---|---|
| Dashboard / Todos los proyectos | Consultar y exportar | Consultar y exportar | Consultar y exportar | Consultar y exportar |
| Ficha de proyecto | Consultar y administrar proyecto | Consultar; capturar relaciones autorizadas | Consultar | Consultar |
| Nuevo proyecto | Crear | Sin acceso | Sin acceso | Sin acceso |
| Usuarios y permisos | Administrar cuentas y asignaciones | Sin acceso | Sin acceso | Sin acceso |
| Catálogos operativos, pantalla de administración | Administrar | Usar opciones en formularios; consulta dedicada por evaluar | Consulta dedicada por evaluar | Usar opciones en consultas; consulta dedicada por evaluar |
| Auditoría | Consultar y filtrar; no editar historial | Sin acceso global | Sin acceso global | Sin acceso global |
| Núcleo agrario | Ficha general y relación con proyecto | Capturar relación con proyecto; consultar ficha general | Consultar | Consultar; geometría mediante funciones GIS |
| Personas | Consultar, capturar, baja y reactivación | Consultar y capturar | Consultar | Consultar |
| ORV | Consultar, capturar, finalizar, baja y reactivación | Consultar, capturar y finalizar participación | Consultar | Consultar |
| Padrones | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| Parcela | Capturar información y gestionar geometría disponible | Capturar información administrativa | Consultar | Consultar y gestionar geometría disponible |
| Unidad agraria | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| Afectación / Detalle de afectación | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| Asamblea | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| Actividades de campo | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| Nuevo convenio | Crear | Crear | Sin acceso al alta | Sin acceso al alta |
| Ficha de convenio | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| Trámite RAN / Ficha RAN | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| FIFONAFE / Ficha FIFONAFE | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| Documentos, incluidos los de actividades | Consultar, registrar, vincular y subir versiones | Consultar, registrar, vincular y subir versiones | Consultar y descargar | Consultar y descargar |
| Expediente documental | Consultar y gestionar requisitos/documentos | Consultar y gestionar requisitos/documentos | Consultar | Consultar |
| Indemnización | Consultar y capturar donde esté disponible | Consultar y capturar donde esté disponible | Consultar lo autorizado | Consultar lo autorizado |
| Estado financiero | Consultar; acceso a captura donde se ofrezca | Consultar; acceso a captura donde se ofrezca | Consultar lo autorizado | Consultar lo autorizado |
| Seguimiento | Consultar y capturar | Consultar y capturar | Consultar | Consultar |
| Derechos colectivos / Reportes colectivos | Consultar y exportar | Consultar y exportar | Consultar y exportar | Consultar y exportar |
| Reportes de convenios | Consultar y exportar | Consultar y exportar | Consultar y exportar | Consultar y exportar |
| Reportes FIFONAFE | Consultar y exportar | Consultar y exportar | Consultar y exportar | Consultar y exportar |
| Reporte de actividades por periodo | Consultar y exportar | Consultar y exportar | Consultar y exportar | Consultar y exportar |
| Mapa | Consultar capas y detalles | Consultar capas y detalles | Consultar capas y detalles | Consultar capas y detalles |
| Gestión geoespacial | Consultar y gestionar GIS | Consultar, sin guardar cambios GIS | Consultar, sin guardar cambios GIS | Consultar y gestionar GIS |
| Cambiar contraseña | Sólo contraseña propia desde esta pantalla | Contraseña propia | Contraseña propia | Contraseña propia |
| Cerrar sesión | Sesión propia | Sesión propia | Sesión propia | Sesión propia |

Las pantallas agrupadas conservan las mismas restricciones en sus accesos desde otros módulos. Por ejemplo, abrir Documentos desde una actividad no convierte al visualizador en capturista. Consultar un catálogo dentro de un formulario tampoco concede permiso para modificar sus opciones.

## 7. Propuesta de presentación de los menús

Se propone que todos tengan accesos claros a sus proyectos, mapa, reportes y configuración personal. En el menú del nombre de usuario, todos verían Cambiar contraseña y Cerrar sesión. Usuarios y permisos se mostraría únicamente al administrador, en los lugares donde actualmente se ofrece ese acceso.

El administrador tendría el grupo Administración con Usuarios, Catálogos operativos y Auditoría. El operador vería las acciones de captura dentro del proyecto y del núcleo. El geógrafo tendría un acceso visible a Gestión geoespacial. Visualizador y operador podrían consultar esa pantalla, pero sin controles para cargar, modificar o confirmar cartografía.

Se sugiere ocultar acciones que una cuenta nunca puede ejecutar, en vez de ofrecer un botón que siempre terminará en rechazo. Cuando una acción esté temporalmente impedida por el estado del registro, conviene conservar una explicación clara del motivo. La revisión de menús sería un cambio posterior si la propuesta se aprueba; no se aplicó con este documento.

## 8. Qué coincide con la base actual y qué debe decidirse

En el código integrado revisado ya se distinguen los cuatro roles. La lectura del dominio, documentos y reportes contempla los cuatro; la captura administrativa y documental contempla administrador/operador; la modificación GIS contempla administrador/geógrafo. Usuarios y auditoría requieren administrador. Las bajas/reactivaciones de personas e integrantes de ORV también se reservan a administración. El cambio de contraseña propia depende de la sesión autenticada.

Estas reglas son una base, no un permiso universal sobre todo registro. El sistema comprueba además acceso al proyecto, estado del registro y condiciones de cada operación. La disponibilidad de un permiso en el servidor tampoco asegura que exista un botón para todas las operaciones posibles.

Las siguientes decisiones se proponen para discusión. **No están aprobadas ni implementadas por este escrito.**

| Tema por evaluar | Propuesta inicial | Decisión que debe tomar el área usuaria |
|---|---|---|
| Lectura de Gestión geoespacial | Permitir consulta a operador y visualizador; cambios sólo admin/geógrafo. | ¿Les aporta revisar cargas e historial, o sólo necesitan el mapa? |
| Descargas y exportaciones | Permitirlas sobre datos autorizados a los cuatro roles. | ¿Algún perfil debe consultar sin descargar? Esa separación requeriría revisar implementación. |
| Información financiera | Mantener lectura según alcance actual; captura administrativa para admin/operador. | ¿Se necesita restringir montos o separar captura de revisión financiera? |
| Documentos para geógrafos | Mantener consulta y descarga; carga administrativa para admin/operador. | ¿Hay evidencia cartográfica documental que deban subir? No confundirla con archivos GIS. |
| Captura y confirmación GIS | Mantener ambas en admin/geógrafo, como base actual. | ¿La persona que confirma debe ser distinta de quien carga? Esa separación no se presume existente. |
| Bajas operativas del operador | Revisar por registro, manteniendo las exclusivas de administrador. | ¿Qué relaciones puede dar de baja directamente y cuáles deben escalarse? |
| Catálogos en el menú | Administración de catálogos sólo para admin; otros usan sus opciones en formularios. | ¿Se necesita una pantalla dedicada de consulta para otros roles? El servidor ya permite ciertas lecturas. |
| Nuevos proyectos y ficha general de núcleos | Mantener creación/edición general en admin; vinculación de núcleos existentes en admin/operador. | ¿Se necesita delegar alguna función? Requeriría revisar permisos y flujo. |
| Auditoría para responsables de área | Mantener auditoría global sólo para admin. | ¿Hace falta una consulta limitada por proyecto para otro perfil? No se ofrece como capacidad actual. |
| Alcance del administrador | Definir quién requiere gestión institucional y quién sólo apoyo operativo. | ¿Basta el modelo actual de roles y asignaciones o se necesita otro alcance? |

## 9. Ejemplos para discutir con los usuarios

**Cambiar contraseña:** un visualizador puede cambiar la suya desde su menú. No puede cambiar la de un compañero. Un administrador atiende el restablecimiento de otra cuenta mediante administración, sin necesitar conocer su contraseña anterior.

**Subir cartografía:** un geógrafo puede cargar el archivo del derecho de vía en un proyecto autorizado, revisar el resultado y confirmarlo conforme al flujo. Un operador puede consultar ese proceso, pero no guardar cambios GIS.

**Documentar una actividad:** un operador puede registrar una actividad y adjuntarle un documento mediante el gestor. Un geógrafo o visualizador puede consultar el documento autorizado, sin recibir por ello permiso de captura documental.

**Corregir un integrante:** un operador puede finalizar su participación con la fecha correspondiente. Dar de baja o reactivar el registro administrativo quedaría a cargo del administrador. Reactivar no equivale a iniciar una nueva participación.

**Registrar un pago:** capturar un registro de pago no demuestra que el usuario tenga facultades institucionales para autorizarlo. Si se necesita aprobación por otra persona, habrá que definir ese proceso antes de solicitar su implementación.

## 10. Formato para acordar ajustes

Para cada cambio propuesto, registrar:

| Pantalla / acción | Rol | ¿Consultar, capturar, administrar o sin acceso? | Alcance de proyectos | Motivo | Responsable de validar | Decisión |
|---|---|---|---|---|---|---|
| Ejemplo: confirmar cartografía | Geógrafo | Gestionar GIS | Proyectos asignados | Función del área geoespacial | Por definir | Pendiente |
| | | | | | | |

Una vez revisado el documento, el área responsable debe indicar qué se acepta, qué se restringe y qué requiere desarrollo. Después se ajustan menús, formularios y permisos del servidor de manera consistente, y se comprueban con cuentas reales de cada rol usando los manuales de testeo.

## Referencia de elaboración

Se revisaron los archivos locales `backend/app/routers/domain.py`, `documents.py`, `geospatial_imports.py`, `users.py`, `audit.py` y `authentication.py`, además de la propuesta del 8 de octubre. Esta entrega únicamente agrega documentación: no cambia roles, cuentas, asignaciones, datos ni código de la aplicación.
