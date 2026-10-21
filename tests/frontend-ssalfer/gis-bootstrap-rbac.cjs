// Execute both administrative modules with DOM/API doubles; this is not a browser run.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const normalizeSource=require('./helpers/source.cjs');
const root=path.resolve(__dirname,'../../frontend-ssalfer/js');

function page({removed=false}={}) {
    const listeners=[],requests=[],errors=[],nodes=new Map();
    let domReads=0,bindings=0,panels=0,resolve;
    class Element {
        constructor(){this.value='';this.files=[];this.dataset={};this.style={};this.children=[];
            this.classList={add(){},remove(){},toggle(){},contains(){return false}};}
        addEventListener(){bindings++}
        append(...children){this.children.push(...children);panels+=children.length}
        appendChild(child){this.append(child);return child}
        before(){panels++}
        replaceChildren(...children){this.children=children}
        closest(){return new Element()}
        querySelector(){return new Element()}
        querySelectorAll(){return []}
        setAttribute(){}
        removeAttribute(){}
    }
    const node=id=>{
        domReads++;
        if(removed)throw Error('The denied page has already removed the administrative DOM');
        if(!nodes.has(id))nodes.set(id,new Element());
        return nodes.get(id);
    };
    const document={addEventListener(name,fn){assert.equal(name,'DOMContentLoaded');listeners.push(fn)},
        getElementById:node,querySelector:node,querySelectorAll(){domReads++;return []},
        createElement(){domReads++;return new Element()}};
    const window={document,location:{search:''},SSALFER_SESION_LISTA:new Promise(r=>resolve=r),
        ClienteAPI:{async get(url){requests.push(url);return []},mostrarErrorAPI(e){errors.push(e)}},
        GeoespacialAPI:{},SSALFER_GESTION:{e:String},SSALFER_UI:{},ProyectosAPI:{ordenar:rows=>rows}};
    const context=vm.createContext({window,document,URLSearchParams,console:{error:e=>errors.push(e),warn:e=>errors.push(e)}});
    // Match the real page's script order: reconciliation registers before the import manager.
    for(const file of ['conciliacionGeoespacial.js','gestionGeoespacial.js'])
        vm.runInContext(normalizeSource(fs.readFileSync(path.join(root,file),'utf8')),context,{filename:file});
    return {window,requests,errors,resolve,stats:()=>({domReads,bindings,panels}),
        start:()=>Promise.all(listeners.map(fn=>fn()))};
}

for(const role of ['operador','visualizador',null]){
    for(const removed of [false,true])test(`administrative bootstrap denied without DOM/API/console work: ${role}, removed=${removed}`,async()=>{
        const p=page({removed}),done=p.start();
        assert.deepEqual(p.stats(),{domReads:0,bindings:0,panels:0});
        p.resolve(role?{user:{rol:role}}:null);
        await done;
        assert.deepEqual(p.stats(),{domReads:0,bindings:0,panels:0});
        assert.equal(p.window.SSALFER_GIS,undefined);
        assert.deepEqual(p.requests,[]);assert.deepEqual(p.errors,[]);
    });
}

for(const role of ['admin','geografo']){
    for(const sessionFirst of [false,true])test(`administrative bootstrap waits for session and starts both modules: ${role}, sessionFirst=${sessionFirst}`,async()=>{
        const p=page(),session={user:{rol:role}};
        if(sessionFirst)p.resolve(session);
        const done=p.start();
        assert.deepEqual(p.stats(),{domReads:0,bindings:0,panels:0});
        if(!sessionFirst)p.resolve(session);
        await done;
        assert.equal(p.window.SSALFER_GIS.puedeEditar(),true);
        assert.ok(p.stats().domReads>0);assert.ok(p.stats().bindings>0);assert.ok(p.stats().panels>=3);
        assert.deepEqual(p.requests,['/proyectos?skip=0&limit=200']);
        assert.deepEqual(p.errors,[]);
    });
}
