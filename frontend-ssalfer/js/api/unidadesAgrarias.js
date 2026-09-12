/**
 * unidadesAgrarias.js — /proyecto-nucleo/{id}/unidades-agrarias,
 * /unidades-agrarias/{id}, titulares y vínculos con afectaciones.
 */

(function () {

    const { get, post, patch, del } = window.ClienteAPI;

    function listarPorProyectoNucleo(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/unidades-agrarias`);
    }

    function crear(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/unidades-agrarias`, payload);
    }

    function obtener(idUnidad) {
        return get(`/unidades-agrarias/${idUnidad}`);
    }

    function actualizar(idUnidad, payload) {
        return patch(`/unidades-agrarias/${idUnidad}`, payload);
    }

    function eliminar(idUnidad, motivo) {
        return del(`/unidades-agrarias/${idUnidad}`, { motivo });
    }

    function listarTitulares(idUnidad) {
        return get(`/unidades-agrarias/${idUnidad}/titulares`);
    }

    function agregarTitular(idUnidad, payload) {
        return post(`/unidades-agrarias/${idUnidad}/titulares`, payload);
    }

    function actualizarTitular(idUnidadTitular, payload) {
        return patch(`/unidad-agraria-titulares/${idUnidadTitular}`, payload);
    }

    function eliminarTitular(idUnidadTitular, motivo) {
        return del(`/unidad-agraria-titulares/${idUnidadTitular}`, { motivo });
    }

    function listarPorAfectacion(idAfectacion) {
        return get(`/afectaciones/${idAfectacion}/unidades-agrarias`);
    }

    function vincularAAfectacion(idAfectacion, payload) {
        return post(`/afectaciones/${idAfectacion}/unidades-agrarias`, payload);
    }

    function actualizarVinculo(idAfectacionUnidad, payload) {
        return patch(`/afectacion-unidades-agrarias/${idAfectacionUnidad}`, payload);
    }

    function eliminarVinculo(idAfectacionUnidad, motivo) {
        return del(`/afectacion-unidades-agrarias/${idAfectacionUnidad}`, { motivo });
    }

    window.UnidadesAgrariasAPI = {
        listarPorProyectoNucleo,
        crear,
        obtener,
        actualizar,
        eliminar,
        listarTitulares,
        agregarTitular,
        actualizarTitular,
        eliminarTitular,
        listarPorAfectacion,
        vincularAAfectacion,
        actualizarVinculo,
        eliminarVinculo
    };

})();