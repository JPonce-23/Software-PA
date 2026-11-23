// Execute real page callbacks with synthetic API/DOM in Node; no browser or server.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'../..');

class Element {
    constructor(tag='div',id='') {
        this.tagName=tag;this.id=id;this.value='';this.children=[];this.listeners={};this.attributes={};
        this.classList={add(){}};this.open=false;this.cards=[];this._html='';this.options=[];
    }
    set innerHTML(value) {
        this._html=value;
        if(this.id==='rpContenido') {
            this.cards=[...value.matchAll(/<article\b[^>]*>([\s\S]*?)<\/article>/g)].map(match=>{
                const card=new Element('article');card.title=match[1].match(/<h[23]>(.*?)<\/h[23]>/)[1];return card;
            });
            this.pay=new Element('div');
        }
        if(this.tagName==='dialog'){this.results=new Element();this.closeButton=new Element('button');}
    }
    get innerHTML(){return this._html;}
    addEventListener(name,callback){this.listeners[name]=callback;}
    append(...nodes){this.children.push(...nodes);}
    add(option){this.options.push(option);}
    get selectedOptions(){return this.options.filter(o=>String(o.value)===String(this.value));}
    replaceChildren(){this.children=[];this._html='';this.cards=[];}
    setAttribute(name,value){this.attributes[name]=value;}
    removeAttribute(name){delete this.attributes[name];}
    querySelectorAll(selector){return selector==='article'?this.cards:[];}
    querySelector(selector){
        if(selector==='h2,h3')return {textContent:this.title};
        if(selector==='.rp-pagos')return this.pay;
        if(selector==='.rp-opciones')return this.results;
        if(selector==='.rp-cerrar')return this.closeButton;
        return null;
    }
    showModal(){this.open=true;}
    close(){this.open=false;this.listeners.close?.();}
    focus(){this.focused=true;}
}
async function load(file='resumenProyecto.js',{search='?id_proyecto=1',get=async()=>[]}={}) {
    const nodes=new Map(),dialogs=[],calls=[];let ready;
    const node=id=>{if(!nodes.has(id))nodes.set(id,new Element('div',id));return nodes.get(id);};
    const document={body:new Element('body'),getElementById:node,
        addEventListener(name,callback){if(name==='DOMContentLoaded')ready=callback;},
        createElement(tag){const element=new Element(tag);if(tag==='dialog')dialogs.push(element);return element;}};
    const window={AuthAPI:{requerirSesion:async()=>({user:{rol:'visualizador'}})},
        ProyectosAPI:{listar:async()=>[{id_proyecto:1,nombre_proyecto:'One'},{id_proyecto:2,nombre_proyecto:'Two'}]},
        ReportesAPI:{obtenerResumenProyecto:async()=>new Proxy({},{get:()=>0})},
        SSALFER_FORMAT:{formatearFecha:String},
        ClienteAPI:{get:async url=>{calls.push(url);return get(url);}}};
    const context=vm.createContext({document,window,URL,URLSearchParams,console,
        location:{search,href:'https://qa.invalid/page'+search},history:{replaceState(){}},
        Option:class{constructor(text,value){this.textContent=text;this.value=value;}}});
    vm.runInContext(fs.readFileSync(path.join(root,'frontend-ssalfer/js',file),'utf8'),context);
    await ready();
    assert.ok(!node(file==='resumenProyecto.js'?'rpError':'sfError').textContent);
    return {node,dialogs,calls};
}
const row=(id,name='Synthetic nucleus',total=1,realizados=1,pendientes=0)=>({id_proyecto_nucleo:id,nombre_nucleo:name,total,realizados,pendientes});

test('summary cards preserve source destinations and individual/collective FIFONAFE filters',async()=>{
    const h=await load(),cards=h.node('rpContenido').cards;
    assert.equal(cards.length,12);
    assert.equal(cards[0].children[0].href,'/pages/fichaProyecto.html?id=1#nucleosAgrarios');
    assert.equal(cards[8].children[0].href,'/pages/seguimientoFifonafe.html?id_proyecto=1&ambito=individual');
    assert.equal(cards[9].children[0].href,'/pages/seguimientoFifonafe.html?id_proyecto=1&ambito=colectivo');
    assert.equal(cards[1].children[0].type,'button');
});

