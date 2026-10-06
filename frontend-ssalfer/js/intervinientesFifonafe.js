document.addEventListener("DOMContentLoaded", async () => {
    "use strict";
    const params = new URLSearchParams(location.search), id = Number(params.get("id_fifonafe") || params.get("id")), pn = Number(params.get("id_proyecto_nucleo"));
    if (!id || !pn) return;
    const g = window.SSALFER_GESTION, api = window.FifonafeAPI, f = window.SSALFER_FORMAT;
    const seccion = document.createElement("section"); seccion.className = "ssalfer-gestion-seccion"; document.querySelector("main").appendChild(seccion);
    let lista = [], ocupado = false;
    async function cargar() {
        lista = await api.listarIntervinientes(id);
        const eventos = await api.listarEventos(id), nombres = new Map();
        for (const r of lista) nombres.set(r.id_persona, window.SSALFER_CONTEXTO.nombrePersona(await window.SSALFER_CONTEXTO.persona(r.id_persona)));
        seccion.innerHTML = `<h2>Intervinientes del trámite</h2>${g.boton("Agregar interviniente", "agregar")}${g.tabla([{ titulo: "Persona", valor: r => nombres.get(r.id_persona) }, { titulo: "Participación", valor: r => f.etiquetaCodigo(r.rol) }, { titulo: "Evento", valor: r => { const evento = eventos.find(e => e.id_evento_fifonafe === r.id_evento_fifonafe); return evento ? `Evento ${evento.ordinal} · ${f.formatearFecha(evento.fecha_evento || evento.fecha_oficio)}` : "Sin evento asociado"; } }, { titulo: "Representación ORV", valor: r => r.id_orv_integrante ? "Acreditada para el evento" : "Sin vínculo ORV" }], lista, r => g.boton("Dar de baja", "baja", r.id_interviniente_fifonafe), "Aún no hay intervinientes. Puedes agregar una persona del núcleo.")}`;
    }
    async function agregar() {
        const [directorio, eventos, orvs, cargos] = await Promise.all([window.SSALFER_DIRECTORIO.listar(pn), api.listarEventos(id), window.OrvAPI.listarPorProyectoNucleo(pn), window.CatalogosAPI.obtenerOperativo("cargo_orv")]);
        const integrantes = [];
        for (const orv of orvs) for (const integrante of await window.OrvAPI.listarIntegrantes(orv.id_orv, true)) integrantes.push({ ...integrante, nombreOrv: orv.numero_orv || "Órgano de representación" });
        const c = (nombre, etiqueta, extra = {}) => ({ nombre, etiqueta, ...extra });
        const resultado = await g.formulario({ titulo: "Agregar interviniente", introduccion: directorio.fallos.length ? "El directorio está incompleto. Algunas fuentes no pudieron consultarse; puedes cerrar y reintentar." : "La acreditación ORV corresponde a la persona y a su vigencia en la fecha del evento.", campos: [c("id_persona", "Persona", { requerido: true, numerico: true, opciones: directorio.personas.map(p => ({ valor: p.id_persona, texto: window.SSALFER_CONTEXTO.nombrePersona(p) })) }), c("rol", "Participación", { requerido: true, opciones: g.opciones(["solicitante", "representante", "titular", "beneficiario", "receptor_designado"]) }), c("id_evento_fifonafe", "Evento del trámite", { numerico: true, opciones: eventos.map(e => ({ valor: e.id_evento_fifonafe, texto: `Evento ${e.ordinal} · ${e.numero_oficio || "Sin oficio"} · ${f.formatearFecha(e.fecha_evento || e.fecha_oficio)}` })) }), c("id_orv_integrante", "Acreditación ORV de la persona", { numerico: true, opciones: [], ayuda: "Selecciona primero persona y evento con fecha." }), c("observaciones", "Observaciones", { tipo: "textarea" })], preparar: form => {
            const persona = form.elements.id_persona, evento = form.elements.id_evento_fifonafe, orv = form.elements.id_orv_integrante;
            const actualizar = () => {
                orv.replaceChildren(new Option("Sin acreditación ORV", ""));
                const acto = eventos.find(e => e.id_evento_fifonafe === Number(evento.value)), fecha = acto?.fecha_evento || acto?.fecha_oficio;
                orv.disabled = !fecha || !persona.value; if (orv.disabled) return;
                integrantes.filter(i => i.id_persona === Number(persona.value) && (!i.fecha_inicio || i.fecha_inicio <= fecha) && (!i.fecha_fin || i.fecha_fin >= fecha)).forEach(i => orv.add(new Option(`${i.nombreOrv} · ${cargos.find(c => c.id_catalogo_opcion === i.id_cargo)?.nombre || "Cargo registrado"} · ${f.formatearFecha(i.fecha_inicio)} — ${f.formatearFecha(i.fecha_fin)}`, i.id_orv_integrante)));
            };
            persona.addEventListener("change", actualizar); evento.addEventListener("change", actualizar); actualizar();
            const nuevo = document.createElement("button"); nuevo.type = "button"; nuevo.className = "btn-secundario"; nuevo.textContent = "Registrar persona nueva"; persona.after(nuevo);
            nuevo.addEventListener("click", async () => { nuevo.disabled = true; try { const p = await window.SSALFER_DIRECTORIO.registrar(pn); if (p) { persona.add(new Option(window.SSALFER_CONTEXTO.nombrePersona(p), p.id_persona)); persona.value = p.id_persona; actualizar(); } } catch(error) { window.ClienteAPI.mostrarErrorAPI(error); } finally { nuevo.disabled = false; } });
        }, guardar: datos => api.agregarInterviniente(id, datos) });
        return resultado;
    }
    seccion.addEventListener("click", async event => {
        const b = event.target.closest("[data-gestion]"); if (!b || ocupado) return; ocupado = true;
        try {
            let actualizado;
            if (b.dataset.gestion === "agregar") actualizado = await agregar();
            if (b.dataset.gestion === "baja") actualizado = await g.baja("la participación de esta persona en el trámite", motivo => api.eliminarInterviniente(Number(b.dataset.registro), motivo));
            if (actualizado || b.dataset.gestion === "reintentar") await cargar();
        } catch(error) { window.ClienteAPI.mostrarErrorAPI(error); }
        finally { ocupado = false; }
    });
    try { const tramites = await api.listarPorProyectoNucleo(pn); if (!tramites.some(t => t.id_tramite_fifonafe === id)) throw new Error("El trámite no pertenece al núcleo seleccionado."); await cargar(); }
    catch(error) { seccion.innerHTML = `<p role="alert">${g.e(error.message)}</p>${g.boton("Reintentar", "reintentar")}`; }
});
