document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idConvenio =
        Number(
            parametros.get("id_convenio") ||
            parametros.get("id")
        );

    const elementos = {
        main:
            document.querySelector("main.contenedor"),

        tituloConvenio:
            document.getElementById("tituloConvenio"),

        btnVolver:
            document.getElementById("btnVolver"),

        btnEditarConvenio:
            document.getElementById("btnEditarConvenio"),

        estadoConvenio:
            document.getElementById("estadoConvenio"),

        tipoInstrumento:
            document.getElementById("tipoInstrumento"),

        tipoConvenio:
            document.getElementById("tipoConvenio"),

        ambito:
            document.getElementById("ambito"),

        consecutivo:
            document.getElementById("consecutivo"),

        modalidadEspecial:
            document.getElementById("modalidadEspecial"),

        descripcionModalidadDato:
            document.getElementById("descripcionModalidadDato"),

        descripcionModalidad:
            document.getElementById("descripcionModalidad"),

        descripcionInstrumentoDato:
            document.getElementById("descripcionInstrumentoDato"),

        descripcionInstrumento:
            document.getElementById("descripcionInstrumento"),

        fechaProgramadaFirma:
            document.getElementById("fechaProgramadaFirma"),

        fechaFirma:
            document.getElementById("fechaFirma"),

        monto90:
            document.getElementById("monto90"),

        monto100:
            document.getElementById("monto100"),

        montoBDT:
            document.getElementById("montoBDT"),

        superficie:
            document.getElementById("superficie"),

        convenioPadre:
            document.getElementById("convenioPadre"),

        padreNombre:
            document.getElementById("padreNombre"),

        padreDescripcion:
            document.getElementById("padreDescripcion"),

        btnVerConvenioPadre:
            document.getElementById("btnVerConvenioPadre"),

        conveniosDerivadosSeccion:
            document.getElementById("conveniosDerivadosSeccion"),

        conveniosDerivados:
            document.getElementById("conveniosDerivados"),

        afectacionesTabla:
            document.getElementById("afectacionesTabla"),

        btnAgregarAfectacion:
            document.getElementById("btnAgregarAfectacion"),

        comparecientesTabla:
            document.getElementById("comparecientesTabla"),

        btnAgregarCompareciente:
            document.getElementById("btnAgregarCompareciente"),

        tramitesRanTabla:
            document.getElementById("tramitesRanTabla"),

        btnNuevoTramiteRan:
            document.getElementById("btnNuevoTramiteRan")
    };

    if (
        !Number.isInteger(idConvenio) ||
        idConvenio <= 0
    ) {
        window.ClienteAPI.mostrarErrorAPI(
            new Error(
                "No se puede mostrar el convenio porque falta un id_convenio válido."
            )
        );

        return;
    }

    let convenio = null;
    let afectacionesConvenio = [];
    let detallesAfectaciones = new Map();
    let comparecientes = [];
    let tramitesRan = [];
    let puedeCapturar = false;

    const nombresCalidad =
        new Map();

    const nombresAcreditacion =
        new Map();

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function fechaVisual(valor) {
        if (!valor) {
            return "—";
        }

        const partes =
            String(valor).split("-");

        return partes.length === 3
            ? `${partes[2]}/${partes[1]}/${partes[0]}`
            : String(valor);
    }

    function moneda(valor) {
        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return "—";
        }

        return new Intl.NumberFormat(
            "es-MX",
            {
                style: "currency",
                currency: "MXN"
            }
        ).format(
            Number(valor)
        );
    }

    function superficie(valor) {
        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return "—";
        }

        return `${Number(valor).toFixed(6)} ha`;
    }

    function etiquetaTipoInstrumento(valor) {
        return {
            convenio: "Convenio",
            otro: "Otro instrumento"
        }[valor] || valor || "—";
    }

    function etiquetaTipoConvenio(valor) {
        return {
            cop_original:
                "COP original",

            modificatorio:
                "Modificatorio",

            superficie_adicional:
                "Superficie adicional",

            obras_complementarias:
                "Obras complementarias",

            ampliacion:
                "Ampliación",

            ampliacion_remanente:
                "Ampliación de remanente"
        }[valor] || valor || "—";
    }

    function etiquetaAmbito(valor) {
        return {
            colectivo: "Colectivo",
            individual: "Individual"
        }[valor] || valor || "—";
    }

    function etiquetaModalidad(valor) {
        return {
            permuta: "Permuta",
            otra: "Otra"
        }[valor] || valor || "—";
    }

    function etiquetaEfectoSuperficie(valor) {
        return {
            adicion: "Adición",
            sustitucion: "Sustitución",
            correccion: "Corrección",
            sin_cambio: "Sin cambio",
            pendiente: "Pendiente"
        }[valor] || valor || "—";
    }

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
            puedeCapturar = false;
        }

        [
            elementos.btnEditarConvenio,
            elementos.btnAgregarAfectacion,
            elementos.btnAgregarCompareciente,
            elementos.btnNuevoTramiteRan
        ].forEach(
            boton => {
                if (boton) {
                    boton.hidden =
                        !puedeCapturar;
                }
            }
        );
    }

    async function cargarCatalogos() {
        const [
            calidad,
            acreditacion
        ] =
            await Promise.all([
                window.CatalogosAPI
                    .obtenerOperativo(
                        "calidad_compareciente_convenio"
                    )
                    .catch(
                        () => []
                    ),

                window.CatalogosAPI
                    .obtenerOperativo(
                        "tipo_acreditacion_derecho_individual"
                    )
                    .catch(
                        () => []
                    )
            ]);

        (
            Array.isArray(calidad)
                ? calidad
                : []
        ).forEach(
            item => {
                nombresCalidad.set(
                    Number(
                        item.id_catalogo_opcion
                    ),
                    item.nombre ||
                    item.codigo ||
                    `#${item.id_catalogo_opcion}`
                );
            }
        );

        (
            Array.isArray(acreditacion)
                ? acreditacion
                : []
        ).forEach(
            item => {
                nombresAcreditacion.set(
                    Number(
                        item.id_catalogo_opcion
                    ),
                    item.nombre ||
                    item.codigo ||
                    `#${item.id_catalogo_opcion}`
                );
            }
        );
    }

    async function cargarDatos() {
        [
            convenio,
            afectacionesConvenio,
            comparecientes,
            tramitesRan
        ] =
            await Promise.all([
                window.ConveniosAPI.obtener(
                    idConvenio
                ),

                window.ConveniosAPI
                    .listarAfectacionesAdicionales(
                        idConvenio
                    ),

                window.ConveniosAPI
                    .listarComparecientes(
                        idConvenio
                    ),

                window.ConveniosAPI
                    .listarTramitesRan(
                        idConvenio
                    )
            ]);

        afectacionesConvenio =
            Array.isArray(
                afectacionesConvenio
            )
                ? afectacionesConvenio
                : [];

        comparecientes =
            Array.isArray(comparecientes)
                ? comparecientes
                : [];

        tramitesRan =
            Array.isArray(tramitesRan)
                ? tramitesRan
                : [];

        const detalles =
            await Promise.all(
                afectacionesConvenio.map(
                    relacion =>
                        window.AfectacionesAPI
                            .obtener(
                                relacion.id_afectacion
                            )
                            .then(
                                afectacion => [
                                    Number(
                                        relacion.id_afectacion
                                    ),
                                    afectacion
                                ]
                            )
                            .catch(
                                () => [
                                    Number(
                                        relacion.id_afectacion
                                    ),
                                    null
                                ]
                            )
                )
            );

        detallesAfectaciones =
            new Map(
                detalles
            );
    }

    function renderInformacionGeneral() {
        document.title =
            `Convenio #${convenio.id_convenio} | SSALFER`;

        elementos.tituloConvenio.textContent =
            `Convenio #${convenio.id_convenio}`;

        elementos.estadoConvenio.textContent =
            convenio.fecha_firma
                ? "Firmado"
                : "Registrado";

        elementos.tipoInstrumento.textContent =
            etiquetaTipoInstrumento(
                convenio.tipo_instrumento
            );

        elementos.tipoConvenio.textContent =
            etiquetaTipoConvenio(
                convenio.tipo_convenio
            );

        elementos.ambito.textContent =
            etiquetaAmbito(
                convenio.ambito
            );

        elementos.consecutivo.textContent =
            convenio.consecutivo ??
            "—";

        elementos.modalidadEspecial.textContent =
            etiquetaModalidad(
                convenio.modalidad_especial
            );

        if (
            convenio.descripcion_modalidad
        ) {
            elementos.descripcionModalidadDato.style.display =
                "";

            elementos.descripcionModalidad.textContent =
                convenio.descripcion_modalidad;

        } else {
            elementos.descripcionModalidadDato.style.display =
                "none";
        }

        if (
            convenio.descripcion_instrumento
        ) {
            elementos.descripcionInstrumentoDato.style.display =
                "";

            elementos.descripcionInstrumento.textContent =
                convenio.descripcion_instrumento;

        } else {
            elementos.descripcionInstrumentoDato.style.display =
                "none";
        }

        elementos.fechaProgramadaFirma.textContent =
            fechaVisual(
                convenio.fecha_programada_firma
            );

        elementos.fechaFirma.textContent =
            fechaVisual(
                convenio.fecha_firma
            );

        elementos.monto90.textContent =
            moneda(
                convenio.monto_90
            );

        elementos.monto100.textContent =
            moneda(
                convenio.monto_100
            );

        elementos.montoBDT.textContent =
            moneda(
                convenio.monto_bdt
            );

        elementos.superficie.textContent =
            superficie(
                convenio.superficie_ha
            );
    }

    async function renderConvenioPadre() {
        if (
            !convenio.id_convenio_padre
        ) {
            elementos.padreNombre.textContent =
                "Sin convenio anterior";

            elementos.padreDescripcion.textContent =
                "Este convenio no tiene un convenio padre registrado.";

            elementos.btnVerConvenioPadre.style.display =
                "none";

            return;
        }

        try {
            const padre =
                await window.ConveniosAPI.obtener(
                    convenio.id_convenio_padre
                );

            elementos.padreNombre.textContent =
                `Convenio #${padre.id_convenio}`;

            elementos.padreDescripcion.textContent =
                `${etiquetaTipoConvenio(
                    padre.tipo_convenio
                )} · ${etiquetaAmbito(
                    padre.ambito
                )}`;

            elementos.btnVerConvenioPadre.style.display =
                "";

            elementos.btnVerConvenioPadre.onclick =
                () => {
                    window.location.href =
                        `/pages/fichaConvenio.html?id_convenio=${encodeURIComponent(
                            padre.id_convenio
                        )}`;
                };

        } catch {
            elementos.padreNombre.textContent =
                `Convenio #${convenio.id_convenio_padre}`;

            elementos.padreDescripcion.textContent =
                "No fue posible cargar el detalle del convenio anterior.";

            elementos.btnVerConvenioPadre.style.display =
                "";
        }

        /*
         * El backend actual no expone un endpoint
         * "listar convenios hijos de X".
         *
         * No inventamos derivados en frontend.
         */
        elementos.conveniosDerivadosSeccion.style.display =
            "none";
    }

    function renderAfectaciones() {
        elementos.afectacionesTabla.innerHTML =
            "";

        if (
            afectacionesConvenio.length === 0
        ) {
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

        afectacionesConvenio.forEach(
            relacion => {
                const detalle =
                    detallesAfectaciones.get(
                        Number(
                            relacion.id_afectacion
                        )
                    );

                const fila =
                    document.createElement(
                        "tr"
                    );

                fila.innerHTML = `
                    <td>
                        AF-${String(
                            relacion.id_afectacion
                        ).padStart(
                            3,
                            "0"
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            detalle?.tipo_afectacion
                                ? etiquetaAmbito(
                                    detalle.tipo_afectacion
                                )
                                : "—"
                        )}
                    </td>

                    <td>
                        <span class="etiqueta-tabla">
                            ${escaparHTML(
                                relacion.rol ===
                                    "principal"
                                    ? "Principal"
                                    : "Adicional"
                            )}
                        </span>
                    </td>

                    <td>
                        <button
                            type="button"
                            class="btn-tabla"
                            data-ver-afectacion="${relacion.id_afectacion}"
                            title="Ver afectación">

                            <i class="bi bi-eye"></i>

                        </button>
                    </td>
                `;

                elementos.afectacionesTabla.appendChild(
                    fila
                );
            }
        );
    }

    function renderComparecientes() {
        elementos.comparecientesTabla.innerHTML =
            "";

        if (
            comparecientes.length === 0
        ) {
            elementos.comparecientesTabla.innerHTML = `
                <tr>
                    <td
                        colspan="8"
                        class="tabla-vacia">

                        No hay comparecientes registrados.

                    </td>
                </tr>
            `;

            return;
        }

        comparecientes.forEach(
            item => {
                const fila =
                    document.createElement(
                        "tr"
                    );

                fila.innerHTML = `
                    <td>
                        Persona #${item.id_persona}
                    </td>

                    <td>
                        ${escaparHTML(
                            nombresCalidad.get(
                                Number(
                                    item.id_tipo_calidad
                                )
                            ) ||
                            `#${item.id_tipo_calidad}`
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            item.id_tipo_acreditacion
                                ? (
                                    nombresAcreditacion.get(
                                        Number(
                                            item.id_tipo_acreditacion
                                        )
                                    ) ||
                                    `#${item.id_tipo_acreditacion}`
                                )
                                : "—"
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            item.nombre_en_instrumento
                        )}
                    </td>

                    <td>
                        ${item.es_firmante
                            ? "Sí"
                            : "No"}
                    </td>

                    <td>
                        ${item.es_beneficiario_pago
                            ? "Sí"
                            : "No"}
                    </td>

                    <td>
                        ${item.requiere_revision
                            ? escaparHTML(
                                item.motivo_revision ||
                                "Sí"
                            )
                            : "No"}
                    </td>

                    <td>
                        ${
                            puedeCapturar
                                ? `
                                    <button
                                        type="button"
                                        class="btn-tabla"
                                        data-eliminar-compareciente="${item.id_compareciente}"
                                        title="Dar de baja compareciente">

                                        <i class="bi bi-trash"></i>

                                    </button>
                                `
                                : "—"
                        }
                    </td>
                `;

                elementos.comparecientesTabla.appendChild(
                    fila
                );
            }
        );
    }

    function renderTramitesRan() {
        elementos.tramitesRanTabla.innerHTML =
            "";

        if (
            tramitesRan.length === 0
        ) {
            elementos.tramitesRanTabla.innerHTML = `
                <tr>
                    <td
                        colspan="4"
                        class="tabla-vacia">

                        No hay trámites RAN registrados.

                    </td>
                </tr>
            `;

            return;
        }

        tramitesRan.forEach(
            tramite => {
                const fila =
                    document.createElement(
                        "tr"
                    );

                fila.innerHTML = `
                    <td>
                        Trámite #${tramite.id_tramite_ran}
                    </td>

                    <td>
                        ${fechaVisual(
                            tramite.fecha_programada_ingreso
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            tramite.referencia_expediente ||
                            "—"
                        )}
                    </td>

                    <td>
                        <a
                            class="btn-tabla"
                            href="/pages/fichaRan.html?id_tramite_ran=${encodeURIComponent(
                                tramite.id_tramite_ran
                            )}">

                            <i class="bi bi-eye"></i>

                        </a>
                    </td>
                `;

                elementos.tramitesRanTabla.appendChild(
                    fila
                );
            }
        );
    }

    function crearPanelEdicion() {
        let panel =
            document.getElementById(
                "panelEdicionConvenio"
            );

        if (panel) {
            return panel;
        }

        panel =
            document.createElement(
                "section"
            );

        panel.id =
            "panelEdicionConvenio";

        panel.className =
            "bloque";

        panel.hidden =
            true;

        panel.innerHTML = `
            <div class="bloque-titulo">

                <div class="bloque-titulo-info">

                    <i class="bi bi-pencil"></i>

                    <div>
                        <h2>
                            Editar convenio
                        </h2>

                        <p>
                            Actualiza fechas, montos y superficie.
                        </p>
                    </div>

                </div>

            </div>

            <form id="formEditarConvenio">

                <div class="form-grid">

                    <div class="campo">

                        <label>
                            Fecha programada de firma
                        </label>

                        <input
                            id="editFechaProgramada"
                            type="date">

                    </div>

                    <div class="campo">

                        <label>
                            Fecha de firma
                        </label>

                        <input
                            id="editFechaFirma"
                            type="date">

                    </div>

                    <div class="campo">

                        <label>
                            Monto 90%
                        </label>

                        <input
                            id="editMonto90"
                            type="number"
                            min="0"
                            step="0.01">

                    </div>

                    <div class="campo">

                        <label>
                            Monto 100%
                        </label>

                        <input
                            id="editMonto100"
                            type="number"
                            min="0"
                            step="0.01">

                    </div>

                    <div class="campo">

                        <label>
                            Monto BDT
                        </label>

                        <input
                            id="editMontoBdt"
                            type="number"
                            min="0"
                            step="0.01">

                    </div>

                    <div class="campo">

                        <label>
                            Superficie (ha)
                        </label>

                        <input
                            id="editSuperficie"
                            type="number"
                            min="0"
                            step="0.000001">

                    </div>

                </div>

                <div
                    id="errorEditarConvenio"
                    class="mensaje-error"
                    hidden>
                </div>

                <div class="acciones-formulario">

                    <button
                        type="button"
                        class="btn-secundario"
                        id="cancelarEditarConvenio">

                        Cancelar

                    </button>

                    <button
                        type="submit"
                        class="btn-principal">

                        Guardar cambios

                    </button>

                </div>

            </form>
        `;

        elementos.main
            .querySelector(
                ".pagina-header"
            )
            .insertAdjacentElement(
                "afterend",
                panel
            );

        return panel;
    }

    function abrirEdicion() {
        const panel =
            crearPanelEdicion();

        panel.querySelector(
            "#editFechaProgramada"
        ).value =
            convenio.fecha_programada_firma ||
            "";

        panel.querySelector(
            "#editFechaFirma"
        ).value =
            convenio.fecha_firma ||
            "";

        panel.querySelector(
            "#editMonto90"
        ).value =
            convenio.monto_90 ??
            "";

        panel.querySelector(
            "#editMonto100"
        ).value =
            convenio.monto_100 ??
            "";

        panel.querySelector(
            "#editMontoBdt"
        ).value =
            convenio.monto_bdt ??
            "";

        panel.querySelector(
            "#editSuperficie"
        ).value =
            convenio.superficie_ha ??
            "";

        panel.hidden =
            false;

        panel.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

        panel.querySelector(
            "#cancelarEditarConvenio"
        ).onclick =
            () => {
                panel.hidden =
                    true;
            };

        panel.querySelector(
            "#formEditarConvenio"
        ).onsubmit =
            guardarEdicion;
    }

    async function guardarEdicion(event) {
        event.preventDefault();

        const panel =
            document.getElementById(
                "panelEdicionConvenio"
            );

        const valorNumero =
            id => {
                const valor =
                    panel.querySelector(
                        id
                    ).value;

                return valor === ""
                    ? null
                    : Number(valor);
            };

        const payload = {
            fecha_programada_firma:
                panel.querySelector(
                    "#editFechaProgramada"
                ).value ||
                null,

            fecha_firma:
                panel.querySelector(
                    "#editFechaFirma"
                ).value ||
                null,

            monto_90:
                valorNumero(
                    "#editMonto90"
                ),

            monto_100:
                valorNumero(
                    "#editMonto100"
                ),

            monto_bdt:
                valorNumero(
                    "#editMontoBdt"
                ),

            superficie_ha:
                valorNumero(
                    "#editSuperficie"
                )
        };

        if (
            payload.monto_90 != null &&
            payload.monto_100 != null &&
            payload.monto_90 >
            payload.monto_100
        ) {
            alert(
                "El monto 90% no puede exceder el monto 100%."
            );

            return;
        }

        const submit =
            event.currentTarget.querySelector(
                '[type="submit"]'
            );

        submit.disabled =
            true;

        try {
            convenio =
                await window.ConveniosAPI
                    .actualizar(
                        idConvenio,
                        payload
                    );

            renderInformacionGeneral();

            panel.hidden =
                true;

        } catch (error) {
            window.ClienteAPI
                .mostrarErrorAPI(
                    error,
                    panel.querySelector(
                        "#errorEditarConvenio"
                    )
                );

        } finally {
            submit.disabled =
                false;
        }
    }

    async function agregarAfectacion() {
        if (!puedeCapturar) {
            return;
        }

        const todas =
            await window.AfectacionesAPI
                .listarPorProyectoNucleo(
                    convenio.id_proyecto_nucleo
                );

        const actuales =
            new Set(
                afectacionesConvenio.map(
                    item =>
                        Number(
                            item.id_afectacion
                        )
                )
            );

        const candidatas =
            (
                Array.isArray(todas)
                    ? todas
                    : []
            ).filter(
                item =>
                    item.tipo_afectacion ===
                        convenio.ambito &&
                    !actuales.has(
                        Number(
                            item.id_afectacion
                        )
                    )
            );

        if (!candidatas.length) {
            alert(
                "No hay otras afectaciones compatibles disponibles para este convenio."
            );

            return;
        }

        let panel =
            document.getElementById(
                "panelAgregarAfectacionConvenio"
            );

        panel?.remove();

        panel =
            document.createElement(
                "section"
            );

        panel.id =
            "panelAgregarAfectacionConvenio";

        panel.className =
            "bloque";

        panel.innerHTML = `
            <div class="bloque-titulo">
                <h2>
                    Agregar afectación
                </h2>
            </div>

            <form id="formAgregarAfectacionConvenio">

                <div class="form-grid">

                    <div class="campo">

                        <label>
                            Afectación *
                        </label>

                        <select
                            id="nuevaAfectacionConvenio"
                            required>

                            <option value="">
                                Seleccionar
                            </option>

                            ${candidatas
                                .map(
                                    item => `
                                        <option value="${item.id_afectacion}">
                                            AF-${String(
                                                item.id_afectacion
                                            ).padStart(
                                                3,
                                                "0"
                                            )}
                                        </option>
                                    `
                                )
                                .join("")}

                        </select>

                    </div>

                    <div class="campo">

                        <label>
                            Efecto sobre superficie *
                        </label>

                        <select
                            id="efectoSuperficieConvenio"
                            required>

                            <option value="pendiente">
                                Pendiente
                            </option>

                            <option value="sin_cambio">
                                Sin cambio
                            </option>

                            <option value="adicion">
                                Adición
                            </option>

                            <option value="sustitucion">
                                Sustitución
                            </option>

                            <option value="correccion">
                                Corrección
                            </option>

                        </select>

                    </div>

                    <div class="campo">

                        <label>
                            Impacto de superficie (ha)
                        </label>

                        <input
                            id="impactoSuperficieConvenio"
                            type="number"
                            step="0.000001">

                    </div>

                </div>

                <div class="acciones-formulario">

                    <button
                        type="button"
                        class="btn-secundario"
                        id="cancelarAgregarAfectacion">

                        Cancelar

                    </button>

                    <button
                        type="submit"
                        class="btn-principal">

                        Agregar

                    </button>

                </div>

            </form>
        `;

        elementos.afectacionesTabla
            .closest("section")
            .appendChild(
                panel
            );

        panel.querySelector(
            "#cancelarAgregarAfectacion"
        ).onclick =
            () => panel.remove();

        panel.querySelector(
            "#formAgregarAfectacionConvenio"
        ).onsubmit =
            async event => {
                event.preventDefault();

                const efecto =
                    panel.querySelector(
                        "#efectoSuperficieConvenio"
                    ).value;

                const impactoTexto =
                    panel.querySelector(
                        "#impactoSuperficieConvenio"
                    ).value;

                let impacto =
                    impactoTexto === ""
                        ? null
                        : Number(
                            impactoTexto
                        );

                if (
                    efecto === "pendiente"
                ) {
                    impacto =
                        null;
                }

                if (
                    efecto === "sin_cambio"
                ) {
                    impacto =
                        0;
                }

                if (
                    efecto === "adicion" &&
                    (
                        impacto == null ||
                        impacto <= 0
                    )
                ) {
                    alert(
                        "Una adición requiere un impacto mayor a cero."
                    );

                    return;
                }

                if (
                    [
                        "sustitucion",
                        "correccion"
                    ].includes(
                        efecto
                    ) &&
                    impacto == null
                ) {
                    alert(
                        "Ese efecto requiere una superficie de impacto."
                    );

                    return;
                }

                await window.ConveniosAPI
                    .agregarAfectacionAdicional(
                        idConvenio,
                        {
                            id_afectacion:
                                Number(
                                    panel.querySelector(
                                        "#nuevaAfectacionConvenio"
                                    ).value
                                ),

                            efecto_superficie:
                                efecto,

                            superficie_impacto_ha:
                                impacto
                        }
                    );

                panel.remove();

                await recargar();
            };
    }

    async function obtenerCandidatosCompareciente() {
        const mapa =
            new Map();

        for (
            const relacion of
            afectacionesConvenio
        ) {
            let afectacion =
                detallesAfectaciones.get(
                    Number(
                        relacion.id_afectacion
                    )
                );

            if (!afectacion) {
                continue;
            }

            const relacionesUnidades =
                Array.isArray(
                    afectacion.unidades_agrarias
                )
                    ? afectacion.unidades_agrarias
                    : [];

            for (
                const relacionUnidad of
                relacionesUnidades
            ) {
                const unidad =
                    relacionUnidad.unidad_agraria;

                if (!unidad?.id_parcela) {
                    continue;
                }

                const titulares =
                    await window.ParcelasAPI
                        .listarTitulares(
                            unidad.id_parcela
                        )
                        .catch(
                            () => []
                        );

                (
                    Array.isArray(titulares)
                        ? titulares
                        : []
                ).forEach(
                    titular => {
                        const clave =
                            `${titular.id_persona}:${titular.id_parcela_titular}`;

                        mapa.set(
                            clave,
                            {
                                id_persona:
                                    titular.id_persona,

                                id_parcela_titular:
                                    titular.id_parcela_titular,

                                nombre:
                                    [
                                        titular.nombre,
                                        titular.apellido_paterno,
                                        titular.apellido_materno
                                    ]
                                        .filter(Boolean)
                                        .join(" ") ||
                                    `Persona #${titular.id_persona}`
                            }
                        );
                    }
                );
            }
        }

        return [
            ...mapa.values()
        ];
    }

    async function agregarCompareciente() {
        if (!puedeCapturar) {
            return;
        }

        if (
            convenio.ambito ===
            "colectivo"
        ) {
            alert(
                "Los comparecientes individuales no aplican al ámbito colectivo en este flujo."
            );

            return;
        }

        const candidatos =
            await obtenerCandidatosCompareciente();

        if (!candidatos.length) {
            alert(
                "No hay titulares de parcelas elegibles para agregar como comparecientes."
            );

            return;
        }

        let panel =
            document.getElementById(
                "panelAgregarCompareciente"
            );

        panel?.remove();

        panel =
            document.createElement(
                "section"
            );

        panel.id =
            "panelAgregarCompareciente";

        panel.className =
            "bloque";

        panel.innerHTML = `
            <div class="bloque-titulo">
                <h2>
                    Agregar compareciente
                </h2>
            </div>

            <form id="formAgregarCompareciente">

                <div class="form-grid">

                    <div class="campo">

                        <label>
                            Persona *
                        </label>

                        <select
                            id="personaCompareciente"
                            required>

                            <option value="">
                                Seleccionar
                            </option>

                            ${candidatos
                                .map(
                                    item => `
                                        <option
                                            value="${item.id_persona}"
                                            data-parcela-titular="${item.id_parcela_titular}"
                                            data-nombre="${escaparHTML(
                                                item.nombre
                                            )}">

                                            ${escaparHTML(
                                                item.nombre
                                            )}

                                        </option>
                                    `
                                )
                                .join("")}

                        </select>

                    </div>

                    <div class="campo">

                        <label>
                            Calidad *
                        </label>

                        <select
                            id="calidadCompareciente"
                            required>

                            <option value="">
                                Seleccionar
                            </option>

                            ${[
                                ...nombresCalidad.entries()
                            ]
                                .map(
                                    ([id, nombre]) => `
                                        <option value="${id}">
                                            ${escaparHTML(nombre)}
                                        </option>
                                    `
                                )
                                .join("")}

                        </select>

                    </div>

                    <div class="campo">

                        <label>
                            Tipo de acreditación
                        </label>

                        <select
                            id="acreditacionCompareciente">

                            <option value="">
                                Sin acreditación adicional
                            </option>

                            ${[
                                ...nombresAcreditacion.entries()
                            ]
                                .map(
                                    ([id, nombre]) => `
                                        <option value="${id}">
                                            ${escaparHTML(nombre)}
                                        </option>
                                    `
                                )
                                .join("")}

                        </select>

                    </div>

                    <div class="campo campo-completo">

                        <label>
                            Nombre en instrumento *
                        </label>

                        <input
                            id="nombreCompareciente"
                            type="text"
                            maxlength="300"
                            required>

                    </div>

                    <div class="campo-checkbox">

                        <label>
                            <input
                                id="firmanteCompareciente"
                                type="checkbox"
                                checked>

                            <span>
                                Es firmante
                            </span>
                        </label>

                    </div>

                    <div class="campo-checkbox">

                        <label>
                            <input
                                id="beneficiarioCompareciente"
                                type="checkbox">

                            <span>
                                Es beneficiario
                            </span>
                        </label>

                    </div>

                </div>

                <div class="acciones-formulario">

                    <button
                        type="button"
                        class="btn-secundario"
                        id="cancelarAgregarCompareciente">

                        Cancelar

                    </button>

                    <button
                        type="submit"
                        class="btn-principal">

                        Agregar

                    </button>

                </div>

            </form>
        `;

        elementos.comparecientesTabla
            .closest("section")
            .appendChild(
                panel
            );

        const selectPersona =
            panel.querySelector(
                "#personaCompareciente"
            );

        selectPersona.onchange =
            () => {
                const option =
                    selectPersona.options[
                        selectPersona.selectedIndex
                    ];

                panel.querySelector(
                    "#nombreCompareciente"
                ).value =
                    option?.dataset?.nombre ||
                    "";
            };

        panel.querySelector(
            "#cancelarAgregarCompareciente"
        ).onclick =
            () => panel.remove();

        panel.querySelector(
            "#formAgregarCompareciente"
        ).onsubmit =
            async event => {
                event.preventDefault();

                const option =
                    selectPersona.options[
                        selectPersona.selectedIndex
                    ];

                await window.ConveniosAPI
                    .agregarCompareciente(
                        idConvenio,
                        {
                            id_persona:
                                Number(
                                    selectPersona.value
                                ),

                            id_parcela_titular:
                                option?.dataset?.parcelaTitular
                                    ? Number(
                                        option.dataset.parcelaTitular
                                    )
                                    : null,

                            id_tipo_calidad:
                                Number(
                                    panel.querySelector(
                                        "#calidadCompareciente"
                                    ).value
                                ),

                            id_tipo_acreditacion:
                                panel.querySelector(
                                    "#acreditacionCompareciente"
                                ).value
                                    ? Number(
                                        panel.querySelector(
                                            "#acreditacionCompareciente"
                                        ).value
                                    )
                                    : null,

                            referencia_acreditacion:
                                null,

                            fecha_acreditacion:
                                null,

                            nombre_en_instrumento:
                                panel.querySelector(
                                    "#nombreCompareciente"
                                ).value.trim(),

                            es_firmante:
                                panel.querySelector(
                                    "#firmanteCompareciente"
                                ).checked,

                            es_beneficiario_pago:
                                panel.querySelector(
                                    "#beneficiarioCompareciente"
                                ).checked,

                            requiere_revision:
                                false,

                            motivo_revision:
                                null
                        }
                    );

                panel.remove();

                await recargar();
            };
    }

    async function eliminarCompareciente(
        idCompareciente
    ) {
        const motivo =
            window.prompt(
                "Motivo de baja del compareciente:"
            );

        if (
            motivo === null
        ) {
            return;
        }

        if (!motivo.trim()) {
            alert(
                "El motivo es obligatorio."
            );

            return;
        }

        await window.ConveniosAPI
            .eliminarCompareciente(
                idCompareciente,
                motivo.trim()
            );

        await recargar();
    }

    async function recargar() {
        await cargarDatos();

        renderInformacionGeneral();
        renderAfectaciones();
        renderComparecientes();
        renderTramitesRan();
        await renderConvenioPadre();
    }

    elementos.btnVolver
        ?.addEventListener(
            "click",
            () => {
                const principal =
                    afectacionesConvenio.find(
                        item =>
                            item.rol ===
                            "principal"
                    );

                if (principal) {
                    window.location.href =
                        `/pages/detalleAfectacion.html?id=${encodeURIComponent(
                            principal.id_afectacion
                        )}`;

                } else {
                    window.history.back();
                }
            }
        );

    elementos.btnEditarConvenio
        ?.addEventListener(
            "click",
            abrirEdicion
        );

    elementos.btnAgregarAfectacion
        ?.addEventListener(
            "click",
            () => {
                agregarAfectacion()
                    .catch(
                        error =>
                            window.ClienteAPI
                                .mostrarErrorAPI(
                                    error
                                )
                    );
            }
        );

    elementos.btnAgregarCompareciente
        ?.addEventListener(
            "click",
            () => {
                agregarCompareciente()
                    .catch(
                        error =>
                            window.ClienteAPI
                                .mostrarErrorAPI(
                                    error
                                )
                    );
            }
        );

    elementos.btnNuevoTramiteRan
        ?.addEventListener(
            "click",
            () => {
                window.location.href =
                    `/pages/tramiteRan.html?id_proyecto_nucleo=${encodeURIComponent(
                        convenio.id_proyecto_nucleo
                    )}&id_convenio=${encodeURIComponent(
                        idConvenio
                    )}`;
            }
        );

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
                    `/pages/detalleAfectacion.html?id=${encodeURIComponent(
                        boton.dataset.verAfectacion
                    )}`;
            }
        );

    elementos.comparecientesTabla
        ?.addEventListener(
            "click",
            event => {
                const boton =
                    event.target.closest(
                        "[data-eliminar-compareciente]"
                    );

                if (!boton) {
                    return;
                }

                eliminarCompareciente(
                    Number(
                        boton.dataset
                            .eliminarCompareciente
                    )
                ).catch(
                    error =>
                        window.ClienteAPI
                            .mostrarErrorAPI(
                                error
                            )
                );
            }
        );

    try {
        await cargarRol();
        await cargarCatalogos();
        await recargar();

    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(
            error
        );
    }
});