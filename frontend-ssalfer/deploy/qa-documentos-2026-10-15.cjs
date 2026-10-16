const {chromium}=require('C:/Users/jplop/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
const {locales,base}=require('./qa-gis-ux-2026-10-06.cjs');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const page=await browser.newPage({viewport:{width:1600,height:1100}}),writes=[],results=[];let role='admin',removed=false,failVersions=false,failDelete=false;
 const common={id_proyecto:4,id_proyecto_nucleo:150,id_nucleo:1,nombre_nucleo:'Núcleo de prueba documental',nombre_proyecto:'Proyecto QA',activo:true};
 const docs=[{id_documento:1,titulo:'Acta de prueba',tipo_documento:'ACTA',estado:'disponible',fecha_documento:'2026-09-01'},{id_documento:2,titulo:'Documento pendiente',tipo_documento:'OTRO',estado:'faltante'}];
 await page.route('**/*',r=>r.abort());await locales(page);
 await page.context().addCookies([{name:'pa_csrf_dev',value:'qa-csrf',url:base}]);
 await page.route('**/api/**',async r=>{const req=r.request(),u=new URL(req.url()),p=u.pathname;if(!p.startsWith('/api/'))return r.fallback();let data=[];
 if(req.method()!=='GET'){
  writes.push({method:req.method(),path:p,body:req.postData()});
  if(req.method()==='DELETE'&&p==='/api/documentos/1'){if(failDelete)return r.fulfill({status:409,json:{detail:'No se pudo dar de baja el documento de prueba'}});removed=true;return r.fulfill({json:{detail:'Documento dado de baja'}});}
  return r.fulfill({status:403,json:{detail:'Escritura bloqueada por QA'}});
 }
 if(p==='/api/auth/sesion')data={user:{id_usuario:1,rol:role,nombre:'QA',apellido_paterno:'Documentos'}};
 else if(p==='/api/proyectos')data=[common];
 else if(p==='/api/proyectos/4'||p==='/api/proyecto-nucleo/150')data=common;
 else if(p==='/api/convenios/1')data={...common,id_convenio:1,id_afectacion:1,tipo_convenio:'individual',afectaciones:[]};
 else if(p==='/api/tramites-ran/1')data={...common,id_tramite_ran:1,id_convenio:1,estado:'pendiente'};
 else if(p==='/api/afectaciones/1')data={...common,id_afectacion:1,tipo_afectacion:'ocupacion',unidades:[]};
 else if(p==='/api/tramites-fifonafe/1')data={...common,id_tramite_fifonafe:1};
 else if(p.startsWith('/api/documentos/objetivos/'))data=removed?[docs[1]]:docs;
 else if(p==='/api/documentos/1/versiones'){if(failVersions)return r.fulfill({status:503,json:{detail:'No disponible'}});data=[{id_documento_version:2,numero_version:2,nombre_original:'acta.pdf',tamano_bytes:200,fecha_carga:'2026-10-15T15:00:00Z'},{id_documento_version:1,numero_version:1,fecha_carga:'2026-10-01T15:00:00Z'}];}
 return r.fulfill({json:data,headers:{'X-Total-Count':String(Array.isArray(data)?data.length:0)}});
 });
 const routes=[['nucleoAgrario','id_proyecto_nucleo=150'],['orv','id_proyecto_nucleo=150'],['padrones','id_proyecto_nucleo=150'],['persona','id_proyecto_nucleo=150'],['actividades','id_proyecto_nucleo=150'],['asamblea','id_proyecto_nucleo=150'],['parcela','id_proyecto_nucleo=150'],['unidadAgraria','id_proyecto_nucleo=150'],['seguimiento','id_proyecto_nucleo=150'],['fichaFifonafe','id_fifonafe=1&id_proyecto_nucleo=150'],['fifonafe','id_proyecto_nucleo=150'],['fichaConvenio','id_convenio=1'],['afectacion','id_proyecto_nucleo=150'],['detalleAfectacion','id=1'],['fichaRan','id_tramite_ran=1'],['indemnizacion','id_afectacion=1']];
 for(const [name,query]of routes){await page.goto(`${base}/pages/${name}.html?${query}`);const button=page.locator(name==='nucleoAgrario'?'#btnDocumentos':'[data-abrir-documentos]');await button.waitFor({timeout:10000});await button.scrollIntoViewIfNeeded();await page.screenshot({path:`outputs/qa-documentos-${name}-2026-10-15.png`});
 if(name==='nucleoAgrario'){assert.match(await button.getAttribute('href'),/documentos.html.*150/);}
 else{await button.click();await page.locator('[data-doc-contenido]').getByText('Acta de prueba',{exact:true}).waitFor({timeout:10000});await page.keyboard.press('Escape');}
 results.push({pantalla:name,acceso:'OK',nucleo:150});console.log('ACCESO OK',name);}
 await page.goto(base+'/pages/afectacion.html?id_proyecto_nucleo=150');await page.locator('[data-abrir-documentos]').click();
 const content=page.locator('[data-doc-contenido]');await content.getByText('Acta de prueba',{exact:true}).waitFor();
 assert.match(await content.innerText(),/Fecha del documento/);assert.match(await content.innerText(),/Última carga/);assert.match(await content.innerText(),/15-10-2026/);assert.match(await content.innerText(),/Sin archivo/);
 await page.screenshot({path:'outputs/qa-documentos-tabla-2026-10-15.png'});
 await content.locator('[data-gestion="versiones"]').first().click();await page.getByRole('button',{name:'Subir nueva versión',exact:true}).click();
 const input=page.locator('input[type=file]');assert.equal(await input.getAttribute('accept'),'.pdf,.docx,.xlsx,.jpg,.jpeg,.png');assert.match(await page.getByRole('dialog').last().innerText(),/20 MB/);await page.keyboard.press('Escape');await page.keyboard.press('Escape');
 await content.locator('[data-gestion="baja"]').first().click();let dialog=page.getByRole('dialog').last();assert.match(await dialog.innerText(),/auditada/);assert.match(await dialog.innerText(),/No borra el archivo físico/);
 await page.screenshot({path:'outputs/qa-documentos-baja-2026-10-15.png'});
 await dialog.getByRole('button',{name:'Guardar',exact:true}).click();assert.equal(writes.length,0);
 await dialog.locator('[name=motivo]').fill('Motivo de prueba');await dialog.getByRole('button',{name:'Guardar',exact:true}).click();assert.equal(writes.length,0);
 await dialog.getByRole('button',{name:'Cancelar',exact:true}).click();assert.equal(writes.length,0);
 await content.locator('[data-gestion="baja"]').first().click();dialog=page.getByRole('dialog').last();await dialog.locator('[name=motivo]').fill('Motivo de prueba');await dialog.locator('[name=confirmar]').check();failDelete=true;await dialog.getByRole('button',{name:'Guardar',exact:true}).click();await dialog.getByRole('alert').waitFor();assert.match(await dialog.innerText(),/No se pudo dar de baja/);failDelete=false;await dialog.getByRole('button',{name:'Guardar',exact:true}).click();await content.getByText('Acta de prueba',{exact:true}).waitFor({state:'hidden'});assert.equal(JSON.parse(writes.at(-1).body).motivo,'Motivo de prueba');
 for(const r of ['operador','geografo','visualizador']){role=r;removed=false;await page.reload();await page.locator('[data-abrir-documentos]').click();await content.getByText('Acta de prueba',{exact:true}).waitFor();assert.equal(await content.locator('[data-gestion="baja"]').count(),r==='operador'?2:0);}
 role='admin';failVersions=true;await page.reload();await page.locator('[data-abrir-documentos]').click();await content.getByText('Acta de prueba',{exact:true}).waitFor();assert.match(await content.innerText(),/Fecha no disponible/);
 fs.writeFileSync('outputs/qa-documentos-2026-10-15.json',JSON.stringify({pantallas:results,pruebas:['fecha última versión','sin archivo','fallo consulta distinto de sin archivo','formatos y límite','cancelación sin escritura','motivo y confirmación obligatorios','error de baja visible','baja y refresco','roles'],escriturasSimuladas:writes},null,2));console.log('OK: 16 accesos, versiones, baja, roles. API completamente simulada.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
