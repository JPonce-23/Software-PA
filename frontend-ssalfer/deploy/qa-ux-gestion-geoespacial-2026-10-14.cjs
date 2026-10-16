// API completamente interceptada. No inicia sesión ni cambia datos reales.
const {chromium}=require(process.env.QA_PLAYWRIGHT || 'C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],writes=[],reads=[],missingFlag=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>r.abort()); // Nada puede alcanzar la API real ni servicios externos.
  await locales(page);
  await page.context().addCookies([{name:'pa_csrf_dev',value:'qa-csrf',url:base}]);
  let rol='admin',bajaStatus=409;
  const record={id_importacion:5,id_proyecto:3,tipo_objetivo:'parcela_gpkg',nombre_original:'Parcelas QA 029.gpkg',activo:true,estado:'previsualizado',version_pipeline:'conciliacion-v3-historia',total_features:4,validos:4,errores:0,advertencias:0,srid_trabajo:4326,reporte:{}};
  const antiguo={...record,id_importacion:6,nombre_original:'Histórico QA.gpkg',activo:false,motivo_baja:'Entrega cancelada',fecha_baja:'2026-10-13T12:00:00Z'};
  const universo={version:'1',origen:'actual',disponibilidad:'disponible',nucleos_vinculados_activos:74,parcelas_elegibles_vinculadas:0,destinos_aplicables:74,fecha_evaluacion:'2026-10-13T20:00:00Z',advertencias:[{codigo:'SIN_PARCELAS_ELEGIBLES',mensaje:'No hay parcelas elegibles vinculadas. <b>Texto literal</b>'}]};
  const usado={...universo,origen:'ciclo',id_ciclo:6,disponibilidad:'parcial',parcelas_elegibles_vinculadas:null,advertencias:[]};
  const ev={destinos_evaluados:74,nucleos_evaluados:74,nucleos_compatibles:0,parcelas_evaluadas:null,candidatos:0,descartes_territoriales:{municipio:1,entidad:0,tipo_nucleo:0},variantes_formato:[]};
  const diag=(mensaje,codigos=['MUNICIPIO_INCOMPATIBLE'])=>({version:'1',origen:'registrado',mensaje,codigos,campos_evaluados:['NombreMuni'],evidencia:{...ev}});
  const noDisponible={version:'1',origen:'no_disponible',codigos:['DIAGNOSTICO_HISTORICO_NO_DISPONIBLE'],mensaje:'Mensaje histórico del servidor',campos_evaluados:[],evidencia:{destinos_evaluados:null,nucleos_evaluados:null,nucleos_compatibles:null,parcelas_evaluadas:null,candidatos:null,descartes_territoriales:null,variantes_formato:[]}};
  const make=(i,d,ciclo=7)=>({id_importacion_feature:100+i,indice_feature:i,id_ciclo_conciliacion:ciclo,diagnostico:d,estado:'valido',estado_conciliacion:'sin_coincidencia',atributos_originales:{NombreNucl:'Núcleo '+i,NombreMuni:'Municipio original',NombreEnti:'Entidad original',no_parcela:'016'},errores:[],advertencias:[],transformaciones:[]});
  const formato=diag('Diferencia de formato observada. No establece equivalencia.',['VARIANTE_FORMATO_PENDIENTE_REVISION']);
  formato.evidencia.variantes_formato=[{campo:'no_parcela',regla:'DIFERENCIA_CEROS_INICIALES_SEGMENTO_NUMERICO',destinos_observados:1}];
  let rows=[make(0,diag('Municipio distinto al registrado. <img src=x onerror=alert(1)>')),make(1,noDisponible,6),make(2,formato),make(3,diag('Mensaje de una causa futura.',['CODIGO_FUTURO']))];
  const historico=()=>({...usado,id_ciclo:6,nucleos_vinculados_activos:12,destinos_aplicables:12});
  const ciclo=id=>({id_ciclo:id,numero_ciclo:id,fecha_inicio:'2026-10-12T12:00:00Z',estado:'cerrado',tipo_ciclo:'reconciliacion',version_algoritmo:'1',motivo:'Motivo guardado',universo_administrativo:id===6?historico():universo,universo_destinos:[{id_proyecto_nucleo:6,nombre_nucleo:'Destino del ciclo 6'}],features:rows.map(f=>({id_importacion_feature:f.id_importacion_feature,estado_matching:'sin_coincidencia',estado_resultado:'sin_coincidencia',diagnostico:id===6?noDisponible:f.diagnostico}))});
  await page.route('**/api/**',async route=>{
   const req=route.request(),u=new URL(req.url()),path=u.pathname;
   if(!path.startsWith('/api/'))return route.fallback();
   const reply=json=>route.fulfill({json});
   if(req.method()!=='GET'){
    writes.push({path,body:JSON.parse(req.postData()),csrf:req.headers()['x-csrf-token']});
    if(path==='/api/importaciones/5/baja'){
     if(bajaStatus!==200)return route.fulfill({status:bajaStatus,json:{detail:{403:'Sin permiso GIS para este proyecto',404:'Importación no encontrada',409:'La importación tiene confirmaciones o dependencias protegidas',422:'El motivo no es válido'}[bajaStatus]}});
     record.activo=false;record.motivo_baja=writes.at(-1).body.motivo;record.fecha_baja='2026-10-13T20:00:00Z';return reply(record);
    }
    return route.fulfill({status:409,json:{detail:'No se admiten escrituras en esta prueba'}});
   }
   reads.push(path+u.search);
   if(path==='/api/auth/sesion')return reply({user:{id_usuario:1,rol,nombre:'QA',apellido_paterno:'Contratos'}});
   if(path==='/api/proyectos')return reply([{id_proyecto:3,nombre_proyecto:'Proyecto QA',activo:true}]);
   if(path==='/api/proyectos/3')return reply({id_proyecto:3,nombre_proyecto:'Proyecto QA'});
   if(path.endsWith('/configuracion'))return reply({srid_trabajo:4326});
   if(path==='/api/proyectos/3/importaciones'){
    const all=[record,antiguo].filter(r=>u.searchParams.get('incluir_inactivas')==='true'||r.activo);
    return route.fulfill({json:all,headers:{'X-Total-Count':String(all.length)}});
   }
   if(path.includes('/importaciones/')){
    const id=Number(path.split('/')[3]),r=id===5?record:antiguo;
    if(r.activo===false && u.searchParams.get('incluir_inactivas')!=='true'){missingFlag.push(path);return route.fulfill({status:404,json:{detail:'Se requiere consulta histórica'}});}
    if(/^\/api\/importaciones\/\d+$/.test(path))return reply(r);
    if(path.endsWith('/resumen'))return reply({features_archivo:rows.length,features_sin_destino:rows.filter(f=>f.estado_conciliacion==='sin_coincidencia').length,registros_administrativos:74,universo_administrativo_actual:universo,universo_administrativo_utilizado:usado});
    if(path.endsWith('/features')){const all=rows.filter(f=>!u.searchParams.get('estado_conciliacion')||f.estado_conciliacion===u.searchParams.get('estado_conciliacion'));return route.fulfill({json:all.slice(Number(u.searchParams.get('skip')||0),Number(u.searchParams.get('skip')||0)+Number(u.searchParams.get('limit')||500)),headers:{'X-Total-Count':String(all.length)}});}
    if(path.endsWith('/conciliaciones'))return route.fulfill({json:[ciclo(6),ciclo(7)],headers:{'X-Total-Count':'2'}});
    if(/\/conciliaciones\/\d+$/.test(path))return reply(ciclo(Number(path.split('/').at(-1))));
    if(path.endsWith('/candidatos'))return reply([6,7].map(n=>({id_candidato:n,id_ciclo:n,id_proyecto_nucleo:n,estado:'propuesto',coincidencias:[]})));
    if(path.endsWith('/decisiones'))return reply([]);
    if(path.endsWith('/geometria'))return reply({type:'Feature',properties:{},geometry:{type:'Polygon',coordinates:[[[-99,20],[-98.9,20],[-98.9,20.1],[-99,20]]]}});
   }
   if(path.endsWith('/mapa'))return reply({type:'FeatureCollection',features:[]});
   return route.fulfill({json:[],headers:{'X-Total-Count':'0'}});
  });
  const ready=async()=>{await page.goto(base+'/pages/gestionGeoespacial.html?id_proyecto=3');try{await page.locator('.js-ver-importacion').first().waitFor({timeout:10000});}catch(e){console.log({errors,reads,text:(await page.locator('body').innerText()).slice(-2000)});throw e;}};
  const panel=page.locator('#conciliacionGeoespacial');
  const open=async id=>{await page.locator(`.js-ver-importacion[data-id-importacion="${id}"]`).click();await panel.locator('[data-gis-lista] tbody tr').first().waitFor();};
  const dialog=()=>page.getByRole('dialog');

  const fs=require('node:fs'),path=require('node:path');
  const phase=process.env.QA_UX_FASE || 'despues';
  if(phase==='antes') {
   await page.route('**/*',async route=>{
    const u=new URL(route.request().url()),name=path.basename(u.pathname);
    const before=path.resolve('.qa-backups/ux-divulgacion-2026-10-14',name);
    if(['gestionGeoespacial.js','conciliacionGeoespacial.js','gestionGeoespacial.html','gestionGeoespacial.css','conciliacionGeoespacial.css'].includes(name))return route.fulfill({body:fs.readFileSync(before),contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html'});
    return route.fallback();
   });
  }
  const capture=async(name,element)=>element.screenshot({path:`frontend-ssalfer/deploy/qa-ux-gis-${name}-${phase}-2026-10-14.png`});
  const keyboardDisclosure=async(locator)=>{
   assert.equal(await locator.evaluate(el=>el.open),false);
   const summary=locator.locator(':scope > summary');await summary.focus();await page.keyboard.press('Enter');
   assert.equal(await locator.evaluate(el=>el.open),true);
   assert.notEqual(await summary.evaluate(el=>getComputedStyle(el).outlineStyle),'none');
   await page.keyboard.press('Space');assert.equal(await locator.evaluate(el=>el.open),false);
  };
  await ready();
  await capture('historial',page.locator('.geoespacial-historial'));
  await page.locator('#btnCrearImportacion').click();await page.locator('#tipoObjetivoGeoespacial').selectOption('parcelas');
  await capture('carga',page.locator('#seccionNuevaImportacion'));
  if(phase==='despues'){
   assert.match(await page.locator('#ayudaTipoGeoespacial').innerText(),/deben estar registradas/);
   const ayuda=page.locator('details').filter({has:page.locator('#detalleTipoGeoespacial')});
   assert.match(await ayuda.textContent(),/no crea automáticamente/);
   await keyboardDisclosure(ayuda);
   assert.equal(await page.locator('#alcanceEntregaGis').getAttribute('required'),'');
  }
  await page.locator('#btnCerrarImportacion').click();await open(5);
  await capture('conciliacion',panel);
  if(phase==='despues') {
   assert.match(await panel.locator('.gis-diagnostico').innerText(),/Sin coincidencia en casi todo/);
   assert.doesNotMatch(await panel.locator('.gis-diagnostico').innerText(),/Ejemplos/);
   const ayuda=panel.locator('.gis-diagnostico > details');await keyboardDisclosure(ayuda);
   await ayuda.locator('summary').click();assert.match(await ayuda.innerText(),/100.0 %/);await ayuda.locator('summary').click();
   assert.match(await page.locator('#gisEstadoCierre').innerText(),/Listo para finalizar/);
   await keyboardDisclosure(panel.locator('[data-gis-cierre] details'));
   assert(await panel.locator('.gis-advertencia').first().isVisible());
  }
  await panel.locator('[data-gestion="detalle-sin-coincidencia"]').click();await dialog().waitFor();
  await capture('modal',dialog());
  if(phase==='despues') {
   const detail=dialog().locator('.gis-diagnostico-detalle details').first();
   assert.doesNotMatch(await dialog().innerText(),/Municipio distinto al registrado/);
   await keyboardDisclosure(detail);await detail.locator('summary').click();
   assert.match(await detail.innerText(),/Municipio distinto al registrado/);
   assert.match(await detail.innerText(),/Parcelas evaluadas: No disponible/);
   assert.equal(await dialog().locator('img').count(),0);
   await dialog().locator('[data-gis-buscar]').fill('CODIGO_FUTURO');
   assert.match(await dialog().locator('[data-gis-conteo]').innerText(),/1–1 de 1/);
   await dialog().locator('.gis-diagnostico-detalle summary').click();assert.match(await dialog().innerText(),/Mensaje de una causa futura/);
   await dialog().locator('[data-gis-limpiar]').click();
   await page.setViewportSize({width:390,height:844});
   await capture('modal-movil',dialog());
   assert(await dialog().evaluate(el=>el.getBoundingClientRect().right<=innerWidth));
   await page.keyboard.press('Escape');
   assert(await panel.locator('[data-gestion="detalle-sin-coincidencia"]').evaluate(el=>el===document.activeElement));
  }
  assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
  console.log(`OK: UX ${phase}; capturas de carga, historial, conciliación y modal; cero escrituras y errores JavaScript.`);
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
