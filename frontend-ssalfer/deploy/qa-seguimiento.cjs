// Prueba de lectura: no envía altas, modificaciones ni bajas de datos.
// Usa Playwright instalado externamente, QA_USER y QA_PASSWORD en el entorno.
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        const context = await browser.newContext();
        const base = 'http://127.0.0.1:5184';
        const login = await context.request.post(`${base}/api/auth/sesiones`, {
            headers: { Origin: base },
            form: { username: process.env.QA_USER, password: process.env.QA_PASSWORD }
        });
        assert.equal(login.status(), 200, 'Inicio de sesión QA');
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        page.on('dialog', async dialog => { errors.push(`Diálogo nativo: ${dialog.message()}`); await dialog.dismiss(); });
        // Ejecuta el archivo de trabajo, con acceso exclusivo de prueba a la precarga.
        await page.route('**/js/seguimiento.js', route => {
            let source = fs.readFileSync(path.join(__dirname, '../js/seguimiento.js'), 'utf8');
            source = source.replace('    /* QA UX: selector documental contextual */',
                '    window.__seguimientoQA = { actualizarControlEntidad, limpiarFormulario };\n    /* QA UX: selector documental contextual */');
            return route.fulfill({ contentType: 'application/javascript', body: source });
        });
        await page.route('**/api/**', route => {
            assert.equal(route.request().method(), 'GET', 'Solo lectura después del login');
            return route.continue();
        });
        if (!process.env.QA_FINAL_ONLY) {
        await page.goto(`${base}/pages/seguimiento.html?id_proyecto_nucleo=150`);
        await page.waitForFunction(() => window.__seguimientoQA && document.querySelector('#seguimientoTabla [data-consultar]'));
        await page.click('#btnNuevoEvento');
        for (const tipo of ['proyecto_nucleo', 'afectacion', 'parcela', 'unidad_agraria', 'asamblea', 'tramite_ran', 'tramite_fifonafe', 'orv', 'padron_historial']) {
            await page.evaluate(async tipo => {
                document.getElementById('entidadTipo').value = tipo;
                await window.__seguimientoQA.actualizarControlEntidad();
            }, tipo);
            const options = await page.locator('#entidadSelector option').allTextContents();
            assert.ok(options.length > 1, `Opciones reales para ${tipo}`);
            assert.ok(options.every(text => !/#\d+/.test(text)), `Etiquetas humanas para ${tipo}`);
            console.log(`PASS directo: ${tipo}`);
        }
        for (const tipo of ['parcela_titular', 'asamblea_convocatoria', 'convenio', 'tramite_ran_evento', 'tramite_fifonafe_evento', 'tramite_fifonafe_interviniente', 'indemnizacion']) {
            await page.evaluate(async tipo => {
                document.getElementById('entidadTipo').value = tipo;
                await window.__seguimientoQA.actualizarControlEntidad();
            }, tipo);
            assert.equal(await page.locator('#entidadSelector').isDisabled(), true);
            const parent = await page.locator('#entidadContextoSelector option').nth(1).getAttribute('value');
            await page.selectOption('#entidadContextoSelector', parent);
            await page.waitForFunction(() => !document.getElementById('entidadSelector').textContent.includes('Cargando'));
            const options = await page.locator('#entidadSelector option').allTextContents();
            if (options.length === 1) {
                assert.match(options[0], /No hay/);
                console.log(`PASS vacío real: ${tipo}; precarga pendiente por falta de datos`);
                continue;
            }
            const child = await page.locator('#entidadSelector option').nth(1).getAttribute('value');
            await page.selectOption('#entidadSelector', child);
            assert.equal(await page.locator('#entidadId').inputValue(), child);
            await page.selectOption('#entidadContextoSelector', '');
            assert.equal(await page.locator('#entidadId').inputValue(), '');
            assert.equal(await page.locator('#entidadSelector').isDisabled(), true);
            // Misma función de precarga usada al editar, con un hijo REAL consultado arriba.
            await page.evaluate(async child => window.__seguimientoQA.actualizarControlEntidad(child), child);
            assert.equal(await page.locator('#entidadContextoSelector').inputValue(), parent);
            assert.equal(await page.locator('#entidadSelector').inputValue(), child);
            if (tipo === 'convenio' && process.env.QA_CAPTURE) {
                await page.locator('#formularioEvento').screenshot({ path: path.join(__dirname, 'qa-seguimiento-formulario.png') });
            }
            await page.selectOption('#entidadTipo', '');
            assert.equal(await page.locator('#entidadId').inputValue(), '');
            console.log(`PASS dependiente y precarga real: ${tipo}`);
        }
        // Regresión de respuestas tardías: una petición anterior no debe restaurar el hijo.
        await page.route('**/api/proyecto-nucleo/150/parcelas', async route => {
            await new Promise(resolve => setTimeout(resolve, 200));
            await route.continue();
        });
        await page.selectOption('#entidadTipo', 'parcela');
        await page.selectOption('#entidadTipo', '');
        await page.waitForTimeout(350);
        assert.equal(await page.locator('#entidadId').inputValue(), '');
        assert.equal(await page.locator('#entidadSelector').isVisible(), false);
        await page.selectOption('#ambito', 'general');
        const suspension = await page.locator('#tipoEvento option').evaluateAll(options => options.find(option => option.dataset.codigo === 'suspension')?.value);
        assert.ok(suspension, 'Suspensión existe en el catálogo real');
        await page.selectOption('#tipoEvento', suspension);
        await page.fill('#fechaEvento', '2026-10-01');
        await page.locator('#formSeguimiento button[type="submit"]').click();
        assert.ok((await page.locator('#mensajeFormulario').innerText()).includes('motivo'));
        await page.click('#btnCancelarEvento');
        await page.locator('[data-consultar]').first().click();
        assert.equal(await page.locator('.ssalfer-modal').isVisible(), true);
        assert.ok(!/#\d+/.test(await page.locator('.ssalfer-modal').innerText()));
        if (process.env.QA_CAPTURE) await page.locator('.ssalfer-modal').screenshot({ path: path.join(__dirname, 'qa-seguimiento-consulta.png') });
        await page.keyboard.press('Escape');
        await page.locator('[data-eliminar]').first().click();
        await page.locator('[data-modal-accion="1"]').click();
        assert.equal(await page.locator('#errorBajaSeguimiento').isVisible(), true);
        await page.locator('[data-modal-accion="0"]').click();
        assert.equal(await page.locator('.ssalfer-modal').count(), 0);

        await page.goto(`${base}/pages/fichaRan.html?id_tramite_ran=263`);
        await page.waitForFunction(() => document.getElementById('idTramite')?.textContent.includes('QA-RAN-001'));
        assert.ok(!(await page.locator('#origenReferencia').innerText()).includes('#133'));
        assert.equal((await page.locator('#fechaProgramada').innerText()).trim(), '25-09-2026');
        await page.click('#btnAgregarEvento');
        assert.equal(await page.locator('select#documentoEventoRan').count(), 1);
        assert.equal(await page.locator('#documentoEventoRan').inputValue(), '');
        assert.equal((await page.locator('#btnGuardarEventoRan').innerText()).trim(), 'Registrar evento');
        await page.click('#btnCancelarEventoRan');
        await page.locator('[data-editar-evento]').first().click();
        assert.equal((await page.locator('#btnGuardarEventoRan').innerText()).trim(), 'Guardar cambios');
        assert.equal(await page.locator('#ordinalEventoRan').isDisabled(), true);
        assert.equal(await page.locator('#fechaEventoRan').inputValue(), '2026-09-25');
        console.log('PASS ficha RAN: referencia de origen, fecha civil, selector documental, alta/edición diferenciadas.');

        await page.goto(`${base}/pages/fichaFifonafe.html?id_fifonafe=63&id_proyecto_nucleo=150`);
        await page.waitForFunction(() => document.getElementById('idTramite')?.textContent.includes('QA-FIF-63-EDIT'));
        assert.ok((await page.locator('#afectacionesTabla').innerText()).includes('1.2 ha'));
        await page.click('#btnAgregarEvento');
        assert.equal(await page.locator('select[name="id_documento"]').count(), 1);
        assert.equal(await page.locator('select[name="id_documento"]').inputValue(), '');
        await page.keyboard.press('Escape');
        await page.locator('[data-editar-evento]').first().click();
        assert.equal(await page.locator('select[name="conflicto_impide_retiro"]').inputValue(), '');
        assert.equal(await page.locator('input[name="fecha_oficio"]').inputValue(), '2026-09-30');
        await page.keyboard.press('Escape');
        console.log('PASS ficha FIFONAFE: afectación humana, documento vacío, fecha y conflicto sin definir conservados.');

        await page.goto(`${base}/pages/padrones.html?id_proyecto_nucleo=150`);
        await page.locator('[data-ver-padron], [data-consultar-padron]').first().waitFor();
        await page.locator('[data-ver-padron], [data-consultar-padron]').first().click();
        assert.ok(!/#\d+/.test(await page.locator('.ssalfer-modal').innerText()));
        await page.keyboard.press('Escape');
        console.log('PASS Padrón: consulta sin referencia técnica.');

        await page.goto(`${base}/pages/expedienteDocumental.html?id_proyecto_nucleo=150`);
        await page.locator('#requisitosTabla [data-editar]').first().waitFor();
        await page.click('#btnNuevoRequisito');
        const tiposExpediente = await page.locator('#entidadTipo option').evaluateAll(options => options.map(option => option.value).filter(Boolean));
        for (const tipo of tiposExpediente) {
            await page.selectOption('#entidadTipo', tipo);
            await page.waitForFunction(() => !document.getElementById('entidadId').textContent.includes('Cargando'));
            const options = await page.locator('#entidadId option').allTextContents();
            assert.ok(!options.some(text => text.includes('No fue posible')), `Consulta real de Expediente: ${tipo}`);
            assert.ok(options.length > 1 || options[0].includes('No hay elementos'), `Lista o vacío real: ${tipo}`);
            assert.equal(await page.locator('#entidadId').inputValue(), '', 'Limpiar relación anterior');
            console.log(`PASS Expediente ${tipo}: ${options.length - 1} registros reales`);
        }
        await page.click('#btnCancelarRequisito');
        await page.locator('#requisitosTabla [data-editar]').first().click();
        await page.waitForFunction(() => document.getElementById('entidadId').value === '128');
        assert.equal(await page.locator('#entidadId').isDisabled(), true);
        assert.equal(await page.locator('#entidadTipo').isDisabled(), true);
        assert.equal(await page.locator('#idRequisito').isDisabled(), true);
        assert.equal(await page.locator('#idDocumento').inputValue(), '');
        console.log('PASS Expediente: edición del requisito real preserva padrón, relación inmutable y documento vacío.');

        await page.goto(`${base}/pages/auditoria.html`);
        await page.locator('select#cambiosProyecto').waitFor();
        await page.selectOption('#cambiosProyecto', '4');
        await page.waitForFunction(() => document.getElementById('cambiosProyectoNucleo').options.length > 1);
        await page.selectOption('#cambiosProyectoNucleo', '150');
        assert.equal(await page.locator('select#cambiosUsuario').count(), 1);
        assert.equal(await page.locator('select#accesosUsuario').count(), 1);
        await page.click('#btnLimpiarCambios');
        assert.equal(await page.locator('#cambiosProyectoNucleo').inputValue(), '');
        assert.equal(await page.locator('#cambiosProyectoNucleo').isDisabled(), true);
        console.log('PASS Auditoría: filtros humanos, núcleo por proyecto y limpieza de contexto.');

        await page.goto(`${base}/pages/fichaConvenio.html?id_convenio=136`);
        await page.waitForFunction(() => document.getElementById('tituloConvenio')?.textContent.includes('Consecutivo 3'));
        await page.waitForFunction(() => document.getElementById('padreNombre')?.textContent.includes('Consecutivo 1'));
        console.log('PASS Convenio: referencia funcional y convenio padre real.');
        }

        await page.goto(`${base}/pages/reportesConvenios.html`);
        await page.locator('select#reporteConvenioFiltro_id_proyecto').waitFor();
        await page.selectOption('#reporteConvenioFiltro_id_proyecto', '4');
        await page.waitForFunction(() => !document.getElementById('reporteConvenioFiltro_id_proyecto_nucleo').disabled);
        await page.selectOption('#reporteConvenioFiltro_id_proyecto_nucleo', '150');
        await page.waitForFunction(() => !document.getElementById('reporteConvenioFiltro_id_convenio').disabled);
        await page.selectOption('#reporteConvenioFiltro_id_convenio', '134');
        await page.click('#btnConsultarReportesConvenios');
        await page.waitForFunction(() => !document.getElementById('btnConsultarReportesConvenios').disabled);
        assert.ok((await page.locator('#tbodyReportesConvenios').innerText()).includes('Consecutivo 1'));
        await page.selectOption('#reporteConvenioFiltro_id_proyecto', '');
        assert.equal(await page.locator('#reporteConvenioFiltro_id_convenio').inputValue(), '');
        assert.equal(await page.locator('#reporteConvenioFiltro_id_proyecto_nucleo').inputValue(), '');
        console.log('PASS Reportes: proyecto → núcleo → convenio, consulta real y limpieza de filtros.');

        await page.goto(`${base}/pages/estadoFinanciero.html?id_proyecto=4`);
        await page.waitForFunction(() => document.getElementById('tablaValoresDeclarados')?.textContent.includes('Consecutivo'));
        await page.waitForFunction(() => document.getElementById('kpiSuperficieDeclarada')?.textContent.includes('ha') || !document.getElementById('mensajeError').hidden);
        if (!await page.locator('#mensajeError').isHidden()) console.log('REVISAR financiero:', await page.locator('#mensajeError').innerText());
        assert.ok(!(await page.locator('#tablaValoresDeclarados').innerText()).includes('#133'));
        assert.ok((await page.locator('#kpiSuperficieDeclarada').innerText()).includes('ha'));
        console.log('PASS Estado financiero: convenios humanos y superficie conserva unidad ha.');

        await page.goto(`${base}/pages/nuevoConvenio.html?id_afectacion=186`);
        await page.waitForFunction(() => document.getElementById('idAsambleaAutorizacion')?.options.length > 1);
        assert.ok(!(await page.locator('#idAsambleaAutorizacion').innerText()).includes('#183'));
        await page.goto(`${base}/pages/nuevoConvenio.html?id_afectacion=187`);
        await page.waitForFunction(() => document.getElementById('idConvenioPadre')?.options.length > 1);
        assert.ok((await page.locator('#idConvenioPadre').innerText()).includes('Consecutivo'));
        console.log('PASS Nuevo convenio: asamblea y convenio padre con etiquetas funcionales.');

        await page.goto(`${base}/pages/asamblea.html?id_proyecto_nucleo=150`);
        await page.waitForFunction(() => document.body.innerText.includes('QA E2E - Obtener anuencia'));
        assert.ok(!/Asamblea #183/.test(await page.locator('main').innerText()));
        console.log('PASS Asamblea: encabezado funcional.');

        await page.goto(`${base}/pages/orv.html?id_proyecto_nucleo=150`);
        await page.locator('#orvLista .orv-item').first().waitFor();
        assert.ok(!/\b2026-\d{2}-\d{2}\b/.test(await page.locator('#orvLista').innerText()));
        console.log('PASS ORV: vigencia en formato dd-mm-yyyy.');
        assert.deepEqual(errors, []);
        console.log('PASS: comprobaciones seleccionadas sin errores JavaScript ni escrituras de datos.');
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
