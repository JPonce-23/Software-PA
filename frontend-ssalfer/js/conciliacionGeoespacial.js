/* Extensión del gestor: las decisiones usan siempre el contexto que abrió el panel. */
(() => {
    "use strict";
    const api = window.GeoespacialAPI, g = window.SSALFER_GESTION, ui = window.SSALFER_UI;
    const estados = {pendiente:"Pendiente",coincidencia_exacta:"Coincidencia fuerte",candidato:"Requiere revisión",ambiguo:"Varias coincidencias",sin_coincidencia:"Sin coincidencia",confirmado:"Confirmado",rechazado:"Rechazado",ignorado:"Ignorado"};
    const rotulos = {DIMENSION_A_2D:"Se conservaron sólo las coordenadas del plano (XY)",CRS_REPROYECTADO:"Coordenadas transformadas al sistema de visualización",GEOMETRIA_EXISTENTE_DISTINTA:"La geometría reemplaza una versión anterior distinta",NombreNucl:"Núcleo agrario",NombreMuni:"Municipio",NombreEnti:"Entidad",TipoNucleo:"Tipo de núcleo",N__CLEO_AG:"Núcleo agrario",TIPO_N__CL:"Tipo de núcleo",Num_parcela:"Número de parcela",PARCELA:"Referencia de parcela",MUNICIPIO:"Municipio",ESTADO:"Entidad",fuerte:"Coincidencia fuerte",exacta:"Coincidencia exacta",revision:"Requiere revisión"};
    const texto = v => rotulos[v] || window.SSALFER_FORMAT?.etiquetaCodigo(v) || String(v ?? "").replaceAll("_"," ");
    const fecha = v => v ? window.SSALFER_FORMAT.formatearFecha(v) : "Sin fecha";
    const e = g.e;
    const mensaje = error => error.status === 403 ? "Tu cuenta no tiene permiso para realizar esta operación en el proyecto." : String(error.message || "No se pudo completar la consulta.").replace(/features?/gi,"elementos").replace(/staging/gi,"previsualización").replace(/CRS/g,"sistema de coordenadas");
    const fallo = (raiz,error) => { raiz.innerHTML = `<p role="alert">${e(mensaje(error))}</p>`; };
    let proyecto = null, revision = 0, registro = null, pagina = 0, filtro = "", lista = [], mapa, tokenLista = 0, tokenElemento = 0, ocupado = false, puede = false;
    let configuracion, panel, revisiones, detalle, resumenActual = {}, nucleos = new Map();
    const cache = new Map();
    const leer = ruta => { if (!cache.has(ruta)) cache.set(ruta, window.ClienteAPI.get(ruta,{silencioso:true}).catch(err => { cache.delete(ruta); throw err; })); return cache.get(ruta); };
    const opciones = items => items.map(([valor,label]) => `<option value="${e(valor)}">${e(label)}</option>`).join("");
    const atributos = f => Object.entries(f.atributos_originales || {}).filter(([k,v]) => !/^(?:id(?:_|$)|fid$)/i.test(k) && v != null && v !== "");
    const nombreElemento = f => atributos(f).filter(([k]) => /nombre|nucl|parcel|municip|estado|entidad|tipo/i.test(k)).map(([,v]) => v).join(" · ") || `Elemento ${Number(f.indice_feature) + 1}`;
    const observaciones = items => (items || []).map(v => typeof v === "string" ? texto(v) : v.mensaje || v.message || v.descripcion || texto(v.codigo || v.code || "Observación del archivo")).join(" · ");
    function paso(n) { document.querySelectorAll(".geoespacial-paso").forEach((p,i) => { p.classList.toggle("gis-paso-activo",i === n-1); if (i === n-1) p.setAttribute("aria-current","step"); else p.removeAttribute("aria-current"); }); }
    const destino = (d, parcela=false) => d ? [d.nombre_nucleo || "Núcleo sin nombre disponible", parcela ? `Parcela ${d.numero_parcela || "sin referencia"}` : "", d.municipio, d.entidad].filter(Boolean).join(" · ") : "Destino sin nombre disponible";
    const claveDestino = d => `${d.id_proyecto_nucleo}:${d.id_parcela || ""}`;
    const actor = nombre => nombre || "Nombre de usuario no disponible";
    const rango = (p,skip) => p.total == null ? `${p.items.length} registros · total no informado` : `${p.items.length ? skip+1 : 0}–${skip+p.items.length} de ${p.total}`;
    const historial = rows => g.tabla([{titulo:"Acción",valor:r=>texto(r.accion)},{titulo:"Fecha",valor:r=>fecha(r.creado_en)},{titulo:"Quién",valor:r=>actor(r.creado_por_nombre)},{titulo:"Motivo",valor:r=>r.motivo}],rows,null,"Aún no hay decisiones registradas.");
    async function proteger(ejecutar) {
        if (ocupado) return; ocupado = true;
        const selector = document.getElementById("selectorProyectoGeoespacial"); selector.disabled = true;
        try { return await ejecutar(); } catch(err) { ui.toast(mensaje(err),{tipo:"error"}); }
        finally { ocupado = false; selector.disabled = false; }
    }
    async function formulario(datos) {
        return g.formulario({...datos,guardar:async d => { try { return await datos.guardar(d); } catch(err) { throw Error(mensaje(err)); } }});
    }
    async function cargarConfiguracion(actual) {
        try {
            const c = await api.configuracion(proyecto); if (actual !== revision) return;
            configuracion.innerHTML = `<h2>1. Sistema de coordenadas del proyecto</h2><p>Define cómo se miden las coordenadas. El archivo de ejemplo usa UTM zona 14N (EPSG:32614).</p><p>Configuración actual: <strong>EPSG:${Number(c.srid_trabajo)}</strong></p>${puede ? g.boton("Cambiar sistema de coordenadas","crs") : "<p>Consulta de configuración.</p>"}`;
            configuracion.querySelector("button")?.addEventListener("click", () => proteger(async () => {
                const resultado = await formulario({titulo:"Cambiar sistema de coordenadas",introduccion:"Este cambio invalida las previsualizaciones anteriores. Si ya hay geometrías confirmadas, el sistema rechazará el cambio.",campos:[{nombre:"habitual",etiqueta:"Sistema",opciones:g.opciones([["4326","WGS 84 · EPSG:4326"],["32614","UTM zona 14N · EPSG:32614"],["otro","Otro código EPSG"]]),valor:String(c.srid_trabajo),requerido:true},{nombre:"otro",etiqueta:"Otro código EPSG",tipo:"number",numerico:true,min:1,max:998999}],validar:d=>d.habitual === "otro" && !Number.isInteger(d.otro) ? "Indica un código EPSG válido." : null,guardar:d=>api.configurar(proyecto,{srid_trabajo:d.habitual === "otro" ? d.otro : Number(d.habitual)})});
                if (resultado && actual === revision) { registro = null; panel.hidden = true; await cargarConfiguracion(actual); }
            }));
        } catch(err) { if (actual === revision) fallo(configuracion,err); }
    }
    async function cambiarProyecto(p) {
        proyecto = Number(p) || null; ++revision; ++tokenLista; ++tokenElemento; registro = null; mapa?.remove(); mapa = null; panel.hidden = true; detalle.replaceChildren(); cache.clear(); nucleos.clear();
        configuracion.hidden = revisiones.hidden = !proyecto; if (!proyecto) return;
        const actual = revision;
        configuracion.textContent = "Consultando configuración…"; revisiones.textContent = "Consultando revisiones…";
        await Promise.allSettled([cargarConfiguracion(actual),cargarRevisiones(actual),leer(`/proyectos/${proyecto}/nucleos`).then(rows=>{if(actual === revision) nucleos = new Map(rows.map(r=>[r.id_proyecto_nucleo,r]));})]);
    }
    async function mostrar(r) {
        if (Number(r.id_proyecto) !== proyecto) return;
        registro = r; pagina = 0; filtro = ""; ++tokenElemento;
        panel.hidden = false; paso(3);
        panel.innerHTML = `<h2>3. ${r.tipo_objetivo === "derecho_via_proyecto" ? "Revisar derecho de vía" : "Conciliar elementos"}</h2><p>${e(r.nombre_original)} · ${e(texto(r.estado))}</p><p>El mismo archivo con la misma configuración reutiliza su procesamiento. Una entrega con contenido distinto genera un nuevo registro.</p><div data-gis-resumen></div><label>Estado de conciliación<select data-gis-filtro>${opciones([["","Todos"],...Object.entries(estados)])}</select></label><div data-gis-lista></div><div class="ssalfer-gestion-barra">${g.boton("Anterior","anterior")}${g.boton("Siguiente","siguiente")}<span data-gis-pagina></span></div><div data-gis-elemento></div><h2>4. Finalizar</h2><p>La confirmación requiere revisión humana. La conciliación puede ser parcial; resuelve o ignora los candidatos, ambigüedades y errores pendientes.</p>${puede ? g.boton(r.tipo_objetivo === "derecho_via_proyecto" ? "Confirmar versión de DDV" : "Finalizar conciliación","finalizar") : ""}<p>El mapa publicado muestra la versión vigente confirmada. Esta previsualización temporal no confirma ni publica el archivo.</p><div data-gis-ciclos></div>`;
        detalle = panel.querySelector("[data-gis-elemento]");
        panel.querySelector("[data-gis-filtro]").addEventListener("change", event => { filtro=event.target.value; pagina=0; cargarElementos(); });
        await refrescar(); ui.desplazarA(panel);
    }
    async function refrescar() {
        const actual = revision, r = registro; if (!r) return;
        try {
            const resumen = await api.resumen(r.id_importacion); if(actual !== revision || registro !== r) return;
            resumenActual=resumen;
            const labels = {registros_administrativos:"Registros del universo administrativo",features_archivo:"Elementos del archivo",confirmados:"Confirmados",ambiguos:"Varias coincidencias",candidatos:"Coincidencias que requieren revisión",registros_sin_geometria:"Registros sin geometría",features_sin_destino:"Sin coincidencia",ignoradas:"Ignorados",rechazadas:"Rechazados"};
            panel.querySelector("[data-gis-resumen]").innerHTML = `<dl class="gis-resumen">${Object.entries(labels).filter(([k])=>resumen[k]!=null).map(([k,l])=>`<div><dt>${e(l)}</dt><dd>${e(resumen[k])}</dd></div>`).join("")}</dl><p>Formato: ${e(r.formato_detectado)}. Total: ${Number(r.total_features)} elementos. Capas: ${e((r.reporte?.capas||[]).join(", "))}. Coordenadas de origen: ${e(r.crs_original)}; trabajo: EPSG:${Number(r.srid_trabajo)}. Válidos: ${Number(r.validos)}; advertencias: ${Number(r.advertencias)}; errores: ${Number(r.errores)}.</p>`;
            if(r.tipo_objetivo !== "derecho_via_proyecto" && Number(resumen.features_archivo)>0 && Number(resumen.features_sin_destino)===Number(resumen.features_archivo)) {
                const sinDestino=await api.elementos(r.id_importacion,{skip:0,limit:5,estado_conciliacion:"sin_coincidencia"});
                if(actual!==revision || registro!==r)return;
                panel.querySelector("[data-gis-resumen]").insertAdjacentHTML("beforeend",`<aside class="gis-diagnostico"><strong>No hay coincidencias</strong><p>Núcleos vinculados al proyecto: ${nucleos.size}. Vincula a este proyecto los núcleos del archivo y pulsa Nueva conciliación.</p><p>Nombres del archivo sin coincidencia (hasta cinco): ${e(sinDestino.map(nombreElemento).join("; ")||"Consulta los elementos del archivo")}</p><a href="/pages/fichaProyecto.html?id=${proyecto}">Ir a vincular núcleos</a> ${puede?g.boton("Nueva conciliación","reconciliar"):""}</aside>`);
            }
            await cargarElementos(); if(actual !== revision || registro !== r) return;
            if (r.tipo_objetivo !== "derecho_via_proyecto") await cargarCiclos();
        } catch(err) { if (actual === revision && registro === r) fallo(panel.querySelector("[data-gis-resumen]"),err); }
    }
    async function cargarElementos() {
        const actual=++tokenLista, contexto=revision,r=registro; if(!r)return;
        const salida=panel.querySelector("[data-gis-lista]"); salida.textContent="Consultando elementos…";
        try {
            const resultado=await api.paginaElementos(r.id_importacion,{skip:pagina*25,limit:25,estado_conciliacion:filtro}),rows=resultado.items;
            if(actual!==tokenLista || contexto!==revision || registro!==r)return; lista=rows;
            salida.innerHTML=g.tabla([{titulo:"Elemento del archivo",valor:nombreElemento},{titulo:"Resultado",valor:f=>estados[f.estado_conciliacion]||texto(f.estado)},{titulo:"Observaciones",valor:f=>observaciones([...f.advertencias,...f.errores,...f.transformaciones])}],rows,f=>g.boton("Revisar elemento","elemento",f.id_importacion_feature),"No hay elementos con este estado.");
            panel.querySelector('[data-gestion="anterior"]').disabled=pagina===0; panel.querySelector('[data-gestion="siguiente"]').disabled=api.fin(resultado,pagina*25,25);
            panel.querySelector("[data-gis-pagina]").textContent=`Página ${pagina+1} · ${rango(resultado,pagina*25)} elementos`;
        } catch(err){if(actual===tokenLista&&contexto===revision)fallo(salida,err);}
    }
    async function candidatosVigentes(iid, fid, candidatos) {
        const ciclos=[];
        for(let skip=0;;skip+=200){const p=await api.paginaCiclos(iid,{skip,limit:200});ciclos.push(...p.items);if(api.fin(p,skip,200))break;}
        for(const ciclo of ciclos.sort((a,b)=>b.numero_ciclo-a.numero_ciclo)) {
            const detalle=await api.ciclo(iid,ciclo.id_ciclo);
            if(detalle.features.some(f=>f.id_importacion_feature===fid)) return {candidatos:candidatos.filter(c=>c.id_ciclo===ciclo.id_ciclo),universo:new Map((detalle.universo_destinos || []).map(d=>[claveDestino(d),d]))};
        }
        return {candidatos:ciclos.length?[]:candidatos,universo:new Map()};
    }
    async function abrirElemento(fid) {
        const f=lista.find(x=>x.id_importacion_feature===fid); if(!f)return;
        const actual=++tokenElemento,contexto=revision,r=registro;
        detalle.innerHTML="<p>Consultando geometría y propuestas…</p>"; ui.desplazarA(detalle);
        mapa?.remove();mapa=null;
        try {
            const esDDV=r.tipo_objetivo==="derecho_via_proyecto";
            const [geo,candidatosTodos,decisiones]=await Promise.all([api.geometria(r.id_importacion,fid),esDDV?[]:api.candidatos(r.id_importacion,fid),esDDV?[]:api.decisiones(r.id_importacion,fid)]);
            const {candidatos,universo}=esDDV?{candidatos:[],universo:new Map()}:await candidatosVigentes(r.id_importacion,fid,candidatosTodos);
            const nombres=candidatos.map(c=>destino(universo.get(claveDestino(c)),Boolean(c.id_parcela)));
            if(actual!==tokenElemento||contexto!==revision||registro!==r)return;
            detalle.innerHTML=`<section class="ssalfer-gestion-seccion"><h3>${e(nombreElemento(f))}</h3><p><strong>Previsualización, aún no confirmada</strong></p><div class="gis-minimapa" data-gis-mapa></div><dl>${atributos(f).map(([k,v])=>`<dt>${e(texto(k))}</dt><dd>${e(v)}</dd>`).join("")}</dl><p>${e(observaciones([...f.advertencias,...f.errores,...f.transformaciones]))}</p><a href="/pages/mapa.html?id_proyecto=${proyecto}&id_importacion=${r.id_importacion}&id_feature=${fid}">Abrir previsualización en el mapa</a>${esDDV?"":`<h3>Destinos propuestos</h3><p>Seleccionar registra la elección, pero no guarda geometría. Confirmar sí la incorpora al proyecto.</p>${g.tabla([{titulo:"Destino",valor:(_,i)=>i},{titulo:"Revisó",valor:c=>actor(c.usuario_revision_nombre)},{titulo:"Criterio",valor:c=>texto(c.criterio)},{titulo:"Resultado",valor:c=>texto(c.clasificacion)},{titulo:"Coincidencias",valor:c=>c.coincidencias.map(texto).join(" · ")}].map((col,i)=>i===0?{...col,valor:c=>nombres[candidatos.indexOf(c)]}:col),candidatos,c=>puede&&r.estado==="previsualizado"&&!["confirmado","ignorado"].includes(f.estado_conciliacion)&&c.estado!=="rechazado"?g.boton("Seleccionar","seleccionar",c.id_candidato)+g.boton("Confirmar","confirmar",c.id_candidato)+g.boton("Rechazar","rechazar",c.id_candidato):"","No hay destinos propuestos. Puedes ignorar el elemento o realizar una nueva conciliación cuando exista su registro administrativo.")}${puede&&r.estado==="previsualizado"&&!["confirmado","ignorado"].includes(f.estado_conciliacion)?g.boton("Ignorar elemento","ignorar"):""}<h3>Historial de decisiones</h3>${historial(decisiones)}`}</section>`;
            if(window.L && geo.geometry){mapa=L.map(detalle.querySelector("[data-gis-mapa]"));L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(mapa);const capa=L.geoJSON(geo,{style:{color:'#bd7618',dashArray:'6 4'}}).addTo(mapa);if(capa.getBounds().isValid())mapa.fitBounds(capa.getBounds());else{mapa.remove();mapa=null;detalle.querySelector("[data-gis-mapa]").textContent="La geometría está vacía; revisa las observaciones del elemento.";}}
            else detalle.querySelector("[data-gis-mapa]").textContent="No hay geometría disponible para previsualizar.";
            if(esDDV){const info=document.createElement("p");info.textContent=`Componentes poligonales de la previsualización: ${geo.geometry?.type === "MultiPolygon" ? geo.geometry.coordinates.length : geo.geometry?.type === "Polygon" ? 1 : "Sin dato"}. La superficie oficial y el historial de versiones vigentes no están disponibles en esta consulta.`;detalle.appendChild(info);}
            detalle.querySelectorAll("[data-gestion]").forEach(b=>b.addEventListener("click",()=>proteger(async()=>{
                const accion=b.dataset.gestion, candidato=candidatos.find(c=>c.id_candidato===Number(b.dataset.registro));
                const warnings=f.advertencias.length>0 || false;
                let formularioActual;
                const resultado=await formulario({preparar:form=>{formularioActual=form;const aceptar=form.elements.aceptar_advertencias;if(aceptar){aceptar.closest("label").hidden=!warnings;aceptar.required=warnings;}},titulo:`${texto(accion)} elemento`,introduccion:accion==="confirmar"?"La geometría y esta decisión quedarán guardadas en el proyecto.":"Esta acción no incorpora geometría al proyecto.",campos:[...(accion==="confirmar"?[{nombre:"confirmacion_explicita",etiqueta:"Confirmo que revisé el destino y la geometría",tipo:"checkbox",requerido:true},{nombre:"aceptar_advertencias",etiqueta:"Acepto las advertencias de reparación o reemplazo informadas",tipo:"checkbox",requerido:warnings}]:[]),{nombre:"motivo",etiqueta:"Motivo",tipo:"textarea",maximo:250,requerido:["rechazar","ignorar"].includes(accion)}],guardar:async d=>{if(contexto!==revision||registro!==r)throw Error("El proyecto cambió. Abre nuevamente el elemento.");try { return await api.decidir(r.id_importacion,fid,{...d,accion,...(accion!=="ignorar"?{id_candidato:candidato.id_candidato}:{})}); } catch(err) { if(accion==="confirmar" && /advertencias/i.test(err.message)){const aceptar=formularioActual.elements.aceptar_advertencias;aceptar.closest("label").hidden=false;aceptar.required=true;} throw err; }}});
                if(resultado&&contexto===revision&&registro===r){detalle.replaceChildren();await refrescar();await abrirElemento(fid);}
            })));
        }catch(err){if(actual===tokenElemento&&contexto===revision)fallo(detalle,{status:err.status,message:err.status===404 ? "La previsualización o sus propuestas ya no están disponibles. Vuelve a consultar la conciliación." : err.status===0 || !err.status ? "No se pudo consultar la previsualización. Comprueba la conexión y vuelve a intentarlo." : err.message});}
    }
    let tokenCiclos=0, tokenRevisiones=0;
    async function cargarCiclos(skip=0) {
        const r=registro,ctx=revision,salida=panel.querySelector("[data-gis-ciclos]"),token=++tokenCiclos;
        try{const p=await api.paginaCiclos(r.id_importacion,{skip,limit:25});if(ctx!==revision||registro!==r||token!==tokenCiclos)return;
            salida.innerHTML=`<h3>Historial de conciliaciones</h3>${puede?g.boton("Nueva conciliación","reconciliar"):""}${g.tabla([{titulo:"Ciclo",valor:r=>r.numero_ciclo},{titulo:"Fecha",valor:r=>fecha(r.fecha_inicio)},{titulo:"Quién",valor:r=>actor(r.usuario_nombre)},{titulo:"Motivo",valor:r=>r.motivo}],p.items,r=>g.boton("Ver ciclo","ciclo",r.id_ciclo))}<div>${g.boton("Anterior","ciclos-anterior")}${g.boton("Siguiente","ciclos-siguiente")}<span>${e(rango(p,skip))} conciliaciones</span></div>`;
            for(const [accion,salto,inhabilitado] of [["anterior",-25,skip===0],["siguiente",25,api.fin(p,skip,25)]]){const b=salida.querySelector(`[data-gestion="ciclos-${accion}"]`);b.disabled=inhabilitado;b.onclick=event=>{event.stopPropagation();cargarCiclos(skip+salto);};}
        }catch(err){if(ctx===revision&&registro===r&&token===tokenCiclos)fallo(salida,err);}
    }
    async function cargarRevisiones(ctx,estado="pendiente",skip=0,objetivo="",tipo_cambio="") {
        const token=++tokenRevisiones;
        try{const p=await api.paginaRevisiones(proyecto,{estado,skip,limit:25,objetivo,tipo_cambio});if(ctx!==revision||token!==tokenRevisiones)return;
            revisiones.innerHTML=`<h2>Revisiones geoespaciales</h2><label>Estado<select data-revision-estado>${opciones([["","Todos"],["pendiente","Pendiente"],["revisado","Revisado"],["no_aplica","No aplica"],["aplicado","Aplicado"]])}</select></label><label>Capa<select data-revision-objetivo>${opciones([["","Todas"],["ddv","Derecho de vía"],["nucleo","Núcleo"],["parcela","Parcela"]])}</select></label><label>Tipo de cambio<select data-revision-cambio>${opciones([["","Todos"],["aparece_en_nueva_version","Aparece en nueva versión"],["desaparece_en_nueva_version","Desaparece en nueva versión"],["geometria_modificada","Geometría modificada"],["cambio_relacion_ddv","Cambio de relación con DDV"]])}</select></label>${g.tabla([{titulo:"Capa",valor:r=>texto(r.objetivo)},{titulo:"Destino",valor:r=>r.objetivo==="ddv"?"Derecho de vía del proyecto":destino(r.destino,r.objetivo==="parcela")},{titulo:"Cambio",valor:r=>texto(r.tipo_cambio)},{titulo:"Estado",valor:r=>texto(r.estado_revision)},{titulo:"Fecha",valor:r=>fecha(r.creado_en)},{titulo:"Quién",valor:r=>actor(r.creado_por_nombre)}],p.items,r=>g.boton("Consultar revisión","revision",r.id_revision),"No hay revisiones con estos filtros.")}<div class="ssalfer-gestion-barra">${g.boton("Anterior","rev-anterior")}${g.boton("Siguiente","rev-siguiente")}<span>${e(rango(p,skip))} revisiones</span></div><div data-revision-detalle></div>`;
            const select=revisiones.querySelector('[data-revision-estado]'),capa=revisiones.querySelector('[data-revision-objetivo]'),cambio=revisiones.querySelector('[data-revision-cambio]');select.value=estado;capa.value=objetivo;cambio.value=tipo_cambio;
            for(const control of [select,capa,cambio])control.onchange=()=>cargarRevisiones(revision,select.value,0,capa.value,cambio.value);
            revisiones.querySelector('[data-gestion="rev-anterior"]').disabled=skip===0;revisiones.querySelector('[data-gestion="rev-siguiente"]').disabled=api.fin(p,skip,25);
            revisiones.querySelector('[data-gestion="rev-anterior"]').onclick=()=>cargarRevisiones(revision,estado,skip-25,objetivo,tipo_cambio);revisiones.querySelector('[data-gestion="rev-siguiente"]').onclick=()=>cargarRevisiones(revision,estado,skip+25,objetivo,tipo_cambio);
            revisiones.querySelectorAll('[data-gestion="revision"]').forEach(b=>b.onclick=()=>abrirRevision(Number(b.dataset.registro),ctx));
        }catch(err){if(ctx===revision&&token===tokenRevisiones)fallo(revisiones,err);}
    }
    let tokenRevision=0;
    async function abrirRevision(id,ctx){
        const token=++tokenRevision,salida=revisiones.querySelector("[data-revision-detalle]");
        try{const r=await api.revision(id);if(ctx!==revision||token!==tokenRevision)return;
            const label=r.objetivo==="ddv"?"Derecho de vía del proyecto":destino(r.destino,r.objetivo==="parcela");if(ctx!==revision||token!==tokenRevision)return;
            salida.innerHTML=`<h3>${e(label)} · ${e(texto(r.tipo_cambio))}</h3><p>${e(texto(r.subtipo_cambio))} · ${e(fecha(r.creado_en))} · ${e(actor(r.creado_por_nombre))}</p><p>Superficie anterior: ${e(r.area_anterior_m2??"Sin dato")} m² · nueva: ${e(r.area_nueva_m2??"Sin dato")} m² · diferencia: ${e(r.porcentaje_diferencia??"Sin dato")} %</p>${historial(r.decisiones)}${puede?g.boton("Marcar como revisado","revisado")+g.boton("No aplica","no_aplica")+g.boton("Aplicado","aplicado"):""}`;ui.desplazarA(salida);
            salida.querySelectorAll("button").forEach(b=>b.onclick=()=>proteger(async()=>{
                let eventos=[];
                if(b.dataset.gestion==="aplicado"){
                    const ns=await leer(`/proyectos/${proyecto}/nucleos`);
                    for(const n of ns){const rows=await leer(`/proyecto-nucleo/${n.id_proyecto_nucleo}/seguimiento`);eventos.push(...rows.map(row=>({valor:row.id_seguimiento_evento,texto:`${n.nombre_nucleo} · ${fecha(row.fecha_evento)} · ${row.detalle||"Evento de seguimiento"}`})));}
                }
                const clave=crypto.randomUUID();
                const resultado=await formulario({titulo:texto(b.dataset.gestion),campos:[{nombre:"motivo",etiqueta:"Motivo",tipo:"textarea",requerido:true,maximo:250},...(b.dataset.gestion==="aplicado"?[{nombre:"id_seguimiento_evento",etiqueta:"Evento de seguimiento (opcional)",numerico:true,opciones:eventos}]:[])],guardar:d=>{if(ctx!==revision)throw Error("El proyecto cambió.");return api.resolver(id,{...d,accion:b.dataset.gestion,clave_solicitud:clave});}});
                if(resultado&&ctx===revision)await cargarRevisiones(ctx);
            }));
        }catch(err){if(ctx===revision&&token===tokenRevision)fallo(salida,err);}
    }
    document.addEventListener("DOMContentLoaded",async()=>{
        document.querySelectorAll(".geoespacial-paso").forEach((p,i)=>{p.querySelector("strong").textContent=["Sistema de coordenadas","Cargar","Conciliar","Finalizar"][i];p.classList.remove("activo");});paso(1);
        document.getElementById("btnCrearImportacion").addEventListener("click",()=>paso(2));
        configuracion=document.createElement("section");configuracion.className="ssalfer-gestion-seccion";configuracion.hidden=true;
        document.querySelector(".geoespacial-layout").before(configuracion);
        panel=document.createElement("section");panel.className="ssalfer-gestion-seccion gis-conciliacion";panel.hidden=true;panel.id="conciliacionGeoespacial";
        revisiones=document.createElement("section");revisiones.className="ssalfer-gestion-seccion";revisiones.hidden=true;
        document.querySelector("main").append(panel,revisiones);detalle=document.createElement("div");
        const sesion=await window.AuthAPI.requerirSesion();puede=["admin","geografo"].includes(sesion?.user?.rol);
        if(!puede){document.getElementById("btnCrearImportacion").hidden=true;document.getElementById("seccionNuevaImportacion").hidden=true;}
        panel.addEventListener("click",event=>{const b=event.target.closest("[data-gestion]");if(!b||detalle.contains(b)||ocupado)return;const accion=b.dataset.gestion;
            if(accion==="anterior"||accion==="siguiente"){pagina+=accion==="anterior"?-1:1;cargarElementos();return;}
            if(accion==="elemento"){abrirElemento(Number(b.dataset.registro));return;}
            proteger(async()=>{const r=registro,ctx=revision;if(!r)return;
                if(accion==="ciclo"){const c=await api.ciclo(r.id_importacion,Number(b.dataset.registro));if(ctx!==revision||registro!==r)return;await ui.abrirModal({titulo:`Conciliación ${c.numero_ciclo}`,contenido:`<p>${e(c.motivo)}</p><p>${e(fecha(c.fecha_inicio))} · ${e(texto(c.estado))} · ${e(actor(c.usuario_nombre))}</p>${g.tabla([{titulo:"Elemento",valor:(_,i)=>i},{titulo:"Coincidencia",valor:f=>texto(f.estado_matching)},{titulo:"Resultado",valor:f=>texto(f.estado_resultado)}].map((col,i)=>i===0?{...col,valor:f=>`Elemento ${c.features.indexOf(f)+1}`}:col),c.features,null)}`,acciones:[{texto:"Cerrar",valor:true}]});return;}
                if(!puede)return;
                if(accion==="finalizar"){
                    paso(4);const resultado=await formulario({titulo:r.tipo_objetivo==="derecho_via_proyecto"?"Confirmar versión de DDV":"Finalizar conciliación",introduccion:`Coincidencias pendientes: ${resumenActual.candidatos??0}; ambiguos: ${resumenActual.ambiguos??0}; errores informados: ${r.errores}. Si hay pendientes, vuelve a los elementos y resuélvelos o ignóralos.`,campos:[{nombre:"confirmacion_explicita",etiqueta:"Confirmo que revisé los resultados",tipo:"checkbox",requerido:true},...(r.advertencias>0?[{nombre:"aceptar_advertencias",etiqueta:"Acepto las advertencias y reparaciones informadas",tipo:"checkbox",requerido:true}]:[])],guardar:async d=>{try{return await api.confirmar(r.id_importacion,d);}catch(err){filtro="";pagina=0;panel.querySelector("select").value="";await cargarElementos();ui.desplazarA(panel.querySelector("[data-gis-lista]"));throw err;}}});
                    if(resultado&&ctx===revision)await mostrar(resultado);
                }
                if(accion==="reconciliar"){
                    const clave=crypto.randomUUID();const resultado=await formulario({titulo:"Nueva conciliación",introduccion:"Vuelve a comparar con los registros administrativos actuales; conserva el historial de decisiones.",campos:[{nombre:"motivo",etiqueta:"Motivo",requerido:true,maximo:250,tipo:"textarea"},{nombre:"incluir_ambiguos",etiqueta:"Volver a revisar elementos con varias coincidencias",tipo:"checkbox",valor:true},{nombre:"reabrir_rechazados",etiqueta:"Volver a proponer los destinos rechazados",tipo:"checkbox"}],guardar:d=>api.reconciliar(r.id_importacion,{...d,clave_solicitud:clave})});if(resultado&&ctx===revision)await mostrar(await api.obtener(r.id_importacion));
                }
            });
        });
    });
    window.SSALFER_GIS={cambiarProyecto,mostrar,paso};
})();
