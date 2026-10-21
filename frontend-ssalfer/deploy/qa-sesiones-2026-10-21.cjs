/* Pruebas aisladas: navegador real, API simulada, sin credenciales ni escrituras de negocio. */
const {chromium}=require(process.env.QA_PLAYWRIGHT || 'C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'), out=path.resolve(process.env.QA_OUT || 'outputs/sesiones-2026-10-21');
const checks=[];
const fixture=`<!doctype html><html lang="es" data-role="admin operador visualizador geografo"><head><script src="/js/utils/proteccion.js"></script><script src="/js/utils/permisos.js"></script><link rel="stylesheet" href="/styles/marco.css"></head><body>
<aside class="aside" style="width:280px;height:550px"><button class="usuario-btn" style="margin-top:380px">Mi cuenta</button><div class="opciones-usuario"></div></aside>
<main><form><label>Nombre <input name="nombre"></label></form><a id="negocio" href="#">Ayuda sobre cerrar sesión</a><button id="normal">Continuar</button><p id="resultado"></p></main>
<script>window.SSALFER_CONFIG={API_BASE_URL:'/api'};</script><script src="/js/api/cliente.js"></script><script src="/js/api/auth.js"></script><script src="/js/utils/marco.js"></script></body></html>`;
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost');
 if(u.pathname==='/pages/prueba.html'){res.setHeader('Content-Type','text/html; charset=utf-8');return res.end(fixture);}
 if(u.pathname==='/Index.html'){res.setHeader('Content-Type','text/html');return res.end('<h1>Inicio de sesión de prueba</h1>');}
 const file=path.resolve(root,'.'+decodeURIComponent(u.pathname));
 if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end();}
 res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.html':'text/html'})[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));
});
(async()=>{
 console.log('Iniciando servidor de pruebas');
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
 console.log('Servidor listo',base);
 fs.mkdirSync(out,{recursive:true});const browser=await chromium.launch({channel:'msedge',headless:true});
 console.log('Navegador listo');
 try{
  async function setup({status=200,viewport={width:1366,height:900}}={}){
   const context=await browser.newContext({viewport}), state={session:status,logout:200,count:0,business:200,delay:0,network:false},errors=[];
   await context.route('**/api/**',async route=>{
    const p=new URL(route.request().url()).pathname;
    if(!p.startsWith('/api/')) return route.fallback();
    if(p==='/api/auth/sesion')return state.session===0?route.abort():route.fulfill({status:state.session,json:state.session===200?{user:{id_usuario:1,rol:'admin',nombre:'Prueba'},expira_en:'2099-01-01T00:00:00Z'}:{detail:'Acceso rechazado'}});
    if(p==='/api/auth/logout'||p==='/api/auth/logout-todas'){
     state.count++;if(state.delay)await new Promise(r=>setTimeout(r,state.delay));
     if(state.network)return route.abort();
     return route.fulfill({status:state.logout,json:{detail:state.logout===200?'Sesión cerrada':'CSRF no válido'}});
    }
    if(state.network)return route.abort();
    return route.fulfill({status:state.business,json:state.business===200?[]:{detail:state.business===403?'CSRF no válido':'Error de prueba'}});
   });
   const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
   await page.goto(base+'/pages/prueba.html');await page.waitForLoadState('networkidle');
   if(errors.length)throw new Error(errors.join(' | '));
   if(state.session===200) await page.waitForFunction(()=>document.documentElement.dataset.rolActual,{},{timeout:3000});
   return {context,page,state,errors};
  }
  async function run(name,fn,opts){const s=await setup(opts);try{await fn(s);assert.deepEqual(s.errors,[]);checks.push(name);console.log('OK',name);}finally{await s.context.close();}}
  const abrir=async p=>{await p.locator('.usuario-btn').click();await p.locator('[data-action="logout"]').waitFor({state:'visible'});};
  await run('Texto de negocio y clic sintético no cierran sesión',async({page,state})=>{
   await page.locator('#negocio').click();await abrir(page);
   await page.locator('[data-action="logout"]').evaluate(el=>el.click());
   await page.evaluate(()=>document.dispatchEvent(new MouseEvent('click',{bubbles:true})));
   assert.equal(state.count,0);assert.ok(page.url().includes('prueba.html'));
  });
  await run('Evento cancelado no cierra sesión',async({page,state})=>{
   await abrir(page);await page.locator('[data-action="logout"]').evaluate(el=>el.addEventListener('click',e=>e.preventDefault()));
   await page.locator('[data-action="logout"]').click();assert.equal(state.count,0);
  });
  await run('Doble clic: un solo POST y regreso a inicio',async({page,state})=>{
   state.delay=500;await abrir(page);await page.locator('[data-action="logout"]').dblclick();await page.waitForURL('**/Index.html');assert.equal(state.count,1);
  });
  for(const key of ['Enter','Space'])await run('Cerrar sesión con teclado '+key,async({page,state})=>{
   await abrir(page);await page.locator('[data-action="logout"]').focus();await page.keyboard.press(key);await page.waitForURL('**/Index.html');assert.equal(state.count,1);
  });
  await run('Escape, foco, límites del menú y botón sin superposición',async({page})=>{
   await abrir(page);assert.equal(await page.locator('[data-action="cambiar-contrasena"]').evaluate(el=>el===document.activeElement),true);
   const box=await page.locator('.ssalfer-menu-usuario').boundingBox(),button=await page.locator('.usuario-btn').boundingBox();
   assert.ok(box.x>=0&&box.x+box.width<=1366&&box.y>=0&&box.y+box.height<=900);assert.ok(box.y+box.height<=button.y);
   await page.screenshot({path:path.join(out,'menu-escritorio.png')});
   await page.keyboard.press('Escape');assert.equal(await page.locator('.usuario-btn').getAttribute('aria-expanded'),'false');
   assert.equal(await page.locator('.usuario-btn').evaluate(el=>el===document.activeElement),true);
  });
  await run('Menú móvil visible dentro de la pantalla',async({page})=>{
   await page.getByRole('button',{name:'Mostrar menú',exact:true}).click();await abrir(page);
   const box=await page.locator('.ssalfer-menu-usuario').boundingBox();assert.ok(box.x>=0&&box.x+box.width<=390&&box.y>=0&&box.y+box.height<=844);
   await page.screenshot({path:path.join(out,'menu-movil.png')});
  },{viewport:{width:390,height:844}});
  for(const status of [403,500,0])await run('Comprobación inicial '+status+' conserva URL y permite reintento',async({page,state})=>{
   await page.getByRole('button',{name:'Reintentar',exact:true}).waitFor();assert.ok(page.url().includes('prueba.html'));assert.equal(state.count,0);
   state.session=200;await page.getByRole('button',{name:'Reintentar',exact:true}).click();await page.locator('#normal').waitFor();
  },{status});
  await run('401 inicial exige inicio de sesión',async({page,state})=>{assert.ok(page.url().includes('/Index.html?return_to='));assert.equal(state.count,0);},{status:401});
  for(const status of [403,500,0])await run('Petición '+status+' conserva sesión y datos',async({page,state})=>{
   await page.locator('[name="nombre"]').fill('Dato de prueba');state.business=status||200;state.network=status===0;
   const result=await page.evaluate(()=>ClienteAPI.get('/prueba').catch(e=>({status:e.status,message:e.message})));
   assert.equal(result.status,status);assert.equal(await page.locator('[name="nombre"]').inputValue(),'Dato de prueba');assert.ok(page.url().includes('prueba.html'));assert.equal(state.count,0);
  });
  await run('401 con edición: aviso único, conserva DOM y bloquea nuevas operaciones',async({page,state})=>{
   await page.locator('[name="nombre"]').fill('Dato de prueba');state.business=401;
   await page.evaluate(()=>Promise.allSettled([ClienteAPI.get('/prueba'),ClienteAPI.get('/prueba')]));
   await page.getByRole('dialog').waitFor();assert.equal(await page.locator('dialog').count(),1);assert.equal(await page.locator('[name="nombre"]').inputValue(),'Dato de prueba');
   assert.equal(await page.evaluate(()=>ClienteAPI.post('/prueba',{}).catch(e=>e.status)),401);
   await page.screenshot({path:path.join(out,'sesion-terminada-formulario.png')});
   await page.getByRole('button',{name:'Ir al inicio de sesión'}).click();await page.waitForURL('**/Index.html?return_to=*');assert.equal(state.count,0);
  });
  await run('Cierre cancelado con formulario no envía logout',async({page,state})=>{
   await page.locator('[name="nombre"]').fill('Dato de prueba');page.on('dialog',d=>d.dismiss());await abrir(page);await page.locator('[data-action="logout"]').click();assert.equal(state.count,0);
  });
  await run('Fallo de logout permite reintento sin redirigir',async({page,state})=>{
   state.logout=403;await abrir(page);await page.locator('[data-action="logout"]').click();await page.getByRole('alert').waitFor();assert.ok(page.url().includes('prueba.html'));
   state.logout=200;await page.locator('[data-action="logout"]').click();await page.waitForURL('**/Index.html');assert.equal(state.count,2);
  });
  await run('Dos pestañas: un POST, aviso en la pestaña editada',async({page,context,state})=>{
   const otra=await context.newPage();await otra.goto(base+'/pages/prueba.html');await otra.locator('[name="nombre"]').fill('Dato de prueba');
   await abrir(page);await page.locator('[data-action="logout"]').click();await page.waitForURL('**/Index.html');await otra.getByRole('dialog').waitFor();assert.equal(state.count,1);
   assert.equal(await otra.locator('[name="nombre"]').inputValue(),'Dato de prueba');
  });
  await run('Carga repetida de auth.js no duplica manejadores',async({page,state})=>{
   await page.addScriptTag({url:base+'/js/api/auth.js'});state.delay=100;await abrir(page);await page.locator('[data-action="logout"]').click();await page.waitForURL('**/Index.html');assert.equal(state.count,1);
  });
  await run('401 de login no invalida la página como una sesión vencida',async({page,state})=>{
   state.business=401;
   assert.equal(await page.evaluate(()=>AuthAPI.login('prueba','incorrecta').catch(e=>e.status)),401);
   assert.equal(await page.evaluate(()=>!!window.SSALFER_SESION_INVALIDA),false);assert.ok(page.url().includes('prueba.html'));
  });
  await run('Cookie CSRF y credenciales incluidas; 403 conserva detalle',async({page,context,state})=>{
   await context.addCookies([{name:'pa_csrf_dev',value:'token-sintetico',url:base}]);state.business=403;
   const sent=page.waitForRequest(r=>new URL(r.url()).pathname==='/api/prueba');
   const result=await page.evaluate(()=>ClienteAPI.post('/prueba',{dato:'prueba'}).catch(e=>({status:e.status,detail:e.detail})));
   const request=await sent;assert.equal(request.headers()['x-csrf-token'],'token-sintetico');
   assert.ok((await request.allHeaders()).cookie.includes('pa_csrf_dev=token-sintetico'));
   assert.deepEqual(result,{status:403,detail:'CSRF no válido'});assert.equal(state.count,0);
  });
  await run('Cancelar una consulta conserva AbortError y no cierra sesión',async({page,state})=>{
   const name=await page.evaluate(async()=>{const c=new AbortController();c.abort();try{await ClienteAPI.get('/prueba',{signal:c.signal});}catch(e){return e.name;}});
   assert.equal(name,'AbortError');assert.equal(state.count,0);assert.ok(page.url().includes('prueba.html'));
  });
  await run('401 de cambio de contraseña exige autenticación sin enviar logout',async({page,state})=>{
   state.business=401;
   await page.evaluate(()=>AuthAPI.cambiarContrasena('prueba','otra').catch(()=>null)).catch(()=>{});
   await page.waitForURL('**/Index.html?return_to=*');assert.equal(state.count,0);
  });
  fs.writeFileSync(path.join(out,'resultados.json'),JSON.stringify({date:new Date().toISOString(),tipo:'Navegador real con API simulada',checks},null,2));
  console.log('TOTAL',checks.length);
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
