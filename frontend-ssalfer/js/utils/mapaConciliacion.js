/* Consulta de conciliación por proyecto. No confirma ni cambia versiones. */
(() => {
    'use strict';
    const api = () => window.GeoespacialAPI;
    const e = value => { const node=document.createElement('span');node.textContent=String(value??'');return node.innerHTML; };
    const nombre = f => Object.entries(f.atributos_originales || {})
        .filter(([k,v]) => /nombre|nucl|n__cleo|parcel|municip|estado|entidad/i.test(k) && v != null && v !== '')
        .map(([,v]) => v).join(' · ') || `Elemento ${Number(f.indice_feature)+1}`;
    async function todas(consulta, vigente) {
        const rows = [];
        for (let skip=0; vigente(); skip+=200) {
            const p = await consulta({skip,limit:200});
            if (!vigente()) return [];
            rows.push(...p.items);
            if (api().fin(p,skip,200)) return rows;
        }
        return [];
    }
    function detalle(proyecto, vigente, geojson) {
        if(!vigente())return;
        const host=document.getElementById('mapaDetalleConciliacion');host.hidden=false;
        if(!geojson || !Array.isArray(geojson.features)){host.innerHTML='<h3>Resumen cartográfico</h3><p role="status">No se pudo consultar la cartografía. Vuelve a seleccionar el proyecto para reintentar.</p>';return;}
        const ids=tipo=>new Set(geojson.features.filter(f=>f.properties?.tipo===tipo && f.geometry && f.properties?.id!=null).map(f=>String(f.properties.id))).size;
        host.innerHTML=`<h3>Resumen cartográfico</h3><dl class="mapa-totales-cartografia"><div><dt>Núcleos con geometría</dt><dd>${ids('nucleo_agrario')}</dd></div><div><dt>Parcelas con geometría</dt><dd>${ids('parcela')}</dd></div><div><dt>Derecho de vía</dt><dd>${ids('derecho_via_proyecto')?'Disponible':'Sin geometría'}</dd></div></dl><p>Geometrías confirmadas vigentes del proyecto. No suma cargas repetidas ni previsualizaciones.</p>`;
    }
    async function coincidencias(iid, proyecto, vigente, lectura={}) {
        const r=await api().obtener(iid,lectura);
        if(!vigente())return null;
        if(Number(r.id_proyecto)!==Number(proyecto))throw Error('La carga pertenece a otro proyecto.');
        if(!['nucleo_agrario_gpkg','parcela_gpkg','nucleo_agrario','parcela'].includes(r.tipo_objetivo))throw Error('Esta vista está disponible para núcleos y parcelas.');
        const rows=await todas(p=>api().paginaElementos(iid,p,lectura),vigente);
        const elegidos=rows.filter(f=>['candidato','coincidencia_exacta','confirmado'].includes(f.estado_conciliacion)&&f.estado!=='error');
        const features=[];let cursor=0,fallidos=0;
        await Promise.all(Array.from({length:Math.min(4,elegidos.length)},async()=>{
            while(vigente()&&cursor<elegidos.length){
                const f=elegidos[cursor++];
                try { const geo=await api().geometria(iid,f.id_importacion_feature,lectura);if(geo.geometry)features.push({...geo,properties:{...geo.properties,nombre:nombre(f),estado:f.estado_conciliacion}});else fallidos++; }
                catch(err){fallidos++;}
            }
        }));
        return vigente()?{inactiva:r.activo===false,geo:{type:'FeatureCollection',features},sin:rows.filter(f=>f.estado_conciliacion==='sin_coincidencia' && f.estado!=='error').length,ambiguos:rows.filter(f=>f.estado_conciliacion==='ambiguo').length,fallidos}:null;
    }
    window.SSALFER_MAPA_CONCILIACION={detalle,coincidencias};
})();
