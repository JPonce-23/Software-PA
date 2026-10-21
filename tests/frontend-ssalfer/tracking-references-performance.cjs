// F06: execute immutable original and current tracking reference functions.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {execFileSync}=require('node:child_process'),root=path.resolve(__dirname,'../..');
const normalizeSource = require('./helpers/source.cjs');
const source=(file,old)=>normalizeSource(old?execFileSync('git',['show',`41d4b68:frontend-ssalfer/js/${file}`],{cwd:root,encoding:'utf8'}):fs.readFileSync(path.join(root,'frontend-ssalfer/js',file),'utf8'));
const section=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert.ok(i>=0&&j>i,a);return s.slice(i,j)};
const clone=x=>JSON.parse(JSON.stringify(x));
function fixture(n=53){
 const parents=Array.from({length:n},(_,i)=>({id_afectacion:i+1,id_proyecto_nucleo:1,tipo_afectacion:i%2?'individual':'colectivo',superficie_afectada_ha:i%2?'1.1234567':null,superficie_preliminar_ha:null,situacion:i%3?'En trámite':null}));
 const agreement=id=>({id_convenio:id,id_proyecto_nucleo:1,tipo_convenio:id%2?'cop_original':null,consecutivo:id,ambito:'colectivo',fecha_firma:null,fecha_programada_firma:'2026-03-04',descripcion_instrumento:'<Documento>'});
 const children=new Map(parents.map(p=>[p.id_afectacion,[agreement(p.id_afectacion+10)]]));
 if(n>1){children.get(1).unshift(agreement(1));children.get(2).unshift(agreement(1));}
 return {parents,children};
}
function harness(old=false,{data=fixture(),fail=()=>false,hold=()=>null}={}){
 const calls=[],errors=[];
 async function get(url){calls.push(url);const pending=hold(url);if(pending)await pending;if(fail(url))throw Error('Fallo sintético');
  if(url.endsWith('/reportes/referencias-convenios'))return clone(data.parents.flatMap(a=>(data.children.get(a.id_afectacion)||[]).map(item=>({id_afectacion:a.id_afectacion,item}))));
  if(url.endsWith('/afectaciones'))return clone(data.parents);
  const m=url.match(/^\/afectaciones\/(\d+)\/convenios$/);if(m)return clone(data.children.get(+m[1])||[]);throw Error(url);
 }
 const window={ClienteAPI:{get},SSALFER_UI:{toast:m=>errors.push(m)},AfectacionesAPI:{listarPorProyectoNucleo:id=>get(`/proyecto-nucleo/${id}/afectaciones`)},ConveniosAPI:{listarPorAfectacion:id=>get(`/afectaciones/${id}/convenios`)}};
 const context=vm.createContext({window,console});
 vm.runInContext(source('utils/formatters.js',old),context);
 vm.runInContext(source('api/seguimiento.js',old),context);
 const s=source('seguimiento.js',old);
 vm.runInContext('const idProyectoNucleo=1;let eventos=[];'+section(s,'    const tiposEntidadSelectorDirecto','    function opcionesEntidad(')+section(s,'    function idEntidadDirecta(','    async function cargarSelectorEntidad(')+section(s,'    async function cargarReferenciasEventos()','    function actualizarResumen()')+'\nglobalThis.refs=referenciasEntidad;globalThis.cache=consultasEntidad;',context);
 return {context,calls,errors,async run(ids){context.ids=ids;vm.runInContext('eventos=ids.map(entidad_id=>({entidad_tipo:"convenio",entidad_id}));',context);await context.cargarReferenciasEventos();},snapshot(){return clone([...context.refs]);},keys(){return clone([...context.cache.keys()]);}};
}
test('tracking preserves parent stop rule, shared agreements, ordering, dates, null types and visited cache',async()=>{
 const rows=[];
 for(const n of [0,3,53,150])for(const ids of [[1],[1,12],[1,n+10],[1,999999]]){
  const data=fixture(n),before=harness(true,{data}),after=harness(false,{data});await before.run(ids);await after.run(ids);
  assert.deepEqual(after.snapshot(),before.snapshot());assert.deepEqual(after.keys(),before.keys());assert.deepEqual(after.errors,before.errors);
  assert.equal(after.calls.length,n?2:1);rows.push({parents:n,ids,original_requests:before.calls.length,optimized_requests:after.calls.length});
 }
 if(process.env.F06_EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.F06_EVIDENCE_DIR,'tracking-node-comparison.json'),JSON.stringify(rows,null,2));
});
test('tracking batch failure falls back to existing partial results and toast',async()=>{
 for(const brokenParent of [null,2]){
  const data=fixture(5),before=harness(true,{data,fail:u=>u===`/afectaciones/${brokenParent}/convenios`});
  const after=harness(false,{data,fail:u=>u.endsWith('/reportes/referencias-convenios')||u===`/afectaciones/${brokenParent}/convenios`});
  await before.run([1,999999]);await after.run([1,999999]);assert.deepEqual(after.snapshot(),before.snapshot());assert.deepEqual(after.errors,before.errors);
 }
});
test('tracking ignores a superseded batch and an old failure cannot evict a fresh cached request',async()=>{
 let release;const gate=new Promise(r=>release=r);let first=true;
 const h=harness(false,{hold:u=>u.endsWith('/reportes/referencias-convenios')&&first?(first=false,gate):null});
 const pending=h.run([1,999999]);await new Promise(r=>setImmediate(r));await h.run([1]);const fresh=h.snapshot();release();await pending;assert.deepEqual(h.snapshot(),fresh);assert.equal(h.errors.length,0);
 let reject;h.context.reject=()=>{};
 vm.runInContext('globalThis.old=consultarUnaVez("old",()=>new Promise((resolve,reject)=>globalThis.reject=reject));',h.context);await new Promise(r=>setImmediate(r));
 vm.runInContext('consultasEntidad.clear();globalThis.fresh=consultarUnaVez("old",()=>42);',h.context);h.context.reject(Error('old'));await assert.rejects(h.context.old);assert.equal(await h.context.fresh,42);assert.equal(h.context.cache.get('old'),h.context.fresh);
});
