// QA de navegador con respuestas reales; las solicitudes de escritura se abortan antes de persistir.
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');

(async () => {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
        const base = 'http://127.0.0.1:5184';
        const auth = await context.request.post(`${base}/api/auth/sesiones`, {
            headers: { Origin: base }, form: { username: process.env.QA_USER, password: process.env.QA_PASSWORD }
        });
        assert.equal(auth.status(), 200);
        const page = await context.newPage();
        const errors = [], mutations = [];
        let capture = null;
        page.on('pageerror', e => errors.push(e.message));
        page.on('dialog', async d => { errors.push('Diálogo nativo: ' + d.message()); await d.dismiss(); });
        await page.route('**/api/**', async route => {
            const req = route.request();
            if (req.method() === 'GET') return route.continue();
            const entry = { method: req.method(), url: req.url(), body: req.postDataJSON() };
            mutations.push(entry);
            if (capture) { capture(entry); return route.abort(); }
            errors.push('Escritura no autorizada: ' + req.url());
            return route.abort();
        });
        const go = async name => { await page.goto(`${base}/pages/${name}`); await page.waitForLoadState('networkidle'); };
        const get = async url => { const r = await context.request.get(base + '/api' + url); assert.ok(r.ok(), url); return r.json(); };

        if (!process.env.QA_NAV_ONLY) {
        const eventos = await get('/fifonafe/63/eventos');
        const evento = eventos.find(e => e.activo !== false);
        assert.ok(evento);
        console.log('FIFONAFE API real:', JSON.stringify({ ordinal: evento.ordinal, fecha_oficio: evento.fecha_oficio, fecha_evento: evento.fecha_evento, observaciones: evento.observaciones }));
        await go('fichaFifonafe.html?id_fifonafe=63&id_proyecto_nucleo=150');
        await page.locator(`[data-editar-evento="${evento.id_evento_fifonafe}"]`).waitFor();
        await page.locator(`[data-editar-evento="${evento.id_evento_fifonafe}"]`).click();
        assert.equal(await page.locator('[name="fecha_oficio"]').inputValue(), evento.fecha_oficio || '');
        assert.equal(await page.locator('[name="fecha_evento"]').inputValue(), evento.fecha_evento || '');
        await page.locator('.fifonafe-modal-form [type="submit"]').click();
        await page.locator('.fifonafe-modal-form').waitFor({ state: 'detached' });
        assert.ok((await page.locator('#ssalferToastRegion').innerText()).includes('No hay cambios'));
        assert.equal(mutations.length, 0);
        await page.locator(`[data-editar-evento="${evento.id_evento_fifonafe}"]`).click();
        await page.fill('[name="origen"]', (evento.origen || '') + ' revisión QA');
        let patch;
        capture = entry => { patch = entry; };
        await page.locator('.fifonafe-modal-form [type="submit"]').click();
        await page.waitForFunction(() => !document.querySelector('.fifonafe-modal-form [type="submit"]').disabled);
        assert.equal(patch.method, 'PATCH');
        assert.deepEqual(Object.keys(patch.body), ['origen']);
        capture = null;
        await page.keyboard.press('Escape');
        await page.click('#btnAgregarEvento');
        await page.selectOption('[name="id_tipo_evento"]', String(evento.id_tipo_evento));
        await page.fill('[name="numero_oficio"]', 'Validación local; no guardar');
        await page.fill('[name="ordinal"]', String(evento.ordinal));
        const before = mutations.length;
        await page.locator('.fifonafe-modal-form [type="submit"]').click();
        await page.waitForFunction(() => document.getElementById('ssalferToastRegion').textContent.includes('Ya existe un evento'));
        assert.equal(mutations.length, before);
        await page.fill('[name="ordinal"]', String(Math.max(...eventos.map(e => e.ordinal)) + 1));
        await page.fill('[name="numero_oficio"]', '');
        await page.locator('.fifonafe-modal-form [type="submit"]').click();
        await page.waitForFunction(() => document.getElementById('ssalferToastRegion').textContent.includes('Indica al menos un dato'));
        assert.equal(mutations.length, before);
        await page.keyboard.press('Escape');
        console.log('PASS FIFONAFE: fechas idénticas a API, sin cambios no envía, PATCH mínimo interceptado/abortado, ordinal duplicado y evidencia validados.');

        await go('auditoria.html');
        await page.locator('#panelCambios').waitFor();
        assert.equal(await page.locator('#panelAccesos').isVisible(), false);
        await page.click('[data-auditoria-tab="accesos"]');
        assert.equal(await page.locator('#panelAccesos').isVisible(), true);
        assert.equal(await page.locator('#panelCambios').isVisible(), false);
        await page.click('[data-auditoria-tab="cambios"]');
        assert.equal(await page.locator('#panelCambios').isVisible(), true);
        console.log('PASS Auditoría: contenido independiente de pestañas.');

        const afectacion = await get('/afectaciones/186');
        await go('detalleAfectacion.html?id=186');
        await page.click('#btnCapturarAvaluo');
        const monto = await page.locator('#inputAvaluoMonto').inputValue();
        await page.fill('#inputAvaluoMonto', '123');
        await page.click('#btnCancelarAvaluo');
        assert.equal(await page.locator('#formAvaluo').isVisible(), false);
        assert.equal(await page.getByText('Avalúo guardado correctamente.', { exact: true }).count(), 0);
        await page.click('#btnCapturarAvaluo');
        assert.equal(await page.locator('#inputAvaluoMonto').inputValue(), monto);
        assert.equal(Number(monto), Number(afectacion.avaluo_monto));
        await page.click('#btnCancelarAvaluo');
        console.log('PASS Avalúo: cancelar descarta y no anuncia guardado.');

        const indemnizacion = await get('/afectaciones/186/indemnizacion');
        await go('indemnizacion.html?id_afectacion=186');
        await page.click('#btnEditarIndemnizacion');
        assert.equal(await page.locator('#descripcionEstatus').inputValue(), indemnizacion.descripcion_estatus || '');
        await page.click('#btnCancelarIndemnizacion');
        console.log('PASS Indemnización: descripción precargada sin cambiar datos.');

        await go('afectacion.html?id_proyecto_nucleo=150');
        await page.click('#btnNuevaAfectacion');
        await page.selectOption('#tipoAfectacion', 'colectivo');
        await page.check('#revisionPendiente');
        assert.equal(await page.locator('#detalleRevisionCampo').isVisible(), true);
        await page.locator('#formAfectacion [type="submit"]').click();
        assert.equal(mutations.length, before);
        await page.fill('#revisionDetalle', 'QA ronda 2: comprobar envío de detalle, sin guardar');
        const opcionesCop = await page.locator('#tipoCop option').evaluateAll(opts => opts.map(o => o.value).filter(Boolean));
        if (opcionesCop.length) await page.selectOption('#tipoCop', opcionesCop[0]);
        let payloadAfectacion;
        capture = entry => { payloadAfectacion = entry; };
        await page.locator('#formAfectacion [type="submit"]').click();
        await page.waitForFunction(() => !document.querySelector('#formAfectacion [type="submit"]').disabled);
        assert.ok(payloadAfectacion, 'El formulario genera petición tras capturar detalle');
        assert.equal(payloadAfectacion.body.tipo_cop_revision_pendiente, true);
        assert.ok(payloadAfectacion.body.tipo_cop_revision_detalle.includes('QA ronda 2'));
        capture = null;
        console.log('PASS Afectación: detalle obligatorio y payload verificado; petición abortada antes de persistir.');

        await go('orv.html?id_proyecto_nucleo=150');
        await page.locator('.orv-item').first().click();
        await page.click('#btnAgregarIntegrante');
        await page.click('#btnBuscarPersona');
        await page.fill('[data-modal-texto]', 'abc');
        await page.click('[data-modal-accion="1"]');
        assert.equal(await page.locator('[data-modal-error]').isVisible(), true);
        await page.fill('[data-modal-texto]', '843');
        await page.click('[data-modal-accion="1"]');
        await page.waitForFunction(() => document.getElementById('personaIntegrante').value.includes('QA Gabriela Titular'));
        console.log('PASS ORV: modal valida identificador y consulta nombre real.');

        await go('unidadAgraria.html?id_proyecto_nucleo=150&id_afectacion=186');
        const vinculo = page.getByRole('link', {name:'Seleccionar / vincular'}).first();
        await vinculo.waitFor();
        assert.equal(await vinculo.locator('i.bi-link-45deg').count(), 1);
        console.log('PASS Seleccionar / vincular: icono de vínculo existente.');

        await go('fifonafe.html?id_proyecto_nucleo=150');
        await page.click('#btnNuevoTramite');
        await page.locator('input[name="ids_afectacion"]').first().check();
        const tipoInicial = page.locator('select[name$="[id_tipo_evento]"]').first();
        const valorTipo = await tipoInicial.locator('option').nth(1).getAttribute('value');
        await tipoInicial.selectOption(valorTipo);
        const antesInicial = mutations.length;
        await page.locator('#formFifonafe [type="submit"]').click();
        await page.waitForFunction(() => document.getElementById('ssalferToastRegion')?.textContent.includes('requiere número de oficio'));
        assert.equal(mutations.length, antesInicial);
        console.log('PASS Alta inicial FIFONAFE: evidencia validada antes de crear trámite.');
        }

        const casos = [
            ['afectacion.html?id_proyecto_nucleo=150','nucleoAgrario.html?id_proyecto_nucleo=150'],
            ['orv.html?id_proyecto_nucleo=150','nucleoAgrario.html?id_proyecto_nucleo=150'],
            ['parcela.html?id_parcela=1&id_proyecto_nucleo=150','nucleoAgrario.html?id_proyecto_nucleo=150'],
            ['unidadAgraria.html?id_proyecto_nucleo=150','nucleoAgrario.html?id_proyecto_nucleo=150'],
            ['persona.html?id_proyecto=4&return_to='+encodeURIComponent('/pages/parcela.html?id_parcela=1&id_proyecto_nucleo=150'),'parcela.html?id_parcela=1&id_proyecto_nucleo=150'],
            ['persona.html?id_proyecto=4','fichaProyecto.html?id=4'],
            ['estadoFinanciero.html?id_proyecto=4','fichaProyecto.html?id=4'],
            ['fichaProyecto.html?id=4','/dashboard.html'],['nuevoProyecto.html','/dashboard.html'],
            ['usuarios.html','/dashboard.html'],['auditoria.html','/dashboard.html'],['cambiarContrasena.html','/dashboard.html'],['catalogosOperativos.html','/dashboard.html'],
            ['reportesConvenios.html?id_proyecto=4','fichaProyecto.html?id=4'],['reportesFifonafe.html?id_proyecto=4','fichaProyecto.html?id=4'],['reporteActividadesPeriodo.html?id_proyecto=4','fichaProyecto.html?id=4'],
            ['expedienteDocumental.html?id_proyecto_nucleo=150','nucleoAgrario.html?id_proyecto_nucleo=150'],
            ['tramiteRan.html?id_asamblea=183&id_proyecto_nucleo=150','asamblea.html?id_proyecto_nucleo=150'],
            ['fichaRan.html?id_tramite_ran=263','nucleoAgrario.html?id_proyecto_nucleo=150'],
            ['fichaConvenio.html?id_convenio=134','detalleAfectacion.html?id=187']
        ];
        for (const [origen, destino] of casos) {
            await go(origen);
            // Espera a que los handlers posteriores a la sesión y consultas se instalen.
            await page.waitForLoadState('networkidle');
            if (origen.startsWith('persona.html') && await page.locator('#modalPersona').isVisible()) {
                await page.click('#btnCancelarPersona');
            }
            await page.click('#btnVolver');
            await page.waitForURL(url => url.href.endsWith(destino));
            console.log('PASS Volver:', origen.split('?')[0]);
        }

        for (const archivo of ['reportesConvenios','reportesFifonafe','reporteActividadesPeriodo']) {
            await go(`${archivo}.html?id_proyecto=4`);
            const enlaces = await page.locator('a[href*="reporteActividadesPeriodo.html"]').evaluateAll(els => els.map(e => e.href));
            assert.ok(enlaces.length && enlaces.every(url => new URL(url).searchParams.get('id_proyecto') === '4'));
            const r = await context.request.get(enlaces[0]); assert.equal(r.status(), 200);
        }
        assert.equal((await context.request.get(base + '/js/reporteAvancePeriodo.js')).status(), 200);
        console.log('PASS navegación de reportes y script de avance.');

        await go('reportesFifonafe.html?id_proyecto=4');
        await page.selectOption('#fifFiltroProyecto', '4');
        for (const tipo of ['cobertura','indicador']) {
            await page.click(`[data-fif-reporte="${tipo}"]`);
            const response = page.waitForResponse(r => r.url().includes('/api/reportes/fifonafe/') && r.request().method() === 'GET');
            await page.click('#btnConsultarFifReportes');
            const r = await response; assert.ok(r.ok());
            await page.waitForFunction(() => !document.getElementById('btnConsultarFifReportes').disabled);
            assert.equal(await page.locator('#fifReportesError').isVisible(), false);
            assert.ok((await page.locator('#tbodyFifReportes').innerText()).trim());
            console.log('PASS Reporte FIFONAFE:', tipo, new URL(r.url()).search);
        }

        await go('fichaProyecto.html?id=4');
        await page.waitForFunction(() => document.getElementById('enlaceReporteConvenios').href.includes('id_proyecto=4'));
        const rects = await page.locator('.reportes-accesos > a').evaluateAll(els => els.map(e => ({x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y})));
        assert.equal(rects.length,3);assert.ok(rects.every(r=>Math.abs(r.y-rects[0].y)<2));
        await page.locator('.tarjeta-reportes').screenshot({path:path.join(__dirname,'qa-ronda2-reportes-desktop.png')});
        await page.setViewportSize({width:390,height:844});
        const mobile = await page.locator('.reportes-accesos > a').evaluateAll(els => els.map(e => ({x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y})));
        assert.ok(mobile[1].y>mobile[0].y && mobile[2].y>mobile[1].y);
        await page.locator('.tarjeta-reportes').screenshot({path:path.join(__dirname,'qa-ronda2-reportes-mobile.png')});
        await page.setViewportSize({width:1440,height:1000});
        console.log('PASS Reportes: tres bloques horizontales y apilados en móvil.');

        assert.deepEqual(errors, []);
        console.log('PASS ronda 2: sin excepciones JavaScript ni diálogos nativos.');
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
