// Inventario de controles después de cargar páginas reales. No imprime datos de personas.
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
        const base = 'http://127.0.0.1:5184';
        const auth = await context.request.post(base + '/api/auth/sesiones', {
            headers: { Origin: base }, form: { username: process.env.QA_USER, password: process.env.QA_PASSWORD }
        });
        assert.equal(auth.status(), 200);
        const page = await context.newPage(), errors = [], writes = [], serverErrors = [], inventory = [];
        page.on('pageerror', e => errors.push(e.message));
        page.on('response', r => { if (r.status() >= 500) serverErrors.push(new URL(r.url()).pathname + ': ' + r.status()); });
        await page.route('**/api/**', route => {
            if (route.request().method() !== 'GET') { writes.push(route.request().method()); return route.abort(); }
            return route.continue();
        });
        const queries = {
            fichaProyecto: 'id=4', nuevoProyecto: '', nuevoConvenio: 'id_afectacion=187',
            fichaConvenio: 'id_convenio=134', detalleAfectacion: 'id=186',
            fichaRan: 'id_tramite_ran=263', tramiteRan: 'id_asamblea=183&id_proyecto_nucleo=150',
            fichaFifonafe: 'id_fifonafe=63&id_proyecto_nucleo=150',
            parcela: 'id_parcela=1&id_proyecto_nucleo=150', indemnizacion: 'id_afectacion=186',
            persona: 'id_proyecto=4', estadoFinanciero: 'id_proyecto=4',
            reportesConvenios: 'id_proyecto=4', reportesFifonafe: 'id_proyecto=4', reporteActividadesPeriodo: 'id_proyecto=4',
            usuarios: '', auditoria: '', catalogosOperativos: '', cambiarContrasena: ''
        };
        const pages = fs.readdirSync(path.join(__dirname, '../pages')).filter(f => f.endsWith('.html') && !['mapa.html', 'gestionGeoespacial.html'].includes(f));
        for (const file of ['dashboard.html', ...pages]) {
            const name = file.replace('.html', ''), query = queries[name] ?? 'id_proyecto_nucleo=150';
            await page.goto(base + (file === 'dashboard.html' ? '/' : '/pages/') + file + '?' + query);
            await page.waitForLoadState('networkidle');
            await page.waitForFunction(() => !document.querySelector('.ssalfer-cargando'));
            const controls = await page.evaluate(() => {
                const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
                return {
                    enlaces: [...document.querySelectorAll('a[href="#"]')].filter(visible).map(el => ({ id: el.id, texto: el.textContent.trim().replace(/\s+/g, ' '), accion: el.dataset.action || '' })),
                    deshabilitados: [...document.querySelectorAll('button:disabled, select:disabled, input:disabled, [aria-disabled="true"]')].filter(visible).map(el => ({ id: el.id, tag: el.tagName }))
                };
            });
            inventory.push({ pantalla: file, ...controls });
            console.log('PASS inventario:', file);
        }
        // Evidencia visual acotada: sólo el componente, sin datos de la cuenta.
        await page.evaluate(() => { window.qaFinalizar = SSALFER_UI.cargando.iniciar(); });
        await page.locator('.ssalfer-cargando-contenido').screenshot({ path: path.join(__dirname, 'qa-ronda3-tren.png') });
        await page.evaluate(() => window.qaFinalizar());
        const login = await context.newPage();
        await context.clearCookies();
        await login.goto(base + '/Index.html');
        await login.waitForLoadState('networkidle');
        assert.ok(await login.evaluate(() => Boolean(window.SSALFER_UI?.cargando)));
        assert.equal(await login.locator('.ssalfer-cargando').count(), 0, 'Comprobación automática de sesión silenciosa');
        fs.writeFileSync(path.join(__dirname, 'inventario-controles-ronda3.json'), JSON.stringify(inventory, null, 2) + '\n', 'utf8');
        assert.deepEqual(writes, []); assert.deepEqual(errors, []); assert.deepEqual(serverErrors, []);
        console.log(`PASS ${pages.length + 1} pantallas autenticadas + login; sin excepciones, HTTP 5xx ni escrituras de negocio.`);
    } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
