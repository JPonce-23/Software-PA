/**
 * seguimiento.js
 *
 * Endpoints reales:
 * GET    /proyecto-nucleo/{id}/seguimiento
 * POST   /proyecto-nucleo/{id}/seguimiento
 * GET    /seguimiento/{id}
 * PATCH  /seguimiento/{id}
 * DELETE /seguimiento/{id}
 */

(function () {
    "use strict";

    const {
        get,
        post,
        patch,
        del
    } = window.ClienteAPI;

    function listarPorProyectoNucleo(
        idProyectoNucleo
    ) {
        return get(
            `/proyecto-nucleo/${encodeURIComponent(
                idProyectoNucleo
            )}/seguimiento`
        );
    }

    function obtener(
        idSeguimientoEvento
    ) {
        return get(
            `/seguimiento/${encodeURIComponent(
                idSeguimientoEvento
            )}`
        );
    }

    function crear(
        idProyectoNucleo,
        payload
    ) {
        return post(
            `/proyecto-nucleo/${encodeURIComponent(
                idProyectoNucleo
            )}/seguimiento`,
            payload
        );
    }

    function actualizar(
        idSeguimientoEvento,
        payload
    ) {
        return patch(
            `/seguimiento/${encodeURIComponent(
                idSeguimientoEvento
            )}`,
            payload
        );
    }

    /*
     * DELETE requiere BajaRequest:
     *
     * {
     *     motivo: "..."
     * }
     */
    function eliminar(
        idSeguimientoEvento,
        motivo
    ) {
        return del(
            `/seguimiento/${encodeURIComponent(
                idSeguimientoEvento
            )}`,
            {
                motivo
            }
        );
    }

    window.SeguimientoAPI = {
        listarPorProyectoNucleo,
        obtener,
        crear,
        actualizar,
        eliminar
    };

})();