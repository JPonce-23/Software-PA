/**
 * afectaciones.js — /proyecto-nucleo/{id}/afectaciones, /afectaciones/{id}
 */

(function () {

    const { get, post, patch, del } = window.ClienteAPI;

    function listarPorProyectoNucleo(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/afectaciones`);
    }

    function crear(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/afectaciones`, payload);
    }

    function obtener(idAfectacion) {
        return get(`/afectaciones/${idAfectacion}`);
    }

    function actualizar(idAfectacion, payload) {
        return patch(`/afectaciones/${idAfectacion}`, payload);
    }

    function eliminar(idAfectacion, motivo) {
        return del(`/afectaciones/${idAfectacion}`, { motivo });
    }

    window.AfectacionesAPI = {
        listarPorProyectoNucleo,
        crear,
        obtener,
        actualizar,
        eliminar
    };

})();