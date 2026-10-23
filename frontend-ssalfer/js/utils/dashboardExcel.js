(() => {
    "use strict";
    const proyectosDatos=[];
    let operacion = null, disponible = false;
    const boton = () => document.getElementById('btnExportarDashboardExcel');
    const estado = mensaje => { const el = document.getElementById('estadoExportacionDashboard'); if (el) { el.textContent = mensaje; el.hidden = !mensaje; } };
    function cancelar() { operacion?.abort(); }
    window.addEventListener('pagehide', cancelar);
    window.addEventListener('popstate', cancelar);
    document.addEventListener('ssalfer:sesion-invalida', cancelar);
    document.addEventListener('click', e => {
        const enlace = e.target.closest?.('a[href]');
        const cierre = e.target.closest?.('[data-action="logout"]');
        if (cierre || (enlace && !e.defaultPrevented && !e.ctrlKey && !e.metaKey &&
            !enlace.target && new URL(enlace.href, window.location.href).pathname !== window.location.pathname)) cancelar();
    });
    try {
        const canal = new BroadcastChannel('ssalfer-sesion');
        canal.onmessage = e => { if (e.data === 'sesion-cerrada') cancelar(); };
    } catch { /* La comprobación de sesión sigue activa sin BroadcastChannel. */ }
    function comprobarOperacion(control) {
        control.signal.throwIfAborted();
        if (operacion !== control || window.SSALFER_SESION_INVALIDA) throw new DOMException('Exportación cancelada', 'AbortError');
    }
    async function identidad(signal) {
        const sesion = await window.ClienteAPI.get('/auth/sesion', {signal, silencioso: true});
        if (!Number.isSafeInteger(sesion?.user?.id_usuario)) throw new Error('No se pudo comprobar tu sesión. Vuelve a iniciar sesión.');
        return `${sesion.user.id_usuario}:${sesion.user.rol}`;
    }
    const textoSeguro=v=>typeof v==='string'&&/^[\s]*[=+@-]/.test(v)?`'${v}`:v;
    const fila=(hoja,values)=>hoja.addRow(values.map(v=>textoSeguro(v??'Sin dato')));
    const encabezado=(hoja,values)=>{const r=fila(hoja,values);r.font={bold:true,color:{argb:'FFFFFFFF'}};r.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FF285438'}};return r;};
    const etiquetas={asambleas:'Asambleas',cop_colectivos:'COP colectivos',cop_individuales:'COP individuales'};
    async function exportar(control){
        const fin=window.SSALFER_UI.cargando.iniciar({silencioso:true});
        try{
            const signal = control.signal;
            const sesionDocumento = await (window.SSALFER_SESION_LISTA || window.AuthAPI.obtenerSesionActual());
            const usuario = await identidad(signal);
            if (usuario !== `${sesionDocumento?.user?.id_usuario}:${sesionDocumento?.user?.rol}`) throw Object.assign(new Error('La cuenta cambió. Actualiza el dashboard antes de exportar.'), {codigo: 'CUENTA_CAMBIADA'});
            const datos = [];
            for (const d of proyectosDatos) {
                comprobarOperacion(control);
                estado(`Preparando Excel: ${d.proyecto.nombre_proyecto}…`);
                const detalle = await window.NucleosAPI.exportacionDashboard(d.proyecto.id_proyecto, {signal});
                comprobarOperacion(control);
                await window.NucleosAPI.validarExportacionDashboard(detalle, d.cop, {signal});
                datos.push({...d, detalle, nucleos: detalle.nucleos.items, cop: {...d.cop, convenios: detalle.convenios.items}});
            }
            comprobarOperacion(control);
            const wb=new ExcelJS.Workbook();wb.creator='SSALFER';wb.created=new Date();
            const nombres=new Set(['resumen','gráficos']);
            const hojaNombre=p=>{let base=String(p.clave_proyecto||p.nombre_proyecto||'Proyecto').replace(/[\\/?*\[\]:]/g,' ').replace(/^'+|'+$/g,'').trim().slice(0,31)||'Proyecto',n=base,i=2;while(nombres.has(n.toLocaleLowerCase('es'))){const suf=' '+i++;n=base.slice(0,31-suf.length)+suf;}nombres.add(n.toLocaleLowerCase('es'));return n;};
            const resumen=wb.addWorksheet('Resumen'),graficos=wb.addWorksheet('Gráficos');
            fila(resumen,['SSALFER · Resumen de proyectos']);fila(resumen,['Generado',new Date().toLocaleString('es-MX',{timeZone:'America/Mexico_City'})]);fila(resumen,['Filtros','Proyectos activos visibles para la cuenta; todos los años consultados']);fila(resumen,['Formalizados','Convenios individuales y colectivos con fecha de firma; no sustituye el KPI histórico de COP colectivos.']);
            encabezado(resumen,['Proyecto','Núcleos agrarios','Individuales','Colectivos','Formalizados']);
            let posicion=1;
            for(const d of datos){
                comprobarOperacion(control);
                fila(resumen,[d.proyecto.nombre_proyecto,d.nucleos.length,d.cop?.individuales,d.cop?.colectivos,d.cop?.formalizados]);
                const sh=wb.addWorksheet(hojaNombre(d.proyecto));fila(sh,[d.proyecto.nombre_proyecto]);fila(sh,['Clave',d.proyecto.clave_proyecto]);fila(sh,['Descripción',d.proyecto.descripcion]);fila(sh,['Inicio',d.proyecto.fecha_inicio]);fila(sh,['Fin',d.proyecto.fecha_fin]);
                encabezado(sh,['Indicador','Año','Programado','Realizado','Cantidad','Superficie (ha)','Monto ($)']);
                for(const k of d.kpis)fila(sh,[etiquetas[k.indicador]||k.indicador.replaceAll('_',' '),k.anio,k.programado,k.realizado,k.cantidad,k.superficie_ha==null?null:Number(k.superficie_ha),k.monto==null?null:Number(k.monto)]);
                encabezado(sh,['Núcleo','Municipio','Entidad']);for(const n of d.nucleos)fila(sh,[n.nombre_nucleo,n.municipio,n.entidad]);
                // El resumen F04 ordena por ID; conservar ese orden también en
                // la presentación, sin reordenar ni cambiar los datos recibidos.
                encabezado(sh,['Convenio','Ámbito','Fecha de firma']);if(d.cop)for(const c of [...d.cop.convenios].sort((a,b)=>a.id_convenio-b.id_convenio))fila(sh,[`${c.tipo_convenio==null?'Tipo no informado':c.tipo_convenio.replaceAll('_',' ')} · Consecutivo ${c.consecutivo}`,c.ambito,c.fecha_firma]);else fila(sh,['No se pudo consultar el detalle de convenios.']);
                graficos.getCell(`A${posicion}`).value=d.proyecto.nombre_proyecto;
                // Los gráficos existentes usan CSS. Capturarlos en canvas conserva sus cifras y rótulos.
                const panel=d.elemento.querySelector('.dashboard-graficas-grid');
                if(panel){const canvas=await html2canvas(panel,{backgroundColor:'#ffffff',scale:1.5,logging:false});const image=wb.addImage({base64:canvas.toDataURL('image/png'),extension:'png'});const width=800,height=canvas.height*width/canvas.width;graficos.addImage(image,{tl:{col:0,row:posicion},ext:{width,height}});posicion+=Math.ceil(height/20)+3;graficos.getRow(posicion).getCell(1).value='';}
                await new Promise(resolve=>setTimeout(resolve,0));
            }
            wb.eachSheet(sh=>{sh.views=[{state:'frozen',ySplit:sh===resumen?5:1}];sh.columns.forEach((c,i)=>{c.width=i===0?45:24;});sh.eachRow(r=>{r.alignment={vertical:'top',wrapText:true};});sh.pageSetup={orientation:'landscape',fitToPage:true,fitToWidth:1,fitToHeight:0};});
            const bytes = await wb.xlsx.writeBuffer();
            comprobarOperacion(control);
            estado('Comprobando que la información siga vigente…');
            // También cubre cambios ocurridos mientras se construían hojas y gráficos.
            for (const d of datos) await window.NucleosAPI.validarExportacionDashboard(d.detalle, d.cop, {signal});
            if (await identidad(signal) !== usuario) throw Object.assign(new Error('La cuenta cambió. Actualiza el dashboard antes de exportar.'), {codigo: 'CUENTA_CAMBIADA'});
            comprobarOperacion(control);
            const url = URL.createObjectURL(new Blob([bytes], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));
            const a = document.createElement('a');
            a.href = url; a.download = 'SSALFER-dashboard.xlsx'; a.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            estado('Excel completo. Descarga iniciada.');
        }finally{fin();}
    }
    function registrar(d){
        const anterior = proyectosDatos.findIndex(p => p.proyecto.id_proyecto === d.proyecto.id_proyecto);
        if (anterior < 0) proyectosDatos.push(d); else proyectosDatos[anterior] = d;
        d.elemento.querySelectorAll('.dashboard-dona').forEach(el=>{
            const canvas=document.createElement('canvas');canvas.width=132;canvas.height=132;canvas.style.cssText='position:absolute;inset:0;width:100%;height:100%';canvas.ariaHidden='true';const ctx=canvas.getContext('2d'),p=Number(el.style.getPropertyValue('--porcentaje'))||0;
            ctx.lineWidth=16;ctx.strokeStyle='#e4e7e5';ctx.beginPath();ctx.arc(66,66,58,0,Math.PI*2);ctx.stroke();ctx.strokeStyle='#237436';ctx.beginPath();ctx.arc(66,66,58,-Math.PI/2,-Math.PI/2+Math.PI*2*p/100);ctx.stroke();el.style.background='transparent';el.prepend(canvas);
        });
    }
    window.SSALFER_DASHBOARD_EXCEL = {registrar, listo: (total, reportesCompletos = true) => {
        proyectosDatos.sort((a,b) => (a.orden ?? 0) - (b.orden ?? 0));
        disponible = total > 0 && proyectosDatos.length === total && reportesCompletos;
        if (boton()) boton().disabled = !disponible || !!operacion;
        if (!disponible) estado('Falta información del dashboard. Reintenta los resúmenes o actualiza la pantalla antes de exportar.');
        else estado('');
    }};
    document.addEventListener('DOMContentLoaded',()=>{
        const b=boton();if(!b)return;
        b.disabled = true;
        const aviso = document.createElement('p'); aviso.id = 'estadoExportacionDashboard';
        aviso.hidden = true;
        aviso.setAttribute('role', 'status'); aviso.setAttribute('aria-live', 'polite');
        aviso.style.cssText = 'margin:0;text-align:right;font-size:.95rem;';
        if (b.parentElement) b.parentElement.insertAdjacentElement('afterend', aviso); else b.before(aviso);
        b.setAttribute('aria-describedby', aviso.id);
        b.onclick = async () => {
            if (!disponible || operacion) return;
            const control = new AbortController(); operacion = control;
            b.disabled = true; b.setAttribute('aria-busy', 'true'); b.textContent = 'Preparando Excel…';
            try { await exportar(control); }
            catch (error) {
                control.abort(); // Detiene también el recurso paralelo, sin conservar lotes parciales.
                const mensaje = error.codigo === 'CUENTA_CAMBIADA' ? error.message : error.name === 'AbortError' ? 'Exportación cancelada. No se descargó ningún archivo.' :
                    error.status === 409 ? 'La información cambió. Actualiza el dashboard y vuelve a exportar.' :
                    error.status === 401 ? 'Tu sesión terminó. Inicia sesión para volver a exportar.' :
                    error.status === 403 ? 'Ya no tienes acceso a uno de los proyectos. Actualiza el dashboard.' :
                    'No se pudo completar el Excel. No se descargó ningún archivo. Vuelve a intentar; si persiste, actualiza el dashboard.';
                estado(mensaje);
            } finally {
                if (operacion === control) operacion = null;
                b.disabled = !disponible || !!window.SSALFER_SESION_INVALIDA;
                b.removeAttribute('aria-busy'); b.textContent = 'Exportar dashboard (Excel)';
            }
        };
    });
})();
