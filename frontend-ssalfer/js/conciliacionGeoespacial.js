/* Extensión del gestor: las decisiones usan siempre el contexto que abrió el panel. */
document.addEventListener("DOMContentLoaded", async () => {
    "use strict";
    const sesion = await window.SSALFER_SESION_LISTA;
    if (!["admin", "geografo"].includes(sesion?.user?.rol)) return;

    const api = window.GeoespacialAPI, g = window.SSALFER_GESTION, ui = window.SSALFER_UI;
    const estados = {pendiente:"Pendiente",coincidencia_exacta:"Coincidencia fuerte",candidato:"Requiere revisión",ambiguo:"Varias coincidencias",sin_coincidencia:"Sin coincidencia",confirmado:"Confirmado",rechazado:"Rechazado",ignorado:"Ignorado"};
    const rotulos = {DIMENSION_A_2D:"Se conservaron sólo las coordenadas del plano (XY)",CRS_REPROYECTADO:"Coordenadas transformadas al sistema de visualización",GEOMETRIA_EXISTENTE_DISTINTA:"La geometría reemplaza una versión anterior distinta",NombreNucl:"Núcleo agrario",NombreMuni:"Municipio",NombreEnti:"Entidad",TipoNucleo:"Tipo de núcleo",N__CLEO_AG:"Núcleo agrario",TIPO_N__CL:"Tipo de núcleo",Num_parcela:"Número de parcela",PARCELA:"Referencia de parcela",MUNICIPIO:"Municipio",ESTADO:"Entidad",fuerte:"Coincidencia fuerte",exacta:"Coincidencia exacta",revision:"Requiere revisión"};
    const texto = v => rotulos[v] || window.SSALFER_FORMAT?.etiquetaCodigo(v) || String(v ?? "").replaceAll("_"," ");
    const fecha = v => v ? window.SSALFER_FORMAT.formatearFecha(v) : "Sin fecha";
    const e = g.e;
    // El contenido se construye localmente y los valores del servidor se escapan antes.
    const ayuda = (titulo, contenido) => `<details class="gis-ayuda"><summary>${e(titulo)}</summary><div class="gis-ayuda-contenido">${contenido}</div></details>`;
    const mensaje = error => /geometría cambió desde (staging|previsualización)/i.test(error.message || "") ? "La geometría guardada cambió después de preparar esta carga. El checkbox no actualiza la propuesta ni permite sobrescribir ese cambio. Verifica primero el tipo de carga: si un archivo de parcelas figura como Núcleos agrarios, abre o prepara su carga de Parcelas. Si el tipo es correcto, realiza una Nueva conciliación y revisa las propuestas actualizadas antes de confirmar." : error.status === 403 ? "Tu cuenta no tiene permiso para realizar esta operación en el proyecto." : String(error.message || "No se pudo completar la consulta.").replace(/features?/gi,"elementos").replace(/staging/gi,"previsualización").replace(/CRS/g,"sistema de coordenadas");
    const fallo = (raiz,error) => { raiz.innerHTML = `<p role="alert">${e(mensaje(error))}</p>`; };
    let proyecto = null, revision = 0, registro = null, pagina = 0, filtro = "", lista = [], mapa, tokenLista = 0, tokenElemento = 0, ocupado = false, puede = false, administrador = false;
    let configuracion, panel, revisiones, detalle, resumenActual = {}, nucleos = new Map();
    const cache = new Map();
    const leer = ruta => { if (!cache.has(ruta)) cache.set(ruta, window.ClienteAPI.get(ruta,{silencioso:true}).catch(err => { cache.delete(ruta); throw err; })); return cache.get(ruta); };
    const opciones = items => items.map(([valor,label]) => `<option value="${e(valor)}">${e(label)}</option>`).join("");
    const atributos = f => Object.entries(f.atributos_originales || {}).filter(([k,v]) => !/^(?:id(?:_|$)|fid$)/i.test(k) && v != null && v !== "");
    const nombreElemento = f => atributos(f).filter(([k]) => /nombre|nucl|parcel|municip|estado|entidad|tipo/i.test(k)).map(([,v]) => v).join(" · ") || `Elemento ${Number(f.indice_feature) + 1}`;
    const etiquetaElemento = f => `Elemento ${Number(f.indice_feature) + 1} · ${nombreElemento(f)}`;
    // Una sola lectura de campos para la tabla, los motivos, la búsqueda y el CSV.
    const normalizarCampo=k=>String(k).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
    const datosArchivo = (f, tipo=registro?.tipo_objetivo) => {
        const datos=f.atributos_originales || {};
        const grupos=[['Núcleo',['nombrenucl','nombrenucleo','nucleo','nucleoagrario','nucleoag','ncleoag']],['Municipio',['nombremuni','nombremunicipio','municipio']],['Entidad',['nombreenti','nombreentidad','entidad','estado']],['Tipo de núcleo',['tiponucleo','tiponucle','tiponcl']],['Número de parcela',['numparcela','numeroparcela','noparcela','parcela']]];
        return grupos.filter(([label])=>label!=='Número de parcela' || ['parcela','parcela_gpkg'].includes(tipo) || Object.keys(datos).some(k=>/parcela/i.test(k))).map(([label,alias])=>({label,campos:Object.entries(datos).filter(([k])=>alias.includes(normalizarCampo(k)))}));
    };
    const valorUtil=v=>v!=null && String(v).trim()!=='';
    const valorCampo=(datos,label)=>datos.find(d=>d.label===label)?.campos.filter(([,v])=>valorUtil(v)).map(([,v])=>String(v)).join(' / ') || '';
    const camposArchivo = (f, tipo=registro?.tipo_objetivo) => datosArchivo(f,tipo).map(({label,campos})=>`${label}: ${campos.length?campos.map(([k,v])=>`${valorUtil(v)?String(v):'Vacío'} [${k}]`).join(' / '):'No informado en el archivo'}`).join(' · ');
    const identificadorArchivo=f=>[valorUtil(f.id_externo)?`Folio ${f.id_externo}`:'',Number.isInteger(f.indice_feature)?`Elemento ${f.indice_feature+1} del archivo`:`Registro ${f.id_importacion_feature??'sin identificador disponible'}`].filter(Boolean).join(' · ');
    const lecturaImportacion = (r=registro) => r?.activo === false ? {incluir_inactivas:true} : {};
    const editable = r => puede && r && r.activo !== false;
    const actividadHtml = r => r.activo===false?`<aside class="gis-inactiva"><strong>Dada de baja · Sólo lectura</strong><p>Fecha: ${e(fecha(r.fecha_baja))}. Motivo: ${e(r.motivo_baja || 'No disponible')}. Se conserva el historial; esta consulta no activa la carga.</p></aside>`:'';
    const valorDisponible = v => v == null ? "No disponible" : String(v);
    const codigosDiagnostico = {
        UNIVERSO_DESTINOS_VACIO:"Sin destinos administrativos elegibles",
        IDENTIDAD_NUCLEO_INSUFICIENTE:"Faltan datos para identificar el núcleo",
        CLAVE_SIN_COINCIDENCIA_EN_UNIVERSO:"Clave sin coincidencia en el proyecto",
        NOMBRE_SIN_COINCIDENCIA_EN_UNIVERSO:"Nombre sin coincidencia en el proyecto",
        MUNICIPIO_INCOMPATIBLE:"El municipio no coincide", ENTIDAD_INCOMPATIBLE:"La entidad no coincide",
        TIPO_NUCLEO_INCOMPATIBLE:"El tipo de núcleo no coincide", NUMERO_PARCELA_AUSENTE:"Falta el número de parcela",
        PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO:"Parcela sin coincidencia entre los destinos elegibles",
        VARIANTE_FORMATO_PENDIENTE_REVISION:"Diferencia de formato para revisión humana",
        MULTIPLES_DESTINOS_COMPATIBLES:"Hay varios destinos compatibles",
        ID_ADMINISTRATIVO_SIN_COINCIDENCIA_EN_UNIVERSO:"Identificador administrativo sin coincidencia",
        DIAGNOSTICO_HISTORICO_NO_DISPONIBLE:"Diagnóstico histórico no disponible"
    };
    const historicoSinDiagnostico = d => d?.origen === 'no_disponible' || d?.codigos?.includes('DIAGNOSTICO_HISTORICO_NO_DISPONIBLE');
    const camposEvidencia = {destinos_evaluados:'Destinos evaluados',nucleos_evaluados:'Núcleos evaluados',nucleos_compatibles:'Núcleos compatibles',parcelas_evaluadas:'Parcelas evaluadas',candidatos:'Candidatos'};
    function evidenciaDiagnostico(d) {
        if (!d) return '';
        const ev=d.evidencia || {};
        const datos=Object.entries(camposEvidencia).map(([k,label])=>`${label}: ${valorDisponible(ev[k])}`);
        const descartes=ev.descartes_territoriales;
        datos.push('Descartes territoriales: '+(descartes == null ? 'No disponible' : Object.entries(descartes).map(([k,v])=>`${texto(k)}: ${valorDisponible(v)}`).join('; ')));
        if(ev.variantes_formato?.length) datos.push('Indicios de formato para revisión humana (no establecen equivalencia ni generan candidatos): '+ev.variantes_formato.map(v=>`${v.campo}: ${v.regla === 'DIFERENCIA_CEROS_INICIALES_SEGMENTO_NUMERICO' ? 'Diferencia de ceros iniciales en el segmento numérico' : v.regla}; destinos observados: ${valorDisponible(v.destinos_observados)}`).join('; '));
        return datos.join(' · ');
    }
    function diagnosticoTexto(f, tipo=registro?.tipo_objetivo) {
        const d=f.diagnostico;
        return [diagnosticoElemento(f,tipo),d ? `Origen: ${d.origen}; códigos: ${(d.codigos||[]).join(', ')}; campos evaluados: ${(d.campos_evaluados||[]).join(', ') || 'No registrados'}; ${evidenciaDiagnostico(d)}` : '',f.id_ciclo_conciliacion!=null?`Ciclo de este resultado: ${f.id_ciclo_conciliacion}`:''].filter(Boolean).join(' · ');
    }
    function diagnosticoHtml(f, historico=false) {
        const d=f.diagnostico;
        const mensajeDiagnostico=historico && !d ? 'Diagnóstico no disponible para este resultado histórico.' : diagnosticoElemento(f);
        const ciclo=f.id_ciclo_conciliacion!=null?`<p>Ciclo de este resultado: ${e(f.id_ciclo_conciliacion)}</p>`:'';
        if(!d) return ayuda(historico ? "Diagnóstico histórico no disponible" : "Ver orientación para este elemento", `<p>${e(mensajeDiagnostico)}</p>${ciclo}`);
        return `<div class="gis-diagnostico-detalle"><p>${e(historicoSinDiagnostico(d) ? "Diagnóstico histórico no disponible" : (d.codigos || []).map(c=>codigosDiagnostico[c]).filter(Boolean).join(" · ") || "Diagnóstico disponible")}</p><details class="gis-ayuda"><summary>${historicoSinDiagnostico(d)?"Consultar disponibilidad del diagnóstico":"Ver diagnóstico y evidencia registrados"}</summary><p>${e(mensajeDiagnostico)}</p>${ciclo}<p>El diagnóstico explica la comparación original; no sustituye el estado ni las decisiones posteriores.</p><ul>${(d.codigos||[]).map(c=>`<li>${e(codigosDiagnostico[c] || d.mensaje || 'Diagnóstico informado por el servidor')} <small>(${e(c)})</small></li>`).join('')}</ul><p>Campos evaluados: ${e((d.campos_evaluados||[]).join(', ') || 'No registrados')}</p><p>${e(evidenciaDiagnostico(d))}</p></details></div>`;
    }
    function universoHtml(u, titulo) {
        const disponibilidad={disponible:'Disponible',parcial:'Información histórica parcial',no_disponible:'No disponible'};
        const campos={nucleos_vinculados_activos:'Núcleos vinculados activos',parcelas_elegibles_vinculadas:'Parcelas elegibles vinculadas',destinos_aplicables:'Destinos aplicables'};
        return `<section class="gis-universo"><h3>${e(titulo)}</h3><p>Disponibilidad: <strong>${e(disponibilidad[u?.disponibilidad] || 'No disponible')}</strong></p>${u?.disponibilidad==='parcial'?'<p>El registro histórico sólo permite demostrar parte de los conteos. Esto no significa que falten registros administrativos.</p>':!u || u.disponibilidad==='no_disponible'?'<p>No hay información suficiente para demostrar los conteos; no significa que sean cero.</p>':''}<dl class="gis-resumen">${Object.entries(campos).map(([k,label])=>`<div><dt>${label}</dt><dd>${e(valorDisponible(u?.[k]))}</dd></div>`).join('')}</dl><p>Fecha de evaluación: ${e(u?.fecha_evaluacion?fecha(u.fecha_evaluacion):'No disponible')}${u?.id_ciclo!=null?` · Ciclo: ${e(u.id_ciclo)}`:''}</p>${u?.advertencias?.length?`<ul class="gis-advertencias-universo">${u.advertencias.map(a=>`<li>${e(a.mensaje || texto(a.codigo))}</li>`).join('')}</ul>`:''}</section>`;
    }
    function universosHtml(resumen) {
        if(!('universo_administrativo_actual' in resumen) && !('universo_administrativo_utilizado' in resumen)) return '';
        const a=resumen.universo_administrativo_actual,h=resumen.universo_administrativo_utilizado;
        const difieren=['nucleos_vinculados_activos','parcelas_elegibles_vinculadas','destinos_aplicables'].some(k=>a?.[k]!=null && h?.[k]!=null && a[k]!==h[k]);
        const avisoUniverso = [...(a?.advertencias || []), ...(h?.advertencias || [])].length ? '<span class="gis-etiqueta gis-advertencia">⚠ Advertencias en los registros administrativos</span>' : '';
        return avisoUniverso + ayuda(difieren ? "Los registros cambiaron: ver comparación" : "Ver registros administrativos y ciclos", `<div class="gis-universos">${universoHtml(a,'Universo administrativo actual')}${universoHtml(h,'Universo utilizado por la conciliación')}</div><p>El universo utilizado corresponde al último ciclo global. Cada elemento puede proceder de otro ciclo; consulta su detalle.</p>${difieren?'<p>Los conteos conocidos cambiaron desde ese ciclo. Los valores no disponibles no se comparan.</p>':''}`);
    }
    function diagnosticoElemento(f,tipo=registro?.tipo_objetivo) {
        if(historicoSinDiagnostico(f.diagnostico)) return 'Diagnóstico no disponible para este resultado histórico.';
        if(f.diagnostico) return f.diagnostico.mensaje || 'El servidor no incluyó un mensaje diagnóstico.';

        const datos=datosArchivo(f,tipo),parcela=['parcela','parcela_gpkg'].includes(tipo);
        const nombre=valorCampo(datos,'Núcleo'),numero=valorCampo(datos,'Número de parcela');
        const identidad=parcela ? `La parcela ${numero || identificadorArchivo(f)}` : `El núcleo ${nombre || identificadorArchivo(f)}`;
        const faltantes=datos.filter(d=>['Núcleo','Municipio','Entidad','Tipo de núcleo',...(parcela?['Número de parcela']:[])].includes(d.label) && !valorCampo(datos,d.label));
        const revisar=faltantes.length?` Datos a revisar: ${faltantes.map(d=>`${d.label.toLowerCase()} ${d.campos.length?'vacío':'no identificado en los campos recibidos'}`).join('; ')}.`:'';
        return `${identidad} ${parcela?'no coincide o no tiene un núcleo con el que se pueda vincular.':'no coincide con ningún núcleo registrado en el proyecto.'}${revisar} El servidor no informó el criterio exacto que impidió la asociación; compara los valores con los registros y vínculos del proyecto.`;
    }
    const resultadoTexto=f=>f.estado==='error'?'✖ Error de geometría o datos':f.estado_conciliacion==='sin_coincidencia'?'ℹ Sin coincidencia administrativa':estados[f.estado_conciliacion]||texto(f.estado);
    const resultadoHtml=f=>`<span class="gis-etiqueta ${f.estado==='error'?'gis-error':f.estado_conciliacion==='sin_coincidencia'?'gis-sin-coincidencia':'gis-informacion'}">${e(resultadoTexto(f))}</span>`;
    const motivoSinDestino=f=>f.diagnostico || (f.estado_conciliacion==='sin_coincidencia' && f.estado!=='error') ? diagnosticoElemento(f) : '';
    const estadosPendientes = new Set(["pendiente", "candidato", "coincidencia_exacta", "ambiguo"]);
    const errorPendiente = f => f.estado === "error" && f.estado_conciliacion !== "ignorado";
    const bloqueaCierre = f => estadosPendientes.has(f.estado_conciliacion) || errorPendiente(f);
    let elementosActuales = [], cierreVerificado = false, tokenResumen = 0;
    async function consultarElementos(iid, opciones) {
        const rows = [];
        for (let skip = 0;; skip += 500) {
            const p = await api.paginaElementos(iid, {skip, limit:500}, opciones);
            rows.push(...p.items);
            if (api.fin(p, skip, 500)) return rows;
        }
    }
    function actualizarCierre(r) {
        const boton = panel.querySelector('[data-gestion="finalizar"]');
        const ddv = r.tipo_objetivo === "derecho_via_proyecto";
        const pendientes = elementosActuales.filter(bloqueaCierre).length;
        const errores = elementosActuales.filter(errorPendiente).length;
        const bloqueado = ddv ? Number(r.errores) > 0 : pendientes > 0;
        if (boton) {
            boton.disabled = !editable(r) || !cierreVerificado || bloqueado || r.estado !== "previsualizado";
            boton.setAttribute("aria-describedby", "gisEstadoCierre");
        }
        const detalleCierre = r.activo === false ? "Importación dada de baja: consulta histórica de sólo lectura." : !cierreVerificado ? "No se pudo verificar si la carga está lista. Vuelve a consultar el estado antes de finalizar." : r.estado !== "previsualizado" ? "Esta importación ya no está pendiente de finalización. Consulta sus resultados y geometrías confirmadas." : ddv ? (bloqueado ? "El derecho de vía tiene errores que impiden confirmar esta versión." : "Revisa el derecho de vía antes de confirmar su versión.") : pendientes ? `Falta resolver ${pendientes} elementos; ${errores} tienen errores sin resolver. Abre Revisar elemento y confirma la asociación correcta, rechaza una propuesta incorrecta o ignora el elemento con un motivo. Seleccionar un candidato no basta para finalizar.` : "No quedan decisiones ni errores pendientes. Puedes finalizar la conciliación. Los elementos sin coincidencia no se incorporarán al mapa.";
        const estadoCierre = r.activo === false ? "Sólo lectura" : !cierreVerificado ? "No se pudo verificar el cierre" : r.estado !== "previsualizado" ? "No disponible para finalizar" : bloqueado ? (errores || (ddv && Number(r.errores)>0) ? "Hay errores por resolver" : "Hay elementos por resolver") : ddv ? "DDV listo para revisar" : "Listo para finalizar";
        panel.querySelector('[data-gis-cierre]').innerHTML = `<p id="gisEstadoCierre" role="status" class="gis-etiqueta ${!cierreVerificado || (bloqueado && (errores || ddv)) ? 'gis-error' : 'gis-informacion'}">${e(estadoCierre)}</p>${ayuda("Ver detalle del cierre", `<p>${e(detalleCierre)}</p>`)}${!ddv && pendientes ? g.boton("Ver elementos por resolver", "por-resolver") : ""}${!ddv && errores ? g.boton("Ver errores por resolver", "errores") : ""}${g.boton("Actualizar estado", "actualizar-estado")}`;
        panel.querySelector('[data-gis-masivo]').innerHTML = administrador && editable(r) && !ddv && r.estado === "previsualizado" ? `<strong>Confirmación conjunta · Sólo administrador</strong>${ayuda("Qué se confirma en conjunto", "<p>Confirma juntas las coincidencias con un único destino. Antes de guardar verás cuáles quedan fuera y los riesgos.</p>")}${g.boton("Confirmar todas las coincidencias", "confirmar-todas")}` : "";
        const masivo=panel.querySelector('[data-gestion="confirmar-todas"]');
        if(masivo) masivo.disabled=!cierreVerificado || !pendientes;
    }
    const tipoSospechoso = r => r.tipo_objetivo === "nucleo_agrario_gpkg" && /parcel/i.test(r.nombre_original || "");
    const observaciones = items => (items || []).map(v => typeof v === "string" ? texto(v) : v.mensaje || v.message || v.descripcion || texto(v.codigo || v.code || "Observación del archivo")).join(" · ");
    function paso(n) { document.querySelectorAll(".geoespacial-paso").forEach((p,i) => { p.classList.toggle("gis-paso-activo",i === n-1); if (i === n-1) p.setAttribute("aria-current","step"); else p.removeAttribute("aria-current"); }); }
    const destino = (d, parcela=false) => d ? [d.nombre_nucleo || "Núcleo sin nombre disponible", parcela ? `Parcela ${d.numero_parcela || "sin referencia"}` : "", d.municipio, d.entidad].filter(Boolean).join(" · ") : "Destino sin nombre disponible";
    const claveDestino = d => `${d.id_proyecto_nucleo}:${d.id_parcela || ""}`;
    const actor = nombre => nombre || "Nombre de usuario no disponible";
    const rango = (p,skip) => p.total == null ? `${p.items.length} registros · total no informado` : `${p.items.length ? skip+1 : 0}–${skip+p.items.length} de ${p.total}`;
    const historial = rows => g.tabla([{titulo:"Acción",valor:r=>texto(r.accion)},{titulo:"Fecha",valor:r=>fecha(r.creado_en)},{titulo:"Quién",valor:r=>actor(r.creado_por_nombre)},{titulo:"Motivo",valor:r=>r.motivo}],rows,null,"Aún no hay decisiones registradas.");
    async function proteger(ejecutar) {
        if (ocupado) return; ocupado = true;
        const controles = [...document.querySelectorAll('#selectorProyectoGeoespacial, #btnCrearImportacion, #btnPrepararImportacion, .js-ver-importacion, .js-baja-importacion, #filtrosHistorial input, #filtrosHistorial select, #limpiarFiltrosHistorial, #btnActualizarImportaciones')].map(el => [el, el.disabled]);
        controles.forEach(([el]) => el.disabled = true);
        try { return await ejecutar(); } catch(err) { ui.toast(mensaje(err),{tipo:"error"}); }
        finally { ocupado = false; controles.forEach(([el, disabled]) => el.disabled = disabled); }
    }
    async function formulario(datos) {
        return g.formulario({...datos,guardar:async d => { try { return await datos.guardar(d); } catch(err) { throw Error(mensaje(err)); } }});
    }
    async function cargarConfiguracion(actual) {
        try {
            const c = await api.configuracion(proyecto); if (actual !== revision) return;
            configuracion.innerHTML = `<h2>1. Sistema de coordenadas del proyecto</h2>${ayuda("Qué significa este sistema", "<p>Define cómo se miden las coordenadas. El archivo de ejemplo usa UTM zona 14N (EPSG:32614).</p>")}<p>Configuración actual: <strong>EPSG:${Number(c.srid_trabajo)}</strong></p>${puede ? g.boton("Cambiar sistema de coordenadas","crs") : "<p>Consulta de configuración.</p>"}`;
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
        mapa?.remove(); mapa=null;
        registro = r; pagina = 0; filtro = ""; ++tokenElemento;
        elementosActuales = []; cierreVerificado = false;
        panel.hidden = false; paso(3);
        panel.innerHTML = `<h2>3. ${r.tipo_objetivo === "derecho_via_proyecto" ? "Revisar derecho de vía" : "Conciliar elementos"}</h2><p>${e(r.nombre_original)} · ${e(texto(r.estado))}</p>${ayuda("Cómo se reconoce una carga", "<p>El mismo archivo con la misma configuración reutiliza su procesamiento. Una entrega con contenido distinto genera un nuevo registro.</p>")}<div data-gis-actividad></div><div data-gis-resumen></div><div class="gis-acciones-conjuntas" data-gis-masivo></div><label>Estado de conciliación<select data-gis-filtro>${opciones([["","Todos"],...Object.entries(estados)])}</select></label><p class="gis-leyenda-estados"><span class="gis-etiqueta gis-sin-coincidencia">ℹ Sin coincidencia administrativa</span> requiere revisar asociaciones. <span class="gis-etiqueta gis-error">✖ Error de geometría o datos</span> requiere revisar el archivo.</p><div data-gis-lista></div><div class="ssalfer-gestion-barra">${g.boton("Anterior","anterior")}${g.boton("Siguiente","siguiente")}<span data-gis-pagina role="status" aria-live="polite"></span></div><div data-gis-elemento></div><h2>${r.activo===false?"Consulta histórica":"4. Finalizar"}</h2>${ayuda("Antes de finalizar", `<p>${r.activo===false?"Esta carga conserva sus resultados y decisiones. No admite nuevas conciliaciones ni confirmaciones.":"La confirmación requiere revisión humana. La conciliación puede ser parcial; resuelve o ignora los candidatos, ambigüedades y errores pendientes."}</p>`)}${editable(r) ? g.boton(r.tipo_objetivo === "derecho_via_proyecto" ? "Confirmar versión de DDV" : "Finalizar conciliación","finalizar") : ""}${ayuda("Cuándo se muestra en el mapa", "<p>El mapa publicado muestra la versión vigente confirmada. Esta previsualización temporal no confirma ni publica el archivo.</p>")}<div data-gis-ciclos></div>`;
        detalle = panel.querySelector("[data-gis-elemento]");
        panel.querySelector("[data-gis-actividad]").innerHTML=actividadHtml(r);
        const botonFinalizar = panel.querySelector('[data-gestion="finalizar"]');
        if (botonFinalizar) botonFinalizar.disabled = true;
        panel.querySelector('[data-gis-ciclos]').insertAdjacentHTML("beforebegin", '<div data-gis-cierre></div><p data-gis-lote role="status" aria-live="polite"></p>');
        panel.querySelector('[data-gis-filtro]').insertAdjacentHTML("beforeend", opciones([["por_resolver","Por resolver antes de finalizar"],["errores","Errores por resolver"]]));
        panel.querySelector("[data-gis-filtro]").addEventListener("change", event => { filtro=event.target.value; pagina=0; cargarElementos(); });
        await refrescar(); if (registro === r) panel.scrollIntoView({behavior:"smooth",block:"start"});
    }
    async function refrescar() {
        const actual = revision, r = registro, token = ++tokenResumen; if (!r) return;
        cierreVerificado = false;
        const boton = panel.querySelector('[data-gestion="finalizar"]'); if (boton) boton.disabled = true;
        try {
            const [resumen, rows, vigente] = await Promise.all([api.resumen(r.id_importacion,lecturaImportacion(r)), consultarElementos(r.id_importacion,lecturaImportacion(r)), api.obtener(r.id_importacion,lecturaImportacion(r))]);
            if(actual !== revision || registro !== r || token !== tokenResumen) return;
            Object.assign(r, vigente);
            panel.querySelector('[data-gis-actividad]').innerHTML=actividadHtml(r);
            if(r.activo===false){detalle.replaceChildren();++tokenElemento;mapa?.remove();mapa=null;panel.querySelector('[data-gestion="finalizar"]')?.remove();}

            elementosActuales = rows; cierreVerificado = true;
            actualizarCierre(r);
            resumenActual=resumen;
            const labels = {registros_administrativos:"Registros del universo administrativo",features_archivo:"Elementos del archivo",confirmados:"Confirmados",ambiguos:"Varias coincidencias",candidatos:"Coincidencias que requieren revisión",registros_sin_geometria:"Registros sin geometría",features_sin_destino:"Sin coincidencia",ignoradas:"Ignorados",rechazadas:"Rechazados"};
            panel.querySelector("[data-gis-resumen]").innerHTML = `<dl class="gis-resumen">${Object.entries(labels).filter(([k])=>resumen[k]!=null).map(([k,l])=>`<div><dt>${e(l)}</dt><dd>${e(resumen[k])}</dd></div>`).join("")}</dl><div class="gis-indicadores">${Number(r.errores)>0?'<span class="gis-etiqueta gis-error">✖ Con errores</span>':''}${Number(r.advertencias)>0?'<span class="gis-etiqueta gis-advertencia">⚠ Con advertencias</span>':''}</div>${ayuda("Ver datos y validación del archivo", `<p>Formato: ${e(r.formato_detectado)}. Total: ${Number(r.total_features)} elementos. Capas: ${e((r.reporte?.capas||[]).join(", "))}. Coordenadas de origen: ${e(r.crs_original)}; trabajo: EPSG:${Number(r.srid_trabajo)}. Válidos: ${Number(r.validos)}; advertencias: ${Number(r.advertencias)}; errores: ${Number(r.errores)}.</p>`)}`;
            panel.querySelector('[data-gis-resumen]').insertAdjacentHTML('beforeend',universosHtml(resumen));
            if(tipoSospechoso(r)) panel.querySelector('[data-gis-resumen]').insertAdjacentHTML("beforeend",'<aside class="gis-diagnostico" role="alert"><strong>Revisa el tipo de esta carga</strong><p>El nombre indica parcelas, pero se registró como Núcleos agrarios. Si contiene parcelas, no confirmes aquí: consulta o prepara su carga con el tipo Parcelas. Tener geometrías válidas no garantiza una asociación administrativa correcta.</p></aside>');
            if(r.tipo_objetivo !== "derecho_via_proyecto" && Number(resumen.features_sin_destino)>0) {
                const sinTodos=rows.filter(f=>f.estado_conciliacion === "sin_coincidencia" && f.estado!=="error");
                const sinDestino=sinTodos.slice(0,5);
                const total=Number(r.total_features)>0?Number(r.total_features):rows.length;
                const porcentaje=total>0?sinTodos.length/total*100:0;
                const generalizado=porcentaje>85;
                const diagnostico=sinTodos.some(f=>f.diagnostico) ? "Consulta los diagnósticos registrados de cada elemento para conocer la causa. Los resultados históricos sin diagnóstico se identifican por separado." : generalizado ? "Es posible que los núcleos o parcelas de este archivo aún no estén registrados o vinculados al proyecto, o que el formato de un campo clave (nombre, número de parcela) no coincida con lo registrado en SSALFER. Revisa una muestra y las relaciones del proyecto antes de corregir elementos uno por uno." : "Revisa los nombres y los datos de los elementos que quedaron sin destino administrativo.";
                const esParcela = ["parcela", "parcela_gpkg"].includes(r.tipo_objetivo);
                panel.querySelector("[data-gis-resumen]").insertAdjacentHTML("beforeend",`<aside class="gis-diagnostico gis-sin-coincidencia"><strong>ℹ ${generalizado ? "Sin coincidencia en casi todo el archivo" : "Hay elementos sin coincidencia"}</strong><p>${generalizado ? "Revisa los registros del proyecto y el formato de los datos del archivo." : "Revisa las asociaciones pendientes."} No es un error de carga.</p>${ayuda("Qué revisar y ejemplos del archivo", `<p>${sinTodos.length} de ${total} elementos del archivo (${porcentaje.toFixed(1)} %). ${generalizado ? "Diagnóstico: falta de coincidencias generalizada." : "Diagnóstico: revisar los casos sin destino."}</p><p>${diagnostico}</p><p>Esto no es un fallo de carga ni un error de geometría. Los errores de geometría o datos se muestran por separado.</p><p>${esParcela ? "Revisa que el nombre del núcleo y el número de parcela del archivo coincidan con las parcelas registradas en este proyecto." : "Revisa que los nombres de las geometrías coincidan con los núcleos registrados en este proyecto."}</p><p>${esParcela ? "Revisa que las parcelas estén registradas y relacionadas con los núcleos del proyecto. Comprueba también los números de parcela." : "Revisa que los núcleos estén vinculados al proyecto y compara su nombre, municipio, entidad y tipo de núcleo con el archivo."} Destinos administrativos disponibles: ${e(valorDisponible(resumen.registros_administrativos))}. ${r.activo===false?"Esta carga es histórica y no admite nuevas decisiones.":"Después de resolver las diferencias, pulsa Nueva conciliación."}</p><p>Ejemplos (hasta cinco): ${e(sinDestino.map(f=>`${etiquetaElemento(f)} — ${camposArchivo(f)}`).join("; "))}</p>`)}<a class="btn-secundario gis-enlace-boton" href="/pages/fichaProyecto.html?id=${proyecto}">Revisar registros del proyecto</a> ${g.boton("Ver elementos sin coincidencia","detalle-sin-coincidencia")} ${g.boton("Filtrar tabla sin coincidencia","sin-coincidencia")} ${editable(r)?g.boton("Nueva conciliación","reconciliar"):""}</aside>`);
            }
            if (r.tipo_objetivo !== "derecho_via_proyecto" && rows.some(f=>["candidato","coincidencia_exacta","confirmado"].includes(f.estado_conciliacion) && f.estado!=="error")) {
                panel.querySelector("[data-gis-resumen]").insertAdjacentHTML("beforeend", `${ayuda("Acerca de la vista en el mapa", "<p>Las coincidencias pueden revisarse juntas en el mapa. Las que aún no confirmaste se muestran como previsualización.</p>")}<a class="btn-secundario gis-enlace-boton" href="/pages/mapa.html?id_proyecto=${proyecto}&id_importacion=${r.id_importacion}&vista=coincidencias${r.activo===false?"&incluir_inactivas=true":""}">Ver coincidencias en el mapa</a>`);
            }
            await cargarElementos(); if(actual !== revision || registro !== r) return;
            if (r.tipo_objetivo !== "derecho_via_proyecto") await cargarCiclos();
        } catch(err) { if (actual === revision && registro === r && token === tokenResumen) { cierreVerificado = false; actualizarCierre(r); fallo(panel.querySelector("[data-gis-resumen]"),err); } }
    }
    async function cargarElementos(irAlInicio=false) {
        const actual=++tokenLista, contexto=revision,r=registro; if(!r)return;
        const salida=panel.querySelector("[data-gis-lista]"); salida.textContent="Consultando elementos…"; salida.setAttribute("aria-busy","true");
        try {
            const filtroLocal = filtro === "por_resolver" ? bloqueaCierre : filtro === "errores" ? errorPendiente : null;
            const filtrados = filtroLocal ? elementosActuales.filter(filtroLocal) : null;
            const resultado=filtrados ? {items:filtrados.slice(pagina*25,pagina*25+25),total:filtrados.length} : await api.paginaElementos(r.id_importacion,{skip:pagina*25,limit:25,estado_conciliacion:filtro},lecturaImportacion(r)),rows=resultado.items;
            if(actual!==tokenLista || contexto!==revision || registro!==r)return; lista=rows;
            salida.innerHTML=g.tabla([{titulo:"Elemento del archivo",valor:etiquetaElemento},{titulo:"Valores originales del archivo",valor:camposArchivo},{titulo:"Resultado",valor:resultadoTexto,html:resultadoHtml},{titulo:"Ciclo del resultado",valor:f=>valorDisponible(f.id_ciclo_conciliacion)},{titulo:"Observaciones",valor:f=>[motivoSinDestino(f),observaciones([...(f.advertencias||[]),...(f.errores||[]),...(f.transformaciones||[])])].filter(Boolean).join(" · "),html:f=>`${f.errores?.length?`<p class="gis-error">${e(observaciones(f.errores))}</p>`:''}${f.advertencias?.length?'<span class="gis-etiqueta gis-advertencia">⚠ Con advertencias</span>':''}${motivoSinDestino(f) || f.advertencias?.length || f.transformaciones?.length ? ayuda("Ver observaciones", `<p>${e([motivoSinDestino(f),observaciones([...(f.advertencias||[]),...(f.transformaciones||[])])].filter(Boolean).join(" · "))}</p>`) : 'Sin observaciones'}`}],rows,f=>g.boton("Revisar elemento","elemento",f.id_importacion_feature),"No hay elementos con este estado.");
            panel.querySelector('[data-gestion="anterior"]').disabled=pagina===0; panel.querySelector('[data-gestion="siguiente"]').disabled=api.fin(resultado,pagina*25,25);
            panel.querySelector("[data-gis-pagina]").textContent=`Página ${pagina+1} · ${rango(resultado,pagina*25)} elementos`;
            if(irAlInicio){salida.tabIndex=-1;salida.focus({preventScroll:true});salida.scrollIntoView({block:'start',behavior:'smooth'});}
        } catch(err){if(actual===tokenLista&&contexto===revision)fallo(salida,err);} finally {if(actual===tokenLista)salida.setAttribute("aria-busy","false");}
    }
    async function abrirSinCoincidencia() {
        const r=registro;
        if(!r || !cierreVerificado)return;
        const tipo=r.tipo_objetivo,parcela=['parcela','parcela_gpkg'].includes(tipo);
        const grupo=parcela?'Parcelas':'Núcleos';
        const buscar=v=>String(v).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
        const filas=elementosActuales.filter(f=>f.estado_conciliacion==='sin_coincidencia' && f.estado!=='error').map(f=>{
            const datos=datosArchivo(f,tipo),identificador=identificadorArchivo(f),valores=camposArchivo(f,tipo),motivo=diagnosticoElemento(f,tipo);
            return {identificador,valores,motivo,datos,feature:f,diagnostico:diagnosticoTexto(f,tipo),busqueda:buscar(`${identificador} ${valores} ${diagnosticoTexto(f,tipo)}`)};
        });
        const etiquetaGrupo=filas.length===1?(parcela?'parcela':'núcleo'):grupo.toLowerCase();
        await ui.abrirModal({titulo:'Elementos sin coincidencia',contenido:`<section class="gis-listado-sin-coincidencia"><p><strong>${e(r.nombre_original)}</strong> · Proyecto ${proyecto}</p><p class="gis-etiqueta gis-sin-coincidencia">ℹ Sin coincidencia · No es un error de carga</p>${ayuda("Cómo resolver las coincidencias", `<p class="gis-etiqueta gis-sin-coincidencia">ℹ Falta una asociación administrativa; no es un error de carga.</p><p>Estos elementos no se incorporarán al mapa ni se asociarán a los registros del proyecto hasta resolver la coincidencia o registrar y vincular sus destinos, revisar una nueva conciliación y confirmar las asociaciones.</p>`)}<h3>${filas.length} ${etiquetaGrupo} sin coincidencia</h3>${ayuda("Qué puedes buscar", "<p>Buscar por nombre, parcela, municipio, entidad, folio, motivo, código o evidencia.</p>")}<label>Buscar en el listado<input type="search" data-gis-buscar placeholder="Escribe un dato del archivo" autocomplete="off"></label><div class="ssalfer-gestion-barra"><button type="button" class="btn-secundario" data-gis-exportar>Exportar listado filtrado (CSV)</button><button type="button" class="btn-secundario" data-gis-limpiar>Limpiar búsqueda</button></div><p data-gis-conteo role="status" aria-live="polite"></p><div data-gis-resultados tabindex="0" role="region" aria-label="Listado de elementos sin coincidencia"></div><div class="ssalfer-gestion-barra"><button type="button" class="btn-secundario" data-gis-prev>Anterior</button><button type="button" class="btn-secundario" data-gis-next>Siguiente</button></div><p data-gis-exportado role="status" aria-live="polite"></p></section>`,acciones:[{texto:'Cerrar listado',valor:true}],preparar:fondo=>{
            fondo.querySelector('.ssalfer-modal').classList.add('gis-modal-listado');
            const input=fondo.querySelector('[data-gis-buscar]'),prev=fondo.querySelector('[data-gis-prev]'),next=fondo.querySelector('[data-gis-next]'),exportar=fondo.querySelector('[data-gis-exportar]');
            let paginaModal=0,filtradas=filas;
            const render=()=>{
                const inicio=paginaModal*25,visibles=filtradas.slice(inicio,inicio+25);
                fondo.querySelector('[data-gis-resultados]').innerHTML=g.tabla([{titulo:'Identificador en el archivo',valor:f=>f.identificador},{titulo:'Valores originales',valor:f=>f.valores},{titulo:'Qué revisar',valor:f=>f.motivo,html:f=>diagnosticoHtml(f.feature)}],visibles,null,'No hay elementos que coincidan con esta búsqueda.');
                fondo.querySelector('[data-gis-conteo]').textContent=`${visibles.length?inicio+1:0}–${inicio+visibles.length} de ${filtradas.length} resultados.`;
                prev.disabled=paginaModal===0;next.disabled=inicio+25>=filtradas.length;exportar.disabled=!filtradas.length;
            };
            input.addEventListener('input',()=>{const q=buscar(input.value.trim());filtradas=filas.filter(f=>f.busqueda.includes(q));paginaModal=0;render();});
            fondo.querySelector('[data-gis-limpiar]').onclick=()=>{input.value='';filtradas=filas;paginaModal=0;render();input.focus();};
            for(const [control,salto] of [[prev,-1],[next,1]])control.onclick=()=>{paginaModal+=salto;render();if(control.disabled)fondo.querySelector('[data-gis-resultados]').focus();};
            exportar.onclick=()=>{
                // CSV textual: escapar comillas y neutralizar fórmulas de hojas de cálculo.
                const celda=v=>{let t=String(v??'');if(/^[\s]*[=+@-]/.test(t))t="'"+t;return '"'+t.replaceAll('"','""')+'"';};
                const encabezado=['Proyecto','Importación','Archivo','Tipo','Identificador','Núcleo','Municipio','Entidad','Tipo de núcleo','Número de parcela','Valores y columnas originales','Qué revisar','Ciclo del resultado','Origen del diagnóstico','Códigos','Campos evaluados','Evidencia'];
                const csv=[encabezado,...filtradas.map(f=>[r.id_proyecto,r.id_importacion,r.nombre_original,grupo,f.identificador,...['Núcleo','Municipio','Entidad','Tipo de núcleo','Número de parcela'].map(k=>valorCampo(f.datos,k)),f.valores,f.motivo,valorDisponible(f.feature.id_ciclo_conciliacion),f.feature.diagnostico?.origen || 'No disponible',(f.feature.diagnostico?.codigos||[]).join(' · '),(f.feature.diagnostico?.campos_evaluados||[]).join(' · '),evidenciaDiagnostico(f.feature.diagnostico)])].map(row=>row.map(celda).join(',')).join('\r\n');
                const url=URL.createObjectURL(new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');
                a.href=url;a.download=`sin-coincidencia-importacion-${r.id_importacion}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
                fondo.querySelector('[data-gis-exportado]').textContent=`Se preparó la descarga de ${filtradas.length} elementos, incluyendo todas las páginas del filtro actual.`;
            };
            render();
        }});
    }
    async function candidatosVigentes(iid, fid, candidatos, consultas = new Map(), feature = elementosActuales.find(f=>f.id_importacion_feature===fid), lectura = lecturaImportacion()) {
        const consultar = (clave, fn) => {if(!consultas.has(clave)) consultas.set(clave, fn()); return consultas.get(clave);};
        // El ciclo de la feature es autoritativo, aunque no sea el último de la carga.
        if(feature?.id_ciclo_conciliacion != null) {
            const id=feature.id_ciclo_conciliacion;
            const detalle=await consultar(`ciclo:${id}`,()=>api.ciclo(iid,id,lectura));
            return {candidatos:candidatos.filter(c=>c.id_ciclo===id),universo:new Map((detalle.universo_destinos || []).map(d=>[claveDestino(d),d])),ciclo:detalle};
        }
        const ciclos=[];
        for(let skip=0;;skip+=200){const p=await consultar(`pagina:${skip}`,()=>api.paginaCiclos(iid,{skip,limit:200},lectura));ciclos.push(...p.items);if(api.fin(p,skip,200))break;}
        for(const ciclo of ciclos.sort((a,b)=>b.numero_ciclo-a.numero_ciclo)) {
            const detalle=await consultar(`ciclo:${ciclo.id_ciclo}`,()=>api.ciclo(iid,ciclo.id_ciclo,lectura));
            if(detalle.features.some(f=>f.id_importacion_feature===fid)) return {candidatos:candidatos.filter(c=>c.id_ciclo===ciclo.id_ciclo),universo:new Map((detalle.universo_destinos || []).map(d=>[claveDestino(d),d])),ciclo:detalle};
        }
        return {candidatos:ciclos.length?[]:candidatos,universo:new Map()};
    }
    async function confirmarTodas() {
        if (!administrador || !editable(registro)) return;
        const r=registro, ctx=revision, salida=panel.querySelector('[data-gis-lote]');
        await refrescar();
        if (!editable(r) || !cierreVerificado || registro!==r || ctx!==revision || r.estado!=="previsualizado") return;
        salida.textContent="Comprobando las coincidencias de toda la carga…";
        const propuestas=[], consultas=new Map();
        try {
            for (const f of elementosActuales.filter(f=>["candidato","coincidencia_exacta"].includes(f.estado_conciliacion) && f.estado!=="error")) {
                const todos=await api.candidatos(r.id_importacion,f.id_importacion_feature);
                const {candidatos}=await candidatosVigentes(r.id_importacion,f.id_importacion_feature,todos,consultas);
                const disponibles=candidatos.filter(c=>c.estado!=="rechazado");
                if(disponibles.length===1) propuestas.push({f,c:disponibles[0]});
            }
            const destinos=new Map();
            propuestas.forEach(({c})=>destinos.set(claveDestino(c),(destinos.get(claveDestino(c))||0)+1));
            const lote=propuestas.filter(({c})=>destinos.get(claveDestino(c))===1);
            if(!lote.length){salida.textContent="No hay coincidencias únicas para confirmar juntas. Revisa los elementos sin destino, con varias propuestas o que comparten destino.";return;}
            const advertencias=lote.filter(({f,c})=>f.advertencias?.length || c.geometria_previa_hash).length;
            const incluidos=new Set(lote.map(({f})=>f.id_importacion_feature));
            const sinCoincidencia=elementosActuales.filter(f=>f.estado_conciliacion==="sin_coincidencia" && f.estado!=="error");
            const fuera=elementosActuales.filter(f=>!incluidos.has(f.id_importacion_feature) && (f.estado_conciliacion!=="sin_coincidencia" || f.estado==="error"));
            const listado=rows=>rows.length ? `<ul class="gis-lista-excepciones">${rows.map(f=>`<li>${e(etiquetaElemento(f))} · ${resultadoHtml(f)}<p>${e(camposArchivo(f))}</p></li>`).join("")}</ul>` : "<p>Ninguno.</p>";
            const aceptar=await ui.abrirModal({titulo:"Confirmar todas las coincidencias",contenido:`<p>Vas a confirmar <strong>${lote.length} asociaciones</strong> de ${e(r.nombre_original)}, en el proyecto seleccionado (${proyecto}), de una sola vez.</p>${tipoSospechoso(r)?"<p role=\"alert\"><strong>Revisa el tipo: el nombre del archivo indica parcelas, pero esta carga está registrada como Núcleos agrarios. No continúes si el tipo es incorrecto: podrías reemplazar polígonos de núcleos con polígonos de parcelas.</strong></p>":""}<p class="gis-etiqueta gis-advertencia">⚠ Puede reemplazar geometrías o asociarlas a un registro incorrecto. No hay deshacer conjunto.</p><p>No cierres la pantalla. Los elementos excluidos no se modifican; finalizar sigue siendo un paso separado.</p>${ayuda("Ver todos los riesgos y advertencias", `<h3>Qué implica aceptar</h3><ul><li>${advertencias} asociaciones pueden incluir advertencias o reemplazar geometrías anteriores. Al confirmar autorizas esas reparaciones y reemplazos.</li><li>Una asociación incorrecta puede colocar un polígono en el registro equivocado y alterar la información visible en el mapa. Este botón no comprueba por ti que cada destino sea correcto.</li><li>Las decisiones se guardan una por una. Si ocurre un problema se detiene el proceso, pero lo guardado se conserva; no hay deshacer conjunto.</li><li>No cierres la pantalla. Si se pierde la conexión, actualiza el estado antes de reintentar: el último envío podría haberse guardado.</li><li>No se crean registros administrativos ni se resuelven automáticamente los elementos excluidos. Finalizar la conciliación sigue siendo un paso separado.</li></ul>`)}<h3>Polígonos sin coincidencia: ${sinCoincidencia.length}</h3><p>No se confirmarán ni se incorporarán al mapa por esta acción.</p>${listado(sinCoincidencia)}<details><summary>Otros elementos fuera de esta acción: ${fuera.length}</summary><p>Incluye confirmados anteriormente, ignorados, errores, varias propuestas y destinos compartidos.</p>${listado(fuera)}</details>`,acciones:[{texto:"Cancelar",valor:false},{texto:"Confirmar",valor:true,principal:true}]});
            if(!aceptar){salida.textContent="Operación cancelada. No se confirmó ningún elemento.";return;}
            let confirmados=0, error=null;
            for(const {f,c} of lote) {
                if(!editable(r) || registro!==r || ctx!==revision) break;
                salida.textContent=`Confirmando ${confirmados+1} de ${lote.length}… No cierres esta pantalla.`;
                try {
                    await api.decidir(r.id_importacion,f.id_importacion_feature,{accion:"confirmar",id_candidato:c.id_candidato,confirmacion_explicita:true,aceptar_advertencias:true,motivo:"Confirmación conjunta autorizada por el administrador"});
                    confirmados++;
                } catch(err) {error=err;break;}
            }
            await refrescar();
            salida.textContent=`Se confirmaron ${confirmados} de ${lote.length} asociaciones. ${error ? `La operación se detuvo: ${mensaje(error)} Lo ya confirmado se conserva. Actualiza el estado antes de volver a intentar; si hubo una pérdida de conexión, el último envío podría haberse guardado.` : "Revisa los elementos restantes y después finaliza la conciliación."}`;
        } catch(err) {salida.textContent=`No se inició la confirmación conjunta: ${mensaje(err)}`;}
    }
    async function abrirElemento(fid) {
        const f=lista.find(x=>x.id_importacion_feature===fid); if(!f)return;
        const actual=++tokenElemento,contexto=revision,r=registro;
        detalle.innerHTML="<p>Consultando geometría y propuestas…</p>"; ui.desplazarA(detalle);
        mapa?.remove();mapa=null;
        try {
            const esDDV=r.tipo_objetivo==="derecho_via_proyecto";
            const [geo,candidatosTodos,decisiones]=await Promise.all([api.geometria(r.id_importacion,fid,lecturaImportacion(r)),esDDV?[]:api.candidatos(r.id_importacion,fid,lecturaImportacion(r)),esDDV?[]:api.decisiones(r.id_importacion,fid,lecturaImportacion(r))]);
            const {candidatos,universo,ciclo}=esDDV?{candidatos:[],universo:new Map()}:await candidatosVigentes(r.id_importacion,fid,candidatosTodos,new Map(),f,lecturaImportacion(r));
            const nombres=candidatos.map(c=>destino(universo.get(claveDestino(c)),Boolean(c.id_parcela)));
            if(actual!==tokenElemento||contexto!==revision||registro!==r)return;
            detalle.innerHTML=`<section class="ssalfer-gestion-seccion"><h3>${e(etiquetaElemento(f))}</h3><p><strong>${r.activo===false?"Geometría histórica · Sólo lectura":"Previsualización del archivo"}</strong></p>${f.diagnostico || f.estado_conciliacion==="sin_coincidencia" ? diagnosticoHtml(f) : ""}${ciclo ? universoHtml(ciclo.universo_administrativo,"Universo utilizado por el ciclo de este elemento") : ""}<div class="gis-minimapa" data-gis-mapa></div><dl>${atributos(f).map(([k,v])=>`<dt>${e(texto(k))}</dt><dd>${e(v)}</dd>`).join("")}</dl><p>${e(observaciones([...f.advertencias,...f.errores,...f.transformaciones]))}</p><a href="/pages/mapa.html?id_proyecto=${proyecto}&id_importacion=${r.id_importacion}&id_feature=${fid}${r.activo===false?"&incluir_inactivas=true":""}">Abrir previsualización en el mapa</a>${esDDV?"":`<h3>Destinos propuestos</h3><p>Seleccionar registra la elección, pero no guarda geometría. Confirmar sí la incorpora al proyecto.</p>${g.tabla([{titulo:"Destino",valor:(_,i)=>i},{titulo:"Revisó",valor:c=>actor(c.usuario_revision_nombre)},{titulo:"Criterio",valor:c=>texto(c.criterio)},{titulo:"Resultado",valor:c=>texto(c.clasificacion)},{titulo:"Coincidencias",valor:c=>c.coincidencias.map(texto).join(" · ")}].map((col,i)=>i===0?{...col,valor:c=>nombres[candidatos.indexOf(c)]}:col),candidatos,c=>editable(r)&&r.estado==="previsualizado"&&!["confirmado","ignorado"].includes(f.estado_conciliacion)&&c.estado!=="rechazado"?g.boton("Seleccionar","seleccionar",c.id_candidato)+g.boton("Confirmar","confirmar",c.id_candidato)+g.boton("Rechazar","rechazar",c.id_candidato):"",r.activo===false?"No hay destinos propuestos registrados para este elemento histórico.":"No hay destinos propuestos. Puedes ignorar el elemento o realizar una nueva conciliación cuando exista su registro administrativo.")}${editable(r)&&r.estado==="previsualizado"&&!["confirmado","ignorado"].includes(f.estado_conciliacion)?g.boton("Ignorar elemento","ignorar"):""}<h3>Historial de decisiones</h3>${f.estado_conciliacion==="ignorado"?"<p>Este elemento fue excluido mediante una decisión guardada. Consulta aquí su motivo, fecha y responsable; no es un error de coordenadas.</p>":""}${historial(decisiones)}`}</section>`;
            if(window.L && geo.geometry){mapa=L.map(detalle.querySelector("[data-gis-mapa]"));L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(mapa);const capa=L.geoJSON(geo,{style:{color:'#bd7618',dashArray:'6 4'}}).addTo(mapa);if(capa.getBounds().isValid())mapa.fitBounds(capa.getBounds());else{mapa.remove();mapa=null;detalle.querySelector("[data-gis-mapa]").textContent="La geometría está vacía; revisa las observaciones del elemento.";}}
            else detalle.querySelector("[data-gis-mapa]").textContent="No hay geometría disponible para previsualizar.";
            if(esDDV){const info=document.createElement("p");info.textContent=`Componentes poligonales de la previsualización: ${geo.geometry?.type === "MultiPolygon" ? geo.geometry.coordinates.length : geo.geometry?.type === "Polygon" ? 1 : "Sin dato"}. La superficie oficial y el historial de versiones vigentes no están disponibles en esta consulta.`;detalle.appendChild(info);}
            detalle.querySelectorAll("[data-gestion]").forEach(b=>b.addEventListener("click",()=>proteger(async()=>{
                if(!editable(r))return;
                const accion=b.dataset.gestion, candidato=candidatos.find(c=>c.id_candidato===Number(b.dataset.registro));
                const warnings=f.advertencias.length>0 || false;
                let formularioActual;
                const resultado=await formulario({preparar:form=>{formularioActual=form;const aceptar=form.elements.aceptar_advertencias;if(aceptar){aceptar.closest("label").hidden=!warnings;aceptar.required=warnings;}},titulo:`${texto(accion)} elemento`,introduccion:accion==="confirmar"?"La geometría y esta decisión quedarán guardadas en el proyecto.":"Esta acción no incorpora geometría al proyecto.",campos:[...(accion==="confirmar"?[{nombre:"confirmacion_explicita",etiqueta:"Confirmo que revisé el destino y la geometría",tipo:"checkbox",requerido:true},{nombre:"aceptar_advertencias",etiqueta:"Acepto las advertencias de reparación o reemplazo informadas",tipo:"checkbox",requerido:warnings}]:[]),{nombre:"motivo",etiqueta:"Motivo",tipo:"textarea",maximo:250,requerido:["rechazar","ignorar"].includes(accion)}],guardar:async d=>{if(!editable(r)||contexto!==revision||registro!==r)throw Error("El proyecto cambió. Abre nuevamente el elemento.");try { return await api.decidir(r.id_importacion,fid,{...d,accion,...(accion!=="ignorar"?{id_candidato:candidato.id_candidato}:{})}); } catch(err) { if(accion==="confirmar" && /advertencias/i.test(err.message)){const aceptar=formularioActual.elements.aceptar_advertencias;aceptar.closest("label").hidden=false;aceptar.required=true;} throw err; }}});
                if(resultado&&contexto===revision&&registro===r){detalle.replaceChildren();await refrescar();await abrirElemento(fid);}
            })));
        }catch(err){if(actual===tokenElemento&&contexto===revision)fallo(detalle,{status:err.status,message:err.status===404 ? "La previsualización o sus propuestas ya no están disponibles. Vuelve a consultar la conciliación." : err.status===0 || !err.status ? "No se pudo consultar la previsualización. Comprueba la conexión y vuelve a intentarlo." : err.message});}
    }
    let tokenCiclos=0, tokenRevisiones=0;
    async function cargarCiclos(skip=0) {
        const r=registro,ctx=revision,salida=panel.querySelector("[data-gis-ciclos]"),token=++tokenCiclos;
        try{const p=await api.paginaCiclos(r.id_importacion,{skip,limit:25},lecturaImportacion(r));if(ctx!==revision||registro!==r||token!==tokenCiclos)return;
            salida.innerHTML=`<h3>Historial de conciliaciones</h3>${editable(r)?g.boton("Nueva conciliación","reconciliar"):""}${g.tabla([{titulo:"Ciclo",valor:r=>r.numero_ciclo},{titulo:"Fecha",valor:r=>fecha(r.fecha_inicio)},{titulo:"Quién",valor:r=>actor(r.usuario_nombre)},{titulo:"Motivo",valor:r=>r.motivo}],p.items,r=>g.boton("Ver ciclo","ciclo",r.id_ciclo))}<div>${g.boton("Anterior","ciclos-anterior")}${g.boton("Siguiente","ciclos-siguiente")}<span>${e(rango(p,skip))} conciliaciones</span></div>`;
            for(const [accion,salto,inhabilitado] of [["anterior",-25,skip===0],["siguiente",25,api.fin(p,skip,25)]]){const b=salida.querySelector(`[data-gestion="ciclos-${accion}"]`);b.disabled=inhabilitado;b.onclick=event=>{event.stopPropagation();cargarCiclos(skip+salto);};}
        }catch(err){if(ctx===revision&&registro===r&&token===tokenCiclos)fallo(salida,err);}
    }
    async function cargarRevisiones(ctx,estado="pendiente",skip=0,objetivo="",tipo_cambio="",irAlInicio=false) {
        const token=++tokenRevisiones;
        if(!revisiones.querySelector('[data-revision-estado]')) {
            revisiones.innerHTML=`<h2>Revisiones geoespaciales</h2><p>Consulta los cambios entre entregas y registra su revisión. Esta sección no activa archivos ni reemplaza el mapa.</p><div class="gis-filtros-revisiones"><label>Estado<select data-revision-estado>${opciones([["","Todos"],["pendiente","Pendiente"],["revisado","Revisado"],["no_aplica","No aplica"],["aplicado","Aplicado"]])}</select></label><label>Capa<select data-revision-objetivo>${opciones([["","Todas"],["ddv","Derecho de vía"],["nucleo","Núcleo"],["parcela","Parcela"]])}</select></label><label>Tipo de cambio<select data-revision-cambio>${opciones([["","Todos"],["aparece_en_nueva_version","Aparece en nueva versión"],["desaparece_en_nueva_version","Desaparece en nueva versión"],["geometria_modificada","Geometría modificada"],["cambio_relacion_ddv","Cambio de relación con DDV"]])}</select></label><button type="button" class="btn-secundario" data-revision-restablecer>Ver todos los pendientes</button></div><p data-revision-estado-consulta role="status" aria-live="polite"></p><div data-revision-resultados></div><div data-revision-detalle></div>`;
            const aplicar=()=>cargarRevisiones(revision,revisiones.querySelector('[data-revision-estado]').value,0,revisiones.querySelector('[data-revision-objetivo]').value,revisiones.querySelector('[data-revision-cambio]').value);
            revisiones.querySelectorAll('select').forEach(control=>control.addEventListener('change',aplicar));
            revisiones.querySelector('[data-revision-restablecer]').onclick=()=>cargarRevisiones(revision);
        }
        const select=revisiones.querySelector('[data-revision-estado]'),capa=revisiones.querySelector('[data-revision-objetivo]'),cambio=revisiones.querySelector('[data-revision-cambio]');
        select.value=estado;capa.value=objetivo;cambio.value=tipo_cambio;
        const salida=revisiones.querySelector('[data-revision-resultados]'),aviso=revisiones.querySelector('[data-revision-estado-consulta]');
        ++tokenRevision;revisiones.querySelector('[data-revision-detalle]').replaceChildren();
        salida.setAttribute('aria-busy','true');salida.textContent='Consultando cambios…';aviso.textContent='Aplicando filtros…';
        try {
            const p=await api.paginaRevisiones(proyecto,{estado,skip,limit:25,objetivo,tipo_cambio});if(ctx!==revision||token!==tokenRevisiones)return;
            const filtros=[select,capa,cambio].map(c=>c.selectedOptions[0].textContent).join(' · ');
            aviso.textContent=`${p.total==null?p.items.length:p.total} revisiones · ${filtros}`;
            salida.innerHTML=g.tabla([{titulo:"Capa",valor:r=>texto(r.objetivo)},{titulo:"Destino",valor:r=>r.objetivo==="ddv"?"Derecho de vía del proyecto":destino(r.destino,r.objetivo==="parcela")},{titulo:"Cambio",valor:r=>texto(r.tipo_cambio)},{titulo:"Estado",valor:r=>texto(r.estado_revision)},{titulo:"Fecha",valor:r=>fecha(r.creado_en)},{titulo:"Quién",valor:r=>actor(r.creado_por_nombre)}],p.items,r=>g.boton("Consultar revisión","revision",r.id_revision),"No hay cambios con esta combinación. Prueba otra capa o pulsa Ver todos los pendientes.")+`<div class="ssalfer-gestion-barra">${g.boton("Anterior","rev-anterior")}${g.boton("Siguiente","rev-siguiente")}<span>${e(rango(p,skip))} revisiones</span></div>`;
            for(const [accion,salto,bloqueado] of [["anterior",-25,skip===0],["siguiente",25,api.fin(p,skip,25)]]) {
                const b=salida.querySelector(`[data-gestion="rev-${accion}"]`);b.disabled=bloqueado;
                b.onclick=()=>cargarRevisiones(revision,estado,skip+salto,objetivo,tipo_cambio,true);
            }
            salida.querySelectorAll('[data-gestion="revision"]').forEach(b=>b.onclick=()=>abrirRevision(Number(b.dataset.registro),ctx));
            if(irAlInicio){salida.tabIndex=-1;salida.focus({preventScroll:true});salida.scrollIntoView({block:'start',behavior:'smooth'});}
        }catch(err){if(ctx===revision&&token===tokenRevisiones){aviso.textContent='No se pudieron consultar los cambios. Vuelve a aplicar los filtros.';fallo(salida,err);}}
        finally{if(ctx===revision&&token===tokenRevisiones)salida.setAttribute('aria-busy','false');}
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
    function iniciar() {
        document.querySelectorAll(".geoespacial-paso").forEach((p,i)=>{p.querySelector("strong").textContent=["Sistema de coordenadas","Cargar","Conciliar","Finalizar"][i];p.classList.remove("activo");});paso(1);
        document.getElementById("btnCrearImportacion").addEventListener("click",()=>paso(2));
        configuracion=document.createElement("section");configuracion.className="ssalfer-gestion-seccion";configuracion.hidden=true;
        document.querySelector(".geoespacial-layout").before(configuracion);
        panel=document.createElement("section");panel.className="ssalfer-gestion-seccion gis-conciliacion";panel.hidden=true;panel.id="conciliacionGeoespacial";
        revisiones=document.createElement("section");revisiones.className="ssalfer-gestion-seccion";revisiones.hidden=true;
        document.querySelector("main").append(panel,revisiones);detalle=document.createElement("div");
        puede=true;administrador=sesion.user.rol==="admin";
        panel.addEventListener("click",event=>{const b=event.target.closest("[data-gestion]");if(!b||detalle.contains(b)||ocupado)return;const accion=b.dataset.gestion;
            if(accion==="anterior"||accion==="siguiente"){pagina+=accion==="anterior"?-1:1;cargarElementos(true);return;}
            if(accion==="elemento"){abrirElemento(Number(b.dataset.registro));return;}
            if (["por-resolver", "errores", "sin-coincidencia"].includes(accion)) {
                filtro = {"por-resolver":"por_resolver",errores:"errores","sin-coincidencia":"sin_coincidencia"}[accion]; pagina = 0;
                panel.querySelector('[data-gis-filtro]').value = filtro;
                cargarElementos(); ui.desplazarA(panel.querySelector('[data-gis-lista]')); return;
            }
            proteger(async()=>{const r=registro,ctx=revision;if(!r)return;
                if(accion==="confirmar-todas"){if(administrador)await confirmarTodas();return;}
                if(accion==="detalle-sin-coincidencia"){await abrirSinCoincidencia();return;}
                if(accion==="actualizar-estado"){await refrescar();return;}
                if(accion==="ciclo"){const c=await api.ciclo(r.id_importacion,Number(b.dataset.registro),lecturaImportacion(r));if(ctx!==revision||registro!==r)return;await ui.abrirModal({titulo:`Conciliación ${c.numero_ciclo}`,contenido:`<p>${e(c.motivo)}</p><p>Ciclo ${e(c.id_ciclo)} · ${e(texto(c.tipo_ciclo))} · Algoritmo ${e(c.version_algoritmo ?? "No registrado")}</p>${universoHtml(c.universo_administrativo,"Universo utilizado por esta conciliación")}<p>${e(fecha(c.fecha_inicio))} · ${e(texto(c.estado))} · ${e(actor(c.usuario_nombre))}</p>${g.tabla([{titulo:"Elemento",valor:(_,i)=>i},{titulo:"Coincidencia",valor:f=>estados[f.estado_matching]||texto(f.estado_matching)},{titulo:"Resultado",valor:f=>estados[f.estado_resultado]||texto(f.estado_resultado)},{titulo:"Diagnóstico de este ciclo",valor:f=>f.diagnostico?.mensaje || "Diagnóstico no disponible para este resultado histórico.",html:f=>diagnosticoHtml({...f,id_ciclo_conciliacion:c.id_ciclo},true)}].map((col,i)=>i===0?{...col,valor:f=>{const elemento=elementosActuales.find(item=>item.id_importacion_feature===f.id_importacion_feature);return elemento?etiquetaElemento(elemento):`Registro ${f.id_importacion_feature} · nombre no disponible`;}}:col),c.features,null)}`,acciones:[{texto:"Cerrar",valor:true}]});return;}
                if(!editable(r))return;
                if(accion==="finalizar"){
                    await refrescar();
                    if(!editable(r) || ctx!==revision || registro!==r || !cierreVerificado || panel.querySelector('[data-gestion="finalizar"]').disabled) return;
                    paso(4);const resultado=await formulario({titulo:r.tipo_objetivo==="derecho_via_proyecto"?"Confirmar versión de DDV":"Finalizar conciliación",introduccion:r.tipo_objetivo==="derecho_via_proyecto"?"Confirma que revisaste la geometría del derecho de vía y sus observaciones.":`Elementos confirmados: ${resumenActual.confirmados??0}. Sin coincidencia: ${resumenActual.features_sin_destino??0}; estos últimos no se incorporarán al mapa. Finalizar cierra la revisión y no crea registros administrativos.`,campos:[{nombre:"confirmacion_explicita",etiqueta:"Confirmo que revisé los resultados",tipo:"checkbox",requerido:true},...(r.advertencias>0?[{nombre:"aceptar_advertencias",etiqueta:"Acepto las advertencias y reparaciones informadas",tipo:"checkbox",requerido:true}]:[])],guardar:async d=>{if(!editable(r)||ctx!==revision||registro!==r)throw Error("El proyecto cambió. Abre nuevamente la importación.");try{return await api.confirmar(r.id_importacion,d);}catch(err){await refrescar();throw err;}}});
                    if(resultado&&ctx===revision)await mostrar(resultado);
                }
                if(accion==="reconciliar"){
                    const clave=crypto.randomUUID();const resultado=await formulario({titulo:"Nueva conciliación",introduccion:"Vuelve a comparar con los registros administrativos actuales; conserva el historial de decisiones.",campos:[{nombre:"motivo",etiqueta:"Motivo",requerido:true,maximo:250,tipo:"textarea"},{nombre:"incluir_ambiguos",etiqueta:"Volver a revisar elementos con varias coincidencias",tipo:"checkbox",valor:true},{nombre:"reabrir_rechazados",etiqueta:"Volver a proponer los destinos rechazados",tipo:"checkbox"}],guardar:d=>{if(!editable(r)||ctx!==revision||registro!==r)throw Error("La importación ya no está disponible para cambios.");return api.reconciliar(r.id_importacion,{...d,clave_solicitud:clave});}});if(resultado&&ctx===revision)await mostrar(await api.obtener(r.id_importacion));
                }
            });
        });
    }
    function limpiar() {
        if (ocupado) return false;
        registro=null; ++tokenResumen; ++tokenLista; ++tokenElemento; ++tokenCiclos;
        elementosActuales=[]; cierreVerificado=false; mapa?.remove(); mapa=null;
        if(panel) { panel.hidden=true; panel.replaceChildren(); }
        return true;
    }
    window.SSALFER_GIS={cambiarProyecto,mostrar,paso,limpiar,camposArchivo,resultadoTexto,diagnosticoElemento,puedeEditar:()=>puede,exclusivo:proteger,ocupado:()=>ocupado};
    iniciar();
});
