// Datos simulados: ninguna solicitud llega al backend real.
const {chromium}=require('C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],pages=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>r.abort());await locales(page);
  const project={id_proyecto:4,nombre_proyecto:'Proyecto de prueba UX',clave_proyecto:'QA',activo:true};
  const nuclei=Array.from({length:205},(_,i)=>({id_proyecto_nucleo:i+1,id_nucleo:i+1,nombre_nucleo:i===204?'San Sebastián de las Barrancas':`Núcleo de prueba ${i+1}`,municipio:'San Juan del Río',entidad:'Querétaro',total_parcelas:3,total_afectaciones:2}));
  await page.route('**/api/**',route=>{
   const u=new URL(route.request().url()),p=u.pathname;
   if(!p.startsWith('/api/'))return route.fallback();
   assert.equal(route.request().method(),'GET');
   let data=[];
   if(p==='/api/auth/sesion')data={user:{id_usuario:1,rol:'admin',nombre:'QA',apellido_paterno:'Pruebas'}};
   else if(p==='/api/proyectos')data=[project];
   else if(p==='/api/proyectos/4')data=project;
   else if(p==='/api/proyectos/4/nucleos'){const skip=Number(u.searchParams.get('skip')||0),limit=Number(u.searchParams.get('limit')||100);pages.push(skip);data=nuclei.slice(skip,skip+limit);}
   return route.fulfill({json:data});
  });
  await page.goto(base+'/pages/fichaProyecto.html?id=4');
  try {await page.waitForFunction(()=>document.querySelector('#kpiNucleos')?.textContent==='205',{},{timeout:10000});}
  catch(e){console.log({errors,pages,url:page.url(),text:(await page.locator('body').innerText()).slice(-2500)});throw e;}
  assert(await page.locator('#resumenProyecto').isVisible());assert(!(await page.locator('#nucleosAgrarios').isVisible()));
  await page.locator('#tabResumenProyecto').focus();await page.keyboard.press('ArrowRight');
  assert(await page.locator('#nucleosAgrarios').isVisible());assert(!(await page.locator('#resumenProyecto').isVisible()));
  assert.equal(await page.locator('#nucleosGrid').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length),4);
  await page.locator('#buscarNucleoProyecto').fill('sebastian');
  assert.match(await page.locator('#resultadoBusquedaNucleos').innerText(),/^1 de 205/);
  assert.equal(await page.locator('#kpiNucleos').textContent(),'205');
  assert.match(await page.locator('#nucleosGrid').innerText(),/San Sebastián/);
  await page.locator('#limpiarBusquedaNucleos').click();
  assert.match(await page.locator('#resultadoBusquedaNucleos').innerText(),/^205 de 205/);
  await page.screenshot({path:'outputs/qa-ficha-proyecto-2026-10-15.png'});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.locator('#nucleosGrid').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length),1);
  await page.locator('#buscarNucleoProyecto').fill('sin resultado');
  assert.match(await page.locator('#nucleosGrid').innerText(),/No hay núcleos/);
  await page.screenshot({path:'outputs/qa-ficha-proyecto-movil-2026-10-15.png'});
  assert(pages.includes(200));assert.deepEqual(errors,[]);
  console.log('OK: 205 núcleos, segunda página, pestañas por teclado, búsqueda sin acentos, KPI sin alteración, 4/1 columnas y cero errores JavaScript.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
