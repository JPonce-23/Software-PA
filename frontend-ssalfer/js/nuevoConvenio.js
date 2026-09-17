document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idAfectacion =
        Number(
            parametros.get("id_afectacion") ||
            parametros.get("id")
        );

    const elementos = {
        enlaceDetalle:
            document.getElementById(
                "enlaceDetalle"
            ),

        identificadorAfectacion:
            document.getElementById(
                "identificadorAfectacion"
            ),

        btnVolver:
            document.getElementById(
                "btnVolver"
            ),

        btnCancelar:
            document.getElementById(
                "btnCancelar"
            ),

        form:
            document.getElementById(
                "formConvenio"
            ),

        tipoInstrumento:
            document.getElementById(
                "tipoInstrumento"
            ),

        campoTipoConvenio:
            document.getElementById(
                "campoTipoConvenio"
            ),

        tipoConvenio:
            document.getElementById(
                "tipoConvenio"
            ),

        modalidadEspecial:
            document.getElementById(
                "modalidadEspecial"
            ),

        campoDescripcionModalidad:
            document.getElementById(
                "campoDescripcionModalidad"
            ),

        descripcionModalidad:
            document.getElementById(
                "descripcionModalidad"
            ),

        campoDescripcionInstrumento:
            document.getElementById(
                "campoDescripcionInstrumento"
            ),

        descripcionInstrumento:
            document.getElementById(
                "descripcionInstrumento"
            ),

        consecutivo:
            document.getElementById(
                "consecutivo"
            ),

        idConvenioPadre:
            document.getElementById(
                "idConvenioPadre"
            ),

        campoAsamblea:
            document.getElementById(
                "campoAsamblea"
            ),

        idAsambleaAutorizacion:
            document.getElementById(
                "idAsambleaAutorizacion"
            ),

        fechaProgramadaFirma:
            document.getElementById(
                "fechaProgramadaFirma"
            ),

        fechaFirma:
            document.getElementById(
                "fechaFirma"
            ),

        monto90:
            document.getElementById(
                "monto90"
            ),

        monto100:
            document.getElementById(
                "monto100"
            ),

        montoBdt:
            document.getElementById(
                "montoBdt"
            ),

        superficieHa:
            document.getElementById(
                "superficieHa"
            ),

        errorMontos:
            document.getElementById(
                "errorMontos"
            ),

        btnAgregarCompareciente:
            document.getElementById(
                "btnAgregarCompareciente"
            ),

        comparecientesContainer:
            document.getElementById(
                "comparecientesContainer"
            ),

        sinComparecientes:
            document.getElementById(
                "sinComparecientes"
            )
    };

    if (
        !Number.isInteger(idAfectacion) ||
        idAfectacion <= 0
    ) {
        window.ClienteAPI.mostrarErrorAPI(
            new Error(
                "No se puede crear el convenio porque falta un id_afectacion válido."
            )
        );

        return;
    }

    let afectacion = null;
    let contextoPN = null;
    let puedeCapturar = false;

    let candidatosCompareciente = [];
    let opcionesCalidad = [];
    let opcionesAcreditacion = [];

    let indiceCompareciente = 0;

    const tiposIndividuales = [
        [
            "cop_original",
            "COP original"
        ],
        [
            "modificatorio",
            "Modificatorio"
        ],
        [
            "ampliacion",
            "Ampliación"
        ],
        [
            "ampliacion_remanente",
            "Ampliación de remanente"
        ]
    ];

    const tiposColectivos = [
        [
            "cop_original",
            "COP original"
        ],
        [
            "modificatorio",
            "Modificatorio"
        ],
        [
            "superficie_adicional",
            "Superficie adicional"
        ],
        [
            "obras_complementarias",
            "Obras complementarias"
        ]
    ];

    /* =====================================================
                        UTILIDADES
    ====================================================== */

    function escaparHTML(valor) {
        return String(valor ?? "")
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

    function esColectiva() {
        return (
            afectacion?.tipo_afectacion ===
            "colectivo"
        );
    }

    function numeroOpcional(
        elemento
    ) {
        if (!elemento?.value) {
            return null;
        }

        const valor =
            Number(
                elemento.value
            );

        return Number.isFinite(valor)
            ? valor
            : null;
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

        if (!puedeCapturar) {
            elementos.form
                .querySelectorAll(
                    "input, select, textarea, button"
                )
                .forEach(
                    control => {
                        control.disabled =
                            true;
                    }
                );

            elementos.btnVolver.disabled =
                false;

            elementos.btnCancelar.disabled =
                false;
        }
    }

    /* =====================================================
                         CONTEXTO
    ====================================================== */

    async function cargarContexto() {
        afectacion =
            await window.AfectacionesAPI
                .obtener(
                    idAfectacion
                );

        contextoPN =
            await window.NucleosAPI
                .obtenerProyectoNucleo(
                    afectacion
                        .id_proyecto_nucleo
                );

        elementos
            .identificadorAfectacion
            .textContent =
            `AF-${String(
                idAfectacion
            ).padStart(
                3,
                "0"
            )}`;

        elementos.enlaceDetalle.href =
            `/pages/detalleAfectacion.html?id=${encodeURIComponent(
                idAfectacion
            )}`;

        document.title =
            `Nuevo convenio | AF-${idAfectacion} | SSALFER`;
    }

    /* =====================================================
                       TIPO DE CONVENIO
    ====================================================== */

    function cargarTiposConvenio() {
        elementos.tipoConvenio.innerHTML =
            '<option value="">Seleccionar tipo</option>';

        const opciones =
            esColectiva()
                ? tiposColectivos
                : tiposIndividuales;

        opciones.forEach(
            (
                [
                    value,
                    text
                ]
            ) => {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    value;

                option.textContent =
                    text;

                elementos
                    .tipoConvenio
                    .appendChild(
                        option
                    );
            }
        );
    }

    function actualizarInstrumento() {
        const esConvenio =
            elementos
                .tipoInstrumento
                .value ===
            "convenio";

        elementos
            .campoTipoConvenio
            .hidden =
            !esConvenio;

        elementos
            .tipoConvenio
            .required =
            esConvenio;

        elementos
            .campoDescripcionInstrumento
            .hidden =
            esConvenio;

        elementos
            .descripcionInstrumento
            .required =
            !esConvenio;

        if (esConvenio) {
            elementos
                .descripcionInstrumento
                .value =
                "";

        } else {
            elementos
                .tipoConvenio
                .value =
                "";

            elementos
                .modalidadEspecial
                .value =
                "";
        }

        actualizarModalidad();
        actualizarReglasPadre();
    }

    function actualizarModalidad() {
        const otra =
            elementos
                .modalidadEspecial
                .value ===
            "otra";

        elementos
            .campoDescripcionModalidad
            .hidden =
            !otra;

        elementos
            .descripcionModalidad
            .required =
            otra;

        if (!otra) {
            elementos
                .descripcionModalidad
                .value =
                "";
        }
    }

    function actualizarAsamblea() {
        elementos.campoAsamblea.hidden =
            !esColectiva();

        if (!esColectiva()) {
            elementos
                .idAsambleaAutorizacion
                .value =
                "";
        }
    }

    function actualizarReglasPadre() {
        const tipo =
            elementos
                .tipoConvenio
                .value;

        const requierePadre =
            !esColectiva() &&
            [
                "modificatorio",
                "ampliacion",
                "ampliacion_remanente"
            ].includes(
                tipo
            );

        elementos
            .idConvenioPadre
            .required =
            requierePadre;

        if (
            tipo ===
            "cop_original"
        ) {
            elementos
                .idConvenioPadre
                .value =
                "";
        }
    }

    /* =====================================================
                          MONTOS
    ====================================================== */

    function validarMontos() {
        const m90 =
            numeroOpcional(
                elementos.monto90
            );

        const m100 =
            numeroOpcional(
                elementos.monto100
            );

        if (
            m90 != null &&
            m100 != null &&
            m90 > m100
        ) {
            elementos
                .errorMontos
                .hidden =
                false;

            elementos
                .errorMontos
                .textContent =
                "El monto 90% no puede exceder el monto 100%.";

            return false;
        }

        elementos
            .errorMontos
            .hidden =
            true;

        elementos
            .errorMontos
            .textContent =
            "";

        return true;
    }

    /* =====================================================
                         ASAMBLEAS
    ====================================================== */

    async function cargarAsambleas() {
        elementos
            .idAsambleaAutorizacion
            .innerHTML =
            '<option value="">Sin asamblea asociada</option>';

        if (!esColectiva()) {
            return;
        }

        const asambleas =
            await window.AsambleasAPI
                .listarPorProyectoNucleo(
                    afectacion
                        .id_proyecto_nucleo
                );

        (
            Array.isArray(asambleas)
                ? asambleas
                : []
        ).forEach(
            asamblea => {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    String(
                        asamblea
                            .id_asamblea
                    );

                option.textContent =
                    `Asamblea #${asamblea.id_asamblea}${
                        asamblea.proposito
                            ? ` · ${asamblea.proposito}`
                            : ""
                    }`;

                elementos
                    .idAsambleaAutorizacion
                    .appendChild(
                        option
                    );
            }
        );
    }

    /* =====================================================
                     CONVENIOS PADRE
    ====================================================== */

    async function cargarConveniosPadre() {
        elementos
            .idConvenioPadre
            .innerHTML =
            '<option value="">Sin convenio padre</option>';

        const afectacionesPN =
            await window.AfectacionesAPI
                .listarPorProyectoNucleo(
                    afectacion
                        .id_proyecto_nucleo
                );

        const compatibles =
            (
                Array.isArray(
                    afectacionesPN
                )
                    ? afectacionesPN
                    : []
            ).filter(
                item =>
                    item.tipo_afectacion ===
                    afectacion.tipo_afectacion
            );

        const respuestas =
            await Promise.all(
                compatibles.map(
                    item =>
                        window.ConveniosAPI
                            .listarPorAfectacion(
                                item.id_afectacion
                            )
                            .catch(
                                () => []
                            )
                )
            );

        const mapa =
            new Map();

        respuestas
            .flat()
            .forEach(
                convenio => {
                    if (
                        convenio
                            ?.id_convenio
                    ) {
                        mapa.set(
                            Number(
                                convenio
                                    .id_convenio
                            ),
                            convenio
                        );
                    }
                }
            );

        [
            ...mapa.values()
        ]
            .sort(
                (
                    a,
                    b
                ) =>
                    Number(
                        a.id_convenio
                    ) -
                    Number(
                        b.id_convenio
                    )
            )
            .forEach(
                convenio => {
                    const option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        String(
                            convenio
                                .id_convenio
                        );

                    option.textContent =
                        `Convenio #${convenio.id_convenio}${
                            convenio.tipo_convenio
                                ? ` · ${convenio.tipo_convenio}`
                                : ""
                        }`;

                    elementos
                        .idConvenioPadre
                        .appendChild(
                            option
                        );
                }
            );
    }

    /* =====================================================
                 CATÁLOGOS DE COMPARECIENTES
    ====================================================== */

    async function cargarCatalogosCompareciente() {
        const [
            calidad,
            acreditacion
        ] =
            await Promise.all([
                window.CatalogosAPI
                    .obtenerOperativo(
                        "calidad_compareciente_convenio"
                    ),

                window.CatalogosAPI
                    .obtenerOperativo(
                        "tipo_acreditacion_derecho_individual"
                    )
            ]);

        opcionesCalidad =
            Array.isArray(
                calidad
            )
                ? calidad
                : [];

        opcionesAcreditacion =
            Array.isArray(
                acreditacion
            )
                ? acreditacion
                : [];
    }

    /* =====================================================
                     CANDIDATOS A FIRMANTE
    ====================================================== */

    async function cargarCandidatosCompareciente() {
        candidatosCompareciente =
            [];

        if (esColectiva()) {
            return;
        }

        const relaciones =
            Array.isArray(
                afectacion
                    .unidades_agrarias
            )
                ? afectacion
                    .unidades_agrarias
                : [];

        const idsParcela =
            new Set();

        for (
            const relacion of
            relaciones
        ) {
            let unidad =
                relacion
                    .unidad_agraria ||
                null;

            if (
                !unidad &&
                relacion
                    .id_unidad_agraria
            ) {
                try {
                    unidad =
                        await window.UnidadesAgrariasAPI
                            .obtener(
                                relacion
                                    .id_unidad_agraria
                            );

                } catch {
                    unidad =
                        null;
                }
            }

            if (
                unidad
                    ?.id_parcela
            ) {
                idsParcela.add(
                    Number(
                        unidad
                            .id_parcela
                    )
                );
            }
        }

        const titularesPorParcela =
            await Promise.all(
                [
                    ...idsParcela
                ].map(
                    idParcela =>
                        window.ParcelasAPI
                            .listarTitulares(
                                idParcela
                            )
                            .catch(
                                () => []
                            )
                )
            );

        const mapa =
            new Map();

        titularesPorParcela
            .flat()
            .forEach(
                titular => {
                    if (
                        !titular
                            ?.id_persona ||
                        !titular
                            ?.id_parcela_titular
                    ) {
                        return;
                    }

                    const key =
                        `${titular.id_persona}:${titular.id_parcela_titular}`;

                    mapa.set(
                        key,
                        {
                            id_persona:
                                Number(
                                    titular
                                        .id_persona
                                ),

                            id_parcela_titular:
                                Number(
                                    titular
                                        .id_parcela_titular
                                ),

                            nombre:
                                [
                                    titular.nombre,
                                    titular.apellido_paterno,
                                    titular.apellido_materno
                                ]
                                    .filter(
                                        Boolean
                                    )
                                    .join(
                                        " "
                                    ) ||
                                `Persona #${titular.id_persona}`
                        }
                    );
                }
            );

        candidatosCompareciente =
            [
                ...mapa.values()
            ];
    }

    function opcionesPersonasHTML() {
        return candidatosCompareciente
            .map(
                item => `
                    <option
                        value="${item.id_persona}"
                        data-id-parcela-titular="${item.id_parcela_titular}">

                        ${escaparHTML(
                            item.nombre
                        )}
                        · Titular #${item.id_parcela_titular}

                    </option>
                `
            )
            .join("");
    }

    function opcionesCatalogoHTML(
        opciones
    ) {
        return opciones
            .map(
                item => `
                    <option
                        value="${item.id_catalogo_opcion}"
                        data-codigo="${escaparHTML(
                            item.codigo ||
                            ""
                        )}">

                        ${escaparHTML(
                            item.nombre ||
                            item.codigo ||
                            item.id_catalogo_opcion
                        )}

                    </option>
                `
            )
            .join("");
    }

    /* =====================================================
                       COMPARECIENTES
    ====================================================== */

    function actualizarEstadoComparecientes() {
        const bloques =
            [
                ...elementos
                    .comparecientesContainer
                    .querySelectorAll(
                        "[data-compareciente]"
                    )
            ];

        bloques.forEach(
            (
                bloque,
                posicion
            ) => {
                const numero =
                    bloque.querySelector(
                        ".numero-compareciente"
                    );

                const titulo =
                    bloque.querySelector(
                        "h3"
                    );

                if (numero) {
                    numero.textContent =
                        String(
                            posicion + 1
                        );
                }

                if (titulo) {
                    titulo.textContent =
                        `Compareciente ${posicion + 1}`;
                }
            }
        );

        elementos
            .sinComparecientes
            .hidden =
            bloques.length > 0;

        elementos
            .sinComparecientes
            .style
            .display =
            bloques.length > 0
                ? "none"
                : "";
    }

    function crearCompareciente() {
        if (esColectiva()) {
            return;
        }

        if (
            !candidatosCompareciente
                .length
        ) {
            alert(
                "No hay titulares elegibles en las unidades agrarias vinculadas a esta afectación. " +
                "Registra primero la parcela/titularidad correspondiente."
            );

            return;
        }

        const indice =
            indiceCompareciente++;

        const bloque =
            document.createElement(
                "div"
            );

        bloque.className =
            "compareciente";

        bloque.dataset.compareciente =
            "";

        bloque.innerHTML = `
            <div class="compareciente-titulo">

                <div>

                    <span class="numero-compareciente">
                        1
                    </span>

                    <h3>
                        Compareciente 1
                    </h3>

                </div>

                <button
                    type="button"
                    class="btn-eliminar-compareciente"
                    title="Eliminar compareciente">

                    <i class="bi bi-trash"></i>

                </button>

            </div>

            <div class="form-grid">

                <div class="campo campo-completo">

                    <label>
                        Persona
                        <span class="obligatorio">
                            *
                        </span>
                    </label>

                    <select
                        name="comparecientes[${indice}][id_persona]"
                        required>

                        <option value="">
                            Seleccionar persona
                        </option>

                        ${opcionesPersonasHTML()}

                    </select>

                    <small>
                        Se muestran titulares de parcelas vinculadas
                        a las unidades afectadas.
                    </small>

                </div>

                <div class="campo">

                    <label>
                        Calidad del compareciente
                        <span class="obligatorio">
                            *
                        </span>
                    </label>

                    <select
                        name="comparecientes[${indice}][id_tipo_calidad]"
                        required>

                        <option value="">
                            Seleccionar calidad
                        </option>

                        ${opcionesCatalogoHTML(
                            opcionesCalidad
                        )}

                    </select>

                </div>

                <div class="campo">

                    <label>
                        Tipo de acreditación
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <select
                        name="comparecientes[${indice}][id_tipo_acreditacion]">

                        <option value="">
                            Seleccionar tipo
                        </option>

                        ${opcionesCatalogoHTML(
                            opcionesAcreditacion
                        )}

                    </select>

                </div>

                <div class="campo">

                    <label>
                        Referencia de acreditación
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <input
                        type="text"
                        name="comparecientes[${indice}][referencia_acreditacion]"
                        maxlength="200">

                </div>

                <div class="campo">

                    <label>
                        Fecha de acreditación
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <input
                        type="date"
                        name="comparecientes[${indice}][fecha_acreditacion]">

                </div>

                <div class="campo campo-completo">

                    <label>
                        Nombre en el instrumento
                        <span class="obligatorio">
                            *
                        </span>
                    </label>

                    <input
                        type="text"
                        name="comparecientes[${indice}][nombre_en_instrumento]"
                        maxlength="300"
                        required>

                </div>

                <div class="campo-checkbox">

                    <label>

                        <input
                            type="checkbox"
                            name="comparecientes[${indice}][es_firmante]"
                            checked>

                        <span>
                            Es firmante
                        </span>

                    </label>

                </div>

                <div class="campo-checkbox">

                    <label>

                        <input
                            type="checkbox"
                            name="comparecientes[${indice}][es_beneficiario_pago]">

                        <span>
                            Es beneficiario de pago
                        </span>

                    </label>

                </div>

                <div class="campo-checkbox campo-completo">

                    <label>

                        <input
                            type="checkbox"
                            class="checkRevision"
                            name="comparecientes[${indice}][requiere_revision]">

                        <span>
                            Requiere revisión
                        </span>

                    </label>

                </div>

                <div
                    class="campo campo-completo campo-motivo-revision"
                    hidden>

                    <label>
                        Motivo de revisión
                        <span class="obligatorio">
                            *
                        </span>
                    </label>

                    <textarea
                        name="comparecientes[${indice}][motivo_revision]"
                        rows="3"></textarea>

                </div>

            </div>
        `;

        elementos
            .comparecientesContainer
            .appendChild(
                bloque
            );

        actualizarEstadoComparecientes();
    }

    function actualizarSeccionComparecientes() {
        const seccion =
            elementos
                .comparecientesContainer
                .closest(
                    "section"
                );

        if (seccion) {
            seccion.hidden =
                esColectiva();
        }

        elementos
            .btnAgregarCompareciente
            .hidden =
            esColectiva() ||
            !puedeCapturar;

        if (esColectiva()) {
            elementos
                .comparecientesContainer
                .innerHTML =
                "";

            actualizarEstadoComparecientes();
        }
    }

    function construirComparecientes() {
        if (esColectiva()) {
            return [];
        }

        return [
            ...elementos
                .comparecientesContainer
                .querySelectorAll(
                    "[data-compareciente]"
                )
        ].map(
            bloque => {
                const persona =
                    bloque.querySelector(
                        '[name*="[id_persona]"]'
                    );

                const optionPersona =
                    persona.options[
                        persona.selectedIndex
                    ];

                const idParcelaTitular =
                    optionPersona
                        ?.dataset
                        ?.idParcelaTitular
                        ? Number(
                            optionPersona
                                .dataset
                                .idParcelaTitular
                        )
                        : null;

                const valor =
                    sufijo =>
                        bloque.querySelector(
                            `[name*="[${sufijo}]"]`
                        );

                const revision =
                    valor(
                        "requiere_revision"
                    ).checked;

                return {
                    id_persona:
                        Number(
                            persona.value
                        ),

                    id_parcela_titular:
                        idParcelaTitular,

                    id_tipo_calidad:
                        Number(
                            valor(
                                "id_tipo_calidad"
                            ).value
                        ),

                    id_tipo_acreditacion:
                        valor(
                            "id_tipo_acreditacion"
                        ).value
                            ? Number(
                                valor(
                                    "id_tipo_acreditacion"
                                ).value
                            )
                            : null,

                    referencia_acreditacion:
                        valor(
                            "referencia_acreditacion"
                        )
                            .value
                            .trim() ||
                        null,

                    fecha_acreditacion:
                        valor(
                            "fecha_acreditacion"
                        ).value ||
                        null,

                    nombre_en_instrumento:
                        valor(
                            "nombre_en_instrumento"
                        )
                            .value
                            .trim(),

                    es_firmante:
                        valor(
                            "es_firmante"
                        ).checked,

                    es_beneficiario_pago:
                        valor(
                            "es_beneficiario_pago"
                        ).checked,

                    requiere_revision:
                        revision,

                    motivo_revision:
                        revision
                            ? (
                                valor(
                                    "motivo_revision"
                                )
                                    .value
                                    .trim() ||
                                null
                            )
                            : null
                };
            }
        );
    }

    /* =====================================================
                          PAYLOAD
    ====================================================== */

    function construirPayload() {
        return {
            tipo_instrumento:
                elementos
                    .tipoInstrumento
                    .value,

            tipo_convenio:
                elementos
                    .tipoInstrumento
                    .value ===
                "convenio"
                    ? (
                        elementos
                            .tipoConvenio
                            .value ||
                        null
                    )
                    : null,

            modalidad_especial:
                elementos
                    .modalidadEspecial
                    .value ||
                null,

            descripcion_modalidad:
                elementos
                    .descripcionModalidad
                    .value
                    .trim() ||
                null,

            descripcion_instrumento:
                elementos
                    .descripcionInstrumento
                    .value
                    .trim() ||
                null,

            consecutivo:
                Number(
                    elementos
                        .consecutivo
                        .value ||
                    1
                ),

            id_convenio_padre:
                elementos
                    .idConvenioPadre
                    .value
                    ? Number(
                        elementos
                            .idConvenioPadre
                            .value
                    )
                    : null,

            id_asamblea_autorizacion:
                esColectiva() &&
                elementos
                    .idAsambleaAutorizacion
                    .value
                    ? Number(
                        elementos
                            .idAsambleaAutorizacion
                            .value
                    )
                    : null,

            fecha_programada_firma:
                elementos
                    .fechaProgramadaFirma
                    .value ||
                null,

            fecha_firma:
                elementos
                    .fechaFirma
                    .value ||
                null,

            monto_90:
                numeroOpcional(
                    elementos.monto90
                ),

            monto_100:
                numeroOpcional(
                    elementos.monto100
                ),

            monto_bdt:
                numeroOpcional(
                    elementos.montoBdt
                ),

            superficie_ha:
                numeroOpcional(
                    elementos.superficieHa
                ),

            comparecientes:
                construirComparecientes()
        };
    }

    function validarPayload(
        payload
    ) {
        if (
            payload
                .tipo_instrumento ===
                "convenio" &&
            !payload.tipo_convenio
        ) {
            return (
                "Selecciona el tipo de convenio."
            );
        }

        if (
            payload
                .tipo_instrumento ===
                "otro" &&
            !payload
                .descripcion_instrumento
        ) {
            return (
                "Un instrumento 'Otro' requiere descripción."
            );
        }

        if (
            payload
                .modalidad_especial ===
                "permuta" &&
            payload.tipo_convenio !==
                "cop_original"
        ) {
            return (
                "La modalidad Permuta solo es válida para COP original."
            );
        }

        if (
            payload
                .modalidad_especial ===
                "otra" &&
            !payload
                .descripcion_modalidad
        ) {
            return (
                "La modalidad 'Otra' requiere descripción."
            );
        }

        if (
            !esColectiva() &&
            [
                "modificatorio",
                "ampliacion",
                "ampliacion_remanente"
            ].includes(
                payload.tipo_convenio
            ) &&
            !payload.id_convenio_padre
        ) {
            return (
                `El convenio individual ${payload.tipo_convenio} requiere un convenio padre.`
            );
        }

        if (
            payload.tipo_convenio ===
                "cop_original" &&
            payload.id_convenio_padre
        ) {
            return (
                "Un COP original no puede tener convenio padre."
            );
        }

        if (!validarMontos()) {
            return (
                "Revisa los montos del convenio."
            );
        }

        if (
            payload.fecha_firma &&
            !esColectiva()
        ) {
            const firmantes =
                payload
                    .comparecientes
                    .filter(
                        item =>
                            item.es_firmante
                    );

            if (!firmantes.length) {
                return (
                    "Un convenio individual firmado requiere al menos un compareciente firmante."
                );
            }
        }

        for (
            const item of
            payload.comparecientes
        ) {
            if (
                !item.id_persona ||
                !item.id_tipo_calidad ||
                !item.nombre_en_instrumento
            ) {
                return (
                    "Completa persona, calidad y nombre en el instrumento para cada compareciente."
                );
            }

            if (
                item.es_firmante &&
                !item.id_parcela_titular &&
                !item.id_tipo_acreditacion
            ) {
                return (
                    "Cada firmante individual requiere una titularidad parcelaria o una acreditación alternativa."
                );
            }

            if (
                item.requiere_revision &&
                !item.motivo_revision
            ) {
                return (
                    "Indica el motivo de revisión de cada compareciente marcado para revisión."
                );
            }
        }

        return null;
    }

    /* =====================================================
                           EVENTOS
    ====================================================== */

    elementos
        .tipoInstrumento
        .addEventListener(
            "change",
            actualizarInstrumento
        );

    elementos
        .tipoConvenio
        .addEventListener(
            "change",
            () => {
                actualizarReglasPadre();

                if (
                    elementos
                        .modalidadEspecial
                        .value ===
                        "permuta" &&
                    elementos
                        .tipoConvenio
                        .value !==
                        "cop_original"
                ) {
                    elementos
                        .modalidadEspecial
                        .value =
                        "";

                    actualizarModalidad();
                }
            }
        );

    elementos
        .modalidadEspecial
        .addEventListener(
            "change",
            actualizarModalidad
        );

    elementos
        .monto90
        .addEventListener(
            "input",
            validarMontos
        );

    elementos
        .monto100
        .addEventListener(
            "input",
            validarMontos
        );

    elementos
        .btnAgregarCompareciente
        .addEventListener(
            "click",
            crearCompareciente
        );

    elementos
        .comparecientesContainer
        .addEventListener(
            "click",
            event => {
                const eliminar =
                    event.target.closest(
                        ".btn-eliminar-compareciente"
                    );

                if (!eliminar) {
                    return;
                }

                eliminar
                    .closest(
                        "[data-compareciente]"
                    )
                    ?.remove();

                actualizarEstadoComparecientes();
            }
        );

    elementos
        .comparecientesContainer
        .addEventListener(
            "change",
            event => {
                const bloque =
                    event.target.closest(
                        "[data-compareciente]"
                    );

                if (!bloque) {
                    return;
                }

                if (
                    event.target.matches(
                        '[name*="[id_persona]"]'
                    )
                ) {
                    const option =
                        event.target
                            .options[
                                event.target
                                    .selectedIndex
                            ];

                    const nombre =
                        option
                            ?.textContent
                            ?.split(
                                " · Titular #"
                            )[0]
                            ?.trim() ||
                        "";

                    const inputNombre =
                        bloque.querySelector(
                            '[name*="[nombre_en_instrumento]"]'
                        );

                    if (
                        inputNombre &&
                        !inputNombre
                            .value
                            .trim()
                    ) {
                        inputNombre.value =
                            nombre;
                    }
                }

                if (
                    event.target
                        .classList
                        .contains(
                            "checkRevision"
                        )
                ) {
                    const campo =
                        bloque.querySelector(
                            ".campo-motivo-revision"
                        );

                    const textarea =
                        campo.querySelector(
                            "textarea"
                        );

                    campo.hidden =
                        !event.target.checked;

                    textarea.required =
                        event.target.checked;

                    if (
                        !event.target.checked
                    ) {
                        textarea.value =
                            "";
                    }
                }
            }
        );

    elementos.form.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            if (!puedeCapturar) {
                return;
            }

            if (
                !elementos.form
                    .checkValidity()
            ) {
                elementos.form
                    .reportValidity();

                return;
            }

            const payload =
                construirPayload();

            const error =
                validarPayload(
                    payload
                );

            if (error) {
                alert(error);
                return;
            }

            const submit =
                elementos.form
                    .querySelector(
                        '[type="submit"]'
                    );

            submit.disabled =
                true;

            try {
                const creado =
                    await window.ConveniosAPI
                        .crearDesdeAfectacion(
                            idAfectacion,
                            payload
                        );

                alert(
                    "El convenio se guardó correctamente."
                );

                window.location.href =
                    `/pages/fichaConvenio.html?id_convenio=${encodeURIComponent(
                        creado.id_convenio
                    )}`;

            } catch (errorAPI) {
                window.ClienteAPI
                    .mostrarErrorAPI(
                        errorAPI
                    );

            } finally {
                submit.disabled =
                    false;
            }
        }
    );

    function volver() {
        window.location.href =
            `/pages/detalleAfectacion.html?id=${encodeURIComponent(
                idAfectacion
            )}`;
    }

    elementos
        .btnVolver
        .addEventListener(
            "click",
            volver
        );

    elementos
        .btnCancelar
        .addEventListener(
            "click",
            volver
        );

    /* =====================================================
                           INICIO
    ====================================================== */

    elementos
        .comparecientesContainer
        .innerHTML =
        "";

    elementos
        .sinComparecientes
        .hidden =
        false;

    elementos
        .errorMontos
        .hidden =
        true;

    try {
        await cargarRol();

        await cargarContexto();

        cargarTiposConvenio();

        actualizarInstrumento();

        actualizarModalidad();

        actualizarAsamblea();

        await Promise.all([
            cargarAsambleas(),
            cargarConveniosPadre(),
            cargarCatalogosCompareciente(),
            cargarCandidatosCompareciente()
        ]);

        actualizarSeccionComparecientes();

        actualizarReglasPadre();

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(
                error
            );
    }
});