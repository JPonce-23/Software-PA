// Whole shared dashboard module, with no administrative DOM/API work on denial.
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const normalizeSource=require('./helpers/source.cjs');
const source=normalizeSource(fs.readFileSync(path.resolve(__dirname,'../../frontend-ssalfer/js/dashboard.js'),'utf8'));

for(const sessionFirst of [false,true])for(const domPresent of [false,true]){
 test(`denied page skips shared dashboard: sessionFirst=${sessionFirst}, DOM=${domPresent}`,async()=>{
  const listeners=[],calls=[],errors=[];let resolve;
  const window={SSALFER_SESION_LISTA:new Promise(r=>resolve=r)};
  const document=new Proxy({addEventListener(name,fn){calls.push('listen:'+name);listeners.push(fn)}},{get(target,name){
   if(name in target)return target[name];
   return ()=>{calls.push('DOM:'+String(name));return domPresent?{}:null};
  }});
  Object.defineProperty(window,'ProyectosAPI',{get(){calls.push('ProyectosAPI');throw Error('A denied page must not consult projects')}});
  vm.runInNewContext(source,{window,document,console:{error:e=>errors.push(e),warn:e=>errors.push(e)}},{filename:'dashboard.js'});
  assert.deepEqual(calls,['listen:DOMContentLoaded']);calls.length=0;
  if(sessionFirst)resolve(null);
  const work=listeners.map(fn=>fn());
  assert.deepEqual(calls,[],'No initialization while page authorization is pending');
  if(!sessionFirst)resolve(null);
  await Promise.all(work);
  assert.deepEqual(calls,[]);assert.deepEqual(errors,[]);
 });
}
