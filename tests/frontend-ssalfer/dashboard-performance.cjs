// Run with node --test. VM/DOM doubles, not browser/HAR/render measurements.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const ExcelJS = require(path.join(root,'frontend-ssalfer/js/vendor/exceljs-4.4.0.min.js'));
const vendor = new vm.Script(fs.readFileSync(path.join(root,'frontend-ssalfer/js/vendor/exceljs-4.4.0.min.js'),'utf8'));
const normalizeSource = require('./helpers/source.cjs');
const original = file => normalizeSource(execFileSync('git', ['show', `cbc78d0:frontend-ssalfer/js/${file}`], {cwd:root,encoding:'utf8'}));
const current = file => normalizeSource(fs.readFileSync(path.join(root,'frontend-ssalfer/js',file),'utf8'));
const baselineOnly = process.env.F04_BASELINE_ONLY === '1';

function dataset(role='admin', sizes=[74,1]) {
    const projects=sizes.map((_,i)=>({id_proyecto:i+1,nombre_proyecto:`Proyecto ${i+1} <seguro>`,
        clave_proyecto:`=P${i+1}`,descripcion:null,fecha_inicio:null,fecha_fin:null,creado_en:`2026-01-0${i+1}`}));
    const nuclei=new Map(), affects=new Map(), agreements=new Map();
    let nId=0,aId=0;
    sizes.forEach((size,p)=>{
        nuclei.set(p+1,Array.from({length:Math.min(size,100)},(_,i)=>{
            const id=++nId;
            const rows=Array.from({length:1+(p===0&&i<17?1:0)},()=>({id_afectacion:++aId}));
            affects.set(id,rows);
            rows.forEach(a=>agreements.set(a.id_afectacion,i<2?[{
                id_convenio:p*100+1,ambito:'colectivo',tipo_convenio:'cop_original',consecutivo:1,fecha_firma:'2026-01-02',activo:true,
            },{
                id_convenio:p*100+2,ambito:'individual',tipo_convenio:'modificatorio',consecutivo:2,fecha_firma:null,activo:true,
            }]:[]));
            return {id_proyecto_nucleo:id,nombre_nucleo:`Núcleo ${id}`,municipio:'Municipio',entidad:'Entidad'};
        }));
    });
    return {role,projects:role==='admin'?projects:projects.slice(0,1),nuclei,affects,agreements};
}

function summary(data,project) {
    const unique=new Map();
    for(const n of data.nuclei.get(project)||[])for(const a of data.affects.get(n.id_proyecto_nucleo)||[])
        for(const c of data.agreements.get(a.id_afectacion)||[])unique.set(c.id_convenio,c);
    const rows=[...unique.values()].filter(c=>c.activo!==false);
    return {individuales:rows.filter(c=>c.ambito==='individual').length,colectivos:rows.filter(c=>c.ambito==='colectivo').length,
        formalizados:rows.filter(c=>['individual','colectivo'].includes(c.ambito)&&c.fecha_firma).length,
        convenios:rows.map(({id_convenio,ambito,tipo_convenio,consecutivo,fecha_firma})=>({id_convenio,ambito,tipo_convenio,consecutivo,fecha_firma}))};
}

