const {chromium}=require(process.env.QA_PLAYWRIGHT||'C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 for(const rol of ['admin','operador','visualizador','geografo']){
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>r.abort());await locales(page);
  await page.route('**/api/**',r=>{
   const p=new URL(r.request().url()).pathname;if(!p.startsWith('/api/'))return r.fallback();assert.equal(r.request().method(),'GET');
   const proyecto={id_proyecto:4,nombre_proyecto:'Proyecto de prueba de roles',activo:true};
   const json=p==='/api/auth/sesion'?{user:{id_usuario:1,rol,nombre:'Prueba'}}:p==='/api/proyectos'?[proyecto]:p==='/api/proyectos/4'?proyecto:[];
   return r.fulfill({json});
  });
  await page.goto(base+'/pages/fichaProyecto.html?id=4');await page.waitForFunction(()=>document.querySelector('#kpiNucleos').textContent==='0');
  await page.locator('#tabNucleosProyecto').click();
  assert.equal(await page.locator('#btnEditarProyecto').isVisible(),rol==='admin');
  assert.equal(await page.locator('#btnAgregarNucleo').isVisible(),['admin','operador'].includes(rol));
  if(['admin','operador'].includes(rol)){
   await page.locator('#btnAgregarNucleo').click();await page.locator('#formNuevoNucleo').waitFor();
   assert.equal(await page.locator('#nucleoAltaExcepcional').isVisible(),rol==='admin');
   assert(await page.locator('#btnBuscarNucleoRan').isVisible());
  }
  assert.deepEqual(errors,[]);await page.screenshot({path:`outputs/roles-2026-10-19/proyecto-${rol}.png`,fullPage:true});await page.close();
 }
 console.log('OK: ficha del proyecto completa, los cuatro roles, vinculación de núcleos para operador y alta excepcional solo admin. Sin escrituras.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
