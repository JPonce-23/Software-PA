document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros = new URLSearchParams(window.location.search);
    const idProyecto = parametros.get("id");

    const elementos = {
        mensajeError: document.getElementById("mensajeError"),

        nombreProyecto: document.getElementById("nombreProyecto"),
        claveProyecto: document.getElementById("claveProyecto"),
        descripcionProyecto: document.getElementById("descripcionProyecto"),
        vigenciaProyecto: document.getElementById("vigenciaProyecto"),
        enlaceEstadoFinanciero:
            document.getElementById("enlaceEstadoFinanciero"),

        enlacePersonas:
            document.getElementById("enlacePersonas"),

        kpiNucleos: document.getElementById("kpiNucleos"),
        kpiParcelasAfectaciones:
            document.getElementById("kpiParcelasAfectaciones"),
        kpiSuperficie: document.getElementById("kpiSuperficie"),
        nucleosGrid: document.getElementById("nucleosGrid"),

        btnEditarProyecto: document.getElementById("btnEditarProyecto"),
        editarProyectoContenedor:
            document.getElementById("editarProyectoContenedor"),
        formEditarProyecto:
            document.getElementById("formEditarProyecto"),
        editarNombreProyecto:
            document.getElementById("editarNombreProyecto"),
        editarDescripcionProyecto:
            document.getElementById("editarDescripcionProyecto"),
        editarFechaInicio:
            document.getElementById("editarFechaInicio"),
        editarFechaFin:
            document.getElementById("editarFechaFin"),
        editarProyectoError:
            document.getElementById("editarProyectoError"),
        btnCancelarEdicionProyecto:
            document.getElementById("btnCancelarEdicionProyecto"),
        btnGuardarEdicionProyecto:
            document.getElementById("btnGuardarEdicionProyecto"),

        btnAgregarNucleo:
            document.getElementById("btnAgregarNucleo"),
        formNuevoNucleo:
            document.getElementById("formNuevoNucleo"),
        btnCancelarNucleo:
            document.getElementById("btnCancelarNucleo"),
        btnGuardarNucleo:
            document.getElementById("btnGuardarNucleo"),
        nucleoEntidad:
            document.getElementById("nucleoEntidad"),
        nucleoMunicipio:
            document.getElementById("nucleoMunicipio"),
        nucleoNombre:
            document.getElementById("nucleoNombre"),
        nucleoTipoTenencia:
            document.getElementById("nucleoTipoTenencia"),
        nuevoNucleoError:
            document.getElementById("nuevoNucleoError")
    };

    if (!idProyecto) {
        window.ClienteAPI.mostrarErrorAPI(
            new Error(
                "No se especificó un proyecto (falta ?id= en la URL)."
            ),
            elementos.mensajeError
        );

        return;
    }

    let proyecto = null;
    let nucleos = [];
    let catalogosNucleoCargados = false;

    /* =====================================================
                        UTILIDADES
    ====================================================== */

    function formatoFecha(valorISO) {
        if (!valorISO) {
            return null;
        }

        const partes = String(valorISO).split("-");

        if (partes.length !== 3) {
            return String(valorISO);
        }

        const [anio, mes, dia] = partes;

        return `${dia}/${mes}/${anio}`;
    }

    function formatoSuperficie(valor) {
        return `${Number(valor || 0).toFixed(2)} ha`;
    }

    function mostrarMensajeError(contenedor, mensaje) {
        if (!contenedor) {
            return;
        }

        contenedor.textContent = mensaje;
        contenedor.hidden = false;
    }

    function limpiarMensajeError(contenedor) {
        if (!contenedor) {
            return;
        }

        contenedor.textContent = "";
        contenedor.hidden = true;
    }

    /* =====================================================
                        PROYECTO
    ====================================================== */

    function renderProyecto() {
        if (!proyecto) {
            return;
        }

        document.title =
            `${proyecto.nombre_proyecto} | SSALFER`;

        if (elementos.nombreProyecto) {
            elementos.nombreProyecto.textContent =
                proyecto.nombre_proyecto || "Proyecto";
        }

        if (elementos.claveProyecto) {
            elementos.claveProyecto.textContent =
                proyecto.clave_proyecto || "—";
        }

        if (elementos.descripcionProyecto) {
            if (proyecto.descripcion) {
                elementos.descripcionProyecto.textContent =
                    proyecto.descripcion;

                elementos.descripcionProyecto.hidden = false;
            } else {
                elementos.descripcionProyecto.textContent = "";
                elementos.descripcionProyecto.hidden = true;
            }
        }

        const fechaInicio =
            formatoFecha(proyecto.fecha_inicio);

        const fechaFin =
            formatoFecha(proyecto.fecha_fin);

        if (elementos.vigenciaProyecto) {
            elementos.vigenciaProyecto.textContent =
                fechaInicio || fechaFin
                    ? `${fechaInicio || "—"} – ${fechaFin || "en curso"}`
                    : "Sin fechas registradas";
        }

        if (elementos.enlaceEstadoFinanciero) {
            elementos.enlaceEstadoFinanciero.href =
                `/pages/estadoFinanciero.html?id_proyecto=${encodeURIComponent(
                    idProyecto
                )}`;
        }

        if (elementos.enlacePersonas) {
            elementos.enlacePersonas.href =
                `/pages/persona.html?id_proyecto=${encodeURIComponent(
                    idProyecto
                )}`;
        }
    }

    /* =====================================================
                    GRID DE NÚCLEOS
    ====================================================== */

    function crearTarjetaNucleo(nucleo) {
        const tarjeta = document.createElement("a");

        tarjeta.className = "tarjeta-nucleo";

        tarjeta.href =
            `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                nucleo.id_proyecto_nucleo
            )}`;

        const icono = document.createElement("div");

        icono.className = "nucleo-icono";
        icono.innerHTML =
            '<i class="bi bi-buildings"></i>';

        const info = document.createElement("div");

        info.className = "nucleo-info";

        const etiqueta =
            document.createElement("span");

        etiqueta.textContent =
            "Núcleo agrario";

        const titulo =
            document.createElement("h3");

        titulo.textContent =
            nucleo.nombre_nucleo ||
            "Núcleo sin nombre";

        const ubicacion =
            document.createElement("p");

        ubicacion.textContent =
            [
                nucleo.municipio,
                nucleo.entidad
            ]
                .filter(Boolean)
                .join(", ") ||
            "Ubicación sin registrar";

        info.append(
            etiqueta,
            titulo,
            ubicacion
        );

        const resumen =
            document.createElement("div");

        resumen.className =
            "nucleo-resumen";

        const parcelas =
            document.createElement("span");

        parcelas.textContent =
            `${Number(
                nucleo.total_parcelas || 0
            )} parcelas`;

        const afectaciones =
            document.createElement("span");

        afectaciones.textContent =
            `${Number(
                nucleo.total_afectaciones || 0
            )} afectaciones`;

        resumen.append(
            parcelas,
            afectaciones
        );

        const flecha =
            document.createElement("i");

        flecha.className =
            "bi bi-chevron-right nucleo-flecha";

        tarjeta.append(
            icono,
            info,
            resumen,
            flecha
        );

        return tarjeta;
    }

    function renderNucleos() {
        const lista =
            Array.isArray(nucleos)
                ? nucleos
                : [];

        const totalParcelas =
            lista.reduce(
                (acumulado, nucleo) =>
                    acumulado +
                    Number(
                        nucleo.total_parcelas || 0
                    ),
                0
            );

        const totalAfectaciones =
            lista.reduce(
                (acumulado, nucleo) =>
                    acumulado +
                    Number(
                        nucleo.total_afectaciones || 0
                    ),
                0
            );

        const superficieAfectada =
            lista.reduce(
                (acumulado, nucleo) =>
                    acumulado +
                    Number(
                        nucleo.superficie_afectada_ha || 0
                    ),
                0
            );

        if (elementos.kpiNucleos) {
            elementos.kpiNucleos.textContent =
                String(lista.length);
        }

        if (elementos.kpiParcelasAfectaciones) {
            elementos.kpiParcelasAfectaciones.textContent =
                `${totalParcelas} / ${totalAfectaciones}`;
        }

        if (elementos.kpiSuperficie) {
            elementos.kpiSuperficie.textContent =
                formatoSuperficie(
                    superficieAfectada
                );
        }

        if (!elementos.nucleosGrid) {
            return;
        }

        elementos.nucleosGrid.innerHTML = "";

        if (lista.length === 0) {
            const vacio =
                document.createElement("p");

            vacio.className =
                "proyectos-lista-vacia";

            vacio.textContent =
                "Este proyecto todavía no tiene núcleos agrarios vinculados.";

            elementos.nucleosGrid.appendChild(
                vacio
            );

            return;
        }

        lista.forEach(nucleo => {
            elementos.nucleosGrid.appendChild(
                crearTarjetaNucleo(nucleo)
            );
        });
    }

    async function cargarDatos() {
        limpiarMensajeError(
            elementos.mensajeError
        );

        try {
            [
                proyecto,
                nucleos
            ] = await Promise.all([
                window.ProyectosAPI.obtener(
                    idProyecto
                ),
                window.NucleosAPI.listarPorProyecto(
                    idProyecto
                )
            ]);

            renderProyecto();
            renderNucleos();

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(
                error,
                elementos.mensajeError
            );

            if (elementos.nombreProyecto) {
                elementos.nombreProyecto.textContent =
                    "No se pudo cargar el proyecto";
            }
        }
    }

    /* =====================================================
                    EDITAR PROYECTO
    ====================================================== */

    function abrirEdicionProyecto() {
        if (!proyecto) {
            return;
        }

        limpiarMensajeError(
            elementos.editarProyectoError
        );

        elementos.editarNombreProyecto.value =
            proyecto.nombre_proyecto || "";

        elementos.editarDescripcionProyecto.value =
            proyecto.descripcion || "";

        elementos.editarFechaInicio.value =
            proyecto.fecha_inicio || "";

        elementos.editarFechaFin.value =
            proyecto.fecha_fin || "";

        elementos.editarProyectoContenedor.hidden =
            false;

        elementos.editarNombreProyecto.focus();
    }

    function cerrarEdicionProyecto() {
        limpiarMensajeError(
            elementos.editarProyectoError
        );

        elementos.editarProyectoContenedor.hidden =
            true;
    }

    if (elementos.btnEditarProyecto) {
        elementos.btnEditarProyecto.addEventListener(
            "click",
            abrirEdicionProyecto
        );
    }

    if (elementos.btnCancelarEdicionProyecto) {
        elementos.btnCancelarEdicionProyecto.addEventListener(
            "click",
            cerrarEdicionProyecto
        );
    }

    if (elementos.formEditarProyecto) {
        elementos.formEditarProyecto.addEventListener(
            "submit",
            async evento => {
                evento.preventDefault();

                limpiarMensajeError(
                    elementos.editarProyectoError
                );

                const nombre =
                    elementos
                        .editarNombreProyecto
                        .value
                        .trim();

                const descripcion =
                    elementos
                        .editarDescripcionProyecto
                        .value
                        .trim();

                const fechaInicio =
                    elementos.editarFechaInicio.value ||
                    null;

                const fechaFin =
                    elementos.editarFechaFin.value ||
                    null;

                if (!nombre) {
                    mostrarMensajeError(
                        elementos.editarProyectoError,
                        "El nombre del proyecto es obligatorio."
                    );

                    return;
                }

                if (nombre.length > 200) {
                    mostrarMensajeError(
                        elementos.editarProyectoError,
                        "El nombre del proyecto no puede superar 200 caracteres."
                    );

                    return;
                }

                if (
                    fechaInicio &&
                    fechaFin &&
                    fechaFin < fechaInicio
                ) {
                    mostrarMensajeError(
                        elementos.editarProyectoError,
                        "La fecha de finalización no puede ser anterior a la fecha de inicio."
                    );

                    return;
                }

                elementos.btnGuardarEdicionProyecto.disabled =
                    true;

                try {
                    proyecto =
                        await window.ProyectosAPI.actualizar(
                            idProyecto,
                            {
                                nombre_proyecto:
                                    nombre,
                                descripcion:
                                    descripcion || null,
                                fecha_inicio:
                                    fechaInicio,
                                fecha_fin:
                                    fechaFin
                            }
                        );

                    renderProyecto();
                    cerrarEdicionProyecto();

                    alert(
                        "Proyecto actualizado correctamente."
                    );

                } catch (error) {
                    window.ClienteAPI.mostrarErrorAPI(
                        error,
                        elementos.editarProyectoError
                    );

                } finally {
                    elementos.btnGuardarEdicionProyecto.disabled =
                        false;
                }
            }
        );
    }

    /* =====================================================
                NUEVO NÚCLEO AGRARIO
    ====================================================== */

    function limpiarFormularioNucleo() {
        elementos.nucleoEntidad.value = "";

        elementos.nucleoMunicipio.innerHTML =
            '<option value="">Selecciona un municipio</option>';

        elementos.nucleoMunicipio.disabled =
            true;

        elementos.nucleoNombre.value = "";

        elementos.nucleoTipoTenencia.value =
            "";

        limpiarMensajeError(
            elementos.nuevoNucleoError
        );
    }

    async function cargarCatalogosNucleo() {
        if (catalogosNucleoCargados) {
            return true;
        }

        limpiarMensajeError(
            elementos.nuevoNucleoError
        );

        try {
            const [
                entidades,
                tiposTenencia
            ] = await Promise.all([
                window.CatalogosAPI
                    .obtenerEntidades(),

                window.CatalogosAPI
                    .obtenerOperativo(
                        "tipo_tenencia"
                    )
            ]);

            elementos.nucleoEntidad.innerHTML =
                '<option value="">Selecciona una entidad</option>';

            for (
                const entidad of
                Array.isArray(entidades)
                    ? entidades
                    : []
            ) {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    entidad.id_entidad;

                option.textContent =
                    entidad.nombre ||
                    entidad.clave_inegi ||
                    `Entidad ${entidad.id_entidad}`;

                elementos.nucleoEntidad.appendChild(
                    option
                );
            }

            elementos.nucleoTipoTenencia.innerHTML =
                '<option value="">Selecciona un tipo</option>';

            for (
                const tipo of
                Array.isArray(tiposTenencia)
                    ? tiposTenencia
                    : []
            ) {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    tipo.id_catalogo_opcion;

                option.textContent =
                    tipo.nombre ||
                    tipo.codigo ||
                    `Tipo ${tipo.id_catalogo_opcion}`;

                elementos
                    .nucleoTipoTenencia
                    .appendChild(option);
            }

            if (
                elementos.nucleoEntidad
                    .options.length <= 1
            ) {
                throw new Error(
                    "El catálogo de entidades federativas está vacío."
                );
            }

            if (
                elementos.nucleoTipoTenencia
                    .options.length <= 1
            ) {
                throw new Error(
                    "El catálogo de tipos de tenencia está vacío."
                );
            }

            catalogosNucleoCargados =
                true;

            return true;

        } catch (error) {
            mostrarMensajeError(
                elementos.nuevoNucleoError,
                error?.mensaje ||
                error?.message ||
                "No se pudieron cargar los catálogos."
            );

            return false;
        }
    }

    if (elementos.nucleoEntidad) {
        elementos.nucleoEntidad.addEventListener(
            "change",
            async () => {
                const idEntidad =
                    elementos.nucleoEntidad.value;

                elementos.nucleoMunicipio.innerHTML =
                    '<option value="">Selecciona un municipio</option>';

                elementos.nucleoMunicipio.disabled =
                    true;

                limpiarMensajeError(
                    elementos.nuevoNucleoError
                );

                if (!idEntidad) {
                    return;
                }

                try {
                    const municipios =
                        await window.CatalogosAPI
                            .obtenerMunicipios(
                                idEntidad
                            );

                    for (
                        const municipio of
                        Array.isArray(municipios)
                            ? municipios
                            : []
                    ) {
                        const option =
                            document.createElement(
                                "option"
                            );

                        option.value =
                            municipio.id_municipio;

                        option.textContent =
                            municipio.nombre ||
                            municipio.clave_inegi ||
                            `Municipio ${municipio.id_municipio}`;

                        elementos
                            .nucleoMunicipio
                            .appendChild(option);
                    }

                    if (
                        elementos.nucleoMunicipio
                            .options.length <= 1
                    ) {
                        mostrarMensajeError(
                            elementos.nuevoNucleoError,
                            "La entidad seleccionada no tiene municipios activos disponibles."
                        );

                        return;
                    }

                    elementos.nucleoMunicipio.disabled =
                        false;

                } catch (error) {
                    window.ClienteAPI.mostrarErrorAPI(
                        error,
                        elementos.nuevoNucleoError
                    );
                }
            }
        );
    }

    if (elementos.btnAgregarNucleo) {
        elementos.btnAgregarNucleo.addEventListener(
            "click",
            async () => {
                limpiarFormularioNucleo();

                elementos.formNuevoNucleo.hidden =
                    false;

                const cargados =
                    await cargarCatalogosNucleo();

                if (cargados) {
                    elementos.nucleoNombre.focus();
                }
            }
        );
    }

    if (elementos.btnCancelarNucleo) {
        elementos.btnCancelarNucleo.addEventListener(
            "click",
            () => {
                limpiarFormularioNucleo();

                elementos.formNuevoNucleo.hidden =
                    true;
            }
        );
    }

    if (elementos.btnGuardarNucleo) {
        elementos.btnGuardarNucleo.addEventListener(
            "click",
            async () => {
                limpiarMensajeError(
                    elementos.nuevoNucleoError
                );

                const idMunicipio =
                    Number(
                        elementos
                            .nucleoMunicipio
                            .value
                    );

                const nombreNucleo =
                    elementos
                        .nucleoNombre
                        .value
                        .trim();

                const idTipoTenencia =
                    Number(
                        elementos
                            .nucleoTipoTenencia
                            .value
                    );

                if (!idMunicipio) {
                    mostrarMensajeError(
                        elementos.nuevoNucleoError,
                        "Selecciona un municipio."
                    );

                    return;
                }

                if (!nombreNucleo) {
                    mostrarMensajeError(
                        elementos.nuevoNucleoError,
                        "Escribe el nombre del núcleo agrario."
                    );

                    return;
                }

                if (nombreNucleo.length > 300) {
                    mostrarMensajeError(
                        elementos.nuevoNucleoError,
                        "El nombre del núcleo no puede superar 300 caracteres."
                    );

                    return;
                }

                if (!idTipoTenencia) {
                    mostrarMensajeError(
                        elementos.nuevoNucleoError,
                        "Selecciona un tipo de tenencia."
                    );

                    return;
                }

                elementos.btnGuardarNucleo.disabled =
                    true;

                try {
                    const nucleoCreado =
                        await window.NucleosAPI.crear(
                            {
                                id_municipio:
                                    idMunicipio,
                                nombre_nucleo:
                                    nombreNucleo,
                                id_tipo_tenencia:
                                    idTipoTenencia
                            }
                        );

                    try {
                        await window.NucleosAPI
                            .vincularAProyecto(
                                idProyecto,
                                {
                                    id_nucleo:
                                        nucleoCreado
                                            .id_nucleo
                                }
                            );

                    } catch (errorVinculo) {
                        throw new Error(
                            `El núcleo se creó con ID ${nucleoCreado.id_nucleo}, ` +
                            "pero no pudo vincularse al proyecto. " +
                            (
                                errorVinculo?.mensaje ||
                                errorVinculo?.message ||
                                "Revisa el backend antes de volver a intentarlo."
                            )
                        );
                    }

                    nucleos =
                        await window.NucleosAPI
                            .listarPorProyecto(
                                idProyecto
                            );

                    renderNucleos();

                    limpiarFormularioNucleo();

                    elementos.formNuevoNucleo.hidden =
                        true;

                    alert(
                        "Núcleo agrario creado y vinculado correctamente."
                    );

                } catch (error) {
                    mostrarMensajeError(
                        elementos.nuevoNucleoError,
                        error?.mensaje ||
                        error?.message ||
                        "No se pudo crear el núcleo agrario."
                    );

                } finally {
                    elementos.btnGuardarNucleo.disabled =
                        false;
                }
            }
        );
    }

    /* =====================================================
                    CONTROL POR ROL
    ====================================================== */

    try {
        const sesion =
            await window.AuthAPI
                .obtenerSesionActual();

        const rol =
            sesion?.user?.rol;

        if (
            rol &&
            rol !== "admin"
        ) {
            if (elementos.btnEditarProyecto) {
                elementos.btnEditarProyecto.hidden =
                    true;
            }

            if (elementos.btnAgregarNucleo) {
                elementos.btnAgregarNucleo.hidden =
                    true;
            }
        }

    } catch {
        /*
         * AuthAPI.requerirSesion() ya protege la página.
         * Si la sesión expiró, ese flujo se encargará
         * de redirigir al login.
         */
    }

    await cargarDatos();
});