# Propuesta de roles y pantallas SSALFER

Fecha: 8 de octubre de 2026. Propuesta demostrativa para capacitación y validación con usuarios. No crea roles, permisos ni asignaciones nuevas.

Los cuatro roles reales del backend son **admin**, **operador**, **visualizador** y **geografo**. Además del rol, el backend comprueba el acceso al proyecto y a cada registro. Ver una pantalla no concede permiso para modificar sus datos.

| Rol real | Nombre para capacitación | Uso propuesto |
|---|---|---|
| admin | Administración | Configuración, usuarios, asignaciones de proyectos, auditoría, operación y cartografía. |
| operador | Operación y captura | Capturar y actualizar información administrativa y documental en sus proyectos autorizados. Consultar cartografía. |
| visualizador | Consulta y seguimiento | Consultar información, documentos, mapas y reportes autorizados. Sin captura. |
| geografo | Geografía | Cargar, revisar, conciliar y confirmar cartografía. Consultar información administrativa y documentos autorizados. |

## Distribución demostrativa de pantallas

**C** = consulta; **G** = gestión permitida por cada operación del backend; **—** = no propuesta para ese rol.

| Pantallas o módulo | admin | operador | visualizador | geografo |
|---|---|---|---|---|
| Dashboard y ficha de proyecto (`dashboard`, `fichaProyecto`) | C/G | C | C | C |
| Crear proyecto (`nuevoProyecto`) | G | — | — | — |
| Usuarios y auditoría (`usuarios`, `auditoria`) | G/C | — | — | — |
| Catálogos operativos (`catalogosOperativos`) | G | C | C | C |
| Núcleo agrario (`nucleoAgrario`) | C/G | C y captura de relaciones autorizadas | C | C |
| ORV (`orv`) | C/G; baja/reactivación administrativa | C/G de participaciones | C | C |
| Personas y padrones (`persona`, `padrones`) | C/G | C/G | C | C |
| Parcelas y unidades agrarias (`parcela`, `unidadAgraria`) | C/G | C/G administrativo | C | C; geometría según API |
| Afectaciones (`afectacion`, `detalleAfectacion`) | C/G | C/G | C | C |
| Convenios (`nuevoConvenio`, `fichaConvenio`) | C/G | C/G | C de existentes | C de existentes |
| Asambleas y actividades (`asamblea`, `actividades`) | C/G | C/G | C | C |
| Trámites (`tramiteRan`, `fichaRan`, `fifonafe`, `fichaFifonafe`) | C/G | C/G | C | C |
| Documentos y expediente (`documentos`, `expedienteDocumental`) | C/G | C/G | C/descarga | C/descarga |
| Indemnización y estado financiero (`indemnizacion`, `estadoFinanciero`) | C/G según operación | C/G según operación | C | C |
| Seguimiento (`seguimiento`) | C/G | C/G | C | C |
| Derechos colectivos y reportes (`derechosColectivos`, `reportesColectivos`, `reportesConvenios`, `reportesFifonafe`, `reporteActividadesPeriodo`) | C | C | C | C |
| Mapa (`mapa`) | C | C | C | C |
| Gestión cartográfica (`gestionGeoespacial`) | C/G | C | C | C/G |
| Cambiar contraseña (`cambiarContrasena`) | Cuenta propia | Cuenta propia | Cuenta propia | Cuenta propia |

Los formularios de alta se muestran como acciones de captura; para consulta se debe entrar a las fichas de registros existentes. Algunas pantallas agrupan operaciones con permisos diferentes. Esta tabla no reemplaza la autorización del servidor ni promete que todas las acciones de un módulo estén disponibles para un rol.

## Protección aplicada

Las 35 pantallas privadas comprueban la sesión antes de mostrar contenido y antes de enviar consultas de negocio. Sin sesión, redirigen al inicio de sesión y conservan la pantalla solicitada como destino seguro del acceso. La pantalla pública es `Index.html`. Un error de conexión al verificar la sesión ofrece reintento y no muestra los datos privados. El retorno acepta únicamente rutas locales del frontend. Las APIs siguen siendo la barrera de autorización para cada dato y operación.

## Propuesta para validación con usuarios

1. Definir qué personas tendrán cada uno de los cuatro roles existentes.
2. Asignar sus proyectos desde administración; el rol por sí solo no concede acceso a todos los proyectos.
3. Capacitar por tareas: consulta, captura, documentación, revisión cartográfica y administración.
4. Validar con cuentas reales de cada rol el alcance autorizado antes de producción. Las simulaciones de frontend no sustituyen esa validación de cuentas y asignaciones.

Fuentes revisadas: OpenAPI QA schema 028 y `backend/app/routers/domain.py`, `documents.py`, `geospatial_imports.py`, `reporting.py`, `users.py`, `audit.py`. No se modificaron esos archivos.
