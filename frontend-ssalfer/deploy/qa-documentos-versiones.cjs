// Respuestas documentales de prueba; todo POST se intercepta antes de llegar al servidor.
const {chromium}=require(process.env.QA_PLAYWRIGHT||'playwright');
const assert=require('node:assert/strict');
(async()=>{
    const browser=await chromium.launch({channel:'msedge',headless:true});
    try{
        const base='http://127.0.0.1:5184',context=await browser.newContext({viewport:{width:390,height:844}});
        const auth=await context.request.post(base+'/api/auth/sesiones',{headers:{Origin:base},form:{username:process.env.QA_USER,password:process.env.QA_PASSWORD}});assert.equal(auth.status(),200);
        const page=await context.newPage(),peticiones=[],errores=[];page.on('pageerror',e=>errores.push(e.message));
        const documento={id_documento:900000,tipo_documento:'Constancia de prueba',titulo:'Documento de prueba sin persistencia',estado:'referenciado',fecha_documento:'2026-10-05',activo:true};
        await page.route('**/api/**',async route=>{
            const req=route.request(),url=new URL(req.url());
            if(req.method()!=='GET'){peticiones.push({ruta:url.pathname,cuerpo:req.postData(),tipo:req.headers()['content-type']});return route.abort();}
            if(url.pathname==='/api/documentos/objetivos/proyecto_nucleo/150')return route.fulfill({json:[documento]});
            if(url.pathname==='/api/documentos/900000/versiones')return route.fulfill({json:[{id_documento_version:900001,numero_version:1,nombre_original:'prueba.txt',tamano_bytes:8,fecha_carga:'2026-10-05'}]});
            if(url.pathname==='/api/documentos/versiones/900001/descarga')return route.fulfill({contentType:'text/plain',body:'prueba QA'});
            return route.continue();
        });
        await page.goto(base+'/pages/documentos.html?id_proyecto_nucleo=150');await page.waitForLoadState('networkidle');
        await page.getByRole('button',{name:'Versiones y archivos'}).click();
        const descarga=page.waitForEvent('download');await page.getByRole('dialog').getByRole('button',{name:'Descargar',exact:true}).click();assert.equal((await descarga).suggestedFilename(),'prueba.txt');
        await page.getByRole('dialog').getByRole('button',{name:'Subir nueva versión'}).click();assert.equal(await page.getByRole('dialog').count(),2);
        await page.getByRole('dialog').last().locator('[name="archivo"]').setInputFiles({name:'prueba.txt',mimeType:'text/plain',buffer:Buffer.from('prueba QA')});
        await page.getByRole('dialog').last().getByRole('button',{name:'Guardar',exact:true}).click();await page.getByRole('dialog').last().locator('[role="alert"]').waitFor({state:'visible'});
        assert.ok(peticiones.at(-1).tipo.startsWith('multipart/form-data; boundary='));assert.ok(peticiones.at(-1).cuerpo.includes('name="archivo"'));assert.equal(peticiones.at(-1).ruta,'/api/documentos/900000/versiones');
        await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),1);await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),0);
        await page.getByRole('button',{name:'Consultar procedencia'}).click();await page.getByRole('dialog').getByRole('button',{name:'Registrar procedencia'}).click();await page.getByRole('dialog').locator('[name="archivo"]').fill('origen.xlsx');await page.getByRole('dialog').locator('[name="tratamiento"]').selectOption('REVISAR');await page.getByRole('dialog').getByRole('button',{name:'Guardar',exact:true}).click();await page.getByRole('dialog').locator('[role="alert"]').waitFor({state:'visible'});assert.equal(peticiones.at(-1).ruta,'/api/trazabilidad/objetivos/proyecto_nucleo/150');await page.keyboard.press('Escape');
        await page.locator('[data-doc-tipo]').selectOption('afectacion');await page.locator('[data-doc-registro]').selectOption('186');await page.getByRole('button',{name:'Vincular documento existente'}).click();
        const dialog=page.getByRole('dialog');await dialog.locator('[name="tipo_origen"]').selectOption('proyecto_nucleo');await dialog.locator('[name="registro_origen"]').selectOption('150');await dialog.locator('[name="documento"]').selectOption('900000');await dialog.getByRole('button',{name:'Guardar',exact:true}).click();await dialog.locator('[role="alert"]').waitFor({state:'visible'});assert.equal(peticiones.at(-1).ruta,'/api/documentos/900000/vinculos/afectacion/186');await page.keyboard.press('Escape');
        await page.screenshot({path:'frontend-ssalfer/deploy/qa-post-merge-documentos-movil.png',fullPage:true});
        assert.deepEqual(errores,[]);console.log('DOCUMENTOS_VERSIONES_OK: descarga, multipart, procedencia, vínculo y Escape anidado; escrituras interceptadas='+peticiones.length);
    }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
