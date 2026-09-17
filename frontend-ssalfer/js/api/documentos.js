/**
 * documentos.js — /documentos/objetivos/{entidad_tipo}/{entidad_id}, versiones,
 * vínculos, /trazabilidad/objetivos/{entidad_tipo}/{entidad_id}, requisitos documentales.
 */

(function () {

    const { get, post, patch, del } = window.ClienteAPI;

    function listarPorEntidad(entidadTipo, entidadId) {
        return get(`/documentos/objetivos/${entidadTipo}/${entidadId}`);
    }

    function crearParaEntidad(entidadTipo, entidadId, payload) {
        return post(`/documentos/objetivos/${entidadTipo}/${entidadId}`, payload);
    }

    function actualizar(idDocumento, payload) {
        return patch(`/documentos/${idDocumento}`, payload);
    }

    function eliminar(idDocumento) {
        return del(`/documentos/${idDocumento}`);
    }

    function listarVersiones(idDocumento) {
        return get(`/documentos/${idDocumento}/versiones`);
    }

    function subirVersion(idDocumento, payload) {
        return post(`/documentos/${idDocumento}/versiones`, payload);
    }

    function urlDescargaVersion(idVersion) {
        return `${window.ClienteAPI.API_BASE_URL}/documentos/versiones/${idVersion}/descarga`;
    }

    function vincularAEntidad(idDocumento, entidadTipo, entidadId) {
        return post(`/documentos/${idDocumento}/vinculos/${entidadTipo}/${entidadId}`, null);
    }

    function listarTrazabilidad(entidadTipo, entidadId) {
        return get(`/trazabilidad/objetivos/${entidadTipo}/${entidadId}`);
    }

    function registrarTrazabilidad(entidadTipo, entidadId, payload) {
        return post(`/trazabilidad/objetivos/${entidadTipo}/${entidadId}`, payload);
    }

    function listarRequisitosPorProyectoNucleo(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/requisitos-documentales`);
    }

    function crearRequisito(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/requisitos-documentales`, payload);
    }

    function actualizarRequisito(idExpedienteRequisito, payload) {
        return patch(`/requisitos-documentales/${idExpedienteRequisito}`, payload);
    }

    function listarCatalogoRequisitos() {
        return get("/catalogos/requisitos-documentales");
    }


    window.DocumentosAPI = {
        listarPorEntidad,
        crearParaEntidad,
        actualizar,
        eliminar,
        listarVersiones,
        subirVersion,
        urlDescargaVersion,
        vincularAEntidad,
        listarTrazabilidad,
        registrarTrazabilidad,
        listarRequisitosPorProyectoNucleo,
        listarCatalogoRequisitos,
        crearRequisito,
        actualizarRequisito
    };

})();
