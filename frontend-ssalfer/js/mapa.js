/**
 * mapa.js — Visor geográfico por proyecto de SSALFER
 * ---------------------------------------------------------------------------
 * Consume exclusivamente datos reales del backend:
 *
 *   GET /proyectos
 *   GET /proyectos/{id_proyecto}/mapa
 *   GET /proyectos/{id_proyecto}/nucleos
 *   GET /proyecto-nucleo/{id_proyecto_nucleo}/parcelas
 *   GET /parcelas/{id_parcela}
 *   GET /parcelas/{id_parcela}/titulares
 *
 * El visor muestra un solo proyecto a la vez.
 *
 * Al cambiar de proyecto:
 *   1. Se limpia completamente el mapa anterior.
 *   2. Se carga únicamente el proyecto seleccionado.
 *   3. Se muestran sus geometrías vigentes.
 *
 * La superficie afectada mostrada proviene de
 * superficie_afectada_ha del backend.
 *
 * NO se calcula superficie administrativa desde PostGIS.
 * NO se muestra porcentaje de participación de titulares.
 * ---------------------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {

    "use strict";


    /* =====================================================
       ELEMENTOS
    ====================================================== */

    const elementos = {

        titulo:
            document.getElementById("tituloMapa"),

        descripcion:
            document.getElementById("descripcionMapa"),

        selectorProyecto:
            document.getElementById("selectorProyectoMapa"),


        mensajeError:
            document.getElementById("mapaMensajeError"),

        mensajeInformativo:
            document.getElementById("mapaMensajeInformativo"),


        contextoProyecto:
            document.getElementById("mapaContextoProyecto"),

        contextoNombreProyecto:
            document.getElementById("mapaContextoNombreProyecto"),

        enlaceFichaProyecto:
            document.getElementById("enlaceFichaProyectoMapa"),

        enlaceGestionGeoespacial:
            document.getElementById(
                "enlaceGestionGeoespacialMapa"
            ),


        estadoCarga:
            document.getElementById("mapaEstadoCarga"),

        mapa:
            document.getElementById("mapa"),


        capaTrazos:
            document.getElementById("capaTrazos"),

        capaNucleos:
            document.getElementById("capaNucleos"),

        capaParcelas:
            document.getElementById("capaParcelas"),


        detalleVacio:
            document.getElementById("mapaDetalleVacio"),

        detalleContenido:
            document.getElementById("mapaDetalleContenido"),

        detalleTipo:
            document.getElementById("mapaDetalleTipo"),

        detalleNombre:
            document.getElementById("mapaDetalleNombre"),

        detalleDatos:
            document.getElementById("mapaDetalleDatos"),

        detalleEnlace:
            document.getElementById(
                "mapaDetalleEnlacePrincipal"
            ),

        detalleTitulares:
            document.getElementById(
                "mapaDetalleTitulares"
            ),

        detalleListaTitulares:
            document.getElementById(
                "mapaDetalleListaTitulares"
            ),


        resumenProyecto:
            document.getElementById(
                "mapaResumenProyecto"
            ),

        tituloResumenProyecto:
            document.getElementById(
                "tituloResumenProyecto"
            ),

        resumenSuperficie:
            document.getElementById(
                "resumenSuperficieAfectada"
            ),

        valorSuperficie:
            document.getElementById(
                "valorSuperficieAfectada"
            ),

        resumenNucleos:
            document.getElementById(
                "resumenNucleos"
            ),

        valorNucleos:
            document.getElementById(
                "valorNucleos"
            ),

        resumenParcelas:
            document.getElementById(
                "resumenParcelas"
            ),

        valorParcelas:
            document.getElementById(
                "valorParcelas"
            ),

        resumenAfectaciones:
            document.getElementById(
                "resumenAfectaciones"
            ),

        valorAfectaciones:
            document.getElementById(
                "valorAfectaciones"
            )

    };


    /* =====================================================
       CONSTANTES
    ====================================================== */

    const VISTA_INICIAL = {

        centro: [
            23.6345,
            -102.5528
        ],

        zoom: 5

    };


    /*
     * Estilos normales.
     */

    const ESTILOS = {

        trazo_proyecto: {

            color: "#7a1f35",

            weight: 5,

            opacity: 0.9

        },


        nucleo_agrario: {

            color: "#286B30",

            weight: 2,

            opacity: 0.9,

            fillColor: "#5f9f68",

            fillOpacity: 0.20

        },


        parcela: {

            color: "#a46a17",

            weight: 1.5,

            opacity: 0.9,

            fillColor: "#d7a24b",

            fillOpacity: 0.25

        }

    };


    /*
     * Estilos para geometrías seleccionadas.
     */

    const ESTILOS_SELECCION = {

        trazo_proyecto: {

            color: "#7a1f35",

            weight: 7,

            opacity: 1

        },


        nucleo_agrario: {

            color: "#174d20",

            weight: 4,

            opacity: 1,

            fillColor: "#5f9f68",

            fillOpacity: 0.38

        },


        parcela: {

            color: "#7a4b08",

            weight: 3,

            opacity: 1,

            fillColor: "#d7a24b",

            fillOpacity: 0.48

        }

    };


    /* =====================================================
       ESTADO
    ====================================================== */

    let mapaLeaflet = null;

    let proyectos = [];

    let idProyectoActivo = null;

    let tokenCarga = 0;


    /*
     * Proyecto por ID.
     */

    const proyectoPorId =
        new Map();


    /*
     * Cachés para evitar repetir llamadas cuando el usuario
     * selecciona varias veces la misma geometría.
     */

    const nucleosProyectoCache =
        new Map();

    const parcelasNucleoCache =
        new Map();

    const titularesParcelaCache =
        new Map();


    /*
     * Grupos Leaflet.
     */

    const grupos = {

        trazo_proyecto:
            null,

        nucleo_agrario:
            null,

        parcela:
            null

    };


    /*
     * Relación:
     *
     * tipo → ID → capas Leaflet
     *
     * Se utiliza para resaltar un núcleo y sus parcelas.
     */

    const capasPorTipoId = {

        trazo_proyecto:
            new Map(),

        nucleo_agrario:
            new Map(),

        parcela:
            new Map()

    };


    /* =====================================================
       VALIDACIÓN INICIAL
    ====================================================== */

    if (!elementos.mapa) {

        return;

    }


    if (!window.L) {

        mostrarError(
            "No fue posible iniciar el mapa porque Leaflet no está disponible."
        );

        ocultarCarga();

        return;

    }


    if (!window.ClienteAPI) {

        mostrarError(
            "No está disponible el cliente necesario para consultar el backend."
        );

        ocultarCarga();

        return;

    }


    /* =====================================================
       UTILIDADES
    ====================================================== */

    function valorPresente(valor) {

        return !(
            valor === null ||
            valor === undefined ||
            valor === ""
        );

    }


    function numeroSeguro(valor) {

        if (!valorPresente(valor)) {

            return null;

        }


        const numero =
            Number(valor);


        return Number.isFinite(numero)
            ? numero
            : null;

    }


    function formatearNumero(
        valor,
        maxDecimales = 2
    ) {

        const numero =
            numeroSeguro(valor);


        if (numero === null) {

            return "—";

        }


        return numero.toLocaleString(
            "es-MX",
            {
                minimumFractionDigits: 0,
                maximumFractionDigits:
                    maxDecimales
            }
        );

    }


    function formatearHectareas(valor) {

        const numero =
            numeroSeguro(valor);


        if (numero === null) {

            return "—";

        }


        return (
            `${formatearNumero(
                numero,
                4
            )} ha`
        );

    }


    function formatearFecha(valor) {

        if (!valorPresente(valor)) {

            return "—";

        }


        const partes =
            String(valor)
                .substring(0, 10)
                .split("-");


        if (partes.length === 3) {

            const [
                anio,
                mes,
                dia
            ] = partes.map(Number);


            const fecha =
                new Date(
                    anio,
                    mes - 1,
                    dia
                );


            if (
                !Number.isNaN(
                    fecha.getTime()
                )
            ) {

                return fecha.toLocaleDateString(
                    "es-MX",
                    {
                        year: "numeric",
                        month: "short",
                        day: "2-digit"
                    }
                );

            }

        }


        return String(valor);

    }


    function textoTipoParcela(valor) {

        const textos = {

            individual:
                "Individual",

            copropiedad:
                "Copropiedad",

            otro:
                "Otro",

            no_determinado:
                "No determinado"

        };


        return (
            textos[valor] ||
            valor ||
            "—"
        );

    }


    function tipoLegible(tipo) {

        const textos = {

            trazo_proyecto:
                "Trazo del proyecto",

            nucleo_agrario:
                "Núcleo agrario",

            parcela:
                "Parcela"

        };


        return (
            textos[tipo] ||
            "Elemento geográfico"
        );

    }


    function obtenerIdProyectoUrl() {

        const parametros =
            new URLSearchParams(
                window.location.search
            );


        const valor =
            parametros.get(
                "id_proyecto"
            );


        if (!valor) {

            return null;

        }


        const id =
            Number(valor);


        return (
            Number.isInteger(id) &&
            id > 0
        )
            ? id
            : null;

    }


    function actualizarUrl(idProyecto) {

        const url =
            new URL(
                window.location.href
            );


        if (idProyecto) {

            url.searchParams.set(
                "id_proyecto",
                String(idProyecto)
            );

        } else {

            url.searchParams.delete(
                "id_proyecto"
            );

        }


        window.history.replaceState(
            {},
            "",
            url
        );

    }


    function nombreProyecto(proyecto) {

        if (!proyecto) {

            return "Proyecto";

        }


        return (
            proyecto.nombre_proyecto ||
            proyecto.clave_proyecto ||
            `Proyecto ${proyecto.id_proyecto}`
        );

    }


    function obtenerProyecto(idProyecto) {

        return (
            proyectoPorId.get(
                Number(idProyecto)
            ) ||
            null
        );

    }


    /*
     * Permite soportar tanto respuestas array como respuestas
     * envueltas por el backend.
     */

    function extraerLista(
        respuesta,
        claves = []
    ) {

        if (
            Array.isArray(
                respuesta
            )
        ) {

            return respuesta;

        }


        for (
            const clave
            of claves
        ) {

            if (
                Array.isArray(
                    respuesta?.[clave]
                )
            ) {

                return respuesta[clave];

            }

        }


        return [];

    }


    /*
     * Genera el resumen administrativo usando los datos
     * proyecto-núcleo.
     *
     * No utiliza geometría para calcular superficies.
     */

    function resumenDesdeNucleos(
        nucleos
    ) {

        const lista =
            Array.isArray(nucleos)
                ? nucleos
                : [];


        const superficie =
            lista.reduce(
                (
                    total,
                    nucleo
                ) =>
                    total +
                    Number(
                        nucleo
                            .superficie_afectada_ha ||
                        0
                    ),
                0
            );


        const parcelas =
            lista.reduce(
                (
                    total,
                    nucleo
                ) =>
                    total +
                    Number(
                        nucleo
                            .total_parcelas ||
                        0
                    ),
                0
            );


        const afectaciones =
            lista.reduce(
                (
                    total,
                    nucleo
                ) =>
                    total +
                    Number(
                        nucleo
                            .total_afectaciones ||
                        0
                    ),
                0
            );


        return {

            superficie,

            nucleos:
                lista.length,

            parcelas,

            afectaciones

        };

    }


    /* =====================================================
       MENSAJES
    ====================================================== */

    function limpiarMensajes() {

        if (
            elementos.mensajeError
        ) {

            elementos.mensajeError.textContent =
                "";

            elementos.mensajeError.hidden =
                true;

        }


        if (
            elementos.mensajeInformativo
        ) {

            elementos
                .mensajeInformativo
                .textContent =
                "";

            elementos
                .mensajeInformativo
                .hidden =
                true;

        }

    }


    function mostrarError(mensaje) {

        if (
            !elementos.mensajeError
        ) {

            return;

        }


        elementos.mensajeError.textContent =
            mensaje;


        elementos.mensajeError.hidden =
            false;

    }


    function mostrarInformativo(mensaje) {

        if (
            !elementos.mensajeInformativo
        ) {

            return;

        }


        elementos
            .mensajeInformativo
            .textContent =
            mensaje;


        elementos
            .mensajeInformativo
            .hidden =
            false;

    }


    /* =====================================================
       ESTADO DEL MAPA
    ====================================================== */

    function mostrarCarga(
        texto =
            "Cargando información geográfica…"
    ) {

        if (
            !elementos.estadoCarga
        ) {

            return;

        }


        const icono =
            elementos
                .estadoCarga
                .querySelector("i");


        const span =
            elementos
                .estadoCarga
                .querySelector("span");


        if (icono) {

            icono.className =
                "bi bi-arrow-repeat";

        }


        if (span) {

            span.textContent =
                texto;

        }


        elementos.estadoCarga.hidden =
            false;

    }


    function mostrarEstadoInicial() {

        if (
            !elementos.estadoCarga
        ) {

            return;

        }


        const icono =
            elementos
                .estadoCarga
                .querySelector("i");


        const span =
            elementos
                .estadoCarga
                .querySelector("span");


        if (icono) {

            icono.className =
                "bi bi-map";

        }


        if (span) {

            span.textContent =
                "Selecciona un proyecto para consultar su información geográfica.";

        }


        elementos.estadoCarga.hidden =
            false;

    }


    function ocultarCarga() {

        if (
            elementos.estadoCarga
        ) {

            elementos.estadoCarga.hidden =
                true;

        }

    }


    /* =====================================================
       DETALLE
    ====================================================== */

    function limpiarTitularesDetalle() {

        if (
            elementos.detalleListaTitulares
        ) {

            elementos
                .detalleListaTitulares
                .innerHTML =
                "";

        }


        if (
            elementos.detalleTitulares
        ) {

            elementos
                .detalleTitulares
                .hidden =
                true;

        }

    }


    function agregarDatoDetalle(
        etiqueta,
        valor
    ) {

        if (
            !elementos.detalleDatos ||
            !valorPresente(valor)
        ) {

            return;

        }


        const fila =
            document.createElement(
                "div"
            );


        const dt =
            document.createElement(
                "dt"
            );


        const dd =
            document.createElement(
                "dd"
            );


        dt.textContent =
            etiqueta;


        dd.textContent =
            String(valor);


        fila.append(
            dt,
            dd
        );


        elementos.detalleDatos
            .appendChild(
                fila
            );

    }


    function prepararDetalle(
        tipo,
        nombre
    ) {

        if (
            elementos.detalleVacio
        ) {

            elementos.detalleVacio.hidden =
                true;

        }


        if (
            elementos.detalleContenido
        ) {

            elementos.detalleContenido.hidden =
                false;

        }


        if (
            elementos.detalleTipo
        ) {

            elementos.detalleTipo.textContent =
                tipo;

        }


        if (
            elementos.detalleNombre
        ) {

            elementos.detalleNombre.textContent =
                nombre ||
                "Sin nombre";

        }


        if (
            elementos.detalleDatos
        ) {

            elementos.detalleDatos.innerHTML =
                "";

        }


        if (
            elementos.detalleEnlace
        ) {

            elementos.detalleEnlace.hidden =
                true;


            elementos.detalleEnlace
                .removeAttribute(
                    "href"
                );

        }


        limpiarTitularesDetalle();

    }


    function restaurarDetalleVacio() {

        if (
            elementos.detalleVacio
        ) {

            elementos.detalleVacio.hidden =
                false;

        }


        if (
            elementos.detalleContenido
        ) {

            elementos.detalleContenido.hidden =
                true;

        }


        if (
            elementos.detalleDatos
        ) {

            elementos.detalleDatos.innerHTML =
                "";

        }


        if (
            elementos.detalleEnlace
        ) {

            elementos.detalleEnlace.hidden =
                true;


            elementos.detalleEnlace
                .removeAttribute(
                    "href"
                );

        }


        limpiarTitularesDetalle();

    }


    function configurarEnlaceDetalle(
        href,
        texto
    ) {

        if (
            !elementos.detalleEnlace ||
            !href
        ) {

            return;

        }


        elementos.detalleEnlace.href =
            href;


        elementos.detalleEnlace.textContent =
            texto ||
            "Ver información";


        elementos.detalleEnlace.hidden =
            false;

    }


    /* =====================================================
       TITULARES
    ====================================================== */

    function nombreCompletoTitular(
        titular
    ) {

        return [
            titular?.nombre,
            titular?.apellido_paterno,
            titular?.apellido_materno
        ]
            .filter(Boolean)
            .join(" ") ||
            "Titular sin nombre";

    }


    function renderizarTitulares(
        titulares
    ) {

        if (
            !elementos.detalleTitulares ||
            !elementos.detalleListaTitulares
        ) {

            return;

        }


        elementos
            .detalleListaTitulares
            .innerHTML =
            "";


        elementos
            .detalleTitulares
            .hidden =
            false;


        const lista =
            Array.isArray(titulares)
                ? titulares
                : [];


        if (
            lista.length === 0
        ) {

            const vacio =
                document.createElement(
                    "p"
                );


            vacio.className =
                "mapa-titulares-vacio";


            vacio.textContent =
                "Sin titulares nominales registrados.";


            elementos
                .detalleListaTitulares
                .appendChild(
                    vacio
                );


            return;

        }


        lista.forEach(
            titular => {

                const articulo =
                    document.createElement(
                        "article"
                    );


                articulo.className =
                    "mapa-titular-item";


                const nombre =
                    document.createElement(
                        "strong"
                    );


                nombre.textContent =
                    nombreCompletoTitular(
                        titular
                    );


                articulo.appendChild(
                    nombre
                );


                if (
                    valorPresente(
                        titular.tipo_derecho
                    )
                ) {

                    const derecho =
                        document.createElement(
                            "span"
                        );


                    derecho.textContent =
                        `Tipo de derecho: ${titular.tipo_derecho}`;


                    articulo.appendChild(
                        derecho
                    );

                }


                if (
                    valorPresente(
                        titular.telefono
                    )
                ) {

                    const telefono =
                        document.createElement(
                            "span"
                        );


                    telefono.textContent =
                        `Teléfono: ${titular.telefono}`;


                    articulo.appendChild(
                        telefono
                    );

                }


                if (
                    valorPresente(
                        titular.correo_electronico
                    )
                ) {

                    const correo =
                        document.createElement(
                            "span"
                        );


                    correo.textContent =
                        `Correo: ${titular.correo_electronico}`;


                    articulo.appendChild(
                        correo
                    );

                }


                /*
                 * porcentaje_participacion puede venir
                 * desde el backend.
                 *
                 * Por decisión funcional NO se muestra.
                 */


                elementos
                    .detalleListaTitulares
                    .appendChild(
                        articulo
                    );

            }
        );

    }


    /* =====================================================
       LEAFLET
    ====================================================== */

    function iniciarMapa() {

        mapaLeaflet =
            window.L.map(
                elementos.mapa,
                {
                    zoomControl: true,
                    preferCanvas: true
                }
            );


        window.L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                maxZoom: 19,

                attribution:
                    "&copy; OpenStreetMap contributors"
            }
        ).addTo(
            mapaLeaflet
        );


        grupos.trazo_proyecto =
            window.L
                .featureGroup()
                .addTo(
                    mapaLeaflet
                );


        grupos.nucleo_agrario =
            window.L
                .featureGroup()
                .addTo(
                    mapaLeaflet
                );


        grupos.parcela =
            window.L
                .featureGroup()
                .addTo(
                    mapaLeaflet
                );


        mapaLeaflet.setView(
            VISTA_INICIAL.centro,
            VISTA_INICIAL.zoom
        );


        window.setTimeout(
            () => {

                mapaLeaflet.invalidateSize();

            },
            0
        );

    }


    function limpiarIndicesCapas() {

        Object
            .values(
                capasPorTipoId
            )
            .forEach(
                mapa =>
                    mapa.clear()
            );

    }


    function limpiarGeometrias() {

        Object
            .values(
                grupos
            )
            .forEach(
                grupo => {

                    grupo?.clearLayers();

                }
            );


        limpiarIndicesCapas();

        restaurarDetalleVacio();

    }


    function capaVisible(tipo) {

        const controles = {

            trazo_proyecto:
                elementos.capaTrazos,

            nucleo_agrario:
                elementos.capaNucleos,

            parcela:
                elementos.capaParcelas

        };


        return (
            controles[tipo]?.checked !==
            false
        );

    }


    function sincronizarCapa(tipo) {

        const grupo =
            grupos[tipo];


        if (
            !grupo ||
            !mapaLeaflet
        ) {

            return;

        }


        if (
            capaVisible(tipo)
        ) {

            if (
                !mapaLeaflet.hasLayer(
                    grupo
                )
            ) {

                grupo.addTo(
                    mapaLeaflet
                );

            }

        } else if (
            mapaLeaflet.hasLayer(
                grupo
            )
        ) {

            mapaLeaflet.removeLayer(
                grupo
            );

        }

    }


    function enlazarControlesCapas() {

        const controles = [

            [
                "trazo_proyecto",
                elementos.capaTrazos
            ],

            [
                "nucleo_agrario",
                elementos.capaNucleos
            ],

            [
                "parcela",
                elementos.capaParcelas
            ]

        ];


        controles.forEach(
            (
                [
                    tipo,
                    control
                ]
            ) => {

                control?.addEventListener(
                    "change",
                    () =>
                        sincronizarCapa(
                            tipo
                        )
                );

            }
        );

    }


    function estiloParaFeature(
        feature
    ) {

        return (
            ESTILOS[
                feature
                    ?.properties
                    ?.tipo
            ] ||
            {
                color: "#555",

                weight: 2,

                opacity: 0.8,

                fillOpacity: 0.15
            }
        );

    }


    function registrarCapa(
        tipo,
        id,
        capa
    ) {

        const mapa =
            capasPorTipoId[tipo];


        if (!mapa) {

            return;

        }


        const clave =
            Number(id);


        const existentes =
            mapa.get(clave) ||
            [];


        existentes.push(
            capa
        );


        mapa.set(
            clave,
            existentes
        );

    }


    function aplicarEstiloACapas(
        capas,
        estilo
    ) {

        (
            capas ||
            []
        ).forEach(
            capa => {

                if (
                    typeof capa?.setStyle ===
                    "function"
                ) {

                    capa.setStyle(
                        estilo
                    );

                }

            }
        );

    }


    function restaurarEstilosGeometrias() {

        Object
            .entries(
                capasPorTipoId
            )
            .forEach(
                (
                    [
                        tipo,
                        mapa
                    ]
                ) => {

                    mapa.forEach(
                        capas => {

                            aplicarEstiloACapas(
                                capas,
                                ESTILOS[tipo]
                            );

                        }
                    );

                }
            );

    }


    function resaltarTrazo(
        idTrazo
    ) {

        restaurarEstilosGeometrias();


        aplicarEstiloACapas(
            capasPorTipoId
                .trazo_proyecto
                .get(
                    Number(
                        idTrazo
                    )
                ),

            ESTILOS_SELECCION
                .trazo_proyecto
        );

    }


    function resaltarNucleo(
        idNucleo,
        idsParcelas = []
    ) {

        restaurarEstilosGeometrias();


        const idSeleccionado =
            Number(
                idNucleo
            );


        const parcelasSeleccionadas =
            new Set(
                idsParcelas.map(
                    Number
                )
            );


        /*
         * Atenuamos otros núcleos.
         */

        capasPorTipoId
            .nucleo_agrario
            .forEach(
                (
                    capas,
                    id
                ) => {

                    if (
                        Number(id) ===
                        idSeleccionado
                    ) {

                        aplicarEstiloACapas(
                            capas,
                            ESTILOS_SELECCION
                                .nucleo_agrario
                        );

                    } else {

                        aplicarEstiloACapas(
                            capas,
                            {
                                ...ESTILOS
                                    .nucleo_agrario,

                                opacity:
                                    0.3,

                                fillOpacity:
                                    0.06
                            }
                        );

                    }

                }
            );


        /*
         * Resaltamos las parcelas que pertenecen
         * al núcleo seleccionado.
         */

        capasPorTipoId
            .parcela
            .forEach(
                (
                    capas,
                    id
                ) => {

                    if (
                        parcelasSeleccionadas.has(
                            Number(id)
                        )
                    ) {

                        aplicarEstiloACapas(
                            capas,
                            ESTILOS_SELECCION
                                .parcela
                        );

                    } else {

                        aplicarEstiloACapas(
                            capas,
                            {
                                ...ESTILOS
                                    .parcela,

                                opacity:
                                    0.25,

                                fillOpacity:
                                    0.05
                            }
                        );

                    }

                }
            );

    }


    function resaltarParcela(
        idParcela,
        idNucleo = null
    ) {

        restaurarEstilosGeometrias();


        aplicarEstiloACapas(
            capasPorTipoId
                .parcela
                .get(
                    Number(
                        idParcela
                    )
                ),

            ESTILOS_SELECCION
                .parcela
        );


        /*
         * También resaltamos el núcleo al que
         * pertenece la parcela.
         */

        if (idNucleo) {

            aplicarEstiloACapas(
                capasPorTipoId
                    .nucleo_agrario
                    .get(
                        Number(
                            idNucleo
                        )
                    ),

                ESTILOS_SELECCION
                    .nucleo_agrario
            );

        }

    }


    function agregarFeature(
        feature,
        proyecto
    ) {

        const tipo =
            feature
                ?.properties
                ?.tipo;


        const id =
            feature
                ?.properties
                ?.id;


        const grupo =
            grupos[tipo];


        if (
            !grupo ||
            !feature?.geometry ||
            !valorPresente(id)
        ) {

            return false;

        }


        const featureEnriquecido = {

            ...feature,

            properties: {

                ...(
                    feature.properties ||
                    {}
                ),

                id_proyecto:
                    proyecto.id_proyecto,

                nombre_proyecto:
                    nombreProyecto(
                        proyecto
                    )

            }

        };


        try {

            const capaGeoJSON =
                window.L.geoJSON(
                    featureEnriquecido,
                    {

                        style:
                            estiloParaFeature,


                        onEachFeature:
                            (
                                featureActual,
                                capa
                            ) => {

                                const nombre =
                                    featureActual
                                        .properties
                                        ?.nombre ||
                                    tipoLegible(
                                        tipo
                                    );


                                const proyectoNombre =
                                    featureActual
                                        .properties
                                        ?.nombre_proyecto;


                                capa.bindTooltip(
                                    tipo ===
                                    "trazo_proyecto"
                                        ? proyectoNombre
                                        : nombre,
                                    {
                                        sticky: true
                                    }
                                );


                                capa.on(
                                    "click",
                                    () => {

                                        mostrarDetalleFeature(
                                            featureActual
                                        )
                                            .catch(
                                                error => {

                                                    console.error(
                                                        "No fue posible cargar el detalle del elemento.",
                                                        error
                                                    );


                                                    mostrarError(
                                                        error?.mensaje ||
                                                        error?.message ||
                                                        "No fue posible cargar el detalle seleccionado."
                                                    );

                                                }
                                            );

                                    }
                                );

                            }

                    }
                );


            capaGeoJSON.eachLayer(
                capa => {

                    grupo.addLayer(
                        capa
                    );


                    registrarCapa(
                        tipo,
                        id,
                        capa
                    );

                }
            );


            return true;

        } catch (error) {

            console.warn(
                `Geometría inválida en ${tipo} del proyecto ${proyecto.id_proyecto}.`,
                error
            );


            return false;

        }

    }


    function ajustarMapaAGeometrias() {

        if (!mapaLeaflet) {

            return;

        }


        const capasConBounds =
            Object
                .values(
                    grupos
                )
                .filter(Boolean)
                .filter(
                    grupo =>
                        grupo
                            .getLayers()
                            .length >
                        0
                );


        if (
            capasConBounds.length ===
            0
        ) {

            mapaLeaflet.setView(
                VISTA_INICIAL.centro,
                VISTA_INICIAL.zoom
            );

            return;

        }


        const conjunto =
            window.L.featureGroup(
                capasConBounds
            );


        const bounds =
            conjunto.getBounds();


        if (
            bounds.isValid()
        ) {

            mapaLeaflet.fitBounds(
                bounds.pad(
                    0.08
                ),
                {
                    maxZoom: 15
                }
            );

        } else {

            mapaLeaflet.setView(
                VISTA_INICIAL.centro,
                VISTA_INICIAL.zoom
            );

        }

    }


    /* =====================================================
       API
    ====================================================== */

    async function obtenerMapaProyecto(
        idProyecto
    ) {

        return window.ClienteAPI.get(
            `/proyectos/${idProyecto}/mapa`
        );

    }


    async function obtenerNucleosProyecto(
        idProyecto
    ) {

        const id =
            Number(
                idProyecto
            );


        if (
            nucleosProyectoCache.has(
                id
            )
        ) {

            return (
                nucleosProyectoCache.get(
                    id
                )
            );

        }


        const limite =
            200;


        const nucleos =
            [];


        let skip =
            0;


        while (true) {

            const respuesta =
                await window.ClienteAPI.get(
                    `/proyectos/${id}/nucleos?skip=${skip}&limit=${limite}`
                );


            const pagina =
                extraerLista(
                    respuesta,
                    [
                        "items",
                        "data",
                        "nucleos"
                    ]
                );


            nucleos.push(
                ...pagina
            );


            if (
                pagina.length <
                limite
            ) {

                break;

            }


            skip +=
                limite;

        }


        nucleosProyectoCache.set(
            id,
            nucleos
        );


        return nucleos;

    }


    async function obtenerParcelasProyectoNucleo(
        idProyectoNucleo
    ) {

        const id =
            Number(
                idProyectoNucleo
            );


        if (
            parcelasNucleoCache.has(
                id
            )
        ) {

            return (
                parcelasNucleoCache.get(
                    id
                )
            );

        }


        const respuesta =
            await window.ClienteAPI.get(
                `/proyecto-nucleo/${id}/parcelas`
            );


        const parcelas =
            extraerLista(
                respuesta,
                [
                    "items",
                    "data",
                    "parcelas"
                ]
            );


        parcelasNucleoCache.set(
            id,
            parcelas
        );


        return parcelas;

    }


    async function obtenerParcela(
        idParcela
    ) {

        return window.ClienteAPI.get(
            `/parcelas/${idParcela}`
        );

    }


    async function obtenerTitularesParcela(
        idParcela
    ) {

        const id =
            Number(
                idParcela
            );


        if (
            titularesParcelaCache.has(
                id
            )
        ) {

            return (
                titularesParcelaCache.get(
                    id
                )
            );

        }


        const respuesta =
            await window.ClienteAPI.get(
                `/parcelas/${id}/titulares`
            );


        const titulares =
            extraerLista(
                respuesta,
                [
                    "items",
                    "data",
                    "titulares"
                ]
            );


        titularesParcelaCache.set(
            id,
            titulares
        );


        return titulares;

    }


    async function cargarMapaDeProyecto(
        proyecto
    ) {

        const geojson =
            await obtenerMapaProyecto(
                proyecto.id_proyecto
            );


        const features =
            Array.isArray(
                geojson?.features
            )
                ? geojson.features
                : [];


        let agregadas =
            0;


        features.forEach(
            feature => {

                if (
                    agregarFeature(
                        feature,
                        proyecto
                    )
                ) {

                    agregadas +=
                        1;

                }

            }
        );


        return {

            total:
                features.length,

            agregadas

        };

    }


    /* =====================================================
       RESUMEN DEL PROYECTO
    ====================================================== */

    function ocultarResumenProyecto() {

        if (
            elementos.resumenProyecto
        ) {

            elementos.resumenProyecto.hidden =
                true;

        }


        [
            elementos.resumenSuperficie,
            elementos.resumenNucleos,
            elementos.resumenParcelas,
            elementos.resumenAfectaciones
        ]
            .forEach(
                elemento => {

                    if (elemento) {

                        elemento.hidden =
                            true;

                    }

                }
            );

    }


    function mostrarResumenProyecto(
        proyecto,
        nucleos
    ) {

        if (!proyecto) {

            ocultarResumenProyecto();

            return;

        }


        const resumen =
            resumenDesdeNucleos(
                nucleos
            );


        if (
            elementos.tituloResumenProyecto
        ) {

            elementos
                .tituloResumenProyecto
                .textContent =
                nombreProyecto(
                    proyecto
                );

        }


        /*
         * Superficie administrativa.
         */

        if (
            elementos.valorSuperficie &&
            elementos.resumenSuperficie
        ) {

            elementos.valorSuperficie.textContent =
                formatearHectareas(
                    resumen.superficie
                );


            elementos.resumenSuperficie.hidden =
                false;

        }


        /*
         * Núcleos.
         */

        if (
            elementos.valorNucleos &&
            elementos.resumenNucleos
        ) {

            elementos.valorNucleos.textContent =
                formatearNumero(
                    resumen.nucleos,
                    0
                );


            elementos.resumenNucleos.hidden =
                false;

        }


        /*
         * Parcelas.
         */

        if (
            elementos.valorParcelas &&
            elementos.resumenParcelas
        ) {

            elementos.valorParcelas.textContent =
                formatearNumero(
                    resumen.parcelas,
                    0
                );


            elementos.resumenParcelas.hidden =
                false;

        }


        /*
         * Afectaciones.
         */

        if (
            elementos.valorAfectaciones &&
            elementos.resumenAfectaciones
        ) {

            elementos.valorAfectaciones.textContent =
                formatearNumero(
                    resumen.afectaciones,
                    0
                );


            elementos.resumenAfectaciones.hidden =
                false;

        }


        if (
            elementos.resumenProyecto
        ) {

            elementos.resumenProyecto.hidden =
                false;

        }

    }


    /* =====================================================
       DETALLE INTERACTIVO
    ====================================================== */

    async function mostrarDetalleFeature(
        feature
    ) {

        limpiarMensajes();


        const props =
            feature?.properties ||
            {};


        const tipo =
            props.tipo;


        const idProyecto =
            Number(
                props.id_proyecto
            );


        const proyecto =
            obtenerProyecto(
                idProyecto
            );


        /*
         * Si mientras cargaba el detalle el usuario cambió
         * de proyecto, ya no mostramos información vieja.
         */

        if (
            !proyecto ||
            idProyecto !==
            idProyectoActivo
        ) {

            return;

        }


        /* =================================================
           TRAZO
        ================================================== */

        if (
            tipo ===
            "trazo_proyecto"
        ) {

            resaltarTrazo(
                props.id
            );


            prepararDetalle(
                "Proyecto / trazo",
                nombreProyecto(
                    proyecto
                )
            );


            const nucleos =
                await obtenerNucleosProyecto(
                    idProyecto
                );


            if (
                idProyectoActivo !==
                idProyecto
            ) {

                return;

            }


            const resumen =
                resumenDesdeNucleos(
                    nucleos
                );


            agregarDatoDetalle(
                "Clave",
                proyecto.clave_proyecto ||
                "—"
            );


            agregarDatoDetalle(
                "Versión de trazo",
                props.nombre ||
                "—"
            );


            agregarDatoDetalle(
                "Inicio",
                formatearFecha(
                    proyecto.fecha_inicio
                )
            );


            agregarDatoDetalle(
                "Fin",
                formatearFecha(
                    proyecto.fecha_fin
                )
            );


            agregarDatoDetalle(
                "Superficie afectada",
                formatearHectareas(
                    resumen.superficie
                )
            );


            agregarDatoDetalle(
                "Núcleos agrarios",
                formatearNumero(
                    resumen.nucleos,
                    0
                )
            );


            agregarDatoDetalle(
                "Parcelas registradas",
                formatearNumero(
                    resumen.parcelas,
                    0
                )
            );


            agregarDatoDetalle(
                "Afectaciones registradas",
                formatearNumero(
                    resumen.afectaciones,
                    0
                )
            );


            configurarEnlaceDetalle(
                `/pages/fichaProyecto.html?id=${encodeURIComponent(
                    idProyecto
                )}`,
                "Ver información del proyecto"
            );


            return;

        }


        /* =================================================
           NÚCLEO AGRARIO
        ================================================== */

        if (
            tipo ===
            "nucleo_agrario"
        ) {

            const asociaciones =
                await obtenerNucleosProyecto(
                    idProyecto
                );


            const asociacion =
                asociaciones.find(
                    item =>
                        Number(
                            item.id_nucleo
                        ) ===
                        Number(
                            props.id
                        )
                );


            let parcelas =
                [];


            if (
                asociacion
                    ?.id_proyecto_nucleo
            ) {

                parcelas =
                    await obtenerParcelasProyectoNucleo(
                        asociacion
                            .id_proyecto_nucleo
                    );

            }


            if (
                idProyectoActivo !==
                idProyecto
            ) {

                return;

            }


            /*
             * Resaltamos el núcleo y las parcelas
             * que pertenecen a él.
             */

            resaltarNucleo(
                props.id,

                parcelas.map(
                    parcela =>
                        parcela.id_parcela
                )
            );


            prepararDetalle(
                "Núcleo agrario",

                props.nombre ||
                asociacion?.nombre_nucleo ||
                `Núcleo ${props.id}`
            );


            agregarDatoDetalle(
                "Proyecto",
                nombreProyecto(
                    proyecto
                )
            );


            agregarDatoDetalle(
                "Entidad",
                asociacion?.entidad ||
                "—"
            );


            agregarDatoDetalle(
                "Municipio",
                asociacion?.municipio ||
                "—"
            );


            agregarDatoDetalle(
                "Tenencia",
                asociacion
                    ?.tipo_tenencia_nombre ||
                asociacion
                    ?.tipo_tenencia_codigo ||
                "—"
            );


            agregarDatoDetalle(
                "Superficie afectada",
                formatearHectareas(
                    asociacion
                        ?.superficie_afectada_ha
                )
            );


            agregarDatoDetalle(
                "Parcelas registradas",
                formatearNumero(
                    asociacion
                        ?.total_parcelas,
                    0
                )
            );


            agregarDatoDetalle(
                "Afectaciones registradas",
                formatearNumero(
                    asociacion
                        ?.total_afectaciones,
                    0
                )
            );


            agregarDatoDetalle(
                "Afectaciones colectivas",
                formatearNumero(
                    asociacion
                        ?.afectaciones_colectivas,
                    0
                )
            );


            agregarDatoDetalle(
                "Afectaciones individuales",
                formatearNumero(
                    asociacion
                        ?.afectaciones_individuales,
                    0
                )
            );


            /*
             * El núcleo no tiene "titular".
             *
             * Se muestra el responsable registrado
             * para el proyecto-núcleo.
             */

            agregarDatoDetalle(
                "Responsable",
                asociacion
                    ?.responsable_nombre ||
                "—"
            );


            agregarDatoDetalle(
                "Cargo",
                asociacion
                    ?.responsable_cargo ||
                "—"
            );


            agregarDatoDetalle(
                "Contacto",
                asociacion
                    ?.responsable_contacto ||
                "—"
            );


            agregarDatoDetalle(
                "Asambleas registradas",
                formatearNumero(
                    asociacion
                        ?.total_asambleas,
                    0
                )
            );


            agregarDatoDetalle(
                "Convenios registrados",
                formatearNumero(
                    asociacion
                        ?.total_convenios,
                    0
                )
            );


            if (
                asociacion
                    ?.id_proyecto_nucleo
            ) {

                configurarEnlaceDetalle(
                    `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                        asociacion
                            .id_proyecto_nucleo
                    )}&id_proyecto=${encodeURIComponent(
                        idProyecto
                    )}`,

                    "Ver información del núcleo"
                );

            }


            return;

        }


        /* =================================================
           PARCELA
        ================================================== */

        if (
            tipo ===
            "parcela"
        ) {

            const [
                parcela,
                asociaciones,
                titulares
            ] = await Promise.all([

                obtenerParcela(
                    props.id
                ),

                obtenerNucleosProyecto(
                    idProyecto
                ),

                obtenerTitularesParcela(
                    props.id
                )

            ]);


            if (
                idProyectoActivo !==
                idProyecto
            ) {

                return;

            }


            const asociacion =
                asociaciones.find(
                    item =>
                        Number(
                            item.id_nucleo
                        ) ===
                        Number(
                            parcela?.id_nucleo
                        )
                );


            /*
             * Resalta parcela y núcleo.
             */

            resaltarParcela(
                props.id,
                parcela?.id_nucleo
            );


            prepararDetalle(
                "Parcela",

                props.nombre ||
                parcela?.no_parcela ||
                `Parcela ${props.id}`
            );


            agregarDatoDetalle(
                "Proyecto",
                nombreProyecto(
                    proyecto
                )
            );


            agregarDatoDetalle(
                "Núcleo agrario",
                asociacion
                    ?.nombre_nucleo ||
                "—"
            );


            agregarDatoDetalle(
                "Número de parcela",
                parcela?.no_parcela ||
                "—"
            );


            agregarDatoDetalle(
                "Tipo",
                textoTipoParcela(
                    parcela?.tipo_parcela
                )
            );


            agregarDatoDetalle(
                "Certificado parcelario",
                parcela
                    ?.certificado_parcelario ||
                "—"
            );


            agregarDatoDetalle(
                "Folio de derechos",
                parcela
                    ?.folio_derechos ||
                "—"
            );


            agregarDatoDetalle(
                "Vigencia de constancia",
                formatearFecha(
                    parcela
                        ?.constancia_vigencia_fecha
                )
            );


            /*
             * Titulares nominales de la parcela.
             *
             * No se muestra porcentaje de participación.
             */

            renderizarTitulares(
                titulares
            );


            /*
             * Todavía no existe una ficha independiente de
             * parcela en frontend-ssalfer, por lo que
             * enlazamos al núcleo correspondiente.
             */

            if (
                asociacion
                    ?.id_proyecto_nucleo
            ) {

                configurarEnlaceDetalle(
                    `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                        asociacion
                            .id_proyecto_nucleo
                    )}&id_proyecto=${encodeURIComponent(
                        idProyecto
                    )}`,

                    "Ver información del núcleo"
                );

            }


            return;

        }


        /*
         * Tipo no previsto.
         */

        restaurarEstilosGeometrias();


        prepararDetalle(
            tipoLegible(
                tipo
            ),

            props.nombre ||
            "Elemento geográfico"
        );


        agregarDatoDetalle(
            "Proyecto",
            nombreProyecto(
                proyecto
            )
        );

    }


    /* =====================================================
       SIN PROYECTO
    ====================================================== */

    function establecerSinProyecto(
        {
            actualizarHistoria =
                true
        } = {}
    ) {

        /*
         * Invalida cualquier carga anterior.
         */

        tokenCarga +=
            1;


        idProyectoActivo =
            null;


        limpiarMensajes();

        limpiarGeometrias();

        ocultarResumenProyecto();


        document.title =
            "Mapa del proyecto | SSALFER";


        if (
            elementos.titulo
        ) {

            elementos.titulo.textContent =
                "Mapa del proyecto";

        }


        if (
            elementos.descripcion
        ) {

            elementos.descripcion.textContent =
                "Selecciona un proyecto para consultar su trazo vigente, núcleos agrarios, parcelas e información administrativa relacionada.";

        }


        if (
            elementos.contextoNombreProyecto
        ) {

            elementos
                .contextoNombreProyecto
                .textContent =
                "—";

        }


        if (
            elementos.contextoProyecto
        ) {

            elementos.contextoProyecto.hidden =
                true;

        }


        if (
            elementos.enlaceFichaProyecto
        ) {

            elementos
                .enlaceFichaProyecto
                .hidden =
                true;


            elementos
                .enlaceFichaProyecto
                .removeAttribute(
                    "href"
                );

        }


        if (
            elementos
                .enlaceGestionGeoespacial
        ) {

            elementos
                .enlaceGestionGeoespacial
                .hidden =
                true;


            elementos
                .enlaceGestionGeoespacial
                .removeAttribute(
                    "href"
                );

        }


        if (
            elementos.selectorProyecto
        ) {

            elementos
                .selectorProyecto
                .value =
                "";

        }


        mapaLeaflet?.setView(
            VISTA_INICIAL.centro,
            VISTA_INICIAL.zoom
        );


        mostrarEstadoInicial();


        if (
            actualizarHistoria
        ) {

            actualizarUrl(
                null
            );

        }

    }


    /* =====================================================
       PROYECTO ACTIVO
    ====================================================== */

    function establecerProyectoActivo(
        proyecto
    ) {

        idProyectoActivo =
            Number(
                proyecto.id_proyecto
            );


        document.title =
            `${nombreProyecto(
                proyecto
            )} | Mapa | SSALFER`;


        if (
            elementos.titulo
        ) {

            elementos.titulo.textContent =
                "Mapa del proyecto";

        }


        if (
            elementos.descripcion
        ) {

            elementos.descripcion.textContent =
                "Consulta el trazo vigente, núcleos agrarios, parcelas e información administrativa del proyecto seleccionado.";

        }


        if (
            elementos.contextoNombreProyecto
        ) {

            elementos
                .contextoNombreProyecto
                .textContent =
                nombreProyecto(
                    proyecto
                );

        }


        if (
            elementos.contextoProyecto
        ) {

            elementos.contextoProyecto.hidden =
                false;

        }


        if (
            elementos.enlaceFichaProyecto
        ) {

            elementos.enlaceFichaProyecto.href =
                `/pages/fichaProyecto.html?id=${encodeURIComponent(
                    proyecto.id_proyecto
                )}`;


            elementos.enlaceFichaProyecto.hidden =
                false;

        }


        if (
            elementos.enlaceGestionGeoespacial
        ) {

            elementos
                .enlaceGestionGeoespacial
                .href =
                `/pages/gestionGeoespacial.html?id_proyecto=${encodeURIComponent(
                    proyecto.id_proyecto
                )}`;


            elementos
                .enlaceGestionGeoespacial
                .hidden =
                false;

        }

    }


    /* =====================================================
       CARGAR UN PROYECTO
    ====================================================== */

    async function cargarProyecto(
        idProyecto,
        {
            actualizarHistoria =
                true
        } = {}
    ) {

        const cargaActual =
            ++tokenCarga;


        const proyecto =
            obtenerProyecto(
                idProyecto
            );


        /*
         * Lo primero es borrar absolutamente todo
         * lo perteneciente al proyecto anterior.
         */

        limpiarMensajes();

        limpiarGeometrias();

        ocultarResumenProyecto();


        if (!proyecto) {

            establecerSinProyecto({
                actualizarHistoria: false
            });


            mostrarError(
                "El proyecto indicado no está disponible para este usuario."
            );


            return;

        }


        establecerProyectoActivo(
            proyecto
        );


        if (
            elementos.selectorProyecto
        ) {

            elementos
                .selectorProyecto
                .value =
                String(
                    proyecto.id_proyecto
                );

        }


        if (
            actualizarHistoria
        ) {

            actualizarUrl(
                proyecto.id_proyecto
            );

        }


        mostrarCarga(
            `Cargando mapa de ${nombreProyecto(
                proyecto
            )}…`
        );


        /*
         * El mapa y el resumen se consultan en paralelo.
         *
         * Si uno falla, el otro todavía puede mostrarse.
         */

        const [
            resultadoMapa,
            resultadoNucleos
        ] = await Promise.allSettled([

            cargarMapaDeProyecto(
                proyecto
            ),

            obtenerNucleosProyecto(
                proyecto.id_proyecto
            )

        ]);


        /*
         * El usuario pudo cambiar de proyecto mientras
         * esperábamos al backend.
         */

        if (
            cargaActual !==
            tokenCarga
        ) {

            return;

        }


        const errores =
            [];


        /*
         * Resumen administrativo.
         */

        if (
            resultadoNucleos.status ===
            "fulfilled"
        ) {

            mostrarResumenProyecto(
                proyecto,
                resultadoNucleos.value
            );

        } else {

            errores.push(
                "No fue posible consultar el resumen administrativo del proyecto."
            );


            console.error(
                "Error al consultar núcleos del proyecto:",
                resultadoNucleos.reason
            );

        }


        /*
         * Geometrías.
         */

        if (
            resultadoMapa.status ===
            "fulfilled"
        ) {

            ajustarMapaAGeometrias();


            if (
                (
                    resultadoMapa
                        .value
                        ?.agregadas ||
                    0
                ) === 0
            ) {

                mostrarInformativo(
                    "Este proyecto todavía no tiene geometrías vigentes registradas en el mapa."
                );

            }

        } else {

            errores.push(
                "No fue posible consultar las geometrías del proyecto."
            );


            console.error(
                "Error al consultar el mapa del proyecto:",
                resultadoMapa.reason
            );


            mapaLeaflet?.setView(
                VISTA_INICIAL.centro,
                VISTA_INICIAL.zoom
            );

        }


        ocultarCarga();


        if (
            errores.length > 0
        ) {

            mostrarError(
                errores.join(" ")
            );

        }

    }


    /* =====================================================
       SELECTOR DE PROYECTOS
    ====================================================== */

    function llenarSelectorProyectos() {

        if (
            !elementos.selectorProyecto
        ) {

            return;

        }


        elementos.selectorProyecto.innerHTML =
            "";


        const placeholder =
            document.createElement(
                "option"
            );


        placeholder.value =
            "";


        placeholder.textContent =
            "Selecciona un proyecto";


        elementos.selectorProyecto.appendChild(
            placeholder
        );


        proyectos.forEach(
            proyecto => {

                const opcion =
                    document.createElement(
                        "option"
                    );


                opcion.value =
                    String(
                        proyecto.id_proyecto
                    );


                opcion.textContent =
                    nombreProyecto(
                        proyecto
                    );


                elementos
                    .selectorProyecto
                    .appendChild(
                        opcion
                    );

            }
        );

    }


    async function cargarProyectos() {

        const limite =
            200;


        const todos =
            [];


        let skip =
            0;


        while (true) {

            const respuesta =
                await window.ClienteAPI.get(
                    `/proyectos?skip=${skip}&limit=${limite}`
                );


            const pagina =
                extraerLista(
                    respuesta,
                    [
                        "items",
                        "data",
                        "proyectos"
                    ]
                );


            todos.push(
                ...pagina
            );


            if (
                pagina.length <
                limite
            ) {

                break;

            }


            skip +=
                limite;

        }


        proyectos =
            todos;


        proyectoPorId.clear();


        proyectos.forEach(
            proyecto => {

                proyectoPorId.set(
                    Number(
                        proyecto.id_proyecto
                    ),
                    proyecto
                );

            }
        );


        llenarSelectorProyectos();

    }


    function enlazarSelector() {

        elementos
            .selectorProyecto
            ?.addEventListener(
                "change",
                async evento => {

                    const valor =
                        evento
                            .target
                            .value;


                    /*
                     * Placeholder:
                     * no carga ningún proyecto.
                     */

                    if (!valor) {

                        establecerSinProyecto();

                        return;

                    }


                    const id =
                        Number(
                            valor
                        );


                    if (
                        Number.isInteger(id) &&
                        id > 0
                    ) {

                        await cargarProyecto(
                            id
                        );

                    }

                }
            );

    }


    /* =====================================================
       INICIO
    ====================================================== */

    async function iniciar() {

        iniciarMapa();

        enlazarControlesCapas();

        enlazarSelector();


        mostrarCarga(
            "Consultando proyectos disponibles…"
        );


        try {

            await cargarProyectos();


            const idUrl =
                obtenerIdProyectoUrl();


            /*
             * Si llegamos desde fichaProyecto:
             *
             * mapa.html?id_proyecto=X
             *
             * se carga directamente ese proyecto.
             */

            if (idUrl) {

                await cargarProyecto(
                    idUrl,
                    {
                        actualizarHistoria:
                            false
                    }
                );


                return;

            }


            /*
             * Si entramos desde Dashboard:
             *
             * mapa.html
             *
             * no cargamos geometrías hasta seleccionar
             * un proyecto.
             */

            establecerSinProyecto({
                actualizarHistoria:
                    false
            });


            if (
                proyectos.length === 0
            ) {

                mostrarInformativo(
                    "No hay proyectos disponibles para consultar."
                );

            }

        } catch (error) {

            console.error(
                "No fue posible iniciar el visor geográfico.",
                error
            );


            establecerSinProyecto({
                actualizarHistoria:
                    false
            });


            mostrarError(
                error?.mensaje ||
                error?.message ||
                "No fue posible consultar los proyectos del sistema."
            );

        }

    }


    iniciar();

});