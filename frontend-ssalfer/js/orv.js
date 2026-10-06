document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros = new URLSearchParams(window.location.search);

    const idProyectoNucleo = Number(
        parametros.get("id_proyecto_nucleo")
    );

    if (
        !Number.isInteger(idProyectoNucleo) ||
        idProyectoNucleo <= 0
    ) {
        await window.SSALFER_UI.verDatos("No se pudo abrir la pantalla", { "Mensaje": "Abre este registro desde la ficha de su proyecto o núcleo." });
        window.location.href = "/dashboard.html";
        return;
    }

    const elementos = {
        enlaceNucleo: document.getElementById("enlaceNucleo"),

        btnNuevoOrv: document.getElementById("btnNuevoOrv"),
        formularioOrv: document.getElementById("formularioOrv"),
        formOrv: document.getElementById("formOrv"),
        btnCerrarOrv: document.getElementById("btnCerrarOrv"),
        btnCancelarOrv: document.getElementById("btnCancelarOrv"),

        numeroOrv: document.getElementById("numeroOrv"),
        estadoRegistral: document.getElementById("estadoRegistral"),
        inicioVigencia: document.getElementById("inicioVigencia"),
        finVigencia: document.getElementById("finVigencia"),
        estatusFuente: document.getElementById("estatusFuente"),

        orvLista: document.getElementById("orvLista"),
        sinOrv: document.getElementById("sinOrv"),
        contadorOrv: document.getElementById("contadorOrv"),

        orvSeleccionado: document.getElementById("orvSeleccionado"),
        integrantesLista: document.getElementById("integrantesLista"),
        sinIntegrantes: document.getElementById("sinIntegrantes"),
        contadorIntegrantes: document.getElementById("contadorIntegrantes"),
        accionIntegrante: document.getElementById("accionIntegrante"),

        btnAgregarIntegrante: document.getElementById("btnAgregarIntegrante"),
        formularioIntegrante: document.getElementById("formularioIntegrante"),
        formIntegrante: document.getElementById("formIntegrante"),
        btnCerrarIntegrante: document.getElementById("btnCerrarIntegrante"),
        btnCancelarIntegrante: document.getElementById("btnCancelarIntegrante"),

        personaIntegrante: document.getElementById("personaIntegrante"),
        idPersonaIntegrante: document.getElementById("idPersonaIntegrante"),
        btnBuscarPersona: document.getElementById("btnBuscarPersona"),

        organoOrv: document.getElementById("organoOrv"),
        cargoOrv: document.getElementById("cargoOrv"),
        calidadIntegrante: document.getElementById("calidadIntegrante"),
        fechaInicioIntegrante: document.getElementById("fechaInicioIntegrante"),

        formularioFinalizarIntegrante: document.getElementById("formularioFinalizarIntegrante"),
        formFinalizarIntegrante: document.getElementById("formFinalizarIntegrante"),
        descripcionFinalizarIntegrante: document.getElementById("descripcionFinalizarIntegrante"),
        fechaFinParticipacion: document.getElementById("fechaFinParticipacion"),
        tipoFinIntegrante: document.getElementById("tipoFinIntegrante"),
        detalleFinIntegrante: document.getElementById("detalleFinIntegrante"),
        btnCerrarFinalizarIntegrante: document.getElementById("btnCerrarFinalizarIntegrante"),
        btnCancelarFinalizarIntegrante: document.getElementById("btnCancelarFinalizarIntegrante")
    };

    const tituloFormularioOrv =
        elementos.formularioOrv?.querySelector("h2");

    const descripcionFormularioOrv =
        elementos.formularioOrv?.querySelector(".formulario-header p");

    const btnGuardarOrv =
        elementos.formOrv?.querySelector('[type="submit"]');

    const tituloFormularioIntegrante =
        elementos.formularioIntegrante?.querySelector("h2");

    const btnGuardarIntegrante =
        elementos.formIntegrante?.querySelector('[type="submit"]');

    let orvs = [];
    let integrantes = [];

    let idOrvSeleccionado = null;
    let idOrvEditando = null;
    let idIntegranteEditando = null;

    let idIntegranteFinalizando = null;

    let puedeCapturar = false;
    let esAdministrador = false;
    const bajasEstaSesion = new Map();

    let estadosRegistrales = [];
    let organos = [];
    let cargos = [];
    let calidades = [];

    let tiposFinIntegrante = [];
    let tipoFinPorId = new Map();

    let estadoPorId = new Map();
    let organoPorId = new Map();
    let cargoPorId = new Map();
    let calidadPorId = new Map();


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

    function textoOpcional(elemento) {
        const valor = elemento?.value?.trim();
        return valor || null;
    }

    function numeroObligatorio(elemento) {
        const numero = Number(elemento?.value);

        return Number.isInteger(numero) && numero > 0
            ? numero
            : null;
    }

    function nombreCatalogo(mapa, id) {
        if (!id) {
            return "Sin información";
        }

        const opcion = mapa.get(Number(id));

        return opcion?.nombre ||
            opcion?.codigo ||
            `#${id}`;
    }

    function llenarCatalogo(select, opciones, inicial) {
        if (!select) return;

        select.innerHTML = "";

        const optionInicial = document.createElement("option");
        optionInicial.value = "";
        optionInicial.textContent = inicial;

        select.appendChild(optionInicial);

        opciones.forEach(item => {
            const option = document.createElement("option");

            option.value = item.id_catalogo_opcion;
            option.textContent =
                item.nombre ||
                item.codigo ||
                `#${item.id_catalogo_opcion}`;

            select.appendChild(option);
        });
    }

    function mostrarFormulario(elemento, visible) {
        if (!elemento) return;

        elemento.hidden = !visible;
        elemento.style.display = visible ? "" : "none";
    }

    function nombrePersona(integrante) {
        const nombre = [
            integrante.nombre,
            integrante.apellido_paterno,
            integrante.apellido_materno
        ]
            .filter(Boolean)
            .join(" ")
            .trim();

        return nombre || "Nombre no disponible";
    }


    /* =====================================================
                        SESIÓN
    ====================================================== */

    try {
        const sesion =
            await window.AuthAPI.obtenerSesionActual();

        const rol = sesion?.user?.rol;

        esAdministrador = rol === "admin";
        puedeCapturar =
            rol === "admin" ||
            rol === "operador";

    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(error);
        return;
    }

    if (!puedeCapturar) {
        if (elementos.btnNuevoOrv) {
            elementos.btnNuevoOrv.hidden = true;
            elementos.btnNuevoOrv.style.display = "none";
        }

        if (elementos.btnAgregarIntegrante) {
            elementos.btnAgregarIntegrante.hidden = true;
            elementos.btnAgregarIntegrante.style.display = "none";
        }
    }


    /* =====================================================
                        NAVEGACIÓN
    ====================================================== */

    if (elementos.enlaceNucleo) {
        elementos.enlaceNucleo.href =
            `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                idProyectoNucleo
            )}`;
    }


    /* =====================================================
                        CATÁLOGOS
    ====================================================== */

    async function cargarCatalogos() {
        [
            estadosRegistrales,
            organos,
            cargos,
            calidades,
            tiposFinIntegrante
        ] = await Promise.all([

            window.CatalogosAPI.obtenerOperativo(
                "estado_registral_orv"
            ),

            window.CatalogosAPI.obtenerOperativo(
                "organo_orv"
            ),

            window.CatalogosAPI.obtenerOperativo(
                "cargo_orv"
            ),

            window.CatalogosAPI.obtenerOperativo(
                "calidad_integrante_orv"
            ),

            window.CatalogosAPI.obtenerOperativo(
                "tipo_fin_orv_integrante"
            )

        ]);

        tiposFinIntegrante =
            Array.isArray(tiposFinIntegrante)
                ? tiposFinIntegrante.filter(
                    item =>
                        item.codigo !==
                        "sin_clasificar"
                )
                : [];


        tipoFinPorId =
            new Map(
                tiposFinIntegrante.map(
                    item => [
                        Number(
                            item.id_catalogo_opcion
                        ),
                        item
                    ]
                )
            );


        llenarCatalogo(
            elementos.tipoFinIntegrante,
            tiposFinIntegrante,
            "Selecciona una opción"
        );


        estadosRegistrales =
            Array.isArray(estadosRegistrales)
                ? estadosRegistrales
                : [];

        organos =
            Array.isArray(organos)
                ? organos
                : [];

        cargos =
            Array.isArray(cargos)
                ? cargos
                : [];

        calidades =
            Array.isArray(calidades)
                ? calidades
                : [];

        estadoPorId = new Map(
            estadosRegistrales.map(item => [
                Number(item.id_catalogo_opcion),
                item
            ])
        );

        organoPorId = new Map(
            organos.map(item => [
                Number(item.id_catalogo_opcion),
                item
            ])
        );

        cargoPorId = new Map(
            cargos.map(item => [
                Number(item.id_catalogo_opcion),
                item
            ])
        );

        calidadPorId = new Map(
            calidades.map(item => [
                Number(item.id_catalogo_opcion),
                item
            ])
        );

        llenarCatalogo(
            elementos.estadoRegistral,
            estadosRegistrales,
            "Selecciona una opción"
        );

        llenarCatalogo(
            elementos.organoOrv,
            organos,
            "Selecciona una opción"
        );

        llenarCatalogo(
            elementos.cargoOrv,
            cargos,
            "Selecciona una opción"
        );

        llenarCatalogo(
            elementos.calidadIntegrante,
            calidades,
            "Selecciona una opción"
        );
    }


    /* =====================================================
                        ORV
    ====================================================== */

        async function cargarOrvs() {
            try {
                const respuesta =
                    await window.OrvAPI.listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

                orvs =
                    Array.isArray(respuesta)
                        ? respuesta
                        : [];

                mostrarOrvs();

            } catch (error) {
                window.ClienteAPI.mostrarErrorAPI(error);
            }
        }

    function mostrarOrvs() {
        elementos.orvLista
            ?.querySelectorAll(".orv-item")
            .forEach(elemento => elemento.remove());

        elementos.contadorOrv.textContent =
            orvs.length === 1
                ? "1 ORV"
                : `${orvs.length} ORVs`;

        elementos.sinOrv.hidden =
            orvs.length > 0;

        orvs.forEach(orv => {
            const articulo =
                document.createElement("article");

            articulo.className = "orv-item";
            articulo.dataset.orvId =
                orv.id_orv;

            articulo.dataset.numero =
                orv.numero_orv ||
                `ORV #${orv.id_orv}`;

            if (
                Number(idOrvSeleccionado) ===
                Number(orv.id_orv)
            ) {
                articulo.classList.add("seleccionado");
            }

            const vigencia = [
                window.SSALFER_FORMAT.formatearFecha(orv.inicio_vigencia),
                window.SSALFER_FORMAT.formatearFecha(orv.fin_vigencia)
            ].join(" a ");

            articulo.innerHTML = `
                <div class="orv-icono">
                    <i class="bi bi-people"></i>
                </div>

                <div class="orv-datos">
                    <h3>
                        ${escaparHTML(
                            orv.numero_orv ||
                            `ORV #${orv.id_orv}`
                        )}
                    </h3>

                    <span>
                        Número:
                        <strong>
                            ${escaparHTML(orv.numero_orv || "—")}
                        </strong>
                    </span>

                    <span>
                        Vigencia:
                        <strong>
                            ${escaparHTML(vigencia)}
                        </strong>
                    </span>

                    <span>
                        Estado registral:
                        <strong>
                            ${escaparHTML(
                                nombreCatalogo(
                                    estadoPorId,
                                    orv.id_estado_registral
                                )
                            )}
                        </strong>
                    </span>
                </div>

                <div class="orv-accion">
                    <button
                        type="button"
                        class="btn-secundario"
                        data-consultar-orv="${orv.id_orv}">
                        <i class="bi bi-eye"></i>
                        Consultar
                    </button>

                    ${
                        puedeCapturar
                            ? `
                                <button
                                    type="button"
                                    class="btn-secundario"
                                    data-editar-orv="${orv.id_orv}">
                                    <i class="bi bi-pencil"></i>
                                    Editar
                                </button>
                            `
                            : ""
                    }
                </div>
            `;

            elementos.orvLista.insertBefore(
                articulo,
                elementos.sinOrv
            );
        });
    }

    function limpiarFormularioOrv() {
        elementos.formOrv?.reset();

        idOrvEditando = null;

        if (tituloFormularioOrv) {
            tituloFormularioOrv.textContent =
                "Nuevo órgano de representación";
        }

        if (descripcionFormularioOrv) {
            descripcionFormularioOrv.textContent =
                "Registra la información del ORV correspondiente al núcleo agrario.";
        }

        if (btnGuardarOrv) {
            btnGuardarOrv.innerHTML = `
                <i class="bi bi-check-lg"></i>
                Guardar ORV
            `;
        }
    }

    function abrirNuevoOrv() {
        if (!puedeCapturar) return;

        limpiarFormularioOrv();

        mostrarFormulario(
            elementos.formularioOrv,
            true
        );

        window.SSALFER_UI?.desplazarA(elementos.formularioOrv);
    }

    function abrirEdicionOrv(id) {
        if (!puedeCapturar) return;

        const orv =
            orvs.find(
                item =>
                    Number(item.id_orv) ===
                    Number(id)
            );

        if (!orv) return;

        idOrvEditando =
            Number(orv.id_orv);

        elementos.numeroOrv.value =
            orv.numero_orv || "";

        elementos.estadoRegistral.value =
            orv.id_estado_registral || "";

        elementos.inicioVigencia.value =
            orv.inicio_vigencia || "";

        elementos.finVigencia.value =
            orv.fin_vigencia || "";

        elementos.estatusFuente.value =
            orv.estatus_fuente || "";

        if (tituloFormularioOrv) {
            tituloFormularioOrv.textContent =
                `Editar ORV · ${orv.numero_orv || "Sin número registrado"}`;
        }

        if (descripcionFormularioOrv) {
            descripcionFormularioOrv.textContent =
                "Modifica la información registrada para este ORV.";
        }

        if (btnGuardarOrv) {
            btnGuardarOrv.innerHTML = `
                <i class="bi bi-check-lg"></i>
                Guardar cambios
            `;
        }

        mostrarFormulario(
            elementos.formularioOrv,
            true
        );

        window.SSALFER_UI?.desplazarA(elementos.formularioOrv);
    }

    function obtenerDatosOrv() {

        return {

            numero_orv:
                textoOpcional(
                    elementos.numeroOrv
                ),

            inicio_vigencia:
                textoOpcional(
                    elementos.inicioVigencia
                ),

            fin_vigencia:
                textoOpcional(
                    elementos.finVigencia
                ),

            estatus_fuente:
                textoOpcional(
                    elementos.estatusFuente
                ),

            id_estado_registral:
                elementos.estadoRegistral.value
                    ? Number(
                        elementos.estadoRegistral.value
                    )
                    : null

        };

    }

    function validarOrv(datos) {

        if (
            datos.inicio_vigencia &&
            datos.fin_vigencia &&
            datos.fin_vigencia <
                datos.inicio_vigencia
        ) {

            window.SSALFER_UI?.toast(
                "La fecha de fin de vigencia no puede ser anterior al inicio.",
                { tipo: "error" }
            );

            return false;

        }

        return true;

    }

    elementos.formOrv?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            if (!puedeCapturar) return;

            const datos =
                obtenerDatosOrv();

            if (!validarOrv(datos)) {
                return;
            }

            btnGuardarOrv.disabled = true;

            try {
                if (idOrvEditando) {
                    await window.OrvAPI.actualizar(
                        idOrvEditando,
                        datos
                    );

                    window.SSALFER_UI.toast("ORV actualizado correctamente.");

                } else {
                    await window.OrvAPI.crear(
                        idProyectoNucleo,
                        datos
                    );

                    window.SSALFER_UI.toast("ORV registrado correctamente.");
                }

                limpiarFormularioOrv();

                mostrarFormulario(
                    elementos.formularioOrv,
                    false
                );

                await cargarOrvs();

            } catch (error) {
                window.ClienteAPI.mostrarErrorAPI(
                    error
                );

            } finally {
                btnGuardarOrv.disabled = false;
            }
        }
    );


    /* =====================================================
                    SELECCIÓN DEL ORV
    ====================================================== */

    async function seleccionarOrv(id) {
        idOrvSeleccionado =
            Number(id);

        const orv =
            orvs.find(
                item =>
                    Number(item.id_orv) ===
                    idOrvSeleccionado
            );

        if (!orv) return;

        mostrarOrvs();

        elementos.orvSeleccionado.innerHTML = `
            <i class="bi bi-check-circle"></i>

            <p>
                <strong>
                    ${escaparHTML(
                        orv.numero_orv ||
                        `ORV #${orv.id_orv}`
                    )}
                </strong>
                seleccionado. Aquí puedes consultar y administrar
                sus integrantes.
            </p>
        `;

        elementos.accionIntegrante.hidden =
            !puedeCapturar;

        await cargarIntegrantes();
        await cargarTramitesRanOrv();
    }

    elementos.orvLista?.addEventListener(
        "click",
        event => {

            const botonEditar =
                event.target.closest(
                    "[data-editar-orv]"
                );

            if (botonEditar) {
                event.stopPropagation();

                abrirEdicionOrv(
                    botonEditar.dataset.editarOrv
                );

                return;
            }

            const articulo =
                event.target.closest(
                    ".orv-item"
                );

            if (!articulo) return;

            seleccionarOrv(
                articulo.dataset.orvId
            );
        }
    );


    /* =====================================================
                        TRÁMITES RAN
    ====================================================== */

    function obtenerPanelRanOrv() {
        let panel =
            document.getElementById(
                "tramitesRanOrv"
            );

        if (panel) {
            return panel;
        }

        panel =
            document.createElement(
                "section"
            );

        panel.id =
            "tramitesRanOrv";

        panel.className =
            "tarjeta";

        panel.hidden =
            true;

        if (elementos.orvSeleccionado) {
            elementos.orvSeleccionado
                .insertAdjacentElement(
                    "afterend",
                    panel
                );
        }

        return panel;
    }


    async function cargarTramitesRanOrv() {
        const panel =
            obtenerPanelRanOrv();

        if (
            !panel ||
            !Number.isInteger(idOrvSeleccionado) ||
            idOrvSeleccionado <= 0
        ) {
            return;
        }

        panel.hidden =
            false;

        panel.innerHTML = `
            <div class="seccion-titulo">
                <div>
                    <i class="bi bi-file-earmark-text"></i>

                    <div>
                        <h2>
                            Trámites RAN
                        </h2>

                        <p class="descripcion-seccion">
                            Trámites ante el Registro Agrario Nacional
                            vinculados al ORV seleccionado.
                        </p>
                    </div>
                </div>
            </div>

            <p>
                Consultando trámites RAN...
            </p>
        `;

        try {
            const respuesta =
                await window.TramitesRanAPI.listarPorOrv(
                    idOrvSeleccionado
                );

            const tramites =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            const listado =
                tramites.length
                    ? tramites
                        .map(tramite => `
                            <a
                                class="btn-secundario"
                                href="/pages/fichaRan.html?id_tramite_ran=${encodeURIComponent(
                                    tramite.id_tramite_ran
                                )}">

                                <i class="bi bi-eye"></i>

                                Trámite RAN #${escaparHTML(
                                    tramite.id_tramite_ran
                                )}

                                ${
                                    tramite.referencia_expediente
                                        ? ` · ${escaparHTML(
                                            tramite.referencia_expediente
                                        )}`
                                        : ""
                                }

                            </a>
                        `)
                        .join("")
                    : `
                        <span
                            style="
                                color:#777;
                                font-size:.9rem;
                            ">
                            No hay trámites RAN registrados para este ORV.
                        </span>
                    `;

            panel.innerHTML = `
                <div class="seccion-titulo">

                    <div>
                        <i class="bi bi-file-earmark-text"></i>

                        <div>
                            <h2>
                                Trámites RAN
                            </h2>

                            <p class="descripcion-seccion">
                                Trámites ante el Registro Agrario Nacional
                                vinculados al ORV seleccionado.
                            </p>
                        </div>
                    </div>

                    <span class="contador-registros">
                        ${tramites.length} trámite(s)
                    </span>

                </div>

                <div
                    style="
                        display:flex;
                        flex-wrap:wrap;
                        align-items:center;
                        gap:10px;
                    ">

                    ${listado}

                    ${
                        puedeCapturar
                            ? `
                                <a
                                    class="btn-principal"
                                    href="/pages/tramiteRan.html?id_orv=${encodeURIComponent(
                                        idOrvSeleccionado
                                    )}&id_proyecto_nucleo=${encodeURIComponent(idProyectoNucleo)}">

                                    <i class="bi bi-plus-lg"></i>

                                    Nuevo trámite RAN

                                </a>
                            `
                            : ""
                    }

                </div>
            `;

        } catch (error) {
            console.error(
                "No fue posible consultar los trámites RAN del ORV.",
                error
            );

            panel.innerHTML = `
                <div class="seccion-titulo">
                    <div>
                        <i class="bi bi-file-earmark-text"></i>

                        <div>
                            <h2>
                                Trámites RAN
                            </h2>
                        </div>
                    </div>
                </div>

                <p style="color:#9b2c2c;">
                    No fue posible consultar los trámites RAN.
                </p>
            `;
        }
    }


    /* =====================================================
                        INTEGRANTES
    ====================================================== */

    async function cargarIntegrantes() {
        if (!idOrvSeleccionado) {
            integrantes = [];
            mostrarIntegrantes();
            return;
        }

        try {
            const idSolicitado = idOrvSeleccionado;
            const respuesta =
                await window.OrvAPI.listarIntegrantes(
                    idSolicitado
                );

            const registros = Array.isArray(respuesta) ? respuesta : [];
            const personas = new Map();
            await Promise.allSettled([...new Set(registros.filter(item => !item.nombre).map(item => item.id_persona))].map(async id => {
                personas.set(Number(id), await window.PersonasAPI.obtener(id));
            }));
            if (idSolicitado !== idOrvSeleccionado) return;

            integrantes =
                registros.map(item => {
                    const persona = personas.get(Number(item.id_persona));
                    return persona ? { ...item, nombre: persona.nombre, apellido_paterno: persona.apellido_paterno, apellido_materno: persona.apellido_materno } : item;
                });

            mostrarIntegrantes();

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(
                error
            );
        }
    }

    function mostrarIntegrantes() {
        elementos.integrantesLista
            ?.querySelectorAll(".integrante-item")
            .forEach(elemento => elemento.remove());

        elementos.contadorIntegrantes.textContent =
            integrantes.length === 1
                ? "1 integrante"
                : `${integrantes.length} integrantes`;

        elementos.sinIntegrantes.hidden =
            integrantes.length > 0;

        [...integrantes, ...[...bajasEstaSesion.values()].filter(i => Number(i.id_orv) === Number(idOrvSeleccionado))].forEach(integrante => {

            const estaFinalizado =
                Boolean(
                    integrante.fecha_fin
                );


            const fila =
                document.createElement(
                    "div"
                );

            fila.className =
                "integrante-item";

            fila.innerHTML = `
                <div>
                    <strong>
                        ${escaparHTML(
                            nombrePersona(integrante)
                        )}
                    </strong>

                    <div>
                        Órgano:
                        ${escaparHTML(
                            nombreCatalogo(
                                organoPorId,
                                integrante.id_organo
                            )
                        )}
                        · Cargo:
                        ${escaparHTML(
                            nombreCatalogo(
                                cargoPorId,
                                integrante.id_cargo
                            )
                        )}
                        · Calidad:
                        ${escaparHTML(
                            nombreCatalogo(
                                calidadPorId,
                                integrante.id_calidad
                            )
                        )}
                    </div>

                    <small>
                        Vigencia:
                        ${escaparHTML(
                            integrante.fecha_inicio || "—"
                        )}
                        a
                        ${escaparHTML(
                            integrante.fecha_fin ||
                            "Vigente"
                        )}
                    </small>


                    <span>
                        Estado:
                        <strong>
                            ${
                                integrante.activo === false ? "Registro dado de baja" : estaFinalizado
                                    ? "Finalizado"
                                    : "Vigente"
                            }
                        </strong>
                    </span>
                </div>

                ${
                    puedeCapturar && integrante.activo !== false
                        ? `
                            <div class="integrante-acciones">

                                <button
                                    type="button"
                                    class="btn-secundario"
                                    data-editar-integrante="${integrante.id_orv_integrante}">
                                    <i class="bi bi-pencil"></i>
                                    Editar
                                </button>

                                ${
                                    !integrante.fecha_fin
                                        ? `
                                            <button
                                                type="button"
                                                class="btn-secundario"
                                                data-finalizar-integrante="${integrante.id_orv_integrante}">
                                                <i class="bi bi-check-circle"></i>
                                                Finalizar participación
                                            </button>
                                        `
                                        : ""
                                }

                                ${esAdministrador ? `<button type="button" class="btn-secundario" data-baja-integrante="${integrante.id_orv_integrante}">Eliminar registro</button>` : ""}
                            </div>
                        `
                        : esAdministrador && integrante.activo === false ? `<button type="button" class="btn-secundario" data-reactivar-integrante="${integrante.id_orv_integrante}">Reactivar registro</button>` : ""
                }
            `;

            elementos.integrantesLista.insertBefore(
                fila,
                elementos.sinIntegrantes
            );
        });
    }

    function limpiarFormularioIntegrante() {
        elementos.formIntegrante?.reset();

        idIntegranteEditando = null;

        elementos.idPersonaIntegrante.value = "";
        elementos.personaIntegrante.value = "";

        elementos.btnBuscarPersona.disabled =
            false;

        if (tituloFormularioIntegrante) {
            tituloFormularioIntegrante.textContent =
                "Agregar integrante";
        }

        if (btnGuardarIntegrante) {
            btnGuardarIntegrante.innerHTML = `
                <i class="bi bi-person-plus"></i>
                Guardar integrante
            `;
        }
    }

    function abrirNuevoIntegrante() {
        if (
            !puedeCapturar ||
            !idOrvSeleccionado
        ) {
            return;
        }

        limpiarFormularioIntegrante();

        mostrarFormulario(
            elementos.formularioIntegrante,
            true
        );

        window.SSALFER_UI?.desplazarA(elementos.formularioIntegrante);
    }

    function abrirEdicionIntegrante(id) {
        if (!puedeCapturar) return;

        const integrante =
            integrantes.find(
                item =>
                    Number(
                        item.id_orv_integrante
                    ) === Number(id)
            );

        if (!integrante) return;

        idIntegranteEditando =
            Number(
                integrante.id_orv_integrante
            );

        elementos.idPersonaIntegrante.value =
            integrante.id_persona;

        elementos.personaIntegrante.value =
            nombrePersona(integrante);

        elementos.organoOrv.value =
            integrante.id_organo || "";

        elementos.cargoOrv.value =
            integrante.id_cargo || "";

        elementos.calidadIntegrante.value =
            integrante.id_calidad || "";

        elementos.fechaInicioIntegrante.value =
            integrante.fecha_inicio || "";

        /*
         * El backend no permite cambiar la persona
         * de un integrante existente.
         */
        elementos.btnBuscarPersona.disabled =
            true;

        if (tituloFormularioIntegrante) {
            tituloFormularioIntegrante.textContent =
                `Editar integrante #${idIntegranteEditando}`;
        }

        if (btnGuardarIntegrante) {
            btnGuardarIntegrante.innerHTML = `
                <i class="bi bi-check-lg"></i>
                Guardar cambios
            `;
        }

        mostrarFormulario(
            elementos.formularioIntegrante,
            true
        );

        window.SSALFER_UI?.desplazarA(elementos.formularioIntegrante);
    }

    function obtenerDatosIntegrante() {

        return {

            id_persona:
                Number(
                    elementos
                        .idPersonaIntegrante
                        .value
                ),

            id_organo:
                numeroObligatorio(
                    elementos.organoOrv
                ),

            id_cargo:
                numeroObligatorio(
                    elementos.cargoOrv
                ),

            id_calidad:
                numeroObligatorio(
                    elementos.calidadIntegrante
                ),

            fecha_inicio:
                textoOpcional(
                    elementos.fechaInicioIntegrante
                )

        };

    }

    function validarIntegrante(datos) {
        if (
            !Number.isInteger(datos.id_persona) ||
            datos.id_persona <= 0
        ) {
            window.SSALFER_UI.toast("Selecciona una persona.", { tipo: "error" });

            return false;
        }

        if (
            !datos.id_organo ||
            !datos.id_cargo ||
            !datos.id_calidad
        ) {
            window.SSALFER_UI.toast("Selecciona órgano, cargo y calidad.", { tipo: "error" });

            return false;
        }

        return true;
    }

    elementos.formIntegrante?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            if (
                !puedeCapturar ||
                !idOrvSeleccionado
            ) {
                return;
            }

            const datos =
                obtenerDatosIntegrante();

            if (!validarIntegrante(datos)) {
                return;
            }

            btnGuardarIntegrante.disabled =
                true;

            try {
                if (idIntegranteEditando) {
                    const payload = {
                        id_organo:
                            datos.id_organo,

                        id_cargo:
                            datos.id_cargo,

                        id_calidad:
                            datos.id_calidad,

                        fecha_inicio:
                            datos.fecha_inicio
                    };

                    await window.OrvAPI.actualizarIntegrante(
                        idIntegranteEditando,
                        payload
                    );

                    window.SSALFER_UI.toast("Integrante actualizado correctamente.");

                } else {
                    await window.OrvAPI.agregarIntegrante(
                        idOrvSeleccionado,
                        datos
                    );

                    window.SSALFER_UI.toast("Integrante registrado correctamente.");
                }

                limpiarFormularioIntegrante();

                mostrarFormulario(
                    elementos.formularioIntegrante,
                    false
                );

                await cargarIntegrantes();

            } catch (error) {
                window.ClienteAPI.mostrarErrorAPI(
                    error
                );

            } finally {
                btnGuardarIntegrante.disabled =
                    false;
            }
        }
    );


    /* =====================================================
                    SELECCIONAR PERSONA
    ====================================================== */

    elementos.btnBuscarPersona?.addEventListener("click", async () => {
        if (idIntegranteEditando) return;
        elementos.btnBuscarPersona.disabled = true;
        try {
            const persona = await window.SSALFER_DIRECTORIO.seleccionar(Number(idProyectoNucleo));
            if (!persona || idIntegranteEditando || elementos.formularioIntegrante.hidden) return;
            elementos.idPersonaIntegrante.value = persona.id_persona;
            elementos.personaIntegrante.value = nombrePersona(persona);
        } catch (error) { window.ClienteAPI.mostrarErrorAPI(error); }
        finally { elementos.btnBuscarPersona.disabled = false; }
    });

    function limpiarFormularioFinalizarIntegrante() {

        elementos
            .formFinalizarIntegrante
            ?.reset();


        idIntegranteFinalizando =
            null;

    }


    function abrirFinalizarIntegrante(
        id
    ) {

        if (!puedeCapturar) {

            return;

        }


        const integrante =
            integrantes.find(
                item =>
                    Number(
                        item.id_orv_integrante
                    ) ===
                    Number(id)
            );


        if (!integrante) {

            return;

        }


        if (integrante.fecha_fin) {

            window.SSALFER_UI.toast("La participación de este integrante ya está finalizada.", { tipo: "error" });

            return;

        }


        idIntegranteFinalizando =
            Number(
                integrante.id_orv_integrante
            );


        if (
            elementos
                .descripcionFinalizarIntegrante
        ) {

            elementos
                .descripcionFinalizarIntegrante
                .textContent =
                `Finaliza la participación de ${nombrePersona(
                    integrante
                )}.`;

        }


        mostrarFormulario(
            elementos
                .formularioFinalizarIntegrante,
            true
        );


        window.SSALFER_UI?.desplazarA(elementos.formularioFinalizarIntegrante);

    }



    elementos
    .formFinalizarIntegrante
    ?.addEventListener(
        "submit",
        async event => {

            event.preventDefault();


            if (
                !puedeCapturar ||
                !idIntegranteFinalizando
            ) {

                return;

            }


            const fechaFin =
                elementos
                    .fechaFinParticipacion
                    ?.value;


            const idTipoFin =
                Number(
                    elementos
                        .tipoFinIntegrante
                        ?.value
                );


            const detalle =
                elementos
                    .detalleFinIntegrante
                    ?.value
                    .trim() ||
                null;


            if (!fechaFin) {

                window.SSALFER_UI.toast("Indica la fecha de finalización.", { tipo: "error" });

                return;

            }


            if (
                !Number.isInteger(
                    idTipoFin
                ) ||
                idTipoFin <= 0
            ) {

                window.SSALFER_UI.toast("Selecciona el motivo de finalización.", { tipo: "error" });

                return;

            }


            const tipoFin =
                tipoFinPorId.get(
                    idTipoFin
                );


            if (
                tipoFin?.codigo ===
                    "otro" &&
                !detalle
            ) {

                window.SSALFER_UI.toast('El motivo "Otro" requiere un detalle.', { tipo: "error" });

                return;

            }


            const integrante =
                integrantes.find(
                    item =>
                        Number(
                            item.id_orv_integrante
                        ) ===
                        idIntegranteFinalizando
                );


            if (
                integrante?.fecha_inicio &&
                fechaFin <
                    integrante.fecha_inicio
            ) {

                window.SSALFER_UI.toast("La fecha de finalización no puede ser anterior a la fecha de inicio.", { tipo: "error" });

                return;

            }


            const botonGuardar =
                elementos
                    .formFinalizarIntegrante
                    ?.querySelector(
                        '[type="submit"]'
                    );


            if (botonGuardar) {

                botonGuardar.disabled =
                    true;

            }


            try {

                await window.OrvAPI
                    .finalizarIntegrante(
                        idIntegranteFinalizando,
                        {
                            fecha_fin:
                                fechaFin,

                            id_tipo_fin:
                                idTipoFin,

                            detalle_fin:
                                detalle
                        }
                    );


                window.SSALFER_UI.toast("Participación finalizada correctamente.");


                limpiarFormularioFinalizarIntegrante();


                mostrarFormulario(
                    elementos
                        .formularioFinalizarIntegrante,
                    false
                );


                await cargarIntegrantes();

            } catch (error) {

                window.ClienteAPI
                    .mostrarErrorAPI(
                        error
                    );

            } finally {

                if (botonGuardar) {

                    botonGuardar.disabled =
                        false;

                }

            }

        }
    );


    elementos
    .btnCerrarFinalizarIntegrante
    ?.addEventListener(
        "click",
        () => {

            limpiarFormularioFinalizarIntegrante();

            mostrarFormulario(
                elementos
                    .formularioFinalizarIntegrante,
                false
            );

        }
    );


