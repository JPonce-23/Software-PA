// Prueba la protección compartida sobre el HTML real de cada pantalla, aislada de sus consultas de negocio.
const {chromium}=require(process.env.QA_PLAYWRIGHT || 'C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
const root=path.resolve('frontend-ssalfer'),out=path.resolve('outputs/roles-2026-10-19');
const paginas=['dashboard.html',...fs.readdirSync(path.join(root,'pages')).filter(p=>p.endsWith('.html')).map(p=>'pages/'+p)];
const admin=new Set(['usuarios.html','catalogosOperativos.html','auditoria.html','nuevoProyecto.html']);
(async()=>{fs.mkdirSync(out,{recursive:true});const browser=await chromium.launch({channel:'msedge',headless:true});let comprobaciones=0;try{
 for(const rol of ['admin','operador','visualizador','geografo','desconocido']){
  const page=await browser.newPage();const escrituras=[];
  await page.route('**/*',r=>r.abort());await locales(page);
  await page.route('**/*.html',async r=>{
   const p=new URL(r.request().url()).pathname.slice(1),file=path.join(root,p);
   let html=fs.readFileSync(file,'utf8');
   html=html.replace(/<script\b([^>]*)>[\s\S]*?<\/script>/gi,(tag,a)=>/src="\/(js\/(utils\/(permisos|proteccion)|api\/(cliente|auth)|env|config)\.js)"/.test(a)?tag:'');
   await r.fulfill({contentType:'text/html; charset=utf-8',body:html});
  });
  await page.route('**/api/**',r=>{if(!new URL(r.request().url()).pathname.startsWith('/api/'))return r.fallback();if(r.request().method()!=='GET')escrituras.push(new URL(r.request().url()).pathname);return r.fulfill({json:new URL(r.request().url()).pathname.endsWith('/auth/sesion')?{user:{id_usuario:1,rol}}:{}});});
  for(const p of paginas){
   console.log(rol,p);await page.goto(base+'/'+p);await page.waitForFunction(()=>document.documentElement.dataset.rolActual || document.body.textContent.includes('Acceso no permitido'),{},{timeout:10000}).catch(async e=>{console.log(await page.evaluate(()=>({body:document.body.innerText.slice(0,200),scripts:[...document.scripts].map(s=>s.src),permisos:!!window.SSALFER_PERMISOS,auth:!!window.AuthAPI})));throw e;});
   const name=path.basename(p),permitido=rol!=='desconocido'&&(!admin.has(name)||rol==='admin')&&(!['nuevoConvenio.html','tramiteRan.html'].includes(name)||['admin','operador'].includes(rol))&&(name!=='gestionGeoespacial.html'||['admin','geografo'].includes(rol))&&(rol!=='geografo'||['dashboard.html','fichaProyecto.html','nucleoAgrario.html','parcela.html','mapa.html','gestionGeoespacial.html','cambiarContrasena.html'].includes(name));
   assert.equal(await page.getByText('Acceso no permitido',{exact:true}).count(),permitido?0:1,`${rol}: ${p}`);
   if(permitido){
    const visibles=await page.locator('[data-role]').evaluateAll(nodes=>nodes.filter(n=>n.getClientRects().length&&getComputedStyle(n).display!=='none').map(n=>n.dataset.role));
    assert(visibles.every(r=>rol==='admin'||r.split(' ').includes(rol)),`${rol}: control ajeno en ${p}`);
   }comprobaciones++;
  }
  if(rol==='desconocido'){await page.close();continue;}
  await page.goto(base+'/dashboard.html');await page.evaluate(()=>window.SSALFER_SESION_LISTA);
  await page.evaluate(()=>{const s=document.createElement('section');s.innerHTML='<a id="enlacePrueba" href="/pages/usuarios.html">Usuarios</a><button id="capturaPrueba" data-role="admin operador">Capturar</button><button id="gisPrueba" data-role="admin geografo">Cartografía</button>';document.body.append(s);});
  assert.equal(await page.locator('#enlacePrueba').isVisible(),rol==='admin');
  assert.equal(await page.locator('#capturaPrueba').isVisible(),['admin','operador'].includes(rol));
  assert.equal(await page.locator('#gisPrueba').isVisible(),['admin','geografo'].includes(rol));
  const pruebas=[['/personas','POST',['admin','operador']],['/proyectos','POST',['admin']],['/importaciones/1/confirmar','POST',['admin','geografo']],['/personas/1','DELETE',['admin']],['/orv-integrantes/1/reactivar','POST',['admin']],['/proyectos/1/nucleos','POST',['admin','operador']]];
  for(const [ruta,metodo,permitidos]of pruebas){const antes=escrituras.length;const status=await page.evaluate(async({ruta,metodo})=>{try{await window.ClienteAPI.post(ruta,{}, {metodo});return 200;}catch(e){return e.status;}},{ruta,metodo});assert.equal(status,permitidos.includes(rol)?200:403);assert.equal(escrituras.length-antes,permitidos.includes(rol)?1:0);comprobaciones++;}
  await page.screenshot({path:path.join(out,`${rol}.png`),fullPage:true});await page.close();
 }
 fs.writeFileSync(path.join(out,'resultado.json'),JSON.stringify({pantallas:paginas.length,comprobaciones,resultado:'OK',alcance:'HTML real + protección y cliente compartidos; API simulada; sin escrituras reales'},null,2));
 console.log(`OK: ${paginas.length} pantallas, cuatro roles y rol desconocido, ${comprobaciones} comprobaciones, controles dinámicos y peticiones de escritura.`);
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
