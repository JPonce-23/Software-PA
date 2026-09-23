document.addEventListener("DOMContentLoaded", () => {

    "use strict";


    /* =====================================================
                        UTILIDADES
    ====================================================== */

    function escaparHTML(valor) {

        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function normalizarPorcentaje(valor) {

        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return null;
        }

        const numero = Number(valor);

        if (!Number.isFinite(numero)) {
            return null;
        }

        return Math.min(
            100,
            Math.max(0, numero)
        );
    }


    function textoPorcentaje(valor) {

        const porcentaje =
            normalizarPorcentaje(valor);

        if (porcentaje === null) {
            return "—";
        }

        const tieneDecimales =
            Math.abs(
                porcentaje -
                Math.round(porcentaje)
            ) > 0.001;

        return (
            porcentaje.toLocaleString(
                "es-MX",
                {
                    minimumFractionDigits: 0,
                    maximumFractionDigits:
                        tieneDecimales
                            ? 1
                            : 0
                }
            ) + "%"
        );
    }


    function crearGraficaDona(porcentaje) {

        const valor =
            normalizarPorcentaje(
                porcentaje
            );

        if (valor === null) {

            return `
                <div
                    class="
                        dashboard-dona
                        dashboard-dona-sin-dato
                    "
                    aria-label="Sin dato disponible"
                >
                    <span
                        class="dashboard-dona-valor"
                    >
                        —
                    </span>
                </div>
            `;
        }

        return `
            <div
                class="dashboard-dona"
                style="--porcentaje: ${valor}"
                role="img"
                aria-label="${textoPorcentaje(valor)} de avance"
            >
                <span
                    class="dashboard-dona-valor"
                >
                    ${textoPorcentaje(valor)}
                </span>
            </div>
        `;
    }


    function formatearEntero(valor) {

        const numero = Number(valor);

        if (!Number.isFinite(numero)) {
            return "—";
        }

        return numero.toLocaleString(
            "es-MX",
            { maximumFractionDigits: 0 }
        );
    }


    function formatearMoneda(valor) {

        const numero = Number(valor);

        if (!Number.isFinite(numero)) {
            return "—";
        }

        return numero.toLocaleString(
            "es-MX",
            {
                style: "currency",
                currency: "MXN",
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        );
    }


    function obtenerFilasKpiProyecto(
        kpis,
        idProyecto,
        indicador
    ) {

        return (Array.isArray(kpis) ? kpis : [])
            .filter(
                fila =>
                    Number(fila.id_proyecto) === Number(idProyecto) &&
                    fila.indicador === indicador
            );
    }


    function sumarCampoKpi(
        kpis,
        idProyecto,
        indicador,
        campo
    ) {

        const filas =
            obtenerFilasKpiProyecto(
                kpis,
                idProyecto,
                indicador
            );

        if (filas.length === 0) {
            return null;
        }

        return filas.reduce(
            (total, fila) => {

                const valor = Number(fila[campo]);

                return Number.isFinite(valor)
                    ? total + valor
                    : total;
            },
            0
        );
    }


    function porcentajeDeAvance(
        realizado,
        total
    ) {

        const numeroRealizado = Number(realizado);
        const numeroTotal = Number(total);

        if (
            !Number.isFinite(numeroRealizado) ||
            !Number.isFinite(numeroTotal) ||
            numeroTotal <= 0
        ) {
            return null;
        }

        return (
            numeroRealizado /
            numeroTotal
        ) * 100;
    }


    function resumirValorConvenio(
        valores,
        idProyecto,
        concepto
    ) {

        const filas =
            (Array.isArray(valores) ? valores : [])
                .filter(
                    fila =>
                        Number(fila.id_proyecto) === Number(idProyecto) &&
                        fila.concepto === concepto &&
                        Number.isFinite(Number(fila.valor_declarado))
                );

        if (filas.length === 0) {
            return {
                total: null,
                convenios: 0
            };
        }

        const idsConvenio = new Set();

        const total = filas.reduce(
            (acumulado, fila) => {

                idsConvenio.add(
                    Number(fila.id_convenio)
                );

                return acumulado +
                    Number(fila.valor_declarado);
            },
            0
        );

        return {
            total,
            convenios: idsConvenio.size
        };
    }


    function anchoBarraComparativa(
        valor,
        maximo
    ) {

        const numero = Number(valor);
        const referencia = Number(maximo);

        if (
            !Number.isFinite(numero) ||
            !Number.isFinite(referencia) ||
            referencia <= 0
        ) {
            return 0;
        }

        return Math.min(
            100,
            Math.max(
                0,
                (numero / referencia) * 100
            )
        );
    }





    /* =====================================================
        NAVEGACIÓN COMÚN DEL SIDEBAR
====================================================== */

function configurarMenuCuenta() {

    document
        .querySelectorAll(
            ".opciones-usuario"
        )
        .forEach(
            menu => {

                const enlaces =
                    Array.from(
                        menu.querySelectorAll(
                            "a"
                        )
                    );


                /* =========================================
                    CAMBIAR CONTRASEÑA
                ========================================== */

                let enlaceContrasena =
                    enlaces.find(
                        enlace =>
                            enlace.dataset.action ===
                                "cambiar-contrasena" ||
                            enlace
                                .textContent
                                .trim()
                                .toLowerCase()
                                .includes(
                                    "cambiar contraseña"
                                )
                    );


                if (!enlaceContrasena) {

                    enlaceContrasena =
                        document.createElement(
                            "a"
                        );


                    enlaceContrasena.innerHTML = `
                        <i class="bi bi-lock"></i>
                        Cambiar contraseña
                    `;


                    menu.appendChild(
                        enlaceContrasena
                    );

                }


                enlaceContrasena.href =
                    "/pages/cambiarContrasena.html";


                enlaceContrasena.dataset.action =
                    "cambiar-contrasena";



                /* =========================================
                    CERRAR SESIÓN
                ========================================== */

                let enlaceLogout =
                    enlaces.find(
                        enlace =>
                            enlace.dataset.action ===
                                "logout" ||
                            enlace
                                .textContent
                                .trim()
                                .toLowerCase()
                                .includes(
                                    "cerrar sesión"
                                )
                    );


                if (!enlaceLogout) {

                    enlaceLogout =
                        document.createElement(
                            "a"
                        );


                    enlaceLogout.innerHTML = `
                        <i class="bi bi-box-arrow-left"></i>
                        Cerrar sesión
                    `;


                    menu.appendChild(
                        enlaceLogout
                    );

                }


                enlaceLogout.href =
                    "#";


                enlaceLogout.dataset.action =
                    "logout";


                /*
                 * Las dos opciones deben quedar juntas.
                 */

                enlaceContrasena
                    .insertAdjacentElement(
                        "afterend",
                        enlaceLogout
                    );

            }
        );

}



/* =====================================================
            ACCESO AL MAPA
====================================================== */

function configurarAccesoMapa() {

    const ruta =
        window.location.pathname
            .toLowerCase()
            .replace(
                /\/$/,
                ""
            );


    const esDashboard =
        ruta.endsWith(
            "/dashboard.html"
        );


    const esFichaProyecto =
        ruta.endsWith(
            "/pages/fichaproyecto.html"
        );


    const esMapa =
        ruta.endsWith(
            "/pages/mapa.html"
        );


    const accesoPermitido =
        esDashboard ||
        esFichaProyecto ||
        esMapa;


    /*
     * Sólo actuamos sobre enlaces del sidebar.
     *
     * No ocultamos botones internos que puedan llamarse
     * de forma parecida.
     */

    document
        .querySelectorAll(
            ".barra a"
        )
        .forEach(
            enlace => {

                const texto =
                    enlace
                        .textContent
                        .trim()
                        .toLowerCase();


                const href =
                    (
                        enlace.getAttribute(
                            "href"
                        ) ||
                        ""
                    )
                        .toLowerCase();


                const esEnlaceMapa =
                    texto.includes(
                        "ver mapa"
                    ) ||
                    href.includes(
                        "/pages/mapa.html"
                    );


                if (!esEnlaceMapa) {

                    return;

                }


                /*
                 * En páginas internas:
                 *
                 * núcleo, parcela, ORV, unidades,
                 * afectaciones, convenios, personas, etc.
                 *
                 * no mostramos el acceso al mapa.
                 */

                if (!accesoPermitido) {

                    enlace.hidden =
                        true;


                    return;

                }


                enlace.hidden =
                    false;


                /*
                 * Desde la ficha del proyecto abrimos
                 * directamente ese proyecto en el mapa.
                 */

                if (esFichaProyecto) {

                    const parametros =
                        new URLSearchParams(
                            window.location.search
                        );


                    const idProyecto =
                        Number(
                            parametros.get(
                                "id"
                            )
                        );


                    enlace.href =
                        Number.isInteger(
                            idProyecto
                        ) &&
                        idProyecto > 0

                            ? (
                                `/pages/mapa.html?id_proyecto=${encodeURIComponent(
                                    idProyecto
                                )}`
                            )

                            : "/pages/mapa.html";


                    return;

                }


                /*
                 * Desde Dashboard entra sin proyecto
                 * seleccionado.
                 */

                enlace.href =
                    "/pages/mapa.html";

            }
        );

}



/* =====================================================
            CONFIGURACIÓN COMÚN
====================================================== */

configurarMenuCuenta();

configurarAccesoMapa();






    /* =====================================================
            SESIÓN REAL DEL USUARIO
    ====================================================== */

    (async () => {

        if (!window.AuthAPI) {
            return;
        }

        try {

            const sesion =
                await window.AuthAPI
                    .obtenerSesionActual();

            const usuario =
                sesion?.user;

            if (!usuario) {
                return;
            }


            const nombreCompleto =
                [
                    usuario.nombre,
                    usuario.apellido_paterno
                ]
                    .filter(Boolean)
                    .join(" ");


            document
                .querySelectorAll(
                    ".js-usuario-nombre"
                )
                .forEach(
                    elemento => {

                        elemento.textContent =
                            nombreCompleto ||
                            usuario.correo ||
                            "Usuario";
                    }
                );


            /*
             * Administración solo para admin.
             *
             * Los bloques correspondientes deben tener:
             * class="js-admin-only"
             * hidden
             */
            const esAdmin =
                usuario.rol === "admin";


            document
                .querySelectorAll(
                    ".js-admin-only"
                )
                .forEach(
                    elemento => {

                        elemento.hidden =
                            !esAdmin;
                    }
                );


        } catch (error) {

            /*
             * requerirSesion() se encarga
             * de redirigir cuando corresponda.
             */
        }

    })();



    /* =====================================================
            LISTA DE PROYECTOS DEL SIDEBAR
    ====================================================== */

    (async () => {

        const contenedor =
            document.getElementById(
                "proyectosLista"
            );

        if (
            !contenedor ||
            !window.ProyectosAPI
        ) {
            return;
        }


        try {

            const proyectos =
                await window.ProyectosAPI
                    .listar();


            const parametrosActuales =
                new URLSearchParams(
                    window.location.search
                );


            const rutaActual =
                window.location.pathname
                    .toLowerCase();


            let idProyectoActual =
                null;


            if (
                rutaActual.endsWith(
                    "fichaproyecto.html"
                )
            ) {

                idProyectoActual =
                    parametrosActuales.get(
                        "id"
                    );
            }


            contenedor.innerHTML = "";


            if (
                !Array.isArray(proyectos) ||
                proyectos.length === 0
            ) {

                const vacio =
                    document.createElement(
                        "p"
                    );

                vacio.className =
                    "proyectos-lista-vacia";

                vacio.textContent =
                    "No hay proyectos disponibles.";

                contenedor.appendChild(
                    vacio
                );

                return;
            }


            proyectos.forEach(
                proyecto => {

                    const enlace =
                        document.createElement(
                            "a"
                        );


                    enlace.href =
                        `/pages/fichaProyecto.html?id=${encodeURIComponent(
                            proyecto.id_proyecto
                        )}`;


                    if (
                        idProyectoActual &&
                        Number(
                            idProyectoActual
                        ) ===
                        Number(
                            proyecto.id_proyecto
                        )
                    ) {

                        enlace.classList.add(
                            "activo"
                        );
                    }


                    const icono =
                        document.createElement(
                            "i"
                        );

                    icono.className =
                        "bi bi-chevron-right";


                    const texto =
                        document.createElement(
                            "span"
                        );

                    texto.textContent =
                        proyecto.nombre_proyecto ||
                        `Proyecto ${proyecto.id_proyecto}`;


                    enlace.append(
                        icono,
                        texto
                    );


                    contenedor.appendChild(
                        enlace
                    );
                }
            );


        } catch (error) {

            window.ClienteAPI
                ?.mostrarErrorAPI?.(
                    error
                );
        }

    })();



    /* =====================================================
            DASHBOARD PRINCIPAL
    ====================================================== */

    (async () => {

        const listaProyectos =
            document.getElementById(
                "listaProyectosDashboard"
            );


        const contenedorError =
            document.getElementById(
                "dashboardMensajeError"
            );


        const botonExportarCsv =
            document.getElementById(
                "btnExportarDashboardCsv"
            );


        /*
         * Este bloque solo debe ejecutarse
         * realmente en dashboard.html.
         */
        if (!listaProyectos) {
            return;
        }


        if (!window.ProyectosAPI) {

            listaProyectos.innerHTML = `
                <p class="proyectos-lista-vacia">
                    No está disponible la API de proyectos.
                </p>
            `;

            return;
        }


        /*
         * El botón empieza deshabilitado
         * hasta confirmar ReportesAPI.
         */
        if (botonExportarCsv) {

            botonExportarCsv
                .removeAttribute(
                    "href"
                );

            botonExportarCsv
                .setAttribute(
                    "aria-disabled",
                    "true"
                );

            botonExportarCsv
                .classList.add(
                    "deshabilitado"
                );
        }


        try {

            /*
             * =============================
             * PROYECTOS
             * =============================
             */

            const proyectos =
                await window.ProyectosAPI
                    .listar();


            /*
             * =============================
             * KPI DEL DASHBOARD
             * =============================
             */

            let kpisDashboard = [];


            if (window.ReportesAPI) {

                try {

                    const respuestaKpi =
                        await window.ReportesAPI
                            .obtenerKpiDashboard();


                    kpisDashboard =
                        Array.isArray(
                            respuestaKpi
                        )
                            ? respuestaKpi
                            : [];


                } catch (error) {

                    /*
                     * Los proyectos pueden seguir
                     * mostrándose aunque falle KPI.
                     */
                    console.warn(
                        "No fue posible cargar los KPI del dashboard.",
                        error
                    );
                }
            }


            /*
             * =============================
             * VALORES DECLARADOS DE CONVENIOS
             * =============================
             *
             * Se usa el endpoint existente de reporting.
             * Los conceptos 90 % y 100 % son universos
             * paralelos y pueden tener distinta cobertura.
             */

            let valoresConveniosDeclarados = [];


            if (
                window.ReportesAPI &&
                typeof window.ReportesAPI
                    .obtenerConveniosValoresDeclarados === "function"
            ) {

                try {

                    const respuestaValores =
                        await window.ReportesAPI
                            .obtenerConveniosValoresDeclarados();


                    valoresConveniosDeclarados =
                        Array.isArray(respuestaValores)
                            ? respuestaValores
                            : [];


                } catch (error) {

                    console.warn(
                        "No fue posible cargar los valores declarados de convenios.",
                        error
                    );
                }
            }


            /*
             * =============================
             * CSV
             * =============================
             */

            if (
                botonExportarCsv &&
                window.ReportesAPI
            ) {

                botonExportarCsv.href =
                    window.ReportesAPI
                        .urlExportacionDashboardCsv();


                botonExportarCsv
                    .removeAttribute(
                        "aria-disabled"
                    );


                botonExportarCsv
                    .classList.remove(
                        "deshabilitado"
                    );
            }


            /*
             * =============================
             * LISTA VACÍA
             * =============================
             */

            listaProyectos.innerHTML =
                "";


            if (
                !Array.isArray(proyectos) ||
                proyectos.length === 0
            ) {

                const vacio =
                    document.createElement(
                        "p"
                    );


                vacio.className =
                    "proyectos-lista-vacia";


                vacio.textContent =
                    "No hay proyectos disponibles todavía. Usa \"Nuevo proyecto\" en el menú para crear el primero.";


                listaProyectos.appendChild(
                    vacio
                );

                return;
            }


            /*
             * =============================
             * TARJETAS POR PROYECTO
             * =============================
             */

            for (
                const proyecto
                of proyectos
            ) {

                let nucleos = [];


                if (window.NucleosAPI) {

                    try {

                        nucleos =
                            await window
                                .NucleosAPI
                                .listarPorProyecto(
                                    proyecto.id_proyecto
                                );


                    } catch (error) {

                        /*
                         * No bloqueamos todo el
                         * dashboard por un proyecto.
                         */
                        nucleos = [];
                    }
                }


                const listaNucleos =
                    Array.isArray(nucleos)
                        ? nucleos
                        : [];


                const totalAsambleasAnuencia =
                    sumarCampoKpi(
                        kpisDashboard,
                        proyecto.id_proyecto,
                        "asambleas",
                        "programado"
                    );


                const asambleasCelebradas =
                    sumarCampoKpi(
                        kpisDashboard,
                        proyecto.id_proyecto,
                        "asambleas",
                        "realizado"
                    );


                const copsFormalizados =
                    sumarCampoKpi(
                        kpisDashboard,
                        proyecto.id_proyecto,
                        "cop_colectivos",
                        "realizado"
                    );


                const porcentajeAsambleas =
                    porcentajeDeAvance(
                        asambleasCelebradas,
                        totalAsambleasAnuencia
                    );


                const monto90 =
                    resumirValorConvenio(
                        valoresConveniosDeclarados,
                        proyecto.id_proyecto,
                        "monto_90_declarado"
                    );


                const monto100 =
                    resumirValorConvenio(
                        valoresConveniosDeclarados,
                        proyecto.id_proyecto,
                        "monto_100_declarado"
                    );


                const maximoMonto = Math.max(
                    Number(monto90.total) || 0,
                    Number(monto100.total) || 0
                );


                const anchoMonto90 =
                    anchoBarraComparativa(
                        monto90.total,
                        maximoMonto
                    );


                const anchoMonto100 =
                    anchoBarraComparativa(
                        monto100.total,
                        maximoMonto
                    );


                const articulo =
                    document.createElement(
                        "article"
                    );


                articulo.className =
                    "tarjeta tarjeta-dashboard-ejecutivo";


                const nombreProyecto =
                    escaparHTML(
                        proyecto.nombre_proyecto ||
                        `Proyecto ${proyecto.id_proyecto}`
                    );


                const claveProyecto =
                    escaparHTML(
                        proyecto.clave_proyecto ||
                        "Sin clave"
                    );


                const detalleMonto90 =
                    monto90.total === null
                        ? "Sin dato disponible"
                        : `${formatearEntero(monto90.convenios)} convenios con dato`;


                const detalleMonto100 =
                    monto100.total === null
                        ? "Sin dato disponible"
                        : `${formatearEntero(monto100.convenios)} convenios con dato`;


                articulo.innerHTML = `

                    <a
                        href="/pages/fichaProyecto.html?id=${encodeURIComponent(
                            proyecto.id_proyecto
                        )}"
                        aria-label="Abrir ficha del proyecto ${nombreProyecto}"
                    >

                        <div
                            class="dashboard-proyecto-cabecera dashboard-proyecto-cabecera-ejecutiva"
                        >

                            <div>

                                <h3>
                                    ${nombreProyecto}
                                </h3>

                                <p
                                    class="dashboard-proyecto-clave"
                                >
                                    ${claveProyecto}
                                </p>

                            </div>

                            <span
                                class="dashboard-resumen-etiqueta"
                            >
                                Resumen general
                            </span>

                        </div>


                        <section
                            class="dashboard-kpis-principales"
                            aria-label="Indicadores principales del proyecto"
                        >

                            <div
                                class="dashboard-kpi-ejecutivo"
                            >

                                <span
                                    class="dashboard-kpi-icono"
                                    aria-hidden="true"
                                >
                                    <i class="bi bi-geo-alt-fill"></i>
                                </span>

                                <div>

                                    <span
                                        class="dashboard-kpi-etiqueta"
                                    >
                                        Núcleos agrarios
                                    </span>

                                    <strong
                                        class="dashboard-kpi-valor"
                                    >
                                        ${formatearEntero(listaNucleos.length)}
                                    </strong>

                                    <small>
                                        Vinculados al proyecto
                                    </small>

                                </div>

                            </div>


                            <div
                                class="dashboard-kpi-ejecutivo"
                            >

                                <span
                                    class="dashboard-kpi-icono"
                                    aria-hidden="true"
                                >
                                    <i class="bi bi-people-fill"></i>
                                </span>

                                <div>

                                    <span
                                        class="dashboard-kpi-etiqueta"
                                    >
                                        Asambleas de anuencia
                                    </span>

                                    <strong
                                        class="dashboard-kpi-valor"
                                    >
                                        ${formatearEntero(totalAsambleasAnuencia)}
                                    </strong>

                                    <small>
                                        ${formatearEntero(asambleasCelebradas)} celebradas
                                    </small>

                                </div>

                            </div>


                            <div
                                class="dashboard-kpi-ejecutivo"
                            >

                                <span
                                    class="dashboard-kpi-icono"
                                    aria-hidden="true"
                                >
                                    <i class="bi bi-file-earmark-check-fill"></i>
                                </span>

                                <div>

                                    <span
                                        class="dashboard-kpi-etiqueta"
                                    >
                                        COPs formalizados
                                    </span>

                                    <strong
                                        class="dashboard-kpi-valor"
                                    >
                                        ${formatearEntero(copsFormalizados)}
                                    </strong>

                                    <small>
                                        Con fecha de firma registrada
                                    </small>

                                </div>

                            </div>

                        </section>


                        <section
                            class="dashboard-graficas-grid"
                            aria-label="Gráficas del resumen del proyecto"
                        >

                            <div
                                class="dashboard-panel-grafica dashboard-panel-asambleas"
                            >

                                <div
                                    class="dashboard-panel-encabezado"
                                >

                                    <div>
                                        <h4>
                                            Asambleas de anuencia
                                        </h4>

                                        <p>
                                            Celebradas / registradas
                                        </p>
                                    </div>

                                </div>

                                <div
                                    class="dashboard-asambleas-grafica"
                                >

                                    ${crearGraficaDona(
                                        porcentajeAsambleas
                                    )}

                                    <div
                                        class="dashboard-asambleas-detalle"
                                    >

                                        <strong>
                                            ${formatearEntero(asambleasCelebradas)} de ${formatearEntero(totalAsambleasAnuencia)}
                                        </strong>

                                        <span>
                                            asambleas celebradas
                                        </span>


                                    </div>

                                </div>

                            </div>


                            <div
                                class="dashboard-panel-grafica dashboard-panel-montos"
                            >

                                <div
                                    class="dashboard-panel-encabezado"
                                >

                                    <div>
                                        <h4>
                                            Convenios — montos declarados
                                        </h4>

                                        <p>
                                            90 % vs 100 %
                                        </p>
                                    </div>

                                </div>


                                <div
                                    class="dashboard-monto-fila"
                                >

                                    <div
                                        class="dashboard-monto-encabezado"
                                    >
                                        <span>
                                            Convenio monto 90 %
                                        </span>

                                        <strong>
                                            ${formatearMoneda(monto90.total)}
                                        </strong>
                                    </div>

                                    <div
                                        class="dashboard-monto-barra"
                                        role="img"
                                        aria-label="Monto 90 por ciento: ${escaparHTML(formatearMoneda(monto90.total))}"
                                    >
                                        <span
                                            class="dashboard-monto-relleno dashboard-monto-relleno-90"
                                            style="--ancho-barra: ${anchoMonto90}%"
                                        ></span>
                                    </div>

                                    <small>
                                        ${escaparHTML(detalleMonto90)}
                                    </small>

                                </div>


                                <div
                                    class="dashboard-monto-fila"
                                >

                                    <div
                                        class="dashboard-monto-encabezado"
                                    >
                                        <span>
                                            Convenio monto 100 %
                                        </span>

                                        <strong>
                                            ${formatearMoneda(monto100.total)}
                                        </strong>
                                    </div>

                                    <div
                                        class="dashboard-monto-barra"
                                        role="img"
                                        aria-label="Monto 100 por ciento: ${escaparHTML(formatearMoneda(monto100.total))}"
                                    >
                                        <span
                                            class="dashboard-monto-relleno dashboard-monto-relleno-100"
                                            style="--ancho-barra: ${anchoMonto100}%"
                                        ></span>
                                    </div>

                                    <small>
                                        ${escaparHTML(detalleMonto100)}
                                    </small>

                                </div>


                                <p
                                    class="dashboard-montos-nota"
                                >
                                    Cobertura distinta por concepto; consulte el número de convenios bajo cada barra.
                                </p>

                            </div>

                        </section>

                    </a>
                `;


                listaProyectos.appendChild(
                    articulo
                );
            }


        } catch (error) {

            listaProyectos.innerHTML = `
                <p class="proyectos-lista-vacia">
                    No fue posible cargar los proyectos.
                </p>
            `;


            window.ClienteAPI
                ?.mostrarErrorAPI?.(
                    error,
                    contenedorError
                );
        }

    })();



    /* =====================================================
                        SIDEBAR
    ====================================================== */

    const botonMenu =
        document.querySelector(
            ".btn-menu"
        );


    const aside =
        document.querySelector(
            ".aside"
        );


    if (
        botonMenu &&
        aside
    ) {

        const sidebarColapsado =
            localStorage.getItem(
                "sidebarColapsado"
            ) === "true";


        if (sidebarColapsado) {

            aside.classList.add(
                "collapsed"
            );
        }


        botonMenu.addEventListener(
            "click",
            () => {

                aside.classList.toggle(
                    "collapsed"
                );


                const estaColapsado =
                    aside.classList.contains(
                        "collapsed"
                    );


                localStorage.setItem(
                    "sidebarColapsado",
                    String(
                        estaColapsado
                    )
                );
            }
        );
    }



    /* =====================================================
                    MENÚ DEL USUARIO
    ====================================================== */

    const usuarioBtn =
        document.querySelector(
            ".usuario-btn"
        );


    const opcionesUsuario =
        document.querySelector(
            ".opciones-usuario"
        );


    if (
        usuarioBtn &&
        opcionesUsuario
    ) {

        usuarioBtn.addEventListener(
            "click",
            evento => {

                evento.stopPropagation();


                opcionesUsuario
                    .classList
                    .toggle(
                        "mostrar"
                    );
            }
        );


        /*
         * Evitar que un click dentro
         * cierre inmediatamente el menú.
         */
        opcionesUsuario.addEventListener(
            "click",
            evento => {

                const enlace = evento.target.closest("a");

                if (!enlace) {
                    evento.stopPropagation();
                }

            }
        );


        /*
         * Cerrar al hacer click fuera.
         */
        document.addEventListener(
            "click",
            () => {

                opcionesUsuario
                    .classList
                    .remove(
                        "mostrar"
                    );
            }
        );


        /*
         * Cerrar con Escape.
         */
        document.addEventListener(
            "keydown",
            evento => {

                if (
                    evento.key ===
                    "Escape"
                ) {

                    opcionesUsuario
                        .classList
                        .remove(
                            "mostrar"
                        );
                }
            }
        );
    }



    /* =====================================================
                    PÁGINA ACTIVA
    ====================================================== */

    const enlacesMenu =
        document.querySelectorAll(
            ".barra a"
        );


    const rutaActual =
        window.location.pathname
            .toLowerCase()
            .replace(
                /\/$/,
                ""
            );


    enlacesMenu.forEach(
        enlace => {

            const href =
                enlace.getAttribute(
                    "href"
                );


            if (
                !href ||
                href === "#"
            ) {
                return;
            }


            const urlEnlace =
                new URL(
                    href,
                    window.location.origin
                );


            const rutaEnlace =
                urlEnlace.pathname
                    .toLowerCase()
                    .replace(
                        /\/$/,
                        ""
                    );


            if (
                rutaActual ===
                rutaEnlace
            ) {

                enlace.classList.add(
                    "activo"
                );
            }
        }
    );



    /* =====================================================
        CERRAR SIDEBAR EN PANTALLAS PEQUEÑAS
    ====================================================== */

    const enlacesNavegacion =
        document.querySelectorAll(
            ".barra a"
        );


    enlacesNavegacion.forEach(
        enlace => {

            enlace.addEventListener(
                "click",
                () => {

                    if (
                        window.innerWidth <=
                            1000 &&
                        aside
                    ) {

                        aside.classList.add(
                            "collapsed"
                        );


                        localStorage.setItem(
                            "sidebarColapsado",
                            "true"
                        );
                    }
                }
            );
        }
    );



    /* =====================================================
    EASTER EGG — 2026
    ===================================================== */

    const easterEgg2026 =
        document.getElementById("easterEgg2026");

    const easterEggTren =
        document.getElementById("easterEggTren");

    const easterEggContador = (() => {

        if (!easterEgg2026) {
            return null;
        }

        const contador =
            document.createElement("span");

        contador.className =
            "easter-egg-contador";

        contador.hidden = true;

        contador.setAttribute(
            "aria-live",
            "polite"
        );

        contador.setAttribute(
            "aria-label",
            "Contador secreto"
        );

        easterEgg2026.insertAdjacentElement(
            "afterend",
            contador
        );

        return contador;
    })();

    let clicsEasterEgg = 0;

    let temporizadorEasterEgg = null;

    let easterEggActivo = false;

    function mostrarContadorEasterEgg() {

        if (!easterEggContador) {
            return;
        }

        easterEggContador.textContent =
            String(clicsEasterEgg);

        easterEggContador.hidden = false;

        easterEggContador.classList.remove(
            "pulso"
        );

        void easterEggContador.offsetWidth;

        easterEggContador.classList.add(
            "pulso"
        );
    }

    function ocultarContadorEasterEgg() {

        if (!easterEggContador) {
            return;
        }

        easterEggContador.hidden = true;
        easterEggContador.textContent = "";
        easterEggContador.classList.remove(
            "pulso"
        );
    }

    function reiniciarContadorEasterEgg(
        ocultarContador = true
    ) {

        clicsEasterEgg = 0;

        if (ocultarContador) {
            ocultarContadorEasterEgg();
        }

        if (temporizadorEasterEgg) {

            clearTimeout(
                temporizadorEasterEgg
            );

            temporizadorEasterEgg = null;
        }
    }

    function activarEasterEgg() {

        if (
            !easterEggTren ||
            easterEggActivo
        ) {
            return;
        }

        easterEggActivo = true;

        /*
         * Conservamos el 8 visible un instante
         * mientras inicia la animación del tren.
         */
        reiniciarContadorEasterEgg(false);

        window.setTimeout(
            ocultarContadorEasterEgg,
            650
        );

        /*
        * Quitamos la clase primero para permitir
        * que la animación pueda ejecutarse nuevamente
        * si el usuario descubre el huevo otra vez.
        */
        easterEggTren.classList.remove(
            "activo"
        );

        void easterEggTren.offsetWidth;

        easterEggTren.classList.add(
            "activo"
        );

        easterEggTren.setAttribute(
            "aria-hidden",
            "false"
        );

        window.setTimeout(
            () => {

                easterEggTren.classList.remove(
                    "activo"
                );

                easterEggTren.setAttribute(
                    "aria-hidden",
                    "true"
                );

                easterEggActivo = false;

            },
            9200
        );
    }

    easterEgg2026?.addEventListener(
        "click",
        () => {

            if (easterEggActivo) {
                return;
            }

            clicsEasterEgg += 1;

            mostrarContadorEasterEgg();

            /*
            * Si pasan 3 segundos sin otro clic,
            * la secuencia vuelve a comenzar.
            */
            if (temporizadorEasterEgg) {

                clearTimeout(
                    temporizadorEasterEgg
                );
            }

            temporizadorEasterEgg =
                window.setTimeout(
                    reiniciarContadorEasterEgg,
                    3000
                );

            if (clicsEasterEgg >= 8) {

                activarEasterEgg();
            }
        }
    );

});