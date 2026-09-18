/**
 * personas.js
 *
 * Personas registradas en SSALFER.
 *
 * Backend disponible:
 *
 * POST   /proyectos/{id_proyecto}/personas
 * GET    /personas/{id_persona}
 * PATCH  /personas/{id_persona}
 * DELETE /personas/{id_persona}
 * POST   /personas/{id_persona}/reactivar
 *
 * Importante:
 * actualmente no existe un endpoint para listar o buscar
 * personas de un proyecto por nombre, CURP, etc.
 */

(function () {

    "use strict";


    const {
        get,
        post,
        patch,
        del
    } = window.ClienteAPI;


    function crear(
        idProyecto,
        payload
    ) {

        return post(
            `/proyectos/${encodeURIComponent(
                idProyecto
            )}/personas`,
            payload
        );

    }


    function obtener(
        idPersona
    ) {

        return get(
            `/personas/${encodeURIComponent(
                idPersona
            )}`
        );

    }


    function actualizar(
        idPersona,
        payload
    ) {

        return patch(
            `/personas/${encodeURIComponent(
                idPersona
            )}`,
            payload
        );

    }


    function darDeBaja(
        idPersona,
        motivo
    ) {

        return del(
            `/personas/${encodeURIComponent(
                idPersona
            )}`,
            {
                motivo
            }
        );

    }


    function reactivar(
        idPersona
    ) {

        return post(
            `/personas/${encodeURIComponent(
                idPersona
            )}/reactivar`
        );

    }


    window.PersonasAPI = {

        crear,

        obtener,

        actualizar,

        darDeBaja,

        reactivar

    };

})();