document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const etiquetas = window.SSALFER_AUDITORIA;
    const usuariosPorId = new Map();
    const tiposDocumentoPorId=new Map();
    const valorCambio=(valor,campo)=>campo==="id_tipo_documento"&&tiposDocumentoPorId.has(Number(valor))?tiposDocumentoPorId.get(Number(valor)):etiquetas.valor(valor,campo,id=>usuariosPorId.get(id));
    const proyectosPorId = new Map();
    const nucleosPorId = new Map();
    const contextosPorId = new Map();

    const tecnicoFiltro=document.createElement('details');tecnicoFiltro.innerHTML='<summary>Filtros técnicos avanzados</summary>';
    const filtroId=document.getElementById('cambiosEntidadId')?.closest('.auditoria-campo');
    if(filtroId){filtroId.before(tecnicoFiltro);tecnicoFiltro.append(filtroId);}
    async function cargarFiltrosHumanos() {
        function convertir(id, etiqueta, opciones, vacio = "Todos") {
            const previo = document.getElementById(id);
            const select = document.createElement("select");
            select.id = previo.id;
            select.name = previo.name;
            select.className = previo.className;
            select.add(new Option(vacio, ""));
            opciones.forEach(([valor, texto]) => select.add(new Option(texto, String(valor))));
            previo.replaceWith(select);
            document.querySelector(`label[for="${id}"]`).textContent = etiqueta;
            return select;
        }
        const [usuarios, proyectos, nucleos] = await Promise.all([
            (async () => {
                const todos = [];
                for (let skip = 0; ; skip += 200) {
                    const pagina = await window.UsuariosAPI.listar({ skip, limit: 200, estado: "todos" });
                    todos.push(...pagina);
                    if (pagina.length < 200) return todos;
                }
            })(),
            window.ProyectosAPI.listar(), window.NucleosAPI.listar()
        ]);
        try{(await window.CatalogosAPI.tiposDocumento(true)).forEach(t=>tiposDocumentoPorId.set(t.id_tipo_documento,t.nombre));}catch{ /* El detalle técnico permanece disponible. */ }
        usuarios.forEach(u=>usuariosPorId.set(Number(u.id_usuario),nombreUsuario(u)));
        convertir("cambiosEntidadTipo","Tipo de entidad",Object.entries(etiquetas.entidades));
        convertir("cambiosAccion","Acción",[["insert","Alta"],["update","Modificación (incluye bajas lógicas)"],["delete","Baja definitiva"]]);
        const opcionesUsuario = usuarios.map(item => [item.id_usuario, nombreUsuario(item)]);
        convertir("cambiosUsuario", "Usuario", opcionesUsuario);
        convertir("accesosUsuario", "Usuario afectado", opcionesUsuario);
        convertir("accesosActor", "Usuario que realizó la acción", opcionesUsuario);
        proyectos.forEach(item => proyectosPorId.set(Number(item.id_proyecto), item.nombre_proyecto));
        nucleos.forEach(item => nucleosPorId.set(Number(item.id_nucleo), item.nombre_nucleo));
        const proyecto = convertir("cambiosProyecto", "Proyecto", [...proyectosPorId]);
        convertir("cambiosNucleo", "Núcleo", [...nucleosPorId]);
        const contexto = convertir("cambiosProyectoNucleo", "Núcleo del proyecto", [], "Selecciona primero un proyecto");
        contexto.disabled = true;
        let revision = 0;
        proyecto.addEventListener("change", async () => {
            const actual = ++revision;
            contexto.replaceChildren(new Option(proyecto.value ? "Cargando núcleos..." : "Selecciona primero un proyecto", ""));
            contexto.disabled = true;
            if (!proyecto.value) return;
            try {
                const lista = await window.NucleosAPI.listarPorProyecto(proyecto.value);
                if (actual !== revision) return;
                contexto.replaceChildren(new Option("Todos los núcleos del proyecto", ""));
                lista.forEach(item => {
                    contexto.add(new Option(item.nombre_nucleo, String(item.id_proyecto_nucleo)));
                    contextosPorId.set(Number(item.id_proyecto_nucleo), item.nombre_nucleo);
                });
                contexto.disabled = false;
            } catch (error) {
                if (actual !== revision) return;
                contexto.replaceChildren(new Option("No fue posible cargar los núcleos", ""));
                mostrarError(error);
            }
        });
        el.formCambios.addEventListener("reset", () => {
            ++revision;
            contexto.replaceChildren(new Option("Selecciona primero un proyecto", ""));
            contexto.disabled = true;
        });
    }

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
            "Usuario sin nombre disponible"
        );
    }


    const formatearFecha = etiquetas.fecha;

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
                    nombreProyectoCambio(item)
                )
            );


            const tdEntidad =
                document.createElement("td");

            const entidad =
                document.createElement("strong");

            entidad.textContent =
                etiquetas.entidad(item.entidad_tipo);

            tdEntidad.appendChild(
                entidad
            );


            tr.appendChild(
                tdEntidad
            );


            const tdAccion =
                document.createElement("td");

            tdAccion.appendChild(
                badge(
                    accionCambio(item),

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
                    etiquetas.accion(item.tipo_evento),
                    "info"
                )
            );

            tr.appendChild(
                tdEvento
            );


            tr.appendChild(
                celda(
                    etiquetas.humanizar(item.motivo_codigo)
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
                    item.id_sesion ? "Sesión registrada" : "—"
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


    function accionCambio(item) {
        if(item.cambios?.some(c=>c.campo==='activo'&&c.anterior===true&&c.nuevo===false))return 'Baja';
        return etiquetas.accion(item.accion_descripcion || item.accion);
    }
    function nombreProyectoCambio(item) {
        const id=item.id_proyecto || (item.entidad_tipo==='proyecto'?item.entidad_id:null);
        if(!id)return '—';
        const cambio=item.cambios?.find(c=>c.campo==='nombre_proyecto');
        return proyectosPorId.get(Number(id)) || cambio?.nuevo || cambio?.anterior || (accionCambio(item)==='Baja' ? 'Proyecto dado de baja' : 'Proyecto sin nombre disponible');
    }
    function detalleTecnico(item) {
        const d=document.createElement('details'),resumen=document.createElement('summary'),pre=document.createElement('pre');
        resumen.textContent='Detalle técnico';pre.textContent=JSON.stringify(item,null,2);d.append(resumen,pre);el.modalContenido.append(d);
    }
    async function abrirDetalleCambio(item) {
        el.modalTitulo.textContent='Detalle del cambio';
        el.modalSubtitulo.textContent=`${formatearFecha(item.fecha_hora)} · ${accionCambio(item)}`;
        el.modalContenido.replaceChildren();
        const pid=item.id_proyecto || (item.entidad_tipo==='proyecto'?item.entidad_id:null);
        if(pid&&!proyectosPorId.has(Number(pid))) {
            try {const proyecto=await window.ProyectosAPI.obtener(pid);proyectosPorId.set(Number(pid),proyecto.nombre_proyecto);}catch {/* La API puede excluir proyectos dados de baja. */}
        }
        const titulo=nombreProyectoCambio(item),accion=accionCambio(item);
        const verbos={'Alta':'registró','Baja':'dio de baja','Modificación':'modificó','Reactivación':'reactivó'};
        const motivo=item.cambios?.find(c=>c.campo==='motivo_baja')?.nuevo;
        const frase=document.createElement('p');frase.className='auditoria-resumen-frase';
        frase.textContent=`${nombreUsuario(item.usuario)} ${verbos[accion]||'registró un cambio en'} ${item.entidad_tipo==='proyecto'?'el ':''}${etiquetas.entidad(item.entidad_tipo).toLowerCase()}${titulo!=='—'?(item.entidad_tipo==='proyecto'?` «${titulo}»`:` del proyecto «${titulo}»`):''} el ${formatearFecha(item.fecha_hora)}.${motivo?` Motivo: ${motivo}`:''}`;
        const resumen=document.createElement('div');resumen.className='auditoria-detalle-grid';
        resumen.append(bloqueDato('Usuario',nombreUsuario(item.usuario)),bloqueDato('Correo',item.usuario?.correo),bloqueDato('Proyecto',titulo),bloqueDato('Entidad',etiquetas.entidad(item.entidad_tipo)),bloqueDato('Acción',accion));
        if(item.id_proyecto_nucleo)resumen.append(bloqueDato('Núcleo del proyecto',contextosPorId.get(Number(item.id_proyecto_nucleo))||'Nombre no disponible'));
        if(item.id_nucleo)resumen.append(bloqueDato('Núcleo',nucleosPorId.get(Number(item.id_nucleo))||'Nombre no disponible'));
        el.modalContenido.append(frase,resumen);
        const h=document.createElement('h3');h.textContent='Campos modificados';el.modalContenido.append(h);
        for(const c of item.cambios||[]){const linea=document.createElement('p');linea.className='auditoria-cambio-linea';linea.textContent=`${etiquetas.campo(item.entidad_tipo,c.campo)}: ${valorCambio(c.anterior,c.campo)} → ${valorCambio(c.nuevo,c.campo)}`;el.modalContenido.append(linea);}
        if(!item.cambios?.length)el.modalContenido.append(bloqueDato('Cambios','Sin diferencias de campos visibles.'));
        detalleTecnico(item);abrirModal();
    }
    function abrirDetalleAcceso(item) {
        el.modalTitulo.textContent='Evento de acceso';el.modalSubtitulo.textContent=`${formatearFecha(item.fecha_hora)} · ${etiquetas.accion(item.tipo_evento)}`;el.modalContenido.replaceChildren();
        el.modalContenido.append(bloqueDato('Usuario',nombreUsuario(item.usuario)),bloqueDato('Actor',nombreUsuario(item.usuario_actor)),bloqueDato('Evento',etiquetas.accion(item.tipo_evento)),bloqueDato('Motivo',etiquetas.humanizar(item.motivo_codigo)),bloqueDato('Detalle',item.detalle),bloqueDato('IP de origen',item.ip_origen));detalleTecnico(item);abrirModal();
    }

    let focoDetalle;
    function abrirModal() {
        focoDetalle=document.activeElement;
        requestAnimationFrame(()=>el.modal.querySelector("[data-cerrar-auditoria-modal]")?.focus());
        el.modal.hidden =
            false;

        document.body.classList.add(
            "auditoria-modal-abierto"
        );
    }


    function cerrarModal() {
        focoDetalle?.focus();
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

        if (sesion.user?.rol === "admin") {
            try { await cargarFiltrosHumanos(); }
            catch (error) { mostrarError(error); }
        }
        await cargarCambios();

    } catch (error) {
        mostrarError(error);
    }
});
