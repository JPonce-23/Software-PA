/**
 * nucleos.js — /nucleos, /proyecto-nucleo/{id}, referencias, responsables
 * (No incluye PATCH /nucleos/{id}/geometria: excluido, es geo/mapa.)
 */

(function () {

    const { get, post, patch } = window.ClienteAPI;

    function listar() {
        return get("/nucleos");
    }

    function obtener(idNucleo) {
        return get(`/nucleos/${idNucleo}`);
    }

    function crear(payload) {
        return post("/nucleos", payload);
    }

    function actualizar(idNucleo, payload) {
        return patch(`/nucleos/${idNucleo}`, payload);
    }

    function listarPorProyecto(idProyecto) {
        return get(`/proyectos/${idProyecto}/nucleos`);
    }

    function vincularAProyecto(idProyecto, payload) {
        return post(`/proyectos/${idProyecto}/nucleos`, payload);
    }

    function obtenerProyectoNucleo(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}`);
    }

    function actualizarProyectoNucleo(idProyectoNucleo, payload) {
        return patch(`/proyecto-nucleo/${idProyectoNucleo}`, payload);
    }

    function eliminarProyectoNucleo(idProyectoNucleo, motivo) {
        return window.ClienteAPI.del(`/proyecto-nucleo/${idProyectoNucleo}`, { motivo });
    }

    function listarReferencias(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/referencias`);
    }

    function crearReferencia(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/referencias`, payload);
    }

    function actualizarReferencia(idReferencia, payload) {
        return patch(`/referencias/${idReferencia}`, payload);
    }

    function listarResponsables(idProyectoNucleo) {
        return get(`/proyecto-nucleo/${idProyectoNucleo}/responsables`);
    }

    function crearResponsable(idProyectoNucleo, payload) {
        return post(`/proyecto-nucleo/${idProyectoNucleo}/responsables`, payload);
    }

    function actualizarResponsable(idResponsable, payload) {
        return patch(`/responsables/${idResponsable}`, payload);
    }


    const camposResumen = ['total_nucleos', 'total_convenios', 'individuales', 'colectivos', 'formalizados'];
    const incompleto = () => new Error('No se pudo comprobar que la información esté completa. No se descargó ningún archivo. Vuelve a intentar.');
    const cambio = () => Object.assign(new Error('La información cambió durante la exportación. Actualiza el dashboard y vuelve a exportar.'), {status: 409});
    const comprobarCancelacion = signal => signal?.throwIfAborted();

    async function resumenDashboard(idProyecto, {signal} = {}) {
        const resumen = await get(`/proyectos/${idProyecto}/dashboard/resumen`, {signal, silencioso: true});
        comprobarCancelacion(signal);
        if (!resumen || camposResumen.some(c => !Number.isSafeInteger(resumen[c]) || resumen[c] < 0) ||
            resumen.individuales + resumen.colectivos > resumen.total_convenios ||
            resumen.formalizados > resumen.individuales + resumen.colectivos) throw incompleto();
        return resumen;
    }

    function comprobarPagina(pagina, {campoId, cursor, limit, revision, total}) {
        if (!pagina || !Array.isArray(pagina.items) || pagina.items.length > limit ||
            !Number.isSafeInteger(pagina.total) || pagina.total < 0 ||
            !/^[a-f0-9]{32}$/.test(pagina.revision) || typeof pagina.hay_mas !== 'boolean') throw incompleto();
        if ((revision !== undefined && pagina.revision !== revision) ||
            (total !== undefined && pagina.total !== total)) throw cambio();
        let ultimo = cursor;
        for (const item of pagina.items) {
            if (!Number.isSafeInteger(item?.[campoId]) || item[campoId] <= ultimo) throw incompleto();
            ultimo = item[campoId];
        }
        if (pagina.hay_mas ? (!pagina.items.length || pagina.siguiente_id !== ultimo) : pagina.siguiente_id !== null) throw incompleto();
        if (pagina.items.length > pagina.total) throw incompleto();
    }

    async function paginaExportacion(idProyecto, recurso, parametros, signal) {
        const pagina = await get(`/proyectos/${idProyecto}/dashboard/exportacion/${recurso}?${new URLSearchParams(parametros)}`, {signal, silencioso: true});
        comprobarCancelacion(signal);
        return pagina;
    }

    async function descargarRecurso(idProyecto, recurso, campoId, signal) {
        const items = [];
        let cursor = 0, revision, total;
        do {
            comprobarCancelacion(signal);
            const parametros = {despues_de: cursor, limit: 200};
            if (revision !== undefined) parametros.revision = revision;
            const pagina = await paginaExportacion(idProyecto, recurso, parametros, signal);
            comprobarPagina(pagina, {campoId, cursor, limit: 200, revision, total});
            revision = pagina.revision;
            total = pagina.total;
            items.push(...pagina.items);
            if (items.length > total || (pagina.hay_mas && items.length >= total)) throw incompleto();
            if (!pagina.hay_mas) {
                if (items.length !== total) throw incompleto();
                return {items, revision, total};
            }
            cursor = pagina.siguiente_id;
        } while (true);
    }

    // Datos locales a una descarga; nunca se reutilizan entre cuentas o proyectos.
    async function exportacionDashboard(idProyecto, {signal} = {}) {
        const [nucleos, convenios] = await Promise.all([
            descargarRecurso(idProyecto, 'nucleos', 'id_proyecto_nucleo', signal),
            descargarRecurso(idProyecto, 'convenios', 'id_convenio', signal)
        ]);
        return {idProyecto, nucleos, convenios};
    }

    async function validarExportacionDashboard(datos, esperado, {signal} = {}) {
        for (const [recurso, campoId] of [['nucleos', 'id_proyecto_nucleo'], ['convenios', 'id_convenio']]) {
            const conjunto = datos[recurso];
            const pagina = await paginaExportacion(datos.idProyecto, recurso,
                {despues_de: 0, limit: 1, revision: conjunto.revision}, signal);
            comprobarPagina(pagina, {campoId, cursor: 0, limit: 1, revision: conjunto.revision, total: conjunto.total});
            if (pagina.items.length !== Math.min(1, conjunto.total) || pagina.hay_mas !== (conjunto.total > 1)) throw incompleto();
        }
        const resumen = await resumenDashboard(datos.idProyecto, {signal});
        const convenios = datos.convenios.items;
        const calculado = {
            total_nucleos: datos.nucleos.items.length, total_convenios: convenios.length,
            individuales: convenios.filter(c => c.ambito === 'individual').length,
            colectivos: convenios.filter(c => c.ambito === 'colectivo').length,
            formalizados: convenios.filter(c => ['individual', 'colectivo'].includes(c.ambito) && c.fecha_firma != null).length
        };
        if (!esperado || camposResumen.some(c => resumen[c] !== esperado[c] || resumen[c] !== calculado[c])) throw cambio();
        return resumen;
    }

    window.NucleosAPI = {
        resumenDashboard,
        exportacionDashboard,
        validarExportacionDashboard,
        listar,
        obtener,
        crear,
        actualizar,
        listarPorProyecto,
        vincularAProyecto,
        obtenerProyectoNucleo,
        actualizarProyectoNucleo,
        eliminarProyectoNucleo,
        listarReferencias,
        crearReferencia,
        actualizarReferencia,
        listarResponsables,
        crearResponsable,
        actualizarResponsable
    };

})();
