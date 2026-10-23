/**
 * estadoFinanciero.js
 *
 * Dashboard de reportes financieros/operativos de UN proyecto
 * (?id_proyecto=<id> en la URL), construido enteramente con los
 * endpoints reales de reporting.py expuestos por ReportesAPI:
 *
 *   - GET /dashboard/kpi                          (KPIs agregados)
 *   - GET /reportes/avance-periodo                (programado vs realizado)
 *   - GET /reportes/convenios/valores-declarados
 *   - GET /reportes/convenios/cobertura-impactos
 *   - GET /reportes/fifonafe/cobertura
 *   - GET /exportaciones/dashboard.csv            (descarga)
 *
 * No existe un endpoint que liste convenios/pagos/FIFONAFE
 * individuales a nivel proyecto (ConveniosAPI e IndemnizacionAPI
 * solo listan por afectación), así que esta página ya NO muestra
 * tablas de convenios/pagos "por beneficiario" con datos inventados;
 * eso se sigue consultando desde detalleAfectacion.html /
 * fichaConvenio.html / indemnizacion.html, que sí tienen ese contexto.
 */

document.addEventListener("DOMContentLoaded", async () => {

    const parametros = new URLSearchParams(window.location.search);
    const idProyecto = parametros.get("id_proyecto");

    const contenedorError = document.getElementById("mensajeError");

    if (!idProyecto) {

        window.ClienteAPI.mostrarErrorAPI(
            new Error("No se especificó un proyecto (falta ?id_proyecto= en la URL)."),
            contenedorError
        );

        return;

    }


    /* =====================================================
                    UTILIDADES DE FORMATO
    ====================================================== */

    const formatoMoneda = new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: "MXN",
        maximumFractionDigits: 2
    });

    function moneda(valor) {
        return formatoMoneda.format(Number(valor || 0));
    }

    function numero(valor) {
        return Number(valor || 0).toLocaleString("es-MX");
    }

    function fecha(valorISO) {
        return window.SSALFER_FORMAT?.formatearFecha(valorISO)
            ?? (valorISO || "—");
    }

    function textoSiNo(valor) {

        if (valor === true) return "Sí";
        if (valor === false) return "No";
        return "—";

    }

    const CONCEPTOS_DECLARADOS = Object.freeze({
        monto_90_declarado: "Monto 90 %",
        monto_100_declarado: "Monto 100 %",
        monto_bdt_declarado: "Monto BDT",
        superficie_declarada: "Superficie"
    });

    function etiquetaConcepto(concepto) {
        return CONCEPTOS_DECLARADOS[concepto]
            || window.SSALFER_FORMAT?.etiquetaCodigo(concepto)
            || concepto
            || "—";
    }

    function valorDeclaradoFormateado(fila) {
        if (fila?.valor_declarado == null) return "—";

        if (fila.concepto === "superficie_declarada") {
            return `${Number(fila.valor_declarado).toLocaleString("es-MX", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 6
            })} ha`;
        }

        return moneda(fila.valor_declarado);
    }

    function celdaVacia(colspan, texto) {
        return `<tr><td colspan="${colspan}">${texto}</td></tr>`;
    }

    function etiquetaIndicador(codigo) {
        const clave = String(codigo || '').toLowerCase();
        if (/^sensibilizacion(?:_|$)/.test(clave)) return 'Sensibilización';
        if (/^caminamiento(?:_|$)/.test(clave)) return 'Caminamiento';
        const etiquetas = {
            nucleos: 'Núcleos', asambleas: 'Asambleas',
            cop_colectivos: 'COP colectivo', cop_individuales: 'COP individual',
            modificatorios: 'Modificatorios', superficies_adicionales: 'Superficie adicional',
            obras_complementarias: 'Obras complementarias', ampliaciones: 'Ampliaciones',
            ampliaciones_remanentes: 'Remanentes', otros_instrumentos: 'Otros instrumentos',
            retiro_fondos: 'Retiro de fondos', parcelas_afectadas: 'Parcelas afectadas',
            superficie_por_destino: 'Superficie por destino',
            superficie_afectada_administrativa: 'Superficie afectada',
            ingreso_ran_acta: 'Ingreso RAN · Acta', ingreso_ran_convenio: 'Ingreso RAN · Convenio',
            inscripcion_ran_acta: 'Inscripción RAN · Acta', inscripcion_ran_convenio: 'Inscripción RAN · Convenio',
            indemnizaciones: 'Indemnizaciones', pagos: 'Pagos', fifonafe: 'FIFONAFE',
            informe_no_conflictos: 'Sin conflictos'
        };
        return etiquetas[clave] || window.SSALFER_FORMAT?.etiquetaCodigo(codigo)
            || clave.replaceAll('_', ' ') || '—';
    }

    /* =====================================================
        INDICADORES QUE CORRESPONDEN A CONVENIOS
        (según vw_dashboard_kpi / migración 001-006)
    ====================================================== */

    const INDICADORES_CONVENIO = new Set([
        "cop_colectivos",
        "cop_individuales",
        "modificatorios",
        "superficies_adicionales",
        "obras_complementarias",
        "ampliaciones",
        "ampliaciones_remanentes",
        "otros_instrumentos"
    ]);


    /* =====================================================
                    ENCABEZADO: DATOS DEL PROYECTO
    ====================================================== */

    document.getElementById("fechaGeneracion").textContent =
        new Date().toLocaleDateString("es-MX", {
            year: "numeric", month: "long", day: "numeric"
        });

    try {

        const proyecto = await window.ProyectosAPI.obtener(idProyecto);

        document.title = `Estado financiero — ${proyecto.nombre_proyecto} | SSALFER`;

        document.getElementById("nombreProyectoTitulo").textContent =
            `Estado financiero — ${proyecto.nombre_proyecto}`;

        const enlaceProyecto = document.getElementById("enlaceProyecto");
        enlaceProyecto.textContent = proyecto.nombre_proyecto;
        enlaceProyecto.href = `/pages/fichaProyecto.html?id=${encodeURIComponent(idProyecto)}`;

    } catch (error) {

        window.ClienteAPI.mostrarErrorAPI(error, contenedorError);

    }


    /* =====================================================
                    BOTÓN DE EXPORTACIÓN CSV
        (urlExportacionDashboardCsv() no acepta parámetros;
        se agrega id_proyecto aquí para no tocar reportes.js)
    ====================================================== */

    const botonExportar = document.getElementById("btnExportarCsv");

    botonExportar.href =
        `${window.ClienteAPI.API_BASE_URL}/exportaciones/dashboard.csv?id_proyecto=${encodeURIComponent(idProyecto)}`;


    /* =====================================================
                    KPIs (dashboard/kpi + valores declarados)
    ====================================================== */

    // Both initial consumers share one snapshot; exports keep their existing URLs.
    const valoresDeclaradosIniciales = window.ReportesAPI.obtenerConveniosValoresDeclarados({ id_proyecto: idProyecto });

    (async () => {

        try {

            const [kpisTodos, valoresDeclarados] = await Promise.all([
                window.ReportesAPI.obtenerKpiDashboard(),
                valoresDeclaradosIniciales
            ]);

            const kpisProyecto = (Array.isArray(kpisTodos) ? kpisTodos : [])
                .filter(fila => fila.id_proyecto === Number(idProyecto));

            const sumarPorIndicador = (indicadores, campo) =>
                kpisProyecto
                    .filter(fila => indicadores.has(fila.indicador))
                    .reduce((acc, fila) => acc + Number(fila[campo] || 0), 0);

            const filasConvenios = kpisProyecto.filter(f => INDICADORES_CONVENIO.has(f.indicador));
            const filasIndemnizaciones = kpisProyecto.filter(f => f.indicador === "indemnizaciones");
            const filasPagos = kpisProyecto.filter(f => f.indicador === "pagos");

            const convProgramado = filasConvenios.reduce((a, f) => a + Number(f.programado || 0), 0);
            const convRealizado = filasConvenios.reduce((a, f) => a + Number(f.realizado || 0), 0);

            document.getElementById("kpiConvenios").textContent =
                `${numero(convRealizado)} / ${numero(convProgramado)}`;

            const filasValores = Array.isArray(valoresDeclarados)
                ? valoresDeclarados
                : [];

            const totalPorConcepto = concepto => filasValores
                .filter(fila => fila.concepto === concepto)
                .reduce((acc, fila) => acc + Number(fila.valor_declarado || 0), 0);

            document.getElementById("kpiMonto90").textContent =
                moneda(totalPorConcepto("monto_90_declarado"));
            document.getElementById("kpiMonto100").textContent =
                moneda(totalPorConcepto("monto_100_declarado"));
            document.getElementById("kpiMontoBdt").textContent =
                moneda(totalPorConcepto("monto_bdt_declarado"));
            document.getElementById("kpiSuperficieDeclarada").textContent =
                `${totalPorConcepto("superficie_declarada").toLocaleString("es-MX", {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 6
                })} ha`;

            const indProgramado = filasIndemnizaciones.reduce((a, f) => a + Number(f.programado || 0), 0);
            const indRealizado = filasIndemnizaciones.reduce((a, f) => a + Number(f.realizado || 0), 0);

            document.getElementById("kpiIndemnizaciones").textContent =
                `${numero(indRealizado)} / ${numero(indProgramado)}`;

            const pagosMonto = filasPagos.reduce((a, f) => a + Number(f.monto || 0), 0);

            document.getElementById("kpiPagos").textContent =
                moneda(pagosMonto);

        } catch (error) {

            window.ClienteAPI.mostrarErrorAPI(error, contenedorError);

        }

    })();


    /* =====================================================
                    TABLA: AVANCE DE PERIODO
    ====================================================== */

    (async () => {

        const cuerpo = document.getElementById("tablaAvancePeriodo");

        try {

            const filas = await window.ReportesAPI.obtenerAvancePeriodo({ id_proyecto: idProyecto });

            if (!Array.isArray(filas) || filas.length === 0) {

                cuerpo.innerHTML = celdaVacia(9, "Este proyecto todavía no tiene avances de periodo registrados.");
                return;

            }

            cuerpo.innerHTML = filas.map(fila => `
                <tr>
                    <td title="${window.SSALFER_UI.escaparHTML(fila.indicador || '')}">${window.SSALFER_UI.escaparHTML(etiquetaIndicador(fila.indicador))}</td>
                    <td>${fila.ambito || "—"}</td>
                    <td>${fila.anio}</td>
                    <td>${fila.mes}</td>
                    <td>${fila.trimestre}</td>
                    <td>${numero(fila.programado)}</td>
                    <td>${numero(fila.realizado)}</td>
                    <td>${fila.superficie_ha != null ? Number(fila.superficie_ha).toFixed(2) : "—"}</td>
                    <td>${fila.monto != null ? moneda(fila.monto) : "—"}</td>
                </tr>
            `).join("");

        } catch (error) {

            cuerpo.innerHTML = celdaVacia(9, "No se pudo cargar el avance de periodo.");
            window.ClienteAPI.mostrarErrorAPI(error, contenedorError);

        }

    })();


    /* =====================================================
                    TABLA: VALORES DECLARADOS DE CONVENIOS
    ====================================================== */

    (async () => {

        const cuerpo = document.getElementById("tablaValoresDeclarados");

        try {

            const filas = await valoresDeclaradosIniciales;

            if (!Array.isArray(filas) || filas.length === 0) {

                cuerpo.innerHTML = celdaVacia(6, "Este proyecto todavía no tiene valores declarados de convenios.");
                return;

            }

            const referencias = new Map();
            const datosReferencias = await window.ReportesAPI.obtenerReferenciasReporte({convenios: filas.map(fila => fila.id_convenio)});
            for (const convenio of datosReferencias.convenios) {
                referencias.set(Number(convenio.id_convenio), [window.SSALFER_FORMAT.etiquetaCodigo(convenio.tipo_convenio),
                    `Consecutivo ${convenio.consecutivo}`, window.SSALFER_FORMAT.etiquetaCodigo(convenio.ambito)].join(" · "));
            }

            cuerpo.innerHTML = filas.map(fila => `
                <tr>
                    <td>
                        <a class="ssalfer-link" href="/pages/fichaConvenio.html?id_convenio=${encodeURIComponent(fila.id_convenio)}">
                            ${window.SSALFER_UI.escaparHTML(referencias.get(Number(fila.id_convenio)) || "Convenio · Referencia no disponible")}
                        </a>
                    </td>
                    <td>${etiquetaConcepto(fila.concepto)}</td>
                    <td>${window.SSALFER_FORMAT?.etiquetaCodigo(fila.tipo_convenio) || fila.tipo_convenio || "—"}</td>
                    <td>${valorDeclaradoFormateado(fila)}</td>
                    <td>${fecha(fila.fecha_instrumento_reportada)}</td>
                    <td>${textoSiNo(fila.firma_acreditada)}</td>
                </tr>
            `).join("");

        } catch (error) {

            cuerpo.innerHTML = celdaVacia(6, "No se pudieron cargar los valores declarados.");
            window.ClienteAPI.mostrarErrorAPI(error, contenedorError);

        }

    })();


    /* =====================================================
                COBERTURA DE IMPACTOS DE CONVENIOS
    ====================================================== */

    (async () => {

        const cuerpo = document.getElementById("tablaCoberturaImpactos");

        try {

            const filas = await window.ReportesAPI.obtenerConveniosCoberturaImpactos({ id_proyecto: idProyecto });

            if (!Array.isArray(filas) || filas.length === 0) {

                cuerpo.innerHTML = celdaVacia(6, "Este proyecto todavía no tiene impactos de convenios registrados.");
                return;

            }

            cuerpo.innerHTML = filas.map(fila => `
                <tr>
                    <td>${fila.ambito}</td>
                    <td>${etiquetaConcepto(fila.concepto)}</td>
                    <td>${numero(fila.universo)}</td>
                    <td>${numero(fila.clasificados)}</td>
                    <td>${numero(fila.pendientes)}</td>
                    <td>${numero(fila.sin_firma_acreditada)}</td>
                </tr>
            `).join("");

        } catch (error) {

            cuerpo.innerHTML = celdaVacia(6, "No se pudo cargar la cobertura de impactos.");
            window.ClienteAPI.mostrarErrorAPI(error, contenedorError);

        }

    })();


    /* =====================================================
                    FIFONAFE — COBERTURA
    ====================================================== */

    (async () => {

        const cuerpo = document.getElementById("tablaFifonafeCobertura");

        try {

            const filas = await window.ReportesAPI.obtenerFifonafeCobertura({ id_proyecto: idProyecto });

            if (!Array.isArray(filas) || filas.length === 0) {

                cuerpo.innerHTML = celdaVacia(8, "Este proyecto todavía no tiene cobertura FIFONAFE registrada.");
                return;

            }

            cuerpo.innerHTML = filas.map(fila => `
                <tr>
                    <td>${fila.ambito}</td>
                    <td>${numero(fila.universo_solicitudes)}</td>
                    <td>${numero(fila.solicitudes_recibidas_acreditadas)}</td>
                    <td>${numero(fila.eventos_consulta_sin_ciclo)}</td>
                    <td>${numero(fila.respuestas_sin_soporte)}</td>
                    <td>${numero(fila.actuaciones_sin_soporte)}</td>
                    <td>${numero(fila.completos_integrales)}</td>
                    <td>${numero(fila.pendientes_integrales)}</td>
                </tr>
            `).join("");

        } catch (error) {

            cuerpo.innerHTML = celdaVacia(8, "No se pudo cargar la cobertura FIFONAFE.");
            window.ClienteAPI.mostrarErrorAPI(error, contenedorError);

        }

    })();

});
