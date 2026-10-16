const {chromium}=require('C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],queries=[];
  page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',r=>r.abort());await locales(page);
  await page.route('**/api/**',async r=>{
   const u=new URL(r.request().url()),p=u.pathname;if(!p.startsWith('/api/'))return r.fallback();
   assert.equal(r.request().method(),'GET');let data=[];
   if(p==='/api/auth/sesion')data={user:{id_usuario:1,rol:'admin',nombre:'QA',apellido_paterno:'Pruebas'}};
   else if(p==='/api/proyectos')data=[{id_proyecto:4,nombre_proyecto:'Proyecto QA',activo:true}];
   else if(p.endsWith('/configuracion'))data={srid_trabajo:4326};
   else if(p.endsWith('/revisiones')){
    queries.push(u.search);const s=u.searchParams;
    if(s.get('estado')==='pendiente'&&(!s.get('objetivo')||s.get('objetivo')==='nucleo'))data=[{id_revision:1,objetivo:'nucleo',estado_revision:'pendiente',tipo_cambio:'aparece_en_nueva_version',creado_en:'2026-10-15T12:00:00Z'}];
    await new Promise(resolve=>setTimeout(resolve,s.get('estado')==='revisado'?400:50));
   }
   return r.fulfill({json:data,headers:{'X-Total-Count':String(Array.isArray(data)?data.length:0)}});
  });
  await page.goto(base+'/pages/gestionGeoespacial.html?id_proyecto=4');
  const status=page.locator('[data-revision-estado-consulta]'),state=page.locator('[data-revision-estado]'),layer=page.locator('[data-revision-objetivo]');
  await page.waitForFunction(()=>document.querySelector('[data-revision-estado-consulta]')?.textContent.startsWith('1 revisiones'));
  await state.focus();await state.selectOption('revisado');
  assert.equal(await status.innerText(),'Aplicando filtros…');
  await state.selectOption('pendiente');await layer.selectOption('parcela');
  await page.waitForFunction(()=>document.querySelector('[data-revision-estado-consulta]')?.textContent.startsWith('0 revisiones'));
  await page.waitForTimeout(450);
  assert.match(await status.innerText(),/0 revisiones.*Pendiente.*Parcela/);
  assert.match(await page.locator('[data-revision-resultados]').innerText(),/No hay cambios/);
  await page.locator('[data-revision-restablecer]').click();
  await page.waitForFunction(()=>document.querySelector('[data-revision-estado-consulta]')?.textContent.startsWith('1 revisiones'));
  await layer.focus();await layer.selectOption('nucleo');
  await page.waitForFunction(()=>document.querySelector('[data-revision-estado-consulta]')?.textContent.includes('Núcleo'));
  assert(await layer.evaluate(el=>el===document.activeElement));
  assert(queries.some(q=>q.includes('objetivo=parcela')));assert.deepEqual(errors,[]);
  await status.scrollIntoViewIfNeeded();await page.screenshot({path:'outputs/qa-revisiones-2026-10-15.png'});
  console.log('OK: filtros consultan API, muestran carga/conteos/vacíos, conservan foco, descartan respuestas atrasadas y restablecen pendientes. Cero escrituras.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
