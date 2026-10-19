# Accesos por rol — 19/10/2026

Esta versión aplica las aclaraciones posteriores del usuario; sustituye la propuesta inicial. Superadmin queda pendiente.

## Reglas aplicadas
- Administrador: todas las pantallas y acciones.
- Operador: captura administrativa en proyectos asignados y todos sus núcleos. No puede entrar en Gestión geoespacial ni modificar cartografía.
- Visualizador: consulta de todos los proyectos activos; no captura ni modifica registros. No entra en Gestión geoespacial ni formularios exclusivos de alta.
- Geógrafo: todos los proyectos activos, mapa, núcleos, parcelas y Gestión geoespacial. Puede gestionar archivos geográficos, sin captura administrativa. Dashboard y ficha de proyecto permiten navegar; las demás pantallas administrativas no están habilitadas.
- Todos pueden cambiar su contraseña y cerrar sesión.
- Solo los operadores aparecen como candidatos para nuevas asignaciones de proyectos; el servidor también rechaza asignar otro rol. No se alteraron asignaciones existentes ni cuentas.

## Correcciones
El servidor exigía asignación a todos los usuarios no administradores: ahora geógrafo y visualizador consultan todos los proyectos activos. El operador sigue limitado a sus asignaciones. Su acceso incluye todos los núcleos del proyecto, sin nuevas asignaciones por núcleo.

Los permisos de captura y cartografía del servidor permanecen separados. La política de pantallas se aplica con data-role y la protección compartida; los controles y enlaces dinámicos también se filtran. Esta restricción visual no sustituye los permisos de operaciones del servidor.

El ingreso revisa el destino solicitado: si la cuenta no tiene acceso a esa pantalla, llega al dashboard. El operador sin proyectos ve una indicación para solicitar asignación, en lugar de una invitación a crear un proyecto. No se reprodujo un bloqueo general del dashboard en las pruebas de navegación.

## Matriz de pantallas
| Pantalla | Admin | Operador | Visualizador | Geógrafo |
|---|---|---|---|---|
| dashboard.html | Acceso | Acceso | Acceso | Acceso |
| actividades.html | Acceso | Acceso | Acceso | Sin acceso |
| afectacion.html | Acceso | Acceso | Acceso | Sin acceso |
| asamblea.html | Acceso | Acceso | Acceso | Sin acceso |
| auditoria.html | Acceso | Sin acceso | Sin acceso | Sin acceso |
| cambiarContrasena.html | Acceso | Acceso | Acceso | Acceso |
| catalogosOperativos.html | Acceso | Sin acceso | Sin acceso | Sin acceso |
| derechosColectivos.html | Acceso | Acceso | Acceso | Sin acceso |
| detalleAfectacion.html | Acceso | Acceso | Acceso | Sin acceso |
| documentos.html | Acceso | Acceso | Acceso | Sin acceso |
| estadoFinanciero.html | Acceso | Acceso | Acceso | Sin acceso |
| expedienteDocumental.html | Acceso | Acceso | Acceso | Sin acceso |
| fichaConvenio.html | Acceso | Acceso | Acceso | Sin acceso |
| fichaFifonafe.html | Acceso | Acceso | Acceso | Sin acceso |
| fichaProyecto.html | Acceso | Acceso | Acceso | Acceso |
| fichaRan.html | Acceso | Acceso | Acceso | Sin acceso |
| fifonafe.html | Acceso | Acceso | Acceso | Sin acceso |
| gestionGeoespacial.html | Acceso | Sin acceso | Sin acceso | Acceso |
| indemnizacion.html | Acceso | Acceso | Acceso | Sin acceso |
| mapa.html | Acceso | Acceso | Acceso | Acceso |
| nucleoAgrario.html | Acceso | Acceso | Acceso | Acceso |
| nuevoConvenio.html | Acceso | Acceso | Sin acceso | Sin acceso |
| nuevoProyecto.html | Acceso | Sin acceso | Sin acceso | Sin acceso |
| orv.html | Acceso | Acceso | Acceso | Sin acceso |
| padrones.html | Acceso | Acceso | Acceso | Sin acceso |
| parcela.html | Acceso | Acceso | Acceso | Acceso |
| persona.html | Acceso | Acceso | Acceso | Sin acceso |
| reporteActividadesPeriodo.html | Acceso | Acceso | Acceso | Sin acceso |
| reportesColectivos.html | Acceso | Acceso | Acceso | Sin acceso |
| reportesConvenios.html | Acceso | Acceso | Acceso | Sin acceso |
| reportesFifonafe.html | Acceso | Acceso | Acceso | Sin acceso |
| seguimiento.html | Acceso | Acceso | Acceso | Sin acceso |
| tramiteRan.html | Acceso | Acceso | Sin acceso | Sin acceso |
| unidadAgraria.html | Acceso | Acceso | Acceso | Sin acceso |
| usuarios.html | Acceso | Sin acceso | Sin acceso | Sin acceso |

## Validación de esta revisión
- 199 comprobaciones de las 35 pantallas, cuatro roles y un rol desconocido; HTML y protección reales, consultas simuladas.
- 8 recorridos de ingreso con sesión nueva o previa: retorno permitido o dashboard según el rol.
- Ficha de proyecto con scripts completos para los cuatro roles: vincular núcleo solo admin/operador; alta excepcional solo admin.
- 31 comprobaciones del servidor: consulta en transacción de solo lectura sobre QA, acceso a núcleos asignados y rechazo de asignaciones a otros roles con persistencia simulada.
- No se realizaron capturas ni cambios en datos reales. Estas pruebas no equivalen a probar todas las operaciones de negocio con cuentas reales.

Scripts: qa-roles-2026-10-19.cjs, qa-roles-login-2026-10-19.cjs, qa-roles-proyecto-2026-10-19.cjs y backend/qa_roles_readonly.py. Evidencia de matriz y capturas: outputs/roles-2026-10-19/.

## Prueba manual
1. Cerrar sesión, recargar con Ctrl+F5 e ingresar con cada cuenta.
2. Ruta: Dashboard → Todos los proyectos. Geógrafo y visualizador ven los activos. Operador solo los asignados.
3. Ruta como administrador: Proyecto → Usuarios responsables → Asignar operador. Solo deben aparecer operadores activos; una asignación da acceso a todos los núcleos del proyecto.
4. Ruta: Proyecto → Núcleos vinculados. El operador asignado puede capturar; visualizador y geógrafo solo consultan datos administrativos.
5. Ruta: Gestión geoespacial → Seleccionar proyecto. Solo admin/geógrafo pueden entrar; comprobar también la URL directa con operador y visualizador.
6. Ruta: Mapa → Seleccionar proyecto. Consultar cartografía según el alcance del rol.
7. Ruta: Menú del usuario → Cambiar contraseña. Disponible para todos.

Cambios disponibles en el contenedor local de integración. Sin commit ni push.
