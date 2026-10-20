// F06: real public report functions, DOM/API doubles; no browser/HAR measurements.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'../..');
const original=file=>execFileSync('git',['show',`41d4b68:frontend-ssalfer/js/${file}`],{cwd:root,encoding:'utf8'});
const current=file=>fs.readFileSync(path.join(root,'frontend-ssalfer/js',file),'utf8');
const section=(s,start,end)=>{const i=s.indexOf(start),j=s.indexOf(end,i);assert.ok(i>=0&&j>i,start);return s.slice(i,j)};
const tick=()=>new Promise(r=>setImmediate(r));
const clone=x=>JSON.parse(JSON.stringify(x));
function dataset(size=74){
    let aid=0;
    const nuclei=Array.from({length:size},(_,i)=>({id_proyecto_nucleo:i+1,nombre_nucleo:`=Núcleo <${i+1}>`}));
    const affects=new Map(),agreements=new Map(),assemblies=new Map(),byC=new Map();
    for(const [i,n]of nuclei.entries()){
        const list=Array.from({length:1+(i<18?1:0)},()=>({id_afectacion:++aid,id_proyecto_nucleo:i+1,tipo_afectacion:'colectivo',situacion:i%2?'En trámite':null,superficie_afectada_ha:i%3?'1.1234567':null}));
        affects.set(i+1,list);
        const c={id_convenio:i+1,id_proyecto_nucleo:i+1,tipo_convenio:i%4?'cop_original':null,consecutivo:i+1,ambito:'colectivo',descripcion_instrumento:i%4?null:'Otro <documento>',fecha_firma:i%2?'2026-02-03':null};
        byC.set(c.id_convenio,c);for(const a of list)agreements.set(a.id_afectacion,[c]);
        assemblies.set(i+1,[{id_asamblea:i+1,id_proyecto_nucleo:i+1,proposito:i%3?'Anuencia <prueba>':null,convocatorias:[]}]);
    }
    const report=nuclei.flatMap(n=>['tuc','camino'].map((destino,j)=>({id_proyecto:1,id_proyecto_nucleo:n.id_proyecto_nucleo,id_convenio:n.id_proyecto_nucleo,id_asamblea:n.id_proyecto_nucleo,tipo_convenio:byC.get(n.id_proyecto_nucleo).tipo_convenio,tipo_cop_operativo:'ORIGEN',destino_superficie:destino,superficie_ha:j?'0.0000001':null,superficie_declarada_ha:'1.1234567',monto_declarado:'123456.78',fecha_firma:byC.get(n.id_proyecto_nucleo).fecha_firma,anio:n.id_proyecto_nucleo%2?null:2026,mes:n.id_proyecto_nucleo%2?null:2,trimestre:n.id_proyecto_nucleo%2?null:1})));
    const values=[...byC.values()].flatMap(c=>['monto_90_declarado','superficie_declarada'].map(concepto=>({id_proyecto:1,id_convenio:c.id_convenio,tipo_convenio:c.tipo_convenio,concepto,valor_declarado:concepto==='superficie_declarada'?null:'123456.78',fecha_instrumento_reportada:null,firma_acreditada:null})));
    return {nuclei,affects,agreements,assemblies,byC,report,values};
}
function setup(reference=false,{data=dataset(),fail=()=>false,hold=()=>null}={}){
    let blob,active=0,maxActive=0;const calls=[],errors=[],nodes=new Map(),listeners=new Map();
    class Element{
        constructor(){this.innerHTML='';this.textContent='';this.disabled=false;this.hidden=false;this.children=[];this.events=new Map();this.options=[];this._value='';}
        addEventListener(name,fn){this.events.set(name,fn)}
        async emit(name,event={}){return this.events.get(name)?.({preventDefault(){},target:this,...event})}
        setAttribute(){}removeAttribute(){}appendChild(el){this.children.push(el)}remove(){}click(){}
        replaceChildren(...children){this.children=children;this.options=children;this._value=String(children[0]?.value||'');this.innerHTML='';}
        add(option){this.options.push(option)}
        get value(){return this._value}set value(v){this._value=String(v)}
    }
    const fields=new Map(['id_proyecto','id_proyecto_nucleo','id_convenio','id_asamblea','tipo_convenio','tipo_cop_operativo','destino_superficie','anio','mes','trimestre'].map(n=>[n,new Element()]));
    const form=new Element();form.elements={namedItem:n=>fields.get(n)};
    const out=new Element(),button=new Element(),notice=new Element(),link=new Element(),rootEl=new Element();
    rootEl.querySelector=selector=>({'form':form,'[data-resultados]':out,'[data-exportar]':button,'[data-sin-fecha]':notice,'[data-enlace-fecha]':link}[selector]);
    const document={title:'',body:new Element(),getElementById:id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id)},createElement:()=>new Element(),addEventListener:(name,fn)=>listeners.set(name,fn)};
    async function get(url){
        calls.push(url);active++;maxActive=Math.max(maxActive,active);
        try{
            const pending=hold(url);if(pending)await pending;if(fail(url))throw Error('Fallo parcial sintético');
            const u=new URL(url,'http://fixture.invalid'),p=u.searchParams;let m;
            if(u.pathname==='/proyectos')return [{id_proyecto:1,nombre_proyecto:'Proyecto <uno>'}];
            if(u.pathname==='/proyectos/1')return {id_proyecto:1,nombre_proyecto:'Proyecto <uno>'};
            if(u.pathname==='/proyectos/1/nucleos')return clone(data.nuclei.slice(0,100));
            if(u.pathname==='/reportes/convenios/colectivos-destino')return clone(data.report.filter(row=>[...p].every(([key,v])=>String(row[key])===v)));
            if(u.pathname==='/reportes/convenios/valores-declarados')return clone(data.values);
            if(u.pathname==='/dashboard/kpi')return [{id_proyecto:1,indicador:'convenios_colectivos',anio:2026,programado:2,realizado:1,monto:null},{id_proyecto:2,indicador:'pagos',programado:100,monto:'99.99'}];
            if(['/reportes/avance-periodo','/reportes/convenios/cobertura-impactos','/reportes/fifonafe/cobertura'].includes(u.pathname))return [];
            if((m=u.pathname.match(/^\/proyecto-nucleo\/(\d+)$/)))return clone(data.nuclei.find(n=>n.id_proyecto_nucleo===+m[1]));
            if((m=u.pathname.match(/^\/proyecto-nucleo\/(\d+)\/afectaciones$/)))return clone(data.affects.get(+m[1])||[]);
            if((m=u.pathname.match(/^\/proyecto-nucleo\/(\d+)\/asambleas$/)))return clone(data.assemblies.get(+m[1])||[]);
            if((m=u.pathname.match(/^\/afectaciones\/(\d+)\/convenios$/)))return clone(data.agreements.get(+m[1])||[]);
            if((m=u.pathname.match(/^\/convenios\/(\d+)$/))){const c=data.byC.get(+m[1]);if(!c)throw Error('404');return clone(c)}
            if(u.pathname==='/reportes/referencias'){
                const ids=key=>p.getAll(key).map(Number),ns=new Set(ids('id_proyecto_nucleo'));
                return clone({nucleos:data.nuclei.filter(n=>ns.has(n.id_proyecto_nucleo)),afectaciones:[...data.affects.values()].flat().filter(a=>ids('id_afectacion').includes(a.id_afectacion)||(p.get('incluir_afectaciones')==='true'&&ns.has(a.id_proyecto_nucleo))),convenios:ids('id_convenio').map(id=>data.byC.get(id)).filter(Boolean)});
            }
            if(u.pathname==='/reportes/referencias-contexto'){
                const ns=new Set(p.getAll('id_proyecto_nucleo').map(Number)),convenios=new Map();
                for(const a of [...data.affects.values()].flat().filter(a=>ns.has(a.id_proyecto_nucleo)))for(const c of data.agreements.get(a.id_afectacion)||[])convenios.set(c.id_convenio,{item:c,id_afectacion:a.id_afectacion});
                return clone({nucleos:data.nuclei.filter(n=>ns.has(n.id_proyecto_nucleo)),afectaciones:[...data.affects.values()].flat().filter(a=>ns.has(a.id_proyecto_nucleo)),convenios:[...convenios.values()],asambleas:[...data.assemblies.values()].flat().filter(a=>ns.has(a.id_proyecto_nucleo))});
            }
            throw Error('Unexpected GET '+url);
        }finally{active--}
    }
    class URLDouble extends URL{}URLDouble.createObjectURL=value=>{blob=value;return 'blob:fixture'};URLDouble.revokeObjectURL=()=>{};
    const escape=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
    const window={location:{search:'?id_proyecto=1'},ClienteAPI:{get,API_BASE_URL:'/api',mostrarErrorAPI:e=>errors.push(e.message)},SSALFER_UI:{escaparHTML:escape,toast:message=>errors.push(message)},
        ProyectosAPI:{listar:()=>get('/proyectos'),obtener:id=>get('/proyectos/'+id)},NucleosAPI:{listarPorProyecto:id=>get(`/proyectos/${id}/nucleos`),obtenerProyectoNucleo:id=>get(`/proyecto-nucleo/${id}`)},AfectacionesAPI:{listarPorProyectoNucleo:id=>get(`/proyecto-nucleo/${id}/afectaciones`)},AsambleasAPI:{listarPorProyectoNucleo:id=>get(`/proyecto-nucleo/${id}/asambleas`)},ConveniosAPI:{listarPorAfectacion:id=>get(`/afectaciones/${id}/convenios`),obtener:id=>get(`/convenios/${id}`)}};
    const context=vm.createContext({window,document,location:{pathname:'/pages/reportesColectivos.html'},URL:URLDouble,URLSearchParams,Blob,console,Option:class{constructor(text,value){this.text=String(text);this.value=String(value)}},FormData:class{constructor(){return [...fields].map(([key,el])=>[key,el.value])}},setTimeout(){},clearTimeout(){}});
    const source=reference?original:current;
    for(const file of ['api/reportes.js','utils/formatters.js','utils/gestion.js','utils/periodos.js','utils/contexto.js'])vm.runInContext(source(file),context,{filename:file});
    return {context,window,document,calls,errors,nodes,fields,form,out,button,source,rootEl,maxActive:()=>maxActive,blob:()=>blob,
        async collective(nucleus=''){vm.runInContext(source('utils/reporteColectivo.js'),context);await window.SSALFER_REPORTE_COLECTIVO.montar(rootEl,1,nucleus);},
        async finance(){vm.runInContext(source('estadoFinanciero.js'),context);await listeners.get('DOMContentLoaded')();await tick();},
        references(){const s=source('reportesConvenios.js');vm.runInContext(section(s,'    let revisionFiltros','    /* =====================================================\n                        ESTADO'),context);vm.runInContext('globalThis.refs=referenciasReporte;',context);return context;},
        snapshot(){return {html:out.innerHTML,options:[...fields].map(([k,v])=>[k,v.options.map(o=>[o.value,o.text]),v.value]),notice:notice.textContent,link:link.innerHTML,disabled:button.disabled}}};
}
function save(name,value){if(process.env.F06_EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.F06_EVIDENCE_DIR,name),JSON.stringify(value,null,2))}
test('baseline original collective and financial HTTP calls before frontend changes',async()=>{
    const c=setup(true);await c.collective();await c.button.emit('click');
    const f=setup(true);await f.finance();
    assert.equal(c.calls.length,244);assert.equal(f.calls.length,81);
    save('frontend-baseline.json',{kind:'Node VM, API/DOM doubles; no HAR',collective_requests:c.calls.length,financial_requests:f.calls.length});
});
if(process.env.F06_BASELINE_ONLY!=='1'){
test('collective report: identical HTML, filters and CSV including nonadditive amounts and null types',async()=>{
    const result=[];
    for(const size of [0,3,74,105])for(const nucleus of ['',size?1:'']){
        const data=dataset(size),before=setup(true,{data}),after=setup(false,{data});await before.collective(nucleus);await after.collective(nucleus);
        assert.deepEqual(after.snapshot(),before.snapshot());
        if(!before.button.disabled){await before.button.emit('click');await after.button.emit('click');assert.equal(await after.blob().text(),await before.blob().text());}
        result.push({size,nucleus,original_requests:before.calls.length,optimized_requests:after.calls.length});
    }
    save('collective-comparison.json',result);
});
test('financial report: same cells, KPI scope, null values and CSV link; one initial values request',async()=>{
    const result=[];
    for(const size of [0,3,74,205]){
        const data=dataset(size),before=setup(true,{data}),after=setup(false,{data});await before.finance();await after.finance();
        const snapshot=h=>[...h.nodes].map(([key,node])=>[key,node.textContent,node.innerHTML,node.href]);
        assert.deepEqual(snapshot(after),snapshot(before));assert.equal(after.calls.filter(u=>u.startsWith('/reportes/convenios/valores-declarados')).length,1);
        assert.ok(after.calls.includes('/dashboard/kpi'));assert.ok(!after.calls.some(u=>u.startsWith('/dashboard/kpi?')));
        result.push({size,original_requests:before.calls.length,optimized_requests:after.calls.length});
    }
    save('financial-comparison.json',result);
});
test('legacy report labels equal with one missing reference, nulls, all affected nuclei and bounded batches',async()=>{
    const data=dataset(205),rows=data.report.map(r=>({...r,id_afectacion:data.affects.get(r.id_proyecto_nucleo)[0].id_afectacion}));rows.push({id_proyecto_nucleo:1,id_convenio:999999});
    const before=setup(true,{data}),after=setup(false,{data}),b=before.references(),a=after.references();
    await b.cargarReferenciasReporte(rows);await a.cargarReferenciasReporte(rows);
    // Normalize VM Array prototypes while preserving every ID and label.
    for(const kind of Object.keys(b.refs))assert.deepEqual(clone([...a.refs[kind]].sort()),clone([...b.refs[kind]].sort()));
    assert.equal(after.errors.length,before.errors.length);
    assert.ok(after.calls.length<before.calls.length);assert.ok(after.maxActive()<=3);
    save('legacy-reference-comparison.json',{original_requests:before.calls.length,optimized_requests:after.calls.length,max_concurrency:after.maxActive()});
});
test('stale reference responses cannot change maps or show old errors',async()=>{
    let release;const gate=new Promise(r=>release=r);const h=setup(false,{hold:()=>gate});const api=h.references();
    let valid=true;const pending=api.cargarReferenciasReporte([{id_convenio:1,id_proyecto_nucleo:1}],()=>valid);
    valid=false;release();await pending;assert.equal(api.refs.id_convenio.size,0);assert.equal(h.errors.length,0);
});
test('filter changes discard an old report response and allow a new query immediately',async()=>{
    const h=setup(false),api=h.references();let release;
    const gate=new Promise(r=>release=r),oldRows=[{id_convenio:1,id_proyecto_nucleo:1}],newRows=[{id_convenio:2,id_proyecto_nucleo:2}];
    Object.assign(api,{estado:{reporte:'valores',cargando:false,filas:[],pagina:1},reportes:{valores:{api:()=>gate}},
        el:{btnConsultar:{},btnExportar:{},busqueda:{}},limpiarMensajes(){},ponerCargando(){},obtenerParametros:()=>({id_proyecto:1}),
        renderTabla(){},mostrarInfo(){},mostrarError(error){throw error}});
    vm.runInContext(section(current('reportesConvenios.js'),'    async function consultarReporte(','    /* =====================================================\n                    CAMBIO DE PESTAÑA'),api);
    const old=api.consultarReporte();api.invalidarConsultaPendiente();
    assert.equal(api.estado.cargando,false);assert.equal(api.el.btnConsultar.disabled,false);
    api.reportes.valores.api=async()=>newRows;await api.consultarReporte();release(oldRows);await old;
    assert.deepEqual(clone(api.estado.filas),newRows);assert.equal(api.refs.id_convenio.has(1),false);assert.equal(api.refs.id_convenio.has(2),true);
    assert.ok(current('reportesConvenios.js').includes('if (estado.reporte !== "general") invalidarConsultaPendiente();'));
});
test('partial reference failure keeps report values and uses existing unavailable fallback',async()=>{
    const h=setup(false,{fail:u=>u.startsWith('/reportes/referencias?')});await h.finance();
    assert.ok(h.nodes.get('tablaValoresDeclarados').innerHTML.includes('Convenio · Referencia no disponible'));
    assert.ok(h.nodes.get('kpiMonto90').textContent);assert.equal(h.errors.length,0);
});
test('colectivo reference error keeps export disabled and shows an error; retry works',async()=>{
    let failed=true;const h=setup(false,{fail:u=>failed&&u.startsWith('/reportes/referencias-contexto?')});await h.collective();assert.equal(h.button.disabled,true);assert.ok(h.out.textContent);
    failed=false;await h.fields.get('id_proyecto').emit('change');assert.equal(h.button.disabled,false);
});
test('changing project while collective references are pending never restores old results',async()=>{
    let release;const gate=new Promise(r=>release=r);const h=setup(false,{hold:u=>u.startsWith('/reportes/referencias-contexto?')?gate:null});
    const mounting=h.collective();await tick();h.fields.get('id_proyecto').value='';await h.fields.get('id_proyecto').emit('change');
    release();await mounting;assert.equal(h.button.disabled,true);assert.equal(h.out.innerHTML,'');
    assert.equal(h.fields.get('id_proyecto_nucleo').options.length,1);
});
test('general report pagination, historical RAN logic and XLSX functions remain byte identical',()=>{
    assert.equal(current('reporteGeneralConvenios.js'),original('reporteGeneralConvenios.js'));
    for(const [start,end]of [['    function escaparCsv(','    /* =====================================================\n                    CATÁLOGOS BASE'],['    function valorVisual(','    function varianteBadge(']])assert.equal(section(current('reportesConvenios.js'),start,end),section(original('reportesConvenios.js'),start,end));
});
test('contextual filters keep options and order; one request replaces affectation traversal',async()=>{
    const before=setup(true),after=setup(false);
    for(const h of [before,after]){
        const api=h.references();h.document.getElementById('reporteConvenioFiltro_id_proyecto_nucleo').value='1';
        await api.cargarFiltrosContextuales('id_proyecto_nucleo');
    }
    for(const id of ['id_convenio','id_afectacion']){
        const opts=h=>h.document.getElementById('reporteConvenioFiltro_'+id).options.map(o=>[o.value,o.text]);
        assert.deepEqual(opts(after),opts(before));
    }
    assert.equal(before.calls.length,3);assert.equal(after.calls.length,1);
});
test('batch concurrency is capped at three under latency and shared values failures keep the existing errors',async()=>{
    const h=setup(false,{data:dataset(1000),hold:()=>new Promise(r=>setImmediate(r))});
    await h.window.ReportesAPI.obtenerReferenciasReporte({convenios:Array.from({length:1000},(_,i)=>i+1)});
    assert.equal(h.calls.length,10);assert.equal(h.maxActive(),3);
    const fail=u=>u.startsWith('/reportes/convenios/valores-declarados');
    const before=setup(true,{fail}),after=setup(false,{fail});await before.finance();await after.finance();
    assert.equal(after.nodes.get('tablaValoresDeclarados').innerHTML,before.nodes.get('tablaValoresDeclarados').innerHTML);
    assert.equal(after.errors.length,before.errors.length);
});
test('general XLSX round trip preserves both sheets, historical RAN dates, nulls and exact long decimals',()=>{
    const outputs=[];
    for(const reference of [true,false]){
        const h=setup(reference),vendor=fs.readFileSync(path.join(root,'frontend-ssalfer/js/vendor/xlsx-0.20.3.mini.min.js'),'utf8');
        vm.runInContext(vendor,h.context);h.window.XLSX=h.context.XLSX;
        vm.runInContext(h.source('reporteGeneralConvenios.js'),h.context);
        const rows={individuales:[{no:1,estado:'Estado',municipio:'Municipio',nucleo_agrario:'=Núcleo',parcelas:[{no_parcela:'10'},{no_parcela:null}],tipo_cop_operativo:null,superficie_excel_m2:'0.00000000001',fecha_firma_cop:'2026-02-03',fecha_ingreso_ran_convenio:'2020-01-01',fecha_inscripcion_ran_convenio:null,monto_total_90:'1234567890123456.78',monto_total_100:null}],colectivos:[{no:2,estado:'Estado',municipio:'Municipio',nucleo_agrario:'Núcleo',destinos:[{nombre:'TUC',superficie:{superficie_m2:'1.1234567'}},{nombre:null,superficie:null}],fecha_asamblea_realizada:'2019-02-03',fecha_ingreso_ran_asamblea:'2019-05-06',fecha_inscripcion_ran_asamblea:null,fecha_firma_cop:null,fecha_ingreso_ran_convenio:'2021-01-02',fecha_inscripcion_ran_convenio:null}]};
        const X=h.window.XLSX,book=h.window.SSALFER_REPORTE_GENERAL.libro(rows,'Proyecto QA');
        const reopened=X.read(X.write(book,{type:'array',bookType:'xlsx'}),{type:'array',cellStyles:true});
        outputs.push(clone({names:reopened.SheetNames,sheets:reopened.Sheets}));
    }
    assert.deepEqual(outputs[1],outputs[0]);
    assert.equal(outputs[1].sheets['Convenios individuales'].K6.v,'1234567890123456.78');
    assert.equal(outputs[1].sheets['Convenios individuales'].K6.t,'s');
});
}
