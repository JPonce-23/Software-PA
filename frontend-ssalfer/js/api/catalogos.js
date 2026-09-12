/**
 * catalogos.js — GET /catalogos/operativos/{tipo_catalogo}, /entidades, /municipios
 */

(function () {

    const { get } = window.ClienteAPI;

    function obtenerOperativo(tipoCatalogo) {

        return get(`/catalogos/operativos/${encodeURIComponent(tipoCatalogo)}`);

    }

    function obtenerEntidades() {

        return get("/catalogos/entidades");

    }

    function obtenerMunicipios(idEntidad) {

        const query = idEntidad ? `?id_entidad=${encodeURIComponent(idEntidad)}` : "";

        return get(`/catalogos/municipios${query}`);

    }

    function obtenerRequisitosDocumentales() {

        return get("/catalogos/requisitos-documentales");

    }

    window.CatalogosAPI = {
        obtenerOperativo,
        obtenerEntidades,
        obtenerMunicipios,
        obtenerRequisitosDocumentales
    };

})();
