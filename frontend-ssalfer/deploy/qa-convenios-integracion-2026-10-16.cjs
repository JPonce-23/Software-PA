const {chromium}=require('C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
const out=path.resolve('outputs/reporte-convenios-2026-10-16');
const fixture=JSON.parse(fs.readFileSync('docs/examples/reporte_general_convenios.json','utf8'));
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[],calls=[];
 let modo='normal',descargas=0;page.on('pageerror',e=>errors.push(e.message));page.on('download',()=>descargas++);
 await page.route('**/*',r=>r.abort());await locales(page);
 await page.route('**/api/**',async route=>{
  const u=new URL(route.request().url()),p=u.pathname;if(!p.startsWith('/api/'))return route.fallback();
  assert.equal(route.request().method(),'GET');calls.push(p+u.search);let data=[];
  if(p==='/api/auth/sesion')data={user:{id_usuario:1,rol:'visualizador',nombre:'QA',apellido_paterno:'Reporte'}};
  else if(p==='/api/proyectos')data=[{id_proyecto:42,nombre_proyecto:'Proyecto sintético QA',activo:true},{id_proyecto:43,nombre_proyecto:'Proyecto sin acceso',activo:true}];
  else if(p.includes('/reportes/convenios/general')){
   if(p.includes('/43/'))return route.fulfill({status:403,json:{detail:'Sin acceso'}});
   if(p.endsWith('/entidades'))data={id_proyecto:42,entidades:[{id_entidad:1,estado:'Entidad sintética A',individuales:4,colectivos:2},{id_entidad:2,estado:'Entidad sólo colectivos',individuales:0,colectivos:2}]};
   else{
    if(p.endsWith('/completo')&&modo==='limite')return route.fulfill({status:413,json:{detail:{codigo:'REPORTE_EXCEDE_LIMITE',mensaje:'Acote filtros'}}});
    data=structuredClone(fixture);data.completo=p.endsWith('/completo');
    if(u.searchParams.get('id_entidad')==='2')data.individuales=[];
    if(modo==='vacio'){data.individuales=[];data.colectivos=[];}
    for(const g of ['individuales','colectivos'])data['paginacion_'+g]={pagina:1,tamano_pagina:50,total:data[g].length,hay_mas:false};
    if(modo==='incompleto'&&data.completo)data.paginacion_colectivos.total++;
   }
  }
  return route.fulfill({json:data});
 });
 await page.goto(base+'/pages/reportesConvenios.html?id_proyecto=42');await page.locator('[data-reporte=general]').click();
 await page.waitForFunction(()=>document.querySelector('#totalReportesConvenios').textContent.includes('1 convenios individuales'));
 assert.equal(await page.locator('#generalConvenio_entidad option').count(),3);
 assert.match(await page.locator('#theadReportesConvenios').innerText(),/N\u00daCLEO AGRARIO/);
 assert.match(await page.locator('#paginaReportesConvenios').innerText(),/P\u00e1gina/);
 assert(!/[\u00c3\u00c2]|\u00e2\u20ac/.test(await page.locator('#tbodyReportesConvenios').innerText()));

 assert.match(await page.locator('#tbodyReportesConvenios').innerText(),/0007/);
 const download=page.waitForEvent('download');await page.locator('#btnExportarReportesConvenios').click();await (await download).saveAs(path.join(out,'Convenios-QA-integracion.xlsx'));
 await page.locator('#generalConvenio_entidad').selectOption('2');await page.waitForFunction(()=>document.querySelector('#totalReportesConvenios').textContent.includes('0 convenios individuales'));
 assert(!(await page.locator('#btnExportarReportesConvenios').isDisabled()));
 const colectivos=page.waitForEvent('download');await page.locator('#btnExportarReportesConvenios').click();await (await colectivos).saveAs(path.join(out,'Convenios-QA-solo-colectivos.xlsx'));
 assert(calls.some(c=>c.includes('/completo?id_entidad=2')));
 for(const m of ['limite','incompleto']){modo=m;await page.locator('#btnExportarReportesConvenios').click();await page.locator('#conveniosReportesError').waitFor({state:'visible'});assert.match(await page.locator('#conveniosReportesError').innerText(),m==='limite'?/10,000/:/incompleta/);}
 assert.equal(descargas,2);
 modo='vacio';await page.locator('#generalConvenio_entidad').selectOption('');await page.waitForFunction(()=>document.querySelector('#totalReportesConvenios').textContent.includes('0 colectivos'));assert(await page.locator('#btnExportarReportesConvenios').isDisabled());
 await page.locator('#generalConvenio_proyecto').selectOption('43');await page.locator('#conveniosReportesError').waitFor({state:'visible'});assert.match(await page.locator('#conveniosReportesError').innerText(),/No tienes acceso/);
 modo='normal';await page.locator('#generalConvenio_proyecto').selectOption('42');await page.waitForFunction(()=>document.querySelector('#totalReportesConvenios').textContent.includes('1 convenios individuales'));
 await page.locator('#generalConvenio_vista').selectOption('colectivos');
 await page.waitForFunction(()=>document.querySelector('#theadReportesConvenios').textContent.includes('DESTINO'));
 assert(await page.locator('#btnConsultarReportesConvenios').isHidden());
 await page.locator('#busquedaReportesConvenios').fill('NO_EXISTE_123');
 assert.match(await page.locator('#tbodyReportesConvenios').innerText(),/No hay coincidencias/);
 await page.locator('#busquedaReportesConvenios').fill('');
 assert((await page.locator('#tbodyReportesConvenios tr').count())>1);

 await page.screenshot({path:path.join(out,'reporte-general-integrado.png'),fullPage:true});
 for(const tab of ['valores','impactos','periodo','cobertura']){await page.locator(`[data-reporte=${tab}]`).click();assert.match(await page.locator('#btnExportarReportesConvenios').innerText(),/CSV/);}
 assert.deepEqual(errors,[]);assert(!calls.some(c=>/^\/api\/(convenios|afectaciones|parcelas)\//.test(c)));
 fs.writeFileSync(path.join(out,'qa-simulada.json'),JSON.stringify({resultado:'OK',descargas,calls,errors},null,2));
 console.log('OK: contrato real simulado, roles lectura, entidades de colectivos, XLSX ambas hojas, vacío, 403, 413, respuesta incompleta sin descarga y CSV anterior.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
