document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const estado = {
        pestana: "cambios",

        cambios: {
            skip: 0,
            limit: 50,
            total: 0,
            items: [],
            cargando: false
        },

        accesos: {
            skip: 0,
            limit: 50,
            total: 0,
            items: [],
            cargando: false
        }
    };


    const el = {
        error:
            document.getElementById("auditoriaError"),

        tabs:
            Array.from(
                document.querySelectorAll(
                    "[data-auditoria-tab]"
                )
            ),

        panelCambios:
            document.getElementById("panelCambios"),

        panelAccesos:
            document.getElementById("panelAccesos"),


        formCambios:
            document.getElementById("formFiltrosCambios"),

        tablaCambios:
            document.getElementById("tablaCambios"),

        totalCambios:
            document.getElementById("totalCambios"),

        btnLimpiarCambios:
            document.getElementById("btnLimpiarCambios"),

        btnAnteriorCambios:
            document.getElementById("btnAnteriorCambios"),

        btnSiguienteCambios:
            document.getElementById("btnSiguienteCambios"),

        paginaCambios:
            document.getElementById("paginaCambios"),

        limiteCambios:
            document.getElementById("limiteCambios"),


        formAccesos:
            document.getElementById("formFiltrosAccesos"),

        tablaAccesos:
            document.getElementById("tablaAccesos"),

        totalAccesos:
            document.getElementById("totalAccesos"),

        btnLimpiarAccesos:
            document.getElementById("btnLimpiarAccesos"),

        btnAnteriorAccesos:
            document.getElementById("btnAnteriorAccesos"),

        btnSiguienteAccesos:
            document.getElementById("btnSiguienteAccesos"),

        paginaAccesos:
            document.getElementById("paginaAccesos"),

        limiteAccesos:
            document.getElementById("limiteAccesos"),


        modal:
            document.getElementById(
                "modalAuditoriaDetalle"
            ),

        modalTitulo:
            document.getElementById(
                "modalAuditoriaTitulo"
            ),

        modalSubtitulo:
            document.getElementById(
                "modalAuditoriaSubtitulo"
            ),

        modalContenido:
            document.getElementById(
                "modalAuditoriaContenido"
            )
    };


    function limpiarError() {
        el.error.hidden = true;
        el.error.textContent = "";
    }


    function mostrarError(error) {
        window.ClienteAPI.mostrarErrorAPI(
            error,
            el.error
        );
    }


    function nombreUsuario(usuario) {
        if (!usuario) {
            return "—";
        }

        const nombre = [
            usuario.nombre,
            usuario.apellido_paterno,
            usuario.apellido_materno
        ]
            .filter(Boolean)
            .join(" ");

        return (
            nombre ||
            usuario.correo ||
            `Usuario ${usuario.id_usuario}`
        );
    }


    function formatearFecha(valor) {
        if (!valor) {
            return "—";
        }

        const fecha =
            new Date(valor);

        if (
            Number.isNaN(
                fecha.getTime()
            )
        ) {
            return String(valor);
        }

        return fecha.toLocaleString(
            "es-MX",
            {
                dateStyle: "medium",
                timeStyle: "medium"
            }
        );
    }


    function fechaParaAPI(valor) {
        if (!valor) {
            return null;
        }

        const fecha =
            new Date(valor);

        if (
            Number.isNaN(
                fecha.getTime()
            )
        ) {
            return valor;
        }

        return fecha.toISOString();
    }


    function valorNumero(formData, nombre) {
        const valor =
            String(
                formData.get(nombre) || ""
            ).trim();

        return valor
            ? Number(valor)
            : null;
    }


    function valorTexto(formData, nombre) {
        const valor =
            String(
                formData.get(nombre) || ""
            ).trim();

        return valor || null;
    }


    function validarRango(desde, hasta) {
        if (
            !desde ||
            !hasta
        ) {
            return;
        }

        const inicio =
            new Date(desde);

        const fin =
            new Date(hasta);

        if (
            inicio.getTime() >
            fin.getTime()
        ) {
            throw new Error(
                "La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'."
            );
        }
    }


    function parametrosCambios() {
        const datos =
            new FormData(
                el.formCambios
            );

        const desdeLocal =
            valorTexto(
                datos,
                "desde"
            );

        const hastaLocal =
            valorTexto(
                datos,
                "hasta"
            );

        validarRango(
            desdeLocal,
            hastaLocal
        );

        return {
            id_usuario:
                valorNumero(
                    datos,
                    "id_usuario"
                ),

            id_proyecto:
                valorNumero(
                    datos,
                    "id_proyecto"
                ),

            id_proyecto_nucleo:
                valorNumero(
                    datos,
                    "id_proyecto_nucleo"
                ),

            id_nucleo:
                valorNumero(
                    datos,
                    "id_nucleo"
                ),

            entidad_tipo:
                valorTexto(
                    datos,
                    "entidad_tipo"
                ),

            entidad_id:
                valorNumero(
                    datos,
                    "entidad_id"
                ),

            accion:
                valorTexto(
                    datos,
                    "accion"
                ),

            desde:
                fechaParaAPI(
                    desdeLocal
                ),

            hasta:
                fechaParaAPI(
                    hastaLocal
                ),

            skip:
                estado.cambios.skip,

            limit:
                estado.cambios.limit
        };
    }


    function parametrosAccesos() {
        const datos =
            new FormData(
                el.formAccesos
            );

        const desdeLocal =
            valorTexto(
                datos,
                "desde"
            );

        const hastaLocal =
            valorTexto(
                datos,
                "hasta"
            );

        validarRango(
            desdeLocal,
            hastaLocal
        );

        return {
            id_usuario:
                valorNumero(
                    datos,
                    "id_usuario"
                ),

            id_usuario_actor:
                valorNumero(
                    datos,
                    "id_usuario_actor"
                ),

            tipo_evento:
                valorTexto(
                    datos,
                    "tipo_evento"
                ),

            motivo_codigo:
                valorTexto(
                    datos,
                    "motivo_codigo"
                ),

            desde:
                fechaParaAPI(
                    desdeLocal
                ),

            hasta:
                fechaParaAPI(
                    hastaLocal
                ),

            skip:
                estado.accesos.skip,

            limit:
                estado.accesos.limit
        };
    }


    function celda(
        texto,
        clase = ""
    ) {
        const td =
            document.createElement("td");

        if (clase) {
            td.className = clase;
        }

        td.textContent =
            texto ?? "—";

        return td;
    }


    function badge(
        texto,
        variante = "neutro"
    ) {
        const span =
            document.createElement("span");

        span.className =
            `auditoria-badge auditoria-badge-${variante}`;

        span.textContent =
            texto || "—";

        return span;
    }


    function botonDetalle(
        tipo,
        id,
        etiqueta = "Ver detalle"
    ) {
        const boton =
            document.createElement("button");

        boton.type =
            "button";

        boton.className =
            "auditoria-btn auditoria-btn-secundario auditoria-btn-compacto";

        boton.dataset.detalleTipo =
            tipo;

        boton.dataset.detalleId =
            String(id);

        const icono =
            document.createElement("i");

        icono.className =
            "bi bi-eye";

        const texto =
            document.createElement("span");

        texto.textContent =
            etiqueta;

        boton.append(
            icono,
            texto
        );

        return boton;
    }


    function varianteAccion(
        accionDescripcion
    ) {
        const valor =
            String(
                accionDescripcion || ""
            ).toLocaleLowerCase("es-MX");

        if (
            valor.includes("baja")
        ) {
            return "peligro";
        }

        if (
            valor.includes("reactiv")
        ) {
            return "ok";
        }

        if (
            valor.includes("alta")
        ) {
            return "ok";
        }

        if (
            valor.includes("modific")
        ) {
            return "info";
        }

        return "neutro";
    }


    function renderCambios() {
        el.tablaCambios.replaceChildren();

        if (
            estado.cambios.items.length === 0
        ) {
            const tr =
                document.createElement("tr");

            const td =
                celda(
                    "No hay registros que coincidan con los filtros.",
                    "auditoria-tabla-estado"
                );

            td.colSpan = 7;

            tr.appendChild(td);

            el.tablaCambios.appendChild(
                tr
            );

            return;
        }


        for (
            const item
            of estado.cambios.items
        ) {
            const tr =
                document.createElement("tr");


            tr.appendChild(
                celda(
                    formatearFecha(
                        item.fecha_hora
                    ),
                    "auditoria-fecha"
                )
            );


            const tdUsuario =
                document.createElement("td");

            const nombre =
                document.createElement("strong");

            nombre.textContent =
                nombreUsuario(
                    item.usuario
                );

            tdUsuario.appendChild(
                nombre
            );

            if (
                item.usuario?.correo
            ) {
                const correo =
                    document.createElement("small");

                correo.textContent =
                    item.usuario.correo;

                tdUsuario.appendChild(
                    correo
                );
            }

            tr.appendChild(
                tdUsuario
            );


            tr.appendChild(
                celda(
                    item.id_proyecto ?? "—"
                )
            );


            const tdEntidad =
                document.createElement("td");

            const entidad =
                document.createElement("strong");

            entidad.textContent =
                item.entidad_tipo || "—";

            tdEntidad.appendChild(
                entidad
            );


            const entidadId =
                document.createElement("small");

            entidadId.textContent =
                item.entidad_id
                    ? `ID ${item.entidad_id}`
                    : "Sin ID de entidad";

            tdEntidad.appendChild(
                entidadId
            );

            tr.appendChild(
                tdEntidad
            );


            const tdAccion =
                document.createElement("td");

            tdAccion.appendChild(
                badge(
                    item.accion_descripcion ||
                    item.accion,

                    varianteAccion(
                        item.accion_descripcion ||
                        item.accion
                    )
                )
            );

            tr.appendChild(
                tdAccion
            );


            const totalCambios =
                Array.isArray(
                    item.cambios
                )
                    ? item.cambios.length
                    : 0;

            tr.appendChild(
                celda(
                    String(totalCambios)
                )
            );


            const tdDetalle =
                document.createElement("td");

            tdDetalle.appendChild(
                botonDetalle(
                    "cambio",
                    item.id_bitacora
                )
            );

            tr.appendChild(
                tdDetalle
            );


            el.tablaCambios.appendChild(
                tr
            );
        }
    }


    function renderAccesos() {
        el.tablaAccesos.replaceChildren();

        if (
            estado.accesos.items.length === 0
        ) {
            const tr =
                document.createElement("tr");

            const td =
                celda(
                    "No hay eventos que coincidan con los filtros.",
                    "auditoria-tabla-estado"
                );

            td.colSpan = 8;

            tr.appendChild(td);

            el.tablaAccesos.appendChild(
                tr
            );

            return;
        }


        for (
            const item
            of estado.accesos.items
        ) {
            const tr =
                document.createElement("tr");


            tr.appendChild(
                celda(
                    formatearFecha(
                        item.fecha_hora
                    ),
                    "auditoria-fecha"
                )
            );


            tr.appendChild(
                celda(
                    nombreUsuario(
                        item.usuario
                    )
                )
            );


            tr.appendChild(
                celda(
                    nombreUsuario(
                        item.usuario_actor
                    )
                )
            );


            const tdEvento =
                document.createElement("td");

            tdEvento.appendChild(
                badge(
                    item.tipo_evento,
                    "info"
                )
            );

            tr.appendChild(
                tdEvento
            );


            tr.appendChild(
                celda(
                    item.motivo_codigo ||
                    "—"
                )
            );


            tr.appendChild(
                celda(
                    item.ip_origen ||
                    "—",
                    "auditoria-mono"
                )
            );


            tr.appendChild(
                celda(
                    item.id_sesion ??
                    "—"
                )
            );


            const tdDetalle =
                document.createElement("td");

            tdDetalle.appendChild(
                botonDetalle(
                    "acceso",
                    item.id_evento
                )
            );

            tr.appendChild(
                tdDetalle
            );


            el.tablaAccesos.appendChild(
                tr
            );
        }
    }


    function actualizarPaginacion(tipo) {
        const datos =
            estado[tipo];

        const paginaActual =
            datos.total === 0
                ? 1
                : Math.floor(
                    datos.skip /
                    datos.limit
                ) + 1;

        const totalPaginas =
            Math.max(
                1,
                Math.ceil(
                    datos.total /
                    datos.limit
                )
            );


        const esCambios =
            tipo === "cambios";


        const btnAnterior =
            esCambios
                ? el.btnAnteriorCambios
                : el.btnAnteriorAccesos;


        const btnSiguiente =
            esCambios
                ? el.btnSiguienteCambios
                : el.btnSiguienteAccesos;


        const textoPagina =
            esCambios
                ? el.paginaCambios
                : el.paginaAccesos;


        const totalTexto =
            esCambios
                ? el.totalCambios
                : el.totalAccesos;


        btnAnterior.disabled =
            datos.cargando ||
            datos.skip === 0;


        btnSiguiente.disabled =
            datos.cargando ||
            (
                datos.skip +
                datos.limit >=
                datos.total
            );


        textoPagina.textContent =
            `Página ${paginaActual} de ${totalPaginas}`;


        totalTexto.textContent =
            `${datos.total.toLocaleString("es-MX")} registro(s)`;
    }


    function estadoCargaTabla(
        tbody,
        columnas,
        mensaje
    ) {
        tbody.replaceChildren();

        const tr =
            document.createElement("tr");

        const td =
            celda(
                mensaje,
                "auditoria-tabla-estado"
            );

        td.colSpan =
            columnas;

        tr.appendChild(td);

        tbody.appendChild(tr);
    }


    async function cargarCambios() {
        if (
            estado.cambios.cargando
        ) {
            return;
        }

        limpiarError();

        estado.cambios.cargando =
            true;

        actualizarPaginacion(
            "cambios"
        );

        estadoCargaTabla(
            el.tablaCambios,
            7,
            "Consultando bitácora de cambios..."
        );

        try {
            const respuesta =
                await window
                    .AuditoriaAPI
                    .listarCambios(
                        parametrosCambios()
                    );

            estado.cambios.total =
                Number(
                    respuesta?.total || 0
                );

            estado.cambios.items =
                Array.isArray(
                    respuesta?.items
                )
                    ? respuesta.items
                    : [];

            renderCambios();

        } catch (error) {
            estado.cambios.total = 0;
            estado.cambios.items = [];

            estadoCargaTabla(
                el.tablaCambios,
                7,
                "No fue posible consultar la bitácora de cambios."
            );

            mostrarError(error);

        } finally {
            estado.cambios.cargando =
                false;

            actualizarPaginacion(
                "cambios"
            );
        }
    }


    async function cargarAccesos() {
        if (
            estado.accesos.cargando
        ) {
            return;
        }

        limpiarError();

        estado.accesos.cargando =
            true;

        actualizarPaginacion(
            "accesos"
        );

        estadoCargaTabla(
            el.tablaAccesos,
            8,
            "Consultando eventos de acceso..."
        );

        try {
            const respuesta =
                await window
                    .AuditoriaAPI
                    .listarAccesos(
                        parametrosAccesos()
                    );

            estado.accesos.total =
                Number(
                    respuesta?.total || 0
                );

            estado.accesos.items =
                Array.isArray(
                    respuesta?.items
                )
                    ? respuesta.items
                    : [];

            renderAccesos();

        } catch (error) {
            estado.accesos.total = 0;
            estado.accesos.items = [];

            estadoCargaTabla(
                el.tablaAccesos,
                8,
                "No fue posible consultar los eventos de acceso."
            );

            mostrarError(error);

        } finally {
            estado.accesos.cargando =
                false;

            actualizarPaginacion(
                "accesos"
            );
        }
    }


    function cambiarPestana(nombre) {
        estado.pestana =
            nombre;

        for (
            const tab
            of el.tabs
        ) {
            const activa =
                tab.dataset.auditoriaTab ===
                nombre;

            tab.classList.toggle(
                "activo",
                activa
            );

            tab.setAttribute(
                "aria-selected",
                String(activa)
            );
        }


        el.panelCambios.hidden =
            nombre !== "cambios";

        el.panelAccesos.hidden =
            nombre !== "accesos";


        if (
            nombre === "cambios" &&
            estado.cambios.items.length === 0 &&
            estado.cambios.total === 0
        ) {
            cargarCambios();
        }


        if (
            nombre === "accesos" &&
            estado.accesos.items.length === 0 &&
            estado.accesos.total === 0
        ) {
            cargarAccesos();
        }
    }


    function textoValor(valor) {
        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return "—";
        }

        if (
            typeof valor === "string"
        ) {
            return valor;
        }

        try {
            return JSON.stringify(
                valor,
                null,
                2
            );

        } catch {
            return String(valor);
        }
    }


    function bloqueDato(
        etiqueta,
        valor,
        clase = ""
    ) {
        const bloque =
            document.createElement("div");

        bloque.className =
            `auditoria-detalle-dato${
                clase
                    ? ` ${clase}`
                    : ""
            }`;


        const titulo =
            document.createElement("span");

        titulo.textContent =
            etiqueta;


        const contenido =
            document.createElement("strong");

        contenido.textContent =
            textoValor(valor);


        bloque.append(
            titulo,
            contenido
        );

        return bloque;
    }


    function abrirDetalleCambio(item) {
        el.modalTitulo.textContent =
            `Cambio #${item.id_bitacora}`;

        el.modalSubtitulo.textContent =
            `${formatearFecha(item.fecha_hora)} · ${item.accion_descripcion || item.accion}`;

        el.modalContenido.replaceChildren();


        const resumen =
            document.createElement("div");

        resumen.className =
            "auditoria-detalle-grid";


        resumen.append(
            bloqueDato(
                "Usuario",
                nombreUsuario(
                    item.usuario
                )
            ),

            bloqueDato(
                "Correo",
                item.usuario?.correo ||
                "—"
            ),

            bloqueDato(
                "Proyecto",
                item.id_proyecto ??
                "—"
            ),

            bloqueDato(
                "Proyecto-núcleo",
                item.id_proyecto_nucleo ??
                "—"
            ),

            bloqueDato(
                "Núcleo",
                item.id_nucleo ??
                "—"
            ),

            bloqueDato(
                "Entidad",
                item.entidad_tipo ||
                "—"
            ),

            bloqueDato(
                "ID entidad",
                item.entidad_id ??
                "—"
            ),

            bloqueDato(
                "Acción técnica",
                item.accion ||
                "—"
            )
        );


        el.modalContenido.appendChild(
            resumen
        );


        const tituloCambios =
            document.createElement("h3");

        tituloCambios.textContent =
            "Campos modificados";

        el.modalContenido.appendChild(
            tituloCambios
        );


        const cambios =
            Array.isArray(
                item.cambios
            )
                ? item.cambios
                : [];


        if (
            cambios.length === 0
        ) {
            const vacio =
                document.createElement("p");

            vacio.className =
                "auditoria-detalle-vacio";

            vacio.textContent =
                "Este registro no contiene diferencias de campos visibles.";

            el.modalContenido.appendChild(
                vacio
            );

        } else {
            const lista =
                document.createElement("div");

            lista.className =
                "auditoria-cambios-lista";


            for (
                const cambio
                of cambios
            ) {
                const tarjeta =
                    document.createElement("article");

                tarjeta.className =
                    "auditoria-cambio-item";


                const campo =
                    document.createElement("h4");

                campo.textContent =
                    cambio.campo ||
                    "Campo";


                const comparacion =
                    document.createElement("div");

                comparacion.className =
                    "auditoria-cambio-comparacion";


                const anterior =
                    document.createElement("div");

                const anteriorLabel =
                    document.createElement("span");

                anteriorLabel.textContent =
                    "Anterior";

                const anteriorValor =
                    document.createElement("pre");

                anteriorValor.textContent =
                    textoValor(
                        cambio.anterior
                    );

                anterior.append(
                    anteriorLabel,
                    anteriorValor
                );


                const nuevo =
                    document.createElement("div");

                const nuevoLabel =
                    document.createElement("span");

                nuevoLabel.textContent =
                    "Nuevo";

                const nuevoValor =
                    document.createElement("pre");

                nuevoValor.textContent =
                    textoValor(
                        cambio.nuevo
                    );

                nuevo.append(
                    nuevoLabel,
                    nuevoValor
                );


                comparacion.append(
                    anterior,
                    nuevo
                );

                tarjeta.append(
                    campo,
                    comparacion
                );

                lista.appendChild(
                    tarjeta
                );
            }

            el.modalContenido.appendChild(
                lista
            );
        }


        abrirModal();
    }


    function abrirDetalleAcceso(item) {
        el.modalTitulo.textContent =
            `Evento de acceso #${item.id_evento}`;

        el.modalSubtitulo.textContent =
            `${formatearFecha(item.fecha_hora)} · ${item.tipo_evento}`;

        el.modalContenido.replaceChildren();


        const resumen =
            document.createElement("div");

        resumen.className =
            "auditoria-detalle-grid";


        resumen.append(
            bloqueDato(
                "Usuario",
                nombreUsuario(
                    item.usuario
                )
            ),

            bloqueDato(
                "ID usuario",
                item.usuario?.id_usuario ??
                "—"
            ),

            bloqueDato(
                "Actor",
                nombreUsuario(
                    item.usuario_actor
                )
            ),

            bloqueDato(
                "ID actor",
                item.usuario_actor?.id_usuario ??
                "—"
            ),

            bloqueDato(
                "Tipo de evento",
                item.tipo_evento ||
                "—"
            ),

            bloqueDato(
                "Código de motivo",
                item.motivo_codigo ||
                "—"
            ),

            bloqueDato(
                "Sesión",
                item.id_sesion ??
                "—"
            ),

            bloqueDato(
                "IP de origen",
                item.ip_origen ||
                "—",
                "auditoria-mono"
            )
        );


        el.modalContenido.appendChild(
            resumen
        );


        const detalle =
            document.createElement("section");

        detalle.className =
            "auditoria-detalle-seccion";


        const tituloDetalle =
            document.createElement("h3");

        tituloDetalle.textContent =
            "Detalle";


        const detalleTexto =
            document.createElement("pre");

        detalleTexto.textContent =
            item.detalle ||
            "—";


        detalle.append(
            tituloDetalle,
            detalleTexto
        );

        el.modalContenido.appendChild(
            detalle
        );


        const agente =
            document.createElement("section");

        agente.className =
            "auditoria-detalle-seccion";


        const tituloAgente =
            document.createElement("h3");

        tituloAgente.textContent =
            "User-Agent";


        const agenteTexto =
            document.createElement("pre");

        agenteTexto.textContent =
            item.user_agent ||
            "—";


        agente.append(
            tituloAgente,
            agenteTexto
        );

        el.modalContenido.appendChild(
            agente
        );


        abrirModal();
    }


    function abrirModal() {
        el.modal.hidden =
            false;

        document.body.classList.add(
            "auditoria-modal-abierto"
        );
    }


    function cerrarModal() {
        el.modal.hidden =
            true;

        document.body.classList.remove(
            "auditoria-modal-abierto"
        );
    }


    function buscarDetalle(
        tipo,
        id
    ) {
        if (
            tipo === "cambio"
        ) {
            return (
                estado.cambios.items.find(
                    item =>
                        Number(
                            item.id_bitacora
                        ) ===
                        Number(id)
                ) || null
            );
        }

        return (
            estado.accesos.items.find(
                item =>
                    Number(
                        item.id_evento
                    ) ===
                    Number(id)
            ) || null
        );
    }


    el.tabs.forEach(
        tab => {
            tab.addEventListener(
                "click",
                () => {
                    cambiarPestana(
                        tab.dataset.auditoriaTab
                    );
                }
            );
        }
    );


    el.formCambios.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            estado.cambios.skip =
                0;

            try {
                parametrosCambios();

                await cargarCambios();

            } catch (error) {
                mostrarError(error);
            }
        }
    );


    el.formAccesos.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            estado.accesos.skip =
                0;

            try {
                parametrosAccesos();

                await cargarAccesos();

            } catch (error) {
                mostrarError(error);
            }
        }
    );


    el.btnLimpiarCambios.addEventListener(
        "click",
        async () => {
            el.formCambios.reset();

            el.limiteCambios.value =
                "50";

            estado.cambios.skip =
                0;

            estado.cambios.limit =
                50;

            await cargarCambios();
        }
    );


    el.btnLimpiarAccesos.addEventListener(
        "click",
        async () => {
            el.formAccesos.reset();

            el.limiteAccesos.value =
                "50";

            estado.accesos.skip =
                0;

            estado.accesos.limit =
                50;

            await cargarAccesos();
        }
    );


    el.limiteCambios.addEventListener(
        "change",
        async () => {
            estado.cambios.limit =
                Number(
                    el.limiteCambios.value
                );

            estado.cambios.skip =
                0;

            await cargarCambios();
        }
    );


    el.limiteAccesos.addEventListener(
        "change",
        async () => {
            estado.accesos.limit =
                Number(
                    el.limiteAccesos.value
                );

            estado.accesos.skip =
                0;

            await cargarAccesos();
        }
    );


    el.btnAnteriorCambios.addEventListener(
        "click",
        async () => {
            estado.cambios.skip =
                Math.max(
                    0,
                    estado.cambios.skip -
                    estado.cambios.limit
                );

            await cargarCambios();
        }
    );


    el.btnSiguienteCambios.addEventListener(
        "click",
        async () => {
            if (
                estado.cambios.skip +
                estado.cambios.limit >=
                estado.cambios.total
            ) {
                return;
            }

            estado.cambios.skip +=
                estado.cambios.limit;

            await cargarCambios();
        }
    );


    el.btnAnteriorAccesos.addEventListener(
        "click",
        async () => {
            estado.accesos.skip =
                Math.max(
                    0,
                    estado.accesos.skip -
                    estado.accesos.limit
                );

            await cargarAccesos();
        }
    );


    el.btnSiguienteAccesos.addEventListener(
        "click",
        async () => {
            if (
                estado.accesos.skip +
                estado.accesos.limit >=
                estado.accesos.total
            ) {
                return;
            }

            estado.accesos.skip +=
                estado.accesos.limit;

            await cargarAccesos();
        }
    );


    document.addEventListener(
        "click",
        event => {
            const boton =
                event.target.closest(
                    "button[data-detalle-tipo][data-detalle-id]"
                );

            if (!boton) {
                return;
            }

            const tipo =
                boton.dataset.detalleTipo;

            const item =
                buscarDetalle(
                    tipo,
                    boton.dataset.detalleId
                );

            if (!item) {
                return;
            }

            if (
                tipo === "cambio"
            ) {
                abrirDetalleCambio(
                    item
                );

            } else {
                abrirDetalleAcceso(
                    item
                );
            }
        }
    );


    document
        .querySelectorAll(
            "[data-cerrar-auditoria-modal]"
        )
        .forEach(
            boton => {
                boton.addEventListener(
                    "click",
                    cerrarModal
                );
            }
        );


    el.modal.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                el.modal
            ) {
                cerrarModal();
            }
        }
    );


    document.addEventListener(
        "keydown",
        event => {
            if (
                event.key === "Escape" &&
                !el.modal.hidden
            ) {
                cerrarModal();
            }
        }
    );


    try {
        const sesion =
            await window.AuthAPI
                .requerirSesion();

        if (!sesion) {
            return;
        }

        await cargarCambios();

    } catch (error) {
        mostrarError(error);
    }
});