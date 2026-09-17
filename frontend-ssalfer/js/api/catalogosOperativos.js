/**
 * js/api/catalogosOperativos.js
 * Administración de catálogos operativos.
 *
 * Backend:
 *   GET   /catalogos/operativos/{tipo_catalogo}
 *   POST  /catalogos/operativos
 *   PATCH /catalogos/operativos/opciones/{id_catalogo_opcion}
 *
 * No usa fetch() directamente.
 */
(function () {
    "use strict";

    const { get, post, patch } = window.ClienteAPI;

    function listar(tipoCatalogo, { incluirInactivos = false } = {}) {
        const tipo = encodeURIComponent(tipoCatalogo);

        const query =
            incluirInactivos
                ? "?incluir_inactivos=true"
                : "";

        return get(
            `/catalogos/operativos/${tipo}${query}`
        );
    }

    function crear(payload) {
        return post(
            "/catalogos/operativos",
            payload
        );
    }

    function actualizar(idCatalogoOpcion, payload) {
        return patch(
            `/catalogos/operativos/opciones/${encodeURIComponent(idCatalogoOpcion)}`,
            payload
        );
    }

    function desactivar(idCatalogoOpcion, motivoBaja) {
        return actualizar(
            idCatalogoOpcion,
            {
                activo: false,
                motivo_baja: motivoBaja
            }
        );
    }

    window.CatalogosOperativosAPI = {
        listar,
        crear,
        actualizar,
        desactivar
    };
})();