async function load({reference=false,data=dataset(),fail=()=>false,delays={},exportExcel=true,allowExportError=false,freezeAgreements=false,pageAuthorization,afterDOMContentLoaded}={}) {
    const calls=[],errors=[],listeners=new Map(),nodes=new Map();let blob,lastWorkbook;
    class Element {
        constructor(tag='div'){this.tagName=tag;this.children=[];this.innerHTML='';this.attributes={};this.style={};
            this.classList={add(){},remove(){},contains(){return false},toggle(){}};}
        append(...children){this.children.push(...children)}
        appendChild(child){this.append(child);return child}
        setAttribute(k,v){this.attributes[k]=v}
        getAttribute(k){return this.attributes[k]||null}
        removeAttribute(k){delete this.attributes[k]}
        addEventListener(){}
        querySelectorAll(){return []}
        querySelector(selector){return selector==='.dashboard-graficas-grid'?new Element():null}
        before(element){nodes.set(element.id,element)}
        click(){}
    }
    for(const id of ['proyectosLista','listaProyectosDashboard','dashboardMensajeError','btnExportarDashboardCsv','btnExportarDashboardExcel'])nodes.set(id,new Element());
    const document={body:new Element('body'),getElementById:id=>nodes.get(id)||null,createElement:tag=>new Element(tag),
        querySelector:()=>null,querySelectorAll:()=>[],dispatchEvent(){},addEventListener(name,fn){
            if(!listeners.has(name))listeners.set(name,[]);listeners.get(name).push(fn);
        }};
    const clone=x=>JSON.parse(JSON.stringify(x));
    async function get(url){
        calls.push(url);
        if(delays[url])await new Promise(resolve=>setTimeout(resolve,delays[url]));
        if(fail(url))throw new Error('Fallo parcial sintético');
        if(url==='/auth/sesion')return {user:{id_usuario:1,rol:data.role,nombre:'QA',apellido_paterno:'F04'}};
        if(url.startsWith('/proyectos?'))return clone(data.projects);
        if(url==='/dashboard/kpi')return data.projects.flatMap(p=>[
            {id_proyecto:p.id_proyecto,indicador:'asambleas',anio:2025,programado:2,realizado:1,cantidad:1,superficie_ha:null,monto:null},
            {id_proyecto:p.id_proyecto,indicador:'asambleas',anio:2026,programado:3,realizado:2,cantidad:2,superficie_ha:'1.1234567',monto:'100.13'},
        ]);
        if(url==='/reportes/convenios/valores-declarados')return data.projects.flatMap(p=>[
            {id_proyecto:p.id_proyecto,id_convenio:1,concepto:'monto_90_declarado',valor_declarado:'90.12'},
            {id_proyecto:p.id_proyecto,id_convenio:1,concepto:'monto_100_declarado',valor_declarado:null},
            {id_proyecto:p.id_proyecto,id_convenio:2,concepto:'monto_100_declarado',valor_declarado:'100.13'},
        ]);
        let match;
        if((match=url.match(/^\/proyectos\/(\d+)\/dashboard\/resumen$/))){
            const cop=summary(data,+match[1]);
            return {total_nucleos:(data.nuclei.get(+match[1])||[]).length,total_convenios:cop.convenios.length,
                individuales:cop.individuales,colectivos:cop.colectivos,formalizados:cop.formalizados};
        }
        if((match=url.match(/^\/proyectos\/(\d+)\/dashboard\/exportacion\/(nucleos|convenios)\?/))){
            const params=new URL(url,'http://qa').searchParams, cursor=Number(params.get('despues_de')),limit=Number(params.get('limit'));
            const field=match[2]==='nucleos'?'id_proyecto_nucleo':'id_convenio';
            const all=(match[2]==='nucleos'?(data.nuclei.get(+match[1])||[]):summary(data,+match[1]).convenios).slice().sort((a,b)=>a[field]-b[field]);
            const remaining=all.filter(x=>x[field]>cursor),items=remaining.slice(0,limit),more=remaining.length>limit;
            return {items,total:all.length,revision:'0123456789abcdef0123456789abcdef',hay_mas:more,siguiente_id:more?items.at(-1)[field]:null};
        }
        if((match=url.match(/^\/proyectos\/(\d+)\/nucleos$/)))return clone(data.nuclei.get(+match[1])||[]);
        if((match=url.match(/^\/proyectos\/(\d+)\/dashboard\/convenios$/))){
            const result=summary(data,+match[1]);
            if(freezeAgreements){result.convenios.forEach(Object.freeze);Object.freeze(result.convenios);}
            return result;
        }
        if((match=url.match(/^\/proyecto-nucleo\/(\d+)\/afectaciones$/)))return clone(data.affects.get(+match[1])||[]);
        if((match=url.match(/^\/afectaciones\/(\d+)\/convenios$/)))return clone(data.agreements.get(+match[1])||[]);
        throw new Error('Unexpected GET '+url);
    }
    class URLDouble extends URL {}
    URLDouble.createObjectURL=value=>{blob=value;return 'blob:fixture'};URLDouble.revokeObjectURL=()=>{};
    const window={addEventListener(){},document,location:{pathname:'/dashboard.html',search:'',origin:'http://fixture.invalid'},
        innerWidth:1200,ClienteAPI:{get,API_BASE_URL:'/api',mostrarErrorAPI(error){errors.push(error)},ErrorAPI:class extends Error{}},
        SSALFER_UI:{cargando:{iniciar:()=>()=>{}},toast(){}},
        html2canvas:async()=>({width:800,height:200,toDataURL:()=> 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6P5QAAAAASUVORK5CYII='}),
        setTimeout};
    if(pageAuthorization)window.SSALFER_SESION_LISTA=pageAuthorization;
    const context=vm.createContext({window,document,console:{warn(){},error(){}},URL:URLDouble,URLSearchParams,Blob,AbortController,DOMException,
        html2canvas:window.html2canvas,CustomEvent:class{},setTimeout,clearTimeout,setImmediate,clearImmediate,
        localStorage:{getItem:()=>null,setItem(){}}});
    // Keep vendor and application arrays in the same JS realm (as in a browser).
    vendor.runInContext(context);
    context.ExcelJS=window.ExcelJS||context.ExcelJS;
    const VendorWorkbook=context.ExcelJS.Workbook;
    context.ExcelJS.Workbook=class extends VendorWorkbook {constructor(){super();lastWorkbook=this}};
    window.ExcelJS=context.ExcelJS;
    for(const file of ['api/auth.js','api/proyectos.js','api/nucleos.js','api/afectaciones.js','api/convenios.js','api/reportes.js','utils/dashboardExcel.js','dashboard.js']){
        vm.runInContext(reference?original(file):current(file),context,{filename:file});
    }
    for(const fn of listeners.get('DOMContentLoaded')||[])fn();
    afterDOMContentLoaded?.({calls,cards:()=>nodes.get('listaProyectosDashboard').children});
    const button=()=>nodes.get('btnExportarDashboardExcel');
    for(let i=0;i<2000&&(!button()||button().disabled)&&!(nodes.get('listaProyectosDashboard').children.length===data.projects.length&&nodes.get('listaProyectosDashboard').children.every(e=>!e.attributes['aria-busy']));i++)await new Promise(resolve=>setTimeout(resolve,1));
    const ready=button()&&!button().disabled;
    const cards=nodes.get('listaProyectosDashboard').children.map(e=>e.innerHTML);
    let sheets=null;
    if(exportExcel&&ready){
        await button().onclick();
        if(!blob&&errors.length&&!allowExportError)throw errors.at(-1);
        if(blob){
            const restored=new ExcelJS.Workbook();await restored.xlsx.load(await blob.arrayBuffer());
            sheets=restored.worksheets.map(sh=>({name:sh.name,rows:sh.getSheetValues().map(row=>
                row?.map(cell=>cell instanceof Date?cell.toISOString():cell)).filter(row=>row?.[1]!=='Generado')}));
        }
    }
    return {calls,cards,ready,sheets,csv:nodes.get('btnExportarDashboardCsv').href,workbookCreated:!!lastWorkbook,
        exportError:errors.at(-1)?.message||null};
}

test('baseline: audited-size traversal issues 174 API calls (VM, not HAR)',async()=>{
    const result=await load({reference:true});
    assert.equal(result.calls.length,174);assert.equal(result.ready,true);assert.ok(result.sheets);
    if(process.env.F04_EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.F04_EVIDENCE_DIR,'frontend-baseline.json'),JSON.stringify({
        kind:'VM execution of original scripts with HTTP doubles; not browser',calls:result.calls,requests:result.calls.length,cards:result.cards,sheets:result.sheets},null,2));
});

test('all roles: identical cards, actual XLSX cells, CSV URL; constant requests', {skip:baselineOnly},async()=>{
    const results=[];
    for(const role of ['admin','operador','visualizador','geografo']){
        const data=dataset(role),before=await load({reference:true,data}),after=await load({data});
        assert.deepEqual(after.cards,before.cards);assert.deepEqual(after.sheets,before.sheets);assert.equal(after.csv,before.csv);
        assert.equal(after.calls.length,6+9*data.projects.length);
        assert.ok(!after.calls.some(u=>u.includes('/afectaciones')));
        results.push({role,before:before.calls.length,after:after.calls.length,identicalCards:true,identicalXlsxCells:true});
    }
    if(process.env.F04_EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.F04_EVIDENCE_DIR,'frontend-comparison.json'),JSON.stringify(results,null,2));
});

