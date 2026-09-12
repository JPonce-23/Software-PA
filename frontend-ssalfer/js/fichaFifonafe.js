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

        window.location.href = "/dashboard.html";
        return;
    }


    /* =====================================================
                        ELEMENTOS
    ====================================================== */

    const elementos = {
        btnVolver:
            document.getElementById("btnVolver"),

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

    function formatoConflictos(valor) {
        if (valor === true) {
            return "Sí";
        }

        if (valor === false) {
            return "No";
        }

        return "Sin definir";
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
            (Array.isArray(tramites)
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


    /* =====================================================
                    INFORMACIÓN GENERAL
    ====================================================== */

    function mostrarInformacion() {
        elementos.idTramite.textContent =
            tramite.id_tramite_fifonafe;

        elementos.ambito.textContent =
            texto(tramite.ambito);

        elementos.estatus.textContent =
            texto(tramite.estatus);

        elementos.estadoFifonafe.textContent =
            texto(tramite.estatus);

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
            elementos.afectacionesTabla.innerHTML = `
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
                document.createElement("tr");

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
                        data-ver-afectacion="${afectacion.id_afectacion}">
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            `;

            elementos.afectacionesTabla
                .appendChild(fila);
        });
    }


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
                    document.createElement("tr");

                /*
                 * La columna se llama genéricamente
                 * "Fecha". Mostramos fecha_evento
                 * primero y, como respaldo,
                 * fecha_oficio.
                 */
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
                                data-ver-evento="${evento.id_evento_fifonafe}">
                                <i class="bi bi-eye"></i>
                            </button>

                            <button
                                type="button"
                                class="btn-tabla"
                                data-editar-evento="${evento.id_evento_fifonafe}">
                                <i class="bi bi-pencil"></i>
                            </button>

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

    elementos.eventosTabla
        ?.addEventListener(
            "click",
            event => {
                const boton =
                    event.target.closest(
                        "[data-ver-evento]"
                    );

                if (!boton) {
                    return;
                }

                const evento =
                    eventos.find(item =>
                        Number(
                            item.id_evento_fifonafe
                        ) ===
                        Number(
                            boton.dataset.verEvento
                        )
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
                        `Oficio: ${evento.numero_oficio || "—"}`,
                        `Fecha de oficio: ${evento.fecha_oficio || "—"}`,
                        `Fecha del evento: ${evento.fecha_evento || "—"}`,
                        `Ciclo de consulta: ${evento.ciclo_consulta || "—"}`,
                        `Conflicto impide retiro: ${formatoConflictos(evento.conflicto_impide_retiro)}`,
                        `Documento: ${
                            evento.id_documento
                                ? `#${evento.id_documento}`
                                : "—"
                        }`
                    ].join("\n")
                );
            }
        );


    /* =====================================================
                    ACCIONES TODAVÍA PENDIENTES
    ====================================================== */

    /*
     * Primero verificamos lectura correcta.
     * En la siguiente parte conectaremos:
     *
     * - PATCH del trámite
     * - agregar afectación
     * - crear/editar/eliminar evento
     * - intervinientes
     *
     * Para que no queden botones falsos mientras
     * hacemos esta prueba, los ocultamos temporalmente.
     */

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
        await cargarDatos();

        mostrarInformacion();
        mostrarAfectaciones();
        mostrarEventos();

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(error);
    }
});