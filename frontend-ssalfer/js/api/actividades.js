/**
 * actividades.js — /proyecto-nucleo/{id}/actividades, /actividades/{id}
 */

(function () {

    const { get, post, patch } = window.ClienteAPI;

    function listarPorProyectoNucleo(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/actividades`);
    }

    function crear(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/actividades`, payload);
    }

    function actualizar(idActividad, payload) {
        return patch(`/actividades/${idActividad}`, payload);
    }

    window.ActividadesAPI = {
        listarPorProyectoNucleo,
        crear,
        actualizar
    };

})();
