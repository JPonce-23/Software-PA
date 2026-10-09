(() => {
    "use strict";
    const api = () => window.DocumentosAPI;
    const g = () => window.SSALFER_GESTION;
    const fecha = valor => window.SSALFER_FORMAT.formatearFecha(valor);
    const campo = (nombre, etiqueta, extra = {}) => ({ nombre, etiqueta, ...extra });
    async function montar(raiz, idNucleo, inicial = {}) {
        const { e, boton, tabla, formulario, opciones } = g();
        const contexto = window.SSALFER_CONTEXTO.crear(idNucleo);
        const sesion=await window.AuthAPI.requerirSesion(),puedeCapturar=["admin","operador"].includes(sesion?.user?.rol);
        let revision = 0, registros = [], documentos = [], ocupado = false;
        raiz.innerHTML = `<div class="ssalfer-gestion-campos"><label class="ssalfer-gestion-campo">Tipo de registro<select data-doc-tipo>${Object.entries(window.SSALFER_CONTEXTO.nombres).map(([valor, nombre]) => `<option value="${valor}">${e(nombre)}</option>`).join("")}</select></label><label class="ssalfer-gestion-campo">Registro<select data-doc-registro disabled></select></label></div><div data-doc-contenido aria-live="polite"></div>`;
        const tipo = raiz.querySelector("[data-doc-tipo]"), registro = raiz.querySelector("[data-doc-registro]"), contenido = raiz.querySelector("[data-doc-contenido]");
        const objetivo = () => ({ tipo: tipo.value, id: Number(registro.value), nombre: registro.selectedOptions[0]?.textContent });
        function errorVisible(error, reintento) {
            contenido.innerHTML = `<p role="alert">${e(error.message || "No fue posible consultar los documentos.")}</p>${boton("Reintentar", reintento)}`;
        }
        async function seleccionarTipo(id) {
            const actual = ++revision;
            registro.disabled = true; registro.replaceChildren(new Option("Cargando registros…", "")); contenido.replaceChildren();
            try {
                const respuesta = await contexto.listar(tipo.value);
                if (actual !== revision) return;
                registros = respuesta;
                registro.replaceChildren(new Option(registros.length ? "Selecciona un registro" : "Aún no hay registros de este tipo", ""));
                registros.forEach(r => registro.add(new Option(r.etiqueta, r.id)));
                registro.disabled = !registros.length;
                if (id && registros.some(r => r.id === Number(id))) registro.value = String(id);
                else if (registros.length === 1) registro.value = String(registros[0].id);
                await cargar();
            } catch (error) { if (actual === revision) errorVisible(error, "reintentar-tipo"); }
        }
        async function cargar() {
            const actual = ++revision, destino = objetivo();
            contenido.replaceChildren(); documentos = [];
            if (!destino.id) return;
            try {
                const respuesta = await api().listarPorEntidad(destino.tipo, destino.id);
                if (actual !== revision) return;
                documentos = respuesta;
                contenido.innerHTML = `<h2>Documentos de ${e(destino.nombre)}</h2><div class="ssalfer-gestion-barra">${puedeCapturar?boton("Registrar documento", "crear")+boton("Vincular documento existente", "vincular"):""}${boton("Consultar procedencia", "fuentes")}</div>${tabla([{ titulo: "Documento", valor: d => d.titulo || api().nombreTipo(d) }, { titulo: "Tipo", valor: d => api().nombreTipo(d) }, { titulo: "Estado", valor: d => window.SSALFER_FORMAT.etiquetaCodigo(d.estado) }, { titulo: "Fecha", valor: d => fecha(d.fecha_documento) }, { titulo: "Folio", valor: d => d.numero_folio }], documentos, d => (puedeCapturar?boton("Editar", "editar", d.id_documento):"") + boton("Versiones y archivos", "versiones", d.id_documento), "Aún no hay documentos. Puedes registrar uno o vincular uno existente.")}`;
            } catch (error) { if (actual === revision) errorVisible(error, "reintentar"); }
        }
        async function notificar(destino) {
            await window.SSALFER_DOCUMENTOS?.refrescar?.(destino.tipo, destino.id);
            window.dispatchEvent(new CustomEvent("ssalfer:documentos", { detail: destino }));
            await cargar();
        }
        async function editar(destino, documento) {
            const tipos=await window.CatalogosAPI.tiposDocumento();
            const activos=tipos.filter(t=>t.activo),opcionesTipo=activos.map(t=>({valor:t.id_tipo_documento,texto:t.nombre}));
            const campos=[...(documento?.id_tipo_documento?[]:documento?[campo('tipo_documento','Tipo histórico',{maximo:80,requerido:true})]:[]),campo('id_tipo_documento',documento?'Clasificar o reclasificar con catálogo (opcional)':'Tipo de documento',{opciones:opcionesTipo,numerico:true,requerido:!documento}),campo('estado','Estado',{requerido:true,opciones:opciones(['disponible','faltante','referenciado'])}),campo('titulo','Título',{maximo:250}),campo('fecha_documento','Fecha del documento',{tipo:'date'}),campo('numero_folio','Folio',{maximo:150}),campo('descripcion','Descripción',{tipo:'textarea'})];
            const inicial=documento?{...documento,id_tipo_documento:null}:{};
            const resultado=await formulario({titulo:documento?'Editar documento':'Registrar documento',campos,inicial,editar:Boolean(documento),introduccion:`Registro: ${destino.nombre}.${documento?' Clasificación actual: '+api().nombreTipo(documento)+'. Conserva la selección vacía para mantenerla.':''} El archivo se agrega en Versiones y archivos.`,preparar:form=>{
                const tipo=form.elements.id_tipo_documento,descripcion=form.elements.descripcion;
                const actualizar=()=>{const codigo=activos.find(t=>t.id_tipo_documento===Number(tipo.value))?.codigo || (!tipo.value?documento?.clasificacion?.codigo:null);descripcion.required=codigo==='OTRO';if(form.elements.tipo_documento)form.elements.tipo_documento.disabled=Boolean(tipo.value);};tipo.addEventListener('change',actualizar);actualizar();
            },validar:d=>{
                const codigo=activos.find(t=>t.id_tipo_documento===Number(d.id_tipo_documento))?.codigo || documento?.clasificacion?.codigo;
                return codigo==='OTRO'&&!(Object.hasOwn(d,'descripcion')?d.descripcion:documento?.descripcion)?.trim()?'Para Otro, escribe una descripción.':null;
            },guardar:datos=>{
                if(!datos.id_tipo_documento)delete datos.id_tipo_documento;else delete datos.tipo_documento;
                if(documento?.id_tipo_documento)delete datos.tipo_documento;
                return documento?api().actualizar(documento.id_documento,datos):api().crearParaEntidad(destino.tipo,destino.id,datos);
            }});
            if (resultado) await notificar(destino);
        }
        async function versiones(documento) {
            const lista = await api().listarVersiones(documento.id_documento);
            await window.SSALFER_UI.abrirModal({ titulo: `Archivos: ${documento.titulo || api().nombreTipo(documento)}`, contenido: `${puedeCapturar?boton("Subir nueva versión", "subir"):""}${tabla([{ titulo: "Versión", valor: v => v.numero_version }, { titulo: "Archivo", valor: v => v.nombre_original }, { titulo: "Tamaño", valor: v => `${Number(v.tamano_bytes).toLocaleString("es-MX")} bytes` }, { titulo: "Carga", valor: v => fecha(v.fecha_carga) }], lista, v => boton("Descargar", "descargar", v.id_documento_version), "Aún no se ha subido un archivo.")}`, preparar: modal => {
                modal.addEventListener("click", async event => {
                    const b = event.target.closest("[data-gestion]"); if (!b || b.disabled) return;
                    b.disabled = true;
                    try {
                        if (b.dataset.gestion === "descargar") {
                            const version = lista.find(v => v.id_documento_version === Number(b.dataset.registro));
                            await g().descargar(`/documentos/versiones/${version.id_documento_version}/descarga`, version.nombre_original);
                        } else if (b.dataset.gestion === "subir") {
                            const nuevo = await formulario({ titulo: "Subir nueva versión", campos: [campo("archivo", "Archivo", { tipo: "file", requerido: true })], guardar: datos => { const payload = new FormData(); payload.append("archivo", datos.archivo); return api().subirVersion(documento.id_documento, payload); } });
                            if (nuevo) { modal.querySelector("[data-modal-cerrar]").click(); await versiones(documento); }
                        }
                    } catch (error) { window.ClienteAPI.mostrarErrorAPI(error); }
                    finally { b.disabled = false; }
                });
            } });
        }
        async function vincular(destino) {
            let origenRevision = 0;
            const resultado = await formulario({ titulo: "Vincular documento existente", introduccion: `Destino: ${destino.nombre}. Elige el registro donde ya está guardado el documento.`, campos: [campo("tipo_origen", "Tipo de registro de origen", { opciones: Object.entries(window.SSALFER_CONTEXTO.nombres).map(([valor, texto]) => ({ valor, texto })), requerido: true }), campo("registro_origen", "Registro de origen", { opciones: [], requerido: true }), campo("documento", "Documento", { opciones: [], requerido: true, numerico: true })], preparar: form => {
                const padre = form.elements.tipo_origen, hijo = form.elements.registro_origen, doc = form.elements.documento;
                padre.addEventListener("change", async () => {
                    const actual = ++origenRevision; hijo.replaceChildren(new Option("Selecciona un registro", "")); doc.replaceChildren(new Option("Selecciona primero un registro", "")); hijo.disabled = doc.disabled = true;
                    if (!padre.value) return;
                    try { const opciones = await contexto.listar(padre.value); if (actual !== origenRevision || !form.isConnected) return; opciones.forEach(r => hijo.add(new Option(r.etiqueta, r.id))); hijo.disabled = !opciones.length; }
                    catch (error) { if (actual === origenRevision) window.ClienteAPI.mostrarErrorAPI(error); }
                });
                hijo.addEventListener("change", async () => {
                    const actual = ++origenRevision; doc.replaceChildren(new Option("Selecciona un documento", "")); doc.disabled = true;
                    if (!hijo.value) return;
                    try { const opciones = await api().listarPorEntidad(padre.value, hijo.value); if (actual !== origenRevision || !form.isConnected) return; opciones.forEach(d => doc.add(new Option(`${d.titulo || api().nombreTipo(d)} · ${api().nombreTipo(d)} · ${fecha(d.fecha_documento)}`, d.id_documento))); doc.disabled = !opciones.length; if (!opciones.length) doc.replaceChildren(new Option("Este registro no tiene documentos", "")); }
                    catch (error) { if (actual === origenRevision) window.ClienteAPI.mostrarErrorAPI(error); }
                });
            }, validar: datos => !datos.documento ? "Selecciona un documento disponible." : null, guardar: datos => api().vincularAEntidad(datos.documento, destino.tipo, destino.id) });
            if (resultado) await notificar(destino);
        }
        async function fuentes(destino) {
            const lista = await api().listarTrazabilidad(destino.tipo, destino.id);
            const accion = await window.SSALFER_UI.abrirModal({ titulo: `Procedencia: ${destino.nombre}`, contenido: tabla([{ titulo: "Archivo de origen", valor: r => r.archivo }, { titulo: "Hoja", valor: r => r.hoja }, { titulo: "Fila", valor: r => r.fila }, { titulo: "Columna", valor: r => r.columna }, { titulo: "Valor original", valor: r => r.valor_original }, { titulo: "Valor interpretado", valor: r => r.valor_normalizado }, { titulo: "Tratamiento", valor: r => r.tratamiento }, { titulo: "Fecha", valor: r => fecha(r.registrado_en) }], lista), acciones: [{ valor: false, texto: "Cerrar" }, ...(puedeCapturar?[{ valor: true, texto: "Registrar procedencia", principal: true }]:[])] });
            if (!accion) return;
            const resultado = await formulario({ titulo: "Registrar procedencia", campos: [campo("archivo", "Archivo de origen", { requerido: true, maximo: 255 }), campo("hoja", "Hoja", { maximo: 255 }), campo("fila", "Fila", { numerico: true, tipo: "number", min: 1, paso: "1" }), campo("columna", "Columna", { maximo: 120 }), campo("valor_original", "Valor original", { tipo: "textarea" }), campo("valor_normalizado", "Valor interpretado", { tipo: "textarea" }), campo("tratamiento", "Tratamiento", { requerido: true, opciones: opciones([["PERSISTIR", "Conservar"], ["DERIVAR", "Derivar"], ["REFERENCIA", "Usar como referencia"], ["DOCUMENTAR", "Documentar"], ["REVISAR", "Revisar"], ["NO IMPLEMENTAR", "No implementar"]]) })], guardar: datos => api().registrarTrazabilidad(destino.tipo, destino.id, datos) });
            if (resultado) await fuentes(destino);
        }
        tipo.addEventListener("change", () => seleccionarTipo()); registro.addEventListener("change", cargar);
        raiz.addEventListener("click", async event => {
            const b = event.target.closest("[data-gestion]"); if (!b || ocupado) return;
            if(!puedeCapturar && ["crear","editar","vincular","subir"].includes(b.dataset.gestion))return;
            ocupado = true; tipo.disabled = registro.disabled = true;
            try {
                const destino = objetivo(), documento = documentos.find(d => d.id_documento === Number(b.dataset.registro));
                if (b.dataset.gestion === "reintentar-tipo") await seleccionarTipo();
                else if (b.dataset.gestion === "reintentar") await cargar();
                else if (b.dataset.gestion === "crear") await editar(destino);
                else if (b.dataset.gestion === "editar") await editar(destino, documento);
                else if (b.dataset.gestion === "versiones") await versiones(documento);
                else if (b.dataset.gestion === "vincular") await vincular(destino);
                else if (b.dataset.gestion === "fuentes") await fuentes(destino);
            } catch (error) { window.ClienteAPI.mostrarErrorAPI(error); }
            finally { ocupado = false; tipo.disabled = false; registro.disabled = !registros.length; }
        });
        tipo.value = inicial.tipo || "proyecto_nucleo";
        await seleccionarTipo(inicial.id || idNucleo);
    }
    async function abrir(idNucleo, inicial) {
        await window.SSALFER_UI.abrirModal({ titulo: "Documentos del núcleo", contenido: '<div data-gestor-documentos></div>', preparar: modal => { montar(modal.querySelector("[data-gestor-documentos]"), idNucleo, inicial).catch(window.ClienteAPI.mostrarErrorAPI); } });
    }
    window.SSALFER_GESTOR_DOCUMENTOS = Object.freeze({ montar, abrir });
    function acceso(id) {
        if (!Number.isSafeInteger(id) || id <= 0 || document.getElementById("documentosContenido") || document.querySelector("[data-abrir-documentos]")) return;
        const destino = document.querySelector(".acciones-header") || document.querySelector(".pagina-header");
        if (!destino) return;
        const b = document.createElement("button"); b.type = "button"; b.className = "btn-secundario"; b.dataset.abrirDocumentos = ""; b.textContent = "Documentos de este núcleo"; b.title = "Registrar, subir y consultar los documentos de este núcleo";
        b.addEventListener("click", () => abrir(id)); destino.appendChild(b);
    }
    window.addEventListener("ssalfer:contexto-documentos", event => acceso(event.detail.idProyectoNucleo));
    document.addEventListener("DOMContentLoaded", () => acceso(Number(new URLSearchParams(location.search).get("id_proyecto_nucleo"))));
})();
