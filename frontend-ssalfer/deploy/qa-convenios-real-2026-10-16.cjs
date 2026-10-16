const {chromium}=require('C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base='http://127.0.0.1:5184',out=path.resolve('outputs/reporte-convenios-2026-10-16');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const context=await browser.newContext({viewport:{width:1600,height:1100}});
 const auth=await context.request.post(base+'/api/auth/sesiones',{headers:{Origin:base},form:{username:process.env.QA_USER,password:process.env.QA_PASSWORD}});assert.equal(auth.status(),200);
 const read=async p=>{const r=await context.request.get(base+'/api/proyectos/3/reportes/convenios/general'+p);assert.equal(r.status(),200);return r.json();};
 const entities=await read('/entidades'),data=await read('/completo');assert(data.completo);
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',r=>r.request().method()==='GET'?r.continue():r.abort());
 await page.goto(base+'/pages/reportesConvenios.html?id_proyecto=3');await page.waitForFunction(()=>document.querySelector('#totalReportesConvenios').textContent.includes('registro(s)'));await page.locator('[data-reporte=general]').click();
 await page.waitForFunction(()=>document.querySelector('#totalReportesConvenios').textContent.includes('66 colectivos')).catch(async e=>{console.log(await page.locator('#conveniosReportesError').textContent(),await page.locator('#totalReportesConvenios').textContent(),await page.locator('#generalConvenio_proyecto').inputValue());throw e;});assert.match(await page.locator('#btnExportarReportesConvenios').innerText(),/Excel/);
 await page.locator('#generalConvenio_vista').selectOption('colectivos');await page.waitForFunction(()=>document.querySelector('#theadReportesConvenios').textContent.includes('DESTINO') && document.querySelector('#tbodyReportesConvenios').rows.length>1);assert(await page.locator('#btnConsultarReportesConvenios').isHidden());
 const download=page.waitForEvent('download');await page.locator('#btnExportarReportesConvenios').click();await (await download).saveAs(path.join(out,'Reporte-general-Mexico-Queretaro.xlsx'));
 await page.screenshot({path:path.join(out,'reporte-general-MQ.png'),fullPage:true});assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'qa-real.json'),JSON.stringify({resultado:'OK',individuales:data.individuales.length,colectivos:data.colectivos.length,entidades:entities.entidades,errors,modo:'Solo lectura después de iniciar sesión'},null,2));
 console.log(JSON.stringify({individuales:data.individuales.length,colectivos:data.colectivos.length,entidades:entities.entidades.length,errors}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
