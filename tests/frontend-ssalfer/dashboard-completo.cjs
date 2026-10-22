const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const source=fs.readFileSync(path.join(root,'frontend-ssalfer/js/api/nucleos.js'),'utf8');
function fixture(n,{alter,fail}={}){
 const calls=[],revision={nucleos:'1'.repeat(32),convenios:'2'.repeat(32)};
 const rows={nucleos:Array.from({length:n},(_,i)=>({id_proyecto_nucleo:i*2+1,nombre_nucleo:'Núcleo '+i})),
 convenios:Array.from({length:n},(_,i)=>({id_convenio:i*3+1,ambito:i%2?'individual':'colectivo',fecha_firma:i%2?null:'2026-01-02',tipo_convenio:null}))};
 const summary={total_nucleos:n,total_convenios:n,individuales:Math.floor(n/2),colectivos:Math.ceil(n/2),formalizados:Math.ceil(n/2)};
 const window={ClienteAPI:{get:async(url,{signal}={})=>{
  calls.push(url);signal?.throwIfAborted();if(fail)await fail(url);
  if(url.endsWith('/resumen'))return {...summary};
  const parsed=new URL(url,'http://qa'),res=parsed.pathname.split('/').at(-1),cursor=Number(parsed.searchParams.get('despues_de')),limit=Number(parsed.searchParams.get('limit'));
  const field=res==='nucleos'?'id_proyecto_nucleo':'id_convenio',remaining=rows[res].filter(x=>x[field]>cursor),items=remaining.slice(0,limit).map(x=>({...x}));
  const page={items,total:n,revision:revision[res],hay_mas:remaining.length>limit,siguiente_id:remaining.length>limit?items.at(-1)[field]:null};
  if(cursor)assert.equal(parsed.searchParams.get('revision'),revision[res]);
  return alter?.(page,{res,cursor,limit,signal})||page;
 }}};
 vm.runInNewContext(source,{window,URLSearchParams});
 return {api:window.NucleosAPI,calls,summary};
}
for(const n of [0,99,100,101,105,200,201,1000])test(`descarga íntegra de ${n} núcleos y convenios, revisión independiente y totales`,async()=>{
 const f=fixture(n),controller=new AbortController();
 const data=await f.api.exportacionDashboard(3,{signal:controller.signal});
 await f.api.validarExportacionDashboard(data,f.summary,{signal:controller.signal});
 assert.equal(data.nucleos.items.length,n);assert.equal(data.convenios.items.length,n);
 assert.equal(f.calls.length,2*Math.max(1,Math.ceil(n/200))+3);
 assert.equal(new Set(data.convenios.items.map(x=>x.id_convenio)).size,n);
});
const invalid={
 'ID repetido':(p,{cursor})=>{if(cursor)p.items[0].id_proyecto_nucleo=cursor;},
 'ID desordenado':p=>{[p.items[0],p.items[1]]=[p.items[1],p.items[0]];},
 'cursor inmóvil':p=>{p.siguiente_id=0;},
 'cursor distinto al último ID':p=>{p.siguiente_id+=1;},
 'revisión distinta':(p,{cursor})=>{if(cursor)p.revision='f'.repeat(32);},
 'total distinto':(p,{cursor})=>{if(cursor)p.total++;},
 'fin anticipado':p=>{p.hay_mas=false;p.siguiente_id=null;},
 'lote vacío con continuación':p=>{p.items=[];},
 'más de 200 filas':p=>{p.items.push({...p.items.at(-1),id_proyecto_nucleo:9999});},
 'revisión inválida':p=>{p.revision='incorrecta';},
 'total no entero':p=>{p.total='201';},
 'cursor al terminar':(p,{cursor})=>{if(cursor)p.siguiente_id=999;},
 'hay_mas inválido':p=>{p.hay_mas='true';}
};
for(const [name,alter]of Object.entries(invalid))test(`rechaza ${name}`,async()=>{
 const f=fixture(201,{alter:(p,m)=>{if(m.res==='nucleos')alter(p,m);}});
 await assert.rejects(f.api.exportacionDashboard(3));
});
for(const status of [401,403,409,500,0])test(`no acepta descarga con fallo ${status} en segunda página`,async()=>{
 const f=fixture(201,{fail:url=>{if(url.includes('despues_de=399'))throw Object.assign(new Error('Prueba'),{status});}});
 await assert.rejects(f.api.exportacionDashboard(3),e=>e.status===status);
});
test('descarta respuesta tardía después de cancelar',async()=>{
 const controller=new AbortController(),f=fixture(201,{alter:()=>{controller.abort();}});
 await assert.rejects(f.api.exportacionDashboard(3,{signal:controller.signal}),{name:'AbortError'});
});
test('detecta cambio después de descargar, incluso con igual cantidad',async()=>{
 let changed=false;
 const f=fixture(201,{alter:(p,{limit})=>{if(changed&&limit===1)p.revision='f'.repeat(32);}});
 const data=await f.api.exportacionDashboard(3);changed=true;
 await assert.rejects(f.api.validarExportacionDashboard(data,f.summary),e=>e.status===409);
});
test('rechaza resumen que no corresponde a las filas recibidas',async()=>{
 const f=fixture(201),data=await f.api.exportacionDashboard(3);
 await assert.rejects(f.api.validarExportacionDashboard(data,{...f.summary,total_convenios:200}),e=>e.status===409);
});
test('no mezcla proyectos simultáneos ni conserva datos entre exportaciones',async()=>{
 const f=fixture(201);await Promise.all([f.api.exportacionDashboard(3),f.api.exportacionDashboard(4)]);
 assert.equal(f.calls.filter(x=>x.startsWith('/proyectos/3/')).length,4);
 assert.equal(f.calls.filter(x=>x.startsWith('/proyectos/4/')).length,4);
 await f.api.exportacionDashboard(3);assert.equal(f.calls.length,12);
});
