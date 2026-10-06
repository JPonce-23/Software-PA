const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
(async () => {
    const browser = await chromium.launch({channel:'msedge',headless:true});
    try {
        const base='http://127.0.0.1:5184', context=await browser.newContext({viewport:{width:1440,height:1000}});
        const login=await context.request.post(base+'/api/auth/sesiones',{headers:{Origin:base},form:{username:process.env.QA_USER,password:process.env.QA_PASSWORD}}); assert.equal(login.status(),200);
        const page=await context.newPage(), errores=[], fallos=[], cambios=[];
        page.on('pageerror',e=>errores.push(e.message));page.on('response',r=>{if(r.url().includes('/api/')&&r.status()>=400)fallos.push([new URL(r.url()).pathname,r.status()]);});
        await page.route('**/api/**',route=>{const r=route.request();if(r.method()==='GET')return route.continue();cambios.push({ruta:new URL(r.url()).pathname,metodo:r.method(),datos:r.postData()});return route.abort();});
        const ir=async ruta=>{await page.goto(base+'/pages/'+ruta);await page.waitForLoadState('networkidle');};
        const cerrar=async()=>{await page.getByRole('dialog').last().getByRole('button',{name:'Cancelar',exact:true}).click();};
        const guardarInterceptado=async ruta=>{const cantidad=cambios.length;await page.getByRole('dialog').last().getByRole('button',{name:'Guardar',exact:true}).click();await page.getByRole('dialog').last().locator('[role="alert"]').waitFor({state:'visible'});assert.equal(cambios.length,cantidad+1);assert.equal(cambios.at(-1).ruta,ruta);await cerrar();};
        await ir('nucleoAgrario.html?id_proyecto_nucleo=150');
        await page.getByRole('button',{name:'Editar datos del proyecto-núcleo'}).click();
        await page.getByRole('dialog').locator('[name="total_cops_planeados"]').fill('11');await guardarInterceptado('/api/proyecto-nucleo/150');
        await page.getByRole('button',{name:'Agregar referencia',exact:true}).click();await page.getByRole('dialog').locator('[name="tipo_referencia"]').selectOption('otro');await page.getByRole('dialog').locator('[name="valor"]').fill('QA interceptada');await guardarInterceptado('/api/proyecto-nucleo/150/referencias');
        await page.getByRole('button',{name:'Agregar responsable',exact:true}).click();await page.getByRole('dialog').locator('[name="nombre"]').fill('QA interceptada');await guardarInterceptado('/api/proyecto-nucleo/150/responsables');
        await ir('fichaProyecto.html?id=4');await page.locator('#btnAgregarNucleo').click();await page.locator('#buscarNucleoRan').fill('San');await page.locator('#btnBuscarNucleoRan').click();await page.waitForLoadState('networkidle');assert.ok(await page.locator('#nucleoNombre').isHidden());
        const catalogo = await context.request.get(base+'/api/catalogos/nucleos?limit=1'); assert.equal(catalogo.status(),200);
        if (!(await catalogo.json()).length) console.log('CATALOGO_RAN_VACIO_EN_QA');
        await ir('orv.html?id_proyecto_nucleo=150');await page.locator('.orv-item').first().click();await page.locator('#btnAgregarIntegrante').click();await page.locator('#btnBuscarPersona').click();await page.getByRole('dialog').locator('[data-persona-elegir] option').nth(1).waitFor({state:'attached'});assert.ok((await page.getByRole('dialog').innerText()).includes('Personas del núcleo'));await cerrar();
        await ir('parcela.html?id_parcela=1&id_proyecto_nucleo=150');await page.getByRole('button',{name:'Editar titular',exact:true}).first().click();await page.getByRole('dialog').locator('[name="porcentaje_participacion"]').fill('99');await guardarInterceptado('/api/parcela-titulares/1');
        await ir('indemnizacion.html?id_afectacion=186');await page.locator('#pagosBody').getByRole('button',{name:'Editar',exact:true}).first().click();await page.getByRole('dialog').locator('[name="referencia"]').fill('QA interceptada');await guardarInterceptado('/api/pagos/1');
        await ir('fichaConvenio.html?id_convenio=134');const editarCompareciente=page.locator('#comparecientesTabla').getByRole('button',{name:'Editar',exact:true});if(await editarCompareciente.count()){await editarCompareciente.first().click();await page.getByRole('dialog').locator('[name="nombre_en_instrumento"]').fill('QA interceptada');const id=await page.evaluate(async()=> (await ConveniosAPI.listarComparecientes(134))[0].id_compareciente);await guardarInterceptado('/api/convenio-comparecientes/'+id);}
        await ir('fichaRan.html?id_tramite_ran=263');await page.getByRole('button',{name:'Editar fecha programada',exact:true}).first().click();await page.getByRole('dialog').locator('[name="fecha_programada_ingreso"]').fill('2026-10-06');await guardarInterceptado('/api/tramites-ran/263');
        await ir('fichaFifonafe.html?id_fifonafe=63&id_proyecto_nucleo=150');await page.getByRole('button',{name:'Agregar interviniente',exact:true}).click();await page.getByRole('dialog').locator('[name="id_persona"]').selectOption({index:1});await page.getByRole('dialog').locator('[name="rol"]').selectOption('beneficiario');await guardarInterceptado('/api/fifonafe/63/intervinientes');
        await ir('unidadAgraria.html?id_proyecto_nucleo=150');await page.locator('[data-id-unidad-agraria="193"]').getByRole('link').click();await page.locator('#btnAgregarTitular').click();await page.getByRole('dialog').locator('[name="id_persona"]').selectOption({index:1});await guardarInterceptado('/api/unidades-agrarias/193/titulares');const directorio=await page.evaluate(async()=>{const d=await SSALFER_DIRECTORIO.listar(150);return {cantidad:d.personas.length,fallos:d.fallos};});assert.ok(directorio.cantidad>0);assert.deepEqual(directorio.fallos,[]);
        await ir('usuarios.html');await page.locator('[data-asignacion-proyecto]').selectOption('4');await page.locator('#asignacionesProyecto').getByRole('button',{name:'Asignar usuario'}).click();await page.getByRole('dialog').locator('[name="id_usuario"]').waitFor();await cerrar();
        console.log(JSON.stringify({errores,fallos,payloadsInterceptados:cambios.map(c=>({ruta:c.ruta,metodo:c.metodo,campos:Object.keys(JSON.parse(c.datos))}))}));assert.deepEqual(errores,[]);assert.deepEqual(fallos,[]);
    } finally {await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
