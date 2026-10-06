/* Destinos explícitos por pantalla. No modifica datos, permisos ni navegación. */
(() => {
    "use strict";
    const pagina = location.pathname.split("/").pop().replace(/\.html$/i, "");
    const reglas = [];
    const nodo = selector => document.querySelector(selector);
    const bloque = selector => () => nodo(selector)?.closest("section, .tarjeta, .bloque") || nodo(selector);
    const campo = selector => () => nodo(selector)?.parentElement;
    const oculto = selector => () => !nodo(selector)?.getClientRects().length;
    const abrir = (selector, destino, carga) => reglas.push({ selector, destino, carga });
    const formulario = (abridores, panel, form, canceladores, origen) => {
        abrir(abridores, panel);
        abrir(canceladores, origen);
        reglas.push({ evento: "submit", selector: form, destino: origen, condicion: oculto(panel) });
    };
    const dependiente = (selector, carga) => reglas.push({ evento: "change", selector, carga });
    const campoDesplegado = (selector, destino) => reglas.push({ evento: "change", selector, destino });
    const resultados = (form, destino, botones) => {
        reglas.push({ evento: "submit", selector: form, destino });
        if (botones) abrir(botones, destino, typeof destino === "string" ? bloque(destino) : destino);
    };

    switch (pagina) {
    case "derechosColectivos":
    case "reportesColectivos":
        abrir(".colectivo-detalle summary", () => document.activeElement?.closest("details"));
        reglas.push({ evento: "submit", selector: "#reporteColectivo form", destino: "[data-resultados]" });
        break;
    case "documentos":
        dependiente("[data-doc-tipo]", campo("[data-doc-registro]"));
        dependiente("[data-doc-registro]", "[data-doc-contenido]");
        break;
    case "actividades":
        formulario("#btnNuevaActividad, [data-editar-actividad]", "#formularioActividad", "#formActividad", "#btnCancelarActividad", bloque("#actividadesTabla"));
        break;
    case "afectacion":
        formulario("#btnNuevaAfectacion", "#formularioContenedor", "#formAfectacion", "#btnCerrarFormulario, #btnCancelar", "#afectacionesGrid");
        campoDesplegado("#condicionEspecial", "#descripcionCondicionCampo");
        campoDesplegado("#revisionPendiente", "#detalleRevisionCampo");
        break;
    case "asamblea":
        abrir("[data-editar-asamblea]", "#formAsamblea");
        abrir("#btnAgregarConvocatoria", "#convocatoriasContainer > :last-child");
        abrir("#btnCancelar", "#asambleasRegistradas");
        break;
    case "detalleAfectacion":
        formulario("#btnEditarAfectacion", "#panelEdicionAfectacion", "#formEditarAfectacion", "#btnCancelarEdicionAfectacion", bloque("#datoSituacion"));
        formulario("#btnCapturarAvaluo", "#formAvaluo", "#formAvaluo", "#btnCancelarAvaluo", bloque("#datoAvaluoMonto"));
        break;
    case "expedienteDocumental":
        formulario("#btnNuevoRequisito, [data-editar]", "#formularioRequisito", "#formRequisito", "#btnCancelarRequisito", bloque("#requisitosTabla"));
        dependiente("#entidadTipo", campo("#entidadId"));
        dependiente("#entidadId", campo("#idDocumento"));
        break;
    case "fichaConvenio":
        formulario("#btnEditarConvenio", "#panelEdicionConvenio", "#formEditarConvenio", "#cancelarEditarConvenio", bloque("#tipoInstrumento"));
        formulario("#btnAgregarAfectacion", "#panelAgregarAfectacionConvenio", "#formAgregarAfectacionConvenio", "#cancelarAgregarAfectacion", bloque("#afectacionesTabla"));
        formulario("#btnAgregarCompareciente", "#panelAgregarCompareciente", "#formAgregarCompareciente", "#cancelarAgregarCompareciente", bloque("#comparecientesTabla"));
        break;
    case "fichaProyecto":
        formulario("#btnEditarProyecto", "#editarProyectoContenedor", "#formEditarProyecto", "#btnCancelarEdicionProyecto", "#nombreProyecto");
        abrir("#btnAgregarNucleo", "#formNuevoNucleo");
        abrir("#btnCancelarNucleo", "#nucleosAgrarios");
        reglas.push({ selector: "#btnGuardarNucleo", destino: "#nucleosAgrarios", condicion: oculto("#formNuevoNucleo") });
        dependiente("#nucleoEntidad", campo("#nucleoMunicipio"));
        break;
    case "fichaRan":
        formulario("#btnAgregarEvento, [data-editar-evento]", "#formularioEventoRan", "#formEventoRan", "#btnCancelarEventoRan", bloque("#eventosTabla"));
        break;
    case "fifonafe":
        formulario("#btnNuevoTramite", "#formularioContenedor", "#formFifonafe", "#btnCerrarFormulario, #btnCancelar", bloque("#tramitesContainer"));
        abrir("#btnAgregarEvento", "#eventosContainer > :last-child");
        campoDesplegado("#hayConflictos", "#campoResultadoConflictos");
        break;
    case "indemnizacion":
        formulario("#btnCrearIndemnizacion, #btnEditarIndemnizacion", "#formIndemnizacion", "#formIndemnizacion", "#btnCancelarIndemnizacion", () => nodo("#indemnizacionRegistrada")?.getClientRects().length ? nodo("#indemnizacionRegistrada") : nodo("#sinIndemnizacion"));
        formulario("#btnRegistrarPago", "#formPago", "#formPago", "#btnCerrarPago, #btnCancelarPago", "#seccionPagos");
        campoDesplegado("#estatus", "#campoDescripcionEstatus");
        break;
    case "orv":
        formulario("#btnNuevoOrv, [data-editar-orv]", "#formularioOrv", "#formOrv", "#btnCerrarOrv, #btnCancelarOrv", bloque("#orvLista"));
        formulario("#btnAgregarIntegrante, [data-editar-integrante]", "#formularioIntegrante", "#formIntegrante", "#btnCerrarIntegrante, #btnCancelarIntegrante", "#seccionIntegrantes");
        formulario("[data-finalizar-integrante]", "#formularioFinalizarIntegrante", "#formFinalizarIntegrante", "#btnCerrarFinalizarIntegrante, #btnCancelarFinalizarIntegrante", "#seccionIntegrantes");
        abrir(".orv-item", "#seccionIntegrantes", "#seccionIntegrantes");
        break;
    case "padrones":
        formulario("#btnNuevoPadron, [data-editar-padron]", "#formularioPadron", "#formPadron", "#btnCancelarPadron", bloque("#padronesTabla"));
        break;
    case "seguimiento":
        formulario("#btnNuevoEvento, [data-editar]", "#formularioEvento", "#formSeguimiento", "#btnCancelarEvento", bloque("#seguimientoTabla"));
        dependiente("#entidadTipo, #entidadContextoSelector, #entidadSelector", campo("#entidadSelector"));
        break;
    case "unidadAgraria":
        formulario("#btnNuevaUnidad", "#formularioUnidad", "#formUnidadAgraria", "#btnCerrarFormulario, #btnCancelarUnidad", bloque("#unidadesContainer"));
        abrir("#btnCancelarVinculacion", "#seccionVinculacion");
        campoDesplegado("#requiereRevision", "#contenedorMotivoRevision");
        break;
    case "nuevoConvenio":
        abrir("#btnAgregarCompareciente", "#comparecientesContainer > :last-child");
        campoDesplegado("#modalidadEspecial", "#campoDescripcionModalidad");
        campoDesplegado("#tipoInstrumento", () => nodo("#campoDescripcionInstrumento")?.getClientRects().length ? nodo("#campoDescripcionInstrumento") : nodo("#campoTipoConvenio"));
        break;
    case "tramiteRan":
        abrir("#btnAgregarEvento", "#eventosLista > :last-child");
        break;
    case "auditoria":
        resultados("#formFiltrosCambios", bloque("#tablaCambios"), "#btnAnteriorCambios, #btnSiguienteCambios");
        resultados("#formFiltrosAccesos", bloque("#tablaAccesos"), "#btnAnteriorAccesos, #btnSiguienteAccesos");
        dependiente("#cambiosProyecto", campo("#cambiosProyectoNucleo"));
        abrir('[data-auditoria-tab="cambios"]', "#panelCambios", "#panelCambios");
        abrir('[data-auditoria-tab="accesos"]', "#panelAccesos", "#panelAccesos");
        break;
    case "reportesConvenios":
        resultados("#formReportesConvenios", "#tituloResultadosConvenios", "#btnAnteriorReportesConvenios, #btnSiguienteReportesConvenios");
        dependiente("#reporteConvenioFiltro_id_proyecto", campo("#reporteConvenioFiltro_id_proyecto_nucleo"));
        dependiente("#reporteConvenioFiltro_id_proyecto_nucleo", () => nodo("#reporteConvenioFiltro_id_convenio, #reporteConvenioFiltro_id_afectacion")?.parentElement);
        abrir("[data-reporte]", "#formReportesConvenios", "#formReportesConvenios");
        break;
    case "reportesFifonafe":
        resultados("#formReportesFifonafe", "#fifTituloResultados", "#btnAnteriorFifReportes, #btnSiguienteFifReportes");
        abrir("[data-fif-reporte]", "#formReportesFifonafe", "#formReportesFifonafe");
        break;
    case "reporteActividadesPeriodo":
        resultados("#formAvancePeriodo", "#tituloResultadosAvance", "#btnAvanceAnterior, #btnAvanceSiguiente");
        break;
    case "catalogosOperativos":
        abrir("#btnCargarCatalogo", "#tituloOpcionesCatalogo", bloque("#tablaCatalogos"));
        break;
    case "persona":
        abrir("#btnConsultarPersona", "#personasContainer", bloque("#personasContainer"));
        break;
    // Las fichas restantes usan navegación, contenido siempre visible o modales.
    }
    window.SSALFER_UI?.registrarAcciones(reglas);

    // Las dos exportaciones de servidor también pasan por request (GET real, mismas rutas).
    document.addEventListener("click", async event => {
        const enlace = event.target.closest?.("#btnExportarDashboardCsv, #btnExportarCsv");
        if (!enlace || enlace.getAttribute("aria-disabled") === "true") return;
        const base = new URL(window.ClienteAPI.API_BASE_URL, location.origin);
        const url = new URL(enlace.href);
        if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname + "/exportaciones/")) return;
        event.preventDefault();
        if (enlace.dataset.descargando) return;
        enlace.dataset.descargando = "true";
        try {
            const blob = await window.ClienteAPI.get(url.pathname.slice(base.pathname.length) + url.search, { tipoRespuesta: "blob" });
            const descarga = document.createElement("a");
            const temporal = URL.createObjectURL(blob);
            descarga.href = temporal;
            descarga.download = "dashboard.csv";
            descarga.click();
            setTimeout(() => URL.revokeObjectURL(temporal), 1000);
        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(error);
        } finally {
            delete enlace.dataset.descargando;
        }
    });
})();
