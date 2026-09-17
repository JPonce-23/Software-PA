document.addEventListener("DOMContentLoaded", async () => {
    "use strict";


    /* =====================================================
                        ESTADO
    ===================================================== */

    const estado = {
        reporte: "cobertura",
        filas: [],
        proyectos: new Map(),
        pagina: 1,
        porPagina: 50,
        cargando: false
    };


    /* =====================================================
                        ELEMENTOS
    ===================================================== */

    const el = {
        error:
            document.getElementById(
                "fifReportesError"
            ),

        info:
            document.getElementById(
                "fifReportesInfo"
            ),

        nota:
            document.getElementById(
                "fifReporteNota"
            ),

        tituloFiltros:
            document.getElementById(
                "fifTituloFiltros"
            ),

        descripcionFiltros:
            document.getElementById(
                "fifDescripcionFiltros"
            ),

        tituloResultados:
            document.getElementById(
                "fifTituloResultados"
            ),

        subtituloResultados:
            document.getElementById(
                "fifSubtituloResultados"
            ),

        tabs:
            Array.from(
                document.querySelectorAll(
                    "[data-fif-reporte]"
                )
            ),

        form:
            document.getElementById(
                "formReportesFifonafe"
            ),

        proyecto:
            document.getElementById(
                "fifFiltroProyecto"
            ),

        grupoAmbito:
            document.getElementById(
                "fifGrupoAmbito"
            ),

        ambito:
            document.getElementById(
                "fifFiltroAmbito"
            ),

        grupoAnio:
            document.getElementById(
                "fifGrupoAnio"
            ),

        anio:
            document.getElementById(
                "fifFiltroAnio"
            ),

        btnLimpiar:
            document.getElementById(
                "btnLimpiarFifReportes"
            ),

        btnConsultar:
            document.getElementById(
                "btnConsultarFifReportes"
            ),

        resumen:
            document.getElementById(
                "fifReportesResumen"
            ),

        busqueda:
            document.getElementById(
                "busquedaFifReportes"
            ),

        btnExportar:
            document.getElementById(
                "btnExportarFifReportes"
            ),

        total:
            document.getElementById(
                "totalFifReportes"
            ),

        porPagina:
            document.getElementById(
                "porPaginaFifReportes"
            ),

        thead:
            document.getElementById(
                "theadFifReportes"
            ),

        tbody:
            document.getElementById(
                "tbodyFifReportes"
            ),

        btnAnterior:
            document.getElementById(
                "btnAnteriorFifReportes"
            ),

        btnSiguiente:
            document.getElementById(
                "btnSiguienteFifReportes"
            ),

        pagina:
            document.getElementById(
                "paginaFifReportes"
            )
    };


    /* =====================================================
                CONFIGURACIÓN DE REPORTES
    ===================================================== */

    const reportes = {

        cobertura: {

            tituloFiltros:
                "Filtros de cobertura",

            descripcionFiltros:
                "Filtra por proyecto y ámbito. Ambos filtros son opcionales.",

            tituloResultados:
                "Cobertura FIFONAFE",

            subtituloResultados:
                "Cobertura de solicitudes por proyecto y ámbito.",

            nota:
                "La cobertura v2 se calcula por solicitud. Los pendientes y la falta de soporte impiden presentar sus subtotales como un total definitivo.",


            columnas: [

                [
                    "id_proyecto",
                    "Proyecto",
                    "proyecto"
                ],

                [
                    "ambito",
                    "Ámbito",
                    "ambito"
                ],

                [
                    "universo_solicitudes",
                    "Universo solicitudes",
                    "entero"
                ],

                [
                    "solicitudes_recibidas_acreditadas",
                    "Solicitudes recibidas acreditadas",
                    "entero"
                ],

                [
                    "eventos_consulta_sin_ciclo",
                    "Eventos consulta sin ciclo",
                    "entero"
                ],

                [
                    "respuestas_sin_soporte",
                    "Respuestas sin soporte",
                    "entero"
                ],

                [
                    "actuaciones_sin_soporte",
                    "Actuaciones sin soporte",
                    "entero"
                ],

                [
                    "completos_integrales",
                    "Completos integrales",
                    "entero"
                ],

                [
                    "pendientes_integrales",
                    "Pendientes integrales",
                    "entero"
                ],

                [
                    "cobertura_integral",
                    "Cobertura integral",
                    "porcentaje"
                ]

            ],


            api(params) {

                return window.ReportesAPI
                    .obtenerFifonafeCobertura(
                        params
                    );

            },


            params() {

                const params = {};


                if (
                    el.proyecto.value
                ) {

                    params.id_proyecto =
                        el.proyecto.value;

                }


                if (
                    el.ambito.value
                ) {

                    params.ambito =
                        el.ambito.value;

                }


                return params;

            },


            transformar(filas) {

                return filas.map(
                    fila => ({

                        ...fila,


                        /*
                         * Este porcentaje NO viene
                         * del backend.
                         *
                         * Es solo una ayuda visual:
                         *
                         * completos_integrales /
                         * universo_solicitudes
                         */
                        cobertura_integral:
                            numero(
                                fila.universo_solicitudes
                            ) > 0

                                ? numero(
                                    fila.completos_integrales
                                ) /
                                numero(
                                    fila.universo_solicitudes
                                ) *
                                100

                                : 0

                    })
                );

            },


            resumen(filas) {

                const universo =
                    sumar(
                        filas,
                        "universo_solicitudes"
                    );


                const recibidas =
                    sumar(
                        filas,
                        "solicitudes_recibidas_acreditadas"
                    );


                const completos =
                    sumar(
                        filas,
                        "completos_integrales"
                    );


                const pendientes =
                    sumar(
                        filas,
                        "pendientes_integrales"
                    );


                return [

                    [
                        "Universo",
                        formatearEntero(
                            universo
                        )
                    ],

                    [
                        "Recibidas acreditadas",
                        formatearEntero(
                            recibidas
                        )
                    ],

                    [
                        "Completos integrales",
                        formatearEntero(
                            completos
                        )
                    ],

                    [
                        "Cobertura integral",

                        universo > 0

                            ? `${formatearDecimal(
                                completos /
                                universo *
                                100,
                                2
                            )} %`

                            : "0 %"
                    ],

                    [
                        "Pendientes integrales",
                        formatearEntero(
                            pendientes
                        )
                    ],

                    [
                        "Actuaciones sin soporte",

                        formatearEntero(
                            sumar(
                                filas,
                                "actuaciones_sin_soporte"
                            )
                        )
                    ]

                ];

            }

        },


        indicador: {

            tituloFiltros:
                "Filtros del indicador institucional",

            descripcionFiltros:
                "Filtra por proyecto y año. Ambos filtros son opcionales.",

            tituloResultados:
                "Indicador institucional FIFONAFE",

            subtituloResultados:
                "Solicitudes resueltas positivamente respecto de solicitudes recibidas, por proyecto y año.",

            nota:
                "El indicador institucional es solicitudes resueltas positivamente / solicitudes recibidas. No cuenta oficios, parcelas, entregas ni pagos.",


            columnas: [

                [
                    "id_proyecto",
                    "Proyecto",
                    "proyecto"
                ],

                [
                    "anio",
                    "Año",
                    "entero"
                ],

                [
                    "solicitudes_recibidas",
                    "Solicitudes recibidas",
                    "entero"
                ],

                [
                    "solicitudes_resueltas_positivas",
                    "Resueltas positivas",
                    "entero"
                ],

                [
                    "porcentaje",
                    "Porcentaje",
                    "porcentaje"
                ]

            ],


            api(params) {

                return window.ReportesAPI
                    .obtenerFifonafeIndicadorInstitucional(
                        params
                    );

            },


            params() {

                const params = {};


                if (
                    el.proyecto.value
                ) {

                    params.id_proyecto =
                        el.proyecto.value;

                }


                if (
                    el.anio.value
                ) {

                    params.anio =
                        el.anio.value;

                }


                return params;

            },


            transformar(filas) {

                return filas;

            },


            resumen(filas) {

                const recibidas =
                    sumar(
                        filas,
                        "solicitudes_recibidas"
                    );


                const positivas =
                    sumar(
                        filas,
                        "solicitudes_resueltas_positivas"
                    );


                return [

                    [
                        "Filas",
                        formatearEntero(
                            filas.length
                        )
                    ],

                    [
                        "Solicitudes recibidas",
                        formatearEntero(
                            recibidas
                        )
                    ],

                    [
                        "Resueltas positivas",
                        formatearEntero(
                            positivas
                        )
                    ],

                    [
                        "Razón global filtrada",

                        recibidas > 0

                            ? `${formatearDecimal(
                                positivas /
                                recibidas *
                                100,
                                2
                            )} %`

                            : "—"
                    ]

                ];

            }

        }

    };


    /* =====================================================
                    UTILIDADES
    ===================================================== */

    function numero(valor) {

        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {

            return 0;

        }


        const resultado =
            Number(valor);


        return Number.isFinite(
            resultado
        )
            ? resultado
            : 0;

    }


    function sumar(
        filas,
        campo
    ) {

        return filas.reduce(
            (
                total,
                fila
            ) =>
                total +
                numero(
                    fila[campo]
                ),
            0
        );

    }


    function formatearEntero(valor) {

        return new Intl.NumberFormat(
            "es-MX",
            {
                maximumFractionDigits: 0
            }
        ).format(
            numero(valor)
        );

    }


    function formatearDecimal(
        valor,
        decimales = 2
    ) {

        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {

            return "—";

        }


        return new Intl.NumberFormat(
            "es-MX",
            {
                minimumFractionDigits: 0,
                maximumFractionDigits:
                    decimales
            }
        ).format(
            numero(valor)
        );

    }


    function nombreProyecto(
        idProyecto
    ) {

        if (
            idProyecto === null ||
            idProyecto === undefined
        ) {

            return "—";

        }


        return (
            estado.proyectos.get(
                Number(idProyecto)
            ) ||
            `Proyecto ${idProyecto}`
        );

    }


    function limpiarMensajes() {

        el.error.hidden =
            true;

        el.error.textContent =
            "";

        el.info.hidden =
            true;

        el.info.textContent =
            "";

    }


    function mostrarError(error) {

        el.info.hidden =
            true;


        window.ClienteAPI
            .mostrarErrorAPI(
                error,
                el.error
            );

    }


    function mostrarInfo(mensaje) {

        el.error.hidden =
            true;

        el.info.textContent =
            mensaje;

        el.info.hidden =
            false;

    }


    /* =====================================================
                    FORMATEAR CELDAS
    ===================================================== */

    function valorVisual(
        fila,
        campo,
        tipo
    ) {

        const valor =
            fila[campo];


        switch (tipo) {

            case "proyecto":

                return nombreProyecto(
                    valor
                );


            case "ambito":

                return valor || "—";


            case "entero":

                return (
                    valor === null ||
                    valor === undefined
                )
                    ? "—"
                    : formatearEntero(
                        valor
                    );


            case "porcentaje":

                return (
                    valor === null ||
                    valor === undefined
                )
                    ? "—"
                    : `${formatearDecimal(
                        valor,
                        2
                    )} %`;


            default:

                return (
                    valor === null ||
                    valor === undefined ||
                    valor === ""
                )
                    ? "—"
                    : String(valor);

        }

    }


    /* =====================================================
                    BÚSQUEDA LOCAL
    ===================================================== */

    function filasFiltradas() {

        const termino =
            el.busqueda.value
                .trim()
                .toLocaleLowerCase(
                    "es-MX"
                );


        if (!termino) {

            return estado.filas;

        }


        const config =
            reportes[
                estado.reporte
            ];


        return estado.filas.filter(
            fila => {

                const contenido =
                    config.columnas
                        .map(
                            ([
                                campo,
                                ,
                                tipo
                            ]) =>
                                valorVisual(
                                    fila,
                                    campo,
                                    tipo
                                )
                        )
                        .join(" ")
                        .toLocaleLowerCase(
                            "es-MX"
                        );


                return contenido.includes(
                    termino
                );

            }
        );

    }


    /* =====================================================
                    CABECERA
    ===================================================== */

    function renderCabecera() {

        const config =
            reportes[
                estado.reporte
            ];


        const tr =
            document.createElement(
                "tr"
            );


        config.columnas.forEach(
            ([
                ,
                titulo
            ]) => {

                const th =
                    document.createElement(
                        "th"
                    );


                th.textContent =
                    titulo;


                tr.appendChild(
                    th
                );

            }
        );


        el.thead.replaceChildren(
            tr
        );

    }


    /* =====================================================
                        RESUMEN
    ===================================================== */

    function renderResumen(filas) {

        const config =
            reportes[
                estado.reporte
            ];


        const items =
            config.resumen(
                filas
            );


        el.resumen.replaceChildren();


        items.forEach(
            ([
                etiqueta,
                valor
            ]) => {

                const card =
                    document.createElement(
                        "article"
                    );


                card.className =
                    "fif-reportes-kpi";


                const span =
                    document.createElement(
                        "span"
                    );


                span.textContent =
                    etiqueta;


                const strong =
                    document.createElement(
                        "strong"
                    );


                strong.textContent =
                    String(valor);


                card.append(
                    span,
                    strong
                );


                el.resumen.appendChild(
                    card
                );

            }
        );

    }


    /* =====================================================
                        TABLA
    ===================================================== */

    function renderTabla() {

        const config =
            reportes[
                estado.reporte
            ];


        const filtradas =
            filasFiltradas();


        const totalPaginas =
            Math.max(
                1,
                Math.ceil(
                    filtradas.length /
                    estado.porPagina
                )
            );


        if (
            estado.pagina >
            totalPaginas
        ) {

            estado.pagina =
                totalPaginas;

        }


        const inicio =
            (
                estado.pagina - 1
            ) *
            estado.porPagina;


        const pagina =
            filtradas.slice(
                inicio,
                inicio +
                estado.porPagina
            );


        el.tbody.replaceChildren();


        el.total.textContent =
            `${filtradas.length.toLocaleString(
                "es-MX"
            )} registro(s)`;


        el.pagina.textContent =
            `Página ${estado.pagina} de ${totalPaginas}`;


        el.btnAnterior.disabled =
            estado.cargando ||
            estado.pagina <= 1;


        el.btnSiguiente.disabled =
            estado.cargando ||
            estado.pagina >=
                totalPaginas;


        el.btnExportar.disabled =
            filtradas.length === 0;


        renderResumen(
            filtradas
        );


        if (
            pagina.length === 0
        ) {

            const tr =
                document.createElement(
                    "tr"
                );


            const td =
                document.createElement(
                    "td"
                );


            td.colSpan =
                config.columnas.length;


            td.className =
                "fif-reportes-tabla-estado";


            td.textContent =
                estado.filas.length === 0

                    ? "No hay registros para los filtros seleccionados."

                    : "No hay coincidencias con la búsqueda local.";


            tr.appendChild(
                td
            );


            el.tbody.appendChild(
                tr
            );


            return;

        }


        pagina.forEach(
            fila => {

                const tr =
                    document.createElement(
                        "tr"
                    );


                config.columnas.forEach(
                    ([
                        campo,
                        ,
                        tipo
                    ]) => {

                        const td =
                            document.createElement(
                                "td"
                            );


                        if (
                            tipo === "ambito"
                        ) {

                            const badge =
                                document.createElement(
                                    "span"
                                );


                            const ambito =
                                String(
                                    fila[campo] ||
                                    ""
                                );


                            badge.className =
                                `fif-reportes-badge fif-reportes-badge-${
                                    ambito ===
                                    "individual"

                                        ? "individual"

                                        : "colectivo"
                                }`;


                            badge.textContent =
                                ambito || "—";


                            td.appendChild(
                                badge
                            );

                        } else {

                            td.textContent =
                                valorVisual(
                                    fila,
                                    campo,
                                    tipo
                                );

                        }


                        if (
                            [
                                "entero",
                                "porcentaje"
                            ].includes(
                                tipo
                            )
                        ) {

                            td.classList.add(
                                "fif-reportes-numero"
                            );

                        }


                        tr.appendChild(
                            td
                        );

                    }
                );


                el.tbody.appendChild(
                    tr
                );

            }
        );

    }


    function ponerCargando() {

        const config =
            reportes[
                estado.reporte
            ];


        const tr =
            document.createElement(
                "tr"
            );


        const td =
            document.createElement(
                "td"
            );


        td.colSpan =
            config.columnas.length;


        td.className =
            "fif-reportes-tabla-estado";


        td.textContent =
            "Consultando reporte FIFONAFE...";


        tr.appendChild(
            td
        );


        el.tbody.replaceChildren(
            tr
        );

    }


    /* =====================================================
                    CONSULTA AL BACKEND
    ===================================================== */

    async function consultarReporte() {

        if (
            estado.cargando
        ) {

            return;

        }


        limpiarMensajes();


        estado.cargando =
            true;


        el.btnConsultar.disabled =
            true;


        el.btnExportar.disabled =
            true;


        el.btnAnterior.disabled =
            true;


        el.btnSiguiente.disabled =
            true;


        ponerCargando();


        try {

            const config =
                reportes[
                    estado.reporte
                ];


            /*
             * Aquí NO usamos fetch().
             *
             * config.api termina llamando a:
             *
             * ReportesAPI.obtenerFifonafeCobertura()
             *
             * o
             *
             * ReportesAPI.obtenerFifonafeIndicadorInstitucional()
             *
             * que ya existen en js/api/reportes.js.
             */
            const respuesta =
                await config.api(
                    config.params()
                );


            const filasOriginales =
                Array.isArray(
                    respuesta
                )
                    ? respuesta
                    : [];


            estado.filas =
                config.transformar(
                    filasOriginales
                );


            estado.pagina =
                1;


            el.busqueda.value =
                "";


            renderTabla();


            if (
                estado.filas.length === 0
            ) {

                mostrarInfo(
                    "La consulta se ejecutó correctamente, pero no encontró registros para los filtros seleccionados."
                );

            }


        } catch (error) {

            estado.filas =
                [];


            renderTabla();


            mostrarError(
                error
            );


        } finally {

            estado.cargando =
                false;


            el.btnConsultar.disabled =
                false;


            renderTabla();

        }

    }


    /* =====================================================
                    CAMBIAR PESTAÑA
    ===================================================== */

    function configurarReporte(
        nombre
    ) {

        if (
            !reportes[nombre]
        ) {

            return;

        }


        estado.reporte =
            nombre;


        estado.filas =
            [];


        estado.pagina =
            1;


        el.busqueda.value =
            "";


        limpiarMensajes();


        const config =
            reportes[
                nombre
            ];


        el.tituloFiltros.textContent =
            config.tituloFiltros;


        el.descripcionFiltros.textContent =
            config.descripcionFiltros;


        el.tituloResultados.textContent =
            config.tituloResultados;


        el.subtituloResultados.textContent =
            config.subtituloResultados;


        el.nota.textContent =
            config.nota;


        const esCobertura =
            nombre === "cobertura";


        el.grupoAmbito.hidden =
            !esCobertura;


        el.grupoAnio.hidden =
            esCobertura;


        if (
            esCobertura
        ) {

            el.anio.value =
                "";

        } else {

            el.ambito.value =
                "";

        }


        el.tabs.forEach(
            tab => {

                const activa =
                    tab.dataset.fifReporte ===
                    nombre;


                tab.classList.toggle(
                    "activo",
                    activa
                );


                tab.setAttribute(
                    "aria-selected",
                    String(activa)
                );

            }
        );


        renderCabecera();


        renderTabla();


        consultarReporte();

    }


    /* =====================================================
                    LIMPIAR FILTROS
    ===================================================== */

    function limpiarFiltros() {

        el.proyecto.value =
            "";


        el.ambito.value =
            "";


        el.anio.value =
            "";


        el.busqueda.value =
            "";


        estado.pagina =
            1;

    }


    /* =====================================================
                    EXPORTACIÓN CSV
    ===================================================== */

    function escaparCsv(valor) {

        const texto =
            valor === null ||
            valor === undefined

                ? ""

                : String(valor);


        return `"${texto.replaceAll(
            '"',
            '""'
        )}"`;

    }


    function exportarCsv() {

        const filas =
            filasFiltradas();


        if (
            filas.length === 0
        ) {

            return;

        }


        const config =
            reportes[
                estado.reporte
            ];


        const lineas =
            [];


        lineas.push(

            config.columnas
                .map(
                    ([
                        ,
                        titulo
                    ]) =>
                        escaparCsv(
                            titulo
                        )
                )
                .join(",")

        );


        filas.forEach(
            fila => {

                lineas.push(

                    config.columnas
                        .map(
                            ([
                                campo,
                                ,
                                tipo
                            ]) =>
                                escaparCsv(
                                    valorVisual(
                                        fila,
                                        campo,
                                        tipo
                                    )
                                )
                        )
                        .join(",")

                );

            }
        );


        const blob =
            new Blob(
                [
                    `\uFEFF${lineas.join(
                        "\r\n"
                    )}`
                ],
                {
                    type:
                        "text/csv;charset=utf-8"
                }
            );


        const url =
            URL.createObjectURL(
                blob
            );


        const enlace =
            document.createElement(
                "a"
            );


        enlace.href =
            url;


        enlace.download =
            `reporte-fifonafe-${estado.reporte}-${new Date()
                .toISOString()
                .slice(
                    0,
                    10
                )}.csv`;


        document.body.appendChild(
            enlace
        );


        enlace.click();


        enlace.remove();


        URL.revokeObjectURL(
            url
        );

    }


    /* =====================================================
                    CARGAR PROYECTOS
    ===================================================== */

    async function cargarProyectos() {

        const proyectos =
            await window.ProyectosAPI
                .listar();


        estado.proyectos.clear();


        el.proyecto.innerHTML =
            `
            <option value="">
                Todos los proyectos autorizados
            </option>
            `;


        if (
            !Array.isArray(
                proyectos
            )
        ) {

            return;

        }


        proyectos.forEach(
            proyecto => {

                const id =
                    Number(
                        proyecto.id_proyecto
                    );


                const nombre =
                    proyecto.nombre_proyecto ||
                    `Proyecto ${id}`;


                estado.proyectos.set(
                    id,
                    nombre
                );


                const opcion =
                    document.createElement(
                        "option"
                    );


                opcion.value =
                    String(id);


                opcion.textContent =
                    nombre;


                el.proyecto.appendChild(
                    opcion
                );

            }
        );

    }


    /* =====================================================
                        EVENTOS
    ===================================================== */

    el.tabs.forEach(
        tab => {

            tab.addEventListener(
                "click",
                () => {

                    configurarReporte(
                        tab.dataset.fifReporte
                    );

                }
            );

        }
    );


    el.form.addEventListener(
        "submit",
        async event => {

            event.preventDefault();


            await consultarReporte();

        }
    );


    el.btnLimpiar.addEventListener(
        "click",
        () => {

            limpiarFiltros();

        }
    );


    el.btnExportar.addEventListener(
        "click",
        exportarCsv
    );


    el.busqueda.addEventListener(
        "input",
        () => {

            estado.pagina =
                1;


            renderTabla();

        }
    );


    el.porPagina.addEventListener(
        "change",
        () => {

            estado.porPagina =
                Number(
                    el.porPagina.value
                ) ||
                50;


            estado.pagina =
                1;


            renderTabla();

        }
    );


    el.btnAnterior.addEventListener(
        "click",
        () => {

            if (
                estado.pagina <= 1
            ) {

                return;

            }


            estado.pagina -=
                1;


            renderTabla();

        }
    );


    el.btnSiguiente.addEventListener(
        "click",
        () => {

            const totalPaginas =
                Math.max(
                    1,
                    Math.ceil(
                        filasFiltradas().length /
                        estado.porPagina
                    )
                );


            if (
                estado.pagina >=
                totalPaginas
            ) {

                return;

            }


            estado.pagina +=
                1;


            renderTabla();

        }
    );


    /* =====================================================
                    INICIALIZACIÓN
    ===================================================== */

    try {

        const sesion =
            await window.AuthAPI
                .requerirSesion();


        if (
            !sesion
        ) {

            return;

        }


        await cargarProyectos();


        configurarReporte(
            "cobertura"
        );


    } catch (error) {

        mostrarError(
            error
        );

    }

});