test('all roles: resolved page authorization preserves dashboard/sidebar requests and XLSX', {skip:baselineOnly},async()=>{
    for(const role of ['admin','operador','visualizador','geografo']){
        const data=dataset(role),before=await load({data});
        const after=await load({data,pageAuthorization:Promise.resolve({user:{id_usuario:1,rol:role}})});
        assert.deepEqual(after.calls,before.calls);assert.deepEqual(after.cards,before.cards);
        assert.deepEqual(after.sheets,before.sheets);assert.equal(after.csv,before.csv);
        assert.equal(after.calls.filter(url=>url.startsWith('/proyectos?')).length,1);
    }
});

test('pending page authorization delays all shared dashboard consumers, then starts normally', {skip:baselineOnly},async()=>{
    let authorize;
    const pageAuthorization=new Promise(resolve=>authorize=resolve);
    const result=await load({pageAuthorization,afterDOMContentLoaded({calls,cards}){
        assert.deepEqual(calls,[]);assert.deepEqual(cards(),[]);
        authorize({user:{id_usuario:1,rol:'admin'}});
    }});
    assert.equal(result.ready,true);assert.equal(result.cards.length,2);assert.ok(result.sheets);
    assert.equal(result.calls.length,24);assert.equal(result.calls.filter(url=>url.startsWith('/proyectos?')).length,1);
});

