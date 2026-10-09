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
        idOrv,
        incluirHistorico = true,
        incluirBajas = false
    ) {

        return get(
            `/orv/${encodeURIComponent(
                idOrv
            )}/integrantes?incluir_historico=${
                incluirHistorico
                    ? "true"
                    : "false"
            }&incluir_bajas=${incluirBajas ? "true" : "false"}`
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


    function finalizarIntegrante(
        idOrvIntegrante,
        payload
    ) {

        return post(
            `/orv-integrantes/${encodeURIComponent(
                idOrvIntegrante
            )}/finalizar`,
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
        reactivarIntegrante: id => window.ClienteAPI.post(`/orv-integrantes/${id}/reactivar`, null),
        eliminarIntegrante: (id, motivo) => window.ClienteAPI.del(`/orv-integrantes/${id}`, { motivo }),

        listarPorProyectoNucleo,

        crear,

        actualizar,

        listarIntegrantes,

        agregarIntegrante,

        actualizarIntegrante,

        finalizarIntegrante,

        listarTramitesRan

    };

})();
