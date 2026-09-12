/**
 * fifonafe.js
 *
 * Contrato real del backend.
 */

(function () {
    "use strict";

    const {
        get,
        post,
        patch,
        del
    } = window.ClienteAPI;


    /* =====================================================
                        TRÁMITES
    ====================================================== */

    function listarPorProyectoNucleo(
        idProyectoNucleo
    ) {
        return get(
            `/proyecto-nucleo/${encodeURIComponent(
                idProyectoNucleo
            )}/fifonafe`
        );
    }

    function crear(
        idProyectoNucleo,
        payload
    ) {
        return post(
            `/proyecto-nucleo/${encodeURIComponent(
                idProyectoNucleo
            )}/fifonafe`,
            payload
        );
    }

    function actualizar(
        idTramiteFifonafe,
        payload
    ) {
        return patch(
            `/fifonafe/${encodeURIComponent(
                idTramiteFifonafe
            )}`,
            payload
        );
    }


    /* =====================================================
                        AFECTACIONES
    ====================================================== */

    function agregarAfectacion(
        idTramiteFifonafe,
        idAfectacion
    ) {
        return post(
            `/fifonafe/${encodeURIComponent(
                idTramiteFifonafe
            )}/afectaciones`,
            {
                id_afectacion: Number(
                    idAfectacion
                )
            }
        );
    }


    /* =====================================================
                        EVENTOS
    ====================================================== */

    function listarEventos(
        idTramiteFifonafe
    ) {
        return get(
            `/fifonafe/${encodeURIComponent(
                idTramiteFifonafe
            )}/eventos`
        );
    }

    function crearEvento(
        idTramiteFifonafe,
        payload
    ) {
        return post(
            `/fifonafe/${encodeURIComponent(
                idTramiteFifonafe
            )}/eventos`,
            payload
        );
    }

    function actualizarEvento(
        idEventoFifonafe,
        payload
    ) {
        return patch(
            `/eventos-fifonafe/${encodeURIComponent(
                idEventoFifonafe
            )}`,
            payload
        );
    }

    function eliminarEvento(
        idEventoFifonafe,
        motivo
    ) {
        return del(
            `/eventos-fifonafe/${encodeURIComponent(
                idEventoFifonafe
            )}`,
            {
                motivo
            }
        );
    }


    /* =====================================================
                        INTERVINIENTES
    ====================================================== */

    function listarIntervinientes(
        idTramiteFifonafe
    ) {
        return get(
            `/fifonafe/${encodeURIComponent(
                idTramiteFifonafe
            )}/intervinientes`
        );
    }

    function agregarInterviniente(
        idTramiteFifonafe,
        payload
    ) {
        return post(
            `/fifonafe/${encodeURIComponent(
                idTramiteFifonafe
            )}/intervinientes`,
            payload
        );
    }

    function eliminarInterviniente(
        idIntervinienteFifonafe,
        motivo
    ) {
        return del(
            `/intervinientes-fifonafe/${encodeURIComponent(
                idIntervinienteFifonafe
            )}`,
            {
                motivo
            }
        );
    }


    /* =====================================================
                        EXPORTAR API
    ====================================================== */

    window.FifonafeAPI = {
        listarPorProyectoNucleo,
        crear,
        actualizar,

        agregarAfectacion,

        listarEventos,
        crearEvento,
        actualizarEvento,
        eliminarEvento,

        listarIntervinientes,
        agregarInterviniente,
        eliminarInterviniente
    };

})();