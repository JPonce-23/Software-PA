// Real mapa.js functions in a VM with DOM/API doubles. No browser/render timings.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'../..');
const normalizeSource = require('./helpers/source.cjs');
const original=normalizeSource(execFileSync('git',['show','0ce1743:frontend-ssalfer/js/mapa.js'],{cwd:root,encoding:'utf8'}));
const current=normalizeSource(fs.readFileSync(path.join(root,'frontend-ssalfer/js/mapa.js'),'utf8'));
const ids=['valorAsambleasRealizadas','valorConveniosIndividuales','valorConveniosColectivos','valorConveniosFirmados'];
const section=(source,start,end)=>source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)));
const metric=source=>section(source,'    async function metricasProyecto(','    const elementos =');
function dataset(size=74){
    let aid=0;
    const nuclei=Array.from({length:size},(_,i)=>({id_proyecto_nucleo:i+1}));
    const affects=new Map(nuclei.map((n,i)=>[n.id_proyecto_nucleo,
        Array.from({length:1+(i<18?1:0)},()=>({id_afectacion:++aid,activo:true}))]));
    const agreements=new Map([...affects.values()].flat().map(a=>[a.id_afectacion,[
        {id_convenio:1,ambito:'colectivo',activo:true,fecha_firma:'2026-01-02'},
        {id_convenio:2,ambito:'individual',activo:true,fecha_firma:null},
        {id_convenio:3,ambito:'individual',activo:false,fecha_firma:'2026-01-02'},
    ]]));
    const assemblies=new Map(nuclei.map((n,i)=>[n.id_proyecto_nucleo,[{id_asamblea:i+1,activo:true,
        convocatorias:[{activo:true,fecha_realizacion:null,id_resultado:null},
            {activo:i%2===0,fecha_realizacion:'2026-01-02',id_resultado:50}]}]]));
    return {nuclei,affects,agreements,assemblies};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function harness(source,{data=dataset(),fail=()=>false,hold=()=>null,catalogMissing=false}={}){
    const nodes=new Map(ids.map(id=>[id,{textContent:''}]));
    const calls=[],layers=[],errors=[];
    async function get(url){
        calls.push(url);const pending=hold(url);if(pending)await pending;
        if(fail(url))throw Error('Fallo parcial sintético');
        if(url==='/catalogos/operativos/resultado_convocatoria')return catalogMissing?[]:[{codigo:'celebrada',id_catalogo_opcion:50}];
        if(url.endsWith('/mapa/indicadores'))return {asambleas_realizadas:catalogMissing?null:Math.ceil(data.nuclei.length/2),
            convenios_individuales:0,convenios_colectivos:data.nuclei.length?1:0,convenios_firmados:data.nuclei.length?1:0};
        let m;
        if((m=url.match(/^\/proyecto-nucleo\/(\d+)\/asambleas$/)))return data.assemblies.get(+m[1])||[];
        if((m=url.match(/^\/proyecto-nucleo\/(\d+)\/afectaciones$/)))return data.affects.get(+m[1])||[];
        if((m=url.match(/^\/afectaciones\/(\d+)\/convenios$/)))return data.agreements.get(+m[1])||[];
        throw Error('Unexpected '+url);
    }
    const context=vm.createContext({window:{ClienteAPI:{get}},document:{getElementById:id=>nodes.get(id)},
        console:{error(){}},URLSearchParams,location:{search:''},idsMetricas:ids,
        tokenCarga:0,capaTemporal:null,mapaLeaflet:{},
        elementos:{selectorProyecto:{classList:{remove(){}}}},
        obtenerProyecto:id=>({id_proyecto:id}),nombreProyecto:p=>String(p.id_proyecto),
        limpiarMensajes(){},limpiarGeometrias(){layers.length=0},ocultarResumenProyecto(){},
        establecerProyectoActivo(){},actualizarUrl(){},mostrarCarga(){},ocultarCarga(){},
        mostrarResumenProyecto(){},mostrarInformativo(){},ajustarMapaAGeometrias(){},
        mostrarError:error=>errors.push(error),obtenerNucleosProyecto:async()=>{
            if(fail('nuclei'))throw Error('Resumen no disponible');return data.nuclei;
        },
        cargarMapaDeProyecto:async(p,token)=>{
            const pending=hold('geo'+p.id_proyecto);if(pending)await pending;
            if(fail('geo'+p.id_proyecto))throw Error('GeoJSON no disponible');
            if(token===context.tokenCarga)layers.push(p.id_proyecto);
            return {agregadas:1,geojson:{type:'FeatureCollection',features:[]}};
        }});
    vm.runInContext(metric(source),context);
    vm.runInContext(section(source,'    async function cargarProyecto(','    /* =====================================================\n       SELECTOR DE PROYECTOS'),context);
    return {context,calls,layers,errors,nodes,values:()=>ids.map(id=>nodes.get(id).textContent),
        run:()=>source===original?context.metricasProyecto(1,data.nuclei,()=>true):context.metricasProyecto(1,()=>true)};
}

test('baseline immutable 0ce1743: 74 nuclei and 92 affects require 241 indicator calls',async()=>{
    const h=harness(original);await h.run();assert.equal(h.calls.length,241);assert.deepEqual(h.values(),['37','0','1','1']);
    if(process.env.F05_EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.F05_EVIDENCE_DIR,'frontend-baseline.json'),
        JSON.stringify({mode:'Node VM; no browser',indicator_requests:h.calls.length,values:h.values()},null,2));
});
if(process.env.F05_BASELINE_ONLY!=='1'){
test('equivalent indicators including empty, 74, 105 and 205 nuclei; one request',async()=>{
    const results=[];
    for(const size of [0,74,105,205]){
        const data=dataset(size),before=harness(original,{data}),after=harness(current,{data});
        await before.run();await after.run();assert.deepEqual(after.values(),before.values());assert.equal(after.calls.length,1);
        results.push({nuclei:size,original_requests:before.calls.length,optimized_requests:after.calls.length,values:after.values()});
    }
    if(process.env.F05_EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.F05_EVIDENCE_DIR,'frontend-comparison.json'),JSON.stringify(results,null,2));
});
test('missing celebrated result keeps assembly unavailable and conventions available',async()=>{
    for(const source of [original,current]){const h=harness(source,{catalogMissing:true});await h.run();assert.deepEqual(h.values(),['No disponible','0','1','1']);}
});
test('failed indicator response never blocks geographic layers or shows false zeros',async()=>{
    const h=harness(current,{fail:url=>url.endsWith('/indicadores')});await h.context.cargarProyecto(1);await tick();
    assert.deepEqual(h.layers,[1]);assert.deepEqual(h.values(),ids.map(()=> 'No disponible'));
});
test('slow indicators do not delay layers or completion of project loading',async()=>{
    let release;const gate=new Promise(resolve=>release=resolve);
    const h=harness(current,{hold:url=>url.endsWith('/indicadores')?gate:null});
    await h.context.cargarProyecto(1);assert.deepEqual(h.layers,[1]);assert.deepEqual(h.values(),ids.map(()=> 'Consultando…'));
    release();await tick();assert.deepEqual(h.values(),['37','0','1','1']);
});
test('indicators start before slow GeoJSON and survive a partial geometry failure',async()=>{
    let release;const gate=new Promise(resolve=>release=resolve);
    const h=harness(current,{hold:url=>url==='geo1'?gate:null,fail:url=>url==='geo1'});
    const loading=h.context.cargarProyecto(1);await tick();assert.deepEqual(h.values(),['37','0','1','1']);
    release();await loading;assert.deepEqual(h.layers,[]);assert.equal(h.errors.length,1);
});
test('fast project changes discard both stale success and stale indicator errors',async()=>{
    for(const failed of [false,true]){
        let release;const gate=new Promise(resolve=>release=resolve);
        const h=harness(current,{hold:url=>url.includes('/1/')?gate:null,fail:url=>failed&&url.includes('/1/')});
        await h.context.cargarProyecto(1);await h.context.cargarProyecto(2);await tick();
        const expected=h.values();assert.deepEqual(h.layers,[2]);release();await tick();assert.deepEqual(h.values(),expected);
    }
});
test('administrative request failure leaves geometry and independent indicators available',async()=>{
    const h=harness(current,{fail:url=>url==='nuclei'});await h.context.cargarProyecto(1);await tick();
    assert.deepEqual(h.layers,[1]);assert.deepEqual(h.values(),['37','0','1','1']);assert.equal(h.errors.length,1);
});
test('malformed aggregate response is unavailable rather than silently zero',async()=>{
    const h=harness(current);h.context.window.ClienteAPI.get=async()=>({asambleas_realizadas:0});
    await h.run();assert.deepEqual(h.values(),ids.map(()=> 'No disponible'));
});
test('real geographic loader keeps coordinates/properties and discards stale project features',async()=>{
    const h=harness(current),inserted=[];let release;
    const gate=new Promise(resolve=>release=resolve);
    const feature={type:'Feature',id:'nucleo_agrario:1',properties:{tipo:'nucleo_agrario',superficie_afectada_ha:null},
        geometry:{type:'MultiPolygon',coordinates:[[[[-99.123456789,20.123456789],[-99,20],[-98,20],[-99.123456789,20.123456789]]]]}};
    h.context.obtenerMapaProyecto=async pid=>{if(pid===1)await gate;return {type:'FeatureCollection',features:[feature]}};
    h.context.agregarFeature=(f,p)=>{inserted.push({feature:f,project:p.id_proyecto});return true};
    vm.runInContext(section(current,'    async function cargarMapaDeProyecto(','    /* =====================================================\n       RESUMEN DEL PROYECTO'),h.context);
    h.context.tokenCarga=1;const stale=h.context.cargarMapaDeProyecto({id_proyecto:1},1);
    h.context.tokenCarga=2;const fresh=await h.context.cargarMapaDeProyecto({id_proyecto:2},2);
    release();await stale;assert.equal(inserted.length,1);assert.equal(inserted[0].project,2);
    assert.equal(inserted[0].feature,feature);assert.equal(fresh.geojson.features[0],feature);
});
test('GeoJSON loading/render function and administrative pagination stay byte identical',()=>{
    for(const [start,end]of [
        ['    async function cargarMapaDeProyecto(','    /* =====================================================\n       RESUMEN DEL PROYECTO'],
        ['    async function obtenerNucleosProyecto(','    async function obtenerParcelasProyectoNucleo('],
        ['    function mostrarResumenProyecto(','    async function mostrarDetalleFeature('],
    ])assert.equal(section(current,start,end),section(original,start,end));
});
}
