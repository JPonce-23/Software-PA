/* Contrato V1. Nunca completa datos faltantes mediante consultas por convenio. */
(() => {
    'use strict';
    const individuales = ['NO.', 'ESTADO', 'MUNICIPIO', 'NÚCLEO AGRARIO', 'NO. DE PARCELA', 'TIPO DE CONVENIO', 'SUPERFICIE (M2)', 'FIRMA DE COP (FECHA)', 'INGRESO AL RAN (FECHA)', 'INSCRITO AL RAN (FECHA)', 'Monto total 90%', 'Monto total 100%'];
    const colectivos = ['NO.', 'ESTADO', 'MUNICIPIO', 'NÚCLEO AGRARIO', 'DESTINO DE LA SUPERFICIE', 'SUPERFICIE (M2)', 'ASAMBLEA REALIZADA (FECHA)', 'INGRESO AL RAN (FECHA)', 'INSCRITO AL RAN (FECHA)', 'FIRMA DE COP (FECHA)', 'INGRESO AL RAN (FECHA)', 'INSCRITO AL RAN (FECHA)'];
    const nota = 'Superficie individual pendiente de definición. Fechas RAN: primeros hitos históricos, no trámite vigente. Se incluyen instrumentos administrativamente activos; sus montos no representan necesariamente obligaciones vigentes.';
    function filasIndividuales(lista) {
        return lista.map(c => [c.no, c.estado, c.municipio, c.nucleo_agrario,
            c.parcelas.map(p => p.no_parcela == null ? 'Sin número registrado' : String(p.no_parcela)).join('; ') || null,
            c.tipo_cop_operativo, c.superficie_excel_m2, c.fecha_firma_cop, c.fecha_ingreso_ran_convenio,
            c.fecha_inscripcion_ran_convenio, c.monto_total_90, c.monto_total_100]);
    }
    function filasColectivos(lista) {
        return lista.flatMap(c => (c.destinos.length ? c.destinos : [null]).map(d => [c.no, c.estado, c.municipio, c.nucleo_agrario,
            d?.nombre ?? null, d?.superficie?.superficie_m2 ?? null, c.fecha_asamblea_realizada,
            c.fecha_ingreso_ran_asamblea, c.fecha_inscripcion_ran_asamblea, c.fecha_firma_cop,
            c.fecha_ingreso_ran_convenio, c.fecha_inscripcion_ran_convenio]));
    }
    function validar(r, id, completo = false) {
        if (r?.version !== '1' || Number(r.id_proyecto) !== Number(id) || !Array.isArray(r.individuales) || !Array.isArray(r.colectivos)) throw Error('La respuesta del reporte no tiene el formato esperado.');
        for (const grupo of ['individuales', 'colectivos']) {
            const p = r[`paginacion_${grupo}`];
            if (!p || !Number.isInteger(p.total) || p.total < r[grupo].length) throw Error('No se pudo comprobar el total del reporte.');
            if (completo && (!r.completo || p.hay_mas || p.total !== r[grupo].length)) throw Error('La respuesta está incompleta. No se descargó ningún archivo.');
        }
        return r;
    }
    // Excel conserva 15 cifras significativas. Los decimales mayores se guardan como texto exacto.
    function decimal(v) {
        if (v == null) return null;
        const s = String(v), cifras = s.replace(/^-/, '').replace('.', '').replace(/^0+/, '').replace(/0+$/, '');
        if (!/^-?\d+(\.\d+)?$/.test(s)) throw Error('El reporte contiene un decimal inválido.');
        return cifras.length > 15 || (s.split('.')[1]?.replace(/0+$/, '').length || 0) > 10 || !Number.isFinite(Number(s)) || (Number(s) === 0 && /[1-9]/.test(s)) ? s : Number(s);
    }
    function libro(r, contexto) {
        const X = window.XLSX;
        if (!X) throw Error('No se pudo cargar el componente de Excel. Actualiza la pantalla e intenta de nuevo.');
        const wb = X.utils.book_new();
        for (const [nombre, cabecera, filas, fechas, decimales] of [
            ['Convenios individuales', individuales, filasIndividuales(r.individuales), [7,8,9], [6,10,11]],
            ['Convenios colectivos', colectivos, filasColectivos(r.colectivos), [6,7,8,9,10,11], [5]]
        ]) {
            const matriz = [[nombre], [contexto], [nota], [nombre === 'Convenios colectivos' ? 'G–I: asamblea. J–L: convenio. El NO. identifica el convenio y puede repetirse por destino.' : 'Una fila por convenio. Parcelas reunidas en una celda. Montos independientes en MXN.'], cabecera, ...filas];
            if (!filas.length) matriz.push(['Sin convenios para el filtro seleccionado']);
            const ws = X.utils.aoa_to_sheet(matriz);
            filas.forEach((fila, i) => {
                fechas.forEach(j => {
                    if (fila[j] == null) return;
                    const s = String(fila[j]);
                    if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || !Number.isFinite(Date.parse(s))) throw Error('El reporte contiene una fecha inválida.');
                    ws[X.utils.encode_cell({r:i+5,c:j})] = {t:'n', v:Date.parse(s + 'T00:00:00Z') / 86400000 + 25569, z:'dd/mm/yyyy'};
                });
                decimales.forEach(j => {
                    const v = decimal(fila[j]);if (v == null) return;
                    ws[X.utils.encode_cell({r:i+5,c:j})] = {t:typeof v === 'number' ? 'n' : 's', v, z:j>=10 ? '"$"#,##0.00' : '#,##0.##########'};
                });
            });
            ws['!cols'] = [8,23,29,32,30,24,24,24,24,24,24,24].map(wch=>({wch}));
            ws['!merges'] = [0,1,2,3].map(row=>({s:{r:row,c:0},e:{r:row,c:11}}));
            ws['!autofilter'] = {ref:`A5:L${Math.max(5,5+filas.length)}`};
            X.utils.book_append_sheet(wb, ws, nombre);
        }
        wb.Props = {Title:'Reporte general de convenio', Subject:nota, Author:'SSALFER'};
        return wb;
    }
    function crear(el) {
        let activo=false, token=0, pagina=1, datos=null, ocupado=false, exportando=false, proyecto, entidad, selector;
        let grupo="individuales";
        const normalizar = v => String(v ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
        const observaciones = {SIN_AFECTACIONES_ACTIVAS:"Este convenio no tiene afectaciones activas vinculadas.", SIN_UNIDADES_ACTIVAS:"Este convenio no tiene unidades agrarias activas vinculadas.", SUPERFICIE_EXCEL_INDIVIDUAL_PENDIENTE_DEFINICION:"Aún no se ha definido qué superficie usar para los convenios individuales. Esa columna queda vacía.", SIN_ASAMBLEA_CELEBRADA_VINCULADA:"No hay una asamblea celebrada vinculada a este convenio; su fecha queda vacía.", CLASIFICACION_COP_INCOMPLETA_O_AMBIGUA:"Falta precisar la clasificación del convenio.", RAN_CONVENIO_MULTIPLES_TRAMITES_SIN_VIGENCIA_DETERMINADA:"El convenio tiene varios trámites RAN. Se muestran las primeras fechas históricas registradas.", RAN_ASAMBLEA_MULTIPLES_TRAMITES_SIN_VIGENCIA_DETERMINADA:"La asamblea tiene varios trámites RAN. Se muestran las primeras fechas históricas registradas."};
        const mensaje = text => {el.info.textContent=text;el.info.hidden=!text;};
        const limpiar = () => {el.error.hidden=true;el.error.textContent='';};
        function error(e) {
            const texto = e.status===413 ? 'El reporte supera 10,000 convenios. Selecciona un estado para reducirlo. No se descargó un archivo parcial.' : e.status===404 ? 'El servidor aún no tiene disponible el reporte general. Solicita actualizar el backend.' : e.status===403 ? 'No tienes acceso a los reportes de este proyecto.' : e.message;
            el.error.textContent=texto || 'No se pudo consultar el reporte.';el.error.hidden=false;
        }
        function render() {
            if(!activo)return;
            el.btnConsultar.disabled=ocupado || exportando || !proyecto?.value;
            el.btnExportar.disabled=ocupado || exportando || !datos || !(datos.paginacion_individuales.total+datos.paginacion_colectivos.total);
            el.btnAnterior.disabled=ocupado || exportando || pagina<=1;
            el.btnSiguiente.disabled=ocupado || exportando || !datos?.[`paginacion_${grupo}`].hay_mas;
            el.porPagina.disabled=ocupado || exportando;
            el.btnExportar.textContent=exportando?'Preparando Excel…':'Exportar Excel (.xlsx)';
            el.tbody.replaceChildren();el.resumen.replaceChildren();
            el.total.textContent=datos ? `${datos.paginacion_individuales.total} convenios individuales · ${datos.paginacion_colectivos.total} colectivos` : 'Selecciona un proyecto para consultar';
            el.pagina.textContent=`Página ${pagina} de ${Math.max(1,Math.ceil((datos?.[`paginacion_${grupo}`].total||0)/Number(el.porPagina.value||50)))} · ${grupo}`;
            selector.disabled=ocupado || exportando;
            el.busqueda.disabled=ocupado;
            const cabecera=grupo==='individuales'?individuales:colectivos;
            const head=document.getElementById('theadReportesConvenios');head.replaceChildren();const hr=document.createElement('tr');cabecera.forEach((v,i)=>{const th=document.createElement('th');th.scope='col';th.textContent=grupo==='colectivos'&&i>=6?v+(i<9?' · Asamblea':' · Convenio'):v;hr.append(th);});head.append(hr);
            const todas=datos ? (grupo==='individuales'?filasIndividuales(datos.individuales):filasColectivos(datos.colectivos)) : [];
            const termino=normalizar(el.busqueda.value).trim();
            const filas=todas.filter(f=>!termino||normalizar(f.join(' ')).includes(termino));
            if(!filas.length){const tr=el.tbody.insertRow(),td=tr.insertCell();td.colSpan=12;td.className='convenios-reportes-tabla-estado';td.textContent=ocupado?'Consultando reporte…':datos?termino?'No hay coincidencias en esta página.':`No hay convenios ${grupo} con este filtro. Puedes cambiar el tipo de vista abajo; el Excel incluye ambas hojas.`:'Elige un proyecto y consulta el reporte.';}
            filas.forEach(f=>{const tr=el.tbody.insertRow();f.forEach((v,i)=>{const td=tr.insertCell();td.textContent=v==null?'—':(grupo==='individuales'?i>=7&&i<=9:i>=6)?window.SSALFER_FORMAT.formatearFecha(v):String(v);});});
            if(datos){const avisos=[...new Set(datos[grupo].flatMap(c=>c.advertencias||[]))];if(avisos.length){const d=document.createElement('details'),s=document.createElement('summary');s.textContent='Observaciones de los convenios consultados';d.append(s);avisos.forEach(a=>{const p=document.createElement('p');p.textContent=observaciones[a] || `Observación adicional: ${String(a).toLowerCase().replaceAll('_',' ')}.`;d.append(p);});el.resumen.append(d);}}
        }
        async function consultar() {
            if(!activo || !proyecto?.value || exportando)return;
            const t=++token,id=proyecto.value,params={pagina,tamano_pagina:Number(el.porPagina.value)||50};if(entidad.value)params.id_entidad=entidad.value;
            ocupado=true;datos=null;limpiar();mensaje('El Excel incluye ambas hojas del estado seleccionado. La búsqueda solo filtra la página visible.');render();
            try{const r=await window.ReportesAPI.generalConvenios(id,params);if(!activo||t!==token)return;datos=validar(r,id);}
            catch(e){if(activo&&t===token)error(e);}
            finally{if(activo&&t===token){ocupado=false;render();}}
        }
        async function cambiarProyecto() {
            const t=++token,id=proyecto.value;datos=null;pagina=1;ocupado=Boolean(id);limpiar();entidad.replaceChildren(new Option('Todos los estados',''));entidad.disabled=true;render();
            if(!id)return;
            try{const r=await window.ReportesAPI.entidadesConvenios(id);if(!activo||t!==token)return;if(Number(r.id_proyecto)!==Number(id)||!Array.isArray(r.entidades))throw Error('No se pudieron comprobar los estados del proyecto.');r.entidades.forEach(e=>entidad.add(new Option(`${e.estado} (${e.individuales+e.colectivos})`,String(e.id_entidad))));entidad.disabled=false;await consultar();}
            catch(e){if(activo&&t===token){ocupado=false;error(e);render();}}
        }
        async function exportar() {
            if(!activo || el.btnExportar.disabled)return;
            const t=token,id=proyecto.value,estado=entidad.value,contexto=`${proyecto.selectedOptions[0].textContent} · ${entidad.selectedOptions[0].textContent}`;
            exportando=true;proyecto.disabled=entidad.disabled=true;limpiar();render();
            try{
                const r=validar(await window.ReportesAPI.generalConvenios(id,estado?{id_entidad:estado}:{},true),id,true);
                if(!activo||t!==token)return;
                const wb=libro(r,contexto),buffer=window.XLSX.write(wb,{bookType:'xlsx',type:'array',compression:true});
                const url=URL.createObjectURL(new Blob([buffer],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})),a=document.createElement('a');a.href=url;a.download=`Reporte-general-convenios-proyecto-${id}-${estado||'todos'}-${new Date().toISOString().slice(0,10)}.xlsx`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
                mensaje('Excel generado con ambas hojas y todos los registros del filtro.');
            }catch(e){if(activo&&t===token)error(e);}
            finally{exportando=false;if(activo){proyecto.disabled=false;entidad.disabled=ocupado||!proyecto.value;render();}}
        }
        return {
            activar(proyectos,id){activo=true;++token;datos=null;pagina=1;ocupado=false;el.filtros.replaceChildren();
                for(const [nombre,label] of [['proyecto','Proyecto'],['entidad','Estado']]){const l=document.createElement('label');l.className='convenios-reportes-campo';l.textContent=label;const s=document.createElement('select');s.id=`generalConvenio_${nombre}`;l.append(s);el.filtros.append(l);if(nombre==='proyecto')proyecto=s;else entidad=s;}
                proyecto.add(new Option('Selecciona un proyecto',''));proyectos.forEach((n,k)=>proyecto.add(new Option(n,String(k))));if(proyectos.has(Number(id)))proyecto.value=String(id);
                proyecto.onchange=cambiarProyecto;entidad.onchange=()=>{pagina=1;consultar();};
                el.busqueda.value='';el.busqueda.disabled=false;el.busqueda.placeholder='Buscar en esta página';el.btnConsultar.hidden=true;
                selector=document.createElement('select');selector.id='generalConvenio_vista';selector.setAttribute('aria-label','Tipo de convenio en la vista previa');selector.add(new Option('Individuales','individuales'));selector.add(new Option('Colectivos','colectivos'));selector.value=grupo;el.pagina.after(selector);selector.onchange=()=>{grupo=selector.value;pagina=1;el.busqueda.value='';consultar();};el.btnExportar.title='Incluye ambas hojas y todas las páginas del estado seleccionado';
                mensaje('El Excel incluye ambas hojas del estado seleccionado. La búsqueda solo filtra la página visible.');cambiarProyecto();
            },
            desactivar(){activo=false;++token;selector?.remove();el.btnConsultar.hidden=false;el.busqueda.placeholder='Proyecto, concepto, convenio, efecto…';},render,consultar,exportar,
            pagina(salto){if(ocupado || exportando)return;pagina=Math.max(1,pagina+salto);consultar();},
            tamano(){pagina=1;consultar();},limpiar(){if(exportando)return;entidad.value='';el.busqueda.value='';pagina=1;consultar();}
        };
    }
    window.SSALFER_REPORTE_GENERAL={crear,libro,validar,filasIndividuales,filasColectivos,individuales,colectivos};
})();
