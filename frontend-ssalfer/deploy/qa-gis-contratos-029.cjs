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
  await ready();assert.equal(await page.locator('.js-ver-importacion').count(),1);await open(5);
  const actual=panel.locator('.gis-universos .gis-universo').nth(0),usadoUi=panel.locator('.gis-universos .gis-universo').nth(1);
  assert.deepEqual(await actual.locator('dd').allTextContents(),['74','0','74']);
  assert.deepEqual(await usadoUi.locator('dd').allTextContents(),['74','No disponible','74']);
  assert.doesNotMatch(await panel.textContent(),/conteos conocidos cambiaron/);
  assert.equal(await actual.locator('b').count(),0);
  assert.match(await usadoUi.textContent(),/no significa que falten registros/);
  assert.match(await panel.locator('[data-gis-lista]').textContent(),/Municipio distinto al registrado/);
  assert.doesNotMatch(await panel.locator('[data-gis-lista]').textContent(),/El servidor no informó/);
  assert.equal(await panel.locator('[data-gis-lista] img').count(),0);
  await panel.locator('[data-gestion="detalle-sin-coincidencia"]').click();
  await dialog().locator('[data-gis-buscar]').fill('MUNICIPIO_INCOMPATIBLE');
  assert.match(await dialog().locator('[data-gis-conteo]').innerText(),/1–1 de 1/);
  await dialog().locator('.gis-diagnostico-detalle summary').click();
  assert.match(await dialog().innerText(),/Parcelas evaluadas: No disponible/);assert.match(await dialog().innerText(),/Núcleos compatibles: 0/);
  await dialog().locator('[data-gis-buscar]').fill('no_parcela');
  assert.match(await dialog().innerText(),/016/);
  await dialog().locator('[data-gis-buscar]').fill('VARIANTE_FORMATO');
  assert.match(await dialog().locator('[data-gis-conteo]').innerText(),/1–1 de 1/);
  await dialog().locator('.gis-diagnostico-detalle summary').click();assert.match(await dialog().innerText(),/no establecen equivalencia ni generan candidatos/);
  await dialog().locator('[data-gis-buscar]').fill('CODIGO_FUTURO');await dialog().locator('.gis-diagnostico-detalle summary').click();assert.match(await dialog().innerText(),/Mensaje de una causa futura/);
  await dialog().locator('[data-gis-limpiar]').click();
  const downloadPromise=page.waitForEvent('download');await dialog().locator('[data-gis-exportar]').click();const download=await downloadPromise;
  const stream=await download.createReadStream();let csv='';for await(const chunk of stream)csv+=chunk.toString('utf8');
  assert.match(csv,/Ciclo del resultado/);assert.match(csv,/MUNICIPIO_INCOMPATIBLE/);assert.match(csv,/No disponible/);assert.match(csv,/"016"/);assert.match(csv,/Diagnóstico no disponible para este resultado histórico/);
  await page.keyboard.press('Escape');
  await panel.locator('[data-gestion="ciclo"][data-registro="6"]').click();
  await dialog().locator('.gis-universo dd').first().waitFor();
  assert.deepEqual(await dialog().locator('.gis-universo dd').allTextContents(),['12','No disponible','12']);
  assert.doesNotMatch(await dialog().innerText(),/Municipio distinto al registrado/);assert.match(await dialog().innerText(),/Diagnóstico histórico no disponible/);await page.keyboard.press('Escape');
  // Feature de ciclo 6 aunque el último ciclo global sea 7.
  rows[1].estado_conciliacion='candidato';await page.evaluate(r=>SSALFER_GIS.mostrar(r),record);
  const inicio=reads.length;await panel.locator('[data-gestion="elemento"][data-registro="101"]').click();
  await panel.locator('[data-gis-elemento] [data-gestion="seleccionar"]').waitFor();
  assert.equal(await panel.locator('[data-gis-elemento] [data-gestion="seleccionar"]').getAttribute('data-registro'),'6');
  assert(!reads.slice(inicio).some(p=>/conciliaciones\/7/.test(p)));
  assert.deepEqual(await panel.locator('[data-gis-elemento] .gis-universo dd').allTextContents(),['12','No disponible','12']);
  // Un cambio demostrado sí se explica; null nunca crea por sí solo una diferencia.
  usado.destinos_aplicables=70;await page.evaluate(r=>SSALFER_GIS.mostrar(r),record);
  assert.match(await panel.textContent(),/conteos conocidos cambiaron/);usado.destinos_aplicables=74;
  const anterior=rows[3].diagnostico;rows[3].diagnostico=null;await page.evaluate(r=>SSALFER_GIS.mostrar(r),record);
  assert.match(await panel.locator('[data-gis-lista]').textContent(),/El servidor no informó/);rows[3].diagnostico=anterior;
  console.log('OK: diagnósticos registrados/históricos/futuros, evidencia null/0, CSV, escape HTML, ceros iniciales, universos separados y ciclo propio.');
  await page.locator('#filtroHistorialDisponibilidad').selectOption('todas');await page.locator('.js-ver-importacion[data-id-importacion="6"]').waitFor();
  await open(6);assert.match(await panel.textContent(),/Dada de baja · Sólo lectura/);
  assert.equal(await panel.locator('[data-gestion="reconciliar"], [data-gestion="finalizar"], [data-gestion="confirmar-todas"]').count(),0);
  await panel.locator('[data-gestion="elemento"][data-registro="101"]').click();await panel.locator('[data-gis-elemento] h3').first().waitFor();
  await page.waitForFunction(()=>document.querySelector('[data-gis-elemento]').textContent.includes('Historial de decisiones'));
  assert.equal(await panel.locator('[data-gis-elemento] [data-gestion]').count(),0);
  // Incluso eventos sobre botones obsoletos no deben provocar POST de una inactiva.
  for(const accion of ['confirmar-todas','reconciliar','finalizar']){await page.evaluate(accion=>{const b=document.createElement('button');b.dataset.gestion=accion;document.querySelector('#conciliacionGeoespacial').append(b);b.click();b.remove();},accion);await page.waitForFunction(()=>!SSALFER_GIS.ocupado());}
  await page.waitForFunction(()=>!SSALFER_GIS.ocupado());assert.equal(writes.length,0);
  await panel.locator('[data-gestion="ciclo"]').first().click();await dialog().waitFor();await page.keyboard.press('Escape');
  const href=await panel.getByRole('link',{name:'Abrir previsualización en el mapa',exact:true}).getAttribute('href');assert.match(href,/incluir_inactivas=true/);
  await page.goto(base+href);await page.locator('#avisoPrevisualizacionGis').waitFor();assert.match(await page.locator('#avisoPrevisualizacionGis').innerText(),/dada de baja/);
  await page.goto(base+'/pages/mapa.html?id_proyecto=3&id_importacion=6&vista=coincidencias&incluir_inactivas=true');await page.locator('#avisoPrevisualizacionGis').waitFor();assert.match(await page.locator('#avisoPrevisualizacionGis').innerText(),/Consulta histórica de sólo lectura/);
  assert.deepEqual(missingFlag,[]);assert.equal(writes.length,0);
  console.log('OK: histórico deliberado, parámetro backend en todas sus lecturas, ciclo/detalle/mapa de sólo lectura, cero escrituras.');
  await ready();await open(5);
  const baja=()=>page.locator('.js-baja-importacion').first().click();
  await baja();await dialog().getByRole('button',{name:'Cancelar',exact:true}).click();assert.equal(writes.length,0);
  await baja();await dialog().locator('[name="motivo"]').fill('ab');await dialog().locator('[name="aceptar"]').check();await dialog().getByRole('button',{name:'Guardar',exact:true}).click();assert.equal(writes.length,0);
  await dialog().locator('[name="motivo"]').fill('Entrega duplicada de prueba');
  for(const status of [403,404,409,422]){
   bajaStatus=status;const response=page.waitForResponse(r=>r.url().endsWith('/baja'));
   await dialog().getByRole('button',{name:'Guardar',exact:true}).click();await response;
   await page.waitForFunction(()=>!document.querySelector('.ssalfer-modal__button--primary')?.disabled);
   await dialog().locator('[role="alert"]').waitFor({state:'visible'});
   assert.match(await dialog().innerText(),new RegExp({403:'Sin permiso GIS',404:'Importación no encontrada',409:'dependencias protegidas',422:'motivo no es válido'}[status]));
   assert(record.activo);
  }
  bajaStatus=200;await dialog().getByRole('button',{name:'Guardar',exact:true}).click();await dialog().waitFor({state:'hidden'});
  await page.waitForFunction(()=>document.querySelector('[data-gis-actividad]').textContent.includes('Dada de baja'));
  await page.waitForFunction(()=>!document.querySelector('#listaImportaciones .js-ver-importacion[data-id-importacion="5"]'));
  assert.equal(await panel.locator('[data-gestion="finalizar"], [data-gestion="reconciliar"], [data-gestion="confirmar-todas"]').count(),0);
  assert.deepEqual(writes.at(-1).body,{motivo:'Entrega duplicada de prueba'});assert.equal(writes.at(-1).csrf,'qa-csrf');
  assert(writes.every(w=>w.path.endsWith('/5/baja')));assert.deepEqual(missingFlag,[]);
  await page.locator('#filtroHistorialDisponibilidad').selectOption('inactivas');await page.locator('.js-ver-importacion[data-id-importacion="5"]').waitFor();assert.equal(await page.locator('.js-baja-importacion').count(),0);
  console.log('OK: cancelación sin POST, motivo obligatorio, CSRF, 403/404/409/422, baja exitosa y refresco de historial/panel.');
  record.activo=true;
  for(const role of ['geografo','visualizador','operador']){
   rol=role;await ready();assert.equal(await page.locator('.js-baja-importacion').count(),role==='geografo'?1:0);
   await open(5);assert.equal(await panel.locator('[data-gestion="confirmar-todas"]').count(),0);
  }
  rol='admin';await ready();await open(5);await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  if(await page.getByRole('button',{name:'Ocultar menú',exact:true}).isVisible())await page.getByRole('button',{name:'Ocultar menú',exact:true}).click();
  await page.setViewportSize({width:390,height:1200});
  await panel.getByText('Ver registros administrativos y ciclos',{exact:true}).click();
  await panel.locator('.gis-universos').screenshot({path:'frontend-ssalfer/deploy/qa-gis-universos-029-movil.png'});
  assert.deepEqual(errors,[]);assert.deepEqual(missingFlag,[]);
  console.log('OK: roles, móvil sin desbordamiento y cero errores JavaScript. API real: cero solicitudes.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