test('legacy capped fixture is compatible; full universes are covered separately', {skip:baselineOnly},async()=>{
    const data=dataset('admin',[105,0]);
    const before=await load({reference:true,data}),after=await load({data});
    assert.deepEqual(after.cards,before.cards);assert.deepEqual(after.sheets,before.sheets);
    assert.equal(after.calls.length,24);
});

test('missing summary/KPI/value data blocks Excel instead of exporting a partial dashboard', {skip:baselineOnly},async()=>{
    for(const url of ['/proyectos/1/dashboard/resumen','/dashboard/kpi','/reportes/convenios/valores-declarados']){
        const result=await load({fail:u=>u===url});
        assert.equal(result.ready,false);assert.equal(result.sheets,null);
    }
});

test('slow first project keeps project order in DOM and XLSX', {skip:baselineOnly},async()=>{
    const data=dataset(),before=await load({reference:true,data});
    const after=await load({data,delays:{'/proyectos/2/dashboard/resumen':50}});
    assert.deepEqual(after.cards,before.cards);assert.deepEqual(after.sheets,before.sheets);
});

test('new documents/users fetch afresh; detail is requested only by explicit export', {skip:baselineOnly},async()=>{
    const [a,b,c]=await Promise.all([load({delays:{'/proyectos/2/dashboard/resumen':30}}),load({data:dataset('visualizador')}),load()]);
    assert.equal(a.calls.length,24);assert.equal(b.calls.length,15);assert.equal(c.calls.length,24);
    assert.equal(b.cards.length,1);assert.ok(!b.cards[0].includes('Proyecto 2'));
    assert.equal(a.calls.filter(u=>u.startsWith('/proyectos?')).length,1);
});

test('all roles: null instrument type exports and reopens XLSX without changing data or indicators', {skip:baselineOnly},async()=>{
    for(const role of ['admin','operador','visualizador','geografo']){
        const data=dataset(role,[3,1]);
        for(const rows of data.agreements.values())for(const c of rows)if(c.id_convenio===1)c.tipo_convenio=null;
        const snapshot=JSON.stringify([...data.agreements]);
        const before=await load({reference:true,data,allowExportError:true});
        const after=await load({data,freezeAgreements:true});
        assert.deepEqual(after.cards,before.cards);assert.equal(after.csv,before.csv);
        assert.match(before.exportError,/null.*replaceAll/);assert.equal(before.sheets,null);
        assert.equal(after.exportError,null);assert.ok(after.sheets);
        assert.ok(after.sheets.some(s=>s.rows.some(r=>r?.[1]==='Tipo no informado · Consecutivo 1')));
        assert.equal(JSON.stringify([...data.agreements]),snapshot);
        // Only the missing presentation label differs from an otherwise identical valid workbook.
        const presented=dataset(role,[3,1]);
        for(const rows of presented.agreements.values())for(const c of rows)if(c.id_convenio===1)c.tipo_convenio='Tipo no informado';
        const expected=await load({reference:true,data:presented});
        assert.deepEqual(after.sheets,expected.sheets);
    }
});

test('agreement export follows F04 ascending ID order, preserving every row/value and input order', {skip:baselineOnly},async()=>{
    const rows=[
        {id_convenio:9,tipo_convenio:'modificatorio',consecutivo:1,ambito:'individual',fecha_firma:null,activo:true},
        {id_convenio:2,tipo_convenio:'cop_original',consecutivo:8,ambito:'colectivo',fecha_firma:'2026-01-03',activo:true},
        {id_convenio:1,tipo_convenio:'cop_original',consecutivo:10,ambito:'colectivo',fecha_firma:'2026-01-02',activo:true},
    ];
    const agreements=sheets=>sheets.find(s=>s.rows.some(r=>r?.[1]==='Convenio')).rows.filter(r=>typeof r?.[1]==='string'&&r[1].includes(' · Consecutivo '));
    let expected;
    for(const order of [rows,[rows[1],rows[2],rows[0]],rows.toReversed?rows.toReversed():[...rows].reverse()]){
        const data=dataset('admin',[3]);
        for(const id of data.agreements.keys())data.agreements.set(id,order.map(c=>({...c})));
        const snapshot=JSON.stringify([...data.agreements]);
        const before=await load({reference:true,data}),after=await load({data,freezeAgreements:true});
        const exported=agreements(after.sheets);
        assert.deepEqual(after.cards,before.cards);
        assert.deepEqual(exported.map(r=>r[1]),['cop original · Consecutivo 10','cop original · Consecutivo 8','modificatorio · Consecutivo 1']);
        assert.deepEqual(exported.map(JSON.stringify).sort(),agreements(before.sheets).map(JSON.stringify).sort());
        assert.equal(exported.length,3);assert.equal(JSON.stringify([...data.agreements]),snapshot);
        if(expected)assert.deepEqual(after.sheets,expected);else expected=after.sheets;
    }
});