test('source dialog paginates beyond 200 and escapes nucleus names',async()=>{
    const rows=Array.from({length:201},(_,i)=>row(i+1,i===0?'<img src=x onerror="bad()">':`Nucleus ${i}`));
    const h=await load('resumenProyecto.js',{get:async url=>{
        const params=new URL('https://qa.invalid'+url).searchParams;
        assert.equal(params.get('tipo'),'parcelas');assert.equal(params.get('limit'),'200');
        const skip=Number(params.get('skip'));return rows.slice(skip,skip+200);
    }});
    await h.node('rpContenido').cards[1].children[0].onclick();
    assert.equal(h.calls.length,2);assert.match(h.calls[1],/skip=200/);
    const html=h.dialogs[0].results.innerHTML;
    assert.equal([...html.matchAll(/<a /g)].length,201);
    assert.ok(!html.includes('<img'));assert.match(html,/&lt;img src=x onerror=&quot;bad\(\)&quot;&gt;/);
    assert.match(html,/parcela.html\?id_proyecto_nucleo=201/);
});

test('activity and payment source states distinguish completed, pending and available',async()=>{
    const h=await load('resumenProyecto.js',{get:async()=>[row(1,'Done',2,2,0),row(2,'Pending',2,0,2),row(3,'Available',2,0,0)]});
    await h.node('rpContenido').cards[5].children[0].onclick();
    let html=h.dialogs[0].results.innerHTML;
    for(const color of ['verde','pendiente','azul'])assert.match(html,new RegExp('rp-origen-'+color));
    assert.match(html,/tipo_actividad=sensibilizacion/);
    h.dialogs[0].close();
    await h.node('rpContenido').pay.children[0].onclick();
    html=h.dialogs[0].results.innerHTML;
    assert.match(html,/Con pagos registrados/);assert.match(html,/Sin pagos registrados/);
    assert.match(html,/afectacion.html\?id_proyecto_nucleo=/);
});

test('empty sources and source failures remain visible without invented records',async()=>{
    for(const fails of [false,true]) {
        const h=await load('resumenProyecto.js',{get:async()=>{if(fails)throw Error('Synthetic failure');return [];}});
        await h.node('rpContenido').cards[2].children[0].onclick();
        const results=h.dialogs[0].results;
        if(fails)assert.equal(results.textContent,'Synthetic failure');
        else assert.match(results.innerHTML,/No hay núcleos con registros/);
    }
});

test('a closed and reopened source dialog ignores the older response or failure',async()=>{
    for(const fails of [false,true]) {
        let resolveOld,rejectOld,first=true;
        const old=new Promise((resolve,reject)=>{resolveOld=resolve;rejectOld=reject;});
        const h=await load('resumenProyecto.js',{get:async()=>{if(first){first=false;return old;}return [row(2,'Fresh activity')];}});
        const pending=h.node('rpContenido').cards[1].children[0].onclick();
        const dialog=h.dialogs[0];dialog.close();
        await h.node('rpContenido').cards[5].children[0].onclick();
        const fresh=dialog.results.innerHTML;
        if(fails)rejectOld(Error('Stale failure'));else resolveOld([row(1,'Stale parcel')]);
        await pending;
        assert.equal(dialog.results.innerHTML,fresh);
        assert.ok(!dialog.results.textContent);
    }
});

test('changing project rejects an older source batch',async()=>{
    let release;const old=new Promise(resolve=>release=resolve);
    const h=await load('resumenProyecto.js',{get:()=>old});
    const pending=h.node('rpContenido').cards[1].children[0].onclick();
    h.node('rpProyecto').value='2';await h.node('rpActualizar').listeners.click();
    assert.equal(h.dialogs[0].open,false);release([row(999,'Old project')]);await pending;
    assert.ok(!h.dialogs[0].results.innerHTML.includes('Old project'));
});

test('FIFONAFE initializes only recognized scope filters from summary links',async()=>{
    for(const ambito of ['individual','colectivo','unknown']) {
        const h=await load('seguimientoFifonafe.js',{search:'?id_proyecto=1&ambito='+ambito,
            get:async()=>({items:[],total:0,individuales:0,colectivos:0,hay_mas:false})});
        const params=new URL('https://qa.invalid'+h.calls[0]).searchParams;
        assert.equal(params.get('ambito'),ambito==='unknown'?null:ambito);
    }
});
