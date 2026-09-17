document.addEventListener(
    "DOMContentLoaded",
    async () => {
        "use strict";

        const parametros =
            new URLSearchParams(
                window.location.search
            );

        const idProyectoNucleo =
            Number(
                parametros.get(
                    "id_proyecto_nucleo"
                )
            );

        const tipoInicial =
            parametros.get(
                "tipo_actividad"
            );

        const elementos = {
            main:
                document.querySelector(
                    "main[data-proyecto-nucleo-id]"
                ),

            btnVolver:
                document.getElementById(
                    "btnVolver"
                ),

            btnNuevaActividad:
                document.getElementById(
                    "btnNuevaActividad"
                ),

            totalActividades:
                document.getElementById(
                    "totalActividades"
                ),

            totalSensibilizaciones:
                document.getElementById(
                    "totalSensibilizaciones"
                ),

            totalCaminamientos:
                document.getElementById(
                    "totalCaminamientos"
                ),

            ultimaActividad:
                document.getElementById(
                    "ultimaActividad"
                ),

            filtroTipo:
                document.getElementById(
                    "filtroTipo"
                ),

            btnLimpiarFiltro:
                document.getElementById(
                    "btnLimpiarFiltro"
                ),

            actividadesTabla:
                document.getElementById(
                    "actividadesTabla"
                ),

            formularioActividad:
                document.getElementById(
                    "formularioActividad"
                ),

            formActividad:
                document.getElementById(
                    "formActividad"
                ),

            tipoActividad:
                document.getElementById(
                    "tipoActividad"
                ),

            contextoActividad:
                document.getElementById(
                    "contextoActividad"
                ),

            afectacionActividad:
                document.getElementById(
                    "afectacionActividad"
                ),

            tipoCop:
                document.getElementById(
                    "tipoCop"
                ),

            fechaProgramada:
                document.getElementById(
                    "fechaProgramada"
                ),

            fechaRealizada:
                document.getElementById(
                    "fechaRealizada"
                ),

            responsable:
                document.getElementById(
                    "responsable"
                ),

            resultado:
                document.getElementById(
                    "resultado"
                ),

            mensajeFormulario:
                document.getElementById(
                    "mensajeFormulario"
                ),

            btnCancelarActividad:
                document.getElementById(
                    "btnCancelarActividad"
                )
        };

        if (
            !Number.isInteger(
                idProyectoNucleo
            ) ||
            idProyectoNucleo <= 0
        ) {
            window.ClienteAPI
                .mostrarErrorAPI(
                    new Error(
                        "No se puede abrir Actividades porque falta un id_proyecto_nucleo válido."
                    )
                );

            return;
        }

        if (elementos.main) {
            elementos.main.dataset
                .proyectoNucleoId =
                String(
                    idProyectoNucleo
                );
        }

        let actividades = [];
        let idActividadEdicion = null;
        let puedeCapturar = false;

        /* =====================================================
                            UTILIDADES
        ====================================================== */

        function escaparHTML(valor) {
            return String(
                valor ?? ""
            )
                .replaceAll(
                    "&",
                    "&amp;"
                )
                .replaceAll(
                    "<",
                    "&lt;"
                )
                .replaceAll(
                    ">",
                    "&gt;"
                )
                .replaceAll(
                    '"',
                    "&quot;"
                )
                .replaceAll(
                    "'",
                    "&#039;"
                );
        }

        function fechaVisual(
            valor
        ) {
            if (!valor) {
                return "—";
            }

            const partes =
                String(valor)
                    .split("-");

            return partes.length === 3
                ? `${partes[2]}/${partes[1]}/${partes[0]}`
                : String(valor);
        }

        function etiquetaTipo(
            valor
        ) {
            return {
                sensibilizacion:
                    "Sensibilización",

                caminamiento:
                    "Caminamiento"
            }[valor] ||
            valor ||
            "—";
        }

        function etiquetaContexto(
            valor
        ) {
            return {
                general:
                    "General",

                superficie_adicional:
                    "Superficie adicional",

                obras_complementarias:
                    "Obras complementarias",

                transversal:
                    "Transversal",

                otro:
                    "Otro"
            }[valor] ||
            valor ||
            "—";
        }

        function mostrarMensaje(
            texto,
            esError = false
        ) {
            if (
                !elementos
                    .mensajeFormulario
            ) {
                return;
            }

            elementos
                .mensajeFormulario
                .textContent =
                texto || "";

            elementos
                .mensajeFormulario
                .classList
                .toggle(
                    "error",
                    esError
                );
        }

        /* =====================================================
                             PERMISOS
        ====================================================== */

        async function cargarRol() {
            try {
                const sesion =
                    await window.AuthAPI
                        .obtenerSesionActual();

                const rol =
                    sesion?.user?.rol;

                puedeCapturar =
                    rol === "admin" ||
                    rol === "operador";

            } catch {
                puedeCapturar =
                    false;
            }

            if (
                elementos
                    .btnNuevaActividad
            ) {
                elementos
                    .btnNuevaActividad
                    .hidden =
                    !puedeCapturar;
            }
        }

        /* =====================================================
                             CONTEXTO
        ====================================================== */

        async function cargarContexto() {
            try {
                const contexto =
                    await window.NucleosAPI
                        .obtenerProyectoNucleo(
                            idProyectoNucleo
                        );

                document.title =
                    `Actividades | ${
                        contexto.nombre_nucleo ||
                        "Núcleo agrario"
                    } | SSALFER`;

            } catch (error) {
                window.ClienteAPI
                    .mostrarErrorAPI(
                        error
                    );
            }
        }

        /* =====================================================
                            CATÁLOGOS
        ====================================================== */

        async function cargarCatalogos() {
            try {
                const opciones =
                    await window.CatalogosAPI
                        .obtenerOperativo(
                            "tipo_cop_operativo"
                        );

                elementos.tipoCop.innerHTML =
                    '<option value="">Selecciona una opción</option>';

                (
                    Array.isArray(
                        opciones
                    )
                        ? opciones
                        : []
                ).forEach(
                    opcion => {
                        const id =
                            Number(
                                opcion
                                    .id_catalogo_opcion
                            );

                        const nombre =
                            opcion.nombre ||
                            opcion.codigo ||
                            `Opción ${id}`;

                        const option =
                            document
                                .createElement(
                                    "option"
                                );

                        option.value =
                            String(id);

                        option.textContent =
                            nombre;

                        elementos
                            .tipoCop
                            .appendChild(
                                option
                            );
                    }
                );

            } catch (error) {
                window.ClienteAPI
                    .mostrarErrorAPI(
                        error
                    );
            }
        }

        /* =====================================================
                         AFECTACIONES
        ====================================================== */

        async function cargarAfectaciones() {
            try {
                const afectaciones =
                    await window.AfectacionesAPI
                        .listarPorProyectoNucleo(
                            idProyectoNucleo
                        );

                elementos
                    .afectacionActividad
                    .innerHTML =
                    '<option value="">Actividad general del núcleo</option>';

                (
                    Array.isArray(
                        afectaciones
                    )
                        ? afectaciones
                        : []
                ).forEach(
                    afectacion => {
                        const option =
                            document
                                .createElement(
                                    "option"
                                );

                        option.value =
                            String(
                                afectacion
                                    .id_afectacion
                            );

                        option.textContent =
                            `AF-${String(
                                afectacion
                                    .id_afectacion
                            ).padStart(
                                3,
                                "0"
                            )} · ${
                                afectacion
                                    .tipo_afectacion ||
                                "afectación"
                            }`;

                        elementos
                            .afectacionActividad
                            .appendChild(
                                option
                            );
                    }
                );

            } catch (error) {
                window.ClienteAPI
                    .mostrarErrorAPI(
                        error
                    );
            }
        }

        /* =====================================================
                             RESUMEN
        ====================================================== */

        function actualizarResumen() {
            const total =
                actividades.length;

            const sensibilizaciones =
                actividades.filter(
                    item =>
                        item.tipo_actividad ===
                        "sensibilizacion"
                ).length;

            const caminamientos =
                actividades.filter(
                    item =>
                        item.tipo_actividad ===
                        "caminamiento"
                ).length;

            const fechas =
                actividades
                    .map(
                        item =>
                            item.fecha_realizada ||
                            item.fecha_programada
                    )
                    .filter(Boolean)
                    .sort();

            elementos
                .totalActividades
                .textContent =
                String(total);

            elementos
                .totalSensibilizaciones
                .textContent =
                String(
                    sensibilizaciones
                );

            elementos
                .totalCaminamientos
                .textContent =
                String(
                    caminamientos
                );

            elementos
                .ultimaActividad
                .textContent =
                fechas.length
                    ? fechaVisual(
                        fechas[
                            fechas.length - 1
                        ]
                    )
                    : "—";
        }

        /* =====================================================
                             TABLA
        ====================================================== */

        function actividadesFiltradas() {
            const filtro =
                elementos
                    .filtroTipo
                    .value;

            return filtro
                ? actividades.filter(
                    item =>
                        item.tipo_actividad ===
                        filtro
                )
                : actividades;
        }

        function renderTabla() {
            const lista =
                actividadesFiltradas();

            elementos
                .actividadesTabla
                .innerHTML =
                "";

            if (!lista.length) {
                elementos
                    .actividadesTabla
                    .innerHTML = `
                        <tr>
                            <td
                                colspan="7"
                                class="tabla-vacia">

                                No hay actividades registradas.

                            </td>
                        </tr>
                    `;

                return;
            }

            lista
                .slice()
                .sort(
                    (
                        a,
                        b
                    ) =>
                        String(
                            b.fecha_realizada ||
                            b.fecha_programada ||
                            ""
                        ).localeCompare(
                            String(
                                a.fecha_realizada ||
                                a.fecha_programada ||
                                ""
                            )
                        )
                )
                .forEach(
                    actividad => {
                        const fila =
                            document
                                .createElement(
                                    "tr"
                                );

                        fila.innerHTML = `
                            <td>
                                ${escaparHTML(
                                    fechaVisual(
                                        actividad.fecha_realizada ||
                                        actividad.fecha_programada
                                    )
                                )}
                            </td>

                            <td>
                                ${escaparHTML(
                                    etiquetaTipo(
                                        actividad.tipo_actividad
                                    )
                                )}
                            </td>

                            <td>
                                ${escaparHTML(
                                    etiquetaContexto(
                                        actividad.contexto_actividad
                                    )
                                )}
                            </td>

                            <td>
                                ${
                                    actividad.id_afectacion
                                        ? `AF-${String(
                                            actividad.id_afectacion
                                        ).padStart(
                                            3,
                                            "0"
                                        )}`
                                        : "General"
                                }
                            </td>

                            <td>
                                ${escaparHTML(
                                    actividad.responsable ||
                                    "—"
                                )}
                            </td>

                            <td>
                                ${escaparHTML(
                                    actividad.resultado ||
                                    "—"
                                )}
                            </td>

                            <td>
                                ${
                                    puedeCapturar
                                        ? `
                                            <button
                                                type="button"
                                                class="btn-tabla"
                                                data-editar-actividad="${actividad.id_actividad}"
                                                title="Editar actividad">

                                                <i class="bi bi-pencil"></i>

                                            </button>
                                        `
                                        : "—"
                                }
                            </td>
                        `;

                        elementos
                            .actividadesTabla
                            .appendChild(
                                fila
                            );
                    }
                );
        }

        async function cargarActividades() {
            try {
                const respuesta =
                    await window.ActividadesAPI
                        .listarPorProyectoNucleo(
                            idProyectoNucleo
                        );

                actividades =
                    Array.isArray(
                        respuesta
                    )
                        ? respuesta
                        : [];

                actualizarResumen();
                renderTabla();

            } catch (error) {
                window.ClienteAPI
                    .mostrarErrorAPI(
                        error
                    );
            }
        }

        /* =====================================================
                          FORMULARIO
        ====================================================== */

        function abrirFormulario(
            actividad = null
        ) {
            if (!puedeCapturar) {
                return;
            }

            idActividadEdicion =
                actividad?.id_actividad ||
                null;

            elementos
                .formActividad
                .reset();

            mostrarMensaje("");

            elementos.tipoActividad.value =
                actividad?.tipo_actividad ||
                (
                    tipoInicial ===
                        "sensibilizacion" ||
                    tipoInicial ===
                        "caminamiento"
                        ? tipoInicial
                        : ""
                );

            elementos.contextoActividad.value =
                actividad?.contexto_actividad ||
                "general";

            elementos.afectacionActividad.value =
                actividad?.id_afectacion
                    ? String(
                        actividad.id_afectacion
                    )
                    : "";

            elementos.tipoCop.value =
                actividad?.id_tipo_cop_operativo
                    ? String(
                        actividad
                            .id_tipo_cop_operativo
                    )
                    : "";

            elementos.fechaProgramada.value =
                actividad?.fecha_programada ||
                "";

            elementos.fechaRealizada.value =
                actividad?.fecha_realizada ||
                "";

            elementos.responsable.value =
                actividad?.responsable ||
                "";

            elementos.resultado.value =
                actividad?.resultado ||
                "";

            const titulo =
                elementos
                    .formularioActividad
                    .querySelector(
                        "h2"
                    );

            if (titulo) {
                titulo.textContent =
                    idActividadEdicion
                        ? "Editar actividad de campo"
                        : "Registrar actividad de campo";
            }

            const submit =
                elementos
                    .formActividad
                    .querySelector(
                        '[type="submit"]'
                    );

            if (submit) {
                submit.innerHTML =
                    idActividadEdicion
                        ? '<i class="bi bi-check-lg"></i> Guardar cambios'
                        : '<i class="bi bi-check-lg"></i> Guardar actividad';
            }

            elementos
                .formularioActividad
                .hidden =
                false;

            elementos
                .formularioActividad
                .scrollIntoView({
                    behavior:
                        "smooth",

                    block:
                        "start"
                });
        }

        function cerrarFormulario() {
            idActividadEdicion =
                null;

            elementos
                .formActividad
                .reset();

            mostrarMensaje("");

            elementos
                .formularioActividad
                .hidden =
                true;
        }

        function construirPayload() {
            return {
                id_afectacion:
                    elementos
                        .afectacionActividad
                        .value
                        ? Number(
                            elementos
                                .afectacionActividad
                                .value
                        )
                        : null,

                id_tipo_cop_operativo:
                    elementos
                        .tipoCop
                        .value
                        ? Number(
                            elementos
                                .tipoCop
                                .value
                        )
                        : null,

                tipo_actividad:
                    elementos
                        .tipoActividad
                        .value,

                contexto_actividad:
                    elementos
                        .contextoActividad
                        .value ||
                    "general",

                fecha_programada:
                    elementos
                        .fechaProgramada
                        .value ||
                    null,

                fecha_realizada:
                    elementos
                        .fechaRealizada
                        .value ||
                    null,

                responsable:
                    elementos
                        .responsable
                        .value
                        .trim() ||
                    null,

                resultado:
                    elementos
                        .resultado
                        .value
                        .trim() ||
                    null
            };
        }

        /* =====================================================
                           EVENTOS
        ====================================================== */

        elementos
            .btnNuevaActividad
            ?.addEventListener(
                "click",
                () =>
                    abrirFormulario()
            );

        elementos
            .btnCancelarActividad
            ?.addEventListener(
                "click",
                cerrarFormulario
            );

        elementos
            .filtroTipo
            ?.addEventListener(
                "change",
                renderTabla
            );

        elementos
            .btnLimpiarFiltro
            ?.addEventListener(
                "click",
                () => {
                    elementos
                        .filtroTipo
                        .value =
                        "";

                    renderTabla();
                }
            );

        elementos
            .actividadesTabla
            ?.addEventListener(
                "click",
                event => {
                    const boton =
                        event.target
                            .closest(
                                "[data-editar-actividad]"
                            );

                    if (!boton) {
                        return;
                    }

                    const actividad =
                        actividades.find(
                            item =>
                                Number(
                                    item.id_actividad
                                ) ===
                                Number(
                                    boton.dataset
                                        .editarActividad
                                )
                        );

                    if (actividad) {
                        abrirFormulario(
                            actividad
                        );
                    }
                }
            );

        elementos
            .formActividad
            ?.addEventListener(
                "submit",
                async event => {
                    event.preventDefault();

                    if (
                        !elementos
                            .formActividad
                            .checkValidity()
                    ) {
                        elementos
                            .formActividad
                            .reportValidity();

                        return;
                    }

                    const payload =
                        construirPayload();

                    if (
                        !payload
                            .tipo_actividad
                    ) {
                        mostrarMensaje(
                            "Selecciona el tipo de actividad.",
                            true
                        );

                        return;
                    }

                    const submit =
                        elementos
                            .formActividad
                            .querySelector(
                                '[type="submit"]'
                            );

                    submit.disabled =
                        true;

                    try {
                        if (
                            idActividadEdicion
                        ) {
                            await window
                                .ActividadesAPI
                                .actualizar(
                                    idActividadEdicion,
                                    payload
                                );

                            mostrarMensaje(
                                "Actividad actualizada correctamente."
                            );

                        } else {
                            await window
                                .ActividadesAPI
                                .crear(
                                    idProyectoNucleo,
                                    payload
                                );

                            mostrarMensaje(
                                "Actividad registrada correctamente."
                            );
                        }

                        await cargarActividades();

                        setTimeout(
                            cerrarFormulario,
                            250
                        );

                    } catch (error) {
                        mostrarMensaje(
                            error?.mensaje ||
                            error?.message ||
                            "No se pudo guardar la actividad.",
                            true
                        );

                    } finally {
                        submit.disabled =
                            false;
                    }
                }
            );

        elementos
            .btnVolver
            ?.addEventListener(
                "click",
                () => {
                    window.location.href =
                        `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                            idProyectoNucleo
                        )}`;
                }
            );

        /* =====================================================
                         FILTRO INICIAL
        ====================================================== */

        if (
            tipoInicial ===
                "sensibilizacion" ||
            tipoInicial ===
                "caminamiento"
        ) {
            elementos
                .filtroTipo
                .value =
                tipoInicial;
        }

        /* =====================================================
                            INICIO
        ====================================================== */

        await cargarRol();

        await Promise.all([
            cargarContexto(),
            cargarCatalogos(),
            cargarAfectaciones()
        ]);

        await cargarActividades();
    }
);