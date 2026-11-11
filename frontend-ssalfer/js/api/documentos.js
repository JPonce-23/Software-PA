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

    function eliminar(idDocumento, motivo) {
        return del(`/documentos/${idDocumento}`, { motivo });
    }

    function listarVersiones(idDocumento) {
        return get(`/documentos/${idDocumento}/versiones`);
    }

    function nuevaClaveCarga() {
        const crypto = window.crypto;
        if (crypto?.randomUUID) return crypto.randomUUID();
        if (!crypto?.getRandomValues) throw new Error("No se pudo preparar una clave segura para la carga.");
        const bytes = crypto.getRandomValues(new Uint8Array(16));
        bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
        const hex = Array.from(bytes, n => n.toString(16).padStart(2, "0")).join("");
        return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
    }

    async function subirVersion(idDocumento, payload, clave = null) {
        try {
            return await post(`/documentos/${idDocumento}/versiones`, payload, { idempotencyKey: clave });
        } catch (error) {
            // Interpret only upload errors. Never rotate a key or retry here.
            const mensajes = {
                DOCUMENT_DUPLICATE: [409, "Este archivo ya está registrado en el documento. Consulta el historial de versiones."],
                DOCUMENT_IDEMPOTENCY_CONFLICT: [409, "Esta clave corresponde a otra carga. Selecciona nuevamente el archivo para iniciar una carga distinta."],
                DOCUMENT_RECONCILIATION_REQUIRED: [null, "El resultado de la carga requiere revisión. Conserva la clave y solicita ayuda antes de iniciar otra carga."],
                DOCUMENT_OPERATION_PENDING: [425, "La carga sigue pendiente. Conserva la clave y vuelve a consultar o reintentar más tarde."],
                DOCUMENT_OPERATION_REJECTED: [null, "La operación anterior fue rechazada. Selecciona nuevamente el archivo para iniciar otra carga."],
                DOCUMENT_INTEGRITY_CONFLICT: [409, "La carga presenta un conflicto de integridad. Consulta el historial o solicita revisión."],
                DOCUMENT_REQUEST_CONFLICT: [409, "La solicitud no puede completarse en su estado actual. Revisa el documento y sus vínculos."]
            };
            const entrada = Object.hasOwn(mensajes, error?.documentErrorCode) ? mensajes[error.documentErrorCode] : null;
            if (entrada && (entrada[0] === null || entrada[0] === error.status)) error.message = entrada[1];
            throw error;
        }
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
        return window.CatalogosAPI.obtenerRequisitosDocumentales();
    }


    window.DocumentosAPI = {
        listarConsolidados: id => get(`/proyecto-nucleo/${encodeURIComponent(id)}/documentos`),
        nombreTipo: d => d?.clasificacion?.nombre || d?.tipo_documento || 'Sin clasificación',
        listarPorEntidad,
        crearParaEntidad,
        actualizar,
        eliminar,
        listarVersiones,
        subirVersion,
        nuevaClaveCarga,
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
