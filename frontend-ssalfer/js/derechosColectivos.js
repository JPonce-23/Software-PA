document.addEventListener("DOMContentLoaded", async () => {
    "use strict";
    const id = Number(new URLSearchParams(location.search).get("id_proyecto_nucleo"));
    const periodoTabla = window.SSALFER_PERIODOS.tabla;
    const { e, tabla } = window.SSALFER_GESTION;
    const f = window.SSALFER_FORMAT, fecha = v => f.formatearFecha(v), codigo = v => f.etiquetaCodigo(v);
    const ha = v => v == null ? "—" : `${Number(v).toLocaleString("es-MX", { maximumFractionDigits: 6 })} ha`;
    const dinero = v => v == null ? "—" : Number(v).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
    const link = (pagina, query, texto) => `<a class="btn-secundario" href="/pages/${pagina}.html?${e(new URLSearchParams(query))}">${e(texto)}</a>`;
    const raiz = document.getElementById("colectivosContenido");
    raiz.addEventListener('click',event=>{const b=event.target.closest('[data-texto-completo]');if(b)window.SSALFER_UI.abrirModal({titulo:'Texto completo',contenido:`<p>${e(b.dataset.textoCompleto)}</p>`,acciones:[{texto:'Cerrar',valor:true}]});});
    if (!Number.isSafeInteger(id) || id <= 0) { raiz.textContent = "Abre Derechos colectivos desde la ficha de un núcleo."; return; }
    try {
        const contexto = window.SSALFER_CONTEXTO.crear(id);
        const nucleo = (await contexto.listar("proyecto_nucleo"))[0].item;
        const proyecto = await window.ProyectosAPI.obtener(nucleo.id_proyecto);
        document.getElementById("colectivosContexto").textContent = `${nucleo.nombre_nucleo} · ${proyecto.nombre_proyecto}`;
        const afectaciones = await window.AfectacionesAPI.listarPorProyectoNucleo(id, { tipo: "colectivo" });
        raiz.innerHTML = `<section class="ssalfer-gestion-seccion"><h2>Afectaciones colectivas</h2>${link("afectacion", { id_proyecto_nucleo: id, tipo: "colectivo" }, "Nueva afectación colectiva")}${afectaciones.length ? afectaciones.map(a => `<details class="colectivo-detalle" data-afectacion="${a.id_afectacion}"><summary>Colectiva · ${e(ha(a.superficie_afectada_ha))} · ${e(a.situacion || "Sin situación registrada")} · ${a.tipo_cop_revision_pendiente ? "COP pendiente de revisión" : "Sin revisión COP pendiente"}</summary><div data-colectivo-detalle></div></details>`).join("") : "<p>Aún no hay afectaciones colectivas. Puedes registrar una con el botón anterior.</p>"}</section><section class="ssalfer-gestion-seccion"><h2>Representación y respaldo del núcleo</h2><div id="respaldoColectivo" class="ssalfer-gestion-campos"></div></section>`;
        raiz.querySelectorAll("details").forEach(detalle => { detalle.cargar = async () => {
            if (detalle.dataset.cargado) return;
            if (detalle.cargaActual) return detalle.cargaActual;
            detalle.dataset.cargando = "true";
            const aid = Number(detalle.dataset.afectacion), cuerpo = detalle.querySelector("[data-colectivo-detalle]");
            try {
                const [unidades, convenios, indemnizaciones, unidadesNucleo, destinos] = await Promise.all([window.UnidadesAgrariasAPI.listarPorAfectacion(aid), window.ConveniosAPI.listarPorAfectacion(aid), window.IndemnizacionAPI.listarPorAfectacion(aid), contexto.listar("unidad_agraria"), window.CatalogosAPI.obtenerOperativo("destino_superficie")]);
                const porUnidad = new Map(unidadesNucleo.map(u => [u.id, u]));
                const porDestino = new Map(destinos.map(d => [d.id_catalogo_opcion, d.nombre]));
                cuerpo.innerHTML = `<div class="ssalfer-gestion-barra">${link("detalleAfectacion", { id_afectacion: aid }, "Consultar afectación")}${link("nuevoConvenio", { id_afectacion: aid }, "Nuevo convenio")}${link("indemnizacion", { id_afectacion: aid }, "Indemnización y pagos")}</div><h3>Superficies y destinos</h3>${tabla([{ titulo: "Unidad", valor: u => porUnidad.get(u.id_unidad_agraria)?.etiqueta || "Unidad sin referencia" }, { titulo: "Destino", valor: u => porDestino.get(porUnidad.get(u.id_unidad_agraria)?.item.id_destino_superficie) || "Sin destino registrado" }, { titulo: "Superficie (ha)", valor: u => ha(u.superficie_afectada_ha), csv:u=>u.superficie_afectada_ha==null?"":Number(u.superficie_afectada_ha), numerico:true }], unidades, u => link("unidadAgraria", { id_unidad_agraria: u.id_unidad_agraria, id_proyecto_nucleo:id }, "Consultar unidad"))}<h3>Convenios</h3>${periodoTabla([{ titulo: "Convenio", valor: c => `${codigo(c.tipo_convenio)} · Consecutivo ${c.consecutivo}` }, { titulo: "Firma", valor: c => fecha(c.fecha_firma) }], convenios, c => link("fichaConvenio", { id_convenio: c.id_convenio }, "Consultar"), "fecha_firma", "la fecha de firma del convenio")}<div data-pagos></div>`;
                const lista = Array.isArray(indemnizaciones) ? indemnizaciones : indemnizaciones ? [indemnizaciones] : [];
                const pagos = cuerpo.querySelector("[data-pagos]");
                if (!lista.length) pagos.innerHTML = "<p>Aún no hay indemnización registrada.</p>";
                for (const indemnizacion of lista) {
                    const registros = await window.IndemnizacionAPI.listarPagos(indemnizacion.id_indemnizacion);
                    pagos.insertAdjacentHTML("beforeend", `<h3>Indemnización · ${e(codigo(indemnizacion.estatus))}</h3>${periodoTabla([{ titulo: "Beneficiario", valor: p => p.beneficiario_nombre }, { titulo: "Pago (MXN)", valor: p => dinero(p.monto), csv:p=>p.monto==null?"":Number(p.monto), numerico:true }, { titulo: "Fecha", valor: p => fecha(p.fecha_pago) }], registros, null, "fecha_pago", "la fecha del pago", "Aún no hay pagos registrados.")}`);
                }
                detalle.dataset.cargado = "true";
            } catch (error) { cuerpo.textContent = `${error.message}. Cierra y vuelve a abrir este bloque para reintentar.`; }
            finally { delete detalle.dataset.cargando; }
        }; detalle.addEventListener("toggle", () => { if (detalle.open) detalle.cargaActual=detalle.cargar().finally(()=>{detalle.cargaActual=null;}); }); });
        const respaldo = document.getElementById("respaldoColectivo");
        await Promise.all([ ["orv", "orv", "Órganos de representación"], ["padron_historial", "padrones", "Padrones"], ["asamblea", "asamblea", "Asambleas"], ["tramite_ran", "tramiteRan", "Trámites RAN"], ["tramite_fifonafe", "fifonafe", "Trámites FIFONAFE"] ].map(async ([tipo, pagina, titulo]) => {
            const tarjeta = document.createElement("div"); respaldo.appendChild(tarjeta);
            try {
                const filas = await contexto.listar(tipo);
                let resumen = `${filas.length} registros`;
                if (tipo === "padron_historial" && filas.length) resumen += ` · Más reciente: ${fecha(filas.map(r => r.item.fecha_padron).filter(Boolean).sort().at(-1))}`;
                if (tipo === "asamblea") resumen += ` · ${(await contexto.listar("asamblea_convocatoria")).length} convocatorias`;
                if (tipo === "orv") resumen += ` · ${filas.filter(r => !r.item.fin_vigencia || r.item.fin_vigencia >= new Date().toISOString().slice(0,10)).length} sin vigencia vencida`;
                tarjeta.innerHTML = `<h3>${e(titulo)}</h3><p>${e(resumen)}</p>${link(pagina, { id_proyecto_nucleo: id }, "Abrir")}`;
            } catch (error) { tarjeta.innerHTML = `<h3>${e(titulo)}</h3><p role="alert">No fue posible consultar este resumen.</p>${link(pagina, { id_proyecto_nucleo: id }, "Abrir y reintentar")}`; }
        }));
        const exportar = document.createElement('button');exportar.type='button';exportar.className='btn-secundario';exportar.textContent='Exportar pantalla completa (CSV)';raiz.prepend(exportar);
        exportar.onclick=async()=>{
            exportar.disabled=true;
            try{
                for(const d of raiz.querySelectorAll('details[data-afectacion]'))await d.cargar();
                if([...raiz.querySelectorAll('details[data-afectacion]')].some(d=>!d.dataset.cargado))throw Error('No se pudo reunir toda la información. Reintenta la consulta antes de exportar.');
                const rows=[['Núcleo',nucleo.nombre_nucleo],['Proyecto',proyecto.nombre_proyecto],['Generado',new Date().toLocaleString('es-MX')]];
                const agregarTabla=(t,seccion,origen)=>{
                    const cab=[...t.querySelectorAll('thead th')].map(n=>n.textContent);
                    if(seccion==='Destino colectivo'){cab[5]='Superficie (ha)';cab[6]='Superficie declarada (ha)';cab[7]='Monto del convenio (MXN, no aditivo)';}
                    rows.push(['Sección','Origen','Periodo',...cab]);
                    for(const tr of t.querySelectorAll('tbody tr'))rows.push([seccion,origen,t.closest('section')?.querySelector('h4')?.textContent||'Sin fecha registrada',...[...tr.cells].map(c=>c.dataset.numerico&&c.dataset.csv!==''?Number(c.dataset.csv):c.dataset.csv??c.textContent.trim())]);
                };
                for(const d of raiz.querySelectorAll('details[data-afectacion]')){
                    const origen=d.querySelector('summary').textContent;rows.push(['Afectación',origen]);
                    for(const nota of d.querySelectorAll('h3,p'))rows.push(['Contexto y estado',origen,nota.textContent.trim()]);
                    for(const t of d.querySelectorAll('table'))agregarTabla(t,'Detalle de afectación',origen);
                }
                for(const tarjeta of respaldo.children)rows.push(['Representación y respaldo','Núcleo',tarjeta.innerText.replace(/\s+/g,' ')]);
                for(const t of document.querySelectorAll('#reporteColectivo table'))agregarTabla(t,'Destino colectivo','Convenio');
                const celda=v=>'"'+(typeof v==='number'?String(v):String(v??'').replace(/^[\s]*[=+@-]/,m=>"'"+m)).replaceAll('"','""')+'"';const csv=rows.map(r=>r.map(celda).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='derechos-colectivos-completo.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
            }catch(error){window.ClienteAPI.mostrarErrorAPI(error);}finally{exportar.disabled=false;}
        };
        await window.SSALFER_REPORTE_COLECTIVO.montar(document.getElementById("reporteColectivo"), nucleo.id_proyecto, id);
    } catch (error) { raiz.textContent = error.message || "No fue posible consultar los derechos colectivos."; raiz.setAttribute("role", "alert"); }
});
