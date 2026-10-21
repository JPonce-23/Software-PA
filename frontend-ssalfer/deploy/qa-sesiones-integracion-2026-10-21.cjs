/* Solo contra una copia QA. Credenciales por entorno, nunca en archivos de evidencia. */
const {chromium}=require(process.env.QA_PLAYWRIGHT || 'C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base=process.env.QA_BASE, password=process.env.QA_PASSWORD;
if(!base||!password||!process.env.QA_USERS)throw Error('Indica QA_BASE, QA_PASSWORD y QA_USERS de una copia de pruebas.');
const out=path.resolve('outputs/sesiones-2026-10-21'),resultados=[];
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 for(const username of process.env.QA_USERS.split(',')){
  console.log('Probando acceso y navegación en copia QA');
  const context=await browser.newContext({viewport:{width:1366,height:900}}),page=await context.newPage();let cierres=0;const errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).pathname==='/api/auth/logout')cierres++;});
  await page.goto(base+'/Index.html');await page.locator('#usuario').fill(username);await page.locator('#password').fill(password);await page.locator('#btnLogin').click();
  await page.waitForURL('**/dashboard.html');console.log('Login completado');await page.waitForFunction(()=>document.documentElement.dataset.rolActual);await page.locator('.usuario-btn').waitFor({state:'visible'});
  const rol=await page.locator('html').getAttribute('data-rol-actual');console.log('Dashboard',rol);
  await page.reload();await page.waitForFunction(()=>document.documentElement.dataset.rolActual);await page.locator('.usuario-btn').waitFor({state:'visible'});
  await page.goto(base+'/pages/mapa.html');await page.waitForFunction(()=>document.documentElement.dataset.rolActual);await page.locator('.usuario-btn').waitFor({state:'visible'});
  await page.goBack();await page.waitForFunction(()=>document.documentElement.dataset.rolActual);await page.locator('.usuario-btn').waitFor({state:'visible'});
  await page.locator('.usuario-btn').click();await page.locator('.ssalfer-menu-usuario').screenshot({path:path.join(out,'menu-real-'+rol+'.png')});
  assert.equal(await page.locator('[data-action="logout"]').evaluate(e=>e.tagName),'BUTTON');
  await page.locator('[data-action="logout"]').focus();await page.keyboard.press('Enter');await page.waitForURL(url=>url.pathname==='/Index.html');assert.equal(cierres,1);
  const status=await (await context.request.get(base+'/api/auth/sesion')).status();assert.equal(status,401);assert.deepEqual(errors,[]);
  resultados.push({rol,login:true,recarga:true,navegacionMapa:true,volver:true,logoutPeticiones:cierres,estadoSesionDespues:status,errores:errors});console.log('OK real',rol);
  await context.close();
 }
 fs.writeFileSync(path.join(out,'sesiones-reales-qa.json'),JSON.stringify({fecha:new Date().toISOString(),base,resultados},null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
