(() => {
    "use strict";
    async function montar(raiz,id) {
        const g=window.SSALFER_GESTION,api=window.DocumentosAPI;
        const categorias=window.SSALFER_CONTEXTO.nombres;
        let revision=0,filas=[],cache=null;
        raiz.innerHTML=`<h2>Documentos registrados del núcleo</h2><p>Documentos autorizados de este núcleo, agrupados con todas sus procedencias.</p><div class="ssalfer-gestion-campos"><label class="ssalfer-gestion-campo">Categoría<select data-categoria></select></label><label class="ssalfer-gestion-campo">Estado<select data-estado><option value="">Todos</option><option>disponible</option><option>faltante</option><option>referenciado</option></select></label><label class="ssalfer-gestion-campo">Buscar<input data-texto type="search" placeholder="Título, tipo, folio o registro"></label></div>${g.boton("Actualizar documentos","actualizar")}<p data-conteo role="status"></p><div data-listado></div>`;
        const categoria=raiz.querySelector("[data-categoria]"),estado=raiz.querySelector("[data-estado]"),buscar=raiz.querySelector("[data-texto]"),salida=raiz.querySelector("[data-listado]");
        categoria.add(new Option("Todas",""));
        const normal=v=>String(v??"").normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
        function mostrar(){
            const rows=filas.filter(r=>(!categoria.value||r.categorias.has(categoria.value))&&(!estado.value||r.estado===estado.value)&&normal([r.titulo,api.nombreTipo(r),r.numero_folio,r.origen,r.descripcion].join(' ')).includes(normal(buscar.value)));
            salida.innerHTML=g.tabla([{titulo:"Título",valor:r=>r.titulo},{titulo:"Tipo",valor:r=>api.nombreTipo(r)},{titulo:"Estado",valor:r=>r.estado},{titulo:"Fecha",valor:r=>window.SSALFER_FORMAT.formatearFecha(r.fecha_documento)},{titulo:"Folio",valor:r=>r.numero_folio},{titulo:"Descripción",valor:r=>r.descripcion},{titulo:"Registro de origen",valor:r=>r.origen},{titulo:"Versión vigente",valor:r=>r.version?.numero_version??"Sin archivo"},{titulo:"Archivo",valor:r=>r.version?.nombre_original},{titulo:"Tamaño",valor:r=>r.version?`${Number(r.version.tamano_bytes).toLocaleString('es-MX')} bytes`:"Sin archivo"}],rows,r=>g.boton("Ver","ver",r.id_documento)+g.boton("Descargar","descargar",r.id_documento)+g.boton("Historial de versiones","historial",r.id_documento),"No hay documentos para estos filtros.");
            raiz.querySelector("[data-conteo]").textContent=`${rows.length} documentos visibles de ${filas.length}.`;
        }
        async function cargar(forzar=false){
            const actual=++revision;salida.textContent='Consultando documentos…';if(forzar)cache=null;
            try{
                const datos=cache||await api.listarConsolidados(id);if(actual!==revision)return;cache=datos;
                const acumulados=new Map(),tipos=new Set();
                for(const row of datos){
                    const d=row.documento;tipos.add(row.entidad_tipo);
                    const nombre=categorias[row.entidad_tipo]||window.SSALFER_FORMAT.etiquetaCodigo(row.entidad_tipo);
                    const origen=!row.origen || /#\s*\d+/.test(row.origen) ? nombre : row.origen;
                    const fuente=row.fuente_relacion==='expediente_requisito'?'Referencia de requisito documental':'Vínculo documental';
                    if(!acumulados.has(d.id_documento))acumulados.set(d.id_documento,{...d,version:row.version_vigente,origenes:new Set(),categorias:new Set()});
                    const item=acumulados.get(d.id_documento);item.origenes.add(`${nombre} · ${origen} · ${fuente}`);item.categorias.add(row.entidad_tipo);
                }
                const previo=categoria.value;categoria.replaceChildren(new Option('Todas',''));[...tipos].forEach(t=>categoria.add(new Option(categorias[t]||window.SSALFER_FORMAT.etiquetaCodigo(t),t)));categoria.value=tipos.has(previo)?previo:'';
                filas=[...acumulados.values()].map(d=>({...d,origen:[...d.origenes].join(' / ')})).sort((a,b)=>String(b.fecha_documento||'').localeCompare(String(a.fecha_documento||'')));
                salida.removeAttribute('role');mostrar();
            }catch(error){if(actual===revision){salida.textContent=error.message;salida.setAttribute('role','alert');}}
        }
        categoria.onchange=mostrar;estado.onchange=mostrar;buscar.oninput=mostrar;
        raiz.addEventListener('click',async event=>{
            const b=event.target.closest('[data-gestion]');if(!b)return;if(b.dataset.gestion==='actualizar'){cargar(true);return;}
            const d=filas.find(r=>r.id_documento===Number(b.dataset.registro));if(!d)return;
            if(b.dataset.gestion==='historial'){
                try { const versiones=await api.listarVersiones(d.id_documento);
                await window.SSALFER_UI.abrirModal({titulo:'Historial de versiones',contenido:g.tabla([{titulo:'Versión',valor:v=>v.numero_version},{titulo:'Archivo',valor:v=>v.nombre_original},{titulo:'Fecha de carga',valor:v=>window.SSALFER_FORMAT.formatearFecha(v.fecha_carga)}],versiones,null,'Este documento aún no tiene archivos.'),acciones:[{texto:'Cerrar',valor:true}]}); } catch(error){window.ClienteAPI.mostrarErrorAPI(error);}return;
            }
            if(!d.version){window.SSALFER_UI.toast(d.archivoError?'No se pudo consultar el archivo. Actualiza la categoría para reintentar.':'Este documento aún no tiene archivo subido.');return;}
            const ver=b.dataset.gestion==='ver',pestana=ver?window.open('about:blank','_blank'):null;
            if(ver&&!pestana){window.SSALFER_UI.toast('Permite abrir pestañas para visualizar el archivo.',{tipo:'error'});return;}
            if(pestana){pestana.opener=null;pestana.document.body.textContent='Preparando archivo…';}
            b.disabled=true;
            try{const blob=await window.ClienteAPI.get(`/documentos/versiones/${d.version.id_documento_version}/descarga`,{tipoRespuesta:'blob'}),url=URL.createObjectURL(blob);
                const visualizable=/^(application\/pdf|image\/(png|jpeg|gif|webp|avif|bmp))(?:;|$)/i.test(blob.type);
                if(ver&&visualizable)pestana.location.href=url;else{pestana?.close();const a=document.createElement('a');a.href=url;a.download=d.version.nombre_original;a.click();if(ver)window.SSALFER_UI.toast('Este tipo de archivo se descarga para abrirlo con su aplicación.');}
                setTimeout(()=>URL.revokeObjectURL(url),ver?300000:1000);
            }catch(err){pestana?.close();window.ClienteAPI.mostrarErrorAPI(err);}finally{b.disabled=false;}
        });
        window.addEventListener('ssalfer:documentos',()=>{cargar(true);});
        await cargar();
    }
    window.SSALFER_LISTADO_DOCUMENTOS={montar};
})();
