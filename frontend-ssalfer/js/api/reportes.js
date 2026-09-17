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

    window.ReportesAPI = {
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
