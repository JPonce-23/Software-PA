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
        try { for (const orv of await contexto.listar("orv")) for (const integrante of await window.OrvAPI.listarIntegrantes(orv.id, true, false)) ids.add(Number(integrante.id_persona)); }
        catch { fallos.push("Órganos de representación"); }
        const resultados = await Promise.allSettled([...ids].map(id => window.SSALFER_CONTEXTO.persona(id)));
        if (resultados.some(r => r.status === "rejected")) fallos.push("Algunas fichas de personas");
        const personas = resultados.filter(r => r.status === "fulfilled").map(r => r.value).filter(p => incluirInactivas || p.activo !== false).sort((a,b) => window.SSALFER_CONTEXTO.nombrePersona(a).localeCompare(window.SSALFER_CONTEXTO.nombrePersona(b), "es"));
        return { personas, fallos };
    }
    async function registrar(idNucleo) {
        const sesion=await window.AuthAPI.requerirSesion();
        if(!["admin","operador"].includes(sesion?.user?.rol))throw Error("Tu cuenta permite consultar personas, pero no registrarlas.");
        const nucleo = await window.NucleosAPI.obtenerProyectoNucleo(idNucleo);
        const c = (nombre, etiqueta, extra = {}) => ({ nombre, etiqueta, ...extra });
        const persona = await window.SSALFER_GESTION.formulario({ titulo: "Registrar persona nueva", introduccion: `Proyecto: ${nucleo.nombre_proyecto || "Proyecto del núcleo"}. Antes de registrar, verifica las personas del directorio para evitar duplicados.`, campos: [c("nombre", "Nombre", { requerido: true, maximo: 300 }), c("apellido_paterno", "Primer apellido", { maximo: 200 }), c("apellido_materno", "Segundo apellido", { maximo: 200 }), c("curp", "CURP", { maximo: 18 }), c("rfc", "RFC", { maximo: 13 }), c("telefono", "Teléfono", { maximo: 30 }), c("correo_electronico", "Correo electrónico", { tipo: "email", maximo: 320 }), c("datos_identidad_incompletos", "Datos de identidad incompletos", { tipo: "checkbox" })], guardar: datos => window.PersonasAPI.crear(nucleo.id_proyecto, { ...datos, origen_registro: "captura_sistema" }) });
        if (persona) { if (!nuevos.has(Number(idNucleo))) nuevos.set(Number(idNucleo), new Set()); nuevos.get(Number(idNucleo)).add(persona.id_persona); }
        return persona;
    }
    async function seleccionar(idNucleo, opciones = {}) {
        const g=window.SSALFER_GESTION,sesion=await window.AuthAPI.requerirSesion(),captura=["admin","operador"].includes(sesion?.user?.rol);
        let elegido=null,personas=[],revision=0,abort,skip=0,consulta=null;
        await window.SSALFER_UI.abrirModal({titulo:"Buscar persona existente",contenido:`<p>La búsqueda muestra únicamente personas que tu cuenta puede consultar. Seleccionar una persona no crea vínculos ni modifica registros.</p><label class="ssalfer-gestion-campo">Buscar por<select data-persona-criterio><option value="q">Nombre</option><option value="curp">CURP</option><option value="rfc">RFC</option></select></label><label class="ssalfer-gestion-campo">Criterio de búsqueda<input type="search" data-persona-buscar maxlength="300"></label><button type="button" class="btn-secundario" data-persona-consultar>Buscar</button><button type="button" class="btn-secundario" data-persona-contexto>Ver directorio de este núcleo</button><p data-persona-estado role="status">Escribe un criterio para comenzar. Se conservan acentos y caracteres literales; el RFC puede tener más de una coincidencia.</p><label class="ssalfer-gestion-campo">Persona<select data-persona-elegir><option value="">Sin selección</option></select></label><div><button type="button" class="btn-secundario" data-persona-anterior disabled>Anterior</button><button type="button" class="btn-secundario" data-persona-siguiente disabled>Siguiente</button></div>${captura?'<button type="button" class="ssalfer-modal__button" data-persona-nueva>Registrar persona nueva</button>':""}<p data-persona-error role="alert" hidden></p>`,acciones:[{valor:false,texto:"Cancelar"},{valor:true,texto:"Seleccionar",principal:true}],preparar:modal=>{
            const select=modal.querySelector('[data-persona-elegir]'),input=modal.querySelector('[data-persona-buscar]'),criterio=modal.querySelector('[data-persona-criterio]'),estado=modal.querySelector('[data-persona-estado]'),anterior=modal.querySelector('[data-persona-anterior]'),siguiente=modal.querySelector('[data-persona-siguiente]');
            const llenar=()=>{select.replaceChildren(new Option(personas.length?"Selecciona una persona":"Sin coincidencias autorizadas",""));personas.forEach(p=>select.add(new Option([window.SSALFER_CONTEXTO.nombrePersona(p),p.curp,p.rfc].filter(Boolean).join(' · '),p.id_persona)));};
            const invalidar=()=>{++revision;abort?.abort();consulta=null;personas=[];llenar();anterior.disabled=siguiente.disabled=true;estado.textContent="Pulsa Buscar para consultar el nuevo criterio.";};
            input.oninput=invalidar;criterio.onchange=()=>{input.maxLength={q:300,curp:18,rfc:13}[criterio.value];invalidar();};
            async function buscar(desde=0,nueva=true){const actual=++revision;abort?.abort();abort=new AbortController();personas=[];llenar();anterior.disabled=siguiente.disabled=true;
                try{if(nueva)consulta={[criterio.value]:input.value};estado.textContent="Buscando personas autorizadas…";const rows=await window.PersonasAPI.buscar({...consulta,skip:desde,limit:20},{signal:abort.signal,silencioso:true});if(actual!==revision||!modal.isConnected)return;skip=desde;personas=rows;llenar();anterior.disabled=skip===0;siguiente.disabled=rows.length<20;estado.textContent=rows.length?`Página ${Math.floor(skip/20)+1} · ${rows.length} coincidencias autorizadas. Verifica nombre, CURP y RFC antes de seleccionar.`:"Sin coincidencias autorizadas con este criterio. Esto no significa que la persona no exista en el sistema.";
                }catch(error){if(actual===revision&&modal.isConnected){estado.textContent=error.message;consulta=null;}}
            }
            modal.querySelector('[data-persona-consultar]').onclick=()=>buscar();input.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();buscar();}};
            anterior.onclick=()=>buscar(Math.max(0,skip-20),false);siguiente.onclick=()=>buscar(skip+20,false);
            modal.querySelector('[data-persona-contexto]').onclick=async()=>{invalidar();const actual=revision;estado.textContent="Consultando referencias de este núcleo…";try{const r=await listar(idNucleo,opciones);if(actual!==revision||!modal.isConnected)return;personas=r.personas;llenar();estado.textContent=`Directorio de este núcleo: ${personas.length} personas. No representa el padrón completo del sistema.${r.fallos.length?' Consulta incompleta: '+r.fallos.join(', '):''}`;}catch(error){if(actual===revision)estado.textContent=error.message;}};
            modal.querySelector('[data-persona-nueva]')?.addEventListener('click',async event=>{const b=event.currentTarget;b.disabled=true;try{const p=await registrar(idNucleo);if(p){invalidar();personas=[p];llenar();select.value=p.id_persona;estado.textContent="Persona registrada. Selecciónala para continuar; aún no se ha creado una asociación.";}}catch(error){estado.textContent=error.message;}finally{b.disabled=false;}});
        },validar:(aceptar,modal)=>{if(!aceptar)return true;elegido=personas.find(p=>p.id_persona===Number(modal.querySelector('[data-persona-elegir]').value));const error=modal.querySelector('[data-persona-error]');error.hidden=Boolean(elegido);error.textContent="Selecciona una persona de los resultados.";return Boolean(elegido);}});
        ++revision;abort?.abort();return elegido;
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
        const boton = document.createElement("button"); boton.type = "button"; boton.className = "btn-secundario"; boton.textContent = "Buscar persona existente";
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
