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


    /*
     * Calcula un avance general usando las metas
     * programadas y realizadas del año más reciente.
     *
     * Si no existen metas programadas, devuelve null
     * para mostrar "—" y no inventar un 0 %.
     */
    function calcularAvanceProyecto(
        kpis,
        idProyecto
    ) {

        const filasProyecto =
            (Array.isArray(kpis) ? kpis : [])
                .filter(
                    fila =>
                        Number(
                            fila.id_proyecto
                        ) ===
                        Number(idProyecto)
                );

        if (
            filasProyecto.length === 0
        ) {
            return null;
        }


        const anios =
            filasProyecto
                .map(
                    fila =>
                        Number(fila.anio)
                )
                .filter(
                    Number.isFinite
                );


        const ultimoAnio =
            anios.length
                ? Math.max(...anios)
                : null;


        const filasPeriodo =
            ultimoAnio === null
                ? filasProyecto
                : filasProyecto.filter(
                    fila =>
                        Number(
                            fila.anio
                        ) ===
                        ultimoAnio
                );


        const filasConMeta =
            filasPeriodo.filter(
                fila => {

                    const programado =
                        Number(
                            fila.programado
                        );

                    const realizado =
                        Number(
                            fila.realizado
                        );

                    return (
                        Number.isFinite(
                            programado
                        ) &&
                        programado > 0 &&
                        Number.isFinite(
                            realizado
                        )
                    );
                }
            );


        if (
            filasConMeta.length === 0
        ) {
            return null;
        }


        const totalProgramado =
            filasConMeta.reduce(
                (total, fila) =>
                    total +
                    Number(
                        fila.programado
                    ),
                0
            );


        const totalRealizado =
            filasConMeta.reduce(
                (total, fila) =>
                    total +
                    Number(
                        fila.realizado
                    ),
                0
            );


        if (
            totalProgramado <= 0
        ) {
            return null;
        }


        return (
            totalRealizado /
            totalProgramado
        ) * 100;
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


                const totalParcelas =
                    listaNucleos.reduce(
                        (total, nucleo) =>
                            total +
                            Number(
                                nucleo.total_parcelas ||
                                0
                            ),
                        0
                    );


                const totalAfectaciones =
                    listaNucleos.reduce(
                        (total, nucleo) =>
                            total +
                            Number(
                                nucleo.total_afectaciones ||
                                0
                            ),
                        0
                    );


                const superficieAfectada =
                    listaNucleos.reduce(
                        (total, nucleo) =>
                            total +
                            Number(
                                nucleo.superficie_afectada_ha ||
                                0
                            ),
                        0
                    );


                const avanceProyecto =
                    calcularAvanceProyecto(
                        kpisDashboard,
                        proyecto.id_proyecto
                    );


                const articulo =
                    document.createElement(
                        "article"
                    );


                articulo.className =
                    "tarjeta";


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


                articulo.innerHTML = `

                    <a
                        href="/pages/fichaProyecto.html?id=${encodeURIComponent(
                            proyecto.id_proyecto
                        )}"
                    >

                        <div
                            class="dashboard-proyecto-cabecera"
                        >

                            <div>

                                <h3>
                                    ${nombreProyecto}
                                </h3>

                                <p
                                    class="
                                        dashboard-proyecto-clave
                                    "
                                >
                                    ${claveProyecto}
                                </p>

                            </div>


                            <div
                                class="dashboard-avance"
                            >

                                ${crearGraficaDona(
                                    avanceProyecto
                                )}

                                <small>
                                    Avance del proyecto
                                </small>

                            </div>

                        </div>


                        <section
                            class="resumen"
                        >

                            <div>

                                <strong>
                                    Núcleos vinculados
                                </strong>

                                <p>
                                    ${listaNucleos.length}
                                </p>

                            </div>


                            <div>

                                <strong>
                                    Parcelas registradas
                                </strong>

                                <p>
                                    ${totalParcelas}
                                </p>

                            </div>


                            <div>

                                <strong>
                                    Afectaciones
                                </strong>

                                <p>
                                    ${totalAfectaciones}
                                </p>

                            </div>


                            <div>

                                <strong>
                                    Superficie afectada
                                </strong>

                                <p>
                                    ${superficieAfectada.toFixed(2)}
                                    ha
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

    let clicsEasterEgg = 0;

    let temporizadorEasterEgg = null;

    let easterEggActivo = false;

    function reiniciarContadorEasterEgg() {

        clicsEasterEgg = 0;

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

        reiniciarContadorEasterEgg();

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