/**
 * proyectos.js — /proyectos, /proyectos/{id}, /proyectos/{id}/usuarios, /proyectos/{id}/trazos
 * (No incluye /proyectos/{id}/mapa: excluido de esta ronda por falta de
 * autorización de mapas, ver docs del proyecto.)
 */

(function () {

    const { get, post, patch, del } = window.ClienteAPI;

    function listar(params = {}) {
        const query = new URLSearchParams(params).toString();
        return get(`/proyectos${query ? `?${query}` : ""}`);
    }

    function obtener(idProyecto) {
        return get(`/proyectos/${idProyecto}`);
    }

    function crear(payload) {
        return post("/proyectos", payload);
    }

    function actualizar(idProyecto, payload) {
        return patch(`/proyectos/${idProyecto}`, payload);
    }

    function eliminar(idProyecto) {
        return del(`/proyectos/${idProyecto}`);
    }

    function listarUsuarios(idProyecto) {
        return get(`/proyectos/${idProyecto}/usuarios`);
    }

    function agregarUsuario(idProyecto, payload) {
        return post(`/proyectos/${idProyecto}/usuarios`, payload);
    }

    function listarTrazos(idProyecto) {
        return get(`/proyectos/${idProyecto}/trazos`);
    }

    function crearTrazo(idProyecto, payload) {
        return post(`/proyectos/${idProyecto}/trazos`, payload);
    }

    window.ProyectosAPI = {
        revocarUsuario: (idProyecto, idUsuario, motivo) => del(`/proyectos/${idProyecto}/usuarios/${idUsuario}`, { motivo }),
        listar,
        obtener,
        crear,
        actualizar,
        eliminar,
        listarUsuarios,
        agregarUsuario,
        listarTrazos,
        crearTrazo
    };

})();
