document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros = new URLSearchParams(window.location.search);
    const idProyectoNucleo = Number(
        parametros.get("id_proyecto_nucleo") ||
        document.querySelector(".contenedor")?.dataset.proyectoNucleoId
    );

    if (!Number.isInteger(idProyectoNucleo) || idProyectoNucleo <= 0) {
        alert("Falta un id_proyecto_nucleo válido.");
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
        if (!elementos.mensaje) {
            if (texto) {
                alert(texto);
            }
            return;
        }

        elementos.mensaje.textContent = texto || "";
        elementos.mensaje.hidden = !texto;

        elementos.mensaje.classList.toggle(
            "error",
            Boolean(esError)
        );
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
            (id ? `#${id}` : "—");
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
        window.ClienteAPI.mostrarErrorAPI(error);
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

            mostrarEventos();
        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(error);
        }
    }


    /* =====================================================
                        RESUMEN
    ====================================================== */

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

            const entidad =
                evento.entidad_tipo &&
                evento.entidad_id

                    ? `${
                        nombresEntidad[
                            evento.entidad_tipo
                        ] ||
                        evento.entidad_tipo
                    } #${evento.entidad_id}`

                    : "Evento general del núcleo";

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
                        evento.fecha_evento || "—"
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

        const entidad =
            evento.entidad_tipo
                ? `${
                    nombresEntidad[
                        evento.entidad_tipo
                    ] ||
                    evento.entidad_tipo
                } #${evento.entidad_id}`
                : "Evento general del núcleo";

        alert(
            [
                `Evento #${evento.id_seguimiento_evento}`,
                "",
                `Fecha: ${evento.fecha_evento || "—"}`,
                `Ámbito: ${nombresAmbito[evento.ambito] || evento.ambito}`,
                `Tipo: ${nombreCatalogo(tipoPorId, evento.id_tipo_evento)}`,
                `Motivo: ${nombreCatalogo(motivoPorId, evento.id_motivo)}`,
                `Relacionado con: ${entidad}`,
                `Fuente: ${evento.fuente || "—"}`,
                `Documento: ${evento.id_documento ? `#${evento.id_documento}` : "—"}`,
                "",
                `Detalle: ${evento.detalle || "—"}`
            ].join("\n")
        );
    }


    /* =====================================================
                        FORMULARIO
    ====================================================== */

    function configurarCamposInmutables(bloqueados) {
        [
            elementos.ambito,
            elementos.tipoEvento,
            elementos.entidadTipo,
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
        if (!puedeCapturar) return;

        limpiarFormulario();

        mostrarFormularioVisible(true);

        elementos.formulario?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

        elementos.ambito?.focus();
    }

    async function abrirEdicion(id) {
        if (!puedeCapturar) return;

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

            elementos.motivo.value =
                evento.id_motivo || "";

            elementos.fechaEvento.value =
                evento.fecha_evento || "";

            elementos.fuente.value =
                evento.fuente || "";

            elementos.detalle.value =
                evento.detalle || "";

            elementos.documento.value =
                evento.id_documento || "";

            configurarCamposInmutables(true);

            if (tituloFormulario) {
                tituloFormulario.textContent =
                    `Editar evento #${idEventoEditando}`;
            }

            if (botonGuardar) {
                botonGuardar.innerHTML = `
                    <i class="bi bi-check-lg"></i>
                    Guardar cambios
                `;
            }

            mostrarMensaje("");

            mostrarFormularioVisible(true);

            elementos.formulario?.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(error);
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
                "Si relacionas el evento con una entidad, debes indicar un identificador válido.",
                true
            );
            return false;
        }

        if (
            !entidadTipo &&
            elementos.entidadId.value.trim()
        ) {
            mostrarMensaje(
                "Selecciona el tipo de entidad relacionada o elimina el identificador.",
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
                "El identificador del documento no es válido.",
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
                "El identificador del documento no es válido.",
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

            if (!puedeCapturar) return;

            mostrarMensaje("");

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

                setTimeout(() => {
                    limpiarFormulario();
                    mostrarFormularioVisible(false);
                }, 500);

            } catch (error) {
                window.ClienteAPI.mostrarErrorAPI(
                    error,
                    elementos.mensaje
                );
            }
        }
    );


    /* =====================================================
                        ELIMINAR
    ====================================================== */

    async function eliminarEvento(id) {
        if (!puedeCapturar) return;

        const motivo = prompt(
            "Indica el motivo de la baja del evento:"
        );

        if (motivo === null) return;

        const limpio = motivo.trim();

        if (limpio.length < 3) {
            alert(
                "El motivo debe contener al menos 3 caracteres."
            );
            return;
        }

        const confirmar = confirm(
            "¿Deseas dar de baja este evento de seguimiento?"
        );

        if (!confirmar) return;

        try {
            await window.SeguimientoAPI.eliminar(
                id,
                limpio
            );

            await cargarEventos();

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(error);
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
        await cargarEventos();
    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(error);
    }
});