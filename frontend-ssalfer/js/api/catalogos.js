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

    let tiposActivos;
    function tiposDocumento(incluirInactivos=false){
        if(incluirInactivos)return get('/catalogos/tipos-documento?incluir_inactivos=true');
        return tiposActivos ||= get('/catalogos/tipos-documento').catch(e=>{tiposActivos=null;throw e;});
    }
    window.CatalogosAPI = {
        tiposDocumento,
        buscarNucleos: (params = {}) => get(`/catalogos/nucleos?${new URLSearchParams(params)}`),
        obtenerOperativo,
        obtenerEntidades,
        obtenerMunicipios,
        obtenerRequisitosDocumentales
    };

})();
