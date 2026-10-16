// Navegador con API interceptada: ninguna escritura sobre importaciones reales.
const {chromium}=require(process.env.QA_PLAYWRIGHT||'C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>r.request().url().startsWith(base+'/')?r.fallback():r.abort());
  await locales(page);
  let delay=false;
  const rows=Array.from({length:64},(_,i)=>({id_importacion_feature:1064+i,indice_feature:i,estado:'valido',estado_conciliacion:[11,46,63].includes(i)?'sin_coincidencia':'candidato',atributos_originales:{NombreNucl:`Núcleo ${i+1}`}}));
  const imports=[{id_importacion:5,id_proyecto:3,nombre_original:'TMQ_NUCLEOS_AGRARIOS.gpkg',tipo_objetivo:'nucleo_agrario_gpkg',activo:true}];
  await page.route('**/api/**',async r=>{
   const req=r.request(),u=new URL(req.url()),p=u.pathname;
   if(!p.startsWith('/api/'))return r.fallback();
   if(req.method()!=='GET'){writes.push(p);return r.abort();}
   const reply=json=>r.fulfill({json,headers:{'X-Total-Count':String(Array.isArray(json)?json.length:0)}});
   if(p==='/api/auth/sesion')return reply({user:{id_usuario:1,rol:'admin',nombre:'Prueba'}});
   if(p==='/api/proyectos')return reply([{id_proyecto:3,nombre_proyecto:'México–Querétaro',activo:true},{id_proyecto:4,nombre_proyecto:'Otro proyecto',activo:true}]);
   if(p.endsWith('/mapa'))return reply({type:'FeatureCollection',features:[{type:'Feature',properties:{tipo:'trazo_proyecto',id:901,nombre:'Trazo oculto'},geometry:{type:'LineString',coordinates:[[-100,20],[-99,21]]}},{type:'Feature',properties:{tipo:'derecho_via_proyecto',id:902,nombre:'DDV de prueba'},geometry:{type:'Polygon',coordinates:[[[-100,20],[-99.99,20],[-99.99,20.01],[-100,20]]]}}]});
   if(p==='/api/proyectos/3/importaciones')return reply(imports);
   if(p==='/api/importaciones/5')return reply(imports[0]);
   if(p==='/api/importaciones/5/features'){
    if(delay)await new Promise(resolve=>setTimeout(resolve,350));
    return reply(rows);
   }
   if(p.endsWith('/geometria'))return reply({type:'Feature',properties:{},geometry:{type:'Polygon',coordinates:[[[-100,20],[-99.99,20],[-99.99,20.01],[-100,20]]]}});
   return reply([]);
  });
  await page.goto(base+'/pages/mapa.html?id_proyecto=3&id_importacion=5&vista=coincidencias');
  await page.locator('#avisoPrevisualizacionGis').waitFor();
  assert.equal(await page.locator('#capaTrazos').count(),0);
  assert.equal(await page.locator('#capaDdv').isChecked(),true);
  const tiposDibujados=await page.evaluate(()=>{const tipos=[];const original=L.geoJSON;L.geoJSON=function(geo,...args){if(geo?.properties?.tipo)window.__qaTipos.push(geo.properties.tipo);return original.call(this,geo,...args);};window.__qaTipos=tipos;return tipos;});
  assert.match(await page.locator('#avisoPrevisualizacionGis').innerText(),/61 geometrías.*Sin coincidencia: 3/);
  assert.match(await page.locator('#avisoPrevisualizacionGis').innerText(),/no confirma ni reemplaza/);
  assert.match(await page.locator('#mapaDetalleConciliacion').innerText(),/Resumen cartográfico/);
  assert.equal(await page.locator('#mapaDetalleConciliacion details').count(),0);
  assert.match(await page.locator('#mapaDetalleConciliacion').innerText(),/Núcleos con geometría\s+0/);
  const capa=page.locator('#capaNucleos');
  const tren=page.locator('label:has(#capaNucleos) .mapa-tren-estado');
  assert.equal(await tren.count(),1);
  assert.equal(await tren.evaluate(e=>getComputedStyle(e).opacity),'1');
  await capa.uncheck({force:true});
  assert.equal(await tren.evaluate(e=>getComputedStyle(e).opacity),'0.55');
  assert.equal(await tren.evaluate(e=>getComputedStyle(e).filter),'none');
  await capa.focus();await page.keyboard.press('Space');
  assert.equal(await capa.isChecked(),true);
  assert.equal(await tren.evaluate(e=>getComputedStyle(e).opacity),'1');
  console.log('OK: tren iluminado al activar, apagado al desactivar y control por teclado.');
  await page.screenshot({path:'frontend-ssalfer/deploy/qa-mapa-coincidencias-2026-10-12.png',fullPage:true});
  console.log('OK: 61 polígonos en previsualización y 3 casos sin coincidencia, sin confirmar ni activar.');
  const selector=page.locator('#selectorProyectoMapa');
  await selector.selectOption('4');
  await page.waitForFunction(()=>!document.querySelector('#avisoPrevisualizacionGis'));
  await page.waitForFunction(()=>document.querySelector('#mapaDetalleConciliacion').textContent.includes('Resumen cartográfico'));
  assert.equal(await page.locator('#mapaDetalleConciliacion li').count(),0);
  assert.equal(await page.evaluate(()=>window.__qaTipos.includes('trazo_proyecto')),false);
  assert.equal(await page.evaluate(()=>window.__qaTipos.includes('derecho_via_proyecto')),true);
  console.log('OK: trazo no se dibuja, DDV se conserva; cambiar proyecto limpia detalle y capa temporal.');
  await page.goto(base+'/pages/mapa.html?id_proyecto=3');
  await page.locator('#mapaDetalleConciliacion h3').waitFor();delay=true;
  await selector.selectOption('4');
  await page.waitForLoadState('networkidle');
  assert.doesNotMatch(await page.locator('#mapaDetalleConciliacion').innerText(),/Núcleo 12/);
  assert.equal(await page.locator('#avisoPrevisualizacionGis').count(),0);
  assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
  console.log('OK: respuestas tardías no mezclan proyectos; cero escrituras y cero errores JavaScript.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
