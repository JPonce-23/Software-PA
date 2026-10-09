const {chromium}=require(process.env.QA_PLAYWRIGHT||'C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base='http://127.0.0.1:5184',root=path.resolve('frontend-ssalfer');
async function locales(page){await page.route(base+'/**',async route=>{const u=new URL(route.request().url());if(u.pathname.startsWith('/api/'))return route.fallback();const file=path.resolve(root,'.'+decodeURIComponent(u.pathname));if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||fs.statSync(file).isDirectory())return route.fallback();const mime={'.js':'text/javascript','.css':'text/css','.html':'text/html','.png':'image/png','.svg':'image/svg+xml','.jpg':'image/jpeg','.woff2':'font/woff2'}[path.extname(file)];return route.fulfill({body:fs.readFileSync(file),contentType:mime||'application/octet-stream'});});}
async function main(){const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const context=await browser.newContext({viewport:{width:1440,height:1000}});const auth=await context.request.post(base+'/api/auth/sesiones',{headers:{Origin:base},form:{username:process.env.QA_USER,password:process.env.QA_PASSWORD}});assert.equal(auth.status(),200);
 const page=await context.newPage(),errores=[],writes=[];page.on('pageerror',e=>errores.push(e.message));page.on('dialog',d=>{errores.push('Diálogo nativo: '+d.message());d.dismiss();});
 await page.route('**/api/**',route=>{if(route.request().method()!=='GET'){writes.push(route.request().url());return route.abort();}return route.continue();});await locales(page);
 for(const url of ['/pages/documentos.html?id_proyecto_nucleo=150','/pages/derechosColectivos.html?id_proyecto_nucleo=150','/pages/fichaProyecto.html?id=4','/pages/nucleoAgrario.html?id_proyecto_nucleo=150','/pages/persona.html?id_proyecto=4&id_proyecto_nucleo=150','/pages/gestionGeoespacial.html?id_proyecto=4']){
   await page.goto(base+url);await page.waitForLoadState('networkidle');assert.equal(await page.locator('footer').innerText(),'© 2026 Procuraduría Agraria. Todos los derechos reservados.');console.log('LECTURA',url);if(errores.length)throw Error(JSON.stringify(errores));
 }
 await page.getByRole('button',{name:'Cambiar sistema de coordenadas',exact:true}).click();await page.getByRole('dialog').locator('[name="habitual"]').selectOption('32614');await page.getByRole('dialog').getByRole('button',{name:'Guardar',exact:true}).click();await page.getByRole('dialog').locator('[role="alert"]').waitFor({state:'visible'});await page.keyboard.press('Escape');
 await page.setViewportSize({width:390,height:844});await page.reload();await page.waitForLoadState('networkidle');await page.screenshot({path:'frontend-ssalfer/deploy/qa-gis-ux-movil-2026-10-06.png',fullPage:true});
 assert.deepEqual(errores,[]);console.log('LECTURAS_OK, escrituras interceptadas:',writes.length);
}finally{await browser.close();}}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={locales,base};
