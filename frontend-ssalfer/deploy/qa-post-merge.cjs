// Lecturas reales. Se aborta toda escritura de negocio antes de enviarla.
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
(async () => {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        const base = 'http://127.0.0.1:5184', context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
        const auth = await context.request.post(base+'/api/auth/sesiones', { headers: { Origin: base }, form: { username: process.env.QA_USER, password: process.env.QA_PASSWORD } });
        assert.equal(auth.status(),200,'Sesión QA');
        const page = await context.newPage(), errores = [], fallos = [], escrituras = [];
        page.on('pageerror', e => errores.push(e.message));
        page.on('response', r => { if(r.url().includes('/api/') && r.status() >= 400) fallos.push([new URL(r.url()).pathname,r.status()]); });
        await page.route('**/api/**', route => {
            if(route.request().method() === 'GET') return route.continue();
            escrituras.push({ metodo: route.request().method(), ruta: new URL(route.request().url()).pathname, datos: route.request().postData() }); return route.abort();
        });
        const ir = async ruta => { await page.goto(base+'/pages/'+ruta); await page.waitForLoadState('networkidle'); };
        await ir('documentos.html?id_proyecto_nucleo=150');
        await page.getByRole('button',{name:'Registrar documento',exact:true}).waitFor();
        const referencias = await page.evaluate(async () => {
            const c=SSALFER_CONTEXTO.crear(150), resultado={};
            for(const tipo of Object.keys(SSALFER_CONTEXTO.nombres)) {
                try { const lista=await c.listar(tipo); resultado[tipo]={cantidad:lista.length, idsValidos:lista.every(r=>Number.isSafeInteger(r.id)&&r.id>0)}; }
                catch(error) { resultado[tipo]={error:error.message}; }
            }
            return resultado;
        });
        console.log('REFERENCIAS',JSON.stringify(referencias));
        assert.ok(Object.values(referencias).every(r=>!r.error&&r.idsValidos),'Referencias contextuales válidas');
        await page.getByRole('button',{name:'Registrar documento',exact:true}).click();
        const dialog=page.getByRole('dialog');
        await dialog.locator('[name="tipo_documento"]').fill('Constancia QA sin persistencia');
        await dialog.locator('[name="estado"]').selectOption('referenciado');
        await dialog.locator('[name="titulo"]').fill('Prueba interceptada');
        await dialog.getByRole('button',{name:'Guardar',exact:true}).click();
        await dialog.locator('[role="alert"]').waitFor({state:'visible'});
        assert.equal(escrituras.length,1); assert.equal(escrituras[0].ruta,'/api/documentos/objetivos/proyecto_nucleo/150');
        const payload=JSON.parse(escrituras[0].datos); assert.equal(payload.estado,'referenciado');
        await page.keyboard.press('Escape'); await dialog.waitFor({state:'hidden'});
        await ir('derechosColectivos.html?id_proyecto_nucleo=150');
        await page.locator('#reporteColectivo [data-resultados] table').waitFor();
        await page.locator('details summary').first().click(); await page.locator('details [data-pagos]').first().waitFor();
        assert.ok((await page.locator('#colectivosContenido').innerText()).includes('1.2 ha'));
        await ir('reportesColectivos.html?id_proyecto=4'); await page.locator('[data-resultados] table').waitFor();
        const nombres = await page.locator('[name="id_proyecto_nucleo"] option').allTextContents(); assert.ok(nombres.length>1);
        await ir('nucleoAgrario.html?id_proyecto_nucleo=150');
        assert.ok((await page.locator('#btnDerechosColectivos').getAttribute('href')).includes('id_proyecto_nucleo=150'));
        assert.ok((await page.locator('#btnDocumentos').getAttribute('href')).includes('id_proyecto_nucleo=150'));
        console.log('RESULTADO',JSON.stringify({errores,fallos,escriturasInterceptadas:escrituras.length}));
        assert.deepEqual(errores,[]); assert.deepEqual(fallos,[]);
    } finally { await browser.close(); }
})().catch(e => { console.error(e.message); process.exitCode=1; });
