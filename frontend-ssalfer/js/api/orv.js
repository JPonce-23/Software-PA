/**
 * orv.js
 *
 * Órganos de Representación y Vigilancia.
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
            )}/orv`
        );
    }

    function crear(
        idProyectoNucleo,
        payload
    ) {
        return post(
            `/proyecto-nucleo/${encodeURIComponent(
                idProyectoNucleo
            )}/orv`,
            payload
        );
    }

    function actualizar(
        idOrv,
        payload
    ) {
        return patch(
            `/orv/${encodeURIComponent(
                idOrv
            )}`,
            payload
        );
    }

    function listarIntegrantes(
        idOrv
    ) {
        return get(
            `/orv/${encodeURIComponent(
                idOrv
            )}/integrantes`
        );
    }

    function agregarIntegrante(
        idOrv,
        payload
    ) {
        return post(
            `/orv/${encodeURIComponent(
                idOrv
            )}/integrantes`,
            payload
        );
    }

    function actualizarIntegrante(
        idOrvIntegrante,
        payload
    ) {
        return patch(
            `/orv-integrantes/${encodeURIComponent(
                idOrvIntegrante
            )}`,
            payload
        );
    }

    function listarTramitesRan(
        idOrv
    ) {
        return get(
            `/orv/${encodeURIComponent(
                idOrv
            )}/tramites-ran`
        );
    }

    window.OrvAPI = {
        listarPorProyectoNucleo,
        crear,
        actualizar,
        listarIntegrantes,
        agregarIntegrante,
        actualizarIntegrante,
        listarTramitesRan
    };

})();