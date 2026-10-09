document.addEventListener("DOMContentLoaded", async () => {
    "use strict";
    const id = Number(new URLSearchParams(location.search).get("id_proyecto_nucleo"));
    if (!Number.isSafeInteger(id) || id <= 0) return;
    const api = window.NucleosAPI, g = window.SSALFER_GESTION, f = window.SSALFER_FORMAT;
    const campo = (nombre, etiqueta, extra = {}) => ({ nombre, etiqueta, ...extra });
    const seccion = document.createElement("section"); seccion.className = "ssalfer-gestion-seccion"; seccion.id = "gestionNucleo";
    document.querySelector("main").appendChild(seccion);
    let nucleo, referencias = [], responsables = [], ocupado = false;
    const fecha = valor => f.formatearFecha(valor);
    async function cargar() {
        [nucleo, referencias, responsables] = await Promise.all([api.obtenerProyectoNucleo(id), api.listarReferencias(id), api.listarResponsables(id)]);
        seccion.innerHTML = `<h2><i class="bi bi-sliders" aria-hidden="true"></i> Datos del núcleo en el proyecto</h2><div class="ssalfer-gestion-barra">${g.boton("Editar datos del proyecto-núcleo", "editar-contexto")}${g.boton("Quitar núcleo del proyecto", "baja-contexto")}</div><p>COP planeados: ${g.e(nucleo.total_cops_planeados ?? "Sin especificar")} · Afecta tierras de uso común: ${nucleo.afecta_tuc == null ? "Sin definir" : nucleo.afecta_tuc ? "Sí" : "No"} · Revisión TUC: ${nucleo.tuc_revision_pendiente ? "Pendiente" : "Sin revisión pendiente"}</p><h2>Referencias</h2>${g.boton("Agregar referencia", "nueva-referencia")}${g.tabla([{ titulo: "Tipo", valor: r => f.etiquetaCodigo(r.tipo_referencia) }, { titulo: "Referencia", valor: r => r.valor }, { titulo: "Principal", valor: r => r.es_principal ? "Sí" : "No" }], referencias, r => g.boton("Editar", "editar-referencia", r.id_referencia))}<h2>Responsables del núcleo</h2>${g.boton("Agregar responsable", "nuevo-responsable")}${g.tabla([{ titulo: "Nombre", valor: r => r.nombre }, { titulo: "Cargo", valor: r => r.cargo }, { titulo: "Contacto", valor: r => r.contacto }, { titulo: "Inicio", valor: r => fecha(r.vigencia_inicio) }, { titulo: "Fin", valor: r => fecha(r.vigencia_fin) }, { titulo: "Principal", valor: r => r.es_principal ? "Sí" : "No" }], responsables, r => g.boton("Editar", "editar-responsable", r.id_responsable))}`;
        const poner = (selector, valor) => { const el = document.getElementById(selector); if (el) { el.textContent = valor || ""; if (["residencia","referencia"].includes(selector)) el.closest(".dato").hidden = !valor; } };
        poner("residencia", nucleo.residencia_nombre); poner("referencia", nucleo.referencia_principal);
        const contenedor=document.getElementById("responsableNombre")?.closest(".responsable-datos");
        if(contenedor){
            try{const [asignados,usuarios]=await Promise.all([window.ProyectosAPI.listarUsuarios(nucleo.id_proyecto),window.SSALFER_USUARIOS_PROYECTO.listar()]);
                const nombres=asignados.map(a=>window.SSALFER_USUARIOS_PROYECTO.nombre(usuarios.find(u=>u.id_usuario===a.id_usuario)||{})||"Usuario sin nombre disponible");
                contenedor.innerHTML=nombres.length>2?' <details><summary>'+nombres.length+' usuarios</summary><ul>'+nombres.map(n=>'<li>'+g.e(n)+'</li>').join('')+'</ul></details>':'<p>'+g.e(nombres.join(' · ')||'No hay usuarios asignados al proyecto.')+'</p>';
            }catch{contenedor.textContent="No se pudo consultar el nombre de los usuarios asignados con esta cuenta.";}
        }
    }
    async function editarContexto() {
        const [residencias, motivos] = await Promise.all([g.catalogo("residencia"), g.catalogo("motivo_no_afecta_tuc")]);
        return g.formulario({ titulo: "Datos del núcleo en el proyecto", inicial: nucleo, editar: true, campos: [campo("id_residencia", "Residencia", { opciones: residencias, numerico: true }), campo("total_cops_planeados", "Total de COP planeados", { tipo: "number", min: 0, paso: "1", numerico: true }), campo("afecta_tuc", "Afecta tierras de uso común", { booleano: true, opciones: g.opciones([[true,"Sí"],[false,"No"]]) }), campo("id_motivo_no_afecta_tuc", "Motivo por el que no afecta TUC", { opciones: motivos, numerico: true }), campo("motivo_no_afecta_tuc_detalle", "Detalle del motivo", { tipo: "textarea" }), campo("tuc_revision_pendiente", "Revisión TUC pendiente", { tipo: "checkbox" }), campo("tuc_revision_detalle", "Detalle de la revisión", { tipo: "textarea" })], preparar: form => {
            const actualizar = () => {
                const noAfecta = form.elements.afecta_tuc.value === "false", pendiente = form.elements.tuc_revision_pendiente.checked;
                ["id_motivo_no_afecta_tuc", "motivo_no_afecta_tuc_detalle"].forEach(nombre => { form.elements[nombre].closest("label").hidden = !noAfecta; if (!noAfecta) form.elements[nombre].value = ""; });
                form.elements.tuc_revision_detalle.closest("label").hidden = !pendiente; if (!pendiente) form.elements.tuc_revision_detalle.value = "";
            };
            form.elements.afecta_tuc.addEventListener("change", actualizar); form.elements.tuc_revision_pendiente.addEventListener("change", actualizar); actualizar();
        }, guardar: datos => api.actualizarProyectoNucleo(id, datos) });
    }
    seccion.addEventListener("click", async event => {
        const boton = event.target.closest("[data-gestion]"); if (!boton || ocupado) return; ocupado = true; boton.disabled = true;
        try {
            const accion = boton.dataset.gestion, rid = Number(boton.dataset.registro);
            let resultado;
            if (accion === "editar-contexto") resultado = await editarContexto();
            else if (accion === "baja-contexto") {
                if (await g.baja(`el núcleo ${nucleo.nombre_nucleo} del proyecto. Sus registros dejarán de estar disponibles desde este proyecto`, motivo => api.eliminarProyectoNucleo(id, motivo))) location.href = `/pages/fichaProyecto.html?id=${nucleo.id_proyecto}`;
                return;
            } else if (accion.includes("referencia")) {
                const item = referencias.find(r => r.id_referencia === rid);
                resultado = await g.formulario({ titulo: item ? "Editar referencia" : "Agregar referencia", inicial: item || {}, editar: Boolean(item), campos: [campo("tipo_referencia", "Tipo", { requerido: true, opciones: g.opciones(["consecutivo", "clave_tramo", "numero_tramo", "otro"]), soloLectura: Boolean(item) }), campo("valor", "Referencia", { requerido: true, maximo: 150 }), campo("es_principal", "Principal dentro de este tipo de referencia", { tipo: "checkbox" })], guardar: datos => item ? api.actualizarReferencia(item.id_referencia, datos) : api.crearReferencia(id, datos) });
            } else if (accion.includes("responsable")) {
                const item = responsables.find(r => r.id_responsable === rid);
                const usuarios = await window.SSALFER_USUARIOS_PROYECTO.listar();
                resultado = await g.formulario({ preparar: form => {
                    const label=document.createElement('label');label.className='ssalfer-gestion-campo';label.textContent='Precargar desde un usuario';const select=document.createElement('select');select.add(new Option('Selecciona un usuario',''));usuarios.forEach(u=>select.add(new Option(window.SSALFER_USUARIOS_PROYECTO.nombre(u),u.id_usuario)));label.appendChild(select);const rol=document.createElement('p');form.prepend(label,rol);
                    select.onchange=()=>{const u=usuarios.find(u=>u.id_usuario===Number(select.value));if(!u)return;form.elements.nombre.value=window.SSALFER_USUARIOS_PROYECTO.nombre(u);form.elements.contacto.value=u.correo||'';rol.textContent='Rol del sistema: '+f.etiquetaCodigo(u.rol)+'. El cargo se captura por separado.';};
                }, titulo: item ? "Editar responsable del núcleo" : "Agregar responsable del núcleo", inicial: item || {}, editar: Boolean(item), campos: [campo("nombre", "Nombre", { requerido: true, maximo: 300 }), campo("cargo", "Cargo", { maximo: 200 }), campo("contacto", "Contacto", { maximo: 200 }), campo("vigencia_inicio", "Inicio de vigencia", { tipo: "date" }), campo("vigencia_fin", "Fin de vigencia", { tipo: "date" }), campo("es_principal", "Responsable principal", { tipo: "checkbox" })], validar: datos => datos.vigencia_inicio && datos.vigencia_fin && datos.vigencia_fin < datos.vigencia_inicio ? "El fin de vigencia no puede ser anterior al inicio." : null, guardar: datos => item ? api.actualizarResponsable(item.id_responsable, datos) : api.crearResponsable(id, datos) });
            }
            if (resultado) await cargar();
        } catch (error) { window.ClienteAPI.mostrarErrorAPI(error); }
        finally { ocupado = false; boton.disabled = false; }
    });
    try { await cargar(); } catch (error) { seccion.innerHTML = `<p role="alert">${g.e(error.message)}</p>${g.boton("Reintentar", "recargar")}`; }
    seccion.addEventListener("click", event => { if (event.target.closest('[data-gestion="recargar"]')) cargar().catch(window.ClienteAPI.mostrarErrorAPI); });
});
