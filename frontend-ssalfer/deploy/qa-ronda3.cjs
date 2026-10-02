// QA local: respuestas GET reales con latencia; ninguna escritura de negocio.
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
        const base = 'http://127.0.0.1:5184';
        const auth = await context.request.post(base + '/api/auth/sesiones', {
            headers: { Origin: base }, form: { username: process.env.QA_USER, password: process.env.QA_PASSWORD }
        });
        assert.equal(auth.status(), 200, 'Sesión de QA');
        const page = await context.newPage();
        const errors = [], mutations = [];
        let delay = 0, abort = false;
        page.on('pageerror', e => errors.push(e.message));
        page.on('dialog', async d => { errors.push('Diálogo nativo'); await d.dismiss(); });
        await page.route('**/api/**', async route => {
            if (route.request().method() !== 'GET') { mutations.push(route.request().method()); return route.abort(); }
            if (delay) await pause(delay);
            if (abort) return route.abort();
            await route.continue();
        });
        await page.addInitScript(() => {
            window.qaCargas = [];
            new MutationObserver(records => records.forEach(r => {
                [...r.addedNodes].filter(n => n.matches?.('.ssalfer-cargando')).forEach(n => window.qaCargas.push({ evento: 'mostrar', clase: n.className, tiempo: performance.now() }));
                [...r.removedNodes].filter(n => n.matches?.('.ssalfer-cargando')).forEach(n => window.qaCargas.push({ evento: 'ocultar', clase: n.className, tiempo: performance.now() }));
            })).observe(document, { childList: true, subtree: true });
        });
        const settled = async () => {
            await page.waitForLoadState('networkidle');
            await page.waitForFunction(() => !document.querySelector('.ssalfer-cargando'));
            await page.waitForTimeout(500); // Permite terminar el scroll suave de Chromium.
        };
        const go = async ruta => { await page.goto(base + '/pages/' + ruta); await settled(); };
        const focusWithin = async (selector, origen = false) => {
            await settled();
            assert.ok(await page.locator(selector).evaluate((el, origen) => (origen ? el.closest('section, .tarjeta, .bloque') || el : el).contains(document.activeElement), origen), 'Foco dentro de ' + selector);
        };
        const roundTrip = async (open, panel, cancel, origin) => {
            await page.locator(open).first().click(); await focusWithin(panel);
            await page.locator(cancel).click(); await focusWithin(origin, true);
        };

        delay = 450;
        await go('orv.html?id_proyecto_nucleo=150');
        const initial = await page.evaluate(() => ({ y: scrollY, cargas: qaCargas }));
        assert.equal(initial.y, 0, 'La carga inicial no desplaza');
        assert.ok(initial.cargas.some(e => e.clase.includes('pantalla')));
        for (let i = 0; i < initial.cargas.length; i += 2) {
            assert.ok(initial.cargas[i + 1].tiempo - initial.cargas[i].tiempo >= 380, 'Mínimo visible 400 ms (tolerancia 20)');
        }
        console.log('PASS carga inicial real lenta y sin scroll inicial');
        await page.locator('.orv-item').first().click();
        await page.locator('#seccionIntegrantes .ssalfer-cargando-inline').waitFor();
        assert.equal(await page.locator('.ssalfer-cargando-pantalla').count(), 0);
        await focusWithin('#seccionIntegrantes');
        assert.ok((await page.locator('#integrantesLista').innerText()).trim());
        await page.locator('#seccionIntegrantes').screenshot({ path: path.join(__dirname, 'qa-ronda3-orv.png') });
        console.log('PASS ORV: cargador en línea, contenido real y foco después de cargar');
        delay = 0;
        await roundTrip('#btnAgregarIntegrante', '#formularioIntegrante', '#btnCancelarIntegrante', '#seccionIntegrantes');
        await roundTrip('[data-editar-orv]', '#formularioOrv', '#btnCancelarOrv', '#orvLista');
        if (await page.locator('[data-finalizar-integrante]').count()) {
            await roundTrip('[data-finalizar-integrante]', '#formularioFinalizarIntegrante', '#btnCancelarFinalizarIntegrante', '#seccionIntegrantes');
        }

        // Concurrencia del componente, incluyendo una nueva petición durante el mínimo visible.
        const timers = await page.evaluate(async () => {
            const wait = ms => new Promise(r => setTimeout(r, ms));
            const inicio = performance.now(), a = SSALFER_UI.cargando.iniciar(), b = SSALFER_UI.cargando.iniciar();
            await wait(180); const rapido = !!document.querySelector('.ssalfer-cargando');
            await wait(160); a(); a(); const paralelo = document.querySelectorAll('.ssalfer-cargando').length;
            b(); await wait(50); const c = SSALFER_UI.cargando.iniciar();
            await wait(350); const retenido = !!document.querySelector('.ssalfer-cargando'); c();
            await wait(100); return { rapido, paralelo, retenido, limpio: !document.querySelector('.ssalfer-cargando'), ms: performance.now() - inicio };
        });
        assert.deepEqual([timers.rapido, timers.paralelo, timers.retenido, timers.limpio], [false, 1, true, true]);
        delay = 450;
        await page.evaluate(() => ClienteAPI.get('/proyectos', { silencioso: true }));
        assert.equal(await page.locator('.ssalfer-cargando').count(), 0);
        abort = true;
        await page.evaluate(() => ClienteAPI.get('/proyectos').catch(() => null));
        await settled(); abort = false;
        await page.evaluate(async () => {
            const controller = new AbortController();
            const p = ClienteAPI.get('/proyectos', { signal: controller.signal }).catch(() => null);
            setTimeout(() => controller.abort(), 350); await p;
        });
        await settled();
        console.log('PASS contador, retraso, mínimo visible, silencio, error de red y cancelación');
        const httpError = await page.evaluate(() => ClienteAPI.get('/personas/2147483647').then(() => 200).catch(e => e.status));
        assert.equal(httpError, 404); await settled();

        await go('seguimiento.html?id_proyecto_nucleo=150');
        await page.click('#btnNuevoEvento'); await focusWithin('#formularioEvento');
        const tipo = page.locator('#entidadTipo');
        const indiceAsamblea = await tipo.evaluate(el => [...el.options].findIndex(o => o.value === 'asamblea'));
        await tipo.focus(); await tipo.press('Home');
        for (let i = 0; i < indiceAsamblea; i++) await tipo.press('ArrowDown');
        await page.locator('#formSeguimiento .ssalfer-cargando-inline').waitFor();
        assert.equal(await page.locator('.ssalfer-cargando-pantalla').count(), 0);
        await settled();
        await page.click('#btnCancelarEvento'); await focusWithin('#seguimientoTabla', true);
        console.log('PASS selectores Seguimiento en línea y regreso al cancelar');

        await page.emulateMedia({ reducedMotion: 'reduce' });
        const reduced = await page.evaluate(async () => {
            const done = SSALFER_UI.cargando.iniciar();
            await new Promise(r => setTimeout(r, 330));
            const animation = getComputedStyle(document.querySelector('.ssalfer-cargando-humo circle')).animationName;
            done(); return animation;
        });
        assert.equal(reduced, 'none'); await settled(); delay = 0;
        await page.emulateMedia({ reducedMotion: 'no-preference' });

        const cases = [
            ['actividades.html?id_proyecto_nucleo=150', '#btnNuevaActividad', '#formularioActividad', '#btnCancelarActividad', '#actividadesTabla'],
            ['afectacion.html?id_proyecto_nucleo=150', '#btnNuevaAfectacion', '#formularioContenedor', '#btnCancelar', '#afectacionesGrid'],
            ['padrones.html?id_proyecto_nucleo=150', '#btnNuevoPadron', '#formularioPadron', '#btnCancelarPadron', '#padronesTabla'],
            ['expedienteDocumental.html?id_proyecto_nucleo=150', '#btnNuevoRequisito', '#formularioRequisito', '#btnCancelarRequisito', '#requisitosTabla'],
            ['fichaProyecto.html?id=4', '#btnEditarProyecto', '#editarProyectoContenedor', '#btnCancelarEdicionProyecto', '#nombreProyecto'],
            ['fichaConvenio.html?id_convenio=134', '#btnEditarConvenio', '#panelEdicionConvenio', '#cancelarEditarConvenio', '#tipoInstrumento'],
            ['fichaRan.html?id_tramite_ran=263', '#btnAgregarEvento', '#formularioEventoRan', '#btnCancelarEventoRan', '#eventosTabla'],
            ['fifonafe.html?id_proyecto_nucleo=150', '#btnNuevoTramite', '#formularioContenedor', '#btnCancelar', '#tramitesContainer'],
            ['unidadAgraria.html?id_proyecto_nucleo=150', '#btnNuevaUnidad', '#formularioUnidad', '#btnCancelarUnidad', '#unidadesContainer'],
            ['detalleAfectacion.html?id=186', '#btnEditarAfectacion', '#panelEdicionAfectacion', '#btnCancelarEdicionAfectacion', '#datoSituacion'],
            ['indemnizacion.html?id_afectacion=186', '#btnEditarIndemnizacion', '#formIndemnizacion', '#btnCancelarIndemnizacion', '#indemnizacionRegistrada']
        ];
        for (const [ruta, open, panel, cancel, origin] of cases) {
            await go(ruta);
            await page.locator(open).first().click(); await focusWithin(panel);
            if (ruta.startsWith('afectacion.html')) {
                await page.check('#revisionPendiente'); await focusWithin('#detalleRevisionCampo');
            }
            await page.click(cancel); await settled();
            // Los destinos de listas incluyen su título para que el lector de pantalla lo anuncie.
            assert.ok(await page.locator(origin).evaluate(el => {
                const target = el.closest('section, .tarjeta, .bloque') || el;
                return target.contains(document.activeElement) || el === document.activeElement;
            }), 'Regreso: ' + ruta);
            console.log('PASS abrir/cancelar:', ruta.split('?')[0]);
        }
        await go('asamblea.html?id_proyecto_nucleo=150');
        await page.locator('[data-editar-asamblea]').first().click(); await focusWithin('#formAsamblea');
        await page.click('#btnAgregarConvocatoria'); await focusWithin('#convocatoriasContainer > :last-child');
        await page.click('#btnCancelar'); await focusWithin('#asambleasRegistradas');
        await go('fichaConvenio.html?id_convenio=134');
        await roundTrip('#btnAgregarCompareciente', '#panelAgregarCompareciente', '#cancelarAgregarCompareciente', '#comparecientesTabla');
        await go('tramiteRan.html?id_asamblea=183&id_proyecto_nucleo=150');
        await page.click('#btnAgregarEvento'); await focusWithin('#eventosLista > :last-child');
        await go('nuevoConvenio.html?id_afectacion=187');
        await page.click('#btnAgregarCompareciente'); await focusWithin('#comparecientesContainer > :last-child');
        console.log('PASS formularios anidados: convocatorias, comparecientes y eventos RAN');

        // Fixture DOM aislado para el retorno de submit: no simula respuestas ni guarda datos.
        await page.evaluate(() => {
            const fixture = document.createElement('section'); fixture.id = 'qaRetorno';
            fixture.innerHTML = '<h2 id="qaOrigen">Origen QA</h2><form id="qaForm"><input aria-label="QA"><button>Guardar QA</button></form>';
            document.body.append(fixture);
            SSALFER_UI.registrarAcciones([{ evento: 'submit', selector: '#qaForm', destino: '#qaOrigen', condicion: () => document.getElementById('qaForm').hidden }]);
            document.getElementById('qaForm').addEventListener('submit', event => { event.preventDefault(); event.target.hidden = true; });
        });
        await page.click('#qaForm button'); await focusWithin('#qaOrigen');
        await page.evaluate(() => document.getElementById('qaRetorno').remove());
        await go('estadoFinanciero.html?id_proyecto=4'); delay = 450;
        const descarga = page.waitForEvent('download');
        await page.click('#btnExportarCsv');
        await page.locator('.ssalfer-cargando-pantalla').waitFor();
        const archivo = await descarga;
        assert.equal(archivo.suggestedFilename(), 'dashboard.csv'); await archivo.cancel();
        await settled(); delay = 0;
        console.log('PASS exportación CSV real y retorno tras submit (fixture DOM, sin persistencia)');
        await go('reportesFifonafe.html?id_proyecto=4');
        await page.click('[data-fif-reporte="indicador"]'); await focusWithin('#formReportesFifonafe');
        await page.click('#btnConsultarFifReportes'); await focusWithin('#fifTituloResultados');
        await go('unidadAgraria.html?id_proyecto_nucleo=150&id_unidad_agraria=193');
        assert.equal(await page.evaluate(() => scrollY), 0, 'Unidad seleccionada sin desplazamiento inicial');
        await go('orv.html?id_proyecto_nucleo=150');
        await page.setViewportSize({ width: 390, height: 844 });
        const menu = await page.locator('.aside').evaluate(el => {
            const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height, position: getComputedStyle(el).position };
        });
        console.log('MENU MOBILE', menu);
        await page.locator('.orv-item').first().click(); await focusWithin('#seccionIntegrantes');
        assert.ok(await page.evaluate(() => document.activeElement.getBoundingClientRect().top >= document.querySelector('.aside').getBoundingClientRect().bottom), 'El foco queda debajo del menú móvil fijo');
        await page.screenshot({ path: path.join(__dirname, 'qa-ronda3-mobile.png') });
        assert.deepEqual(mutations, [], 'Cero escrituras de negocio');
        assert.deepEqual(errors, [], 'Sin excepciones JavaScript');
        console.log('PASS ronda 3: reduced motion, reportes, móvil y cero escrituras');
    } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
