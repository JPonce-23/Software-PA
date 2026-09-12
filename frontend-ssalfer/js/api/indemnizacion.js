/**
 * indemnizacion.js — /afectaciones/{id}/indemnizacion, /indemnizaciones/{id},
 * /indemnizaciones/{id}/pagos, /pagos/{id}
 */

(function () {

    const { get, post, patch } = window.ClienteAPI;

    function listarPorAfectacion(idAfectacion) {
        return get(`/afectaciones/${idAfectacion}/indemnizacion`);
    }

    function crear(idAfectacion, payload) {
        return post(`/afectaciones/${idAfectacion}/indemnizacion`, payload);
    }

    function actualizar(idIndemnizacion, payload) {
        return patch(`/indemnizaciones/${idIndemnizacion}`, payload);
    }

    function listarPagos(idIndemnizacion) {
        return get(`/indemnizaciones/${idIndemnizacion}/pagos`);
    }

    function registrarPago(idIndemnizacion, payload) {
        return post(`/indemnizaciones/${idIndemnizacion}/pagos`, payload);
    }

    function actualizarPago(idPago, payload) {
        return patch(`/pagos/${idPago}`, payload);
    }

    window.IndemnizacionAPI = {
        listarPorAfectacion,
        crear,
        actualizar,
        listarPagos,
        registrarPago,
        actualizarPago
    };

})();
