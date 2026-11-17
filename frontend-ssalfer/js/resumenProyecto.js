/* Percentages always refer to the explicitly named universe, never to a chart axis. */
document.addEventListener('DOMContentLoaded', async () => {
    'use strict';
    if (window.SSALFER_SESION_LISTA && !await window.SSALFER_SESION_LISTA) return;
    const $ = id => document.getElementById(id);
    const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const number = value => value == null ? 'Sin dato' : new Intl.NumberFormat('es-MX', {maximumFractionDigits: 4}).format(value);
    const money = value => value == null ? 'Sin dato' : new Intl.NumberFormat('es-MX', {style:'currency', currency:'MXN'}).format(value);
    let revision = 0;
    function bar(label, value, total, color = '') {
        const percent = value != null && total > 0 ? value / total * 100 : null;
        return `<div class="rp-barra ${color}"><div><span>${escape(label)}</span><strong>${number(value)} <small>· ${percent == null ? 'Sin porcentaje' : number(Math.round(percent * 10) / 10) + ' %'}</small></strong></div><div class="rp-pista" aria-hidden="true"><span style="width:${percent == null ? 0 : Math.min(100,Math.max(0,percent))}%"></span></div></div>`;
    }
    function activity(title, key, label, data) {
        const total = data[key + '_total'];
        return `<article class="tarjeta rp-grafica"><h2>${title}</h2>${bar('Registradas',total,total)}${bar(label,data[key + '_realizadas'],total,'rp-verde')}<p>Porcentaje del total de ${title.toLowerCase()} registradas.${total === 0 ? ' Aún no hay registros.' : ''}</p></article>`;
    }
    function render(d) {
        const totalCop = d.individual_total + d.colectivo_total;
        $('rpContenido').innerHTML = `<section class="rp-indicadores" aria-label="Totales del proyecto">
            ${[['Núcleos vinculados',number(d.nucleos)],['Parcelas',number(d.parcelas)],['Afectaciones',number(d.afectaciones)],['Superficie afectada',d.superficie_ha == null ? 'Sin dato' : number(d.superficie_ha) + ' ha']].map(([title,value]) => `<article class="tarjeta"><h2>${title}</h2><strong>${value}</strong></article>`).join('')}</section>
            <p class="rp-nota">Superficie registrada: ${number(d.sin_superficie)} afectaciones con superficie pendiente o incompleta.</p>
            <section class="rp-grid" aria-label="Avance de actividades">
            ${activity('Convocatorias','convocatorias','Con fecha de realización',d)}
            ${activity('Sensibilizaciones','sensibilizacion','Realizadas',d)}
            ${activity('Caminamientos','caminamiento','Realizados',d)}
            ${activity('Asambleas','asambleas','Celebradas',d)}</section>
            <section class="tarjeta rp-seccion"><h2>COP y seguimiento FIFONAFE</h2><p>${number(totalCop)} COP registrados en el proyecto. Cada porcentaje se calcula sobre el total de su tipo.</p><div class="rp-grid">
            ${['individual','colectivo'].map(kind => `<article class="rp-grafica"><h3>${kind === 'individual' ? 'Individuales' : 'Colectivos'}</h3>${bar('Total',d[kind+'_total'],d[kind+'_total'])}${bar('FIFONAFE completo',d[kind+'_completos'],d[kind+'_total'],'rp-verde')}${bar('Con conflicto',d[kind+'_conflicto'],d[kind+'_total'],'rp-rojo')}${bar('Sin trámite vinculado',d[kind+'_sin_tramite'],d[kind+'_total'],'rp-gris')}<p>Conflicto sin información completa: ${number(d[kind+'_conflicto_sin_dato'])}.</p></article>`).join('')}</div>
            <details><summary>Cómo se cuenta el avance</summary><p>Un COP tiene FIFONAFE completo cuando cuenta con trámites vinculados a sus afectaciones y todos están registrados como completos. Tener firma no equivale a terminar FIFONAFE. El conflicto se cuenta por separado: puede existir aunque el trámite esté completo. Estas barras no se suman entre sí.</p></details></section>
            <section class="tarjeta rp-seccion"><h2>Montos declarados de los COP</h2><p>Conceptos 90 % y 100 % por separado. No representan un saldo pendiente de pago.</p><div class="rp-grid">
            ${['90','100'].map(concept => {
                const values = ['individual','colectivo'].map(k => d[k+'_monto_'+concept]);
                const total = values.reduce((sum,v) => sum + Number(v || 0), 0);
                return `<article class="rp-grafica"><h3>Monto ${concept} %</h3>${['individual','colectivo'].map((kind,i) => `<div class="rp-monto"><strong>${kind === 'individual' ? 'Individuales' : 'Colectivos'}: ${money(values[i])}</strong>${bar('Participación del monto',values[i],total)}<small>${number(d[kind+'_con_dato_'+concept])} de ${number(d[kind+'_total'])} COP con monto registrado.</small></div>`).join('')}<p>Porcentaje del monto declarado disponible para este concepto.</p></article>`;
            }).join('')}</div>
            <div class="rp-pagos"><h3>Pagos registrados por afectación</h3><strong>${d.pagos_registros === 0 ? 'Sin pagos registrados' : money(d.pagos_total)}</strong><p>${number(d.pagos_registros)} pagos registrados. No se restan de los montos de COP: pertenecen a afectaciones y no existe una relación directa de cada pago con un COP.</p></div></section>
            <details class="rp-metodo"><summary>Qué información incluye este resumen</summary><p>Registros activos de los núcleos vinculados al proyecto. Actividades realizadas: tienen fecha de realización. Asambleas celebradas: tienen convocatoria activa con fecha de realización y resultado «Celebrada»; cada asamblea se cuenta una sola vez. Los porcentajes reflejan el avance sobre lo registrado, no sobre una meta institucional. «Sin dato» indica información no disponible; un cero indica que la consulta no encontró registros.</p></details>`;
    }
    async function load() {
        const current = ++revision, id = $('rpProyecto').value;
        $('rpContenido').replaceChildren(); $('rpError').hidden = true;
        $('rpContenido').setAttribute('aria-busy', String(Boolean(id)));
        for (const [key,page,param] of [['rpFicha','fichaProyecto','id'],['rpSeguimiento','seguimientoFifonafe','id_proyecto']]) {
            $(key).hidden = !id; if(id) $(key).href = `/pages/${page}.html?${param}=${encodeURIComponent(id)}`;
        }
        $('rpEstado').textContent = id ? 'Consultando el resumen del proyecto…' : 'Selecciona un proyecto para ver su resumen.';
        if(!id) return;
        try {
            const data = await window.ReportesAPI.obtenerResumenProyecto(id);
            if(current !== revision) return;
            render(data);
            $('rpEstado').textContent = `${$('rpProyecto').selectedOptions[0].textContent} · Consultado a las ${new Date().toLocaleTimeString('es-MX')}`;
        } catch(err) {
            if(current !== revision) return;
            $('rpError').textContent = err.mensaje || err.message || 'No fue posible consultar el resumen.';
            $('rpError').hidden = false; $('rpEstado').textContent = 'No se muestran datos incompletos. Usa Actualizar para reintentar.';
        } finally { if(current === revision) $('rpContenido').setAttribute('aria-busy','false'); }
    }
    $('rpProyecto').addEventListener('change', () => {
        const url = new URL(location.href);
        if($('rpProyecto').value) url.searchParams.set('id_proyecto',$('rpProyecto').value);
        else url.searchParams.delete('id_proyecto');
        history.replaceState(null,'',url); load();
    });
    $('rpActualizar').addEventListener('click', load);
    try {
        if(!await window.AuthAPI.requerirSesion()) return;
        const projects = await window.ProyectosAPI.listar();
        projects.forEach(p => $('rpProyecto').add(new Option(p.nombre_proyecto,p.id_proyecto)));
        const requested = new URLSearchParams(location.search).get('id_proyecto');
        if(requested) $('rpProyecto').value = requested;
        await load();
    } catch(err) { $('rpError').textContent = err.mensaje || err.message; $('rpError').hidden = false; }
});
