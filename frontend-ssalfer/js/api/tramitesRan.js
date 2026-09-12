/**
 * tramitesRan.js
 *
 * Un trámite RAN se crea con exactamente uno de:
 *
 * - id_asamblea
 * - id_convenio
 * - id_orv
 *
 * No existe POST independiente por proyecto-núcleo.
 */

(function () {
    "use strict";

    const {
        get,
        post,
        patch
    } = window.ClienteAPI;

    function crear(
        payload
    ) {
        return post(
            "/tramites-ran",
            payload
        );
    }

    function obtener(
        idTramiteRan
    ) {
        return get(
            `/tramites-ran/${encodeURIComponent(
                idTramiteRan
            )}`
        );
    }

    function listarPorAsamblea(
        idAsamblea
    ) {
        return get(
            `/asambleas/${encodeURIComponent(
                idAsamblea
            )}/tramites-ran`
        );
    }

    function listarPorConvenio(
        idConvenio
    ) {
        return get(
            `/convenios/${encodeURIComponent(
                idConvenio
            )}/tramites-ran`
        );
    }

    function listarPorOrv(
        idOrv
    ) {
        return get(
            `/orv/${encodeURIComponent(
                idOrv
            )}/tramites-ran`
        );
    }

    function listarPorProyectoNucleo(
        idProyectoNucleo
    ) {
        return get(
            `/proyecto-nucleo/${encodeURIComponent(
                idProyectoNucleo
            )}/tramites-ran`
        );
    }

    function listarEventos(
        idTramiteRan
    ) {
        return get(
            `/tramites-ran/${encodeURIComponent(
                idTramiteRan
            )}/eventos`
        );
    }

    function crearEvento(
        idTramiteRan,
        payload
    ) {
        return post(
            `/tramites-ran/${encodeURIComponent(
                idTramiteRan
            )}/eventos`,
            payload
        );
    }

    function actualizarEvento(
        idEventoRan,
        payload
    ) {
        return patch(
            `/eventos-ran/${encodeURIComponent(
                idEventoRan
            )}`,
            payload
        );
    }

    window.TramitesRanAPI = {
        crear,
        obtener,
        listarPorAsamblea,
        listarPorConvenio,
        listarPorOrv,
        listarPorProyectoNucleo,
        listarEventos,
        crearEvento,
        actualizarEvento
    };

})();