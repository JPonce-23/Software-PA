/**
 * padrones.js
 *
 * Historial de padrones de un núcleo agrario.
 */

(function () {
    "use strict";

    const {
        get,
        post,
        patch
    } = window.ClienteAPI;

    function listarPorProyectoNucleo(
        idProyectoNucleo
    ) {
        return get(
            `/proyecto-nucleo/${encodeURIComponent(
                idProyectoNucleo
            )}/padrones`
        );
    }

    function crear(
        idProyectoNucleo,
        payload
    ) {
        return post(
            `/proyecto-nucleo/${encodeURIComponent(
                idProyectoNucleo
            )}/padrones`,
            payload
        );
    }

    function actualizar(
        idPadron,
        payload
    ) {
        return patch(
            `/padrones/${encodeURIComponent(
                idPadron
            )}`,
            payload
        );
    }

    window.PadronesAPI = {
        listarPorProyectoNucleo,
        crear,
        actualizar
    };

})();