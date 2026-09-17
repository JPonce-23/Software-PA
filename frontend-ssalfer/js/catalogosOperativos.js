document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    /*
     * Son sugerencias conocidas del backend actual.
     *
     * El input NO está limitado a esta lista:
     * si posteriormente el backend agrega otro tipo,
     * se puede escribir manualmente.
     */
    const TIPOS_CONOCIDOS = [
        "calidad_compareciente_convenio",
        "calidad_integrante_orv",
        "cargo_orv",
        "contexto_asamblea",
        "destino_superficie",
        "estado_registral_orv",
        "estado_requisito_documental",
        "motivo_no_afecta_tuc",
        "motivo_seguimiento",
        "organo_orv",
        "residencia",
        "resultado_convocatoria",
        "tipo_acreditacion_compareciente_colectivo",
        "tipo_acreditacion_derecho_individual",
        "tipo_asamblea",
        "tipo_cop_operativo",
        "tipo_evento_fifonafe",
        "tipo_evento_ran",
        "tipo_evento_seguimiento",
        "tipo_gestion",
        "tipo_tenencia",
        "tipo_tierra",
        "tipo_titularidad_unidad"
    ];

    const estado = {
        opciones: [],
        tipoActual: "",
        cargando: false
    };

    const el = {
        error:
            document.getElementById("catalogosError"),

        ok:
            document.getElementById("catalogosOk"),

        tipo:
            document.getElementById("tipoCatalogo"),

        tiposDatalist:
            document.getElementById("tiposCatalogo"),

        incluirInactivos:
            document.getElementById("incluirInactivos"),

        busqueda:
            document.getElementById("busquedaCatalogo"),

        btnCargar:
            document.getElementById("btnCargarCatalogo"),

        btnNuevo:
            document.getElementById("btnNuevoCatalogo"),

        resumen:
            document.getElementById("catalogoResumen"),

        tabla:
            document.getElementById("tablaCatalogos"),

        modal:
            document.getElementById("modalCatalogo"),

        modalTitulo:
            document.getElementById("modalCatalogoTitulo"),

        form:
            document.getElementById("formCatalogo"),

        formError:
            document.getElementById("catalogoModalError"),

        modo:
            document.getElementById("catalogoModo"),

        id:
            document.getElementById("catalogoId"),

        campoTipo:
            document.getElementById("campoTipoCatalogo"),

        campoCodigo:
            document.getElementById("campoCodigoCatalogo"),

        nombre:
            document.getElementById("catalogoNombre"),

        descripcion:
            document.getElementById("catalogoDescripcion"),

        orden:
            document.getElementById("catalogoOrden"),

        fuente:
            document.getElementById("catalogoFuente"),

        vigenciaInicio:
            document.getElementById("catalogoVigenciaInicio"),

        vigenciaFin:
            document.getElementById("catalogoVigenciaFin"),

        observaciones:
            document.getElementById("catalogoObservaciones"),

        observacionesAyuda:
            document.getElementById(
                "catalogoObservacionesAyuda"
            ),

        btnGuardar:
            document.getElementById(
                "btnGuardarCatalogo"
            ),

        modalBaja:
            document.getElementById(
                "modalBajaCatalogo"
            ),

        formBaja:
            document.getElementById(
                "formBajaCatalogo"
            ),

        bajaError:
            document.getElementById(
                "bajaCatalogoError"
            ),

        bajaId:
            document.getElementById(
                "bajaCatalogoId"
            ),

        bajaNombre:
            document.getElementById(
                "bajaCatalogoNombre"
            ),

        bajaMotivo:
            document.getElementById(
                "bajaCatalogoMotivo"
            ),

        btnConfirmarBaja:
            document.getElementById(
                "btnConfirmarBajaCatalogo"
            )
    };


    function texto(valor, fallback = "—") {
        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return fallback;
        }

        return String(valor);
    }


    function valorNullable(valor) {
        const limpio =
            String(valor ?? "").trim();

        return limpio === ""
            ? null
            : limpio;
    }


    function formatearFecha(fecha) {
        if (!fecha) {
            return "—";
        }

        const partes =
            String(fecha).split("-");

        if (partes.length !== 3) {
            return String(fecha);
        }

        return (
            `${partes[2]}/${partes[1]}/${partes[0]}`
        );
    }


    function ocultarMensajes() {
        el.error.hidden = true;
        el.ok.hidden = true;
    }


    function mostrarExito(mensaje) {
        el.error.hidden = true;

        el.ok.textContent = mensaje;
        el.ok.hidden = false;
    }


    function mostrarError(
        error,
        contenedor = el.error
    ) {
        if (contenedor !== el.error) {
            contenedor.hidden = true;
        } else {
            el.ok.hidden = true;
        }

        window.ClienteAPI.mostrarErrorAPI(
            error,
            contenedor
        );
    }


    function renderTiposConocidos() {
        const fragmento =
            document.createDocumentFragment();

        for (const tipo of TIPOS_CONOCIDOS) {
            const opcion =
                document.createElement("option");

            opcion.value = tipo;

            fragmento.appendChild(opcion);
        }

        el.tiposDatalist.replaceChildren(
            fragmento
        );
    }


    function actualizarResumen() {
        const total =
            estado.opciones.length;

        const activas =
            estado.opciones.filter(
                opcion => opcion.activo
            ).length;

        const inactivas =
            total - activas;

        if (!estado.tipoActual) {
            el.resumen.textContent =
                "Selecciona un tipo de catálogo para consultar sus opciones.";

            return;
        }

        el.resumen.textContent =
            `${estado.tipoActual}: ` +
            `${total} opción(es) · ` +
            `${activas} activa(s) · ` +
            `${inactivas} inactiva(s)`;
    }


    function crearCelda(
        valor,
        clase = ""
    ) {
        const celda =
            document.createElement("td");

        if (clase) {
            celda.className = clase;
        }

        celda.textContent =
            texto(valor);

        return celda;
    }


    function crearBoton(
        textoBoton,
        accion,
        id,
        variante = "secundario"
    ) {
        const boton =
            document.createElement("button");

        boton.type = "button";

        boton.className =
            `catalogos-btn catalogos-btn-${variante}`;

        boton.dataset.accion =
            accion;

        boton.dataset.idCatalogo =
            String(id);

        boton.textContent =
            textoBoton;

        return boton;
    }


    function opcionesFiltradas() {
        const termino =
            el.busqueda.value
                .trim()
                .toLocaleLowerCase("es-MX");

        if (!termino) {
            return estado.opciones;
        }

        return estado.opciones.filter(
            opcion => {
                const contenido = [
                    opcion.id_catalogo_opcion,
                    opcion.codigo,
                    opcion.nombre,
                    opcion.descripcion,
                    opcion.fuente,
                    opcion.orden,
                    opcion.activo
                        ? "activo"
                        : "inactivo"
                ]
                    .filter(
                        valor =>
                            valor !== null &&
                            valor !== undefined
                    )
                    .join(" ")
                    .toLocaleLowerCase("es-MX");

                return contenido.includes(
                    termino
                );
            }
        );
    }


    function renderTabla() {
        const opciones =
            opcionesFiltradas();

        el.tabla.replaceChildren();

        if (opciones.length === 0) {
            const fila =
                document.createElement("tr");

            const celda =
                document.createElement("td");

            celda.colSpan = 9;
            celda.className =
                "catalogos-tabla-estado";

            celda.textContent =
                el.busqueda.value.trim()
                    ? "No hay coincidencias con la búsqueda."
                    : "No hay opciones para este tipo de catálogo.";

            fila.appendChild(celda);

            el.tabla.appendChild(fila);

            return;
        }

        for (const opcion of opciones) {
            const fila =
                document.createElement("tr");

            if (!opcion.activo) {
                fila.classList.add(
                    "catalogos-fila-inactiva"
                );
            }

            fila.appendChild(
                crearCelda(
                    opcion.id_catalogo_opcion,
                    "catalogos-id"
                )
            );


            const tdCodigo =
                document.createElement("td");

            const codigo =
                document.createElement("code");

            codigo.textContent =
                texto(opcion.codigo);

            tdCodigo.appendChild(codigo);

            fila.appendChild(tdCodigo);


            fila.appendChild(
                crearCelda(opcion.nombre)
            );

            fila.appendChild(
                crearCelda(opcion.descripcion)
            );

            fila.appendChild(
                crearCelda(opcion.orden)
            );

            fila.appendChild(
                crearCelda(opcion.fuente)
            );


            const tdVigencia =
                document.createElement("td");

            const inicio =
                formatearFecha(
                    opcion.vigencia_inicio
                );

            const fin =
                formatearFecha(
                    opcion.vigencia_fin
                );

            tdVigencia.textContent =
                `${inicio} — ${fin}`;

            fila.appendChild(tdVigencia);


            const tdEstado =
                document.createElement("td");

            const badge =
                document.createElement("span");

            badge.className =
                opcion.activo
                    ? "catalogos-badge catalogos-badge-activo"
                    : "catalogos-badge catalogos-badge-inactivo";

            badge.textContent =
                opcion.activo
                    ? "Activo"
                    : "Inactivo";

            tdEstado.appendChild(badge);


            if (
                !opcion.activo &&
                opcion.motivo_baja
            ) {
                const motivo =
                    document.createElement("small");

                motivo.className =
                    "catalogos-motivo-baja";

                motivo.textContent =
                    opcion.motivo_baja;

                tdEstado.appendChild(motivo);
            }

            fila.appendChild(tdEstado);


            const tdAcciones =
                document.createElement("td");

            const acciones =
                document.createElement("div");

            acciones.className =
                "catalogos-acciones";


            acciones.appendChild(
                crearBoton(
                    "Editar",
                    "editar",
                    opcion.id_catalogo_opcion
                )
            );


            if (opcion.activo) {
                acciones.appendChild(
                    crearBoton(
                        "Desactivar",
                        "desactivar",
                        opcion.id_catalogo_opcion,
                        "peligro"
                    )
                );
            }


            tdAcciones.appendChild(
                acciones
            );

            fila.appendChild(
                tdAcciones
            );

            el.tabla.appendChild(
                fila
            );
        }
    }


    async function cargarCatalogo({
        conservarMensaje = false
    } = {}) {

        const tipo =
            el.tipo.value.trim();

        if (!tipo) {
            el.error.textContent =
                "Indica el tipo de catálogo que deseas consultar.";

            el.error.hidden = false;

            el.tipo.focus();

            return;
        }

        if (estado.cargando) {
            return;
        }

        estado.cargando = true;

        el.btnCargar.disabled = true;
        el.btnNuevo.disabled = true;

        if (!conservarMensaje) {
            ocultarMensajes();
        }

        el.tabla.innerHTML = `
            <tr>
                <td
                    colspan="9"
                    class="catalogos-tabla-estado">
                    Cargando catálogo...
                </td>
            </tr>
        `;

        try {
            const respuesta =
                await window
                    .CatalogosOperativosAPI
                    .listar(
                        tipo,
                        {
                            incluirInactivos:
                                el.incluirInactivos.checked
                        }
                    );

            estado.opciones =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            estado.tipoActual =
                tipo;

            localStorage.setItem(
                "ssalferTipoCatalogo",
                tipo
            );

            el.busqueda.value = "";

            actualizarResumen();

            renderTabla();

        } catch (error) {
            estado.opciones = [];
            estado.tipoActual = "";

            actualizarResumen();

            el.tabla.innerHTML = `
                <tr>
                    <td
                        colspan="9"
                        class="catalogos-tabla-estado">
                        No fue posible cargar el catálogo.
                    </td>
                </tr>
            `;

            mostrarError(error);

        } finally {
            estado.cargando = false;

            el.btnCargar.disabled = false;
            el.btnNuevo.disabled = false;
        }
    }


    function cerrarModal(modal) {
        modal.hidden = true;

        if (
            el.modal.hidden &&
            el.modalBaja.hidden
        ) {
            document.body.classList.remove(
                "catalogos-modal-abierto"
            );
        }
    }


    function abrirModal(modal) {
        modal.hidden = false;

        document.body.classList.add(
            "catalogos-modal-abierto"
        );
    }


    function abrirCrear() {
        ocultarMensajes();

        el.form.reset();
        el.formError.hidden = true;

        el.modo.value = "crear";
        el.id.value = "";

        el.modalTitulo.textContent =
            "Nueva opción de catálogo";

        el.btnGuardar.textContent =
            "Crear opción";

        el.campoTipo.readOnly = false;
        el.campoCodigo.readOnly = false;
        el.observaciones.readOnly = false;

        el.campoTipo.value =
            el.tipo.value.trim();

        el.orden.value = "0";

        el.observacionesAyuda.textContent =
            "Las observaciones se almacenan al crear la opción.";

        abrirModal(el.modal);

        if (el.campoTipo.value) {
            el.campoCodigo.focus();
        } else {
            el.campoTipo.focus();
        }
    }


    function abrirEditar(opcion) {
        ocultarMensajes();

        el.form.reset();
        el.formError.hidden = true;

        el.modo.value = "editar";

        el.id.value =
            String(
                opcion.id_catalogo_opcion
            );

        el.modalTitulo.textContent =
            "Editar opción de catálogo";

        el.btnGuardar.textContent =
            "Guardar cambios";


        el.campoTipo.value =
            opcion.tipo_catalogo ||
            estado.tipoActual;

        el.campoCodigo.value =
            opcion.codigo || "";

        el.nombre.value =
            opcion.nombre || "";

        el.descripcion.value =
            opcion.descripcion || "";

        el.orden.value =
            String(
                opcion.orden ?? 0
            );

        el.fuente.value =
            opcion.fuente || "";

        el.vigenciaInicio.value =
            opcion.vigencia_inicio || "";

        el.vigenciaFin.value =
            opcion.vigencia_fin || "";

        el.observaciones.value =
            opcion.observaciones || "";


        /*
         * El backend no permite modificar
         * tipo_catalogo ni codigo.
         */
        el.campoTipo.readOnly = true;
        el.campoCodigo.readOnly = true;


        /*
         * El schema acepta observaciones,
         * pero el servicio actual las excluye
         * del PATCH.
         */
        el.observaciones.readOnly = true;

        el.observacionesAyuda.textContent =
            "Solo lectura: el servicio actual del backend no persiste cambios de observaciones en PATCH.";


        abrirModal(el.modal);

        el.nombre.focus();
    }


    function abrirBaja(opcion) {
        ocultarMensajes();

        el.formBaja.reset();

        el.bajaError.hidden = true;

        el.bajaId.value =
            String(
                opcion.id_catalogo_opcion
            );

        el.bajaNombre.textContent =
            `${opcion.nombre} (${opcion.codigo})`;

        abrirModal(
            el.modalBaja
        );

        el.bajaMotivo.focus();
    }


    function buscarOpcion(id) {
        return (
            estado.opciones.find(
                opcion =>
                    Number(
                        opcion.id_catalogo_opcion
                    ) ===
                    Number(id)
            ) || null
        );
    }


    function validarVigencia() {
        const inicio =
            el.vigenciaInicio.value;

        const fin =
            el.vigenciaFin.value;

        if (
            inicio &&
            fin &&
            fin < inicio
        ) {
            throw new Error(
                "La vigencia final no puede ser anterior a la vigencia inicial."
            );
        }
    }


    renderTiposConocidos();

    el.tipo.value =
        localStorage.getItem(
            "ssalferTipoCatalogo"
        ) ||
        "tipo_tenencia";


    try {
        const sesion =
            await window.AuthAPI
                .requerirSesion();

        if (!sesion) {
            return;
        }

        await cargarCatalogo();

    } catch (error) {
        mostrarError(error);
    }


    el.btnCargar.addEventListener(
        "click",
        () => cargarCatalogo()
    );


    el.btnNuevo.addEventListener(
        "click",
        abrirCrear
    );


    el.incluirInactivos.addEventListener(
        "change",
        () => cargarCatalogo()
    );


    el.busqueda.addEventListener(
        "input",
        renderTabla
    );


    el.tipo.addEventListener(
        "keydown",
        event => {
            if (event.key === "Enter") {
                event.preventDefault();

                cargarCatalogo();
            }
        }
    );


    el.form.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            ocultarMensajes();

            el.formError.hidden = true;

            try {
                validarVigencia();

                const modo =
                    el.modo.value;

                const payloadComun = {
                    nombre:
                        el.nombre.value.trim(),

                    descripcion:
                        valorNullable(
                            el.descripcion.value
                        ),

                    orden:
                        Number(
                            el.orden.value || 0
                        ),

                    fuente:
                        valorNullable(
                            el.fuente.value
                        ),

                    vigencia_inicio:
                        valorNullable(
                            el.vigenciaInicio.value
                        ),

                    vigencia_fin:
                        valorNullable(
                            el.vigenciaFin.value
                        )
                };


                el.btnGuardar.disabled =
                    true;


                if (modo === "crear") {
                    const tipoCatalogo =
                        el.campoTipo.value.trim();

                    const payload = {
                        tipo_catalogo:
                            tipoCatalogo,

                        codigo:
                            el.campoCodigo
                                .value
                                .trim(),

                        ...payloadComun,

                        observaciones:
                            valorNullable(
                                el.observaciones.value
                            )
                    };


                    await window
                        .CatalogosOperativosAPI
                        .crear(payload);


                    el.tipo.value =
                        tipoCatalogo;

                    cerrarModal(
                        el.modal
                    );


                    await cargarCatalogo({
                        conservarMensaje: true
                    });


                    mostrarExito(
                        "Opción de catálogo creada correctamente."
                    );

                } else {
                    const idCatalogo =
                        Number(
                            el.id.value
                        );

                    /*
                     * No mandamos:
                     * - tipo_catalogo
                     * - codigo
                     * - observaciones
                     *
                     * porque el backend actual
                     * no los modifica vía PATCH.
                     */
                    await window
                        .CatalogosOperativosAPI
                        .actualizar(
                            idCatalogo,
                            payloadComun
                        );


                    cerrarModal(
                        el.modal
                    );


                    await cargarCatalogo({
                        conservarMensaje: true
                    });


                    mostrarExito(
                        "Opción de catálogo actualizada correctamente."
                    );
                }

            } catch (error) {
                mostrarError(
                    error,
                    el.formError
                );

            } finally {
                el.btnGuardar.disabled =
                    false;
            }
        }
    );


    el.tabla.addEventListener(
        "click",
        event => {
            const boton =
                event.target.closest(
                    "button[data-accion][data-id-catalogo]"
                );

            if (!boton) {
                return;
            }

            const opcion =
                buscarOpcion(
                    boton.dataset.idCatalogo
                );

            if (!opcion) {
                return;
            }

            if (
                boton.dataset.accion ===
                "editar"
            ) {
                abrirEditar(opcion);

            } else if (
                boton.dataset.accion ===
                "desactivar"
            ) {
                abrirBaja(opcion);
            }
        }
    );


    el.formBaja.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            ocultarMensajes();

            el.bajaError.hidden = true;

            const idCatalogo =
                Number(
                    el.bajaId.value
                );

            const motivo =
                el.bajaMotivo
                    .value
                    .trim();


            if (!motivo) {
                el.bajaError.textContent =
                    "Indica el motivo de la desactivación.";

                el.bajaError.hidden =
                    false;

                return;
            }


            el.btnConfirmarBaja.disabled =
                true;


            try {
                await window
                    .CatalogosOperativosAPI
                    .desactivar(
                        idCatalogo,
                        motivo
                    );


                cerrarModal(
                    el.modalBaja
                );


                await cargarCatalogo({
                    conservarMensaje: true
                });


                mostrarExito(
                    "Opción desactivada correctamente."
                );

            } catch (error) {
                mostrarError(
                    error,
                    el.bajaError
                );

            } finally {
                el.btnConfirmarBaja.disabled =
                    false;
            }
        }
    );


    document
        .querySelectorAll(
            "[data-cerrar-catalogos-modal]"
        )
        .forEach(
            boton => {
                boton.addEventListener(
                    "click",
                    () => {
                        const destino =
                            boton.dataset
                                .cerrarCatalogosModal;

                        cerrarModal(
                            destino === "baja"
                                ? el.modalBaja
                                : el.modal
                        );
                    }
                );
            }
        );


    el.modal.addEventListener(
        "click",
        event => {
            if (
                event.target === el.modal
            ) {
                cerrarModal(el.modal);
            }
        }
    );


    el.modalBaja.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                el.modalBaja
            ) {
                cerrarModal(
                    el.modalBaja
                );
            }
        }
    );


    document.addEventListener(
        "keydown",
        event => {
            if (event.key !== "Escape") {
                return;
            }

            if (!el.modalBaja.hidden) {
                cerrarModal(
                    el.modalBaja
                );

                return;
            }

            if (!el.modal.hidden) {
                cerrarModal(
                    el.modal
                );
            }
        }
    );
});