/* Seguimiento por COP: evidencia y etiquetas manuales independientes. */
document.addEventListener("DOMContentLoaded", async () => {
    "use strict";
    const $ = id => document.getElementById(id);
    const e = valor => String(valor ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const fecha = v => window.SSALFER_FORMAT.formatearFecha(v);
    const api = window.ClienteAPI;
    const dialogo = $("sfDetalle");
    const nombres = {espera_firma:"En espera de firma", bienes_distintos_tierra:"Bienes distintos a la tierra", observaciones_importantes:"Observaciones importantes"};
    const pasos = [["oficio_fifonafe_dgaopr","Oficio FIFONAFE a DGAOPR/Representación"],["oficio_dgaopr_representacion","Oficio DGAOPR a Representación"],["respuesta_representacion_dgaopr","Respuesta de Representación a DGAOPR"],["respuesta_dgaopr_fifonafe","Respuesta final a FIFONAFE"]];
    let revision=0, skip=0, resultado=null, editando=null, permisos=false, origenFoco=null;
    const error = err => { $("sfError").textContent=err?.mensaje || err?.message || "No fue posible consultar los datos."; $("sfError").hidden=false; };
    const badge = (texto,color="") => `<span class="sf-etiqueta ${color}">${e(texto)}</span>`;
    function conflicto(cop) {
        const valores=cop.tramites.map(t=>t.hay_conflictos);
        if(valores.some(v=>v===true))return badge("Con conflicto","sf-rojo");
        if(valores.length && valores.every(v=>v===false))return badge("Sin conflicto registrado","sf-verde");
        return badge("Conflicto: sin información completa");
    }
    function avance(cop) {
        if(!cop.tramites.length)return badge("Sin trámite vinculado");
        if(cop.tramites.every(t=>t.estatus==="completo"))return badge("Trámite registrado como completo","sf-verde");
        if(cop.tramites.every(t=>t.estatus==="cancelado"))return badge("Trámite cancelado");
        const abiertos=cop.tramites.filter(t=>!["completo","cancelado"].includes(t.estatus));
        if(abiertos.length===1){
            const eventos=abiertos[0].eventos || [];
            const ciclo=Math.max(1,...eventos.map(ev=>Number(ev.ciclo_consulta)||1));
            const codigos=new Set(eventos.filter(ev=>(Number(ev.ciclo_consulta)||1)===ciclo).map(ev=>ev.codigo));
            if((codigos.has("oficio_dgaopr_representacion") && !codigos.has("respuesta_representacion_dgaopr")) || (codigos.has("consulta_conflictos_enviada") && !codigos.has("respuesta_conflictos_acreditada")))return badge("Respuesta pendiente de registro","sf-azul");
            if(codigos.has("respuesta_representacion_dgaopr") && !codigos.has("respuesta_dgaopr_fifonafe"))return badge("Respuesta final pendiente de registro","sf-azul");
            if(codigos.has("oficio_fifonafe_dgaopr") && !codigos.has("oficio_dgaopr_representacion"))return badge("Envío a Representación pendiente de registro","sf-azul");
        }
        return badge("Seguimiento pendiente","sf-azul");
    }
    const manuales = cop => cop.etiquetas.filter(t=>t.habilitada).map(t=>badge(nombres[t.codigo], t.codigo==="bienes_distintos_tierra"?"sf-morado":"sf-amarillo")).join("");
    const titulo = cop => `COP ${cop.ambito} · ${cop.nombre_nucleo} · Consecutivo ${cop.consecutivo} · #${cop.id_convenio}`;
    function abrir(tituloModal, html) {
        origenFoco=document.activeElement;$("sfTitulo").textContent=tituloModal;$("sfDetalleContenido").innerHTML=html;
        if(!dialogo.open)dialogo.showModal();dialogo.scrollTop=0;$("sfCerrar").focus({preventScroll:true});
    }
    $("sfCerrar").onclick=()=>dialogo.close();
    dialogo.addEventListener("close",()=>{editando=null;origenFoco?.focus();});
    async function cargar() {
        const actual=++revision, id=$("sfProyecto").value;
        resultado=null;$("sfListado").replaceChildren();$("sfError").hidden=true;
        $("sfAnterior").disabled=true;$("sfSiguiente").disabled=true;$("sfRegistrar").disabled=!id;
        $("sfIndividuales").textContent="—";$("sfColectivos").textContent="—";$("sfPagina").textContent="";
        if(!id){$("sfEstado").textContent="Selecciona un proyecto para consultar sus COP.";return;}
        $("sfEstado").textContent="Consultando COP y seguimiento…";$("sfListado").setAttribute("aria-busy","true");
        try {
            const params=new URLSearchParams({skip,limit:50});if($("sfAmbito").value)params.set("ambito",$("sfAmbito").value);
            const data=await api.get(`/proyectos/${id}/fifonafe/seguimiento?${params}`);
            if(actual!==revision)return;resultado=data;
            $("sfIndividuales").textContent=data.individuales;$("sfColectivos").textContent=data.colectivos;
            $("sfListado").innerHTML=data.items.map(cop=>`<button class="sf-cop" data-cop="${cop.id_convenio}"><h3>${e(titulo(cop))}</h3><p>${e(cop.municipio)} · ${e(cop.entidad)}</p>${avance(cop)}${conflicto(cop)}${manuales(cop)}<p>Ver detalle y oficios</p></button>`).join("") || "<p>No hay COP registrados con este filtro.</p>";
            $("sfEstado").textContent=`${data.total} COP en esta consulta. Los totales superiores corresponden a todo el proyecto.`;
            $("sfPagina").textContent=`Página ${Math.floor(skip/50)+1} de ${Math.max(1,Math.ceil(data.total/50))}`;
            $("sfAnterior").disabled=skip===0;$("sfSiguiente").disabled=!data.hay_mas;
        } catch(err) {if(actual===revision){error(err);$("sfEstado").textContent="No se pudo cargar el seguimiento. Usa Actualizar para reintentar.";}}
        finally {if(actual===revision)$("sfListado").removeAttribute("aria-busy");}
    }
    function eventoHtml(evento) {
        return `<div class="sf-evento"><strong>${e(evento.nombre)}</strong>${evento.ciclo_consulta?`<p>Ciclo de consulta: ${e(evento.ciclo_consulta)}</p>`:""}<p>Oficio: ${e(evento.numero_oficio || "Sin número registrado")} · Fecha: ${e(fecha(evento.fecha_oficio || evento.fecha_evento))}</p><p>${e([evento.origen,evento.destino].filter(Boolean).join(" → "))}</p>${evento.observaciones?`<details><summary>Observaciones</summary><p>${e(evento.observaciones)}</p></details>`:""}${evento.id_documento?`<button class="btn-secundario" data-documento="${evento.id_documento}">Descargar oficio</button>`:"<small>Sin documento vinculado a este movimiento.</small>"}</div>`;
    }
    function verCop(cop) {
        editando=cop;
        const tramites=cop.tramites.map(t=>`<section class="sf-tramite"><h3>Trámite ${e(t.referencia_expediente || `#${t.id_tramite_fifonafe}`)}</h3><p>Fecha de acuse: ${e(fecha(t.acuse_fifonafe_fecha))}</p><p>Estado registrado: ${e(t.estatus)}. Relacionado mediante las afectaciones del COP; puede abarcar otros convenios.</p><p>Conflicto: ${t.hay_conflictos===true?"Sí":t.hay_conflictos===false?"No":"Sin información"}</p>${t.resultado_no_conflictos?`<p>${e(t.resultado_no_conflictos)}</p>`:""}<h4>Oficios y respuestas</h4>${pasos.map(([codigo,nombre])=>{const registrados=t.eventos.filter(ev=>ev.codigo===codigo);return registrados.length?registrados.map(eventoHtml).join(""):`<div class="sf-evento"><strong>${e(nombre)}</strong><p>Pendiente de registro. No acredita que el oficio no se haya enviado.</p></div>`;}).join("")}${t.eventos.filter(ev=>!pasos.some(([codigo])=>codigo===ev.codigo)).map(eventoHtml).join("")}<a class="btn-secundario" href="/pages/fichaFifonafe.html?id_fifonafe=${t.id_tramite_fifonafe}&id_proyecto_nucleo=${t.id_proyecto_nucleo}">Consultar o actualizar trámite</a></section>`).join("");
        abrir(titulo(cop),`<p>${e(cop.municipio)} · ${e(cop.entidad)} · Firma del COP: ${e(fecha(cop.fecha_firma))}</p>${avance(cop)}${conflicto(cop)}${manuales(cop)}<p>Personas registradas en el convenio: ${e((cop.personas || []).join(", ") || "Sin personas vinculadas")}</p><button class="btn-secundario" data-archivos-cop="${cop.id_convenio}">Consultar archivos del COP</button><div id="sfArchivosCop"></div><p><a href="/pages/fichaConvenio.html?id_convenio=${cop.id_convenio}&id_proyecto_nucleo=${cop.id_proyecto_nucleo}">Consultar convenio y sus documentos</a></p>${tramites || `<p>No hay un trámite FIFONAFE relacionado con las afectaciones de este COP.</p><a class="btn-secundario" href="/pages/fifonafe.html?id_proyecto_nucleo=${cop.id_proyecto_nucleo}">Registrar o vincular seguimiento FIFONAFE</a>`}<h3>Etiquetas manuales</h3>${cop.etiquetas.map(t=>`<p>${badge(nombres[t.codigo])} ${t.habilitada?"Activada":"Retirada"}: ${e(t.motivo)} · ${e(fecha(t.creado_en))} · Usuario #${t.creado_por}</p>`).join("") || "<p>Sin etiquetas registradas.</p>"}${permisos && resultado.etiquetas_disponibles?`<form id="sfEtiquetaForm" class="sf-etiquetas-form"><label>Etiqueta<select name="codigo">${Object.entries(nombres).map(([k,v])=>`<option value="${k}">${e(v)}</option>`).join("")}</select></label><label class="sf-check"><input type="checkbox" name="habilitada" checked> Activar etiqueta (desmarca para retirarla)</label><label>Motivo obligatorio<textarea name="motivo" minlength="5" maxlength="2000" required></textarea></label><p id="sfEtiquetaError" role="alert"></p><button class="btn-principal" type="submit">Guardar etiqueta</button></form>`:permisos?"<p>La captura de etiquetas requiere actualizar la base de datos.</p>":""}<div id="sfDocumentosMensaje" role="status"></div>`);
        $("sfEtiquetaForm")?.addEventListener("submit",async ev=>{
            ev.preventDefault();const form=ev.currentTarget,btn=form.querySelector('button[type="submit"]'),datos=new FormData(form);btn.disabled=true;
            try {await api.post(`/convenios/${cop.id_convenio}/fifonafe/etiquetas`,{codigo:datos.get("codigo"),habilitada:datos.has("habilitada"),motivo:String(datos.get("motivo")).trim()});await cargar();if(dialogo.open && resultado && editando?.id_convenio===cop.id_convenio){const vigente=resultado.items.find(c=>c.id_convenio===cop.id_convenio);if(vigente)verCop(vigente);}}
            catch(err){$("sfEtiquetaError").textContent=err.mensaje||err.message;btn.disabled=false;}
        });
    }
    $("sfListado").onclick=ev=>{const btn=ev.target.closest('[data-cop]');if(btn){const cop=resultado?.items.find(c=>c.id_convenio===Number(btn.dataset.cop));if(cop)verCop(cop);}};
    $("sfDetalleContenido").addEventListener("click",async ev=>{
        const archivos=ev.target.closest('[data-archivos-cop]');
        if(archivos){
            archivos.disabled=true;const contenedor=$("sfArchivosCop");
            try {const docs=await window.DocumentosAPI.listarPorEntidad("convenio",Number(archivos.dataset.archivosCop));
                if(contenedor?.isConnected)contenedor.innerHTML=docs.map(d=>`<p>${e(d.titulo || "Documento del convenio")} <button class="btn-secundario" data-documento="${d.id_documento}">Descargar</button></p>`).join("")||"<p>No hay documentos vinculados al convenio.</p>";
            }catch(err){if(contenedor?.isConnected)contenedor.textContent=err.message;}finally{archivos.disabled=false;}return;
        }
        const btn=ev.target.closest('[data-documento]');if(!btn)return;btn.disabled=true;const mensaje=$("sfDocumentosMensaje");
        try {const versions=await window.DocumentosAPI.listarVersiones(Number(btn.dataset.documento));const latest=[...versions].sort((a,b)=>b.numero_version-a.numero_version)[0];if(!latest)throw new Error("El documento está registrado, pero aún no tiene un archivo cargado.");await window.SSALFER_GESTION.descargar(`/documentos/versiones/${latest.id_documento_version}/descarga`,latest.nombre_original);if(mensaje?.isConnected)mensaje.textContent="Descarga preparada.";}
        catch(err){if(mensaje?.isConnected)mensaje.textContent=err.mensaje||err.message;}finally{btn.disabled=false;}
    });
    $("sfProyecto").onchange=()=>{skip=0;if(dialogo.open)dialogo.close();const url=new URL(location.href);url.searchParams.set("id_proyecto",$("sfProyecto").value);history.replaceState(null,"",url);$("btnVolver").onclick=()=>location.href=`/pages/fichaProyecto.html?id=${encodeURIComponent($("sfProyecto").value)}`;cargar();};
    $("sfAmbito").onchange=()=>{skip=0;cargar();};$("sfActualizar").onclick=()=>cargar();
    $("sfAnterior").onclick=()=>{skip=Math.max(0,skip-50);cargar();};$("sfSiguiente").onclick=()=>{skip+=50;cargar();};
    $("sfRegistrar").onclick=async()=>{
        const id=$("sfProyecto").value,actual=revision;abrir("Registrar COP o vincular seguimiento","<p>Consultando núcleos…</p>");
        try {const nucleos=[];for(let offset=0;;offset+=200){const lote=await api.get(`/proyectos/${id}/nucleos?skip=${offset}&limit=200`);if(actual!==revision||!dialogo.open)return;nucleos.push(...lote);if(lote.length<200)break;}
            $("sfDetalleContenido").innerHTML=`<p>El COP pertenece a las afectaciones de un núcleo. Elige el núcleo para registrar el convenio o relacionar su seguimiento FIFONAFE.</p><label>Núcleo<select id="sfNucleo"><option value="">Selecciona un núcleo</option>${nucleos.map(n=>`<option value="${n.id_proyecto_nucleo}">${e(n.nombre_nucleo)}</option>`).join("")}</select></label><div id="sfAccionesRegistro"></div>`;
            $("sfNucleo").onchange=async()=>{const pn=$("sfNucleo").value;$("sfAccionesRegistro").replaceChildren();if(!pn)return;try{const afectaciones=await window.AfectacionesAPI.listarPorProyectoNucleo(pn);if(!$("sfNucleo")||$("sfNucleo").value!==pn)return;$("sfAccionesRegistro").innerHTML=`<p><a href="/pages/fifonafe.html?id_proyecto_nucleo=${pn}">Registrar o vincular trámite FIFONAFE a las afectaciones</a></p><h3>Registrar COP</h3>${afectaciones.map(a=>`<p><a href="/pages/nuevoConvenio.html?id_afectacion=${a.id_afectacion}&id_proyecto_nucleo=${pn}">Nueva captura · afectación ${a.id_afectacion} · ${e(a.tipo_afectacion)}</a></p>`).join("")||`<p>Primero registra una afectación.</p><a href="/pages/afectacion.html?id_proyecto_nucleo=${pn}">Registrar afectación</a>`}`;}catch(err){if($("sfAccionesRegistro"))$("sfAccionesRegistro").textContent=err.message;}};
        }catch(err){if(dialogo.open)$("sfDetalleContenido").textContent=err.message;}
    };
    try {const sesion=await window.AuthAPI.requerirSesion();if(!sesion)return;permisos=["admin","operador"].includes(sesion.user.rol);$("sfRegistrar").hidden=!permisos;const proyectos=await window.ProyectosAPI.listar();proyectos.forEach(p=>$("sfProyecto").add(new Option(p.nombre_proyecto,p.id_proyecto)));$("sfProyecto").value=new URLSearchParams(location.search).get("id_proyecto")||"";await cargar();}catch(err){error(err);}
});
