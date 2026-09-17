/**
 * parcelas.js — /proyecto-nucleo/{id}/parcelas, /parcelas/{id}, /parcelas/{id}/titulares
 * (No incluye PATCH /parcelas/{id}/geometria: excluido, es geo/mapa.)
 */

(function () {

    const { get, post, patch } = window.ClienteAPI;

    function listarPorProyectoNucleo(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/parcelas`);
    }

    function crear(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/parcelas`, payload);
    }

    function obtener(idParcela) {
        return get(`/parcelas/${idParcela}`);
    }

    function actualizar(idParcela, payload) {
        return patch(`/parcelas/${idParcela}`, payload);
    }

    function listarTitulares(idParcela) {
        return get(`/parcelas/${idParcela}/titulares`);
    }

    function agregarTitular(idParcela, payload) {
        return post(`/parcelas/${idParcela}/titulares`, payload);
    }

    function actualizarTitular(idParcelaTitular, payload) {
        return patch(`/parcela-titulares/${idParcelaTitular}`, payload);
    }

    window.ParcelasAPI = {
        listarPorProyectoNucleo,
        crear,
        obtener,
        actualizar,
        listarTitulares,
        agregarTitular,
        actualizarTitular
    };

})();
