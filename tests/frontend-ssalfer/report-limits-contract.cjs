// Pure VM contract check: no DOM, network, backend, cookies or services.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const calls = [];
let failure = null;
const rows = [{id_proyecto: 1, indicador: 'synthetic', cantidad: 3, monto: '100.25'}];
const window = {ClienteAPI: {API_BASE_URL: 'https://qa.invalid/api', get: async url => {
    calls.push(url);
    if (failure) throw failure;
    return rows;
}}};
vm.runInNewContext(fs.readFileSync(path.resolve(__dirname, '../../frontend-ssalfer/js/api/reportes.js'), 'utf8'),
    {window, URLSearchParams});
(async () => {
    const result = await window.ReportesAPI.obtenerAvancePeriodo({id_proyecto: 1, anio: 2026, indicador: 'synthetic'});
    assert.equal(result, rows);
    assert.equal(Array.isArray(result), true);
    assert.equal(calls.at(-1), '/reportes/avance-periodo?id_proyecto=1&anio=2026&indicador=synthetic');
    assert.equal(await window.ReportesAPI.obtenerResumenActual(), rows);
    assert.equal(calls.at(-1), '/reportes/resumen-actual');
    assert.equal(window.ReportesAPI.urlExportacionDashboardCsv(), 'https://qa.invalid/api/exportaciones/dashboard.csv');
    failure = Object.assign(new Error('El reporte excede el límite de filas; acote los filtros.'), {status: 413});
    await assert.rejects(window.ReportesAPI.obtenerAvancePeriodo(), error => error === failure);
    await assert.rejects(window.ReportesAPI.obtenerResumenActual(), error => error === failure);
    console.log('SS-11 frontend API contract: arrays, filters, URLs and explicit failures OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
