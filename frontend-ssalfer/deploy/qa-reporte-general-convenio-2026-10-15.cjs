const {chromium}=require('C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const p=await browser.newPage({viewport:{width:1600,height:1100}}),requests=[],errors=[];
 p.on('pageerror',e=>errors.push(e.message));await p.route('**/*',r=>r.abort());await locales(p);
 await p.route('**/api/**',async r=>{
  const u=new URL(r.request().url());if(!u.pathname.startsWith('/api/'))return r.fallback();
  assert.equal(r.request().method(),'GET');requests.push(u.pathname);let data=[];
  if(u.pathname==='/api/auth/sesion')data={user:{id_usuario:1,rol:'admin',nombre:'QA',apellido_paterno:'Pruebas'}};
  else if(u.pathname==='/api/proyectos')data=[{id_proyecto:4,nombre_proyecto:'Proyecto QA',activo:true}];
  if(u.pathname.includes('/reportes/'))await new Promise(resolve=>setTimeout(resolve,250));
  return r.fulfill({json:data});
 });
 await p.goto(base+'/pages/reportesConvenios.html?id_proyecto=4');
 await p.waitForFunction(()=>document.querySelector('#reporteConvenioFiltro_id_proyecto')?.options.length===2);
 await p.locator('[data-reporte=general]').click();const count=requests.length;await p.waitForTimeout(400);
 assert.equal(requests.length,count);
 assert(await p.locator('#reporteGeneralEstado').isDisabled());
 assert.equal(await p.locator('#reporteGeneralEstado option').count(),1);
 assert.equal(await p.locator('#reporteConvenioFiltro_id_proyecto').inputValue(),'4');
 assert(await p.locator('#btnExportarReportesConvenios').isDisabled());
 assert.match(await p.locator('#btnExportarReportesConvenios').innerText(),/Excel/);
 assert(await p.locator('#btnConsultarReportesConvenios').isDisabled());
 assert.equal(await p.locator('#theadReportesConvenios th').count(),12);
 assert.match(await p.locator('#tbodyReportesConvenios').innerText(),/aún no está disponible/);
 await p.locator('[data-reporte=general]').scrollIntoViewIfNeeded();
 await p.screenshot({path:'outputs/convenios-general-2026-10-15/pestana-reporte-general.png',fullPage:true});
 for(const tab of ['valores','impactos','periodo','cobertura']){
  await p.locator(`[data-reporte="${tab}"]`).click();await p.waitForTimeout(350);
  assert.match(await p.locator('#btnExportarReportesConvenios').innerText(),/CSV/);
  assert(!(await p.locator('#btnConsultarReportesConvenios').isDisabled()));
  assert.equal(await p.locator('#reporteGeneralEstado').count(),0);
 }
 assert.deepEqual(errors,[]);
 console.log('OK: bloqueo claro, 12 columnas, proyecto seleccionado, estado deshabilitado, cero solicitudes desde pestaña nueva; cuatro pestañas existentes conservan CSV y consulta. Sin errores JavaScript.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
