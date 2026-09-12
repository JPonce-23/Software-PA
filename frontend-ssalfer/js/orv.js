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
        alert("Falta un id_proyecto_nucleo válido.");
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
        fechaFinIntegrante: document.getElementById("fechaFinIntegrante")
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

    let puedeCapturar = false;

    let estadosRegistrales = [];
    let organos = [];
    let cargos = [];
    let calidades = [];

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

        return nombre || `Persona #${integrante.id_persona}`;
    }


    /* =====================================================
                        SESIÓN
    ====================================================== */

    try {
        const sesion =
            await window.AuthAPI.obtenerSesionActual();

        const rol = sesion?.user?.rol;

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
            calidades
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
            )
        ]);

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
                orv.inicio_vigencia || "—",
                orv.fin_vigencia || "—"
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

        elementos.formularioOrv?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
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
                `Editar ORV #${orv.id_orv}`;
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

        elementos.formularioOrv?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
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
            alert(
                "La fecha de fin de vigencia no puede ser anterior al inicio."
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

                    alert(
                        "ORV actualizado correctamente."
                    );

                } else {
                    await window.OrvAPI.crear(
                        idProyectoNucleo,
                        datos
                    );

                    alert(
                        "ORV registrado correctamente."
                    );
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
                        INTEGRANTES
    ====================================================== */

    async function cargarIntegrantes() {
        if (!idOrvSeleccionado) {
            integrantes = [];
            mostrarIntegrantes();
            return;
        }

        try {
            const respuesta =
                await window.OrvAPI.listarIntegrantes(
                    idOrvSeleccionado
                );

            integrantes =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

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

        integrantes.forEach(integrante => {
            const fila =
                document.createElement("div");

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
                        Participación:
                        ${escaparHTML(
                            integrante.fecha_inicio || "—"
                        )}
                        a
                        ${escaparHTML(
                            integrante.fecha_fin || "—"
                        )}
                    </small>
                </div>

                ${
                    puedeCapturar
                        ? `
                            <button
                                type="button"
                                class="btn-secundario"
                                data-editar-integrante="${integrante.id_orv_integrante}">
                                <i class="bi bi-pencil"></i>
                                Editar
                            </button>
                        `
                        : ""
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

        elementos.formularioIntegrante?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
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

        elementos.fechaFinIntegrante.value =
            integrante.fecha_fin || "";

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

        elementos.formularioIntegrante?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function obtenerDatosIntegrante() {
        return {
            id_persona:
                Number(
                    elementos.idPersonaIntegrante.value
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
                ),

            fecha_fin:
                textoOpcional(
                    elementos.fechaFinIntegrante
                )
        };
    }

    function validarIntegrante(datos) {
        if (
            !Number.isInteger(datos.id_persona) ||
            datos.id_persona <= 0
        ) {
            alert(
                "Selecciona una persona."
            );

            return false;
        }

        if (
            !datos.id_organo ||
            !datos.id_cargo ||
            !datos.id_calidad
        ) {
            alert(
                "Selecciona órgano, cargo y calidad."
            );

            return false;
        }

        if (
            datos.fecha_inicio &&
            datos.fecha_fin &&
            datos.fecha_fin <
                datos.fecha_inicio
        ) {
            alert(
                "La fecha de fin no puede ser anterior al inicio."
            );

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
                            datos.fecha_inicio,

                        fecha_fin:
                            datos.fecha_fin
                    };

                    await window.OrvAPI.actualizarIntegrante(
                        idIntegranteEditando,
                        payload
                    );

                    alert(
                        "Integrante actualizado correctamente."
                    );

                } else {
                    await window.OrvAPI.agregarIntegrante(
                        idOrvSeleccionado,
                        datos
                    );

                    alert(
                        "Integrante registrado correctamente."
                    );
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

    /*
     * El backend actual no ofrece un listado/buscador general
     * de personas del proyecto.
     *
     * Para no dejar otro botón falso, permitimos indicar
     * una persona existente por su ID. El backend valida
     * posteriormente que exista y esté activa.
     */
    elementos.btnBuscarPersona?.addEventListener(
        "click",
        () => {
            if (idIntegranteEditando) {
                return;
            }

            const valor = prompt(
                "Indica el ID de una persona activa ya registrada:"
            );

            if (valor === null) {
                return;
            }

            const idPersona =
                Number(valor.trim());

            if (
                !Number.isInteger(idPersona) ||
                idPersona <= 0
            ) {
                alert(
                    "El ID de persona no es válido."
                );

                return;
            }

            elementos.idPersonaIntegrante.value =
                idPersona;

            elementos.personaIntegrante.value =
                `Persona #${idPersona}`;
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
        event => {
            const boton =
                event.target.closest(
                    "[data-editar-integrante]"
                );

            if (!boton) return;

            abrirEdicionIntegrante(
                boton.dataset.editarIntegrante
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