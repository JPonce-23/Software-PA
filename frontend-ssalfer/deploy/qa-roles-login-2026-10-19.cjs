const {chromium}=require('C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 for(const rol of ['admin','operador','visualizador','geografo']) for(const activa of [true,false]){
  const p=await browser.newPage();let sesion=activa;
  await p.route('**/*',r=>r.abort());await locales(p);
  await p.route('**/api/**',r=>{const u=new URL(r.request().url());if(!u.pathname.startsWith('/api/'))return r.fallback();if(u.pathname==='/api/auth/sesiones')sesion=true;return r.fulfill({status:sesion?200:401,json:u.pathname.startsWith('/api/auth/')&&sesion?{user:{id_usuario:1,rol,nombre:'Prueba'}}:[]});});
  await p.goto(base+'/Index.html?return_to=/pages/gestionGeoespacial.html');
  if(!activa){await p.locator('#usuario').fill('prueba@local.invalid');await p.locator('#password').fill('Prueba-simulada');await p.locator('#btnLogin').click();}
  await p.waitForURL('**/'+(['admin','geografo'].includes(rol)?'pages/gestionGeoespacial.html':'dashboard.html'));
  assert.equal(await p.getByText('Acceso no permitido',{exact:true}).count(),0);
  await p.close();
 }
 console.log('OK: 8 recorridos de ingreso y retorno por rol, con sesión previa y nueva; API simulada.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
