document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idProyectoNucleo =
        Number(
            parametros.get(
                "id_proyecto_nucleo"
            )
        );

    const idAfectacion =
        parametros.get(
            "id_afectacion"
        );

    const idUnidadAgraria =
        parametros.get(
            "id_unidad_agraria"
        );

    const elementos = {
        enlaceNucleo: document.getElementById("enlaceNucleo"),
        btnNuevaUnidad: document.getElementById("btnNuevaUnidad"),
        contadorUnidades: document.getElementById("contadorUnidades"),
        unidadesContainer: document.getElementById("unidadesContainer"),
        sinUnidades: document.getElementById("sinUnidades"),
        formularioUnidad: document.getElementById("formularioUnidad"),
        btnCerrarFormulario: document.getElementById("btnCerrarFormulario"),
        formUnidad: document.getElementById("formUnidadAgraria"),
        btnCancelarUnidad: document.getElementById("btnCancelarUnidad"),
        idTipoTierra: document.getElementById("idTipoTierra"),
        idTipoTitularidad: document.getElementById("idTipoTitularidad"),
        idTipoGestion: document.getElementById("idTipoGestion"),
        idDestinoSuperficie: document.getElementById("idDestinoSuperficie"),
        idParcela: document.getElementById("idParcela"),
        requiereRevision: document.getElementById("requiereRevision"),
        contenedorMotivoRevision: document.getElementById("contenedorMotivoRevision"),
        motivoRevision: document.getElementById("motivoRevision"),
        seccionTitulares: document.getElementById("seccionTitulares"),
        btnAgregarTitular: document.getElementById("btnAgregarTitular"),
        titularesUnidadContainer: document.getElementById("titularesUnidadContainer"),
        seccionVinculacion: document.getElementById("seccionVinculacion"),
        formVinculacion: document.getElementById("formVinculacion"),
        btnCancelarVinculacion: document.getElementById("btnCancelarVinculacion")
    };

    if (
    !Number.isInteger(idProyectoNucleo) ||
        idProyectoNucleo <= 0
    ) {
        window.ClienteAPI.mostrarErrorAPI(
            new Error(
                "No se puede abrir Unidades Agrarias porque falta un id_proyecto_nucleo válido."
            )
        );

        return;
    }

    let puedeCapturar = false;
    let unidadSeleccionada = null;
    let vinculoActual = null;

    const etiquetasCatalogo = {
        tipo_tierra: new Map(),
        tipo_titularidad_unidad: new Map(),
        tipo_gestion: new Map(),
        destino_superficie: new Map()
    };

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function valorNumerico(formData, nombre) {
        const valor = formData.get(nombre);

        return valor === null || valor === ""
            ? null
            : Number(valor);
    }

    function etiqueta(tipo, id) {
        if (id == null) {
            return "—";
        }

        return etiquetasCatalogo[tipo]?.get(Number(id)) || `#${id}`;
    }

    function configurarNavegacion() {
        if (elementos.enlaceNucleo) {
            elementos.enlaceNucleo.href =
                `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                    idProyectoNucleo
                )}`;
        }
    }

    async function cargarRol() {
        try {
            const sesion =
                await window.AuthAPI.obtenerSesionActual();

            const rol =
                sesion?.user?.rol;

            puedeCapturar =
                rol === "admin" ||
                rol === "operador";

        } catch {
            puedeCapturar = false;
        }

        if (elementos.btnNuevaUnidad) {
            elementos.btnNuevaUnidad.hidden =
                !puedeCapturar;
        }

        if (elementos.btnAgregarTitular) {
            elementos.btnAgregarTitular.hidden =
                !puedeCapturar;
        }
    }

    async function cargarCatalogo(tipo, select) {
        const opciones =
            await window.CatalogosAPI.obtenerOperativo(tipo);

        const lista =
            Array.isArray(opciones)
                ? opciones
                : [];

        etiquetasCatalogo[tipo].clear();

        const placeholder =
            select
                ?.querySelector('option[value=""]')
                ?.cloneNode(true);

        if (select) {
            select.innerHTML = "";

            if (placeholder) {
                select.appendChild(placeholder);
            }
        }

        lista.forEach(opcion => {
            const id =
                Number(opcion.id_catalogo_opcion);

            const nombre =
                opcion.nombre ||
                opcion.codigo ||
                `Opción ${id}`;

            etiquetasCatalogo[tipo].set(
                id,
                nombre
            );

            if (select) {
                const option =
                    document.createElement("option");

                option.value =
                    String(id);

                option.textContent =
                    nombre;

                select.appendChild(option);
            }
        });
    }

    async function cargarParcelas() {
        if (!elementos.idParcela) {
            return;
        }

        const parcelas =
            await window.ParcelasAPI.listarPorProyectoNucleo(
                Number(idProyectoNucleo)
            );

        elementos.idParcela.innerHTML =
            '<option value="">Sin parcela relacionada</option>';

        (
            Array.isArray(parcelas)
                ? parcelas
                : []
        ).forEach(parcela => {
            const option =
                document.createElement("option");

            option.value =
                String(parcela.id_parcela);

            option.textContent =
                parcela.no_parcela ||
                `Parcela #${parcela.id_parcela}`;

            elementos.idParcela.appendChild(
                option
            );
        });
    }

    async function cargarCatalogosYParcelas() {
        await Promise.all([
            cargarCatalogo(
                "tipo_tierra",
                elementos.idTipoTierra
            ),

            cargarCatalogo(
                "tipo_titularidad_unidad",
                elementos.idTipoTitularidad
            ),

            cargarCatalogo(
                "tipo_gestion",
                elementos.idTipoGestion
            ),

            cargarCatalogo(
                "destino_superficie",
                elementos.idDestinoSuperficie
            ),

            cargarParcelas()
        ]);
    }

    function actualizarMotivoRevision() {
        const activo =
            Boolean(
                elementos.requiereRevision?.checked
            );

        if (elementos.contenedorMotivoRevision) {
            elementos.contenedorMotivoRevision.hidden =
                !activo;
        }

        if (
            !activo &&
            elementos.motivoRevision
        ) {
            elementos.motivoRevision.value =
                "";
        }
    }

    function mostrarFormularioUnidad() {
        if (!puedeCapturar) {
            return;
        }

        elementos.formularioUnidad.hidden =
            false;

        elementos.formularioUnidad.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

        elementos.idTipoTierra?.focus();
    }

    function ocultarFormularioUnidad() {
        elementos.formularioUnidad.hidden =
            true;

        elementos.formUnidad.reset();

        actualizarMotivoRevision();
    }

    function obtenerDatosUnidad() {
        const data =
            new FormData(
                elementos.formUnidad
            );

        return {
            id_tipo_tierra:
                valorNumerico(
                    data,
                    "id_tipo_tierra"
                ),

            id_tipo_gestion:
                valorNumerico(
                    data,
                    "id_tipo_gestion"
                ),

            id_destino_superficie:
                valorNumerico(
                    data,
                    "id_destino_superficie"
                ),

            id_tipo_titularidad:
                valorNumerico(
                    data,
                    "id_tipo_titularidad"
                ),

            id_parcela:
                valorNumerico(
                    data,
                    "id_parcela"
                ),

            referencia_alfanumerica:
                data
                    .get("referencia_alfanumerica")
                    ?.trim() ||
                null,

            detalle:
                data
                    .get("detalle")
                    ?.trim() ||
                null,

            fuente:
                data
                    .get("fuente")
                    ?.trim() ||
                null,

            requiere_revision:
                Boolean(
                    elementos.requiereRevision?.checked
                ),

            motivo_revision:
                elementos.requiereRevision?.checked
                    ? (
                        data
                            .get("motivo_revision")
                            ?.trim() ||
                        null
                    )
                    : null
        };
    }

    function validarUnidad(datos) {
        if (!datos.id_tipo_tierra) {
            return "Selecciona el tipo de tierra.";
        }

        if (!datos.id_tipo_titularidad) {
            return "Selecciona el tipo de titularidad.";
        }

        const tieneDatoIdentificador =
            Boolean(datos.id_tipo_gestion) ||
            Boolean(datos.id_destino_superficie) ||
            Boolean(datos.id_parcela) ||
            Boolean(
                datos.referencia_alfanumerica?.trim()
            ) ||
            Boolean(
                datos.detalle?.trim()
            );

        if (!tieneDatoIdentificador) {
            return (
                "Además del tipo de tierra y la titularidad, " +
                "debes capturar al menos uno de estos datos: " +
                "tipo de gestión, destino de superficie, parcela relacionada, " +
                "referencia o detalle."
            );
        }

        if (
            datos.referencia_alfanumerica?.length >
            150
        ) {
            return "La referencia no puede superar 150 caracteres.";
        }

        if (
            datos.fuente?.length >
            250
        ) {
            return "La fuente no puede superar 250 caracteres.";
        }

        if (
            datos.requiere_revision &&
            !datos.motivo_revision
        ) {
            return "Indica el motivo de revisión.";
        }

        return null;
    }

    function urlUnidad(id) {
        const url =
            new URL(
                "/pages/unidadAgraria.html",
                window.location.origin
            );

        url.searchParams.set(
            "id_proyecto_nucleo",
            idProyectoNucleo
        );

        url.searchParams.set(
            "id_unidad_agraria",
            id
        );

        if (idAfectacion) {
            url.searchParams.set(
                "id_afectacion",
                idAfectacion
            );
        }

        return `${url.pathname}${url.search}`;
    }

    function renderizarUnidad(unidad) {
        const article =
            document.createElement("article");

        article.className =
            "unidad";

        article.dataset.unidad =
            "";

        article.dataset.idUnidadAgraria =
            unidad.id_unidad_agraria;

        const referencia =
            unidad.referencia_alfanumerica ||
            unidad.referencia_normalizada ||
            `Unidad #${unidad.id_unidad_agraria}`;

        article.innerHTML = `
            <div class="unidad-icono">
                <i class="bi bi-house"></i>
            </div>

            <div class="unidad-datos">

                <h3>
                    ${escaparHTML(referencia)}
                </h3>

                <span>
                    Tipo de tierra:
                    ${escaparHTML(
                        etiqueta(
                            "tipo_tierra",
                            unidad.id_tipo_tierra
                        )
                    )}
                </span>

                <span>
                    Tipo de titularidad:
                    ${escaparHTML(
                        etiqueta(
                            "tipo_titularidad_unidad",
                            unidad.id_tipo_titularidad
                        )
                    )}
                </span>

                <span>
                    Revisión:
                    ${
                        unidad.requiere_revision
                            ? "Pendiente de revisión"
                            : "No requiere revisión"
                    }
                </span>

            </div>

            <div class="unidad-accion">

                <a
                    class="btn-secundario"
                    href="${escaparHTML(
                        urlUnidad(
                            unidad.id_unidad_agraria
                        )
                    )}">

                    <i class="bi bi-eye"></i>

                    ${
                        idAfectacion
                            ? "Seleccionar / vincular"
                            : "Consultar"
                    }

                </a>

            </div>
        `;

        elementos.unidadesContainer.appendChild(
            article
        );
    }

    function actualizarEstadoLista(cantidad) {
        elementos.contadorUnidades.textContent =
            cantidad === 1
                ? "1 unidad"
                : `${cantidad} unidades`;

        elementos.sinUnidades.hidden =
            cantidad > 0;

        elementos.sinUnidades.style.display =
            cantidad > 0
                ? "none"
                : "";
    }

    async function cargarUnidades() {
        const unidades =
            await window.UnidadesAgrariasAPI.listarPorProyectoNucleo(
                Number(idProyectoNucleo)
            );

        const lista =
            Array.isArray(unidades)
                ? unidades
                : [];

        elementos.unidadesContainer.innerHTML =
            "";

        lista.forEach(
            renderizarUnidad
        );

        actualizarEstadoLista(
            lista.length
        );

        return lista;
    }

    async function cargarUnidadSeleccionada() {
        if (!idUnidadAgraria) {
            elementos.seccionTitulares.hidden =
                true;

            elementos.seccionVinculacion.hidden =
                true;

            return;
        }

        unidadSeleccionada =
            await window.UnidadesAgrariasAPI.obtener(
                Number(idUnidadAgraria)
            );

        elementos.seccionTitulares.hidden =
            false;

        if (elementos.btnAgregarTitular) {
            elementos.btnAgregarTitular.hidden =
                !puedeCapturar;
        }

        await cargarTitularesUnidad();

        if (idAfectacion) {
            elementos.seccionVinculacion.hidden =
                false;

            await cargarVinculoActual();

            if (!puedeCapturar) {
                elementos.formVinculacion
                    .querySelectorAll(
                        "input, textarea, select, button"
                    )
                    .forEach(control => {
                        control.disabled =
                            true;
                    });
            }

        } else {
            elementos.seccionVinculacion.hidden =
                true;
        }
    }

    async function cargarTitularesUnidad() {
        if (!unidadSeleccionada) {
            return;
        }

        const titulares =
            await window.UnidadesAgrariasAPI.listarTitulares(
                unidadSeleccionada.id_unidad_agraria
            );

        const lista =
            Array.isArray(titulares)
                ? titulares
                : [];

        let nombresParcela =
            new Map();

        if (unidadSeleccionada.id_parcela) {
            try {
                const titularesParcela =
                    await window.ParcelasAPI.listarTitulares(
                        unidadSeleccionada.id_parcela
                    );

                (
                    Array.isArray(titularesParcela)
                        ? titularesParcela
                        : []
                ).forEach(titular => {
                    nombresParcela.set(
                        Number(
                            titular.id_parcela_titular
                        ),
                        [
                            titular.nombre,
                            titular.apellido_paterno,
                            titular.apellido_materno
                        ]
                            .filter(Boolean)
                            .join(" ")
                    );
                });

            } catch {
                nombresParcela =
                    new Map();
            }
        }

        elementos.titularesUnidadContainer.innerHTML =
            "";

        if (lista.length === 0) {
            elementos.titularesUnidadContainer.innerHTML =
                '<p class="proyectos-lista-vacia">No hay titulares registrados para esta unidad.</p>';

            return;
        }

        lista.forEach(titular => {
            const nombre =
                titular.id_parcela_titular
                    ? (
                        nombresParcela.get(
                            Number(
                                titular.id_parcela_titular
                            )
                        ) ||
                        `Titular de parcela #${titular.id_parcela_titular}`
                    )
                    : `Persona #${titular.id_persona}`;

            const article =
                document.createElement(
                    "article"
                );

            article.className =
                "titular";

            article.innerHTML = `
                <div class="titular-icono">
                    <i class="bi bi-person"></i>
                </div>

                <div class="titular-datos">

                    <h3>
                        ${escaparHTML(nombre)}
                    </h3>

                    <span>
                        Participación:
                        ${
                            titular.porcentaje_participacion !=
                            null
                                ? `${escaparHTML(
                                    titular.porcentaje_participacion
                                )}%`
                                : "No especificada"
                        }
                    </span>

                    <span>
                        ${
                            titular.es_principal
                                ? "Titular principal"
                                : "Titular relacionado"
                        }
                    </span>

                </div>
            `;

            elementos.titularesUnidadContainer.appendChild(
                article
            );
        });
    }

    function crearModalTitularUnidad(opciones) {
        let modal =
            document.getElementById(
                "modalTitularUnidad"
            );

        if (modal) {
            modal.remove();
        }

        modal =
            document.createElement(
                "div"
            );

        modal.id =
            "modalTitularUnidad";

        modal.className =
            "modal";

        modal.innerHTML = `
            <div
                class="modal-contenido"
                role="dialog"
                aria-modal="true">

                <div class="modal-header">

                    <div>
                        <p class="etiqueta">
                            TITULAR
                        </p>

                        <h2>
                            Agregar titular a la unidad
                        </h2>
                    </div>

                    <button
                        type="button"
                        class="btn-cerrar-modal"
                        id="cerrarTitularUnidad">

                        <i class="bi bi-x-lg"></i>

                    </button>

                </div>

                <form id="formTitularUnidad">

                    <div class="form-grid">

                        <div class="campo campo-completo">

                            <label for="parcelaTitularUnidad">
                                Titular de la parcela *
                            </label>

                            <select
                                id="parcelaTitularUnidad"
                                required>

                                <option value="">
                                    Seleccionar
                                </option>

                                ${opciones
                                    .map(
                                        opcion =>
                                            `<option value="${opcion.id}">${escaparHTML(
                                                opcion.nombre
                                            )}</option>`
                                    )
                                    .join("")}

                            </select>

                        </div>

                        <div class="campo">

                            <label for="porcentajeTitularUnidad">
                                Porcentaje
                            </label>

                            <input
                                id="porcentajeTitularUnidad"
                                type="number"
                                min="0"
                                max="100"
                                step="0.01">

                        </div>

                        <div class="campo campo-checkbox">

                            <label>
                                <input
                                    id="principalTitularUnidad"
                                    type="checkbox">

                                <span>
                                    Es principal
                                </span>
                            </label>

                        </div>

                    </div>

                    <div class="acciones-formulario">

                        <button
                            type="button"
                            class="btn-secundario"
                            id="cancelarTitularUnidad">

                            Cancelar

                        </button>

                        <button
                            type="submit"
                            class="btn-principal">

                            Agregar titular

                        </button>

                    </div>

                </form>

            </div>
        `;

        document.body.appendChild(
            modal
        );

        document.body.style.overflow =
            "hidden";

        const cerrar = () => {
            modal.remove();
            document.body.style.overflow =
                "";
        };

        modal
            .querySelector(
                "#cerrarTitularUnidad"
            )
            .addEventListener(
                "click",
                cerrar
            );

        modal
            .querySelector(
                "#cancelarTitularUnidad"
            )
            .addEventListener(
                "click",
                cerrar
            );

        modal.addEventListener(
            "click",
            event => {
                if (
                    event.target === modal
                ) {
                    cerrar();
                }
            }
        );

        modal
            .querySelector(
                "#formTitularUnidad"
            )
            .addEventListener(
                "submit",
                async event => {
                    event.preventDefault();

                    const idParcelaTitular =
                        Number(
                            modal
                                .querySelector(
                                    "#parcelaTitularUnidad"
                                )
                                .value
                        );

                    const valorPorcentaje =
                        modal
                            .querySelector(
                                "#porcentajeTitularUnidad"
                            )
                            .value;

                    if (!idParcelaTitular) {
                        return;
                    }

                    const submit =
                        event.currentTarget.querySelector(
                            '[type="submit"]'
                        );

                    submit.disabled =
                        true;

                    try {
                        await window.UnidadesAgrariasAPI.agregarTitular(
                            unidadSeleccionada.id_unidad_agraria,
                            {
                                id_persona:
                                    null,

                                id_parcela_titular:
                                    idParcelaTitular,

                                porcentaje_participacion:
                                    valorPorcentaje === ""
                                        ? null
                                        : Number(
                                            valorPorcentaje
                                        ),

                                es_principal:
                                    modal
                                        .querySelector(
                                            "#principalTitularUnidad"
                                        )
                                        .checked
                            }
                        );

                        cerrar();

                        await cargarTitularesUnidad();

                    } catch (error) {
                        window.ClienteAPI.mostrarErrorAPI(
                            error
                        );

                        submit.disabled =
                            false;
                    }
                }
            );
    }

    async function abrirAgregarTitular() {
        if (
            !puedeCapturar ||
            !unidadSeleccionada
        ) {
            return;
        }

        if (!unidadSeleccionada.id_parcela) {
            alert(
                "Para seleccionar un titular desde la interfaz, primero relaciona la unidad con una parcela que tenga titulares registrados."
            );

            return;
        }

        try {
            const titulares =
                await window.ParcelasAPI.listarTitulares(
                    unidadSeleccionada.id_parcela
                );

            const opciones =
                (
                    Array.isArray(titulares)
                        ? titulares
                        : []
                ).map(titular => ({
                    id:
                        titular.id_parcela_titular,

                    nombre:
                        [
                            titular.nombre,
                            titular.apellido_paterno,
                            titular.apellido_materno
                        ]
                            .filter(Boolean)
                            .join(" ") ||
                        `Titular #${titular.id_parcela_titular}`
                }));

            if (opciones.length === 0) {
                alert(
                    "La parcela relacionada todavía no tiene titulares. Registra primero un titular en la ficha de la parcela."
                );

                return;
            }

            crearModalTitularUnidad(
                opciones
            );

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(
                error
            );
        }
    }

    function obtenerDatosVinculacion() {
        const data =
            new FormData(
                elementos.formVinculacion
            );

        return {
            superficie_preliminar_ha:
                valorNumerico(
                    data,
                    "superficie_preliminar_ha"
                ),

            superficie_afectada_ha:
                valorNumerico(
                    data,
                    "superficie_afectada_ha"
                ),

            superficie_valor_original:
                data
                    .get(
                        "superficie_valor_original"
                    )
                    ?.trim() ||
                null,

            superficie_formato_origen:
                data
                    .get(
                        "superficie_formato_origen"
                    )
                    ?.trim() ||
                null,

            fuente:
                data
                    .get("fuente")
                    ?.trim() ||
                null
        };
    }

    function rellenarVinculacion(datos) {
        elementos.formVinculacion
            .querySelector(
                "#superficiePreliminar"
            )
            .value =
            datos?.superficie_preliminar_ha ??
            "";

        elementos.formVinculacion
            .querySelector(
                "#superficieAfectada"
            )
            .value =
            datos?.superficie_afectada_ha ??
            "";

        elementos.formVinculacion
            .querySelector(
                "#superficieValorOriginal"
            )
            .value =
            datos?.superficie_valor_original ||
            "";

        elementos.formVinculacion
            .querySelector(
                "#superficieFormatoOrigen"
            )
            .value =
            datos?.superficie_formato_origen ||
            "";

        elementos.formVinculacion
            .querySelector(
                "#fuenteVinculacion"
            )
            .value =
            datos?.fuente ||
            "";
    }

    async function cargarVinculoActual() {
        vinculoActual =
            null;

        const relaciones =
            await window.UnidadesAgrariasAPI.listarPorAfectacion(
                Number(idAfectacion)
            );

        vinculoActual =
            (
                Array.isArray(relaciones)
                    ? relaciones
                    : []
            ).find(
                relacion =>
                    Number(
                        relacion.id_unidad_agraria
                    ) ===
                    Number(
                        idUnidadAgraria
                    )
            ) ||
            null;

        rellenarVinculacion(
            vinculoActual
        );

        const submit =
            elementos.formVinculacion.querySelector(
                '[type="submit"]'
            );

        if (submit) {
            submit.innerHTML =
                vinculoActual
                    ? '<i class="bi bi-check-lg"></i> Actualizar vínculo'
                    : '<i class="bi bi-link"></i> Vincular afectación';
        }
    }

    elementos.btnNuevaUnidad
        ?.addEventListener(
            "click",
            () => {
                if (
                    elementos.formularioUnidad.hidden
                ) {
                    mostrarFormularioUnidad();

                } else {
                    ocultarFormularioUnidad();
                }
            }
        );

    elementos.btnCerrarFormulario
        ?.addEventListener(
            "click",
            ocultarFormularioUnidad
        );

    elementos.btnCancelarUnidad
        ?.addEventListener(
            "click",
            ocultarFormularioUnidad
        );

    elementos.requiereRevision
        ?.addEventListener(
            "change",
            actualizarMotivoRevision
        );

    elementos.btnAgregarTitular
        ?.addEventListener(
            "click",
            abrirAgregarTitular
        );

    elementos.formUnidad
        ?.addEventListener(
            "submit",
            async event => {
                event.preventDefault();

                if (
                    !elementos.formUnidad.checkValidity()
                ) {
                    elementos.formUnidad.reportValidity();
                    return;
                }

                const datos =
                    obtenerDatosUnidad();

                const error =
                    validarUnidad(datos);

                if (error) {
                    alert(error);
                    return;
                }

                const submit =
                    elementos.formUnidad.querySelector(
                        '[type="submit"]'
                    );

                submit.disabled =
                    true;

                try {
                    const creada =
                        await window.UnidadesAgrariasAPI.crear(
                            Number(
                                idProyectoNucleo
                            ),
                            datos
                        );

                    ocultarFormularioUnidad();

                    await cargarUnidades();

                    if (idAfectacion) {
                        window.location.href =
                            urlUnidad(
                                creada.id_unidad_agraria
                            );
                    }

                } catch (errorAPI) {
                    window.ClienteAPI.mostrarErrorAPI(
                        errorAPI
                    );

                } finally {
                    submit.disabled =
                        false;
                }
            }
        );

    elementos.formVinculacion
        ?.addEventListener(
            "submit",
            async event => {
                event.preventDefault();

                if (
                    !idAfectacion ||
                    !idUnidadAgraria
                ) {
                    return;
                }

                const datos =
                    obtenerDatosVinculacion();

                if (
                    datos.superficie_preliminar_ha != null &&
                    datos.superficie_preliminar_ha < 0
                ) {
                    alert(
                        "La superficie preliminar no puede ser negativa."
                    );

                    return;
                }

                if (
                    datos.superficie_afectada_ha != null &&
                    datos.superficie_afectada_ha < 0
                ) {
                    alert(
                        "La superficie afectada no puede ser negativa."
                    );

                    return;
                }

                const submit =
                    elementos.formVinculacion.querySelector(
                        '[type="submit"]'
                    );

                submit.disabled =
                    true;

                const yaExistia =
                    Boolean(vinculoActual);

                try {
                    if (vinculoActual) {
                        await window.UnidadesAgrariasAPI.actualizarVinculo(
                            vinculoActual.id_afectacion_unidad,
                            datos
                        );

                    } else {
                        await window.UnidadesAgrariasAPI.vincularAAfectacion(
                            Number(idAfectacion),
                            {
                                id_unidad_agraria:
                                    Number(
                                        idUnidadAgraria
                                    ),
                                ...datos
                            }
                        );
                    }

                    await cargarVinculoActual();

                    alert(
                        yaExistia
                            ? "La vinculación quedó actualizada."
                            : "La unidad quedó vinculada a la afectación."
                    );

                } catch (error) {
                    window.ClienteAPI.mostrarErrorAPI(
                        error
                    );

                } finally {
                    submit.disabled =
                        false;
                }
            }
        );

    elementos.btnCancelarVinculacion
        ?.addEventListener(
            "click",
            () => {
                rellenarVinculacion(
                    vinculoActual
                );
            }
        );

    configurarNavegacion();
    actualizarMotivoRevision();

    try {
        await cargarRol();
        await cargarCatalogosYParcelas();
        await cargarUnidades();
        await cargarUnidadSeleccionada();

    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(
            error
        );
    }
});