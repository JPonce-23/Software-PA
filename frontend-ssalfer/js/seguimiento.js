document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros = new URLSearchParams(window.location.search);
    const idProyectoNucleo = Number(
        parametros.get("id_proyecto_nucleo") ||
        document.querySelector(".contenedor")?.dataset.proyectoNucleoId
    );

    if (!Number.isInteger(idProyectoNucleo) || idProyectoNucleo <= 0) {
        await window.SSALFER_UI.verDatos("Selecciona un núcleo", {
            Información: "Abre Seguimiento desde el núcleo del proyecto que deseas consultar."
        });
        window.location.href = "/dashboard.html";
        return;
    }

    const elementos = {
        btnVolver: document.getElementById("btnVolver"),
        btnNuevoEvento: document.getElementById("btnNuevoEvento"),
        btnCancelarEvento: document.getElementById("btnCancelarEvento"),

        formulario: document.getElementById("formularioEvento"),
        form: document.getElementById("formSeguimiento"),
        tabla: document.getElementById("seguimientoTabla"),
        mensaje: document.getElementById("mensajeFormulario"),

        ambito: document.getElementById("ambito"),
        tipoEvento: document.getElementById("tipoEvento"),
        entidadTipo: document.getElementById("entidadTipo"),
        entidadContextoCampo: document.getElementById("entidadContextoCampo"),
        entidadContextoSelector: document.getElementById("entidadContextoSelector"),
        entidadSelector: document.getElementById("entidadSelector"),
        entidadId: document.getElementById("entidadId"),
        motivo: document.getElementById("motivo"),
        fechaEvento: document.getElementById("fechaEvento"),
        fuente: document.getElementById("fuente"),
        detalle: document.getElementById("detalle"),
        documento: document.getElementById("documento"),

        totalEventos: document.getElementById("totalEventos"),
        totalGenerales: document.getElementById("totalGenerales"),
        totalColectivos: document.getElementById("totalColectivos"),
        totalIndividuales: document.getElementById("totalIndividuales")
    };

    const tituloFormulario =
        elementos.formulario?.querySelector("h2");

    const botonGuardar =
        elementos.form?.querySelector('button[type="submit"]');

    let eventos = [];
    let tiposEvento = [];
    let motivos = [];

    let tipoPorId = new Map();
    let motivoPorId = new Map();

    let idEventoEditando = null;
    let puedeCapturar = false;
    let guardando = false;

    const nombresEntidad = {
        proyecto_nucleo: "Núcleo del proyecto",
        afectacion: "Afectación",
        parcela: "Parcela",
        parcela_titular: "Titular de parcela",
        unidad_agraria: "Unidad agraria",
        asamblea: "Asamblea",
        asamblea_convocatoria: "Convocatoria de asamblea",
        convenio: "Convenio",
        tramite_ran: "Trámite RAN",
        tramite_ran_evento: "Evento RAN",
        tramite_fifonafe: "Trámite FIFONAFE",
        tramite_fifonafe_evento: "Evento FIFONAFE",
        tramite_fifonafe_interviniente: "Interviniente FIFONAFE",
        orv: "ORV",
        padron_historial: "Padrón",
        indemnizacion: "Indemnización"
    };

    const nombresAmbito = {
        general: "General",
        colectivo: "Colectivo",
        individual: "Individual"
    };


    /* =====================================================
                        UTILIDADES
    ====================================================== */

    /* =====================================================
                SELECTOR CONTEXTUAL DE ENTIDAD
    ====================================================== */

    const tiposEntidadSelectorDirecto = new Set([
        "proyecto_nucleo",
        "afectacion",
        "parcela",
        "unidad_agraria",
        "asamblea",
        "tramite_ran",
        "tramite_fifonafe",
        "orv",
        "padron_historial"
    ]);

    let revisionEntidad = 0;
    const referenciasEntidad = new Map();
    const consultasEntidad = new Map();
    const dependenciasEntidad = {
        asamblea_convocatoria: {
            padre: "asamblea", campo: "id_convocatoria", anidados: "convocatorias",
            listar: id => window.AsambleasAPI.listarConvocatorias(id)
        },
        convenio: {
            padre: "afectacion", campo: "id_convenio",
            listar: id => window.ConveniosAPI.listarPorAfectacion(id)
        },
        tramite_ran_evento: {
            padre: "tramite_ran", campo: "id_evento_ran", anidados: "eventos",
            listar: id => window.TramitesRanAPI.listarEventos(id)
        },
        tramite_fifonafe_evento: {
            padre: "tramite_fifonafe", campo: "id_evento_fifonafe", anidados: "eventos",
            listar: id => window.FifonafeAPI.listarEventos(id)
        },
        tramite_fifonafe_interviniente: {
            padre: "tramite_fifonafe", campo: "id_interviniente_fifonafe", anidados: "intervinientes",
            listar: id => window.FifonafeAPI.listarIntervinientes(id)
        },
        indemnizacion: {
            padre: "afectacion", campo: "id_indemnizacion",
            listar: id => window.IndemnizacionAPI.listarPorAfectacion(id)
        }
    };

    function consultarUnaVez(clave, consulta) {
        if (!consultasEntidad.has(clave)) {
            consultasEntidad.set(clave, Promise.resolve().then(consulta).catch(error => {
                consultasEntidad.delete(clave);
                throw error;
            }));
        }
        return consultasEntidad.get(clave);
    }

    function comoLista(respuesta) {
        return Array.isArray(respuesta) ? respuesta : respuesta ? [respuesta] : [];
    }

    async function etiquetaDependiente(tipo, item) {
        const fecha = valor => valor ? window.SSALFER_FORMAT.formatearFecha(valor) : null;
        const humano = valor => valor ? window.SSALFER_FORMAT.etiquetaCodigo(valor) : null;
        let partes;
        switch (tipo) {
            case "asamblea_convocatoria":
                partes = [`Convocatoria ${item.ordinal}`, fecha(item.fecha_realizacion || item.fecha_programada || item.fecha_expedicion), item.observaciones_resultado];
                break;
            case "convenio":
                partes = [humano(item.tipo_convenio), item.consecutivo ? `Consecutivo ${item.consecutivo}` : null,
                    humano(item.ambito), fecha(item.fecha_firma || item.fecha_programada_firma), item.descripcion_instrumento];
                break;
            case "tramite_ran_evento":
                partes = [`Evento ${item.ordinal}`, item.folio_referencia || item.numero_solicitud, fecha(item.fecha_evento), item.resultado];
                break;
            case "tramite_fifonafe_evento":
                partes = [`Evento ${item.ordinal}`, item.numero_oficio, fecha(item.fecha_evento || item.fecha_oficio), item.origen, item.destino];
                break;
            case "tramite_fifonafe_interviniente": {
                let nombre = "Persona no disponible";
                try {
                    const persona = await consultarUnaVez(`persona:${item.id_persona}`,
                        () => window.PersonasAPI.obtener(item.id_persona));
                    nombre = [persona.nombre, persona.apellido_paterno, persona.apellido_materno].filter(Boolean).join(" ") || nombre;
                } catch (error) {
                    console.warn("No fue posible consultar la persona del interviniente.", error);
                }
                partes = [nombre, humano(item.rol)];
                break;
            }
            case "indemnizacion":
                partes = ["Indemnización", humano(item.estatus), fecha(item.fecha_resolucion || item.fecha_programada), item.descripcion_estatus];
                break;
        }
        return partes.filter(Boolean).join(" · ");
    }

    async function listarHijos(tipo, idPadre) {
        return consultarUnaVez(`${tipo}:${idPadre}`, async () => {
            const config = dependenciasEntidad[tipo];
            const lista = comoLista(await config.listar(idPadre));
            return Promise.all(lista.map(async item => ({
                id: Number(item[config.campo]),
                etiqueta: await etiquetaDependiente(tipo, item)
            })));
        });
    }

    function opcionesEntidad(select, opciones, inicial) {
        select.replaceChildren(new Option(inicial, ""));
        for (const item of opciones) {
            if (Number.isInteger(item.id) && item.id > 0) {
                select.add(new Option(item.etiqueta, String(item.id)));
            }
        }
    }

    async function cargarHijosDependientes(tipo, idPadre, valorActual = null, revision = revisionEntidad) {
        const select = elementos.entidadSelector;
        elementos.entidadId.value = "";
        select.disabled = true;
        opcionesEntidad(select, [], idPadre ? "Cargando registros..." : "Selecciona primero el registro de contexto");
        if (!idPadre) return;
        try {
            const hijos = await listarHijos(tipo, Number(idPadre));
            if (revision !== revisionEntidad) return;
            opcionesEntidad(select, hijos, hijos.length ? "Selecciona un registro" : "No hay elementos disponibles");
            select.disabled = !hijos.length || Boolean(idEventoEditando);
            if (valorActual && hijos.some(hijo => hijo.id === Number(valorActual))) select.value = String(valorActual);
            elementos.entidadId.value = select.value;
            hijos.forEach(hijo => referenciasEntidad.set(`${tipo}:${hijo.id}`, hijo.etiqueta));
        } catch (error) {
            if (revision !== revisionEntidad) return;
            opcionesEntidad(select, [], "No fue posible cargar los registros");
            mostrarMensaje("No fue posible cargar los registros relacionados. Vuelve a seleccionar el contexto para reintentar.", true);
        }
    }

    async function cargarContextoDependiente(tipo, valorActual, revision) {
        const config = dependenciasEntidad[tipo];
        const contexto = elementos.entidadContextoSelector;
        elementos.entidadContextoCampo.hidden = false;
        elementos.entidadContextoCampo.querySelector("label").textContent = nombresEntidad[config.padre];
        elementos.entidadContextoCampo.querySelector("small").textContent = "Selecciona primero el registro al que pertenece la relación.";
        contexto.hidden = false;
        contexto.disabled = true;
        opcionesEntidad(contexto, [], "Cargando registros...");
        await cargarHijosDependientes(tipo, null, null, revision);
        try {
            const padres = comoLista(await consultarUnaVez(`padres:${config.padre}`, () => listarEntidadDirecta(config.padre)));
            if (revision !== revisionEntidad) return;
            opcionesEntidad(contexto, padres.map(item => ({
                id: idEntidadDirecta(config.padre, item), etiqueta: etiquetaEntidadDirecta(config.padre, item)
            })), padres.length ? "Selecciona un registro" : "No hay elementos disponibles");
            contexto.disabled = !padres.length || Boolean(idEventoEditando);
            if (!valorActual) return;
            // Las respuestas de asambleas/RAN/FIFONAFE ya incluyen sus hijos.
            // Convenios e indemnizaciones requieren como máximo una consulta por afectación.
            for (const padre of padres) {
                const idPadre = idEntidadDirecta(config.padre, padre);
                const hijos = config.anidados && Array.isArray(padre[config.anidados])
                    ? padre[config.anidados].map(item => ({ id: Number(item[config.campo]) }))
                    : await listarHijos(tipo, idPadre);
                if (revision !== revisionEntidad) return;
                if (hijos.some(hijo => hijo.id === Number(valorActual))) {
                    contexto.value = String(idPadre);
                    await cargarHijosDependientes(tipo, idPadre, valorActual, revision);
                    return;
                }
            }
            opcionesEntidad(elementos.entidadSelector, [], "El registro asociado ya no está disponible");
        } catch (error) {
            if (revision !== revisionEntidad) return;
            opcionesEntidad(contexto, [], "No fue posible cargar el contexto");
            mostrarMensaje("No fue posible recuperar el contexto de la relación. Cierra y vuelve a abrir el formulario para reintentar.", true);
        }
    }

    function idEntidadDirecta(tipo, item) {
        const campos = {
            proyecto_nucleo: "id_proyecto_nucleo",
            afectacion: "id_afectacion",
            parcela: "id_parcela",
            unidad_agraria: "id_unidad_agraria",
            asamblea: "id_asamblea",
            tramite_ran: "id_tramite_ran",
            tramite_fifonafe: "id_tramite_fifonafe",
            orv: "id_orv",
            padron_historial: "id_padron"
        };

        const campo = campos[tipo];
        const id = campo
            ? Number(item?.[campo])
            : NaN;

        return Number.isInteger(id) && id > 0
            ? id
            : null;
    }

    function etiquetaEntidadDirecta(tipo, item) {
        const id = idEntidadDirecta(tipo, item);

        if (!id) {
            return "";
        }

        switch (tipo) {
            case "proyecto_nucleo":
                return (
                    item.nombre_nucleo ||
                    "Núcleo del proyecto"
                );

            case "afectacion": {
                const superficie =
                    item.superficie_afectada_ha ??
                    item.superficie_preliminar_ha;

                const numeroSuperficie =
                    Number(superficie);

                const superficieTexto =
                    Number.isFinite(numeroSuperficie)
                        ? `${numeroSuperficie.toLocaleString(
                            "es-MX",
                            {
                                maximumFractionDigits: 2
                            }
                        )} ha`
                        : null;

                const tipo =
                    item.tipo_afectacion
                        ? item.tipo_afectacion
                            .charAt(0)
                            .toUpperCase() +
                          item.tipo_afectacion.slice(1)
                        : "Afectación";

                return [
                    tipo,
                    superficieTexto,
                    item.situacion || null
                ]
                    .filter(Boolean)
                    .join(" · ");
            }

            case "parcela": {
                const tipo =
                    item.tipo_parcela
                        ? item.tipo_parcela
                            .charAt(0)
                            .toUpperCase() +
                          item.tipo_parcela.slice(1)
                        : null;

                return [
                    item.no_parcela || "Parcela",
                    tipo,
                    item.certificado_parcelario
                        ? `Certificado ${item.certificado_parcelario}`
                        : null
                ]
                    .filter(Boolean)
                    .join(" · ");
            }

            case "unidad_agraria":
                return (
                    item.referencia_alfanumerica ||
                    item.referencia_normalizada ||
                    "Unidad agraria"
                );

            case "asamblea":
                return (
                    item.proposito ||
                    "Asamblea"
                );

            case "tramite_ran": {
                const fecha =
                    window.SSALFER_FORMAT
                        ?.formatearFecha(
                            item.fecha_programada_ingreso
                        ) ||
                    item.fecha_programada_ingreso ||
                    null;

                return [
                    item.referencia_expediente ||
                        "Trámite RAN",
                    fecha
                ]
                    .filter(Boolean)
                    .join(" · ");
            }

            case "tramite_fifonafe": {
                const estatus =
                    item.estatus
                        ? item.estatus
                            .charAt(0)
                            .toUpperCase() +
                          item.estatus.slice(1)
                        : null;

                const ambito =
                    item.ambito
                        ? item.ambito
                            .charAt(0)
                            .toUpperCase() +
                          item.ambito.slice(1)
                        : null;

                return [
                    item.referencia_expediente ||
                        "Trámite FIFONAFE",
                    estatus,
                    ambito
                ]
                    .filter(Boolean)
                    .join(" · ");
            }

            case "orv": {
                const fecha =
                    window.SSALFER_FORMAT
                        ?.formatearFecha(
                            item.inicio_vigencia
                        ) ||
                    item.inicio_vigencia ||
                    null;

                return [
                    item.numero_orv || "ORV",
                    fecha,
                    item.estatus_fuente || null
                ]
                    .filter(Boolean)
                    .join(" · ");
            }

            case "padron_historial": {
                const fecha =
                    window.SSALFER_FORMAT
                        ?.formatearFecha(
                            item.fecha_padron
                        ) ||
                    item.fecha_padron ||
                    "sin fecha";

                const integrantes =
                    item.numero_ejidatarios_comuneros != null
                        ? `${item.numero_ejidatarios_comuneros} integrantes`
                        : null;

                return [
                    "Padrón",
                    fecha,
                    integrantes,
                    item.fuente || null
                ]
                    .filter(Boolean)
                    .join(" · ");
            }

            default:
                return nombresEntidad[tipo] || "Registro";
        }
    }

    async function listarEntidadDirecta(tipo) {
        switch (tipo) {
            case "proyecto_nucleo": {
                const contexto =
                    await window.NucleosAPI
                        .obtenerProyectoNucleo(
                            idProyectoNucleo
                        );

                return [
                    {
                        ...contexto,
                        id_proyecto_nucleo:
                            idProyectoNucleo
                    }
                ];
            }

            case "afectacion":
                return await window.AfectacionesAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            case "parcela":
                return await window.ParcelasAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            case "unidad_agraria":
                return await window.UnidadesAgrariasAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            case "asamblea":
                return await window.AsambleasAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            case "tramite_ran":
                return await window.TramitesRanAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            case "tramite_fifonafe":
                return await window.FifonafeAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            case "orv":
                return await window.OrvAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            case "padron_historial":
                return await window.PadronesAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            default:
                return [];
        }
    }

    async function cargarSelectorEntidad(
        tipo,
        valorActual = null
    ) {
        const revision = revisionEntidad;
        const select =
            elementos.entidadSelector;

        if (!select) {
            return;
        }

        select.innerHTML = `
            <option value="">
                Cargando registros...
            </option>
        `;

        try {
            const respuesta =
                await listarEntidadDirecta(tipo);

            if (revision !== revisionEntidad) return;

            const lista =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            select.innerHTML = `
                <option value="">
                    Selecciona un registro
                </option>
            `;

            const idsDisponibles =
                new Set();

            lista.forEach(item => {
                const id =
                    idEntidadDirecta(
                        tipo,
                        item
                    );

                if (
                    !id ||
                    idsDisponibles.has(id)
                ) {
                    return;
                }

                idsDisponibles.add(id);

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    String(id);

                option.textContent =
                    etiquetaEntidadDirecta(
                        tipo,
                        item
                    );

                select.appendChild(option);
            });

            const idActual =
                Number(valorActual);

            if (
                Number.isInteger(idActual) &&
                idActual > 0 &&
                !idsDisponibles.has(idActual)
            ) {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    String(idActual);

                option.textContent =
                    "Registro asociado no disponible en el listado";

                select.appendChild(option);
            }

            if (
                select.options.length === 1
            ) {
                select.options[0].textContent =
                    "No hay elementos disponibles";
            }

            let seleccionado = "";

            if (
                Number.isInteger(idActual) &&
                idActual > 0
            ) {
                seleccionado =
                    String(idActual);

            } else if (
                tipo === "proyecto_nucleo"
            ) {
                seleccionado =
                    String(idProyectoNucleo);
            }

            select.value =
                seleccionado;

            elementos.entidadId.value =
                select.value;

        } catch (error) {
            if (revision !== revisionEntidad) return;
            console.warn(
                "No fue posible cargar el selector contextual de entidad.",
                error
            );

            opcionesEntidad(select, [], "No fue posible cargar los registros");
            select.disabled = true;
            elementos.entidadId.value = "";
            mostrarMensaje("No fue posible cargar los registros. Vuelve a seleccionar el tipo de relación para reintentar.", true);
        }
    }

    function ocultarContextoEntidad() {
        if (elementos.entidadContextoCampo) {
            elementos.entidadContextoCampo.hidden = true;
        }

        if (elementos.entidadContextoSelector) {
            elementos.entidadContextoSelector.hidden = true;
            elementos.entidadContextoSelector.disabled = true;
            elementos.entidadContextoSelector.innerHTML = `
                <option value="">
                    Selecciona una opción
                </option>
            `;
        }
    }

    function etiquetaTitularParcela(titular) {
        const nombre = [
            titular.nombre,
            titular.apellido_paterno,
            titular.apellido_materno
        ]
            .filter(Boolean)
            .join(" ")
            .trim();

        const porcentaje =
            Number(titular.porcentaje_participacion);

        const porcentajeTexto =
            Number.isFinite(porcentaje)
                ? `${porcentaje.toLocaleString(
                    "es-MX",
                    {
                        maximumFractionDigits: 2
                    }
                )} %`
                : null;

        return [
            nombre || "Titular de parcela",
            titular.tipo_derecho || null,
            porcentajeTexto
        ]
            .filter(Boolean)
            .join(" · ");
    }

    async function cargarTitularesParcela(
        idParcela,
        valorActual = null
    ) {
        const revision = revisionEntidad;
        const select =
            elementos.entidadSelector;

        const idParcelaNumero =
            Number(idParcela);

        const idActual =
            Number(valorActual);

        if (
            !select ||
            !Number.isInteger(idParcelaNumero) ||
            idParcelaNumero <= 0
        ) {
            if (select) {
                select.innerHTML = `
                    <option value="">
                        Selecciona primero una parcela
                    </option>
                `;

                select.disabled = true;
            }

            if (
                !Number.isInteger(idActual) ||
                idActual <= 0
            ) {
                elementos.entidadId.value = "";
            }

            return;
        }

        select.disabled = true;

        select.innerHTML = `
            <option value="">
                Cargando titulares...
            </option>
        `;

        try {
            const respuesta =
                await window.ParcelasAPI
                    .listarTitulares(
                        idParcelaNumero
                    );

            if (revision !== revisionEntidad) return;

            const titulares =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            select.innerHTML = `
                <option value="">
                    Selecciona un titular
                </option>
            `;

            const idsDisponibles =
                new Set();

            titulares.forEach(titular => {
                const id =
                    Number(
                        titular.id_parcela_titular
                    );

                if (
                    !Number.isInteger(id) ||
                    id <= 0 ||
                    idsDisponibles.has(id)
                ) {
                    return;
                }

                idsDisponibles.add(id);

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    String(id);

                option.textContent =
                    etiquetaTitularParcela(
                        titular
                    );

                select.appendChild(option);
            });

            if (
                Number.isInteger(idActual) &&
                idActual > 0 &&
                !idsDisponibles.has(idActual)
            ) {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    String(idActual);

                option.textContent =
                    "Titular asociado";

                select.appendChild(option);
            }

            if (
                select.options.length === 1
            ) {
                select.options[0].textContent =
                    "No hay titulares disponibles";

                select.disabled = true;
            } else {
                select.disabled = false;
            }

            if (
                Number.isInteger(idActual) &&
                idActual > 0
            ) {
                select.value =
                    String(idActual);
            }

            elementos.entidadId.value =
                select.value;

        } catch (error) {
            if (revision !== revisionEntidad) return;
            console.warn(
                "No fue posible cargar los titulares de la parcela.",
                error
            );

            select.innerHTML = `
                <option value="">
                    No fue posible cargar los titulares
                </option>
            `;

            select.disabled = true;

            elementos.entidadId.value =
                Number.isInteger(idActual) &&
                idActual > 0
                    ? String(idActual)
                    : "";
        }
    }

    async function cargarContextoParcelaTitular(
        valorActual = null
    ) {
        const revision = revisionEntidad;
        const contexto =
            elementos.entidadContextoSelector;

        const select =
            elementos.entidadSelector;

        if (!contexto || !select) {
            return;
        }

        elementos.entidadContextoCampo.hidden =
            false;

        contexto.hidden =
            false;

        contexto.disabled =
            true;

        contexto.innerHTML = `
            <option value="">
                Cargando parcelas...
            </option>
        `;

        select.hidden =
            false;

        select.disabled =
            true;

        select.innerHTML = `
            <option value="">
                Selecciona primero una parcela
            </option>
        `;

        try {
            const respuesta =
                await window.ParcelasAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            if (revision !== revisionEntidad) return;

            const parcelas =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            contexto.innerHTML = `
                <option value="">
                    Selecciona una parcela
                </option>
            `;

            for (const parcela of parcelas) {
                const idParcela =
                    idEntidadDirecta(
                        "parcela",
                        parcela
                    );

                if (!idParcela) {
                    continue;
                }

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    String(idParcela);

                option.textContent =
                    etiquetaEntidadDirecta(
                        "parcela",
                        parcela
                    );

                contexto.appendChild(option);
            }

            contexto.disabled =
                contexto.options.length === 1;

            if (
                contexto.options.length === 1
            ) {
                contexto.options[0].textContent =
                    "No hay parcelas disponibles";
            }

            const idActual =
                Number(valorActual);

            if (
                !Number.isInteger(idActual) ||
                idActual <= 0
            ) {
                elementos.entidadId.value = "";
                return;
            }

            let idParcelaActual =
                null;

            for (const parcela of parcelas) {
                const idParcela =
                    idEntidadDirecta(
                        "parcela",
                        parcela
                    );

                if (!idParcela) {
                    continue;
                }

                const titulares =
                    await window.ParcelasAPI
                        .listarTitulares(
                            idParcela
                        );

                if (revision !== revisionEntidad) return;

                const encontrado =
                    Array.isArray(titulares) &&
                    titulares.some(
                        titular =>
                            Number(
                                titular
                                    .id_parcela_titular
                            ) === idActual
                    );

                if (encontrado) {
                    idParcelaActual =
                        idParcela;

                    break;
                }
            }

            if (idParcelaActual) {
                contexto.value =
                    String(idParcelaActual);

                await cargarTitularesParcela(
                    idParcelaActual,
                    idActual
                );

                return;
            }

            select.innerHTML = `
                <option value="${idActual}">
                    Titular asociado
                </option>
            `;

            select.disabled =
                false;

            select.value =
                String(idActual);

            elementos.entidadId.value =
                String(idActual);

        } catch (error) {
            if (revision !== revisionEntidad) return;
            console.warn(
                "No fue posible cargar el contexto de titular de parcela.",
                error
            );

            contexto.innerHTML = `
                <option value="">
                    No fue posible cargar las parcelas
                </option>
            `;

            contexto.disabled =
                true;
        }
    }
    async function actualizarControlEntidad(
        valorActual = null
    ) {
        const revision = ++revisionEntidad;
        elementos.entidadId.value = "";
        const tipo =
            elementos.entidadTipo
                ?.value
                ?.trim() || "";

        const campo =
            elementos.entidadId
                ?.closest(".campo");

        const label =
            campo?.querySelector("label");

        const ayuda =
            campo?.querySelector("small");

        ocultarContextoEntidad();

        if (!tipo) {
            if (campo) {
                campo.hidden = true;
            }

            elementos.entidadSelector.hidden =
                true;

            elementos.entidadSelector.disabled =
                true;

            elementos.entidadId.value =
                "";

            return;
        }

        if (campo) {
            campo.hidden = false;
        }

        if (dependenciasEntidad[tipo]) {
            elementos.entidadId.hidden = true;
            elementos.entidadSelector.hidden = false;
            label.textContent = nombresEntidad[tipo];
            label.htmlFor = "entidadSelector";
            ayuda.textContent = "Selecciona el contexto y después el registro relacionado.";
            await cargarContextoDependiente(tipo, valorActual, revision);
            return;
        }

        if (tipo === "parcela_titular") {
            elementos.entidadId.hidden =
                true;

            elementos.entidadSelector.hidden =
                false;

            elementos.entidadSelector.disabled =
                true;

            if (label) {
                label.textContent =
                    "Titular de parcela";

                label.htmlFor =
                    "entidadSelector";
            }

            if (ayuda) {
                ayuda.textContent =
                    "Selecciona primero una parcela y después uno de sus titulares.";
            }

            const contextoLabel =
                elementos.entidadContextoCampo
                    ?.querySelector("label");

            const contextoAyuda =
                elementos.entidadContextoCampo
                    ?.querySelector("small");

            if (contextoLabel) {
                contextoLabel.textContent =
                    "Parcela";

                contextoLabel.htmlFor =
                    "entidadContextoSelector";
            }

            if (contextoAyuda) {
                contextoAyuda.textContent =
                    "Selecciona la parcela relacionada con el titular.";
            }

            await cargarContextoParcelaTitular(
                valorActual
            );

            return;
        }
        if (
            !tiposEntidadSelectorDirecto.has(
                tipo
            )
        ) {
            elementos.entidadSelector.hidden =
                false;

            elementos.entidadSelector.disabled =
                true;

            elementos.entidadId.hidden =
                true;

            elementos.entidadId.value =
                "";
            opcionesEntidad(elementos.entidadSelector, [], "No hay un selector disponible para esta relación");

            if (label) {
                label.textContent =
                    "Registro relacionado";

                label.htmlFor =
                    "entidadSelector";
            }

            if (ayuda) {
                ayuda.textContent =
                    "No fue posible recuperar este tipo de relación. Vuelve a abrir el evento para reintentar.";
            }

            return;
        }

        elementos.entidadId.hidden =
            true;

        elementos.entidadSelector.hidden =
            false;

        elementos.entidadSelector.disabled =
            false;

        if (label) {
            label.textContent =
                "Registro relacionado";

            label.htmlFor =
                "entidadSelector";
        }

        if (ayuda) {
            ayuda.textContent =
                "Selecciona un registro disponible en este núcleo.";
        }

        await cargarSelectorEntidad(
            tipo,
            valorActual
        );
    }

    elementos.entidadTipo
        ?.addEventListener(
            "change",
            async () => {
                elementos.entidadId.value =
                    "";

                await actualizarControlEntidad();
            }
        );

    elementos.entidadContextoSelector
        ?.addEventListener(
            "change",
            async () => {
                const tipo = elementos.entidadTipo.value;
                if (dependenciasEntidad[tipo]) {
                    ++revisionEntidad;
                    await cargarHijosDependientes(tipo, elementos.entidadContextoSelector.value);
                    return;
                }
                if (
                    elementos.entidadTipo
                        ?.value !==
                    "parcela_titular"
                ) {
                    return;
                }

                elementos.entidadId.value =
                    "";

                ++revisionEntidad;

                await cargarTitularesParcela(
                    elementos
                        .entidadContextoSelector
                        .value
                );
            }
        );
    elementos.entidadSelector
        ?.addEventListener(
            "change",
            () => {
                elementos.entidadId.value =
                    elementos.entidadSelector
                        .value;
            }
        );
    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function valorOpcionalTexto(elemento) {
        const valor = elemento?.value?.trim();
        return valor ? valor : null;
    }

    function valorOpcionalNumero(elemento) {
        const valor = elemento?.value?.trim();

        if (!valor) {
            return null;
        }

        const numero = Number(valor);

        return Number.isInteger(numero) && numero > 0
            ? numero
            : NaN;
    }

    function mostrarMensaje(texto, esError = false) {
        if (texto && (!esError || elementos.formulario?.hidden)) {
            window.SSALFER_UI.toast(texto, { tipo: esError ? "error" : "success" });
        }
        if (!elementos.mensaje) {
            if (texto) {
                window.SSALFER_UI.toast(texto, { tipo: esError ? "error" : "success" });
            }
            return;
        }

        elementos.mensaje.textContent = texto || "";
        elementos.mensaje.hidden = !texto;
        elementos.mensaje.classList.toggle(
            "mostrar",
            Boolean(texto)
        );
        elementos.mensaje.classList.toggle(
            "error",
            Boolean(texto) && Boolean(esError)
        );
        elementos.mensaje.classList.toggle(
            "exito",
            Boolean(texto) && !esError
        );
    }

    function mostrarErrorSeguimiento(error) {
        console.error("Error de Seguimiento:", error);
        const mensaje = error?.status === 403
            ? "No tienes permiso para realizar esta acción."
            : error?.status === 401
                ? "Tu sesión terminó. Vuelve a iniciar sesión."
                : "No fue posible completar la operación. Revisa los datos e inténtalo de nuevo.";
        mostrarMensaje(mensaje, true);
    }

    function mostrarFormularioVisible(visible) {
        if (!elementos.formulario) return;

        elementos.formulario.hidden = !visible;
        elementos.formulario.style.display =
            visible ? "" : "none";
    }

    function opcionCatalogoPorId(mapa, id) {
        return mapa.get(Number(id)) || null;
    }

    function nombreCatalogo(mapa, id) {
        const opcion = opcionCatalogoPorId(mapa, id);

        return opcion?.nombre ||
            opcion?.codigo ||
            (id ? "Opción no disponible" : "—");
    }

    function llenarSelectCatalogo(
        select,
        opciones,
        textoInicial
    ) {
        if (!select) return;

        select.innerHTML = "";

        const inicial = document.createElement("option");
        inicial.value = "";
        inicial.textContent = textoInicial;

        select.appendChild(inicial);

        opciones.forEach(opcion => {
            const option = document.createElement("option");

            option.value =
                opcion.id_catalogo_opcion;

            option.textContent =
                opcion.nombre || opcion.codigo;

            option.dataset.codigo =
                opcion.codigo || "";

            select.appendChild(option);
        });
    }


    /* =====================================================
                        SESIÓN / PERMISOS
    ====================================================== */

    try {
        const sesion =
            await window.AuthAPI.obtenerSesionActual();

        const rol = sesion?.user?.rol;

        puedeCapturar =
            rol === "admin" ||
            rol === "operador";
    } catch (error) {
        mostrarErrorSeguimiento(error);
        return;
    }

    if (!puedeCapturar && elementos.btnNuevoEvento) {
        elementos.btnNuevoEvento.hidden = true;
        elementos.btnNuevoEvento.style.display = "none";
    }


    /* =====================================================
                        NAVEGACIÓN
    ====================================================== */

    elementos.btnVolver?.addEventListener(
        "click",
        () => {
            window.location.href =
                `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                    idProyectoNucleo
                )}`;
        }
    );


    /* =====================================================
                        CATÁLOGOS
    ====================================================== */

    /* QA UX: selector documental contextual */

    function asegurarDocumentoSeleccionable(idDocumento) {
        const id = Number(idDocumento);

        if (
            !elementos.documento ||
            !Number.isInteger(id) ||
            id <= 0
        ) {
            return;
        }

        const valor = String(id);

        const existe = Array.from(
            elementos.documento.options
        ).some(
            option => option.value === valor
        );

        if (existe) {
            return;
        }

        const option =
            document.createElement("option");

        option.value = valor;
        option.textContent =
            "Documento asociado no disponible en el listado";

        elementos.documento.appendChild(option);
    }


    window.addEventListener("ssalfer:documentos", async event => {
        const actual = elementos.documento?.value;
        await cargarDocumentos(event.detail);
        if (actual) { asegurarDocumentoSeleccionable(actual); elementos.documento.value = actual; }
    });

    async function cargarDocumentos(objetivoNuevo = null) {
        if (
            !elementos.documento ||
            !window.DocumentosAPI
        ) {
            return;
        }

        elementos.documento.innerHTML = `
            <option value="">
                Sin documento asociado
            </option>
        `;

        const consultas = [
            window.DocumentosAPI.listarPorEntidad(
                "proyecto_nucleo",
                idProyectoNucleo
            )
        ];

        if (objetivoNuevo?.tipo && Number(objetivoNuevo.id) > 0) consultas.push(window.DocumentosAPI.listarPorEntidad(objetivoNuevo.tipo, objetivoNuevo.id));

        try {
            if (
                window.NucleosAPI
                    ?.obtenerProyectoNucleo
            ) {
                try {
                    const contexto =
                        await window.NucleosAPI
                            .obtenerProyectoNucleo(
                                idProyectoNucleo
                            );

                    const idNucleo =
                        Number(
                            contexto?.id_nucleo
                        );

                    if (
                        Number.isInteger(idNucleo) &&
                        idNucleo > 0
                    ) {
                        consultas.push(
                            window.DocumentosAPI
                                .listarPorEntidad(
                                    "nucleo_agrario",
                                    idNucleo
                                )
                        );
                    }

                } catch (error) {
                    console.warn(
                        "No fue posible obtener el núcleo para ampliar el catálogo documental.",
                        error
                    );
                }
            }

            const resultados =
                await Promise.allSettled(
                    consultas
                );

            const documentos = [];
            const ids = new Set();

            resultados.forEach(resultado => {
                if (
                    resultado.status !==
                    "fulfilled"
                ) {
                    return;
                }

                const lista =
                    Array.isArray(
                        resultado.value
                    )
                        ? resultado.value
                        : [];

                lista.forEach(documento => {
                    const id =
                        Number(
                            documento
                                .id_documento
                        );

                    if (
                        !Number.isInteger(id) ||
                        id <= 0 ||
                        ids.has(id)
                    ) {
                        return;
                    }

                    ids.add(id);
                    documentos.push(documento);
                });
            });

            documentos.forEach(documento => {
                const id =
                    Number(
                        documento.id_documento
                    );

                const etiqueta =
                    documento.titulo ||
                    window.DocumentosAPI.nombreTipo(documento) ||
                    "Documento";

                const option =
                    document.createElement(
                        "option"
                    );

                option.value = String(id);
                option.textContent =
                    etiqueta;

                elementos.documento
                    .appendChild(option);
            });

        } catch (error) {
            console.warn(
                "No fue posible cargar los documentos relacionados.",
                error
            );
        }
    }

    async function cargarCatalogos() {
        [
            tiposEvento,
            motivos
        ] = await Promise.all([
            window.CatalogosAPI.obtenerOperativo(
                "tipo_evento_seguimiento"
            ),
            window.CatalogosAPI.obtenerOperativo(
                "motivo_seguimiento"
            )
        ]);

        tiposEvento =
            Array.isArray(tiposEvento)
                ? tiposEvento
                : [];

        motivos =
            Array.isArray(motivos)
                ? motivos
                : [];

        tipoPorId = new Map(
            tiposEvento.map(item => [
                Number(item.id_catalogo_opcion),
                item
            ])
        );

        motivoPorId = new Map(
            motivos.map(item => [
                Number(item.id_catalogo_opcion),
                item
            ])
        );

        llenarSelectCatalogo(
            elementos.tipoEvento,
            tiposEvento,
            "Selecciona una opción"
        );

        llenarSelectCatalogo(
            elementos.motivo,
            motivos,
            "Sin especificar"
        );
    }


    /* =====================================================
                        CARGAR EVENTOS
    ====================================================== */

    async function cargarEventos() {
        try {
            const respuesta =
                await window.SeguimientoAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            eventos =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            await cargarReferenciasEventos();
            mostrarEventos();
        } catch (error) {
            mostrarErrorSeguimiento(error);
        }
    }


    /* =====================================================
                        RESUMEN
    ====================================================== */

    function referenciaEvento(evento) {
        if (!evento.entidad_tipo || !evento.entidad_id) return "Evento general del núcleo";
        return referenciasEntidad.get(`${evento.entidad_tipo}:${evento.entidad_id}`)
            || `${nombresEntidad[evento.entidad_tipo] || "Registro"} · Referencia no disponible`;
    }

    async function cargarReferenciasEventos() {
        referenciasEntidad.clear();
        consultasEntidad.clear();
        const tipos = [...new Set(eventos.map(evento => evento.entidad_tipo).filter(Boolean))];
        const resultados = await Promise.allSettled(tipos.map(async tipo => {
            if (tiposEntidadSelectorDirecto.has(tipo)) {
                const lista = comoLista(await consultarUnaVez(`padres:${tipo}`, () => listarEntidadDirecta(tipo)));
                lista.forEach(item => referenciasEntidad.set(`${tipo}:${idEntidadDirecta(tipo, item)}`, etiquetaEntidadDirecta(tipo, item)));
                return;
            }
            const config = dependenciasEntidad[tipo];
            const padreTipo = config?.padre || (tipo === "parcela_titular" ? "parcela" : null);
            if (!padreTipo) return;
            const padres = comoLista(await consultarUnaVez(`padres:${padreTipo}`, () => listarEntidadDirecta(padreTipo)));
            const pendientes = new Set(eventos.filter(evento => evento.entidad_tipo === tipo).map(evento => Number(evento.entidad_id)));
            for (const padre of padres) {
                if (!pendientes.size) break;
                const idPadre = idEntidadDirecta(padreTipo, padre);
                let hijos;
                if (tipo === "parcela_titular") {
                    hijos = comoLista(await window.ParcelasAPI.listarTitulares(idPadre)).map(item => ({
                        id: Number(item.id_parcela_titular), etiqueta: etiquetaTitularParcela(item)
                    }));
                } else if (config.anidados && Array.isArray(padre[config.anidados])) {
                    hijos = await Promise.all(padre[config.anidados].map(async item => ({
                        id: Number(item[config.campo]), etiqueta: await etiquetaDependiente(tipo, item)
                    })));
                } else {
                    hijos = await listarHijos(tipo, idPadre);
                }
                hijos.forEach(hijo => {
                    referenciasEntidad.set(`${tipo}:${hijo.id}`, `${etiquetaEntidadDirecta(padreTipo, padre)} · ${hijo.etiqueta}`);
                    pendientes.delete(hijo.id);
                });
            }
        }));
        if (resultados.some(resultado => resultado.status === "rejected")) {
            window.SSALFER_UI.toast("No se pudieron cargar algunas referencias. Puedes volver a abrir Seguimiento para reintentar.", { tipo: "error" });
        }
    }

    function actualizarResumen() {
        elementos.totalEventos.textContent =
            eventos.length;

        elementos.totalGenerales.textContent =
            eventos.filter(
                item => item.ambito === "general"
            ).length;

        elementos.totalColectivos.textContent =
            eventos.filter(
                item => item.ambito === "colectivo"
            ).length;

        elementos.totalIndividuales.textContent =
            eventos.filter(
                item => item.ambito === "individual"
            ).length;
    }


    /* =====================================================
                        TABLA
    ====================================================== */

    function mostrarEventos() {
        if (!elementos.tabla) return;

        elementos.tabla.innerHTML = "";

        if (!eventos.length) {
            elementos.tabla.innerHTML = `
                <tr>
                    <td colspan="7" class="tabla-vacia">
                        No hay eventos de seguimiento registrados.
                    </td>
                </tr>
            `;

            actualizarResumen();
            return;
        }

        const ordenados = [...eventos].sort(
            (a, b) => {
                const fechaA =
                    a.fecha_evento || "";

                const fechaB =
                    b.fecha_evento || "";

                if (fechaA !== fechaB) {
                    return fechaB.localeCompare(fechaA);
                }

                return Number(
                    b.id_seguimiento_evento
                ) - Number(
                    a.id_seguimiento_evento
                );
            }
        );

        ordenados.forEach(evento => {
            const fila =
                document.createElement("tr");

            const ambito =
                evento.ambito || "general";

            const entidad = referenciaEvento(evento);

            const accionesCaptura =
                puedeCapturar
                    ? `
                        <button
                            type="button"
                            class="btn-tabla"
                            title="Editar evento"
                            data-editar="${evento.id_seguimiento_evento}">
                            <i class="bi bi-pencil"></i>
                        </button>

                        <button
                            type="button"
                            class="btn-tabla"
                            title="Eliminar evento"
                            data-eliminar="${evento.id_seguimiento_evento}">
                            <i class="bi bi-trash"></i>
                        </button>
                    `
                    : "";

            fila.innerHTML = `
                <td>
                    ${escaparHTML(
                        window.SSALFER_FORMAT?.formatearFecha(evento.fecha_evento)
                        || evento.fecha_evento
                        || "—"
                    )}
                </td>

                <td>
                    <span class="etiqueta-tabla ${escaparHTML(
                        ambito
                    )}">
                        ${escaparHTML(
                            nombresAmbito[ambito] ||
                            ambito
                        )}
                    </span>
                </td>

                <td>
                    ${escaparHTML(
                        nombreCatalogo(
                            tipoPorId,
                            evento.id_tipo_evento
                        )
                    )}
                </td>

                <td>
                    ${escaparHTML(entidad)}
                </td>

                <td>
                    ${escaparHTML(
                        nombreCatalogo(
                            motivoPorId,
                            evento.id_motivo
                        )
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        evento.detalle || "—"
                    )}
                </td>

                <td>
                    <div class="acciones-tabla">
                        <button
                            type="button"
                            class="btn-tabla"
                            title="Consultar evento"
                            data-consultar="${evento.id_seguimiento_evento}">
                            <i class="bi bi-eye"></i>
                        </button>

                        ${accionesCaptura}
                    </div>
                </td>
            `;

            elementos.tabla.appendChild(fila);
        });

        conectarAccionesTabla();
        actualizarResumen();
    }


    /* =====================================================
                        CONSULTAR
    ====================================================== */

    function consultarEvento(id) {
        const evento =
            eventos.find(
                item =>
                    Number(
                        item.id_seguimiento_evento
                    ) === Number(id)
            );

        if (!evento) return;

        const entidad = referenciaEvento(evento);

        window.SSALFER_UI.verDatos("Evento de seguimiento", {
            Fecha: window.SSALFER_FORMAT.formatearFecha(evento.fecha_evento),
            Ámbito: nombresAmbito[evento.ambito] || "—",
            Tipo: nombreCatalogo(tipoPorId, evento.id_tipo_evento),
            Motivo: nombreCatalogo(motivoPorId, evento.id_motivo),
            "Relacionado con": entidad,
            Fuente: evento.fuente || "—",
            Documento: evento.id_documento
                ? Array.from(elementos.documento.options).find(opcion =>
                    Number(opcion.value) === Number(evento.id_documento))?.textContent
                    || "Documento asociado no disponible en el listado"
                : "Sin documento asociado",
            Detalle: evento.detalle || "—"
        });
    }


    /* =====================================================
                        FORMULARIO
    ====================================================== */

    function configurarCamposInmutables(bloqueados) {
        [
            elementos.ambito,
            elementos.tipoEvento,
            elementos.entidadTipo,
            elementos.entidadContextoSelector,
            elementos.entidadSelector,
            elementos.entidadId,
            elementos.motivo
        ].forEach(elemento => {
            if (elemento) {
                elemento.disabled = bloqueados;
            }
        });
    }

    function limpiarFormulario() {
        elementos.form?.reset();

        idEventoEditando = null;

        configurarCamposInmutables(false);
        void actualizarControlEntidad();

        mostrarMensaje("");

        if (tituloFormulario) {
            tituloFormulario.textContent =
                "Registrar evento de seguimiento";
        }

        if (botonGuardar) {
            botonGuardar.innerHTML = `
                <i class="bi bi-check-lg"></i>
                Registrar evento
            `;
        }
    }

    function abrirNuevoEvento() {
        if (!puedeCapturar || guardando) return;

        limpiarFormulario();

        mostrarFormularioVisible(true);

        window.SSALFER_UI?.desplazarA(elementos.formulario);

        elementos.ambito?.focus({ preventScroll: true });
    }

    async function abrirEdicion(id) {
        if (!puedeCapturar || guardando) return;

        try {
            const evento =
                await window.SeguimientoAPI.obtener(id);

            idEventoEditando =
                Number(evento.id_seguimiento_evento);

            elementos.ambito.value =
                evento.ambito || "";

            elementos.tipoEvento.value =
                evento.id_tipo_evento || "";

            elementos.entidadTipo.value =
                evento.entidad_tipo || "";

            elementos.entidadId.value =
                evento.entidad_id || "";
            await actualizarControlEntidad(
                evento.entidad_id
            );

            elementos.motivo.value =
                evento.id_motivo || "";

            elementos.fechaEvento.value =
                evento.fecha_evento || "";

            elementos.fuente.value =
                evento.fuente || "";

            elementos.detalle.value =
                evento.detalle || "";

            asegurarDocumentoSeleccionable(
                evento.id_documento
            );

            elementos.documento.value =
                evento.id_documento || "";

            configurarCamposInmutables(true);

            if (tituloFormulario) {
                tituloFormulario.textContent =
                    "Editar evento de seguimiento";
            }

            if (botonGuardar) {
                botonGuardar.innerHTML = `
                    <i class="bi bi-check-lg"></i>
                    Guardar cambios
                `;
            }

            mostrarMensaje("");

            mostrarFormularioVisible(true);

            window.SSALFER_UI?.desplazarA(elementos.formulario);

        } catch (error) {
            mostrarErrorSeguimiento(error);
        }
    }

    elementos.btnNuevoEvento?.addEventListener(
        "click",
        abrirNuevoEvento
    );

    elementos.btnCancelarEvento?.addEventListener(
        "click",
        () => {
            limpiarFormulario();
            mostrarFormularioVisible(false);
        }
    );


    /* =====================================================
                        VALIDACIÓN
    ====================================================== */

    function validarCreacion() {
        const ambito =
            elementos.ambito.value;

        const idTipoEvento =
            Number(elementos.tipoEvento.value);

        const entidadTipo =
            valorOpcionalTexto(
                elementos.entidadTipo
            );

        const entidadId =
            valorOpcionalNumero(
                elementos.entidadId
            );

        const idMotivo =
            valorOpcionalNumero(
                elementos.motivo
            );

        const idDocumento =
            valorOpcionalNumero(
                elementos.documento
            );

        const detalle =
            valorOpcionalTexto(
                elementos.detalle
            );

        if (!ambito) {
            mostrarMensaje(
                "Selecciona el ámbito del evento.",
                true
            );
            return false;
        }

        if (
            !Number.isInteger(idTipoEvento) ||
            idTipoEvento <= 0
        ) {
            mostrarMensaje(
                "Selecciona el tipo de evento.",
                true
            );
            return false;
        }

        if (
            entidadTipo &&
            !Number.isInteger(entidadId)
        ) {
            mostrarMensaje(
                "Selecciona el registro con el que deseas relacionar el evento.",
                true
            );
            return false;
        }

        if (
            !entidadTipo &&
            elementos.entidadId.value.trim()
        ) {
            mostrarMensaje(
                "Selecciona un registro relacionado o elige Evento general del núcleo.",
                true
            );
            return false;
        }

        if (Number.isNaN(idMotivo)) {
            mostrarMensaje(
                "El motivo seleccionado no es válido.",
                true
            );
            return false;
        }

        if (Number.isNaN(idDocumento)) {
            mostrarMensaje(
                "El documento seleccionado no es válido.",
                true
            );
            return false;
        }

        const tipo =
            opcionCatalogoPorId(
                tipoPorId,
                idTipoEvento
            );

        const motivo =
            idMotivo
                ? opcionCatalogoPorId(
                    motivoPorId,
                    idMotivo
                )
                : null;

        const codigoTipo =
            tipo?.codigo || "";

        const codigoMotivo =
            motivo?.codigo || "";



        const fechaEvento =
            elementos.fechaEvento.value.trim();

        if (
            [
                "inicio",
                "suspension",
                "reapertura",
                "cierre",
                "cambio_alcance"
            ].includes(codigoTipo) &&
            !fechaEvento
        ) {
            mostrarMensaje(
                "Este tipo de evento requiere indicar la fecha del evento.",
                true
            );

            elementos.fechaEvento.focus();

            return false;
        }




        if (
            codigoTipo === "suspension" &&
            !idMotivo
        ) {
            mostrarMensaje(
                "Una suspensión requiere indicar un motivo.",
                true
            );
            return false;
        }

        if (
            codigoTipo === "reapertura" &&
            !detalle
        ) {
            mostrarMensaje(
                "Una reapertura requiere detalle.",
                true
            );
            return false;
        }

        if (
            ["cierre", "cambio_alcance"]
                .includes(codigoTipo) &&
            (!idMotivo || !detalle)
        ) {
            mostrarMensaje(
                "Este tipo de evento requiere motivo y detalle.",
                true
            );
            return false;
        }

        if (
            codigoMotivo === "otro" &&
            !detalle
        ) {
            mostrarMensaje(
                "Cuando el motivo es «Otro» debes indicar el detalle.",
                true
            );
            return false;
        }

        if (
            codigoTipo === "continuacion_asamblea" &&
            ![
                "asamblea",
                "asamblea_convocatoria"
            ].includes(entidadTipo)
        ) {
            mostrarMensaje(
                "La continuación de asamblea debe relacionarse con una asamblea o convocatoria.",
                true
            );
            return false;
        }

        if (
            codigoMotivo === "dominio_pleno" &&
            (
                ambito !== "individual" ||
                ![
                    "parcela",
                    "afectacion",
                    "unidad_agraria"
                ].includes(entidadTipo)
            )
        ) {
            mostrarMensaje(
                "Dominio pleno requiere ámbito individual y una parcela, afectación o unidad agraria relacionada.",
                true
            );
            return false;
        }

        if (
            [
                "conflicto_titularidad",
                "juicio_agrario"
            ].includes(codigoMotivo) &&
            (
                ambito !== "individual" ||
                ![
                    "parcela",
                    "parcela_titular",
                    "afectacion",
                    "unidad_agraria"
                ].includes(entidadTipo)
            )
        ) {
            mostrarMensaje(
                "Este motivo requiere ámbito individual y una entidad compatible.",
                true
            );
            return false;
        }

        return true;
    }

    function validarEdicion() {
        const idDocumento =
            valorOpcionalNumero(
                elementos.documento
            );

        if (Number.isNaN(idDocumento)) {
            mostrarMensaje(
                "El documento seleccionado no es válido.",
                true
            );
            return false;
        }

        return true;
    }


    /* =====================================================
                        GUARDAR
    ====================================================== */

    elementos.form?.addEventListener(
        "submit",
        async eventoSubmit => {
            eventoSubmit.preventDefault();

            if (!puedeCapturar || guardando) return;

            mostrarMensaje("");
            guardando = true;
            botonGuardar.disabled = true;
            elementos.btnNuevoEvento.disabled = true;
            elementos.btnCancelarEvento.disabled = true;

            try {
                if (idEventoEditando) {
                    if (!validarEdicion()) {
                        return;
                    }

                    const payload = {
                        fecha_evento:
                            valorOpcionalTexto(
                                elementos.fechaEvento
                            ),

                        detalle:
                            valorOpcionalTexto(
                                elementos.detalle
                            ),

                        id_documento:
                            valorOpcionalNumero(
                                elementos.documento
                            ),

                        fuente:
                            valorOpcionalTexto(
                                elementos.fuente
                            )
                    };

                    await window.SeguimientoAPI.actualizar(
                        idEventoEditando,
                        payload
                    );

                    mostrarMensaje(
                        "Evento actualizado correctamente."
                    );

                } else {
                    if (!validarCreacion()) {
                        return;
                    }

                    const payload = {
                        entidad_tipo:
                            valorOpcionalTexto(
                                elementos.entidadTipo
                            ),

                        entidad_id:
                            valorOpcionalNumero(
                                elementos.entidadId
                            ),

                        ambito:
                            elementos.ambito.value,

                        id_tipo_evento:
                            Number(
                                elementos.tipoEvento.value
                            ),

                        id_motivo:
                            valorOpcionalNumero(
                                elementos.motivo
                            ),

                        fecha_evento:
                            valorOpcionalTexto(
                                elementos.fechaEvento
                            ),

                        detalle:
                            valorOpcionalTexto(
                                elementos.detalle
                            ),

                        id_documento:
                            valorOpcionalNumero(
                                elementos.documento
                            ),

                        fuente:
                            valorOpcionalTexto(
                                elementos.fuente
                            )
                    };

                    await window.SeguimientoAPI.crear(
                        idProyectoNucleo,
                        payload
                    );

                    mostrarMensaje(
                        "Evento registrado correctamente."
                    );
                }

                await cargarEventos();

                limpiarFormulario();
                mostrarFormularioVisible(false);

            } catch (error) {
                mostrarErrorSeguimiento(error);
            } finally {
                guardando = false;
                botonGuardar.disabled = false;
                elementos.btnNuevoEvento.disabled = false;
                elementos.btnCancelarEvento.disabled = false;
            }
        }
    );


    /* =====================================================
                        ELIMINAR
    ====================================================== */

    async function eliminarEvento(id) {
        if (!puedeCapturar) return;

        let limpio = "";
        const confirmacion = window.SSALFER_UI.abrirModal({
            titulo: "Dar de baja el evento",
            contenido: `<p>Indica el motivo de la baja. Esta acción quedará registrada.</p>
                <label for="motivoBajaSeguimiento">Motivo de la baja</label>
                <textarea id="motivoBajaSeguimiento" rows="3" required minlength="3"></textarea>
                <p id="errorBajaSeguimiento" role="alert" hidden>El motivo debe contener al menos 3 caracteres.</p>`,
            acciones: [
                { valor: false, texto: "Cancelar" },
                { valor: true, texto: "Dar de baja", principal: true }
            ]
        });
        const campoMotivo = document.getElementById("motivoBajaSeguimiento");
        const modal = campoMotivo.closest(".ssalfer-modal-backdrop");
        modal.addEventListener("click", event => {
            if (!event.target.closest('[data-modal-accion="1"]')) return;
            limpio = campoMotivo.value.trim();
            if (limpio.length < 3) {
                event.stopImmediatePropagation();
                document.getElementById("errorBajaSeguimiento").hidden = false;
                campoMotivo.focus();
            }
        }, true);
        campoMotivo.focus();
        if (!await confirmacion) return;

        try {
            await window.SeguimientoAPI.eliminar(
                id,
                limpio
            );

            await cargarEventos();

            window.SSALFER_UI.toast("Evento dado de baja correctamente.");

        } catch (error) {
            mostrarErrorSeguimiento(error);
        }
    }


    /* =====================================================
                    ACCIONES DE TABLA
    ====================================================== */

    function conectarAccionesTabla() {
        elementos.tabla
            ?.querySelectorAll("[data-consultar]")
            .forEach(boton => {
                boton.addEventListener(
                    "click",
                    () => consultarEvento(
                        boton.dataset.consultar
                    )
                );
            });

        elementos.tabla
            ?.querySelectorAll("[data-editar]")
            .forEach(boton => {
                boton.addEventListener(
                    "click",
                    () => abrirEdicion(
                        boton.dataset.editar
                    )
                );
            });

        elementos.tabla
            ?.querySelectorAll("[data-eliminar]")
            .forEach(boton => {
                boton.addEventListener(
                    "click",
                    () => eliminarEvento(
                        boton.dataset.eliminar
                    )
                );
            });
    }


    /* =====================================================
                        INICIALIZACIÓN
    ====================================================== */

    try {
        await cargarCatalogos();
        await cargarDocumentos();
        await cargarEventos();
    } catch (error) {
        mostrarErrorSeguimiento(error);
    }
});
