document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idProyectoNucleo =
        parametros.get(
            "id_proyecto_nucleo"
        );

    const idParcela =
        parametros.get(
            "id_parcela"
        );

    const idPersonaCreada =
        parametros.get(
            "id_persona_creada"
        );

    const nombrePersonaCreada =
        parametros.get(
            "persona_nombre"
        );

    const elementos = {
        main:
            document.querySelector("main"),

        encabezado:
            document.querySelector(".pagina-header"),

        bloqueParcela:
            document.querySelector(".bloque-parcela"),

        seccionTitulares:
            document.querySelectorAll(
                "main > section.tarjeta"
            )[1] || null,

        enlaceNucleo:
            document.getElementById(
                "enlaceNucleo"
            ),

        btnEditarParcela:
            document.getElementById(
                "btnEditarParcela"
            ),

        btnEditarDatosParcela:
            document.getElementById(
                "btnEditarDatosParcela"
            ),

        estadoParcela:
            document.getElementById(
                "estadoParcela"
            ),

        tipoParcela:
            document.getElementById(
                "tipoParcela"
            ),

        numeroParcela:
            document.getElementById(
                "numeroParcela"
            ),

        certificadoParcelario:
            document.getElementById(
                "certificadoParcelario"
            ),

        folioDerechos:
            document.getElementById(
                "folioDerechos"
            ),

        constanciaVigencia:
            document.getElementById(
                "constanciaVigencia"
            ),

        titularesContainer:
            document.getElementById(
                "titularesContainer"
            ),

        sinTitulares:
            document.getElementById(
                "sinTitulares"
            ),

        contadorTitulares:
            document.getElementById(
                "contadorTitulares"
            ),

        btnAgregarTitular:
            document.getElementById(
                "btnAgregarTitular"
            ),

        modalTitular:
            document.getElementById(
                "modalTitular"
            ),

        btnCerrarModal:
            document.getElementById(
                "btnCerrarModal"
            ),

        btnCancelarTitular:
            document.getElementById(
                "btnCancelarTitular"
            ),

        formTitular:
            document.getElementById(
                "formTitular"
            ),

        idPersona:
            document.getElementById(
                "idPersona"
            ),

        btnNuevaPersona:
            document.getElementById(
                "btnNuevaPersona"
            )
    };

    let parcela = null;
    let contextoProyectoNucleo = null;
    let puedeCapturar = false;

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function fechaLegible(valorISO) {
        if (!valorISO) {
            return "—";
        }

        const partes =
            String(valorISO)
                .split("-");

        return partes.length === 3
            ? `${partes[2]}/${partes[1]}/${partes[0]}`
            : String(valorISO);
    }

    function limpiarPersonaRetornoDeUrl() {
        if (!idPersonaCreada) {
            return;
        }

        const url =
            new URL(
                window.location.href
            );

        url.searchParams.delete(
            "id_persona_creada"
        );

        url.searchParams.delete(
            "persona_nombre"
        );

        history.replaceState(
            {},
            "",
            `${url.pathname}${url.search}`
        );
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
    }

    async function cargarContextoProyectoNucleo() {
        if (
            !idProyectoNucleo ||
            contextoProyectoNucleo
        ) {
            return contextoProyectoNucleo;
        }

        contextoProyectoNucleo =
            await window.NucleosAPI
                .obtenerProyectoNucleo(
                    Number(idProyectoNucleo)
                );

        return contextoProyectoNucleo;
    }

    function configurarNavegacion() {
        if (
            elementos.enlaceNucleo &&
            idProyectoNucleo
        ) {
            elementos.enlaceNucleo.href =
                `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                    idProyectoNucleo
                )}`;
        }
    }

    function crearModalParcela() {
        let modal =
            document.getElementById(
                "modalParcelaEdicion"
            );

        if (modal) {
            return modal;
        }

        modal =
            document.createElement("div");

        modal.id =
            "modalParcelaEdicion";

        modal.className =
            "modal";

        modal.hidden = true;

        modal.innerHTML = `
            <div class="modal-contenido"
                 role="dialog"
                 aria-modal="true"
                 aria-labelledby="tituloModalParcela">

                <div class="modal-header">

                    <div>
                        <p class="etiqueta">
                            PARCELA
                        </p>

                        <h2 id="tituloModalParcela">
                            Registrar parcela
                        </h2>
                    </div>

                    <button
                        type="button"
                        class="btn-cerrar-modal"
                        id="btnCerrarModalParcela"
                        aria-label="Cerrar">

                        <i class="bi bi-x-lg"></i>

                    </button>

                </div>

                <form id="formParcelaEdicion">

                    <div class="form-grid">

                        <div class="campo">

                            <label for="editTipoParcela">
                                Tipo de parcela *
                            </label>

                            <select
                                id="editTipoParcela"
                                required>

                                <option value="">
                                    Seleccionar
                                </option>

                                <option value="individual">
                                    Individual
                                </option>

                                <option value="copropiedad">
                                    Copropiedad
                                </option>

                                <option value="otro">
                                    Otro
                                </option>

                                <option value="no_determinado">
                                    No determinado
                                </option>

                            </select>

                        </div>

                        <div class="campo">

                            <label for="editNoParcela">
                                Número / clave
                            </label>

                            <input
                                id="editNoParcela"
                                type="text"
                                maxlength="80">

                        </div>

                        <div class="campo">

                            <label for="editCertificadoParcelario">
                                Certificado parcelario
                            </label>

                            <input
                                id="editCertificadoParcelario"
                                type="text"
                                maxlength="120">

                        </div>

                        <div class="campo">

                            <label for="editFolioDerechos">
                                Folio de derechos
                            </label>

                            <input
                                id="editFolioDerechos"
                                type="text"
                                maxlength="120">

                        </div>

                        <div class="campo">

                            <label for="editConstanciaVigencia">
                                Constancia de vigencia
                            </label>

                            <input
                                id="editConstanciaVigencia"
                                type="date">

                        </div>

                    </div>

                    <div
                        id="errorParcelaEdicion"
                        class="mensaje-error"
                        hidden>
                    </div>

                    <div class="acciones-formulario">

                        <button
                            type="button"
                            class="btn-secundario"
                            id="btnCancelarParcelaEdicion">

                            Cancelar

                        </button>

                        <button
                            type="submit"
                            class="btn-principal">

                            Guardar

                        </button>

                    </div>

                </form>

            </div>
        `;

        document.body.appendChild(
            modal
        );

        const cerrar = () => {
            modal.hidden = true;
            document.body.style.overflow = "";
        };

        modal
            .querySelector(
                "#btnCerrarModalParcela"
            )
            ?.addEventListener(
                "click",
                cerrar
            );

        modal
            .querySelector(
                "#btnCancelarParcelaEdicion"
            )
            ?.addEventListener(
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

        return modal;
    }

    function abrirModalParcela(
        modo,
        datos = null
    ) {
        if (!puedeCapturar) {
            return;
        }

        const modal =
            crearModalParcela();

        const titulo =
            modal.querySelector(
                "#tituloModalParcela"
            );

        const form =
            modal.querySelector(
                "#formParcelaEdicion"
            );

        const error =
            modal.querySelector(
                "#errorParcelaEdicion"
            );

        titulo.textContent =
            modo === "crear"
                ? "Registrar parcela"
                : "Editar parcela";

        error.hidden = true;
        error.textContent = "";

        form.querySelector(
            "#editTipoParcela"
        ).value =
            datos?.tipo_parcela ||
            "";

        form.querySelector(
            "#editNoParcela"
        ).value =
            datos?.no_parcela ||
            "";

        form.querySelector(
            "#editCertificadoParcelario"
        ).value =
            datos?.certificado_parcelario ||
            "";

        form.querySelector(
            "#editFolioDerechos"
        ).value =
            datos?.folio_derechos ||
            "";

        form.querySelector(
            "#editConstanciaVigencia"
        ).value =
            datos?.constancia_vigencia_fecha ||
            "";

        form.onsubmit =
            async event => {
                event.preventDefault();

                const payload = {
                    tipo_parcela:
                        form.querySelector(
                            "#editTipoParcela"
                        ).value,

                    no_parcela:
                        form.querySelector(
                            "#editNoParcela"
                        ).value.trim() ||
                        null,

                    certificado_parcelario:
                        form.querySelector(
                            "#editCertificadoParcelario"
                        ).value.trim() ||
                        null,

                    folio_derechos:
                        form.querySelector(
                            "#editFolioDerechos"
                        ).value.trim() ||
                        null,

                    constancia_vigencia_fecha:
                        form.querySelector(
                            "#editConstanciaVigencia"
                        ).value ||
                        null
                };

                if (
                    !payload.tipo_parcela
                ) {
                    error.textContent =
                        "Selecciona el tipo de parcela.";

                    error.hidden = false;

                    return;
                }

                const submit =
                    form.querySelector(
                        '[type="submit"]'
                    );

                submit.disabled = true;

                try {
                    if (
                        modo === "crear"
                    ) {
                        if (
                            !idProyectoNucleo
                        ) {
                            throw new Error(
                                "Falta id_proyecto_nucleo para registrar la parcela."
                            );
                        }

                        const creada =
                            await window.ParcelasAPI
                                .crear(
                                    Number(
                                        idProyectoNucleo
                                    ),
                                    payload
                                );

                        window.location.href =
                            `/pages/parcela.html?id_proyecto_nucleo=${encodeURIComponent(
                                idProyectoNucleo
                            )}` +
                            `&id_parcela=${encodeURIComponent(
                                creada.id_parcela
                            )}`;

                    } else {
                        parcela =
                            await window.ParcelasAPI
                                .actualizar(
                                    Number(idParcela),
                                    payload
                                );

                        pintarParcela(
                            parcela
                        );

                        cerrarModalProgramaticamente(
                            modal
                        );
                    }

                } catch (err) {
                    error.textContent =
                        err?.mensaje ||
                        err?.message ||
                        "No se pudo guardar la parcela.";

                    error.hidden = false;

                } finally {
                    submit.disabled = false;
                }
            };

        modal.hidden = false;
        document.body.style.overflow =
            "hidden";

        form.querySelector(
            "#editTipoParcela"
        ).focus();
    }

    function cerrarModalProgramaticamente(
        modal
    ) {
        modal.hidden = true;
        document.body.style.overflow = "";
    }

    function pintarParcela(datos) {
        if (!datos) {
            return;
        }

        elementos.tipoParcela.textContent =
            {
                individual:
                    "Individual",

                copropiedad:
                    "Copropiedad",

                otro:
                    "Otro",

                no_determinado:
                    "No determinado"
            }[datos.tipo_parcela] ||
            datos.tipo_parcela ||
            "—";

        elementos.numeroParcela.textContent =
            datos.no_parcela ||
            "—";

        elementos.certificadoParcelario.textContent =
            datos.certificado_parcelario ||
            "—";

        elementos.folioDerechos.textContent =
            datos.folio_derechos ||
            "—";

        elementos.constanciaVigencia.textContent =
            fechaLegible(
                datos.constancia_vigencia_fecha
            );

        elementos.estadoParcela.textContent =
            datos.activo === false
                ? "Inactiva"
                : "Registrada";
    }

    function nombreTitular(titular) {
        return [
            titular.nombre,
            titular.apellido_paterno,
            titular.apellido_materno
        ]
            .filter(Boolean)
            .join(" ") ||
            `Persona #${titular.id_persona}`;
    }

    function agregarOpcionPersona(
        id,
        nombre,
        seleccionar = false
    ) {
        if (
            !elementos.idPersona ||
            !id
        ) {
            return;
        }

        let option =
            [
                ...elementos.idPersona.options
            ].find(
                item =>
                    String(item.value) ===
                    String(id)
            );

        if (!option) {
            option =
                document.createElement(
                    "option"
                );

            option.value =
                String(id);

            option.textContent =
                nombre ||
                `Persona #${id}`;

            elementos.idPersona.appendChild(
                option
            );
        }

        if (seleccionar) {
            elementos.idPersona.value =
                String(id);
        }
    }

    function pintarTitulares(lista) {
        elementos.titularesContainer.innerHTML =
            "";

        const titulares =
            Array.isArray(lista)
                ? lista
                : [];

        titulares.forEach(
            titular => {
                const article =
                    document.createElement(
                        "article"
                    );

                article.className =
                    "titular";

                article.dataset.titular =
                    "";

                article.innerHTML = `
                    <div class="titular-icono">
                        <i class="bi bi-person"></i>
                    </div>

                    <div class="titular-datos">

                        <h3>
                            ${escaparHTML(
                                nombreTitular(
                                    titular
                                )
                            )}
                        </h3>

                        <span>
                            Tipo de derecho:
                            ${escaparHTML(
                                titular.tipo_derecho ||
                                "—"
                            )}
                        </span>

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

                    </div>

                    <div class="titular-vigencia">

                        <span>
                            Inicio:
                            ${escaparHTML(
                                fechaLegible(
                                    titular.fecha_inicio
                                )
                            )}
                        </span>

                        <span>
                            Fin:
                            ${escaparHTML(
                                fechaLegible(
                                    titular.fecha_fin
                                )
                            )}
                        </span>

                    </div>
                `;

                elementos.titularesContainer
                    .appendChild(article);

                agregarOpcionPersona(
                    titular.id_persona,
                    nombreTitular(titular)
                );
            }
        );

        elementos.contadorTitulares.textContent =
            titulares.length === 1
                ? "1 titular"
                : `${titulares.length} titulares`;

        elementos.sinTitulares.hidden =
            titulares.length > 0;

        elementos.sinTitulares.style.display =
            titulares.length > 0
                ? "none"
                : "";
    }

    async function cargarTitulares() {
        if (!idParcela) {
            return;
        }

        const titulares =
            await window.ParcelasAPI
                .listarTitulares(
                    Number(idParcela)
                );

        pintarTitulares(titulares);
    }

    function abrirModalTitular() {
        if (
            !idParcela ||
            !puedeCapturar
        ) {
            return;
        }

        elementos.modalTitular.hidden =
            false;

        document.body.style.overflow =
            "hidden";

        elementos.idPersona?.focus();
    }

    function cerrarModalTitular() {
        elementos.modalTitular.hidden =
            true;

        document.body.style.overflow =
            "";

        elementos.formTitular.reset();

        if (idPersonaCreada) {
            agregarOpcionPersona(
                idPersonaCreada,
                nombrePersonaCreada,
                true
            );
        }
    }

    function datosTitular() {
        const data =
            new FormData(
                elementos.formTitular
            );

        const porcentaje =
            data.get(
                "porcentaje_participacion"
            );

        return {
            id_persona:
                data.get("id_persona")
                    ? Number(
                        data.get(
                            "id_persona"
                        )
                    )
                    : null,

            tipo_derecho:
                data.get(
                    "tipo_derecho"
                )?.trim() ||
                "",

            porcentaje_participacion:
                porcentaje
                    ? Number(porcentaje)
                    : null,

            fecha_inicio:
                data.get(
                    "fecha_inicio"
                ) ||
                null,

            fecha_fin:
                data.get(
                    "fecha_fin"
                ) ||
                null
        };
    }

    function validarTitular(datos) {
        if (!datos.id_persona) {
            return "Selecciona una persona.";
        }

        if (!datos.tipo_derecho) {
            return "El tipo de derecho es obligatorio.";
        }

        if (
            datos.tipo_derecho.length > 50
        ) {
            return "El tipo de derecho no puede superar 50 caracteres.";
        }

        if (
            datos.porcentaje_participacion !=
            null &&
            (
                !Number.isFinite(
                    datos.porcentaje_participacion
                ) ||
                datos.porcentaje_participacion <= 0 ||
                datos.porcentaje_participacion > 100
            )
        ) {
            return "El porcentaje debe ser mayor a 0 y hasta 100.";
        }

        if (
            datos.fecha_inicio &&
            datos.fecha_fin &&
            datos.fecha_fin <
            datos.fecha_inicio
        ) {
            return "La fecha de fin no puede ser anterior a la fecha de inicio.";
        }

        return null;
    }

    function crearSeccionListado() {
        let seccion =
            document.getElementById(
                "seccionListaParcelas"
            );

        if (seccion) {
            return seccion;
        }

        seccion =
            document.createElement(
                "section"
            );

        seccion.id =
            "seccionListaParcelas";

        seccion.className =
            "tarjeta";

        seccion.innerHTML = `
            <div class="seccion-titulo">

                <div>

                    <i class="bi bi-bounding-box"></i>

                    <div>

                        <h2>
                            Parcelas registradas
                        </h2>

                        <p class="descripcion-seccion">
                            Selecciona una parcela para consultar sus datos y titulares.
                        </p>

                    </div>

                </div>

                <span
                    class="contador-registros"
                    id="contadorParcelasLista">

                    0 parcelas

                </span>

            </div>

            <div id="parcelasLista"></div>

            <div
                id="sinParcelasLista"
                class="sin-registros"
                hidden>

                <i class="bi bi-bounding-box"></i>

                <p>
                    No hay parcelas registradas.
                </p>

                <span>
                    Registra una nueva parcela para este núcleo.
                </span>

            </div>
        `;

        elementos.encabezado
            .insertAdjacentElement(
                "afterend",
                seccion
            );

        return seccion;
    }

    async function cargarListadoParcelas() {
        const seccion =
            crearSeccionListado();

        const contenedor =
            seccion.querySelector(
                "#parcelasLista"
            );

        const vacio =
            seccion.querySelector(
                "#sinParcelasLista"
            );

        const contador =
            seccion.querySelector(
                "#contadorParcelasLista"
            );

        try {
            const lista =
                await window.ParcelasAPI
                    .listarPorProyectoNucleo(
                        Number(
                            idProyectoNucleo
                        )
                    );

            const parcelas =
                Array.isArray(lista)
                    ? lista
                    : [];

            contenedor.innerHTML = "";

            contador.textContent =
                parcelas.length === 1
                    ? "1 parcela"
                    : `${parcelas.length} parcelas`;

            vacio.hidden =
                parcelas.length > 0;

            vacio.style.display =
                parcelas.length > 0
                    ? "none"
                    : "";

            parcelas.forEach(
                item => {
                    const card =
                        document.createElement(
                            "article"
                        );

                    card.className =
                        "tarjeta";

                    card.style.marginBottom =
                        "1rem";

                    card.innerHTML = `
                        <div class="seccion-titulo">

                            <div>

                                <i class="bi bi-bounding-box"></i>

                                <div>

                                    <h3>
                                        ${escaparHTML(
                                            item.no_parcela ||
                                            `Parcela #${item.id_parcela}`
                                        )}
                                    </h3>

                                    <p>
                                        ${escaparHTML(
                                            item.tipo_parcela ||
                                            "—"
                                        )}
                                    </p>

                                </div>

                            </div>

                            <a
                                class="btn-secundario"
                                href="/pages/parcela.html?id_proyecto_nucleo=${encodeURIComponent(
                                    idProyectoNucleo
                                )}&id_parcela=${encodeURIComponent(
                                    item.id_parcela
                                )}">

                                Consultar

                            </a>

                        </div>
                    `;

                    contenedor.appendChild(
                        card
                    );
                }
            );

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(
                error
            );
        }
    }

    async function modoListado() {
        elementos.bloqueParcela.hidden =
            true;

        if (
            elementos.seccionTitulares
        ) {
            elementos.seccionTitulares.hidden =
                true;
        }

        const h1 =
            elementos.encabezado?.querySelector(
                "h1"
            );

        const subtitulo =
            elementos.encabezado?.querySelector(
                ".subtitulo"
            );

        if (h1) {
            h1.textContent =
                "Parcelas";
        }

        if (subtitulo) {
            subtitulo.textContent =
                "Consulta o registra las parcelas pertenecientes a este núcleo agrario.";
        }

        if (
            elementos.btnEditarParcela
        ) {
            elementos.btnEditarParcela.innerHTML =
                '<i class="bi bi-plus-lg"></i> Nueva parcela';

            elementos.btnEditarParcela.hidden =
                !puedeCapturar;

            elementos.btnEditarParcela
                .addEventListener(
                    "click",
                    () =>
                        abrirModalParcela(
                            "crear"
                        )
                );
        }

        await cargarListadoParcelas();
    }

    async function modoDetalle() {
        elementos.titularesContainer.innerHTML =
            "";

        elementos.sinTitulares.hidden =
            false;

        elementos.contadorTitulares.textContent =
            "0 titulares";

        try {
            parcela =
                await window.ParcelasAPI
                    .obtener(
                        Number(idParcela)
                    );

            pintarParcela(parcela);

            await cargarTitulares();

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(
                error
            );

            return;
        }

        if (
            elementos.btnEditarParcela
        ) {
            elementos.btnEditarParcela.hidden =
                !puedeCapturar;

            elementos.btnEditarParcela
                .addEventListener(
                    "click",
                    () =>
                        abrirModalParcela(
                            "editar",
                            parcela
                        )
                );
        }

        if (
            elementos.btnEditarDatosParcela
        ) {
            elementos.btnEditarDatosParcela.hidden =
                !puedeCapturar;

            elementos.btnEditarDatosParcela
                .addEventListener(
                    "click",
                    () =>
                        abrirModalParcela(
                            "editar",
                            parcela
                        )
                );
        }

        if (
            elementos.btnAgregarTitular
        ) {
            elementos.btnAgregarTitular.hidden =
                !puedeCapturar;
        }

        if (
            elementos.btnNuevaPersona
        ) {
            elementos.btnNuevaPersona.hidden =
                !puedeCapturar;
        }

        if (idPersonaCreada) {
            agregarOpcionPersona(
                idPersonaCreada,
                nombrePersonaCreada ||
                `Persona #${idPersonaCreada}`,
                true
            );

            limpiarPersonaRetornoDeUrl();

            setTimeout(
                () => {
                    abrirModalTitular();
                },
                0
            );
        }
    }

    elementos.btnAgregarTitular
        ?.addEventListener(
            "click",
            abrirModalTitular
        );

    elementos.btnCerrarModal
        ?.addEventListener(
            "click",
            cerrarModalTitular
        );

    elementos.btnCancelarTitular
        ?.addEventListener(
            "click",
            cerrarModalTitular
        );

    elementos.modalTitular
        ?.addEventListener(
            "click",
            event => {
                if (
                    event.target ===
                    elementos.modalTitular
                ) {
                    cerrarModalTitular();
                }
            }
        );

    elementos.formTitular
        ?.addEventListener(
            "submit",
            async event => {
                event.preventDefault();

                const datos =
                    datosTitular();

                const error =
                    validarTitular(
                        datos
                    );

                if (error) {
                    alert(error);
                    return;
                }

                const submit =
                    elementos.formTitular
                        .querySelector(
                            '[type="submit"]'
                        );

                submit.disabled = true;

                try {
                    await window.ParcelasAPI
                        .agregarTitular(
                            Number(
                                idParcela
                            ),
                            datos
                        );

                    await cargarTitulares();

                    cerrarModalTitular();

                } catch (err) {
                    window.ClienteAPI
                        .mostrarErrorAPI(
                            err
                        );

                } finally {
                    submit.disabled =
                        false;
                }
            }
        );

    elementos.btnNuevaPersona
        ?.addEventListener(
            "click",
            async () => {
                if (
                    !idProyectoNucleo
                ) {
                    alert(
                        "No se pudo determinar el proyecto de esta parcela."
                    );

                    return;
                }

                try {
                    const contexto =
                        await cargarContextoProyectoNucleo();

                    const retorno =
                        `${window.location.pathname}${window.location.search}`;

                    window.location.href =
                        `/pages/persona.html?id_proyecto=${encodeURIComponent(
                            contexto.id_proyecto
                        )}` +
                        `&return_to=${encodeURIComponent(
                            retorno
                        )}`;

                } catch (error) {
                    window.ClienteAPI
                        .mostrarErrorAPI(
                            error
                        );
                }
            }
        );

    configurarNavegacion();

    await cargarRol();

    if (!idParcela) {
        if (!idProyectoNucleo) {
            window.ClienteAPI
                .mostrarErrorAPI(
                    new Error(
                        "Falta id_proyecto_nucleo para consultar las parcelas."
                    )
                );

            return;
        }

        await modoListado();

    } else {
        await modoDetalle();
    }
});