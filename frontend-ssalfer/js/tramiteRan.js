document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    /* =====================================================
                        CONTEXTO
    ====================================================== */

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idAsamblea =
        numeroParametro("id_asamblea");

    const idConvenio =
        numeroParametro("id_convenio");

    const idOrv =
        numeroParametro("id_orv");

    const objetivos = [
        idAsamblea
            ? {
                tipo: "asamblea",
                id: idAsamblea,
                campo: "id_asamblea",
                nombre: "Asamblea"
            }
            : null,

        idConvenio
            ? {
                tipo: "convenio",
                id: idConvenio,
                campo: "id_convenio",
                nombre: "Convenio"
            }
            : null,

        idOrv
            ? {
                tipo: "orv",
                id: idOrv,
                campo: "id_orv",
                nombre: "Órgano de Representación (ORV)"
            }
            : null
    ].filter(Boolean);

    const objetivo =
        objetivos.length === 1
            ? objetivos[0]
            : null;


    /* =====================================================
                        ELEMENTOS
    ====================================================== */

    const elementos = {
        form:
            document.getElementById(
                "formTramiteRan"
            ),

        eventosLista:
            document.getElementById(
                "eventosLista"
            ),

        btnAgregarEvento:
            document.getElementById(
                "btnAgregarEvento"
            ),

        btnCancelar:
            document.getElementById(
                "btnCancelar"
            ),

        btnVolver:
            document.getElementById(
                "btnVolver"
            ),

        enlaceOrigen:
            document.getElementById(
                "enlaceAsamblea"
            ),

        objetivoNombre:
            document.getElementById(
                "objetivoNombre"
            ),

        objetivoDescripcion:
            document.getElementById(
                "objetivoDescripcion"
            )
    };

    const btnGuardar =
        elementos.form?.querySelector(
            '[type="submit"]'
        );

    let tiposEvento = [];
    let puedeCapturar = false;


    /* =====================================================
                        UTILIDADES
    ====================================================== */

    function numeroParametro(nombre) {
        const valor =
            parametros.get(nombre);

        if (!valor) {
            return null;
        }

        const numero =
            Number(valor);

        return Number.isInteger(numero) &&
            numero > 0
            ? numero
            : null;
    }

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
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

        return Number.isInteger(numero) &&
            numero > 0
            ? numero
            : NaN;
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


    /* =====================================================
                        CONTEXTO
    ====================================================== */

    function mostrarContexto() {
        if (!objetivo) {
            if (elementos.objetivoNombre) {
                elementos.objetivoNombre.textContent =
                    "Origen no válido";
            }

            if (elementos.objetivoDescripcion) {
                elementos.objetivoDescripcion.textContent =
                    "Esta pantalla debe abrirse desde exactamente una Asamblea, Convenio u ORV.";
            }

            bloquearCaptura();

            return;
        }

        if (elementos.objetivoNombre) {
            elementos.objetivoNombre.textContent =
                `${objetivo.nombre} #${objetivo.id}`;
        }

        if (elementos.objetivoDescripcion) {
            elementos.objetivoDescripcion.textContent =
                `El trámite quedará asociado a ${objetivo.nombre.toLowerCase()} #${objetivo.id}.`;
        }

        /*
         * El elemento conserva el id histórico "enlaceAsamblea",
         * pero se reutiliza como enlace genérico de origen.
         */
        if (elementos.enlaceOrigen) {
            elementos.enlaceOrigen.textContent =
                `${objetivo.nombre} #${objetivo.id}`;

            elementos.enlaceOrigen.href = "#";

            elementos.enlaceOrigen.addEventListener(
                "click",
                event => {
                    event.preventDefault();
                    window.history.back();
                }
            );
        }
    }

    function bloquearCaptura() {
        if (btnGuardar) {
            btnGuardar.disabled = true;
        }

        if (elementos.btnAgregarEvento) {
            elementos.btnAgregarEvento.disabled =
                true;
        }

        elementos.form
            ?.querySelectorAll(
                "input, select, textarea"
            )
            .forEach(campo => {
                campo.disabled = true;
            });
    }

    if (!puedeCapturar) {
        bloquearCaptura();
    }


    /* =====================================================
                    CATÁLOGO TIPO EVENTO
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

        if (!tiposEvento.length) {
            console.warn(
                "El catálogo tipo_evento_ran no contiene opciones."
            );
        }
    }

    function opcionesTipoEvento() {
        return tiposEvento
            .map(item => `
                <option value="${escaparHTML(
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
                        EVENTOS
    ====================================================== */

    function obtenerSiguienteOrdinal() {
        const ordinales =
            Array.from(
                elementos.eventosLista
                    ?.querySelectorAll(
                        ".evento-ordinal"
                    ) || []
            )
            .map(elemento =>
                Number(elemento.value)
            )
            .filter(numero =>
                Number.isInteger(numero) &&
                numero > 0
            );

        if (!ordinales.length) {
            return 1;
        }

        return Math.max(
            ...ordinales
        ) + 1;
    }

    function obtenerPlantillaEvento(
        ordinal
    ) {
        return `
            <div class="evento">

                <div class="evento-header">

                    <div class="evento-numero">
                        <span>
                            Evento
                        </span>

                        <strong>
                            ${ordinal}
                        </strong>
                    </div>

                    <button
                        type="button"
                        class="btn-eliminar-evento"
                        title="Eliminar evento">

                        <i class="bi bi-trash"></i>

                    </button>

                </div>

                <div class="form-grid evento-grid">

                    <div class="campo">

                        <label>
                            Orden
                            <span class="obligatorio">
                                *
                            </span>
                        </label>

                        <input
                            type="number"
                            class="evento-ordinal"
                            min="1"
                            step="1"
                            value="${ordinal}"
                            required>

                    </div>

                    <div class="campo">

                        <label>
                            Tipo de evento
                            <span class="obligatorio">
                                *
                            </span>
                        </label>

                        <select
                            class="evento-tipo"
                            required>

                            <option value="">
                                Selecciona una opción
                            </option>

                            ${opcionesTipoEvento()}

                        </select>

                    </div>

                    <div class="campo">

                        <label>
                            Fecha del evento
                        </label>

                        <input
                            type="date"
                            class="evento-fecha">

                    </div>

                    <div class="campo">

                        <label>
                            Número de solicitud
                        </label>

                        <input
                            type="text"
                            class="evento-solicitud"
                            maxlength="150">

                    </div>

                    <div class="campo">

                        <label>
                            Resultado
                        </label>

                        <input
                            type="text"
                            class="evento-resultado"
                            maxlength="250">

                    </div>

                    <div class="campo">

                        <label>
                            Calificación
                        </label>

                        <textarea
                            class="evento-calificacion"
                            rows="2"></textarea>

                    </div>

                    <div class="campo">

                        <label>
                            Folio / referencia
                        </label>

                        <input
                            type="text"
                            class="evento-folio"
                            maxlength="200">

                    </div>

                    <div class="campo">

                        <label>
                            ID de documento
                        </label>

                        <input
                            type="number"
                            class="evento-documento"
                            min="1"
                            step="1"
                            placeholder="Opcional">

                    </div>

                </div>

            </div>
        `;
    }

    function agregarEvento() {
        if (
            !puedeCapturar ||
            !objetivo
        ) {
            return;
        }

        const ordinal =
            obtenerSiguienteOrdinal();

        elementos.eventosLista
            ?.insertAdjacentHTML(
                "beforeend",
                obtenerPlantillaEvento(
                    ordinal
                )
            );
    }

    elementos.btnAgregarEvento
        ?.addEventListener(
            "click",
            agregarEvento
        );

    elementos.eventosLista
        ?.addEventListener(
            "click",
            event => {
                const boton =
                    event.target.closest(
                        ".btn-eliminar-evento"
                    );

                if (!boton) {
                    return;
                }

                /*
                 * El backend permite crear un trámite
                 * sin eventos, por lo que también se
                 * permite eliminar el último formulario.
                 */
                boton.closest(".evento")?.remove();
            }
        );


    /* =====================================================
                        VALIDACIÓN EVENTOS
    ====================================================== */

    function obtenerEventos() {
        const tarjetas =
            Array.from(
                elementos.eventosLista
                    ?.querySelectorAll(
                        ".evento"
                    ) || []
            );

        const resultado = [];
        const ordinales = new Set();

        for (const tarjeta of tarjetas) {
            const ordinalElemento =
                tarjeta.querySelector(
                    ".evento-ordinal"
                );

            const tipoElemento =
                tarjeta.querySelector(
                    ".evento-tipo"
                );

            const ordinal =
                Number(
                    ordinalElemento?.value
                );

            const idTipoEvento =
                Number(
                    tipoElemento?.value
                );

            if (
                !Number.isInteger(ordinal) ||
                ordinal <= 0
            ) {
                alert(
                    "El orden de cada evento debe ser un entero mayor que cero."
                );

                ordinalElemento?.focus();

                return null;
            }

            if (ordinales.has(ordinal)) {
                alert(
                    `El orden ${ordinal} está repetido.`
                );

                ordinalElemento?.focus();

                return null;
            }

            ordinales.add(ordinal);

            if (
                !Number.isInteger(
                    idTipoEvento
                ) ||
                idTipoEvento <= 0
            ) {
                alert(
                    `Selecciona el tipo del evento ${ordinal}.`
                );

                tipoElemento?.focus();

                return null;
            }

            const idDocumento =
                numeroOpcional(
                    tarjeta.querySelector(
                        ".evento-documento"
                    )
                );

            if (
                Number.isNaN(idDocumento)
            ) {
                alert(
                    `El documento del evento ${ordinal} no es válido.`
                );

                return null;
            }

            resultado.push({
                ordinal,

                id_tipo_evento:
                    idTipoEvento,

                fecha_evento:
                    textoOpcional(
                        tarjeta.querySelector(
                            ".evento-fecha"
                        )
                    ),

                numero_solicitud:
                    textoOpcional(
                        tarjeta.querySelector(
                            ".evento-solicitud"
                        )
                    ),

                resultado:
                    textoOpcional(
                        tarjeta.querySelector(
                            ".evento-resultado"
                        )
                    ),

                calificacion:
                    textoOpcional(
                        tarjeta.querySelector(
                            ".evento-calificacion"
                        )
                    ),

                folio_referencia:
                    textoOpcional(
                        tarjeta.querySelector(
                            ".evento-folio"
                        )
                    ),

                id_documento:
                    idDocumento
            });
        }

        return resultado;
    }


    /* =====================================================
                        GUARDAR
    ====================================================== */

    elementos.form?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            if (!puedeCapturar) {
                return;
            }

            if (!objetivo) {
                alert(
                    "No se puede registrar el trámite porque debe tener exactamente una Asamblea, Convenio u ORV de origen."
                );

                return;
            }

            if (
                !elementos.form.checkValidity()
            ) {
                elementos.form.reportValidity();
                return;
            }

            const eventos =
                obtenerEventos();

            if (eventos === null) {
                return;
            }

            const formData =
                new FormData(
                    elementos.form
                );

            const payload = {
                id_asamblea: null,
                id_convenio: null,
                id_orv: null,

                fecha_programada_ingreso:
                    formData.get(
                        "fecha_programada_ingreso"
                    ) || null,

                referencia_expediente:
                    formData.get(
                        "referencia_expediente"
                    )?.trim() || null
            };

            payload[objetivo.campo] =
                objetivo.id;

            /*
             * Conservamos la creación de eventos mediante
             * sus endpoints explícitos porque esos endpoints
             * están confirmados en el backend.
             *
             * Así no asumimos que create_ran_procedure()
             * persista los eventos anidados internamente.
             */
            if (btnGuardar) {
                btnGuardar.disabled = true;
            }

            let tramiteCreado = null;

            try {
                tramiteCreado =
                    await window.TramitesRanAPI
                        .crear(payload);

                for (const eventoRan of eventos) {
                    try {
                        await window.TramitesRanAPI
                            .crearEvento(
                                tramiteCreado
                                    .id_tramite_ran,
                                eventoRan
                            );

                    } catch (errorEvento) {
                        /*
                         * En este punto el trámite ya existe.
                         * No se vuelve a crear para evitar
                         * duplicarlo al reintentar.
                         */
                        window.ClienteAPI
                            .mostrarErrorAPI(
                                errorEvento
                            );

                        alert(
                            `El trámite #${tramiteCreado.id_tramite_ran} sí fue creado, pero no fue posible guardar todos sus eventos. Puedes completarlos desde su ficha.`
                        );

                        window.location.href =
                            `/pages/fichaRan.html?id_tramite_ran=${encodeURIComponent(
                                tramiteCreado.id_tramite_ran
                            )}`;

                        return;
                    }
                }

                alert(
                    "El trámite ante el RAN se guardó correctamente."
                );

                window.location.href =
                    `/pages/fichaRan.html?id_tramite_ran=${encodeURIComponent(
                        tramiteCreado.id_tramite_ran
                    )}`;

            } catch (error) {
                window.ClienteAPI
                    .mostrarErrorAPI(error);

            } finally {
                if (btnGuardar) {
                    btnGuardar.disabled = false;
                }
            }
        }
    );


    /* =====================================================
                        VOLVER / CANCELAR
    ====================================================== */

    function volver() {
        window.history.back();
    }

    elementos.btnVolver
        ?.addEventListener(
            "click",
            volver
        );

    elementos.btnCancelar
        ?.addEventListener(
            "click",
            volver
        );


    /* =====================================================
                        INICIALIZACIÓN
    ====================================================== */

    mostrarContexto();

    /*
     * Eliminamos cualquier evento de ejemplo que
     * estuviera escrito estáticamente en el HTML.
     */
    if (elementos.eventosLista) {
        elementos.eventosLista.innerHTML =
            "";
    }

    try {
        await cargarCatalogo();

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(error);

        bloquearCaptura();

        return;
    }

    /*
     * Dejamos un evento preparado por comodidad,
     * pero ahora sí puede eliminarse si el trámite
     * todavía no tiene movimientos.
     */
    if (
        objetivo &&
        puedeCapturar
    ) {
        agregarEvento();
    }
});