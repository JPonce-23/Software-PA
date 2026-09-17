document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    /* =====================================================
                        ESTADO
    ===================================================== */

    const estado = {
        reporte: "valores",
        filas: [],
        proyectos: new Map(),
        entidades: new Map(),
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
                "conveniosReportesError"
            ),

        info:
            document.getElementById(
                "conveniosReportesInfo"
            ),

        nota:
            document.getElementById(
                "notaReporteConvenio"
            ),

        descripcion:
            document.getElementById(
                "descripcionReporteConvenio"
            ),

        subtituloResultados:
            document.getElementById(
                "subtituloResultadosConvenios"
            ),

        tabs:
            Array.from(
                document.querySelectorAll(
                    "[data-reporte]"
                )
            ),

        form:
            document.getElementById(
                "formReportesConvenios"
            ),

        filtros:
            document.getElementById(
                "filtrosReportesConvenios"
            ),

        btnLimpiar:
            document.getElementById(
                "btnLimpiarReportesConvenios"
            ),

        btnConsultar:
            document.getElementById(
                "btnConsultarReportesConvenios"
            ),

        resumen:
            document.getElementById(
                "resumenReportesConvenios"
            ),

        busqueda:
            document.getElementById(
                "busquedaReportesConvenios"
            ),

        btnExportar:
            document.getElementById(
                "btnExportarReportesConvenios"
            ),

        total:
            document.getElementById(
                "totalReportesConvenios"
            ),

        porPagina:
            document.getElementById(
                "porPaginaReportesConvenios"
            ),

        thead:
            document.getElementById(
                "theadReportesConvenios"
            ),

        tbody:
            document.getElementById(
                "tbodyReportesConvenios"
            ),

        btnAnterior:
            document.getElementById(
                "btnAnteriorReportesConvenios"
            ),

        btnSiguiente:
            document.getElementById(
                "btnSiguienteReportesConvenios"
            ),

        pagina:
            document.getElementById(
                "paginaReportesConvenios"
            )
    };


    /* =====================================================
                    OPCIONES DE FILTROS
    ===================================================== */

    const opciones = {

        ambito: [
            ["", "Todos"],
            ["colectivo", "Colectivo"],
            ["individual", "Individual"]
        ],

        booleano: [
            ["", "Todos"],
            ["true", "Sí"],
            ["false", "No"]
        ],

        efecto: [
            ["", "Todos"],
            ["adicion", "Adición"],
            ["sustitucion", "Sustitución"],
            ["correccion", "Corrección"],
            ["sin_cambio", "Sin cambio"],
            ["pendiente", "Pendiente"]
        ],

        mes: [
            ["", "Todos"],
            ["1", "Enero"],
            ["2", "Febrero"],
            ["3", "Marzo"],
            ["4", "Abril"],
            ["5", "Mayo"],
            ["6", "Junio"],
            ["7", "Julio"],
            ["8", "Agosto"],
            ["9", "Septiembre"],
            ["10", "Octubre"],
            ["11", "Noviembre"],
            ["12", "Diciembre"]
        ],

        trimestre: [
            ["", "Todos"],
            ["1", "T1"],
            ["2", "T2"],
            ["3", "T3"],
            ["4", "T4"]
        ]

    };


    /* =====================================================
                CONFIGURACIÓN DE REPORTES
    ===================================================== */

    const reportes = {

        valores: {

            titulo:
                "Valores declarados",

            descripcion:
                "Valores literales declarados por instrumento y concepto; no deben sumarse entre universos 90 %, 100 % y BDT.",

            nota:
                "Cada fila representa un valor declarado del convenio. Superficie, monto 90 %, monto 100 % y BDT son conceptos distintos y no deben consolidarse entre sí.",

            api:
                params =>
                    window.ReportesAPI
                        .obtenerConveniosValoresDeclarados(
                            params
                        ),

            filtros: [
                "id_proyecto",
                "id_entidad",
                "id_proyecto_nucleo",
                "id_convenio",
                "ambito",
                "concepto_valor",
                "firma_acreditada"
            ],

            columnas: [
                [
                    "id_proyecto",
                    "Proyecto",
                    "proyecto"
                ],
                [
                    "id_entidad",
                    "Entidad",
                    "entidad"
                ],
                [
                    "id_proyecto_nucleo",
                    "Proyecto-núcleo",
                    "entero"
                ],
                [
                    "id_convenio",
                    "Convenio",
                    "entero"
                ],
                [
                    "ambito",
                    "Ámbito",
                    "badge"
                ],
                [
                    "tipo_cop_operativo",
                    "Tipo COP",
                    "texto"
                ],
                [
                    "tipo_convenio",
                    "Tipo convenio",
                    "texto"
                ],
                [
                    "concepto",
                    "Concepto",
                    "texto"
                ],
                [
                    "unidad",
                    "Unidad",
                    "texto"
                ],
                [
                    "valor_declarado",
                    "Valor declarado",
                    "decimal"
                ],
                [
                    "fecha_instrumento_reportada",
                    "Fecha instrumento",
                    "fecha"
                ],
                [
                    "firma_acreditada",
                    "Firma acreditada",
                    "booleano"
                ]
            ],

            resumen: filas => [
                [
                    "Registros",
                    filas.length
                ],
                [
                    "Convenios",
                    contarUnicos(
                        filas,
                        "id_convenio"
                    )
                ],
                [
                    "Con firma acreditada",
                    filas.filter(
                        fila =>
                            fila.firma_acreditada === true
                    ).length
                ],
                [
                    "Sin firma acreditada",
                    filas.filter(
                        fila =>
                            fila.firma_acreditada === false
                    ).length
                ]
            ]
        },


        impactos: {

            titulo:
                "Impactos",

            descripcion:
                "Impactos de superficie y montos separados por convenio, afectación, concepto y efecto.",

            nota:
                "Un valor NULL pendiente no equivale a cero. La superficie se reporta por convenio-afectación y los montos por instrumento/concepto.",

            api:
                params =>
                    window.ReportesAPI
                        .obtenerConveniosImpactos(
                            params
                        ),

            filtros: [
                "id_proyecto",
                "id_entidad",
                "id_proyecto_nucleo",
                "id_convenio",
                "id_afectacion",
                "ambito",
                "concepto_impacto",
                "efecto",
                "pendiente",
                "firma_acreditada"
            ],

            columnas: [
                [
                    "clave_impacto",
                    "Clave impacto",
                    "mono"
                ],
                [
                    "id_proyecto",
                    "Proyecto",
                    "proyecto"
                ],
                [
                    "id_entidad",
                    "Entidad",
                    "entidad"
                ],
                [
                    "id_proyecto_nucleo",
                    "Proyecto-núcleo",
                    "entero"
                ],
                [
                    "id_convenio",
                    "Convenio",
                    "entero"
                ],
                [
                    "id_convenio_afectacion",
                    "Convenio-afectación",
                    "entero"
                ],
                [
                    "id_afectacion",
                    "Afectación",
                    "entero"
                ],
                [
                    "ambito",
                    "Ámbito",
                    "badge"
                ],
                [
                    "tipo_cop_operativo",
                    "Tipo COP",
                    "texto"
                ],
                [
                    "tipo_convenio",
                    "Tipo convenio",
                    "texto"
                ],
                [
                    "concepto",
                    "Concepto",
                    "texto"
                ],
                [
                    "unidad",
                    "Unidad",
                    "texto"
                ],
                [
                    "efecto",
                    "Efecto",
                    "badge"
                ],
                [
                    "fecha_efecto",
                    "Fecha efecto",
                    "fecha"
                ],
                [
                    "valor_impacto",
                    "Valor impacto",
                    "decimal"
                ],
                [
                    "pendiente",
                    "Pendiente",
                    "booleano"
                ],
                [
                    "firma_acreditada",
                    "Firma acreditada",
                    "booleano"
                ]
            ],

            resumen: filas => [
                [
                    "Impactos",
                    filas.length
                ],
                [
                    "Clasificados",
                    filas.filter(
                        fila =>
                            fila.pendiente === false &&
                            fila.valor_impacto !== null
                    ).length
                ],
                [
                    "Pendientes",
                    filas.filter(
                        fila =>
                            fila.pendiente === true
                    ).length
                ],
                [
                    "Sin firma acreditada",
                    filas.filter(
                        fila =>
                            fila.firma_acreditada === false
                    ).length
                ]
            ]
        },


        periodo: {

            titulo:
                "Impactos por periodo",

            descripcion:
                "Subtotales conocidos por año, mes, trimestre, concepto, unidad y efecto.",

            nota:
                "Este reporte excluye pendientes, firmas no acreditadas, fechas de efecto ausentes e impactos sin valor. Por diseño no representa un total definitivo del universo.",

            api:
                params =>
                    window.ReportesAPI
                        .obtenerConveniosImpactosPeriodo(
                            params
                        ),

            filtros: [
                "id_proyecto",
                "id_entidad",
                "anio",
                "mes",
                "trimestre",
                "ambito",
                "tipo_cop_operativo",
                "tipo_convenio",
                "concepto_impacto",
                "efecto"
            ],

            columnas: [
                [
                    "id_proyecto",
                    "Proyecto",
                    "proyecto"
                ],
                [
                    "id_entidad",
                    "Entidad",
                    "entidad"
                ],
                [
                    "ambito",
                    "Ámbito",
                    "badge"
                ],
                [
                    "tipo_cop_operativo",
                    "Tipo COP",
                    "texto"
                ],
                [
                    "tipo_convenio",
                    "Tipo convenio",
                    "texto"
                ],
                [
                    "concepto",
                    "Concepto",
                    "texto"
                ],
                [
                    "unidad",
                    "Unidad",
                    "texto"
                ],
                [
                    "efecto",
                    "Efecto",
                    "badge"
                ],
                [
                    "anio",
                    "Año",
                    "entero"
                ],
                [
                    "mes",
                    "Mes",
                    "entero"
                ],
                [
                    "trimestre",
                    "Trimestre",
                    "entero"
                ],
                [
                    "cantidad",
                    "Cantidad",
                    "entero"
                ],
                [
                    "valor_impacto",
                    "Valor impacto",
                    "decimal"
                ]
            ],

            resumen: filas => [
                [
                    "Filas",
                    filas.length
                ],
                [
                    "Cantidad",
                    sumar(
                        filas,
                        "cantidad"
                    )
                ],
                [
                    "Proyectos",
                    contarUnicos(
                        filas,
                        "id_proyecto"
                    )
                ],
                [
                    "Entidades",
                    contarUnicos(
                        filas,
                        "id_entidad"
                    )
                ]
            ]
        },


        cobertura: {

            titulo:
                "Cobertura de impactos",

            descripcion:
                "Cobertura del universo de impactos: clasificados, pendientes y casos sin firma acreditada.",

            nota:
                "La cobertura acompaña a los subtotales de impacto. Sirve para medir qué tan completo está el universo antes de interpretar cifras agregadas.",

            api:
                params =>
                    window.ReportesAPI
                        .obtenerConveniosCoberturaImpactos(
                            params
                        ),

            filtros: [
                "id_proyecto",
                "id_entidad",
                "ambito",
                "concepto_impacto"
            ],

            columnas: [
                [
                    "id_proyecto",
                    "Proyecto",
                    "proyecto"
                ],
                [
                    "id_entidad",
                    "Entidad",
                    "entidad"
                ],
                [
                    "ambito",
                    "Ámbito",
                    "badge"
                ],
                [
                    "concepto",
                    "Concepto",
                    "texto"
                ],
                [
                    "unidad",
                    "Unidad",
                    "texto"
                ],
                [
                    "universo",
                    "Universo",
                    "entero"
                ],
                [
                    "clasificados",
                    "Clasificados",
                    "entero"
                ],
                [
                    "pendientes",
                    "Pendientes",
                    "entero"
                ],
                [
                    "sin_firma_acreditada",
                    "Sin firma acreditada",
                    "entero"
                ],
                [
                    "cobertura_calculada",
                    "Cobertura",
                    "porcentaje"
                ]
            ],

            transformar:
                filas =>
                    filas.map(
                        fila => ({
                            ...fila,

                            cobertura_calculada:
                                numero(
                                    fila.universo
                                ) > 0
                                    ? (
                                        numero(
                                            fila.clasificados
                                        ) /
                                        numero(
                                            fila.universo
                                        )
                                    ) * 100
                                    : 0
                        })
                    ),

            resumen: filas => {

                const universo =
                    sumar(
                        filas,
                        "universo"
                    );

                const clasificados =
                    sumar(
                        filas,
                        "clasificados"
                    );


                return [
                    [
                        "Universo",
                        universo
                    ],
                    [
                        "Clasificados",
                        clasificados
                    ],
                    [
                        "Pendientes",
                        sumar(
                            filas,
                            "pendientes"
                        )
                    ],
                    [
                        "Cobertura",
                        universo > 0
                            ? `${formatearDecimal(
                                clasificados /
                                universo *
                                100,
                                2
                            )} %`
                            : "0 %"
                    ]
                ];

            }
        }

    };


    /* =====================================================
                    DEFINICIONES DE FILTROS
    ===================================================== */

    const definicionesFiltros = {

        id_proyecto: {
            etiqueta:
                "Proyecto",

            tipo:
                "proyecto",

            param:
                "id_proyecto"
        },


        id_entidad: {
            etiqueta:
                "Entidad federativa",

            tipo:
                "entidad",

            param:
                "id_entidad"
        },


        id_proyecto_nucleo: {
            etiqueta:
                "ID proyecto-núcleo",

            tipo:
                "number",

            param:
                "id_proyecto_nucleo",

            min:
                1
        },


        id_convenio: {
            etiqueta:
                "ID convenio",

            tipo:
                "number",

            param:
                "id_convenio",

            min:
                1
        },


        id_afectacion: {
            etiqueta:
                "ID afectación",

            tipo:
                "number",

            param:
                "id_afectacion",

            min:
                1
        },


        ambito: {
            etiqueta:
                "Ámbito",

            tipo:
                "select",

            param:
                "ambito",

            opciones:
                opciones.ambito
        },


        concepto_valor: {
            etiqueta:
                "Concepto",

            tipo:
                "select",

            param:
                "concepto",

            opciones: [
                [
                    "",
                    "Todos"
                ],
                [
                    "superficie_declarada",
                    "Superficie declarada"
                ],
                [
                    "monto_90_declarado",
                    "Monto 90 % declarado"
                ],
                [
                    "monto_100_declarado",
                    "Monto 100 % declarado"
                ],
                [
                    "monto_bdt_declarado",
                    "Monto BDT declarado"
                ]
            ]
        },


        concepto_impacto: {
            etiqueta:
                "Concepto",

            tipo:
                "select",

            param:
                "concepto",

            opciones: [
                [
                    "",
                    "Todos"
                ],
                [
                    "superficie",
                    "Superficie"
                ],
                [
                    "monto_90",
                    "Monto 90 %"
                ],
                [
                    "monto_100",
                    "Monto 100 %"
                ],
                [
                    "monto_bdt",
                    "Monto BDT"
                ],
                [
                    "monto_pendiente_clasificar",
                    "Monto pendiente de clasificar"
                ]
            ]
        },


        firma_acreditada: {
            etiqueta:
                "Firma acreditada",

            tipo:
                "select",

            param:
                "firma_acreditada",

            opciones:
                opciones.booleano
        },


        pendiente: {
            etiqueta:
                "Pendiente",

            tipo:
                "select",

            param:
                "pendiente",

            opciones:
                opciones.booleano
        },


        efecto: {
            etiqueta:
                "Efecto",

            tipo:
                "select",

            param:
                "efecto",

            opciones:
                opciones.efecto
        },


        anio: {
            etiqueta:
                "Año",

            tipo:
                "number",

            param:
                "anio",

            min:
                2000,

            max:
                2200
        },


        mes: {
            etiqueta:
                "Mes",

            tipo:
                "select",

            param:
                "mes",

            opciones:
                opciones.mes
        },


        trimestre: {
            etiqueta:
                "Trimestre",

            tipo:
                "select",

            param:
                "trimestre",

            opciones:
                opciones.trimestre
        },


        tipo_cop_operativo: {
            etiqueta:
                "Tipo COP operativo",

            tipo:
                "text",

            param:
                "tipo_cop_operativo",

            placeholder:
                "Ej. ORIGEN"
        },


        tipo_convenio: {
            etiqueta:
                "Tipo de convenio",

            tipo:
                "text",

            param:
                "tipo_convenio",

            placeholder:
                "Ej. modificatorio"
        }

    };


    /* =====================================================
                    FUNCIONES GENERALES
    ===================================================== */

    function numero(valor) {

        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return 0;
        }


        const n =
            Number(valor);


        return Number.isFinite(n)
            ? n
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


    function contarUnicos(
        filas,
        campo
    ) {

        return new Set(
            filas
                .map(
                    fila =>
                        fila[campo]
                )
                .filter(
                    valor =>
                        valor !== null &&
                        valor !== undefined &&
                        valor !== ""
                )
        ).size;

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


        window.ClienteAPI.mostrarErrorAPI(
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
                    CREACIÓN DE FILTROS
    ===================================================== */

    function crearCampo(
        nombreFiltro
    ) {

        const def =
            definicionesFiltros[
                nombreFiltro
            ];


        const wrapper =
            document.createElement(
                "label"
            );


        wrapper.className =
            "convenios-reportes-campo";


        const etiqueta =
            document.createElement(
                "span"
            );


        etiqueta.textContent =
            def.etiqueta;


        wrapper.appendChild(
            etiqueta
        );


        let control;


        if (
            def.tipo === "proyecto" ||
            def.tipo === "entidad" ||
            def.tipo === "select"
        ) {

            control =
                document.createElement(
                    "select"
                );


            if (
                def.tipo === "proyecto"
            ) {

                agregarOpcion(
                    control,
                    "",
                    "Todos los proyectos autorizados"
                );


                for (
                    const [
                        id,
                        nombre
                    ]
                    of estado.proyectos.entries()
                ) {

                    agregarOpcion(
                        control,
                        String(id),
                        nombre
                    );

                }

            } else if (
                def.tipo === "entidad"
            ) {

                agregarOpcion(
                    control,
                    "",
                    "Todas las entidades"
                );


                for (
                    const [
                        id,
                        nombre
                    ]
                    of estado.entidades.entries()
                ) {

                    agregarOpcion(
                        control,
                        String(id),
                        nombre
                    );

                }

            } else {

                for (
                    const [
                        valor,
                        texto
                    ]
                    of def.opciones
                ) {

                    agregarOpcion(
                        control,
                        valor,
                        texto
                    );

                }

            }

        } else {

            control =
                document.createElement(
                    "input"
                );


            control.type =
                def.tipo;


            if (
                def.min !== undefined
            ) {
                control.min =
                    String(
                        def.min
                    );
            }


            if (
                def.max !== undefined
            ) {
                control.max =
                    String(
                        def.max
                    );
            }


            if (
                def.tipo === "number"
            ) {
                control.step =
                    "1";
            }


            if (
                def.placeholder
            ) {
                control.placeholder =
                    def.placeholder;
            }

        }


        control.dataset.param =
            def.param;


        control.dataset.filtro =
            nombreFiltro;


        control.id =
            `reporteConvenioFiltro_${nombreFiltro}`;


        wrapper.appendChild(
            control
        );


        return wrapper;

    }


    function agregarOpcion(
        select,
        valor,
        texto
    ) {

        const option =
            document.createElement(
                "option"
            );


        option.value =
            valor;


        option.textContent =
            texto;


        select.appendChild(
            option
        );

    }


    function renderFiltros() {

        const config =
            reportes[
                estado.reporte
            ];


        el.filtros.replaceChildren();


        config.filtros.forEach(
            nombre => {

                el.filtros.appendChild(
                    crearCampo(
                        nombre
                    )
                );

            }
        );

    }


    function obtenerParametros() {

        const params = {};


        el.filtros
            .querySelectorAll(
                "[data-param]"
            )
            .forEach(
                control => {

                    const valor =
                        String(
                            control.value ??
                            ""
                        ).trim();


                    if (
                        valor !== ""
                    ) {

                        params[
                            control.dataset.param
                        ] =
                            valor;

                    }

                }
            );


        return params;

    }


    /* =====================================================
                    FORMATEADORES
    ===================================================== */

    function nombreProyecto(id) {

        if (
            id === null ||
            id === undefined
        ) {
            return "—";
        }


        return (
            estado.proyectos.get(
                Number(id)
            ) ||
            `Proyecto ${id}`
        );

    }


    function nombreEntidad(id) {

        if (
            id === null ||
            id === undefined
        ) {
            return "—";
        }


        return (
            estado.entidades.get(
                Number(id)
            ) ||
            `Entidad ${id}`
        );

    }


    function textoCatalogo(valor) {

        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return "—";
        }


        return String(valor)
            .replaceAll(
                "_",
                " "
            );

    }


    function formatearDecimal(
        valor,
        max = 7
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
                minimumFractionDigits:
                    0,

                maximumFractionDigits:
                    max
            }
        ).format(
            numero(valor)
        );

    }


    function formatearFecha(valor) {

        if (!valor) {
            return "—";
        }


        const partes =
            String(valor)
                .split("-");


        return partes.length === 3
            ? `${partes[2]}/${partes[1]}/${partes[0]}`
            : String(valor);

    }


    function formatearBooleano(valor) {

        if (
            valor === true
        ) {
            return "Sí";
        }


        if (
            valor === false
        ) {
            return "No";
        }


        return "—";

    }


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


            case "entidad":

                return nombreEntidad(
                    valor
                );


            case "texto":

                return textoCatalogo(
                    valor
                );


            case "entero":

                return (
                    valor === null ||
                    valor === undefined
                )
                    ? "—"
                    : new Intl.NumberFormat(
                        "es-MX",
                        {
                            maximumFractionDigits:
                                0
                        }
                    ).format(
                        numero(valor)
                    );


            case "decimal":

                return formatearDecimal(
                    valor
                );


            case "fecha":

                return formatearFecha(
                    valor
                );


            case "booleano":

                return formatearBooleano(
                    valor
                );


            case "porcentaje":

                return (
                    `${formatearDecimal(
                        valor,
                        2
                    )} %`
                );


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


    function varianteBadge(
        campo,
        valor
    ) {

        if (
            campo === "ambito"
        ) {

            return valor === "individual"
                ? "info"
                : "ok";

        }


        if (
            campo === "efecto"
        ) {

            if (
                valor === "pendiente"
            ) {
                return "peligro";
            }


            if (
                valor === "sin_cambio"
            ) {
                return "neutro";
            }


            return "info";

        }


        return "neutro";

    }


    /* =====================================================
                    CABECERA DE TABLA
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
                    FILTRO LOCAL
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

                const bolsa =
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


                return bolsa.includes(
                    termino
                );

            }
        );

    }


    /* =====================================================
                        KPIs
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
                    "convenios-reportes-kpi";


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
                    typeof valor === "number"
                        ? new Intl.NumberFormat(
                            "es-MX",
                            {
                                maximumFractionDigits:
                                    7
                            }
                        ).format(
                            valor
                        )
                        : String(valor);


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
                "convenios-reportes-tabla-estado";


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


                        const texto =
                            valorVisual(
                                fila,
                                campo,
                                tipo
                            );


                        if (
                            tipo === "badge"
                        ) {

                            const span =
                                document.createElement(
                                    "span"
                                );


                            span.className =
                                `convenios-reportes-badge convenios-reportes-badge-${varianteBadge(
                                    campo,
                                    fila[campo]
                                )}`;


                            span.textContent =
                                textoCatalogo(
                                    fila[campo]
                                );


                            td.appendChild(
                                span
                            );


                        } else if (
                            tipo === "booleano"
                        ) {

                            const span =
                                document.createElement(
                                    "span"
                                );


                            const esOk =
                                fila[campo] === true;


                            span.className =
                                `convenios-reportes-badge convenios-reportes-badge-${
                                    esOk
                                        ? "ok"
                                        : fila[campo] === false
                                            ? "peligro"
                                            : "neutro"
                                }`;


                            span.textContent =
                                texto;


                            td.appendChild(
                                span
                            );


                        } else {

                            td.textContent =
                                texto;

                        }


                        if (
                            [
                                "entero",
                                "decimal",
                                "porcentaje"
                            ].includes(
                                tipo
                            )
                        ) {

                            td.classList.add(
                                "convenios-reportes-numero"
                            );

                        }


                        if (
                            tipo === "mono"
                        ) {

                            td.classList.add(
                                "convenios-reportes-mono"
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


        el.tbody.replaceChildren();


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
            "convenios-reportes-tabla-estado";


        td.textContent =
            "Consultando reporte...";


        tr.appendChild(
            td
        );


        el.tbody.appendChild(
            tr
        );

    }


    /* =====================================================
                    LLAMADA AL BACKEND
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


        ponerCargando();


        try {

            const config =
                reportes[
                    estado.reporte
                ];


            /*
             * AQUÍ ocurre la llamada.
             *
             * config.api apunta a una función
             * de window.ReportesAPI, definida
             * en js/api/reportes.js.
             */
            let respuesta =
                await config.api(
                    obtenerParametros()
                );


            let filas =
                Array.isArray(
                    respuesta
                )
                    ? respuesta
                    : [];


            if (
                typeof config.transformar ===
                "function"
            ) {

                filas =
                    config.transformar(
                        filas
                    );

            }


            estado.filas =
                filas;


            estado.pagina =
                1;


            el.busqueda.value =
                "";


            renderTabla();


            if (
                filas.length === 0
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
                    CAMBIO DE PESTAÑA
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


        el.descripcion.textContent =
            config.descripcion;


        el.subtituloResultados.textContent =
            config.descripcion;


        el.nota.textContent =
            config.nota;


        el.tabs.forEach(
            tab => {

                const activo =
                    tab.dataset.reporte ===
                    nombre;


                tab.classList.toggle(
                    "activo",
                    activo
                );


                tab.setAttribute(
                    "aria-selected",
                    String(activo)
                );

            }
        );


        renderFiltros();


        renderCabecera();


        renderTabla();


        consultarReporte();

    }


    /* =====================================================
                    LIMPIAR FILTROS
    ===================================================== */

    function limpiarFiltros() {

        renderFiltros();


        estado.pagina =
            1;


        el.busqueda.value =
            "";

    }


    /* =====================================================
                    EXPORTAR CSV
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


        const lineas = [];


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
            `reporte-convenios-${estado.reporte}-${new Date()
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
                    CATÁLOGOS BASE
    ===================================================== */

    async function cargarCatalogosBase() {

        const [
            proyectos,
            entidades
        ] =
            await Promise.all([
                window.ProyectosAPI.listar(),
                window.CatalogosAPI.obtenerEntidades()
            ]);


        estado.proyectos.clear();


        if (
            Array.isArray(
                proyectos
            )
        ) {

            proyectos.forEach(
                proyecto => {

                    const id =
                        Number(
                            proyecto.id_proyecto
                        );


                    estado.proyectos.set(
                        id,
                        proyecto.nombre_proyecto ||
                        `Proyecto ${id}`
                    );

                }
            );

        }


        estado.entidades.clear();


        if (
            Array.isArray(
                entidades
            )
        ) {

            entidades.forEach(
                entidad => {

                    const id =
                        Number(
                            entidad.id_entidad
                        );


                    estado.entidades.set(
                        id,
                        entidad.nombre ||
                        `Entidad ${id}`
                    );

                }
            );

        }

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
                        tab.dataset.reporte
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
        limpiarFiltros
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


        if (!sesion) {
            return;
        }


        await cargarCatalogosBase();


        configurarReporte(
            "valores"
        );


    } catch (error) {

        mostrarError(
            error
        );

    }

});