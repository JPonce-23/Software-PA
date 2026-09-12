/**
 * nucleos.js — /nucleos, /proyecto-nucleo/{id}, referencias, responsables
 * (No incluye PATCH /nucleos/{id}/geometria: excluido, es geo/mapa.)
 */

(function () {

    const { get, post, patch } = window.ClienteAPI;

    function listar() {
        return get("/nucleos");
    }

    function obtener(idNucleo) {
        return get(`/nucleos/${idNucleo}`);
    }

    function crear(payload) {
        return post("/nucleos", payload);
    }

    function actualizar(idNucleo, payload) {
        return patch(`/nucleos/${idNucleo}`, payload);
    }

    function listarPorProyecto(idProyecto) {
        return get(`/proyectos/${idProyecto}/nucleos`);
    }

    function vincularAProyecto(idProyecto, payload) {
        return post(`/proyectos/${idProyecto}/nucleos`, payload);
    }

    function obtenerProyectoNucleo(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}`);
    }

    function actualizarProyectoNucleo(idProyectoNucleo, payload) {
        return patch(`/proyecto-nucleo/${idProyectoNucleo}`, payload);
    }

    function eliminarProyectoNucleo(idProyectoNucleo) {
        return window.ClienteAPI.del(`/proyecto-nucleo/${idProyectoNucleo}`);
    }

    function listarReferencias(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/referencias`);
    }

    function crearReferencia(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/referencias`, payload);
    }

    function actualizarReferencia(idReferencia, payload) {
        return patch(`/referencias/${idReferencia}`, payload);
    }

    function listarResponsables(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/responsables`);
    }

    function crearResponsable(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/responsables`, payload);
    }

    function actualizarResponsable(idResponsable, payload) {
        return patch(`/responsables/${idResponsable}`, payload);
    }

    window.NucleosAPI = {
        listar,
        obtener,
        crear,
        actualizar,
        listarPorProyecto,
        vincularAProyecto,
        obtenerProyectoNucleo,
        actualizarProyectoNucleo,
        eliminarProyectoNucleo,
        listarReferencias,
        crearReferencia,
        actualizarReferencia,
        listarResponsables,
        crearResponsable,
        actualizarResponsable
    };

})();
