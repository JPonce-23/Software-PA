/**
 * reportes.js — endpoints de dashboard.py / reporting.py
 * Usados por dashboard.html y pages/estadoFinanciero.html.
 */

(function () {

    const { get } = window.ClienteAPI;

    function obtenerKpiDashboard() {
        return get("/dashboard/kpi");
    }

    function obtenerAvancePeriodo(params = {}) {
        const query = new URLSearchParams(params).toString();
        return get(`/reportes/avance-periodo${query ? `?${query}` : ""}`);
    }

    function obtenerResumenActual() {
        return get("/reportes/resumen-actual");
    }

    function obtenerConveniosValoresDeclarados(params = {}) {
        const query = new URLSearchParams(params).toString();
        return get(`/reportes/convenios/valores-declarados${query ? `?${query}` : ""}`);
    }

    function obtenerConveniosImpactos(params = {}) {
        const query = new URLSearchParams(params).toString();
        return get(`/reportes/convenios/impactos${query ? `?${query}` : ""}`);
    }

    function obtenerConveniosImpactosPeriodo(params = {}) {
        const query = new URLSearchParams(params).toString();
        return get(`/reportes/convenios/impactos-periodo${query ? `?${query}` : ""}`);
    }

    function obtenerConveniosCoberturaImpactos(params = {}) {
        const query = new URLSearchParams(params).toString();
        return get(`/reportes/convenios/cobertura-impactos${query ? `?${query}` : ""}`);
    }

    function obtenerFifonafeCobertura(params = {}) {
        const query = new URLSearchParams(params).toString();
        return get(`/reportes/fifonafe/cobertura${query ? `?${query}` : ""}`);
    }

    function obtenerFifonafeIndicadorInstitucional(params = {}) {
        const query = new URLSearchParams(params).toString();
        return get(`/reportes/fifonafe/indicador-institucional${query ? `?${query}` : ""}`);
    }

    function urlExportacionDashboardCsv() {
        return `${window.ClienteAPI.API_BASE_URL}/exportaciones/dashboard.csv`;
    }

    async function obtenerReferenciasReporte(ids = {}, incluirAfectaciones = false) {
        const claves = {nucleos: 'id_proyecto_nucleo', afectaciones: 'id_afectacion', convenios: 'id_convenio'};
        const entradas = Object.entries(claves).flatMap(([tipo, clave]) =>
            [...new Set((ids[tipo] || []).map(Number))].map(id => [clave, id]));
        const respuesta = {nucleos: [], afectaciones: [], convenios: [], incompletas: false};
        let siguiente = 0;
        // Scope is this invocation only. No references or permission results persist here.
        await Promise.all(Array.from({length: Math.min(3, Math.ceil(entradas.length / 100))}, async () => {
            while (siguiente < entradas.length) {
                const lote = entradas.slice(siguiente, siguiente += 100);
                const params = new URLSearchParams(lote);
                if (incluirAfectaciones && params.has('id_proyecto_nucleo')) params.set('incluir_afectaciones', 'true');
                try {
                    const datos = await get(`/reportes/referencias?${params}`);
                    for (const tipo of Object.keys(claves)) if (!Array.isArray(datos?.[tipo])) throw Error('Respuesta no válida');
                    for (const tipo of Object.keys(claves)) {
                        respuesta[tipo].push(...datos[tipo]);
                        const encontrados = new Set(datos[tipo].map(r => Number(r[claves[tipo]])));
                        if (lote.some(([clave, id]) => clave === claves[tipo] && !encontrados.has(id))) respuesta.incompletas = true;
                    }
                } catch {
                    respuesta.incompletas = true;
                }
            }
        }));
        return respuesta;
    }

    function obtenerReferenciasContexto(nucleos) {
        const params = new URLSearchParams([...new Set(nucleos.map(Number))].map(id => ['id_proyecto_nucleo', id]));
        return get(`/reportes/referencias-contexto?${params}`);
    }

    window.ReportesAPI = {
        obtenerReferenciasReporte,
        obtenerReferenciasContexto,
        generalConvenios: (id, params = {}, completo = false) => get(`/proyectos/${encodeURIComponent(id)}/reportes/convenios/general${completo ? '/completo' : ''}?${new URLSearchParams(params)}`),
        entidadesConvenios: id => get(`/proyectos/${encodeURIComponent(id)}/reportes/convenios/general/entidades`),
        obtenerColectivosDestino: (params = {}) => get(`/reportes/convenios/colectivos-destino?${new URLSearchParams(params)}`),
        obtenerResumenConveniosDashboard: idProyecto => get(`/proyectos/${encodeURIComponent(idProyecto)}/dashboard/convenios`),
        obtenerKpiDashboard,
        obtenerAvancePeriodo,
        obtenerResumenActual,
        obtenerConveniosValoresDeclarados,
        obtenerConveniosImpactos,
        obtenerConveniosImpactosPeriodo,
        obtenerConveniosCoberturaImpactos,
        obtenerFifonafeCobertura,
        obtenerFifonafeIndicadorInstitucional,
        urlExportacionDashboardCsv
    };

})();
