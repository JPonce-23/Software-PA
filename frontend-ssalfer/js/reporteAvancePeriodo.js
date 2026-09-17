document.addEventListener("DOMContentLoaded", async () => {
    "use strict";


    const estado = {

        filas: [],

        proyectos: new Map(),

        entidades: new Map(),

        pagina: 1,

        porPagina: 50,

        cargando: false

    };


    const el = {

        error:
            document.getElementById("avanceError"),

        info:
            document.getElementById("avanceInfo"),

        form:
            document.getElementById("formAvancePeriodo"),

        proyecto:
            document.getElementById("filtroProyecto"),

        entidad:
            document.getElementById("filtroEntidad"),

        ambito:
            document.getElementById("filtroAmbito"),

        anio:
            document.getElementById("filtroAnio"),

        mes:
            document.getElementById("filtroMes"),

        trimestre:
            document.getElementById("filtroTrimestre"),

        indicador:
            document.getElementById("filtroIndicador"),

        tipoCop:
            document.getElementById("filtroTipoCop"),

        tipoConvenio:
            document.getElementById("filtroTipoConvenio"),

        destinoSuperficie:
            document.getElementById(
                "filtroDestinoSuperficie"
            ),

        btnConsultar:
            document.getElementById(
                "btnConsultarAvance"
            ),

        btnLimpiar:
            document.getElementById(
                "btnLimpiarAvance"
            ),

        btnExportar:
            document.getElementById(
                "btnExportarAvance"
            ),

        busqueda:
            document.getElementById(
                "busquedaAvance"
            ),

        tabla:
            document.getElementById(
                "tablaAvancePeriodo"
            ),

        totalFilas:
            document.getElementById(
                "totalFilasAvance"
            ),

        porPagina:
            document.getElementById(
                "avancePorPagina"
            ),

        paginaTexto:
            document.getElementById(
                "avancePaginaTexto"
            ),

        btnAnterior:
            document.getElementById(
                "btnAvanceAnterior"
            ),

        btnSiguiente:
            document.getElementById(
                "btnAvanceSiguiente"
            ),

        kpiProgramado:
            document.getElementById(
                "kpiProgramado"
            ),

        kpiRealizado:
            document.getElementById(
                "kpiRealizado"
            ),

        kpiCantidad:
            document.getElementById(
                "kpiCantidad"
            ),

        kpiSuperficie:
            document.getElementById(
                "kpiSuperficie"
            ),

        kpiMonto:
            document.getElementById(
                "kpiMonto"
            )

    };


    function limpiarMensajes() {

        el.error.hidden = true;
        el.error.textContent = "";

        el.info.hidden = true;
        el.info.textContent = "";

    }


    function mostrarError(error) {

        el.info.hidden = true;

        window.ClienteAPI.mostrarErrorAPI(
            error,
            el.error
        );

    }


    function mostrarInfo(mensaje) {

        el.error.hidden = true;

        el.info.textContent =
            mensaje;

        el.info.hidden =
            false;

    }


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


    function formatearSuperficie(valor) {

        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return "—";
        }

        return (
            new Intl.NumberFormat(
                "es-MX",
                {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 7
                }
            ).format(
                numero(valor)
            ) +
            " ha"
        );

    }


    function formatearMonto(valor) {

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
                style: "currency",
                currency: "MXN",
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        ).format(
            numero(valor)
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


    function nombreProyecto(idProyecto) {

        return (
            estado.proyectos.get(
                Number(idProyecto)
            ) ||
            `Proyecto ${idProyecto}`
        );

    }


    function nombreEntidad(idEntidad) {

        return (
            estado.entidades.get(
                Number(idEntidad)
            ) ||
            `Entidad ${idEntidad}`
        );

    }


    /* =====================================================
                    PARÁMETROS DEL BACKEND
    ===================================================== */

    function obtenerParametros() {

        const params = {};


        const valores = {

            id_proyecto:
                el.proyecto.value,

            id_entidad:
                el.entidad.value,

            ambito:
                el.ambito.value,

            anio:
                el.anio.value,

            mes:
                el.mes.value,

            trimestre:
                el.trimestre.value,

            indicador:
                el.indicador
                    .value
                    .trim(),

            tipo_cop_operativo:
                el.tipoCop.value,

            tipo_convenio:
                el.tipoConvenio.value,

            destino_superficie:
                el.destinoSuperficie
                    .value
                    .trim()

        };


        Object.entries(
            valores
        ).forEach(
            ([clave, valor]) => {

                if (
                    valor !== null &&
                    valor !== undefined &&
                    String(valor).trim() !== ""
                ) {

                    params[clave] =
                        String(valor).trim();

                }

            }
        );


        return params;

    }


    /* =====================================================
                    FILTRADO LOCAL
    ===================================================== */

    function filasFiltradas() {

        const termino =
            el.busqueda
                .value
                .trim()
                .toLocaleLowerCase(
                    "es-MX"
                );


        if (!termino) {

            return estado.filas;

        }


        return estado.filas.filter(
            fila => {

                const contenido = [

                    nombreProyecto(
                        fila.id_proyecto
                    ),

                    nombreEntidad(
                        fila.id_entidad
                    ),

                    fila.ambito,

                    fila.tipo_cop_operativo,

                    fila.tipo_convenio,

                    fila.destino_superficie,

                    fila.anio,

                    fila.mes,

                    fila.trimestre,

                    fila.indicador,

                    fila.programado,

                    fila.realizado,

                    fila.cantidad,

                    fila.superficie_ha,

                    fila.monto

                ]
                    .filter(
                        valor =>
                            valor !== null &&
                            valor !== undefined
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


    function celda(
        valor,
        clase = ""
    ) {

        const td =
            document.createElement("td");


        if (clase) {

            td.className =
                clase;

        }


        td.textContent =
            valor;


        return td;

    }


    function badge(
        valor,
        variante = "neutro"
    ) {

        const span =
            document.createElement(
                "span"
            );


        span.className =
            `avance-badge avance-badge-${variante}`;


        span.textContent =
            valor;


        return span;

    }


    /* =====================================================
                        KPIs
    ===================================================== */

    function renderKpis(filas) {

        const totales =
            filas.reduce(
                (
                    acumulado,
                    fila
                ) => {

                    acumulado.programado +=
                        numero(
                            fila.programado
                        );

                    acumulado.realizado +=
                        numero(
                            fila.realizado
                        );

                    acumulado.cantidad +=
                        numero(
                            fila.cantidad
                        );

                    acumulado.superficie +=
                        numero(
                            fila.superficie_ha
                        );

                    acumulado.monto +=
                        numero(
                            fila.monto
                        );


                    return acumulado;

                },
                {
                    programado: 0,
                    realizado: 0,
                    cantidad: 0,
                    superficie: 0,
                    monto: 0
                }
            );


        el.kpiProgramado.textContent =
            formatearEntero(
                totales.programado
            );


        el.kpiRealizado.textContent =
            formatearEntero(
                totales.realizado
            );


        el.kpiCantidad.textContent =
            formatearEntero(
                totales.cantidad
            );


        el.kpiSuperficie.textContent =
            formatearSuperficie(
                totales.superficie
            );


        el.kpiMonto.textContent =
            formatearMonto(
                totales.monto
            );

    }


    /* =====================================================
                        TABLA
    ===================================================== */

    function renderTabla() {

        const filtradas =
            filasFiltradas();


        const total =
            filtradas.length;


        const totalPaginas =
            Math.max(
                1,
                Math.ceil(
                    total /
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


        const fin =
            inicio +
            estado.porPagina;


        const pagina =
            filtradas.slice(
                inicio,
                fin
            );


        el.tabla.replaceChildren();


        el.totalFilas.textContent =
            `${total.toLocaleString(
                "es-MX"
            )} registro(s)`;


        el.paginaTexto.textContent =
            `Página ${estado.pagina} de ${totalPaginas}`;


        el.btnAnterior.disabled =
            estado.cargando ||
            estado.pagina <= 1;


        el.btnSiguiente.disabled =
            estado.cargando ||
            estado.pagina >=
                totalPaginas;


        el.btnExportar.disabled =
            total === 0;


        renderKpis(
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
                celda(
                    estado.filas.length === 0
                        ? "No hay registros para los filtros seleccionados."
                        : "No hay coincidencias con la búsqueda local.",
                    "avance-tabla-estado"
                );


            td.colSpan =
                15;


            tr.appendChild(
                td
            );


            el.tabla.appendChild(
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


                tr.appendChild(
                    celda(
                        nombreProyecto(
                            fila.id_proyecto
                        )
                    )
                );


                tr.appendChild(
                    celda(
                        nombreEntidad(
                            fila.id_entidad
                        )
                    )
                );


                const tdAmbito =
                    document.createElement(
                        "td"
                    );


                tdAmbito.appendChild(
                    badge(
                        textoCatalogo(
                            fila.ambito
                        ),
                        fila.ambito ===
                            "individual"
                            ? "individual"
                            : "colectivo"
                    )
                );


                tr.appendChild(
                    tdAmbito
                );


                tr.appendChild(
                    celda(
                        String(
                            fila.anio ??
                            "—"
                        ),
                        "avance-numero"
                    )
                );


                tr.appendChild(
                    celda(
                        String(
                            fila.mes ??
                            "—"
                        ),
                        "avance-numero"
                    )
                );


                tr.appendChild(
                    celda(
                        String(
                            fila.trimestre ??
                            "—"
                        ),
                        "avance-numero"
                    )
                );


                tr.appendChild(
                    celda(
                        textoCatalogo(
                            fila.indicador
                        ),
                        "avance-indicador"
                    )
                );


                tr.appendChild(
                    celda(
                        textoCatalogo(
                            fila.tipo_cop_operativo
                        )
                    )
                );


                tr.appendChild(
                    celda(
                        textoCatalogo(
                            fila.tipo_convenio
                        )
                    )
                );


                tr.appendChild(
                    celda(
                        textoCatalogo(
                            fila.destino_superficie
                        )
                    )
                );


                tr.appendChild(
                    celda(
                        formatearEntero(
                            fila.programado
                        ),
                        "avance-numero"
                    )
                );


                tr.appendChild(
                    celda(
                        formatearEntero(
                            fila.realizado
                        ),
                        "avance-numero"
                    )
                );


                tr.appendChild(
                    celda(
                        formatearEntero(
                            fila.cantidad
                        ),
                        "avance-numero"
                    )
                );


                tr.appendChild(
                    celda(
                        formatearSuperficie(
                            fila.superficie_ha
                        ),
                        "avance-numero"
                    )
                );


                tr.appendChild(
                    celda(
                        formatearMonto(
                            fila.monto
                        ),
                        "avance-numero"
                    )
                );


                el.tabla.appendChild(
                    tr
                );

            }
        );

    }


    /* =====================================================
                    PROYECTOS Y ENTIDADES
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


        el.proyecto.innerHTML =
            `
            <option value="">
                Todos los proyectos autorizados
            </option>
            `;


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


                    const option =
                        document.createElement(
                            "option"
                        );


                    option.value =
                        String(id);


                    option.textContent =
                        proyecto.nombre_proyecto ||
                        `Proyecto ${id}`;


                    el.proyecto.appendChild(
                        option
                    );

                }
            );

        }


        el.entidad.innerHTML =
            `
            <option value="">
                Todas las entidades
            </option>
            `;


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


                    const option =
                        document.createElement(
                            "option"
                        );


                    option.value =
                        String(id);


                    option.textContent =
                        `${entidad.clave_inegi} — ${entidad.nombre}`;


                    el.entidad.appendChild(
                        option
                    );

                }
            );

        }

    }


    /* =====================================================
                    CONSULTAR BACKEND
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


        el.tabla.innerHTML = `
            <tr>
                <td
                    colspan="15"
                    class="avance-tabla-estado">

                    Consultando avance por periodo...

                </td>
            </tr>
        `;


        try {

            const respuesta =
                await window
                    .ReportesAPI
                    .obtenerAvancePeriodo(
                        obtenerParametros()
                    );


            estado.filas =
                Array.isArray(
                    respuesta
                )
                    ? respuesta
                    : [];


            estado.pagina =
                1;


            el.busqueda.value =
                "";


            renderTabla();


            if (
                estado.filas.length === 0
            ) {

                mostrarInfo(
                    "La consulta se ejecutó correctamente, pero no existen hitos periodizados para los filtros seleccionados."
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
                    LIMPIAR FILTROS
    ===================================================== */

    function limpiarFiltros() {

        el.form.reset();


        el.busqueda.value =
            "";


        estado.pagina =
            1;


        const anioActual =
            new Date()
                .getFullYear();


        el.anio.value =
            String(
                anioActual
            );

    }


    /* =====================================================
                    EXPORTACIÓN CSV LOCAL
    ===================================================== */

    function exportarCsv() {

        const filas =
            filasFiltradas();


        if (
            filas.length === 0
        ) {
            return;
        }


        const encabezados = [

            "id_proyecto",

            "proyecto",

            "id_entidad",

            "entidad",

            "ambito",

            "tipo_cop_operativo",

            "tipo_convenio",

            "destino_superficie",

            "anio",

            "mes",

            "trimestre",

            "indicador",

            "programado",

            "realizado",

            "cantidad",

            "superficie_ha",

            "monto"

        ];


        const lineas = [

            encabezados
                .map(
                    escaparCsv
                )
                .join(",")

        ];


        filas.forEach(
            fila => {

                const valores = [

                    fila.id_proyecto,

                    nombreProyecto(
                        fila.id_proyecto
                    ),

                    fila.id_entidad,

                    nombreEntidad(
                        fila.id_entidad
                    ),

                    fila.ambito,

                    fila.tipo_cop_operativo,

                    fila.tipo_convenio,

                    fila.destino_superficie,

                    fila.anio,

                    fila.mes,

                    fila.trimestre,

                    fila.indicador,

                    fila.programado,

                    fila.realizado,

                    fila.cantidad,

                    fila.superficie_ha,

                    fila.monto

                ];


                lineas.push(
                    valores
                        .map(
                            escaparCsv
                        )
                        .join(",")
                );

            }
        );


        const contenido =
            `\uFEFF${lineas.join(
                "\r\n"
            )}`;


        const blob =
            new Blob(
                [contenido],
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


        const fecha =
            new Date()
                .toISOString()
                .slice(
                    0,
                    10
                );


        enlace.href =
            url;


        enlace.download =
            `avance-periodo-${fecha}.csv`;


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
                        EVENTOS
    ===================================================== */

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

            const total =
                filasFiltradas()
                    .length;


            const totalPaginas =
                Math.max(
                    1,
                    Math.ceil(
                        total /
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
            await window
                .AuthAPI
                .requerirSesion();


        if (!sesion) {
            return;
        }


        limpiarFiltros();


        await cargarCatalogosBase();


        await consultarReporte();

    } catch (error) {

        mostrarError(
            error
        );

    }

});