// Execute the real map preview branch. API/DOM doubles; no browser navigation.
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.resolve(__dirname,'../../frontend-ssalfer/js/mapa.js'),'utf8');
const start=source.indexOf('        const vista = new URLSearchParams(location.search)');
const end=source.indexOf('        /*\n         * Resumen administrativo.',start);
assert(start>=0 && end>start);
const preview=source.slice(start,end);

async function run(role,search,session){
    const calls=[],errors=[],messages=[];
    const node=()=>({append(){},className:'',textContent:'',id:''});
    const layer={addTo(){return this;},bindTooltip(){return this;},getBounds(){return {isValid:()=>false};}};
    const context=vm.createContext({URLSearchParams,location:{search},Number,
        proyecto:{id_proyecto:7},cargaActual:1,tokenCarga:1,
        resultadoMapa:{status:'fulfilled',value:{geojson:{type:'FeatureCollection',features:[]}}},
        errores:errors,capaTemporal:null,mapaLeaflet:{},
        document:{createElement:node,querySelector:()=>({prepend:n=>messages.push(n.textContent)})},
        window:{SSALFER_SESION_LISTA:session||Promise.resolve({user:{rol:role}}),
            SSALFER_MAPA_CONCILIACION:{detalle:()=>calls.push('public-summary'),coincidencias:async(...args)=>{
                calls.push(['preview-batch',...args.filter(a=>typeof a!=='function')]);
                return {inactiva:true,geo:{features:[]},sin:0,ambiguos:0};
            }},
            GeoespacialAPI:{obtener:async(...args)=>{calls.push(['import',...args]);return {id_proyecto:7,activo:false};},
                geometria:async(...args)=>{calls.push(['raw-geometry',...args]);return {geometry:{type:'Polygon',coordinates:[]}};}},
            L:{geoJSON:()=>layer}},
    });
    const pending=vm.runInContext(`(async()=>{${preview}})()`,context);
    return {context,calls,errors,messages,pending};
}

test('published map summary works for all roles without consulting internal GIS endpoints',async()=>{
    for(const role of ['admin','geografo','operador','visualizador']){
        const r=await run(role,'?id_proyecto=7');await r.pending;
        assert.deepEqual(r.calls,['public-summary']);assert.deepEqual(r.errors,[]);
    }
});

test('feature and coincidence previews never query GIS management for operator or viewer',async()=>{
    for(const role of ['operador','visualizador'])for(const suffix of ['&id_feature=11','&vista=coincidencias']){
        const r=await run(role,'?id_proyecto=7&id_importacion=9&incluir_inactivas=true'+suffix);await r.pending;
        assert.deepEqual(r.calls,['public-summary']);
        assert.equal(r.errors.length,1);assert.match(r.errors[0],/mapa vigente sigue disponible/);
    }
});

test('administrator and geographer retain explicit historical import previews',async()=>{
    for(const role of ['admin','geografo']){
        const r=await run(role,'?id_proyecto=7&id_importacion=9&id_feature=11&incluir_inactivas=true');await r.pending;
        assert.deepEqual(r.calls.map(c=>Array.isArray(c)?c[0]:c),['public-summary','import','raw-geometry']);
        assert.equal(r.calls[1][2].incluir_inactivas,true);
        assert.equal(r.calls[2][3].incluir_inactivas,true);
        assert.match(r.messages[0],/Geometría histórica/);assert.deepEqual(r.errors,[]);
        const batch=await run(role,'?id_proyecto=7&id_importacion=9&vista=coincidencias&incluir_inactivas=true');await batch.pending;
        assert.deepEqual(batch.calls.map(c=>Array.isArray(c)?c[0]:c),['public-summary','preview-batch']);
        assert.equal(batch.calls[1][3].incluir_inactivas,true);
    }
});

test('a project switch while session validation is pending discards the old preview',async()=>{
    let resolve;
    const session=new Promise(r=>{resolve=r;});
    const r=await run('geografo','?id_proyecto=7&id_importacion=9&id_feature=11',session);
    r.context.tokenCarga=2;resolve({user:{rol:'geografo'}});await r.pending;
    assert.deepEqual(r.calls,[]);assert.deepEqual(r.errors,[]);
});
