document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(window.location.search);

    const idFifonafe = Number(
        parametros.get("id_fifonafe") ||
        parametros.get("id") ||
        document.querySelector(".contenedor")
            ?.dataset.fifonafeId
    );

    const idProyectoNucleo = Number(
        parametros.get("id_proyecto_nucleo")
    );

    if (
        !Number.isInteger(idFifonafe) ||
        idFifonafe <= 0 ||
        !Number.isInteger(idProyectoNucleo) ||
        idProyectoNucleo <= 0
    ) {
        alert(
            "Falta el identificador del trámite o del proyecto-núcleo."
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

        btnEditar:
            document.getElementById(
                "btnEditarFifonafe"
            ),

        btnEditarDatos:
            document.getElementById(
                "btnEditarDatos"
            ),

        btnAgregarAfectacion:
            document.getElementById(
                "btnAgregarAfectacion"
            ),

        btnAgregarEvento:
            document.getElementById(
                "btnAgregarEvento"
            ),

        idTramite:
            document.getElementById(
                "idTramite"
            ),

        ambito:
            document.getElementById(
                "ambito"
            ),

        estatus:
            document.getElementById(
                "estatus"
            ),

        estadoFifonafe:
            document.getElementById(
                "estadoFifonafe"
            ),

        acuseFifonafe:
            document.getElementById(
                "acuseFifonafe"
            ),

        hayConflictos:
            document.getElementById(
                "hayConflictos"
            ),

        resultadoNoConflictos:
            document.getElementById(
                "resultadoNoConflictos"
            ),

        datoResultadoConflictos:
            document.getElementById(
                "datoResultadoConflictos"
            ),

        totalAfectaciones:
            document.getElementById(
                "totalAfectaciones"
            ),

        afectacionesTabla:
            document.getElementById(
                "afectacionesTabla"
            ),

        totalEventos:
            document.getElementById(
                "totalEventos"
            ),

        eventosTabla:
            document.getElementById(
                "eventosTabla"
            ),

        observaciones:
            document.getElementById(
                "observaciones"
            )
    };


    /* =====================================================
                        ESTADO
    ====================================================== */

    let tramite = null;
    let afectaciones = [];
    let eventos = [];

    let tiposEvento = [];
    let tipoEventoPorId = new Map();

    let puedeCapturar = false;

    let formularioEdicion = null;
    let formularioEvento = null;

    let idEventoEditando = null;


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

    function texto(valor) {
        return (
            valor === null ||
            valor === undefined ||
            valor === ""
        )
            ? "—"
            : String(valor);
    }

    function textoOpcional(elemento) {
        const valor =
            elemento?.value?.trim();

        return valor || null;
    }

    function numeroOpcional(elemento) {
        const valor =
            elemento?.value?.trim();

        if (!valor) {
            return null;
        }

        const numero =
            Number(valor);

        return (
            Number.isInteger(numero) &&
            numero > 0
        )
            ? numero
            : NaN;
    }

    function formatoConflictos(valor) {
        if (valor === true) {
            return "Sí";
        }

        if (valor === false) {
            return "No";
        }

        return "Sin definir";
    }

    function nombreEstatus(valor) {
        const nombres = {
            programado: "Programado",
            pendiente: "Pendiente",
            completo: "Completo",
            cancelado: "Cancelado",
            otro: "Otro"
        };

        return nombres[valor] ||
            valor ||
            "—";
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

    function opcionesTipoEvento() {
        return tiposEvento
            .map(item => `
                <option
                    value="${escaparHTML(
                        item.id_catalogo_opcion
                    )}">
                    ${escaparHTML(
                        item.nombre ||
                        item.codigo ||
                        `#${item.id_catalogo_opcion}`
                    )}
                </option>
            `)
            .join("");
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

    if (!puedeCapturar) {
        [
            elementos.btnEditar,
            elementos.btnEditarDatos,
            elementos.btnAgregarAfectacion,
            elementos.btnAgregarEvento
        ].forEach(boton => {
            if (boton) {
                boton.hidden = true;
                boton.style.display = "none";
            }
        });
    }


    /* =====================================================
                    CARGAR DATOS REALES
    ====================================================== */

    async function cargarDatos() {
        const [
            tramites,
            afectacionesNucleo,
            tipos,
            eventosReales
        ] = await Promise.all([
            window.FifonafeAPI
                .listarPorProyectoNucleo(
                    idProyectoNucleo
                ),

            window.AfectacionesAPI
                .listarPorProyectoNucleo(
                    idProyectoNucleo
                ),

            window.CatalogosAPI
                .obtenerOperativo(
                    "tipo_evento_fifonafe"
                ),

            window.FifonafeAPI
                .listarEventos(
                    idFifonafe
                )
        ]);

        tramite =
            (
                Array.isArray(tramites)
                    ? tramites
                    : []
            ).find(item =>
                Number(
                    item.id_tramite_fifonafe
                ) === idFifonafe
            );

        if (!tramite) {
            throw new Error(
                "El trámite FIFONAFE no fue encontrado."
            );
        }

        tiposEvento =
            Array.isArray(tipos)
                ? tipos
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

        eventos =
            Array.isArray(eventosReales)
                ? eventosReales
                : [];

        const idsRelacionados =
            new Set(
                (
                    Array.isArray(
                        tramite.afectaciones
                    )
                        ? tramite.afectaciones
                        : []
                ).map(item =>
                    Number(
                        item.id_afectacion
                    )
                )
            );

        afectaciones =
            (
                Array.isArray(
                    afectacionesNucleo
                )
                    ? afectacionesNucleo
                    : []
            ).filter(item =>
                idsRelacionados.has(
                    Number(
                        item.id_afectacion
                    )
                )
            );
    }

    async function recargar() {
        await cargarDatos();

        mostrarInformacion();
        mostrarAfectaciones();
        mostrarEventos();
    }


    /* =====================================================
                    INFORMACIÓN GENERAL
    ====================================================== */

    function mostrarInformacion() {
        elementos.idTramite.textContent =
            tramite.id_tramite_fifonafe;

        elementos.ambito.textContent =
            texto(tramite.ambito);

        elementos.estatus.textContent =
            nombreEstatus(
                tramite.estatus
            );

        elementos.estadoFifonafe.textContent =
            nombreEstatus(
                tramite.estatus
            );

        elementos.acuseFifonafe.textContent =
            texto(
                tramite.acuse_fifonafe_fecha
            );

        elementos.hayConflictos.textContent =
            formatoConflictos(
                tramite.hay_conflictos
            );

        elementos.resultadoNoConflictos
            .textContent =
            texto(
                tramite.resultado_no_conflictos
            );

        elementos.datoResultadoConflictos
            .style.opacity =
            tramite.hay_conflictos === false
                ? "1"
                : ".55";

        if (elementos.observaciones) {
            elementos.observaciones.textContent =
                tramite.referencia_expediente
                    ? `Referencia de expediente: ${tramite.referencia_expediente}`
                    : "No hay observaciones registradas.";
        }
    }


    /* =====================================================
                        AFECTACIONES
    ====================================================== */

    function mostrarAfectaciones() {
        elementos.totalAfectaciones.textContent =
            afectaciones.length;

        elementos.afectacionesTabla.innerHTML =
            "";

        if (!afectaciones.length) {
            elementos.afectacionesTabla
                .innerHTML = `
                    <tr>
                        <td
                            colspan="4"
                            class="tabla-vacia">
                            No hay afectaciones relacionadas.
                        </td>
                    </tr>
                `;

            return;
        }

        afectaciones.forEach(afectacion => {
            const fila =
                document.createElement(
                    "tr"
                );

            const referencia =
                afectacion.referencia ||
                afectacion.referencia_alfanumerica ||
                "—";

            const tipo =
                afectacion.tipo_afectacion ||
                "—";

            fila.innerHTML = `
                <td>
                    ${escaparHTML(
                        afectacion.id_afectacion
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        referencia
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        tipo
                    )}
                </td>

                <td>
                    <button
                        type="button"
                        class="btn-tabla"
                        title="Ver afectación"
                        data-ver-afectacion="${afectacion.id_afectacion}">

                        <i class="bi bi-eye"></i>

                    </button>
                </td>
            `;

            elementos.afectacionesTabla
                .appendChild(fila);
        });
    }

    elementos.afectacionesTabla
        ?.addEventListener(
            "click",
            event => {
                const boton =
                    event.target.closest(
                        "[data-ver-afectacion]"
                    );

                if (!boton) {
                    return;
                }

                window.location.href =
                    `/pages/detalleAfectacion.html?id_afectacion=${encodeURIComponent(
                        boton.dataset.verAfectacion
                    )}&id_proyecto_nucleo=${encodeURIComponent(
                        idProyectoNucleo
                    )}`;
            }
        );


    /* =====================================================
                        EVENTOS
    ====================================================== */

    function mostrarEventos() {
        elementos.totalEventos.textContent =
            eventos.length;

        elementos.eventosTabla.innerHTML =
            "";

        if (!eventos.length) {
            elementos.eventosTabla.innerHTML = `
                <tr>
                    <td
                        colspan="8"
                        class="tabla-vacia">
                        No hay eventos registrados.
                    </td>
                </tr>
            `;

            return;
        }

        [...eventos]
            .sort(
                (a, b) =>
                    Number(a.ordinal) -
                    Number(b.ordinal)
            )
            .forEach(evento => {
                const fila =
                    document.createElement(
                        "tr"
                    );

                const fecha =
                    evento.fecha_evento ||
                    evento.fecha_oficio ||
                    "—";

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
                            evento.origen || "—"
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            evento.destino || "—"
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            evento.numero_oficio || "—"
                        )}
                    </td>

                    <td>
                        ${escaparHTML(fecha)}
                    </td>

                    <td>
                        ${
                            evento.id_documento
                                ? `
                                    <span class="etiqueta-tabla">
                                        <i class="bi bi-paperclip"></i>
                                        #${escaparHTML(
                                            evento.id_documento
                                        )}
                                    </span>
                                `
                                : "—"
                        }
                    </td>

                    <td>
                        <div class="acciones-tabla">

                            <button
                                type="button"
                                class="btn-tabla"
                                title="Ver evento"
                                data-ver-evento="${evento.id_evento_fifonafe}">
                                <i class="bi bi-eye"></i>
                            </button>

                            ${
                                puedeCapturar
                                    ? `
                                        <button
                                            type="button"
                                            class="btn-tabla"
                                            title="Editar evento"
                                            data-editar-evento="${evento.id_evento_fifonafe}">
                                            <i class="bi bi-pencil"></i>
                                        </button>

                                        <button
                                            type="button"
                                            class="btn-tabla"
                                            title="Dar de baja evento"
                                            data-eliminar-evento="${evento.id_evento_fifonafe}">
                                            <i class="bi bi-trash"></i>
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
            eventos.find(item =>
                Number(
                    item.id_evento_fifonafe
                ) ===
                Number(idEvento)
            );

        if (!evento) {
            return;
        }

        alert(
            [
                `Evento FIFONAFE #${evento.id_evento_fifonafe}`,
                "",
                `Ordinal: ${evento.ordinal}`,
                `Tipo: ${nombreTipoEvento(evento.id_tipo_evento)}`,
                `Origen: ${evento.origen || "—"}`,
                `Destino: ${evento.destino || "—"}`,
                `Número de oficio: ${evento.numero_oficio || "—"}`,
                `Fecha de oficio: ${evento.fecha_oficio || "—"}`,
                `Fecha del evento: ${evento.fecha_evento || "—"}`,
                `Ciclo de consulta: ${evento.ciclo_consulta || "—"}`,
                `Conflicto impide retiro: ${formatoConflictos(
                    evento.conflicto_impide_retiro
                )}`,
                `Documento: ${
                    evento.id_documento
                        ? `#${evento.id_documento}`
                        : "—"
                }`
            ].join("\n")
        );
    }


    /* =====================================================
                FORMULARIO EDITAR TRÁMITE
    ====================================================== */

    function crearFormularioEdicion() {
        if (formularioEdicion) {
            return;
        }

        const bloque =
            elementos.btnEditarDatos
                ?.closest(".bloque");

        if (!bloque) {
            return;
        }

        formularioEdicion =
            document.createElement(
                "section"
            );

        formularioEdicion.className =
            "bloque";

        formularioEdicion.hidden = true;

        formularioEdicion.innerHTML = `
            <div class="bloque-titulo">

                <div class="bloque-titulo-info">

                    <span class="numero-seccion">
                        ✎
                    </span>

                    <div>
                        <h2>
                            Editar trámite FIFONAFE
                        </h2>

                        <p>
                            Modifica el estado y los datos generales
                            del trámite.
                        </p>
                    </div>

                </div>

            </div>

            <form id="formEditarFifonafe">

                <div class="form-grid">

                    <div class="campo">

                        <label for="editarEstatus">
                            Estatus
                        </label>

                        <select
                            id="editarEstatus"
                            required>

                            <option value="programado">
                                Programado
                            </option>

                            <option value="pendiente">
                                Pendiente
                            </option>

                            <option value="completo">
                                Completo
                            </option>

                            <option value="cancelado">
                                Cancelado
                            </option>

                            <option value="otro">
                                Otro
                            </option>

                        </select>

                    </div>

                    <div class="campo">

                        <label for="editarAcuse">
                            Fecha de acuse FIFONAFE
                        </label>

                        <input
                            type="date"
                            id="editarAcuse">

                    </div>

                    <div class="campo">

                        <label for="editarConflictos">
                            ¿Hay conflictos?
                        </label>

                        <select id="editarConflictos">

                            <option value="">
                                Sin definir
                            </option>

                            <option value="true">
                                Sí
                            </option>

                            <option value="false">
                                No
                            </option>

                        </select>

                    </div>

                    <div
                        class="campo campo-completo"
                        id="editarCampoResultado">

                        <label for="editarResultado">
                            Resultado de no conflictos
                        </label>

                        <textarea
                            id="editarResultado"
                            rows="3"></textarea>

                    </div>

                    <div class="campo campo-completo">

                        <label for="editarReferencia">
                            Referencia de expediente
                        </label>

                        <input
                            type="text"
                            maxlength="200"
                            id="editarReferencia">

                    </div>

                </div>

                <div class="acciones-formulario">

                    <button
                        type="button"
                        class="btn-secundario"
                        id="btnCancelarEditarFifonafe">
                        Cancelar
                    </button>

                    <button
                        type="submit"
                        class="btn-principal"
                        id="btnGuardarEditarFifonafe">

                        <i class="bi bi-check-lg"></i>
                        Guardar cambios

                    </button>

                </div>

            </form>
        `;

        bloque.insertAdjacentElement(
            "afterend",
            formularioEdicion
        );

        document
            .getElementById(
                "editarConflictos"
            )
            ?.addEventListener(
                "change",
                actualizarResultadoEdicion
            );

        document
            .getElementById(
                "btnCancelarEditarFifonafe"
            )
            ?.addEventListener(
                "click",
                cerrarEdicion
            );

        document
            .getElementById(
                "formEditarFifonafe"
            )
            ?.addEventListener(
                "submit",
                guardarEdicion
            );
    }

    function actualizarResultadoEdicion() {
        const conflictos =
            document.getElementById(
                "editarConflictos"
            )?.value;

        const campo =
            document.getElementById(
                "editarCampoResultado"
            );

        const resultado =
            document.getElementById(
                "editarResultado"
            );

        const visible =
            conflictos === "false";

        if (campo) {
            campo.hidden = !visible;
        }

        if (
            !visible &&
            resultado
        ) {
            resultado.value = "";
        }
    }

    function abrirEdicion() {
        if (!puedeCapturar) {
            return;
        }

        crearFormularioEdicion();

        document.getElementById(
            "editarEstatus"
        ).value =
            tramite.estatus ||
            "pendiente";

        document.getElementById(
            "editarAcuse"
        ).value =
            tramite.acuse_fifonafe_fecha ||
            "";

        document.getElementById(
            "editarConflictos"
        ).value =
            tramite.hay_conflictos === null ||
            tramite.hay_conflictos === undefined
                ? ""
                : String(
                    tramite.hay_conflictos
                );

        document.getElementById(
            "editarResultado"
        ).value =
            tramite.resultado_no_conflictos ||
            "";

        document.getElementById(
            "editarReferencia"
        ).value =
            tramite.referencia_expediente ||
            "";

        actualizarResultadoEdicion();

        formularioEdicion.hidden =
            false;

        formularioEdicion.style.display =
            "";

        formularioEdicion.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function cerrarEdicion() {
        if (!formularioEdicion) {
            return;
        }

        formularioEdicion.hidden =
            true;

        formularioEdicion.style.display =
            "none";
    }

    async function guardarEdicion(event) {
        event.preventDefault();

        const conflictosValor =
            document.getElementById(
                "editarConflictos"
            ).value;

        const payload = {
            estatus:
                document.getElementById(
                    "editarEstatus"
                ).value,

            acuse_fifonafe_fecha:
                document.getElementById(
                    "editarAcuse"
                ).value ||
                null,

            hay_conflictos:
                conflictosValor === ""
                    ? null
                    : conflictosValor === "true",

            resultado_no_conflictos:
                conflictosValor === "false"
                    ? (
                        document.getElementById(
                            "editarResultado"
                        ).value.trim() ||
                        null
                    )
                    : null,

            referencia_expediente:
                document.getElementById(
                    "editarReferencia"
                ).value.trim() ||
                null
        };

        const boton =
            document.getElementById(
                "btnGuardarEditarFifonafe"
            );

        boton.disabled = true;

        try {
            await window.FifonafeAPI
                .actualizar(
                    idFifonafe,
                    payload
                );

            alert(
                "Trámite FIFONAFE actualizado correctamente."
            );

            cerrarEdicion();

            await recargar();

        } catch (error) {
            window.ClienteAPI
                .mostrarErrorAPI(error);

        } finally {
            boton.disabled = false;
        }
    }


    /* =====================================================
                    FORMULARIO EVENTO
    ====================================================== */

    function crearFormularioEvento() {
        if (formularioEvento) {
            return;
        }

        const bloque =
            elementos.btnAgregarEvento
                ?.closest(".bloque");

        if (!bloque) {
            return;
        }

        formularioEvento =
            document.createElement(
                "section"
            );

        formularioEvento.className =
            "bloque";

        formularioEvento.hidden = true;

        formularioEvento.innerHTML = `
            <div class="bloque-titulo">

                <div class="bloque-titulo-info">

                    <span class="numero-seccion">
                        +
                    </span>

                    <div>
                        <h2 id="tituloFormularioEventoFifonafe">
                            Registrar evento FIFONAFE
                        </h2>

                        <p>
                            Agrega una actuación al seguimiento
                            del trámite.
                        </p>
                    </div>

                </div>

            </div>

            <form id="formEventoFifonafe">

                <div class="form-grid">

                    <div class="campo">

                        <label for="eventoOrdinal">
                            Ordinal
                            <span class="obligatorio">*</span>
                        </label>

                        <input
                            type="number"
                            min="1"
                            step="1"
                            id="eventoOrdinal"
                            required>

                    </div>

                    <div class="campo">

                        <label for="eventoTipo">
                            Tipo de evento
                            <span class="obligatorio">*</span>
                        </label>

                        <select
                            id="eventoTipo"
                            required>

                            <option value="">
                                Selecciona una opción
                            </option>

                            ${opcionesTipoEvento()}

                        </select>

                    </div>

                    <div class="campo">

                        <label for="eventoOrigen">
                            Origen
                        </label>

                        <input
                            type="text"
                            maxlength="200"
                            id="eventoOrigen">

                    </div>

                    <div class="campo">

                        <label for="eventoDestino">
                            Destino
                        </label>

                        <input
                            type="text"
                            maxlength="200"
                            id="eventoDestino">

                    </div>

                    <div class="campo">

                        <label for="eventoNumeroOficio">
                            Número de oficio
                        </label>

                        <input
                            type="text"
                            maxlength="150"
                            id="eventoNumeroOficio">

                    </div>

                    <div class="campo">

                        <label for="eventoFechaOficio">
                            Fecha de oficio
                        </label>

                        <input
                            type="date"
                            id="eventoFechaOficio">

                    </div>

                    <div class="campo">

                        <label for="eventoFecha">
                            Fecha del evento
                        </label>

                        <input
                            type="date"
                            id="eventoFecha">

                    </div>

                    <div class="campo">

                        <label for="eventoCiclo">
                            Ciclo de consulta
                        </label>

                        <input
                            type="number"
                            min="1"
                            step="1"
                            id="eventoCiclo">

                    </div>

                    <div class="campo">

                        <label for="eventoConflicto">
                            ¿Conflicto impide retiro?
                        </label>

                        <select id="eventoConflicto">

                            <option value="">
                                Sin definir
                            </option>

                            <option value="true">
                                Sí
                            </option>

                            <option value="false">
                                No
                            </option>

                        </select>

                    </div>

                    <div class="campo">

                        <label for="eventoDocumento">
                            ID de documento
                        </label>

                        <input
                            type="number"
                            min="1"
                            step="1"
                            id="eventoDocumento">

                    </div>

                </div>

                <div class="acciones-formulario">

                    <button
                        type="button"
                        class="btn-secundario"
                        id="btnCancelarEventoFifonafe">
                        Cancelar
                    </button>

                    <button
                        type="submit"
                        class="btn-principal"
                        id="btnGuardarEventoFifonafe">

                        <i class="bi bi-check-lg"></i>
                        Guardar evento

                    </button>

                </div>

            </form>
        `;

        bloque.insertAdjacentElement(
            "afterend",
            formularioEvento
        );

        document
            .getElementById(
                "btnCancelarEventoFifonafe"
            )
            ?.addEventListener(
                "click",
                cerrarFormularioEvento
            );

        document
            .getElementById(
                "formEventoFifonafe"
            )
            ?.addEventListener(
                "submit",
                guardarEvento
            );
    }

    function siguienteOrdinal() {
        if (!eventos.length) {
            return 1;
        }

        return Math.max(
            ...eventos.map(
                item =>
                    Number(
                        item.ordinal
                    ) || 0
            )
        ) + 1;
    }

    function limpiarFormularioEvento() {
        document.getElementById(
            "formEventoFifonafe"
        )?.reset();

        const ordinal =
            document.getElementById(
                "eventoOrdinal"
            );

        if (ordinal) {
            ordinal.disabled = false;
        }

        idEventoEditando = null;
    }

    function abrirNuevoEvento() {
        if (!puedeCapturar) {
            return;
        }

        crearFormularioEvento();
        limpiarFormularioEvento();

        document.getElementById(
            "eventoOrdinal"
        ).value =
            siguienteOrdinal();

        document.getElementById(
            "tituloFormularioEventoFifonafe"
        ).textContent =
            "Registrar evento FIFONAFE";

        formularioEvento.hidden =
            false;

        formularioEvento.style.display =
            "";

        formularioEvento.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function abrirEdicionEvento(idEvento) {
        if (!puedeCapturar) {
            return;
        }

        const evento =
            eventos.find(item =>
                Number(
                    item.id_evento_fifonafe
                ) ===
                Number(idEvento)
            );

        if (!evento) {
            return;
        }

        crearFormularioEvento();
        limpiarFormularioEvento();

        idEventoEditando =
            Number(
                evento.id_evento_fifonafe
            );

        const ordinal =
            document.getElementById(
                "eventoOrdinal"
            );

        ordinal.value =
            evento.ordinal;

        /*
         * TramiteFifonafeEventoUpdate
         * no permite cambiar el ordinal.
         */
        ordinal.disabled = true;

        document.getElementById(
            "eventoTipo"
        ).value =
            evento.id_tipo_evento ||
            "";

        document.getElementById(
            "eventoOrigen"
        ).value =
            evento.origen ||
            "";

        document.getElementById(
            "eventoDestino"
        ).value =
            evento.destino ||
            "";

        document.getElementById(
            "eventoNumeroOficio"
        ).value =
            evento.numero_oficio ||
            "";

        document.getElementById(
            "eventoFechaOficio"
        ).value =
            evento.fecha_oficio ||
            "";

        document.getElementById(
            "eventoFecha"
        ).value =
            evento.fecha_evento ||
            "";

        document.getElementById(
            "eventoCiclo"
        ).value =
            evento.ciclo_consulta ||
            "";

        document.getElementById(
            "eventoConflicto"
        ).value =
            evento.conflicto_impide_retiro === null ||
            evento.conflicto_impide_retiro === undefined
                ? ""
                : String(
                    evento.conflicto_impide_retiro
                );

        document.getElementById(
            "eventoDocumento"
        ).value =
            evento.id_documento ||
            "";

        document.getElementById(
            "tituloFormularioEventoFifonafe"
        ).textContent =
            `Editar evento FIFONAFE #${idEventoEditando}`;

        formularioEvento.hidden =
            false;

        formularioEvento.style.display =
            "";

        formularioEvento.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function cerrarFormularioEvento() {
        if (!formularioEvento) {
            return;
        }

        limpiarFormularioEvento();

        formularioEvento.hidden =
            true;

        formularioEvento.style.display =
            "none";
    }


    /* =====================================================
                    CONSTRUIR EVENTO
    ====================================================== */

    function construirDatosEvento() {
        const idTipo =
            Number(
                document.getElementById(
                    "eventoTipo"
                ).value
            );

        if (
            !Number.isInteger(idTipo) ||
            idTipo <= 0
        ) {
            alert(
                "Selecciona el tipo de evento."
            );

            return null;
        }

        const idDocumento =
            numeroOpcional(
                document.getElementById(
                    "eventoDocumento"
                )
            );

        const ciclo =
            numeroOpcional(
                document.getElementById(
                    "eventoCiclo"
                )
            );

        if (
            Number.isNaN(idDocumento) ||
            Number.isNaN(ciclo)
        ) {
            alert(
                "Revisa el ID del documento y el ciclo de consulta."
            );

            return null;
        }

        const numeroOficio =
            textoOpcional(
                document.getElementById(
                    "eventoNumeroOficio"
                )
            );

        const fechaOficio =
            textoOpcional(
                document.getElementById(
                    "eventoFechaOficio"
                )
            );

        const fechaEvento =
            textoOpcional(
                document.getElementById(
                    "eventoFecha"
                )
            );

        /*
         * Regla de integridad del evento FIFONAFE:
         * debe existir al menos algún soporte temporal,
         * de oficio o documental.
         */
        if (
            !numeroOficio &&
            !fechaOficio &&
            !fechaEvento &&
            !idDocumento
        ) {
            alert(
                "El evento necesita al menos número de oficio, fecha de oficio, fecha del evento o un documento."
            );

            return null;
        }

        const conflictoValor =
            document.getElementById(
                "eventoConflicto"
            ).value;

        return {
            id_tipo_evento:
                idTipo,

            origen:
                textoOpcional(
                    document.getElementById(
                        "eventoOrigen"
                    )
                ),

            destino:
                textoOpcional(
                    document.getElementById(
                        "eventoDestino"
                    )
                ),

            numero_oficio:
                numeroOficio,

            fecha_oficio:
                fechaOficio,

            id_documento:
                idDocumento,

            ciclo_consulta:
                ciclo,

            fecha_evento:
                fechaEvento,

            conflicto_impide_retiro:
                conflictoValor === ""
                    ? null
                    : conflictoValor ===
                        "true"
        };
    }


    /* =====================================================
                        GUARDAR EVENTO
    ====================================================== */

    async function guardarEvento(event) {
        event.preventDefault();

        if (!puedeCapturar) {
            return;
        }

        const datos =
            construirDatosEvento();

        if (!datos) {
            return;
        }

        const boton =
            document.getElementById(
                "btnGuardarEventoFifonafe"
            );

        boton.disabled = true;

        try {
            if (idEventoEditando) {
                /*
                 * PATCH no lleva ordinal.
                 */
                await window.FifonafeAPI
                    .actualizarEvento(
                        idEventoEditando,
                        datos
                    );

                alert(
                    "Evento FIFONAFE actualizado correctamente."
                );

            } else {
                const ordinal =
                    Number(
                        document.getElementById(
                            "eventoOrdinal"
                        ).value
                    );

                if (
                    !Number.isInteger(ordinal) ||
                    ordinal <= 0
                ) {
                    alert(
                        "Indica un ordinal válido."
                    );

                    return;
                }

                if (
                    eventos.some(item =>
                        Number(
                            item.ordinal
                        ) === ordinal
                    )
                ) {
                    alert(
                        `Ya existe un evento con ordinal ${ordinal}.`
                    );

                    return;
                }

                await window.FifonafeAPI
                    .crearEvento(
                        idFifonafe,
                        {
                            ordinal,
                            ...datos
                        }
                    );

                alert(
                    "Evento FIFONAFE registrado correctamente."
                );
            }

            cerrarFormularioEvento();

            await recargar();

        } catch (error) {
            window.ClienteAPI
                .mostrarErrorAPI(error);

        } finally {
            boton.disabled = false;
        }
    }


    /* =====================================================
                        ELIMINAR EVENTO
    ====================================================== */

    async function eliminarEvento(idEvento) {
        if (!puedeCapturar) {
            return;
        }

        const motivo =
            prompt(
                "Motivo de la baja del evento:"
            );

        if (motivo === null) {
            return;
        }

        const motivoLimpio =
            motivo.trim();

        if (motivoLimpio.length < 3) {
            alert(
                "El motivo debe tener al menos 3 caracteres."
            );

            return;
        }

        const confirmar =
            confirm(
                "¿Seguro que deseas dar de baja este evento FIFONAFE?"
            );

        if (!confirmar) {
            return;
        }

        try {
            await window.FifonafeAPI
                .eliminarEvento(
                    idEvento,
                    motivoLimpio
                );

            alert(
                "Evento FIFONAFE dado de baja correctamente."
            );

            await recargar();

        } catch (error) {
            window.ClienteAPI
                .mostrarErrorAPI(error);
        }
    }


    /* =====================================================
                    ACCIONES DE EVENTOS
    ====================================================== */

    elementos.eventosTabla
        ?.addEventListener(
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
                        botonEditar.dataset
                            .editarEvento
                    );

                    return;
                }

                const botonEliminar =
                    event.target.closest(
                        "[data-eliminar-evento]"
                    );

                if (botonEliminar) {
                    eliminarEvento(
                        botonEliminar.dataset
                            .eliminarEvento
                    );
                }
            }
        );


    /* =====================================================
                        BOTONES
    ====================================================== */

    elementos.btnEditar
        ?.addEventListener(
            "click",
            abrirEdicion
        );

    elementos.btnEditarDatos
        ?.addEventListener(
            "click",
            abrirEdicion
        );

    elementos.btnAgregarEvento
        ?.addEventListener(
            "click",
            abrirNuevoEvento
        );

    /*
     * Lo activaremos en el siguiente paso
     * junto con intervinientes.
     */
    if (elementos.btnAgregarAfectacion) {
        elementos.btnAgregarAfectacion.hidden =
            true;

        elementos.btnAgregarAfectacion
            .style.display = "none";
    }


    /* =====================================================
                        VOLVER
    ====================================================== */

    elementos.btnVolver
        ?.addEventListener(
            "click",
            () => {
                window.location.href =
                    `/pages/fifonafe.html?id_proyecto_nucleo=${encodeURIComponent(
                        idProyectoNucleo
                    )}`;
            }
        );


    /* =====================================================
                        INICIALIZACIÓN
    ====================================================== */

    try {
        await recargar();

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(error);
    }
});