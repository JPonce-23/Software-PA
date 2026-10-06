(() => {
    "use strict";
    const nuevos = new Map();
    async function listar(idNucleo, { incluirInactivas = false } = {}) {
        const contexto = window.SSALFER_CONTEXTO.crear(idNucleo), ids = new Set(nuevos.get(Number(idNucleo)) || []);
        const fallos = [];
        for (const tipo of ["parcela_titular", "unidad_agraria_titular", "convenio_compareciente", "tramite_fifonafe_interviniente", "pago"]) {
            try { for (const {item} of await contexto.listar(tipo)) { if (item.id_persona || item.id_persona_beneficiaria) ids.add(Number(item.id_persona || item.id_persona_beneficiaria)); } }
            catch { fallos.push(window.SSALFER_CONTEXTO.nombres[tipo]); }
        }
        try { for (const orv of await contexto.listar("orv")) for (const integrante of await window.OrvAPI.listarIntegrantes(orv.id)) ids.add(Number(integrante.id_persona)); }
        catch { fallos.push("Órganos de representación"); }
        const resultados = await Promise.allSettled([...ids].map(id => window.SSALFER_CONTEXTO.persona(id)));
        if (resultados.some(r => r.status === "rejected")) fallos.push("Algunas fichas de personas");
        const personas = resultados.filter(r => r.status === "fulfilled").map(r => r.value).filter(p => incluirInactivas || p.activo !== false).sort((a,b) => window.SSALFER_CONTEXTO.nombrePersona(a).localeCompare(window.SSALFER_CONTEXTO.nombrePersona(b), "es"));
        return { personas, fallos };
    }
    async function registrar(idNucleo) {
        const nucleo = await window.NucleosAPI.obtenerProyectoNucleo(idNucleo);
        const c = (nombre, etiqueta, extra = {}) => ({ nombre, etiqueta, ...extra });
        const persona = await window.SSALFER_GESTION.formulario({ titulo: "Registrar persona nueva", introduccion: `Proyecto: ${nucleo.nombre_proyecto || "Proyecto del núcleo"}. Antes de registrar, verifica las personas del directorio para evitar duplicados.`, campos: [c("nombre", "Nombre", { requerido: true, maximo: 300 }), c("apellido_paterno", "Primer apellido", { maximo: 200 }), c("apellido_materno", "Segundo apellido", { maximo: 200 }), c("curp", "CURP", { maximo: 18 }), c("rfc", "RFC", { maximo: 13 }), c("telefono", "Teléfono", { maximo: 30 }), c("correo_electronico", "Correo electrónico", { tipo: "email", maximo: 320 }), c("datos_identidad_incompletos", "Datos de identidad incompletos", { tipo: "checkbox" })], guardar: datos => window.PersonasAPI.crear(nucleo.id_proyecto, { ...datos, origen_registro: "captura_sistema" }) });
        if (persona) { if (!nuevos.has(Number(idNucleo))) nuevos.set(Number(idNucleo), new Set()); nuevos.get(Number(idNucleo)).add(persona.id_persona); }
        return persona;
    }
    async function seleccionar(idNucleo, opciones = {}) {
        const { personas, fallos } = await listar(idNucleo, opciones), g = window.SSALFER_GESTION;
        let elegido = null;
        await window.SSALFER_UI.abrirModal({ titulo: "Personas del núcleo", contenido: `<p>Personas referenciadas en los registros de este núcleo. Este directorio no incluye a todas las personas del sistema.</p>${fallos.length ? `<p role="alert">Consulta incompleta: ${g.e(fallos.join(", "))}. Puedes cerrar y volver a abrir para reintentar.</p>` : ""}<label class="ssalfer-gestion-campo">Buscar por nombre o CURP en este directorio<input type="search" data-persona-buscar></label><label class="ssalfer-gestion-campo">Persona<select data-persona-elegir></select></label><button type="button" class="ssalfer-modal__button" data-persona-nueva>Registrar persona nueva</button><p data-persona-error role="alert" hidden></p>`, acciones: [{ valor: false, texto: "Cancelar" }, { valor: true, texto: "Seleccionar", principal: true }], preparar: modal => {
            const select = modal.querySelector("[data-persona-elegir]"), busqueda = modal.querySelector("[data-persona-buscar]");
            const llenar = () => { const q = busqueda.value.trim().toLocaleLowerCase("es"); const lista = personas.filter(p => `${window.SSALFER_CONTEXTO.nombrePersona(p)} ${p.curp || ""}`.toLocaleLowerCase("es").includes(q)); select.replaceChildren(new Option(lista.length ? "Selecciona una persona" : "Sin personas coincidentes", "")); lista.forEach(p => select.add(new Option(`${window.SSALFER_CONTEXTO.nombrePersona(p)}${p.curp ? ` · ${p.curp}` : ""}${p.activo === false ? " · Dada de baja" : ""}`, p.id_persona))); };
            llenar(); busqueda.addEventListener("input", llenar);
            modal.querySelector("[data-persona-nueva]").addEventListener("click", async event => { const boton = event.currentTarget; boton.disabled = true; try { const persona = await registrar(idNucleo); if (persona) { personas.push(persona); busqueda.value = ""; llenar(); select.value = persona.id_persona; } } catch(error) { window.ClienteAPI.mostrarErrorAPI(error); } finally { boton.disabled = false; } });
        }, validar: (aceptar, modal) => {
            if (!aceptar) return true;
            elegido = personas.find(p => p.id_persona === Number(modal.querySelector("[data-persona-elegir]").value));
            const error = modal.querySelector("[data-persona-error]"); error.hidden = Boolean(elegido); error.textContent = "Selecciona una persona del directorio."; return Boolean(elegido);
        } });
        return elegido;
    }
    async function resolverNucleo() {
        const params = new URLSearchParams(location.search), directo = Number(params.get("id_proyecto_nucleo")); if (directo > 0) return directo;
        if (params.get("id_afectacion")) return (await window.AfectacionesAPI.obtener(params.get("id_afectacion"))).id_proyecto_nucleo;
        if (params.get("id_convenio")) { const convenio = await window.ConveniosAPI.obtener(params.get("id_convenio")); return convenio.id_proyecto_nucleo || (await window.AfectacionesAPI.obtener(convenio.id_afectacion)).id_proyecto_nucleo; }
        return null;
    }
    function conectar(select) {
        if (select.dataset.directorioConectado) return;
        select.dataset.directorioConectado = "true";
        const boton = document.createElement("button"); boton.type = "button"; boton.className = "btn-secundario"; boton.textContent = "Elegir del directorio o registrar persona";
        select.insertAdjacentElement("afterend", boton);
        boton.addEventListener("click", async () => { boton.disabled = true; try {
            const id = await resolverNucleo(); if (!id) throw new Error("Abre este formulario desde el núcleo o su afectación.");
            const persona = await seleccionar(id); if (!persona || !select.isConnected) return;
            let opcion = [...select.options].find(o => Number(o.value) === persona.id_persona);
            const nombre = window.SSALFER_CONTEXTO.nombrePersona(persona);
            if (!opcion) { opcion = new Option(nombre, persona.id_persona); select.add(opcion); }
            opcion.dataset.nombre = nombre; select.value = persona.id_persona; select.dispatchEvent(new Event("change", { bubbles: true }));
        } catch(error) { window.ClienteAPI.mostrarErrorAPI(error); } finally { boton.disabled = false; } });
    }
    document.addEventListener("DOMContentLoaded", () => {
        const buscar = () => document.querySelectorAll('select#idPersona, select#idPersonaBeneficiaria, select#personaCompareciente, select[name*="[id_persona]"]').forEach(conectar);
        buscar(); new MutationObserver(buscar).observe(document.querySelector("main") || document.body, { childList: true, subtree: true });
    });
    window.SSALFER_DIRECTORIO = Object.freeze({ listar, seleccionar, registrar, resolverNucleo });
})();
