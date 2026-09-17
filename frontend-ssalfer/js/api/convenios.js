/**
 * convenios.js
 *
 * Un convenio siempre nace de una afectación.
 *
 * POST /afectaciones/{id_afectacion}/convenios
 *
 * Los comparecientes pueden viajar anidados durante la creación
 * inicial o administrarse posteriormente mediante sus endpoints.
 */

(function () {
    "use strict";

    const {
        get,
        post,
        patch,
        del
    } = window.ClienteAPI;

    function crearDesdeAfectacion(
        idAfectacion,
        payload
    ) {
        return post(
            `/afectaciones/${idAfectacion}/convenios`,
            payload
        );
    }

    function listarPorAfectacion(
        idAfectacion
    ) {
        return get(
            `/afectaciones/${idAfectacion}/convenios`
        );
    }

    function obtener(
        idConvenio
    ) {
        return get(
            `/convenios/${idConvenio}`
        );
    }

    function actualizar(
        idConvenio,
        payload
    ) {
        return patch(
            `/convenios/${idConvenio}`,
            payload
        );
    }

    /* =====================================================
                        COMPARECIENTES
    ====================================================== */

    function listarComparecientes(
        idConvenio
    ) {
        return get(
            `/convenios/${idConvenio}/comparecientes`
        );
    }

    function agregarCompareciente(
        idConvenio,
        payload
    ) {
        return post(
            `/convenios/${idConvenio}/comparecientes`,
            payload
        );
    }

    function actualizarCompareciente(
        idCompareciente,
        payload
    ) {
        return patch(
            `/convenio-comparecientes/${idCompareciente}`,
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
    function eliminarCompareciente(
        idCompareciente,
        motivo
    ) {
        return del(
            `/convenio-comparecientes/${idCompareciente}`,
            {
                motivo
            }
        );
    }

    /* =====================================================
                    AFECTACIONES ADICIONALES
    ====================================================== */

    function listarAfectacionesAdicionales(
        idConvenio
    ) {
        return get(
            `/convenios/${idConvenio}/afectaciones`
        );
    }

    function agregarAfectacionAdicional(
        idConvenio,
        payload
    ) {
        return post(
            `/convenios/${idConvenio}/afectaciones`,
            payload
        );
    }

    function actualizarAfectacionAdicional(
        idConvenioAfectacion,
        payload
    ) {
        return patch(
            `/convenio-afectaciones/${idConvenioAfectacion}`,
            payload
        );
    }

    /* =====================================================
                         TRÁMITES RAN
    ====================================================== */

    function listarTramitesRan(
        idConvenio
    ) {
        return get(
            `/convenios/${idConvenio}/tramites-ran`
        );
    }

    window.ConveniosAPI = {
        crearDesdeAfectacion,
        listarPorAfectacion,
        obtener,
        actualizar,
        listarComparecientes,
        agregarCompareciente,
        actualizarCompareciente,
        eliminarCompareciente,
        listarAfectacionesAdicionales,
        agregarAfectacionAdicional,
        actualizarAfectacionAdicional,
        listarTramitesRan
    };

})();