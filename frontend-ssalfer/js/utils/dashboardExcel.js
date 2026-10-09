(() => {
    "use strict";
    const proyectosDatos=[];
    async function contarConvenios(nucleos){
        const unicos=new Map();let indice=0;
        async function worker(){while(indice<nucleos.length){const n=nucleos[indice++],afectaciones=await window.AfectacionesAPI.listarPorProyectoNucleo(n.id_proyecto_nucleo);for(const a of afectaciones){for(const c of await window.ConveniosAPI.listarPorAfectacion(a.id_afectacion))unicos.set(c.id_convenio,c);}}}
        await Promise.all(Array.from({length:Math.min(3,nucleos.length)},worker));
        const convenios=[...unicos.values()].filter(c=>c.activo!==false);
        return {individuales:convenios.filter(c=>c.ambito==='individual').length,colectivos:convenios.filter(c=>c.ambito==='colectivo').length,formalizados:convenios.filter(c=>['individual','colectivo'].includes(c.ambito)&&c.fecha_firma).length,convenios};
    }
    const textoSeguro=v=>typeof v==='string'&&/^[\s]*[=+@-]/.test(v)?`'${v}`:v;
    const fila=(hoja,values)=>hoja.addRow(values.map(v=>textoSeguro(v??'Sin dato')));
    const encabezado=(hoja,values)=>{const r=fila(hoja,values);r.font={bold:true,color:{argb:'FFFFFFFF'}};r.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FF285438'}};return r;};
    const etiquetas={asambleas:'Asambleas',cop_colectivos:'COP colectivos',cop_individuales:'COP individuales'};
    async function exportar(){
        const fin=window.SSALFER_UI.cargando.iniciar({carga:document.body});
        try{
            const wb=new ExcelJS.Workbook();wb.creator='SSALFER';wb.created=new Date();
            const nombres=new Set(['resumen','gráficos']);
            const hojaNombre=p=>{let base=String(p.clave_proyecto||p.nombre_proyecto||'Proyecto').replace(/[\\/?*\[\]:]/g,' ').replace(/^'+|'+$/g,'').trim().slice(0,31)||'Proyecto',n=base,i=2;while(nombres.has(n.toLocaleLowerCase('es'))){const suf=' '+i++;n=base.slice(0,31-suf.length)+suf;}nombres.add(n.toLocaleLowerCase('es'));return n;};
            const resumen=wb.addWorksheet('Resumen'),graficos=wb.addWorksheet('Gráficos');
            fila(resumen,['SSALFER · Resumen de proyectos']);fila(resumen,['Generado',new Date().toLocaleString('es-MX',{timeZone:'America/Mexico_City'})]);fila(resumen,['Filtros','Proyectos activos visibles para la cuenta; todos los años consultados']);fila(resumen,['Formalizados','Convenios individuales y colectivos con fecha de firma; no sustituye el KPI histórico de COP colectivos.']);
            encabezado(resumen,['Proyecto','Núcleos agrarios','Individuales','Colectivos','Formalizados']);
            let posicion=1;
            for(const d of proyectosDatos){
                fila(resumen,[d.proyecto.nombre_proyecto,d.nucleos.length,d.cop?.individuales,d.cop?.colectivos,d.cop?.formalizados]);
                const sh=wb.addWorksheet(hojaNombre(d.proyecto));fila(sh,[d.proyecto.nombre_proyecto]);fila(sh,['Clave',d.proyecto.clave_proyecto]);fila(sh,['Descripción',d.proyecto.descripcion]);fila(sh,['Inicio',d.proyecto.fecha_inicio]);fila(sh,['Fin',d.proyecto.fecha_fin]);
                encabezado(sh,['Indicador','Año','Programado','Realizado','Cantidad','Superficie (ha)','Monto ($)']);
                for(const k of d.kpis)fila(sh,[etiquetas[k.indicador]||k.indicador.replaceAll('_',' '),k.anio,k.programado,k.realizado,k.cantidad,k.superficie_ha==null?null:Number(k.superficie_ha),k.monto==null?null:Number(k.monto)]);
                encabezado(sh,['Núcleo','Municipio','Entidad']);for(const n of d.nucleos)fila(sh,[n.nombre_nucleo,n.municipio,n.entidad]);
                encabezado(sh,['Convenio','Ámbito','Fecha de firma']);if(d.cop)for(const c of d.cop.convenios)fila(sh,[`${c.tipo_convenio.replaceAll('_',' ')} · Consecutivo ${c.consecutivo}`,c.ambito,c.fecha_firma]);else fila(sh,['No se pudo consultar el detalle de convenios.']);
                graficos.getCell(`A${posicion}`).value=d.proyecto.nombre_proyecto;
                // Los gráficos existentes usan CSS. Capturarlos en canvas conserva sus cifras y rótulos.
                const panel=d.elemento.querySelector('.dashboard-graficas-grid');
                if(panel){const canvas=await html2canvas(panel,{backgroundColor:'#ffffff',scale:1.5,logging:false});const image=wb.addImage({base64:canvas.toDataURL('image/png'),extension:'png'});const width=800,height=canvas.height*width/canvas.width;graficos.addImage(image,{tl:{col:0,row:posicion},ext:{width,height}});posicion+=Math.ceil(height/20)+3;graficos.getRow(posicion).getCell(1).value='';}
                await new Promise(resolve=>setTimeout(resolve,0));
            }
            wb.eachSheet(sh=>{sh.views=[{state:'frozen',ySplit:sh===resumen?5:1}];sh.columns.forEach((c,i)=>{c.width=i===0?45:24;});sh.eachRow(r=>{r.alignment={vertical:'top',wrapText:true};});sh.pageSetup={orientation:'landscape',fitToPage:true,fitToWidth:1,fitToHeight:0};});
            const bytes=await wb.xlsx.writeBuffer(),url=URL.createObjectURL(new Blob([bytes],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})),a=document.createElement('a');a.href=url;a.download='SSALFER-dashboard.xlsx';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        }finally{fin();}
    }
    function registrar(d){
        proyectosDatos.push(d);
        d.elemento.querySelectorAll('.dashboard-dona').forEach(el=>{
            const canvas=document.createElement('canvas');canvas.width=132;canvas.height=132;canvas.style.cssText='position:absolute;inset:0;width:100%;height:100%';canvas.ariaHidden='true';const ctx=canvas.getContext('2d'),p=Number(el.style.getPropertyValue('--porcentaje'))||0;
            ctx.lineWidth=16;ctx.strokeStyle='#e4e7e5';ctx.beginPath();ctx.arc(66,66,58,0,Math.PI*2);ctx.stroke();ctx.strokeStyle='#237436';ctx.beginPath();ctx.arc(66,66,58,-Math.PI/2,-Math.PI/2+Math.PI*2*p/100);ctx.stroke();el.style.background='transparent';el.prepend(canvas);
        });
    }
    window.SSALFER_DASHBOARD_EXCEL={contarConvenios,registrar,listo:()=>{document.getElementById('btnExportarDashboardExcel').disabled=false;}};
    document.addEventListener('DOMContentLoaded',()=>{
        const csv=document.getElementById('btnExportarDashboardCsv');if(!csv)return;
        const b=document.createElement('button');b.type='button';b.className='btn-secundario';b.textContent='Exportar dashboard (Excel)';b.id='btnExportarDashboardExcel';b.disabled=true;csv.before(b);csv.textContent='CSV de respaldo';
        b.onclick=async()=>{if(!proyectosDatos.length){window.SSALFER_UI.toast('Espera a que se carguen los proyectos.');return;}b.disabled=true;try{await exportar();}catch(err){window.ClienteAPI.mostrarErrorAPI(err);}finally{b.disabled=false;}};
    });
})();
