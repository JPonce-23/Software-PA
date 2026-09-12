document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros = new URLSearchParams(window.location.search);
    const idProyectoNucleo = Number(parametros.get("id_proyecto_nucleo"));

    const elementos = {
        nombreNucleo: document.getElementById("nombreNucleo"),
        btnVolver: document.getElementById("btnVolver"),
        btnCancelar: document.getElementById("btnCancelar"),
        form: document.getElementById("formAsamblea"),
        idPadron: document.getElementById("idPadron"),
        idTipoAsamblea: document.getElementById("idTipoAsamblea"),
        idContextoAsamblea: document.getElementById("idContextoAsamblea"),
        idTipoCopOperativo: document.getElementById("idTipoCopOperativo"),
        proposito: document.getElementById("proposito"),
        resultado: document.getElementById("resultado"),
        btnAgregarConvocatoria: document.getElementById("btnAgregarConvocatoria"),
        convocatoriasContainer: document.getElementById("convocatoriasContainer"),
        sinConvocatorias: document.getElementById("sinConvocatorias")
    };

    if (!Number.isInteger(idProyectoNucleo) || idProyectoNucleo <= 0) {
        window.ClienteAPI.mostrarErrorAPI(
            new Error(
                "No se puede abrir Asamblea porque falta un id_proyecto_nucleo válido."
            )
        );

        return;
    }

    let puedeCapturar = false;
    let indiceConvocatoria = 0;
    let resultadosConvocatoria = [];
    let asambleas = [];
    let idAsambleaEdicion = null;
    let seccionListado = null;

    const codigosCatalogo = {
        tipo_asamblea: new Map(),
        contexto_asamblea: new Map(),
        resultado_convocatoria: new Map()
    };

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

        elementos.form
            .querySelectorAll(
                "input, select, textarea, button"
            )
            .forEach(control => {
                control.disabled =
                    !puedeCapturar;
            });

        if (elementos.btnVolver) {
            elementos.btnVolver.disabled =
                false;
        }

        if (elementos.btnCancelar) {
            elementos.btnCancelar.disabled =
                false;
        }
    }

    async function cargarContexto() {
        try {
            const contexto =
                await window.NucleosAPI.obtenerProyectoNucleo(
                    idProyectoNucleo
                );

            if (elementos.nombreNucleo) {
                elementos.nombreNucleo.textContent =
                    contexto.nombre_nucleo ||
                    "Núcleo agrario";
            }

            document.title =
                `Asambleas | ${
                    contexto.nombre_nucleo ||
                    "Núcleo agrario"
                } | SSALFER`;

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(
                error
            );
        }
    }

    function limpiarSelect(
        select,
        textoInicial
    ) {
        if (!select) {
            return;
        }

        select.innerHTML = "";

        const option =
            document.createElement(
                "option"
            );

        option.value = "";
        option.textContent =
            textoInicial;

        select.appendChild(
            option
        );
    }

    async function cargarCatalogo(
        tipo,
        select,
        textoInicial
    ) {
        limpiarSelect(
            select,
            textoInicial
        );

        const opciones =
            await window.CatalogosAPI.obtenerOperativo(
                tipo
            );

        const lista =
            Array.isArray(opciones)
                ? opciones
                : [];

        if (codigosCatalogo[tipo]) {
            codigosCatalogo[tipo].clear();
        }

        lista.forEach(opcion => {
            const id =
                Number(
                    opcion.id_catalogo_opcion
                );

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                String(id);

            option.textContent =
                opcion.nombre ||
                opcion.codigo ||
                `Opción ${id}`;

            option.dataset.codigo =
                opcion.codigo ||
                "";

            select.appendChild(
                option
            );

            if (codigosCatalogo[tipo]) {
                codigosCatalogo[tipo].set(
                    id,
                    opcion.codigo || ""
                );
            }
        });

        return lista;
    }

    async function cargarPadrones() {
        limpiarSelect(
            elementos.idPadron,
            "Sin padrón asociado"
        );

        try {
            const padrones =
                await window.PadronesAPI.listarPorProyectoNucleo(
                    idProyectoNucleo
                );

            (
                Array.isArray(padrones)
                    ? padrones
                    : []
            ).forEach(padron => {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    String(
                        padron.id_padron
                    );

                const partes = [];

                if (padron.fecha_padron) {
                    partes.push(
                        fechaVisual(
                            padron.fecha_padron
                        )
                    );
                }

                if (
                    padron.numero_ejidatarios_comuneros !=
                    null
                ) {
                    partes.push(
                        `${padron.numero_ejidatarios_comuneros} integrantes`
                    );
                }

                option.textContent =
                    partes.length
                        ? `Padrón #${padron.id_padron} · ${partes.join(" · ")}`
                        : `Padrón #${padron.id_padron}`;

                elementos.idPadron.appendChild(
                    option
                );
            });

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(
                error
            );
        }
    }

    async function cargarCatalogos() {
        const [
            ,
            ,
            ,
            resultados
        ] = await Promise.all([
            cargarCatalogo(
                "tipo_asamblea",
                elementos.idTipoAsamblea,
                "Seleccionar tipo"
            ),

            cargarCatalogo(
                "contexto_asamblea",
                elementos.idContextoAsamblea,
                "Seleccionar contexto"
            ),

            cargarCatalogo(
                "tipo_cop_operativo",
                elementos.idTipoCopOperativo,
                "Sin tipo COP"
            ),

            window.CatalogosAPI.obtenerOperativo(
                "resultado_convocatoria"
            )
        ]);

        resultadosConvocatoria =
            Array.isArray(resultados)
                ? resultados
                : [];

        codigosCatalogo
            .resultado_convocatoria
            .clear();

        resultadosConvocatoria.forEach(
            item => {
                codigosCatalogo
                    .resultado_convocatoria
                    .set(
                        Number(
                            item.id_catalogo_opcion
                        ),
                        item.codigo || ""
                    );
            }
        );
    }

    function opcionesResultadoHTML() {
        return resultadosConvocatoria
            .map(
                opcion => `
                    <option
                        value="${opcion.id_catalogo_opcion}"
                        data-codigo="${escaparHTML(
                            opcion.codigo || ""
                        )}">
                        ${escaparHTML(
                            opcion.nombre ||
                            opcion.codigo ||
                            opcion.id_catalogo_opcion
                        )}
                    </option>
                `
            )
            .join("");
    }

    function actualizarNumeracion() {
        const bloques = [
            ...elementos
                .convocatoriasContainer
                .querySelectorAll(
                    "[data-convocatoria]"
                )
        ];

        bloques.forEach(
            (
                bloque,
                posicion
            ) => {
                const numero =
                    posicion + 1;

                const badge =
                    bloque.querySelector(
                        ".numero-convocatoria"
                    );

                const titulo =
                    bloque.querySelector(
                        "h3"
                    );

                if (badge) {
                    badge.textContent =
                        String(numero);
                }

                if (titulo) {
                    titulo.textContent =
                        `Convocatoria ${numero}`;
                }
            }
        );

        elementos.sinConvocatorias.hidden =
            bloques.length > 0;

        elementos.sinConvocatorias.style.display =
            bloques.length > 0
                ? "none"
                : "";
    }

    function crearConvocatoria(
        valores = {}
    ) {
        const indice =
            indiceConvocatoria++;

        const bloque =
            document.createElement(
                "div"
            );

        bloque.className =
            "convocatoria";

        bloque.dataset.convocatoria =
            "";

        if (valores.id_convocatoria) {
            bloque.dataset.idConvocatoria =
                String(
                    valores.id_convocatoria
                );
        }

        const existente =
            Boolean(
                valores.id_convocatoria
            );

        bloque.innerHTML = `
            <div class="convocatoria-titulo">

                <div>

                    <span class="numero-convocatoria">
                        1
                    </span>

                    <h3>
                        Convocatoria 1
                    </h3>

                </div>

                <button
                    type="button"
                    class="btn-eliminar-convocatoria"
                    title="${
                        existente
                            ? "Las convocatorias ya guardadas no se pueden eliminar desde este endpoint"
                            : "Eliminar convocatoria"
                    }"
                    ${
                        existente
                            ? "disabled"
                            : ""
                    }>

                    <i class="bi bi-trash"></i>

                </button>

            </div>

            <div class="form-grid">

                <div class="campo">

                    <label>
                        Ordinal
                        <span class="obligatorio">
                            *
                        </span>
                    </label>

                    <input
                        type="number"
                        name="convocatorias[${indice}][ordinal]"
                        min="1"
                        step="1"
                        required>

                </div>

                <div class="campo">

                    <label>
                        Fecha de expedición
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <input
                        type="date"
                        name="convocatorias[${indice}][fecha_expedicion]">

                </div>

                <div class="campo">

                    <label>
                        Fecha programada
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <input
                        type="date"
                        name="convocatorias[${indice}][fecha_programada]">

                </div>

                <div class="campo">

                    <label>
                        Fecha de realización
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <input
                        type="date"
                        name="convocatorias[${indice}][fecha_realizacion]">

                </div>

                <div class="campo">

                    <label>
                        Resultado
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <select
                        name="convocatorias[${indice}][id_resultado]">

                        <option value="">
                            Seleccionar resultado
                        </option>

                        ${opcionesResultadoHTML()}

                    </select>

                </div>

                <div class="campo">

                    <label>
                        Documento
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <select
                        name="convocatorias[${indice}][id_documento]">

                        <option value="">
                            Sin documento
                        </option>

                    </select>

                </div>

                <div class="campo campo-completo">

                    <label>
                        Observaciones del resultado
                        <span class="opcional">
                            Opcional
                        </span>
                    </label>

                    <textarea
                        name="convocatorias[${indice}][observaciones_resultado]"
                        rows="3"></textarea>

                </div>

            </div>
        `;

        elementos
            .convocatoriasContainer
            .appendChild(
                bloque
            );

        bloque
            .querySelector(
                '[name*="[ordinal]"]'
            )
            .value =
            valores.ordinal ||
            elementos
                .convocatoriasContainer
                .querySelectorAll(
                    "[data-convocatoria]"
                ).length;

        bloque
            .querySelector(
                '[name*="[fecha_expedicion]"]'
            )
            .value =
            valores.fecha_expedicion ||
            "";

        bloque
            .querySelector(
                '[name*="[fecha_programada]"]'
            )
            .value =
            valores.fecha_programada ||
            "";

        bloque
            .querySelector(
                '[name*="[fecha_realizacion]"]'
            )
            .value =
            valores.fecha_realizacion ||
            "";

        bloque
            .querySelector(
                '[name*="[id_resultado]"]'
            )
            .value =
            valores.id_resultado
                ? String(
                    valores.id_resultado
                )
                : "";

        bloque
            .querySelector(
                '[name*="[id_documento]"]'
            )
            .value =
            valores.id_documento
                ? String(
                    valores.id_documento
                )
                : "";

        bloque
            .querySelector(
                '[name*="[observaciones_resultado]"]'
            )
            .value =
            valores.observaciones_resultado ||
            "";

        actualizarNumeracion();
    }

    function construirConvocatorias() {
        return [
            ...elementos
                .convocatoriasContainer
                .querySelectorAll(
                    "[data-convocatoria]"
                )
        ].map(
            bloque => {
                const valor =
                    sufijo =>
                        bloque
                            .querySelector(
                                `[name*="[${sufijo}]"]`
                            )
                            ?.value ??
                        "";

                return {
                    id_convocatoria:
                        bloque.dataset
                            .idConvocatoria
                            ? Number(
                                bloque.dataset
                                    .idConvocatoria
                            )
                            : null,

                    ordinal:
                        Number(
                            valor(
                                "ordinal"
                            )
                        ),

                    fecha_expedicion:
                        valor(
                            "fecha_expedicion"
                        ) ||
                        null,

                    fecha_programada:
                        valor(
                            "fecha_programada"
                        ) ||
                        null,

                    fecha_realizacion:
                        valor(
                            "fecha_realizacion"
                        ) ||
                        null,

                    id_resultado:
                        valor(
                            "id_resultado"
                        )
                            ? Number(
                                valor(
                                    "id_resultado"
                                )
                            )
                            : null,

                    observaciones_resultado:
                        valor(
                            "observaciones_resultado"
                        )
                            .trim() ||
                        null,

                    id_documento:
                        valor(
                            "id_documento"
                        )
                            ? Number(
                                valor(
                                    "id_documento"
                                )
                            )
                            : null
                };
            }
        );
    }

    function validarConvocatorias(
        convocatorias
    ) {
        const ordinales =
            convocatorias.map(
                item =>
                    item.ordinal
            );

        if (
            ordinales.some(
                item =>
                    !Number.isInteger(
                        item
                    ) ||
                    item <= 0
            )
        ) {
            return (
                "Todos los ordinales de convocatoria " +
                "deben ser enteros positivos."
            );
        }

        if (
            new Set(
                ordinales
            ).size !==
            ordinales.length
        ) {
            return (
                "Los ordinales de las convocatorias " +
                "no pueden repetirse."
            );
        }

        const celebradas =
            convocatorias.filter(
                item =>
                    item.id_resultado &&
                    codigosCatalogo
                        .resultado_convocatoria
                        .get(
                            item.id_resultado
                        ) ===
                        "celebrada"
            );

        if (
            celebradas.length > 1
        ) {
            return (
                "Una asamblea solo puede tener " +
                "una convocatoria celebrada activa."
            );
        }

        for (
            const item of
            convocatorias
        ) {
            const codigo =
                item.id_resultado
                    ? codigosCatalogo
                        .resultado_convocatoria
                        .get(
                            item.id_resultado
                        )
                    : null;

            if (
                item.fecha_realizacion &&
                codigo !==
                    "celebrada"
            ) {
                return (
                    "Una fecha de realización " +
                    "requiere resultado 'Celebrada'."
                );
            }

            if (
                codigo ===
                    "celebrada" &&
                !item.fecha_realizacion
            ) {
                return (
                    "Una convocatoria con resultado " +
                    "'Celebrada' requiere fecha de realización."
                );
            }
        }

        return null;
    }

    function validarTipoContexto() {
        const tipo =
            Number(
                elementos
                    .idTipoAsamblea
                    .value
            );

        const contexto =
            Number(
                elementos
                    .idContextoAsamblea
                    .value
            );

        const codigoTipo =
            tipo
                ? codigosCatalogo
                    .tipo_asamblea
                    .get(tipo)
                : null;

        const codigoContexto =
            contexto
                ? codigosCatalogo
                    .contexto_asamblea
                    .get(contexto)
                : null;

        if (
            codigoTipo ===
                "retiro_fondos" &&
            codigoContexto !==
                "retiro_fondos"
        ) {
            return (
                "Una asamblea de retiro de fondos " +
                "debe utilizar el contexto 'Retiro de fondos'."
            );
        }

        if (
            codigoTipo ===
                "anuencia" &&
            codigoContexto ===
                "retiro_fondos"
        ) {
            return (
                "Una asamblea de anuencia no puede " +
                "utilizar el contexto 'Retiro de fondos'."
            );
        }

        return null;
    }

    function crearSeccionListado() {
        if (seccionListado) {
            return seccionListado;
        }

        seccionListado =
            document.createElement(
                "section"
            );

        seccionListado.className =
            "tarjeta";

        seccionListado.id =
            "asambleasRegistradas";

        seccionListado.innerHTML = `
            <div class="seccion-titulo">

                <div>

                    <i class="bi bi-list-check"></i>

                    <h2>
                        Asambleas registradas
                    </h2>

                </div>

                <span id="contadorAsambleas">
                    0 asambleas
                </span>

            </div>

            <div id="listaAsambleas"></div>

            <div
                id="sinAsambleas"
                class="sin-convocatorias"
                hidden>

                <i class="bi bi-calendar-x"></i>

                <p>
                    No hay asambleas registradas.
                </p>

                <span>
                    El formulario inferior permite
                    registrar la primera.
                </span>

            </div>
        `;

        elementos.form.insertAdjacentElement(
            "beforebegin",
            seccionListado
        );

        return seccionListado;
    }

    function nombreCatalogo(
        tipo,
        id
    ) {
        const codigo =
            id
                ? codigosCatalogo[
                    tipo
                ]?.get(
                    Number(id)
                )
                : null;

        if (!codigo) {
            return "—";
        }

        const select =
            tipo ===
                "tipo_asamblea"
                ? elementos
                    .idTipoAsamblea
                : elementos
                    .idContextoAsamblea;

        const option =
            [
                ...select.options
            ].find(
                item =>
                    Number(
                        item.value
                    ) ===
                    Number(id)
            );

        return (
            option?.textContent ||
            codigo
        );
    }

    function renderAsambleas() {
        const seccion =
            crearSeccionListado();

        const lista =
            seccion.querySelector(
                "#listaAsambleas"
            );

        const vacio =
            seccion.querySelector(
                "#sinAsambleas"
            );

        const contador =
            seccion.querySelector(
                "#contadorAsambleas"
            );

        lista.innerHTML = "";

        contador.textContent =
            asambleas.length === 1
                ? "1 asamblea"
                : `${asambleas.length} asambleas`;

        vacio.hidden =
            asambleas.length > 0;

        vacio.style.display =
            asambleas.length > 0
                ? "none"
                : "";

        asambleas.forEach(
            asamblea => {
                const card =
                    document.createElement(
                        "article"
                    );

                card.style.background =
                    "#fff";

                card.style.border =
                    "1px solid #ddd";

                card.style.borderRadius =
                    "8px";

                card.style.padding =
                    "14px";

                card.style.marginBottom =
                    "10px";

                card.innerHTML = `
                    <div
                        style="
                            display:flex;
                            justify-content:space-between;
                            gap:16px;
                            align-items:center;
                        ">

                        <div>

                            <strong>
                                Asamblea #${asamblea.id_asamblea}
                            </strong>

                            <div
                                style="
                                    margin-top:5px;
                                    color:#666;
                                    font-size:.85rem;
                                ">

                                ${escaparHTML(
                                    nombreCatalogo(
                                        "tipo_asamblea",
                                        asamblea.id_tipo_asamblea
                                    )
                                )}

                                ·

                                ${escaparHTML(
                                    nombreCatalogo(
                                        "contexto_asamblea",
                                        asamblea.id_contexto_asamblea
                                    )
                                )}

                                ·

                                ${
                                    Array.isArray(
                                        asamblea.convocatorias
                                    )
                                        ? asamblea.convocatorias.length
                                        : 0
                                }
                                convocatoria(s)

                            </div>

                            ${
                                asamblea.proposito
                                    ? `
                                        <div
                                            style="
                                                margin-top:4px;
                                                color:#777;
                                                font-size:.82rem;
                                            ">

                                            ${escaparHTML(
                                                asamblea.proposito
                                            )}

                                        </div>
                                    `
                                    : ""
                            }

                        </div>

                        ${
                            puedeCapturar
                                ? `
                                    <button
                                        type="button"
                                        class="btn-secundario"
                                        data-editar-asamblea="${asamblea.id_asamblea}">

                                        <i class="bi bi-pencil"></i>

                                        Editar

                                    </button>
                                `
                                : ""
                        }

                    </div>
                `;

                lista.appendChild(
                    card
                );
            }
        );
    }

    async function cargarAsambleas() {
        const respuesta =
            await window.AsambleasAPI.listarPorProyectoNucleo(
                idProyectoNucleo
            );

        asambleas =
            Array.isArray(respuesta)
                ? respuesta
                : [];

        renderAsambleas();
    }

    function actualizarTextoFormulario() {
        const titulo =
            elementos.form.querySelector(
                "h2"
            );

        if (titulo) {
            titulo.textContent =
                idAsambleaEdicion
                    ? `Editar asamblea #${idAsambleaEdicion}`
                    : "Información de la asamblea";
        }

        const submit =
            elementos.form.querySelector(
                '[type="submit"]'
            );

        if (submit) {
            submit.innerHTML =
                idAsambleaEdicion
                    ? '<i class="bi bi-check-lg"></i> Guardar cambios'
                    : '<i class="bi bi-check-lg"></i> Guardar asamblea';
        }
    }

    function prepararNueva() {
        idAsambleaEdicion =
            null;

        indiceConvocatoria =
            0;

        elementos.form.reset();

        elementos
            .convocatoriasContainer
            .innerHTML =
            "";

        elementos.sinConvocatorias.hidden =
            false;

        elementos.sinConvocatorias.style.display =
            "";

        crearConvocatoria();

        actualizarTextoFormulario();
    }

    async function abrirEdicion(
        asamblea
    ) {
        idAsambleaEdicion =
            Number(
                asamblea.id_asamblea
            );

        indiceConvocatoria =
            0;

        elementos.form.reset();

        elementos.idPadron.value =
            asamblea.id_padron
                ? String(
                    asamblea.id_padron
                )
                : "";

        elementos.idTipoAsamblea.value =
            String(
                asamblea.id_tipo_asamblea ||
                ""
            );

        elementos.idContextoAsamblea.value =
            asamblea.id_contexto_asamblea
                ? String(
                    asamblea.id_contexto_asamblea
                )
                : "";

        elementos.idTipoCopOperativo.value =
            asamblea.id_tipo_cop_operativo
                ? String(
                    asamblea.id_tipo_cop_operativo
                )
                : "";

        elementos.proposito.value =
            asamblea.proposito ||
            "";

        elementos.resultado.value =
            asamblea.resultado ||
            "";

        let convocatorias =
            Array.isArray(
                asamblea.convocatorias
            )
                ? asamblea.convocatorias
                : [];

        if (!convocatorias.length) {
            try {
                const cargadas =
                    await window.AsambleasAPI.listarConvocatorias(
                        idAsambleaEdicion
                    );

                convocatorias =
                    Array.isArray(cargadas)
                        ? cargadas
                        : [];

            } catch {
                convocatorias = [];
            }
        }

        elementos
            .convocatoriasContainer
            .innerHTML =
            "";

        convocatorias.forEach(
            crearConvocatoria
        );

        if (!convocatorias.length) {
            crearConvocatoria();
        }

        actualizarTextoFormulario();

        elementos.form.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    async function guardarEdicion(
        payloadBase,
        convocatorias
    ) {
        await window.AsambleasAPI.actualizar(
            idAsambleaEdicion,
            payloadBase
        );

        for (
            const convocatoria of
            convocatorias
        ) {
            const {
                id_convocatoria,
                ...payloadConvocatoria
            } =
                convocatoria;

            if (id_convocatoria) {
                await window.AsambleasAPI.actualizarConvocatoria(
                    id_convocatoria,
                    payloadConvocatoria
                );

            } else {
                await window.AsambleasAPI.crearConvocatoria(
                    idAsambleaEdicion,
                    payloadConvocatoria
                );
            }
        }
    }

    elementos.btnAgregarConvocatoria
        ?.addEventListener(
            "click",
            () => {
                if (puedeCapturar) {
                    crearConvocatoria();
                }
            }
        );

    elementos.convocatoriasContainer
        ?.addEventListener(
            "click",
            event => {
                const boton =
                    event.target.closest(
                        ".btn-eliminar-convocatoria"
                    );

                if (
                    !boton ||
                    boton.disabled
                ) {
                    return;
                }

                boton
                    .closest(
                        "[data-convocatoria]"
                    )
                    ?.remove();

                actualizarNumeracion();
            }
        );

    document.addEventListener(
        "click",
        event => {
            const boton =
                event.target.closest(
                    "[data-editar-asamblea]"
                );

            if (!boton) {
                return;
            }

            const asamblea =
                asambleas.find(
                    item =>
                        Number(
                            item.id_asamblea
                        ) ===
                        Number(
                            boton.dataset
                                .editarAsamblea
                        )
                );

            if (asamblea) {
                abrirEdicion(
                    asamblea
                ).catch(
                    error =>
                        window.ClienteAPI
                            .mostrarErrorAPI(
                                error
                            )
                );
            }
        }
    );

    elementos.form
        ?.addEventListener(
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

                const convocatorias =
                    construirConvocatorias();

                const errorConvocatorias =
                    validarConvocatorias(
                        convocatorias
                    );

                if (
                    errorConvocatorias
                ) {
                    alert(
                        errorConvocatorias
                    );

                    return;
                }

                const errorContexto =
                    validarTipoContexto();

                if (errorContexto) {
                    alert(
                        errorContexto
                    );

                    return;
                }

                const payloadBase = {
                    id_padron:
                        elementos
                            .idPadron
                            .value
                            ? Number(
                                elementos
                                    .idPadron
                                    .value
                            )
                            : null,

                    id_tipo_asamblea:
                        Number(
                            elementos
                                .idTipoAsamblea
                                .value
                        ),

                    id_contexto_asamblea:
                        elementos
                            .idContextoAsamblea
                            .value
                            ? Number(
                                elementos
                                    .idContextoAsamblea
                                    .value
                            )
                            : null,

                    id_tipo_cop_operativo:
                        elementos
                            .idTipoCopOperativo
                            .value
                            ? Number(
                                elementos
                                    .idTipoCopOperativo
                                    .value
                            )
                            : null,

                    proposito:
                        elementos
                            .proposito
                            .value
                            .trim() ||
                        null,

                    resultado:
                        elementos
                            .resultado
                            .value
                            .trim() ||
                        null
                };

                if (
                    !payloadBase
                        .id_tipo_asamblea
                ) {
                    alert(
                        "Selecciona el tipo de asamblea."
                    );

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
                    if (
                        idAsambleaEdicion
                    ) {
                        await guardarEdicion(
                            payloadBase,
                            convocatorias
                        );

                        alert(
                            `Asamblea #${idAsambleaEdicion} actualizada correctamente.`
                        );

                    } else {
                        const payloadCrear = {
                            ...payloadBase,

                            convocatorias:
                                convocatorias.map(
                                    ({
                                        id_convocatoria,
                                        ...item
                                    }) =>
                                        item
                                )
                        };

                        const creada =
                            await window.AsambleasAPI.crear(
                                idProyectoNucleo,
                                payloadCrear
                            );

                        alert(
                            `Asamblea #${creada.id_asamblea} registrada correctamente.`
                        );
                    }

                    await cargarAsambleas();

                    prepararNueva();

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

    function volver() {
        window.location.href =
            `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                idProyectoNucleo
            )}`;
    }

    elementos.btnVolver
        ?.addEventListener(
            "click",
            volver
        );

    elementos.btnCancelar
        ?.addEventListener(
            "click",
            () => {
                if (
                    idAsambleaEdicion
                ) {
                    prepararNueva();

                } else {
                    volver();
                }
            }
        );

    elementos
        .convocatoriasContainer
        .innerHTML =
        "";

    elementos.sinConvocatorias.hidden =
        false;

    elementos.sinConvocatorias.style.display =
        "";

    await cargarRol();

    await Promise.all([
        cargarContexto(),
        cargarPadrones(),
        cargarCatalogos()
    ]);

    await cargarAsambleas();

    prepararNueva();
});