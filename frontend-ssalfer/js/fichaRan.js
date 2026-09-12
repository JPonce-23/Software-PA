document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idTramiteRan = Number(
        parametros.get("id_tramite_ran") ||
        parametros.get("id") ||
        document.querySelector(".contenedor")
            ?.dataset.tramiteRanId
    );

    if (
        !Number.isInteger(idTramiteRan) ||
        idTramiteRan <= 0
    ) {
        alert(
            "No se encontró un id_tramite_ran válido."
        );

        window.location.href =
            "/dashboard.html";

        return;
    }


    /* =====================================================
                        ELEMENTOS
    ====================================================== */

    const elementos = {
        btnVolver:
            document.getElementById(
                "btnVolver"
            ),

        btnEditarTramite:
            document.getElementById(
                "btnEditarTramite"
            ),

        btnEditarDatos:
            document.getElementById(
                "btnEditarDatos"
            ),

        btnAgregarEvento:
            document.getElementById(
                "btnAgregarEvento"
            ),

        idTramite:
            document.getElementById(
                "idTramite"
            ),

        nombreNucleo:
            document.getElementById(
                "nombreNucleo"
            ),

        nombreProyecto:
            document.getElementById(
                "nombreProyecto"
            ),

        fechaProgramada:
            document.getElementById(
                "fechaProgramada"
            ),

        referenciaExpediente:
            document.getElementById(
                "referenciaExpediente"
            ),

        tipoOrigen:
            document.getElementById(
                "tipoOrigen"
            ),

        origenTipo:
            document.getElementById(
                "origenTipo"
            ),

        origenId:
            document.getElementById(
                "origenId"
            ),

        origenReferencia:
            document.getElementById(
                "origenReferencia"
            ),

        eventosTabla:
            document.getElementById(
                "eventosTabla"
            ),

        totalEventos:
            document.getElementById(
                "totalEventos"
            ),

        ultimoEvento:
            document.getElementById(
                "ultimoEvento"
            ),

        detalleUltimoEvento:
            document.getElementById(
                "detalleUltimoEvento"
            ),

        iconoEstado:
            document.getElementById(
                "iconoEstado"
            )
    };


    /* =====================================================
                        ESTADO
    ====================================================== */

    let tramite = null;
    let contexto = null;

    let eventos = [];

    let tiposEvento = [];
    let tipoEventoPorId =
        new Map();

    let puedeCapturar = false;

    let idEventoEditando = null;

    let seccionFormularioEvento = null;


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

    function texto(
        valor,
        respaldo = "—"
    ) {
        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return respaldo;
        }

        return String(valor);
    }

    function nombreTipoEvento(id) {
        const opcion =
            tipoEventoPorId.get(
                Number(id)
            );

        return opcion?.nombre ||
            opcion?.codigo ||
            (id ? `#${id}` : "—");
    }

    function numeroOpcional(elemento) {
        const valor =
            elemento?.value?.trim();

        if (!valor) {
            return null;
        }

        const numero =
            Number(valor);

        return Number.isInteger(numero) &&
            numero > 0

            ? numero
            : NaN;
    }

    function textoOpcional(elemento) {
        const valor =
            elemento?.value?.trim();

        return valor || null;
    }


    /* =====================================================
                        SESIÓN
    ====================================================== */

    try {
        const sesion =
            await window.AuthAPI
                .obtenerSesionActual();

        const rol =
            sesion?.user?.rol;

        puedeCapturar =
            rol === "admin" ||
            rol === "operador";

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(error);

        return;
    }


    /*
     * El backend NO tiene endpoint para modificar
     * TramiteRan directamente.
     *
     * Por lo tanto ocultamos los dos botones que
     * actualmente prometen una edición inexistente.
     */
    [
        elementos.btnEditarTramite,
        elementos.btnEditarDatos
    ].forEach(boton => {
        if (boton) {
            boton.hidden = true;
            boton.style.display = "none";
        }
    });

    if (
        !puedeCapturar &&
        elementos.btnAgregarEvento
    ) {
        elementos.btnAgregarEvento.hidden =
            true;

        elementos.btnAgregarEvento
            .style.display = "none";
    }


    /* =====================================================
                        CATÁLOGO RAN
    ====================================================== */

    async function cargarCatalogo() {
        const respuesta =
            await window.CatalogosAPI
                .obtenerOperativo(
                    "tipo_evento_ran"
                );

        tiposEvento =
            Array.isArray(respuesta)
                ? respuesta
                : [];

        tipoEventoPorId =
            new Map(
                tiposEvento.map(item => [
                    Number(
                        item.id_catalogo_opcion
                    ),
                    item
                ])
            );
    }


    /* =====================================================
                        CARGAR TRÁMITE
    ====================================================== */

    async function cargarTramite() {
        const [
            tramiteReal,
            eventosReales
        ] = await Promise.all([
            window.TramitesRanAPI.obtener(
                idTramiteRan
            ),

            window.TramitesRanAPI.listarEventos(
                idTramiteRan
            )
        ]);

        tramite =
            tramiteReal;

        eventos =
            Array.isArray(eventosReales)
                ? eventosReales
                : [];

        if (tramite?.id_proyecto_nucleo) {
            try {
                contexto =
                    await window.NucleosAPI
                        .obtenerProyectoNucleo(
                            tramite.id_proyecto_nucleo
                        );

            } catch (error) {
                console.warn(
                    "No fue posible cargar el contexto del proyecto-núcleo.",
                    error
                );

                contexto = null;
            }
        }

        mostrarInformacion();
        mostrarOrigen();
        mostrarEventos();
        actualizarUltimoEvento();
    }


    /* =====================================================
                    INFORMACIÓN GENERAL
    ====================================================== */

    function mostrarInformacion() {
        elementos.idTramite.textContent =
            texto(
                tramite?.id_tramite_ran
            );

        elementos.nombreNucleo.textContent =
            texto(
                contexto?.nombre_nucleo,
                tramite?.id_nucleo
                    ? `Núcleo #${tramite.id_nucleo}`
                    : "—"
            );

        elementos.nombreProyecto.textContent =
            texto(
                contexto?.nombre_proyecto,
                "—"
            );

        elementos.fechaProgramada.textContent =
            texto(
                tramite?.fecha_programada_ingreso
            );

        elementos.referenciaExpediente.textContent =
            texto(
                tramite?.referencia_expediente
            );
    }


    /* =====================================================
                        ORIGEN
    ====================================================== */

    function obtenerOrigen() {
        if (tramite?.id_asamblea) {
            return {
                tipo: "Asamblea",
                id: tramite.id_asamblea,
                referencia:
                    `Asamblea #${tramite.id_asamblea}`
            };
        }

        if (tramite?.id_convenio) {
            return {
                tipo: "Convenio",
                id: tramite.id_convenio,
                referencia:
                    `Convenio #${tramite.id_convenio}`
            };
        }

        if (tramite?.id_orv) {
            return {
                tipo: "ORV",
                id: tramite.id_orv,
                referencia:
                    `ORV #${tramite.id_orv}`
            };
        }

        return {
            tipo: "—",
            id: null,
            referencia: "—"
        };
    }

    function mostrarOrigen() {
        const origen =
            obtenerOrigen();

        elementos.tipoOrigen.textContent =
            origen.tipo;

        elementos.origenTipo.textContent =
            origen.tipo;

        elementos.origenId.textContent =
            origen.id || "—";

        elementos.origenReferencia.textContent =
            origen.referencia;
    }


    /* =====================================================
                        TABLA EVENTOS
    ====================================================== */

    function mostrarEventos() {
        if (!elementos.eventosTabla) {
            return;
        }

        elementos.eventosTabla.innerHTML =
            "";

        elementos.totalEventos.textContent =
            eventos.length;

        if (!eventos.length) {
            elementos.eventosTabla.innerHTML = `
                <tr>
                    <td
                        colspan="9"
                        class="tabla-vacia">
                        No hay eventos registrados.
                    </td>
                </tr>
            `;

            return;
        }

        const ordenados =
            [...eventos].sort(
                (a, b) =>
                    Number(a.ordinal) -
                    Number(b.ordinal)
            );

        ordenados.forEach(evento => {
            const fila =
                document.createElement("tr");

            fila.innerHTML = `
                <td>
                    ${escaparHTML(
                        evento.ordinal
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        nombreTipoEvento(
                            evento.id_tipo_evento
                        )
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        texto(
                            evento.fecha_evento
                        )
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        texto(
                            evento.numero_solicitud
                        )
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        texto(
                            evento.resultado
                        )
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        texto(
                            evento.calificacion
                        )
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        texto(
                            evento.folio_referencia
                        )
                    )}
                </td>

                <td>
                    ${
                        evento.id_documento
                            ? `
                                <span class="etiqueta-tabla">
                                    <i class="bi bi-paperclip"></i>
                                    Documento #${escaparHTML(
                                        evento.id_documento
                                    )}
                                </span>
                            `
                            : `
                                <span class="etiqueta-tabla sin-documento">
                                    Sin documento
                                </span>
                            `
                    }
                </td>

                <td>
                    <div class="acciones-tabla">

                        <button
                            type="button"
                            class="btn-tabla"
                            title="Ver evento"
                            data-ver-evento="${evento.id_evento_ran}">
                            <i class="bi bi-eye"></i>
                        </button>

                        ${
                            puedeCapturar
                                ? `
                                    <button
                                        type="button"
                                        class="btn-tabla"
                                        title="Editar evento"
                                        data-editar-evento="${evento.id_evento_ran}">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                `
                                : ""
                        }

                    </div>
                </td>
            `;

            elementos.eventosTabla
                .appendChild(fila);
        });
    }


    /* =====================================================
                        CONSULTAR EVENTO
    ====================================================== */

    function consultarEvento(idEvento) {
        const evento =
            eventos.find(
                item =>
                    Number(
                        item.id_evento_ran
                    ) ===
                    Number(idEvento)
            );

        if (!evento) {
            return;
        }

        alert(
            [
                `Evento RAN #${evento.id_evento_ran}`,
                "",
                `Ordinal: ${evento.ordinal}`,
                `Tipo: ${nombreTipoEvento(evento.id_tipo_evento)}`,
                `Fecha: ${evento.fecha_evento || "—"}`,
                `Número de solicitud: ${evento.numero_solicitud || "—"}`,
                `Resultado: ${evento.resultado || "—"}`,
                `Calificación: ${evento.calificacion || "—"}`,
                `Folio / referencia: ${evento.folio_referencia || "—"}`,
                `Documento: ${
                    evento.id_documento
                        ? `#${evento.id_documento}`
                        : "—"
                }`
            ].join("\n")
        );
    }


    /* =====================================================
                FORMULARIO DINÁMICO DEL EVENTO
    ====================================================== */

    function crearFormularioEvento() {
        if (seccionFormularioEvento) {
            return;
        }

        const bloqueSeguimiento =
            elementos.btnAgregarEvento
                ?.closest(".bloque");

        if (!bloqueSeguimiento) {
            return;
        }

        seccionFormularioEvento =
            document.createElement(
                "section"
            );

        seccionFormularioEvento.className =
            "bloque";

        seccionFormularioEvento.id =
            "formularioEventoRan";

        seccionFormularioEvento.hidden =
            true;

        seccionFormularioEvento.innerHTML = `
            <div class="bloque-titulo">

                <div class="bloque-titulo-info">

                    <span class="numero-seccion">
                        +
                    </span>

                    <div>
                        <h2 id="tituloFormularioEventoRan">
                            Registrar evento RAN
                        </h2>

                        <p>
                            Agrega un movimiento al seguimiento
                            del trámite ante el RAN.
                        </p>
                    </div>

                </div>

            </div>

            <form id="formEventoRan">

                <div class="form-grid">

                    <div class="campo">

                        <label for="ordinalEventoRan">
                            Ordinal
                            <span class="obligatorio">*</span>
                        </label>

                        <input
                            type="number"
                            min="1"
                            step="1"
                            id="ordinalEventoRan"
                            required>

                    </div>

                    <div class="campo">

                        <label for="tipoEventoRan">
                            Tipo de evento
                            <span class="obligatorio">*</span>
                        </label>

                        <select
                            id="tipoEventoRan"
                            required>
                        </select>

                    </div>

                    <div class="campo">

                        <label for="fechaEventoRan">
                            Fecha
                        </label>

                        <input
                            type="date"
                            id="fechaEventoRan">

                    </div>

                    <div class="campo">

                        <label for="numeroSolicitudRan">
                            Número de solicitud
                        </label>

                        <input
                            type="text"
                            maxlength="150"
                            id="numeroSolicitudRan">

                    </div>

                    <div class="campo campo-completo">

                        <label for="resultadoEventoRan">
                            Resultado
                        </label>

                        <input
                            type="text"
                            maxlength="250"
                            id="resultadoEventoRan">

                    </div>

                    <div class="campo campo-completo">

                        <label for="calificacionEventoRan">
                            Calificación
                        </label>

                        <textarea
                            id="calificacionEventoRan"
                            rows="3"></textarea>

                    </div>

                    <div class="campo">

                        <label for="folioEventoRan">
                            Folio / referencia
                        </label>

                        <input
                            type="text"
                            maxlength="200"
                            id="folioEventoRan">

                    </div>

                    <div class="campo">

                        <label for="documentoEventoRan">
                            ID de documento
                        </label>

                        <input
                            type="number"
                            min="1"
                            step="1"
                            id="documentoEventoRan"
                            placeholder="Opcional">

                    </div>

                </div>

                <div class="acciones-formulario">

                    <button
                        type="button"
                        class="btn-secundario"
                        id="btnCancelarEventoRan">
                        Cancelar
                    </button>

                    <button
                        type="submit"
                        class="btn-principal"
                        id="btnGuardarEventoRan">

                        <i class="bi bi-check-lg"></i>
                        Guardar evento

                    </button>

                </div>

            </form>
        `;

        bloqueSeguimiento.insertAdjacentElement(
            "afterend",
            seccionFormularioEvento
        );

        llenarTiposEvento();

        document
            .getElementById(
                "btnCancelarEventoRan"
            )
            ?.addEventListener(
                "click",
                cerrarFormularioEvento
            );

        document
            .getElementById(
                "formEventoRan"
            )
            ?.addEventListener(
                "submit",
                guardarEvento
            );
    }

    function llenarTiposEvento() {
        const select =
            document.getElementById(
                "tipoEventoRan"
            );

        if (!select) {
            return;
        }

        select.innerHTML = `
            <option value="">
                Selecciona una opción
            </option>
        `;

        tiposEvento.forEach(item => {
            const option =
                document.createElement(
                    "option"
                );

            option.value =
                item.id_catalogo_opcion;

            option.textContent =
                item.nombre ||
                item.codigo ||
                `#${item.id_catalogo_opcion}`;

            select.appendChild(option);
        });
    }

    function siguienteOrdinal() {
        if (!eventos.length) {
            return 1;
        }

        return Math.max(
            ...eventos.map(
                item =>
                    Number(item.ordinal) || 0
            )
        ) + 1;
    }

    function abrirNuevoEvento() {
        if (!puedeCapturar) {
            return;
        }

        crearFormularioEvento();

        idEventoEditando =
            null;

        const form =
            document.getElementById(
                "formEventoRan"
            );

        form?.reset();

        const ordinal =
            document.getElementById(
                "ordinalEventoRan"
            );

        if (ordinal) {
            ordinal.disabled = false;
            ordinal.value =
                siguienteOrdinal();
        }

        const titulo =
            document.getElementById(
                "tituloFormularioEventoRan"
            );

        if (titulo) {
            titulo.textContent =
                "Registrar evento RAN";
        }

        seccionFormularioEvento.hidden =
            false;

        seccionFormularioEvento
            .style.display = "";

        seccionFormularioEvento.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function abrirEdicionEvento(idEvento) {
        if (!puedeCapturar) {
            return;
        }

        const evento =
            eventos.find(
                item =>
                    Number(
                        item.id_evento_ran
                    ) ===
                    Number(idEvento)
            );

        if (!evento) {
            return;
        }

        crearFormularioEvento();

        idEventoEditando =
            Number(
                evento.id_evento_ran
            );

        const ordinal =
            document.getElementById(
                "ordinalEventoRan"
            );

        ordinal.value =
            evento.ordinal;

        /*
         * El schema de UPDATE no permite cambiar
         * el ordinal.
         */
        ordinal.disabled =
            true;

        document.getElementById(
            "tipoEventoRan"
        ).value =
            evento.id_tipo_evento || "";

        document.getElementById(
            "fechaEventoRan"
        ).value =
            evento.fecha_evento || "";

        document.getElementById(
            "numeroSolicitudRan"
        ).value =
            evento.numero_solicitud || "";

        document.getElementById(
            "resultadoEventoRan"
        ).value =
            evento.resultado || "";

        document.getElementById(
            "calificacionEventoRan"
        ).value =
            evento.calificacion || "";

        document.getElementById(
            "folioEventoRan"
        ).value =
            evento.folio_referencia || "";

        document.getElementById(
            "documentoEventoRan"
        ).value =
            evento.id_documento || "";

        const titulo =
            document.getElementById(
                "tituloFormularioEventoRan"
            );

        if (titulo) {
            titulo.textContent =
                `Editar evento RAN #${evento.id_evento_ran}`;
        }

        seccionFormularioEvento.hidden =
            false;

        seccionFormularioEvento
            .style.display = "";

        seccionFormularioEvento.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function cerrarFormularioEvento() {
        idEventoEditando = null;

        const form =
            document.getElementById(
                "formEventoRan"
            );

        form?.reset();

        if (seccionFormularioEvento) {
            seccionFormularioEvento.hidden =
                true;

            seccionFormularioEvento
                .style.display = "none";
        }
    }


    /* =====================================================
                        GUARDAR EVENTO
    ====================================================== */

    async function guardarEvento(event) {
        event.preventDefault();

        if (!puedeCapturar) {
            return;
        }

        const ordinal =
            Number(
                document.getElementById(
                    "ordinalEventoRan"
                ).value
            );

        const idTipoEvento =
            Number(
                document.getElementById(
                    "tipoEventoRan"
                ).value
            );

        const idDocumento =
            numeroOpcional(
                document.getElementById(
                    "documentoEventoRan"
                )
            );

        if (
            !idEventoEditando &&
            (
                !Number.isInteger(ordinal) ||
                ordinal <= 0
            )
        ) {
            alert(
                "Indica un ordinal válido."
            );

            return;
        }

        if (
            !Number.isInteger(idTipoEvento) ||
            idTipoEvento <= 0
        ) {
            alert(
                "Selecciona el tipo de evento."
            );

            return;
        }

        if (Number.isNaN(idDocumento)) {
            alert(
                "El ID del documento no es válido."
            );

            return;
        }

        const datosComunes = {
            id_tipo_evento:
                idTipoEvento,

            fecha_evento:
                textoOpcional(
                    document.getElementById(
                        "fechaEventoRan"
                    )
                ),

            numero_solicitud:
                textoOpcional(
                    document.getElementById(
                        "numeroSolicitudRan"
                    )
                ),

            resultado:
                textoOpcional(
                    document.getElementById(
                        "resultadoEventoRan"
                    )
                ),

            calificacion:
                textoOpcional(
                    document.getElementById(
                        "calificacionEventoRan"
                    )
                ),

            folio_referencia:
                textoOpcional(
                    document.getElementById(
                        "folioEventoRan"
                    )
                ),

            id_documento:
                idDocumento
        };

        const boton =
            document.getElementById(
                "btnGuardarEventoRan"
            );

        boton.disabled =
            true;

        try {
            if (idEventoEditando) {
                await window.TramitesRanAPI
                    .actualizarEvento(
                        idEventoEditando,
                        datosComunes
                    );

                alert(
                    "Evento RAN actualizado correctamente."
                );

            } else {
                await window.TramitesRanAPI
                    .crearEvento(
                        idTramiteRan,
                        {
                            ordinal,
                            ...datosComunes
                        }
                    );

                alert(
                    "Evento RAN registrado correctamente."
                );
            }

            cerrarFormularioEvento();

            const respuesta =
                await window.TramitesRanAPI
                    .listarEventos(
                        idTramiteRan
                    );

            eventos =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            mostrarEventos();
            actualizarUltimoEvento();

        } catch (error) {
            window.ClienteAPI
                .mostrarErrorAPI(error);

        } finally {
            boton.disabled =
                false;
        }
    }


    /* =====================================================
                    ACCIONES DE TABLA
    ====================================================== */

    elementos.eventosTabla?.addEventListener(
        "click",
        event => {
            const botonVer =
                event.target.closest(
                    "[data-ver-evento]"
                );

            if (botonVer) {
                consultarEvento(
                    botonVer.dataset.verEvento
                );

                return;
            }

            const botonEditar =
                event.target.closest(
                    "[data-editar-evento]"
                );

            if (botonEditar) {
                abrirEdicionEvento(
                    botonEditar.dataset.editarEvento
                );
            }
        }
    );


    /* =====================================================
                        ÚLTIMO EVENTO
    ====================================================== */

    function actualizarUltimoEvento() {
        if (!eventos.length) {
            elementos.ultimoEvento.textContent =
                "Sin eventos registrados";

            elementos.detalleUltimoEvento.textContent =
                "El trámite todavía no cuenta con movimientos registrados.";

            elementos.iconoEstado.className =
                "bi bi-hourglass-split";

            return;
        }

        const ultimo =
            [...eventos].sort(
                (a, b) =>
                    Number(a.ordinal) -
                    Number(b.ordinal)
            ).at(-1);

        elementos.ultimoEvento.textContent =
            nombreTipoEvento(
                ultimo.id_tipo_evento
            );

        const partes = [];

        if (ultimo.fecha_evento) {
            partes.push(
                `Fecha: ${ultimo.fecha_evento}`
            );
        }

        if (ultimo.resultado) {
            partes.push(
                `Resultado: ${ultimo.resultado}`
            );
        }

        if (ultimo.folio_referencia) {
            partes.push(
                `Folio: ${ultimo.folio_referencia}`
            );
        }

        elementos.detalleUltimoEvento.textContent =
            partes.join(" · ") ||
            "Último movimiento registrado.";

        elementos.iconoEstado.className =
            "bi bi-check-circle";
    }


    /* =====================================================
                        BOTONES
    ====================================================== */

    elementos.btnAgregarEvento
        ?.addEventListener(
            "click",
            abrirNuevoEvento
        );

    elementos.btnVolver
        ?.addEventListener(
            "click",
            () => {
                if (
                    tramite?.id_proyecto_nucleo
                ) {
                    window.location.href =
                        `/pages/tramiteRan.html?id_proyecto_nucleo=${encodeURIComponent(
                            tramite.id_proyecto_nucleo
                        )}`;

                    return;
                }

                window.history.back();
            }
        );


    /* =====================================================
                        INICIALIZACIÓN
    ====================================================== */

    try {
        await cargarCatalogo();
        await cargarTramite();

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(error);
    }
});