elementos
    .btnCancelarFinalizarIntegrante
    ?.addEventListener(
        "click",
        () => {

            limpiarFormularioFinalizarIntegrante();

            mostrarFormulario(
                elementos
                    .formularioFinalizarIntegrante,
                false
            );

        }
    );


    /* =====================================================
                        BOTONES
    ====================================================== */

    elementos.btnNuevoOrv?.addEventListener(
        "click",
        abrirNuevoOrv
    );

    elementos.btnCerrarOrv?.addEventListener(
        "click",
        () => {
            limpiarFormularioOrv();

            mostrarFormulario(
                elementos.formularioOrv,
                false
            );
        }
    );

    elementos.btnCancelarOrv?.addEventListener(
        "click",
        () => {
            limpiarFormularioOrv();

            mostrarFormulario(
                elementos.formularioOrv,
                false
            );
        }
    );

    elementos.btnAgregarIntegrante?.addEventListener(
        "click",
        abrirNuevoIntegrante
    );

    elementos.btnCerrarIntegrante?.addEventListener(
        "click",
        () => {
            limpiarFormularioIntegrante();

            mostrarFormulario(
                elementos.formularioIntegrante,
                false
            );
        }
    );

    elementos.btnCancelarIntegrante?.addEventListener(
        "click",
        () => {
            limpiarFormularioIntegrante();

            mostrarFormulario(
                elementos.formularioIntegrante,
                false
            );
        }
    );

    elementos.integrantesLista?.addEventListener(
        "click",
        async event => {
            const ciclo = event.target.closest("[data-baja-integrante], [data-reactivar-integrante]");
            if (ciclo && esAdministrador && !ciclo.disabled) {
                ciclo.disabled = true;
                try {
                    const id = Number(ciclo.dataset.bajaIntegrante || ciclo.dataset.reactivarIntegrante);
                    if (ciclo.dataset.bajaIntegrante) {
                        const integrante = integrantes.find(i => Number(i.id_orv_integrante) === id);
                        if (await window.SSALFER_GESTION.baja(`el registro de ${nombrePersona(integrante)}. Esto es una baja administrativa y no finaliza su vigencia de participación`, motivo => window.OrvAPI.eliminarIntegrante(id, motivo))) bajasEstaSesion.set(id, { ...integrante, activo: false });
                    } else if (await window.SSALFER_UI.confirmar("Se restaurará el registro conservando sus fechas de participación.", "Reactivar integrante")) {
                        await window.OrvAPI.reactivarIntegrante(id); bajasEstaSesion.delete(id); window.SSALFER_UI.toast("Registro reactivado.");
                    }
                    await cargarIntegrantes();
                } catch (error) { window.ClienteAPI.mostrarErrorAPI(error); }
                finally { ciclo.disabled = false; }
                return;
            }


            /* =================================================
                        FINALIZAR INTEGRANTE
            ================================================== */

            const botonFinalizar =
                event.target.closest(
                    "[data-finalizar-integrante]"
                );


            if (botonFinalizar) {

                abrirFinalizarIntegrante(
                    botonFinalizar
                        .dataset
                        .finalizarIntegrante
                );


                return;

            }


            /* =================================================
                        EDITAR INTEGRANTE
            ================================================== */

            const botonEditar =
                event.target.closest(
                    "[data-editar-integrante]"
                );


            if (!botonEditar) {

                return;

            }


            abrirEdicionIntegrante(
                botonEditar
                    .dataset
                    .editarIntegrante
            );

        }
    );


    /* =====================================================
                        INICIALIZACIÓN
    ====================================================== */

    elementos.accionIntegrante.hidden = true;

    if (elementos.btnBuscarPersona) {
        elementos.btnBuscarPersona.innerHTML = `
            <i class="bi bi-person-check"></i>
            Indicar persona
        `;
    }

    try {
        await cargarCatalogos();
        await cargarOrvs();

    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(error);
    }
});
