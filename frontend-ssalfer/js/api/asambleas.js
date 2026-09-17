/**
 * asambleas.js — /proyecto-nucleo/{id}/asambleas, /asambleas/{id}, convocatorias
 */

(function () {

    const { get, post, patch } = window.ClienteAPI;

    function listarPorProyectoNucleo(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/asambleas`);
    }

    function crear(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/asambleas`, payload);
    }

    function actualizar(idAsamblea, payload) {
        return patch(`/asambleas/${idAsamblea}`, payload);
    }

    function listarConvocatorias(idAsamblea) {
        return get(`/asambleas/${idAsamblea}/convocatorias`);
    }

    function crearConvocatoria(idAsamblea, payload) {
        return post(`/asambleas/${idAsamblea}/convocatorias`, payload);
    }

    function actualizarConvocatoria(idConvocatoria, payload) {
        return patch(`/convocatorias/${idConvocatoria}`, payload);
    }

    function listarTramitesRan(idAsamblea) {
        return get(`/asambleas/${idAsamblea}/tramites-ran`);
    }

    window.AsambleasAPI = {
        listarPorProyectoNucleo,
        crear,
        actualizar,
        listarConvocatorias,
        crearConvocatoria,
        actualizarConvocatoria,
        listarTramitesRan
    };

})();
