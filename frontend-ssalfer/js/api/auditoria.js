/**
 * js/api/auditoria.js
 * Consultas administrativas de auditoría.
 *
 * Backend:
 *   GET /auditoria/cambios
 *   GET /auditoria/accesos
 *
 * Ambos endpoints son de solo lectura y el backend exige rol admin.
 * No usa fetch() directamente: todo pasa por ClienteAPI.
 */
(function () {
    "use strict";

    const { get } = window.ClienteAPI;

    function construirQuery(parametros = {}) {
        const query = new URLSearchParams();

        Object.entries(parametros).forEach(([clave, valor]) => {
            if (
                valor === null ||
                valor === undefined ||
                valor === ""
            ) {
                return;
            }

            query.set(clave, String(valor));
        });

        const texto = query.toString();

        return texto
            ? `?${texto}`
            : "";
    }

    function listarCambios(parametros = {}) {
        return get(
            `/auditoria/cambios${construirQuery(parametros)}`
        );
    }

    function listarAccesos(parametros = {}) {
        return get(
            `/auditoria/accesos${construirQuery(parametros)}`
        );
    }

    window.AuditoriaAPI = {
        listarCambios,
        listarAccesos
    };
})();