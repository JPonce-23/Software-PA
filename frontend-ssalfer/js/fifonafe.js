document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(window.location.search);

    const idProyectoNucleo = Number(
        parametros.get("id_proyecto_nucleo")
    );

    if (
        !Number.isInteger(idProyectoNucleo) ||
        idProyectoNucleo <= 0
    ) {
        alert(
            "Falta el identificador del proyecto-núcleo."
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

        btnNuevoTramite:
            document.getElementById("btnNuevoTramite"),

        tramitesContainer:
            document.getElementById("tramitesContainer"),

        sinTramites:
            document.getElementById("sinTramites"),

        formularioContenedor:
            document.getElementById("formularioContenedor"),

        btnCerrarFormulario:
            document.getElementById("btnCerrarFormulario"),

        btnCancelar:
            document.getElementById("btnCancelar"),

        formFifonafe:
            document.getElementById("formFifonafe"),

        afectacionesContainer:
            document.getElementById("afectacionesContainer"),

        errorAfectaciones:
            document.getElementById("errorAfectaciones"),

        eventosContainer:
            document.getElementById("eventosContainer"),

        btnAgregarEvento:
            document.getElementById("btnAgregarEvento"),

        campoEstatus:
            document.getElementById("estatus"),

        campoAcuseFecha:
            document.getElementById("acuseFecha"),

        campoHayConflictos:
            document.getElementById("hayConflictos"),

        campoResultadoConflictos:
            document.getElementById("campoResultadoConflictos"),

        campoResultadoTexto:
            document.getElementById("resultadoNoConflictos")
    };


    /* =====================================================
                        ESTADO
    ====================================================== */

    let tramites = [];
    let afectacionesNucleo = [];
    let tiposEvento = [];
    let contadorEventos = 0;
    let puedeCapturar = false;


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

    function nombreEstatus(valor) {
        const nombres = {
            programado: "Programado",
            pendiente: "Pendiente",
            completo: "Completo",
            cancelado: "Cancelado",
            otro: "Otro"
        };

        return nombres[valor] || valor || "—";
    }

    function claseEstatus(valor) {
        return `estado-${valor || "pendiente"}`;
    }


    /* =====================================================
                        SESIÓN
    ====================================================== */

    try {
        const sesion =
            await window.AuthAPI.obtenerSesionActual();

        const rol = sesion?.user?.rol;

        puedeCapturar =
            rol === "admin" || rol === "operador";

    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(error);
        return;
    }

    if (!puedeCapturar && elementos.btnNuevoTramite) {
        elementos.btnNuevoTramite.hidden = true;
        elementos.btnNuevoTramite.style.display = "none";
    }


    /* =====================================================
                    CARGAR DATOS REALES
    ====================================================== */

    async function cargarDatos() {
        const [
            listaTramites,
            listaAfectaciones,
            listaTipos
        ] = await Promise.all([
            window.FifonafeAPI.listarPorProyectoNucleo(
                idProyectoNucleo
            ),

            window.AfectacionesAPI.listarPorProyectoNucleo(
                idProyectoNucleo
            ),

            window.CatalogosAPI.obtenerOperativo(
                "tipo_evento_fifonafe"
            )
        ]);

        tramites =
            Array.isArray(listaTramites)
                ? listaTramites
                : [];

        afectacionesNucleo =
            Array.isArray(listaAfectaciones)
                ? listaAfectaciones
                : [];

        tiposEvento =
            Array.isArray(listaTipos)
                ? listaTipos
                : [];
    }

    async function recargar() {
        await cargarDatos();
        mostrarTramites();
    }


    /* =====================================================
                    RENDER DE LA LISTA
    ====================================================== */

    function referenciasAfectaciones(tramite) {
        const ids =
            new Set(
                (
                    Array.isArray(tramite.afectaciones)
                        ? tramite.afectaciones
                        : []
                ).map(item => Number(item.id_afectacion))
            );

        return afectacionesNucleo
            .filter(item =>
                ids.has(Number(item.id_afectacion))
            )
            .map(item =>
                item.referencia ||
                item.referencia_alfanumerica ||
                `#${item.id_afectacion}`
            );
    }

    function mostrarTramites() {
        elementos.tramitesContainer.innerHTML = "";

        if (!tramites.length) {
            elementos.sinTramites.hidden = false;
            return;
        }

        elementos.sinTramites.hidden = true;

        tramites.forEach(tramite => {
            const referencias = referenciasAfectaciones(tramite);

            const articulo = document.createElement("article");
            articulo.className = "tramite";

            articulo.innerHTML = `
                <div class="tramite-header">
                    <div>
                        <span class="tramite-id">
                            FIF-${escaparHTML(tramite.id_tramite_fifonafe)}
                        </span>
                        <h3>Trámite FIFONAFE</h3>
                    </div>

                    <span class="estado ${claseEstatus(tramite.estatus)}">
                        ${escaparHTML(nombreEstatus(tramite.estatus))}
                    </span>
                </div>

                <div class="tramite-datos">
                    <div>
                        <span>Afectaciones</span>
                        <strong>
                            ${escaparHTML(
                                referencias.length
                                    ? referencias.join(" · ")
                                    : "—"
                            )}
                        </strong>
                    </div>

                    <div>
                        <span>Acuse FIFONAFE</span>
                        <strong>
                            ${escaparHTML(texto(tramite.acuse_fifonafe_fecha))}
                        </strong>
                    </div>

                    <div>
                        <span>Conflictos</span>
                        <strong>
                            ${escaparHTML(formatoConflictos(tramite.hay_conflictos))}
                        </strong>
                    </div>
                </div>

                <div class="tramite-acciones">
                    <button
                        type="button"
                        class="btn-secundario btn-ver-tramite"
                        data-id-fifonafe="${tramite.id_tramite_fifonafe}">

                        <i class="bi bi-eye"></i>
                        Ver seguimiento

                    </button>
                </div>
            `;

            elementos.tramitesContainer.appendChild(articulo);
        });
    }

    elementos.tramitesContainer
        ?.addEventListener("click", event => {
            const boton =
                event.target.closest("[data-id-fifonafe]");

            if (!boton) {
                return;
            }

            window.location.href =
                `/pages/fichaFifonafe.html?id_fifonafe=${encodeURIComponent(
                    boton.dataset.idFifonafe
                )}&id_proyecto_nucleo=${encodeURIComponent(
                    idProyectoNucleo
                )}`;
        });


    /* =====================================================
                FORMULARIO NUEVO TRÁMITE
    ====================================================== */

    function poblarAfectaciones() {
        if (!elementos.afectacionesContainer) {
            return;
        }

        if (!afectacionesNucleo.length) {
            elementos.afectacionesContainer.innerHTML =
                `<p class="tabla-vacia">No hay afectaciones registradas en este núcleo.</p>`;
            return;
        }

        elementos.afectacionesContainer.innerHTML =
            afectacionesNucleo.map(item => `
                <label class="afectacion-opcion">
                    <input
                        type="checkbox"
                        name="ids_afectacion"
                        value="${item.id_afectacion}">

                    <span>
                        <strong>
                            ${escaparHTML(
                                item.referencia ||
                                item.referencia_alfanumerica ||
                                `#${item.id_afectacion}`
                            )}
                        </strong>
                        <small>
                            ${escaparHTML(item.tipo_afectacion || "—")}
                        </small>
                    </span>
                </label>
            `).join("");
    }

    function opcionesTipoEvento() {
        return tiposEvento.map(item => `
            <option value="${escaparHTML(item.id_catalogo_opcion)}">
                ${escaparHTML(
                    item.nombre ||
                    item.codigo ||
                    `#${item.id_catalogo_opcion}`
                )}
            </option>
        `).join("");
    }

    function crearBloqueEvento(indice) {
        const articulo = document.createElement("article");
        articulo.className = "evento";
        articulo.dataset.evento = "";

        articulo.innerHTML = `
            <div class="evento-header">
                <div>
                    <span class="numero-evento">${indice + 1}</span>
                    <h4>Evento ${indice + 1}</h4>
                </div>

                <button type="button" class="btn-eliminar-evento">
                    <i class="bi bi-trash"></i>
                </button>
            </div>

            <div class="form-grid">
                <div class="campo">
                    <label>
                        Ordinal <span class="obligatorio">*</span>
                    </label>
                    <input
                        type="number"
                        name="eventos[${indice}][ordinal]"
                        min="1" step="1" value="${indice + 1}" required>
                </div>

                <div class="campo">
                    <label>
                        Tipo de evento <span class="obligatorio">*</span>
                    </label>
                    <select name="eventos[${indice}][id_tipo_evento]" required>
                        <option value="">Seleccionar tipo</option>
                        ${opcionesTipoEvento()}
                    </select>
                </div>

                <div class="campo">
                    <label>Origen <span class="opcional">Opcional</span></label>
                    <input type="text" name="eventos[${indice}][origen]" maxlength="200">
                </div>

                <div class="campo">
                    <label>Destino <span class="opcional">Opcional</span></label>
                    <input type="text" name="eventos[${indice}][destino]" maxlength="200">
                </div>

                <div class="campo">
                    <label>
                        Número de oficio <span class="opcional">Opcional</span>
                    </label>
                    <input type="text" name="eventos[${indice}][numero_oficio]" maxlength="150">
                </div>

                <div class="campo">
                    <label>
                        Fecha del oficio <span class="opcional">Opcional</span>
                    </label>
                    <input type="date" name="eventos[${indice}][fecha_oficio]">
                </div>

                <div class="campo">
                    <label>
                        Documento <span class="opcional">Opcional</span>
                    </label>
                    <input type="number" name="eventos[${indice}][id_documento]" min="1">
                    <small>Referencia a un documento ya registrado.</small>
                </div>
            </div>
        `;

        articulo.querySelector(".btn-eliminar-evento")
            .addEventListener("click", () => {
                articulo.remove();
                renumerarEventos();
            });

        return articulo;
    }

    function renumerarEventos() {
        const bloques =
            elementos.eventosContainer.querySelectorAll("[data-evento]");

        bloques.forEach((bloque, indice) => {
            bloque.querySelector(".numero-evento").textContent =
                String(indice + 1);

            bloque.querySelector("h4").textContent =
                `Evento ${indice + 1}`;
        });
    }

    function agregarBloqueEvento() {
        const bloque = crearBloqueEvento(contadorEventos);
        contadorEventos += 1;
        elementos.eventosContainer.appendChild(bloque);
    }

    function actualizarCampoResultado() {
        const visible =
            elementos.campoHayConflictos.value === "false";

        elementos.campoResultadoConflictos.hidden = !visible;

        if (!visible) {
            elementos.campoResultadoTexto.value = "";
        }
    }

    elementos.campoHayConflictos
        ?.addEventListener("change", actualizarCampoResultado);

    function reiniciarFormulario() {
        elementos.formFifonafe.reset();
        elementos.eventosContainer.innerHTML = "";
        contadorEventos = 0;
        agregarBloqueEvento();
        elementos.errorAfectaciones.hidden = true;
        actualizarCampoResultado();
    }

    function abrirFormulario() {
        if (!puedeCapturar) {
            return;
        }

        poblarAfectaciones();
        reiniciarFormulario();

        elementos.formularioContenedor.hidden = false;

        elementos.formularioContenedor.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function cerrarFormulario() {
        elementos.formularioContenedor.hidden = true;
    }

    elementos.btnNuevoTramite?.addEventListener("click", abrirFormulario);
    elementos.btnCerrarFormulario?.addEventListener("click", cerrarFormulario);
    elementos.btnCancelar?.addEventListener("click", cerrarFormulario);
    elementos.btnAgregarEvento?.addEventListener("click", agregarBloqueEvento);


    /* =====================================================
                    LEER EVENTOS DEL FORMULARIO
    ====================================================== */

    function leerEventos() {
        const bloques =
            [...elementos.eventosContainer.querySelectorAll("[data-evento]")];

        return bloques.map(bloque => {
            const obtener = sufijo =>
                bloque.querySelector(`[name$="[${sufijo}]"]`);

            const idDocumentoValor =
                obtener("id_documento")?.value.trim();

            return {
                ordinal: Number(obtener("ordinal")?.value),
                idTipoEvento: Number(obtener("id_tipo_evento")?.value),
                origen: obtener("origen")?.value.trim() || null,
                destino: obtener("destino")?.value.trim() || null,
                numeroOficio: obtener("numero_oficio")?.value.trim() || null,
                fechaOficio: obtener("fecha_oficio")?.value || null,
                idDocumento: idDocumentoValor ? Number(idDocumentoValor) : null
            };
        });
    }


    /* =====================================================
                        GUARDAR TRÁMITE
    ====================================================== */

    async function guardarTramite(event) {
        event.preventDefault();

        if (!puedeCapturar) {
            return;
        }

        const idsAfectacion =
            [...elementos.formFifonafe.querySelectorAll(
                'input[name="ids_afectacion"]:checked'
            )].map(input => Number(input.value));

        if (!idsAfectacion.length) {
            elementos.errorAfectaciones.hidden = false;
            return;
        }

        elementos.errorAfectaciones.hidden = true;

        const eventos = leerEventos();

        for (const evento of eventos) {
            if (!Number.isInteger(evento.ordinal) || evento.ordinal <= 0) {
                alert("Revisa el ordinal de los eventos.");
                return;
            }

            if (!Number.isInteger(evento.idTipoEvento) || evento.idTipoEvento <= 0) {
                alert("Selecciona el tipo de evento en cada evento agregado.");
                return;
            }
        }

        const conflictosValor = elementos.campoHayConflictos.value;

        const payload = {
            estatus: elementos.campoEstatus.value,

            acuse_fifonafe_fecha:
                elementos.campoAcuseFecha.value || null,

            hay_conflictos:
                conflictosValor === ""
                    ? null
                    : conflictosValor === "true",

            resultado_no_conflictos:
                conflictosValor === "false"
                    ? (elementos.campoResultadoTexto.value.trim() || null)
                    : null
        };

        const botonEnviar =
            elementos.formFifonafe.querySelector('button[type="submit"]');

        if (botonEnviar) {
            botonEnviar.disabled = true;
        }

        try {
            const tramiteCreado =
                await window.FifonafeAPI.crear(idProyectoNucleo, payload);

            const idTramite = tramiteCreado?.id_tramite_fifonafe;

            if (!idTramite) {
                throw new Error(
                    "El backend no devolvió id_tramite_fifonafe al crear el trámite."
                );
            }

            for (const idAfectacion of idsAfectacion) {
                await window.FifonafeAPI.agregarAfectacion(
                    idTramite,
                    idAfectacion
                );
            }

            for (const evento of eventos) {
                await window.FifonafeAPI.crearEvento(idTramite, {
                    ordinal: evento.ordinal,
                    id_tipo_evento: evento.idTipoEvento,
                    origen: evento.origen,
                    destino: evento.destino,
                    numero_oficio: evento.numeroOficio,
                    fecha_oficio: evento.fechaOficio,
                    id_documento: evento.idDocumento
                });
            }

            alert("Trámite FIFONAFE registrado correctamente.");

            cerrarFormulario();
            await recargar();

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(error);

        } finally {
            if (botonEnviar) {
                botonEnviar.disabled = false;
            }
        }
    }

    elementos.formFifonafe?.addEventListener("submit", guardarTramite);


    /* =====================================================
                        VOLVER
    ====================================================== */

    elementos.btnVolver?.addEventListener("click", () => {
        window.location.href =
            `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                idProyectoNucleo
            )}`;
    });


    /* =====================================================
                        INICIALIZACIÓN
    ====================================================== */

    try {
        await recargar();

    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(error);
    }
});