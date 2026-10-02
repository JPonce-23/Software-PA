# Prompt para inspeccionar SSALFER después de la ronda 3

Continúa la inspección del frontend de SSALFER en `C:\Proyectos\Software-PA-integracion-mq`. Lee primero `git status`, `git log -2` y estos documentos dentro de `frontend-ssalfer/deploy/`:

- `QA-UX-2026-10-01.md` y `QA-UX-2026-10-02-RONDA2.md`.
- `QA-UX-2026-10-03-RONDA3.md`, que contiene el detalle y la tabla de desplazamiento por pantalla.
- `BLOQUEOS-BACKEND-2026-10-03-RONDA3.md` y los informes de backend de las rondas 1 y 2.
- `inventario-controles-ronda3.json`, con controles visibles después de cargar las páginas.

Los nombres con 2026-10-03 identifican esta ronda; las pruebas descritas se realizaron el 02-10-2026. La carpeta es un worktree: no cambies la otra carpeta `C:\Proyectos\Software-PA`.

## Respaldo y alcance

Las rondas 1 y 2 quedaron respaldadas en GitHub: rama `feature/integracion-mq-deploy`, commit `f8b9e86`, 77 archivos. La ronda 3 corresponde al commit local posterior; identifica su hash con Git. No hagas push de este segundo commit sin autorización nueva. No hay permiso para desplegar al servidor, hacer merge, force push, reset o restaurar archivos.

Sólo modifica `frontend-ssalfer/` si la inspección encuentra defectos de esta ronda. No cambies backend, esquemas, migraciones, reglas de negocio, roles ni geografía. **Omite Derechos colectivos**: el usuario decidió dejar esa parte fuera mientras continúa el trabajo del backend. No retires su tarjeta ni supongas que no existe backend.

No guardes credenciales, cookies, tokens ni datos personales en archivos o capturas. Usa la sesión QA o variables de entorno para una cuenta autorizada. No escribas datos de negocio durante las pruebas de lectura. Si necesitas validar persistencia, presenta primero el caso y los fixtures concretos para autorización.

## Cambios ya realizados que debes preservar

Rondas 1 y 2: selectores humanos y relaciones contextuales de Seguimiento y Expediente, documentos RAN/FIFONAFE, nombres/fechas de reportes, navegación Volver, tarjetas de reportes, modales/toasts y validaciones. Se corrigieron el falso éxito al cancelar avalúo, el acceso a parcela nula en Unidad Agraria, el PATCH mínimo de eventos FIFONAFE y sus validaciones de ordinal/evidencia. No reimplementes estas funciones.

Ronda 3:

1. `js/utils/ui.js` y `styles/shared.css`: tren SVG propio con tres volutas, ruedas y «Cargando...», en pantalla completa o compacto. Inicio tras 300 ms, mínimo visible de 400 ms, contador por destino, liberación idempotente, accesibilidad y movimiento reducido. Sin recursos externos ni cambios al tren oculto del dashboard.
2. `js/api/cliente.js`: activación única en `request`, limpieza con `finally`, opciones `silencioso`, `carga`, `signal`, `tipoRespuesta: "blob"`. Comprobación automática de sesión silenciosa en `js/api/auth.js`.
3. Exportaciones CSV de dashboard/Estado financiero pasan por el cliente común usando sus rutas y filtros existentes. Los CSV de reportes que usan datos ya cargados siguen siendo locales.
4. `SSALFER_UI.desplazarA` y el nuevo `js/utils/experiencia.js`: destinos explícitos, espera de consultas/render, foco en título o campo, margen de encabezado y menú móvil, cancelación por una interacción posterior y cero scroll inicial. Regreso al listado/resumen cuando se cierra el formulario; los modales conservan su comportamiento.
5. Sustitución de desplazamientos dispersos en Actividades, Afectación, Asamblea, Detalle de afectación, Expediente, Convenio, RAN, FIFONAFE, Indemnización, ORV, Padrones, Seguimiento y Unidad Agraria. Se completaron paneles anidados, comparecientes, convocatorias, eventos, consulta ORV → integrantes y resultados de reportes.
6. Dependencias compartidas incorporadas a login/dashboard y configuración de UX cargada en las 29 páginas no geográficas. Backend y relaciones de datos intactos.
7. Pruebas `qa-ronda3.cjs`, `qa-inventario-ronda3.cjs`, inventario de controles y tres capturas QA. `qa-ronda2.cjs` permite `QA_SIN_CAPTURAS=1` para no sobrescribir evidencias históricas.

## Inspección solicitada

Usa QA local `http://127.0.0.1:5184/`, proyecto 4 y proyecto-núcleo 150. Comprueba:

- Tren durante carga inicial y consulta/exportación larga; sólo un indicador por destino ante peticiones simultáneas. Sin parpadeo, sin retenerse ante 404, error de red o cancelación. Sesión automática silenciosa.
- Carga compacta en ORV, selectores de Seguimiento/Expediente y filtros dependientes de Auditoría/Reportes. El resto de la pantalla debe seguir utilizable.
- ORV → integrantes: esperar datos/estado vacío, desplazar y enfocar. Repetir Editar/Crear/Cancelar y los paneles de la tabla del informe. No desplazar al cargar una URL ni quitar el foco a alguien que ya continuó interactuando.
- A 390×844, el título enfocado queda debajo del menú fijo. No dar por resuelto el diseño general del menú sólo porque se corrigió el margen de scroll.
- `prefers-reduced-motion`, teclado y lector de pantalla manual. Probar también el perfil «3G rápida» de DevTools: la automatización sólo añadió 450 ms por petición real, sin simular su ancho de banda completo.
- Los errores de validación no deben devolver al listado como si se hubiera guardado. El retorno de submit sólo tiene una prueba DOM aislada y revisión de ramas de éxito; la persistencia real sigue pendiente de prueba autorizada.

Ejecuta las pruebas con Playwright disponible mediante `QA_PLAYWRIGHT` y credenciales en `QA_USER`/`QA_PASSWORD`. No pongas sus valores en el repositorio. Las pruebas existentes abortan escrituras de negocio; conserva esa protección. Si hay timeouts, identifica la ruta/espera y repite el tramo aislado antes de atribuirlo al backend.

Valida sintaxis JS, UTF-8 sin BOM y `git diff --check`. Si hay que refrescar QA, reconstruye y recrea únicamente `frontend_ssalfer` con la combinación de Compose ya usada; no detengas ni recrees servicios de backend/BD. No borres `.qa-backups/`.

## Pendientes que debes reportar con evidencia

Revalida búsqueda general de personas, observaciones/reactivación de catálogos, ciclo de asignaciones usuario-proyecto y mensajes 409 de FIFONAFE/Afectación frente al backend vigente. **Observaciones de eventos FIFONAFE sí estaba soportado**: no reutilices el diagnóstico incorrecto de que no se guarda. No confundas datos QA vacíos con endpoints faltantes.

El inventario encontró enlaces `#` en Todos los proyectos y en Núcleo agrario de FIFONAFE; el origen de RAN tiene handler funcional aunque conserva `#`. Reporta también textos técnicos, edición general de trámite RAN oculta, derivados de convenio ocultos, fórmula financiera pendiente y diseño móvil. Derechos colectivos y geografía siguen fuera de esta revisión.

Entrega hallazgos priorizados con pasos, archivo, evidencia, impacto y clasificación frontend/backend/decisión/QA pendiente. Separa comprobado, corregido y no probado. No declares «listo para producción»: el máximo estado es **listo para QA local manual** hasta la inspección del usuario.
