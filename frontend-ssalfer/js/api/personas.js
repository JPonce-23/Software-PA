/**
 * personas.js — POST /proyectos/{id_proyecto}/personas
 *
 * IMPORTANTE: el backend NO tiene ningún endpoint de listado/búsqueda de
 * personas (ni /personas ni /proyectos/{id}/personas en GET). Solo existe
 * la creación. Para mostrar personas ya existentes hay que reutilizar los
 * listados scoped de otras entidades:
 *   - GET /orv/{id_orv}/integrantes
 *   - GET /parcelas/{id_parcela}/titulares
 * Ver docs/notas del proyecto: esto es un pendiente para el equipo de
 * backend (se necesitaría algo como GET /proyectos/{id_proyecto}/personas).
 */

(function () {

    const { post } = window.ClienteAPI;

    function crear(idProyecto, payload) {
        return post(`/proyectos/${idProyecto}/personas`, payload);
    }

    window.PersonasAPI = {
        crear
    };

})();
