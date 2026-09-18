/**
 * gestionGeoespacial.js
 * ------------------------------------------------------------
 * Gestión de importaciones geoespaciales de SSALFER.
 *
 * Flujo:
 *
 * Proyecto
 *   ↓
 * Archivo GIS
 *   ↓
 * POST /proyectos/{id}/importaciones
 *   ↓
 * Previsualización
 *   ↓
 * GET /importaciones/{id}/features
 *   ↓
 * Confirmación
 *   ↓
 * POST /importaciones/{id}/confirmar
 *   ↓
 * PostGIS
 *
 * No utiliza datos simulados.
 * ------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {

    "use strict";


    /* =====================================================
       ELEMENTOS
    ====================================================== */

    const elementos = {

        mensajeError:
            document.getElementById("geoespacialMensajeError"),

        mensajeExito:
            document.getElementById("geoespacialMensajeExito"),

        mensajeInformativo:
            document.getElementById("geoespacialMensajeInformativo"),


        selectorProyecto:
            document.getElementById("selectorProyectoGeoespacial"),


        form:
            document.getElementById("formImportacionGeoespacial"),

        tipoObjetivo:
            document.getElementById("tipoObjetivoGeoespacial"),

        fuente:
            document.getElementById("fuenteGeoespacial"),

        fechaFuente:
            document.getElementById("fechaFuenteGeoespacial"),


        grupoMapeo:
            document.getElementById("grupoMapeoDestino"),

        campoIdDestino:
            document.getElementById("campoIdDestino"),

        ayudaMapeo:
            document.getElementById("ayudaMapeoDestino"),


        inputArchivo:
            document.getElementById("archivoGeoespacial"),

        zonaArchivo:
            document.getElementById("zonaArchivoGeoespacial"),

        archivoSeleccionado:
            document.getElementById("archivoSeleccionado"),

        archivoNombre:
            document.getElementById("archivoSeleccionadoNombre"),

        archivoTamano:
            document.getElementById("archivoSeleccionadoTamano"),

        btnQuitarArchivo:
            document.getElementById("btnQuitarArchivo"),

        btnPreparar:
            document.getElementById("btnPrepararImportacion"),


        btnActualizarImportaciones:
            document.getElementById("btnActualizarImportaciones"),

        importacionesVacio:
            document.getElementById("importacionesVacio"),

        listaImportaciones:
            document.getElementById("listaImportaciones"),


        seccionPreview:
            document.getElementById("seccionPrevisualizacion"),

        previewNombreArchivo:
            document.getElementById("previewNombreArchivo"),

        previewEstado:
            document.getElementById("previewEstado"),

        previewFormato:
            document.getElementById("previewFormato"),

        previewObjetivo:
            document.getElementById("previewObjetivo"),

        previewCrsOriginal:
            document.getElementById("previewCrsOriginal"),

        previewCrsDestino:
            document.getElementById("previewCrsDestino"),

        previewFuente:
            document.getElementById("previewFuente"),

        previewFechaFuente:
            document.getElementById("previewFechaFuente"),

        previewSha256:
            document.getElementById("previewSha256"),

        previewTotal:
            document.getElementById("previewTotal"),

        previewValidos:
            document.getElementById("previewValidos"),

        previewAdvertencias:
            document.getElementById("previewAdvertencias"),

        previewErrores:
            document.getElementById("previewErrores"),

        previewImportados:
            document.getElementById("previewImportados"),


        tablaFeatures:
            document.getElementById("tablaFeaturesGeoespaciales"),

        featuresVacio:
            document.getElementById("featuresVacio"),


        bloqueConfirmacion:
            document.getElementById("bloqueConfirmacionImportacion"),

        contenedorAceptarAdvertencias:
            document.getElementById("contenedorAceptarAdvertencias"),

        aceptarAdvertencias:
            document.getElementById("aceptarAdvertencias"),

        btnConfirmar:
            document.getElementById("btnConfirmarImportacion"),

        btnVerProyectoMapa:
            document.getElementById("btnVerProyectoMapa"),

        btnCrearImportacion:
            document.getElementById("btnCrearImportacion"),

        seccionNuevaImportacion:
            document.getElementById("seccionNuevaImportacion"),

        btnCerrarImportacion:
            document.getElementById("btnCerrarImportacion")

    };


    /* =====================================================
       CONSTANTES
    ====================================================== */

    const EXTENSIONES_PERMITIDAS = new Set([
        "geojson",
        "json",
        "kml",
        "gpkg",
        "zip"
    ]);


    const TIPOS_OBJETIVO = new Set([
        "trazo_proyecto",
        "nucleo_agrario",
        "parcela"
    ]);


    /* =====================================================
       ESTADO
    ====================================================== */

    let proyectos = [];

    let proyectoActivo = null;

    let archivoActivo = null;

    let importacionActiva = null;

    let procesando = false;


    /* =====================================================
       VALIDACIÓN INICIAL
    ====================================================== */

    if (!window.ClienteAPI) {

        console.error(
            "ClienteAPI no está disponible."
        );

        return;

    }


    /* =====================================================
       UTILIDADES
    ====================================================== */

    function tieneValor(valor) {

        return !(
            valor === null ||
            valor === undefined ||
            valor === ""
        );

    }


    function numero(valor, respaldo = 0) {

        const convertido = Number(valor);

        return Number.isFinite(convertido)
            ? convertido
            : respaldo;

    }


    function texto(valor, respaldo = "—") {

        return tieneValor(valor)
            ? String(valor)
            : respaldo;

    }


    function escaparTexto(valor) {

        const div = document.createElement("div");

        div.textContent = texto(valor, "");

        return div.innerHTML;

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


    function etiquetaTipo(tipo) {

        const tipos = {

            trazo_proyecto:
                "Trazo del proyecto",

            nucleo_agrario:
                "Núcleo agrario",

            parcela:
                "Parcela"

        };

        return tipos[tipo] || texto(tipo);

    }


    function etiquetaEstado(estado) {

        const estados = {

            procesando:
                "Procesando",

            previsualizado:
                "Previsualizado",

            completo:
                "Completo",

            error:
                "Error"

        };

        return estados[estado] || texto(estado);

    }


    function formatearTamano(bytes) {

        const cantidad = Number(bytes);

        if (!Number.isFinite(cantidad)) {
            return "—";
        }


        if (cantidad < 1024) {

            return `${cantidad} B`;

        }


        if (cantidad < 1024 ** 2) {

            return (
                `${(cantidad / 1024).toLocaleString(
                    "es-MX",
                    {
                        maximumFractionDigits: 1
                    }
                )} KB`
            );

        }


        return (
            `${(cantidad / (1024 ** 2)).toLocaleString(
                "es-MX",
                {
                    maximumFractionDigits: 2
                }
            )} MB`
        );

    }


    function formatearFecha(valor) {

        if (!valor) {
            return "—";
        }


        const partes =
            String(valor)
                .substring(0, 10)
                .split("-");


        if (partes.length !== 3) {

            return texto(valor);

        }


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


        if (Number.isNaN(fecha.getTime())) {

            return texto(valor);

        }


        return fecha.toLocaleDateString(
            "es-MX",
            {
                year: "numeric",
                month: "short",
                day: "2-digit"
            }
        );

    }


    function formatearFechaHora(valor) {

        if (!valor) {
            return "—";
        }


        const fecha =
            new Date(valor);


        if (Number.isNaN(fecha.getTime())) {

            return texto(valor);

        }


        return fecha.toLocaleString(
            "es-MX",
            {
                year: "numeric",
                month: "short",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit"
            }
        );

    }


    function obtenerExtension(nombre) {

        const partes =
            String(nombre || "")
                .toLowerCase()
                .split(".");


        if (partes.length < 2) {

            return "";

        }


        return partes.pop();

    }


    function obtenerIdProyectoUrl() {

        const parametros =
            new URLSearchParams(
                window.location.search
            );


        const id =
            Number(
                parametros.get("id_proyecto")
            );


        return (
            Number.isInteger(id) &&
            id > 0
        )
            ? id
            : null;

    }


    function actualizarUrlProyecto(idProyecto) {

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




    function obtenerIdProyectoSeleccionado() {

    /*
     * Primero intentamos obtenerlo directamente
     * del selector visible en pantalla.
     */
    const valorSelector =
        elementos.selectorProyecto?.value;

    const idSelector =
        Number(valorSelector);


    if (
        Number.isInteger(idSelector) &&
        idSelector > 0
    ) {

        return idSelector;

    }


    /*
     * Si entramos desde la ficha de un proyecto,
     * también puede venir en la URL.
     */
    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idUrl =
        Number(
            parametros.get("id_proyecto")
        );


    if (
        Number.isInteger(idUrl) &&
        idUrl > 0
    ) {

        return idUrl;

    }


    return null;
}





    /* =====================================================
       MENSAJES
    ====================================================== */

    function limpiarMensajes() {

        [
            elementos.mensajeError,
            elementos.mensajeExito,
            elementos.mensajeInformativo

        ].forEach(elemento => {

            if (!elemento) {
                return;
            }

            elemento.textContent = "";

            elemento.hidden = true;

        });

    }


    function mostrarError(mensaje) {

        if (!elementos.mensajeError) {
            return;
        }


        elementos.mensajeError.textContent =
            mensaje;

        elementos.mensajeError.hidden =
            false;

    }


    function mostrarExito(mensaje) {

        if (!elementos.mensajeExito) {
            return;
        }


        elementos.mensajeExito.textContent =
            mensaje;

        elementos.mensajeExito.hidden =
            false;

    }


    function mostrarInformativo(mensaje) {

        if (!elementos.mensajeInformativo) {
            return;
        }


        elementos.mensajeInformativo.textContent =
            mensaje;

        elementos.mensajeInformativo.hidden =
            false;

    }


    function manejarError(error) {

        console.error(
            "Error de gestión geoespacial:",
            error
        );


        const mensaje =
            error?.mensaje ||
            error?.message ||
            "Ocurrió un error inesperado.";


        mostrarError(mensaje);

    }


    /* =====================================================
       ESTADO DE BOTONES
    ====================================================== */

    function establecerProcesando(
        valor,
        textoBoton = null
    ) {

        procesando = valor;


        if (elementos.btnPreparar) {

            elementos.btnPreparar.disabled =
                valor;


            if (valor) {

                elementos.btnPreparar.innerHTML = `
                    <i class="bi bi-arrow-repeat"></i>
                    Procesando…
                `;

            } else {

                elementos.btnPreparar.innerHTML = `
                    <i class="bi bi-search"></i>
                    Preparar previsualización
                `;

            }

        }


        if (
            elementos.btnConfirmar &&
            valor
        ) {

            elementos.btnConfirmar.disabled =
                true;

        }


        if (
            textoBoton &&
            elementos.btnPreparar
        ) {

            elementos.btnPreparar.textContent =
                textoBoton;

        }

    }


    /* =====================================================
       PROYECTOS
    ====================================================== */

    async function cargarTodosLosProyectos() {

        const limite = 200;

        const resultados = [];

        let skip = 0;


        while (true) {

            const pagina =
                await window.ClienteAPI.get(
                    `/proyectos?skip=${skip}&limit=${limite}`
                );


            const registros =
                Array.isArray(pagina)
                    ? pagina
                    : [];


            resultados.push(
                ...registros
            );


            if (
                registros.length <
                limite
            ) {

                break;

            }


            skip += limite;

        }


        return resultados;

    }


    function llenarSelectorProyectos() {

        if (!elementos.selectorProyecto) {
            return;
        }


        elementos.selectorProyecto.innerHTML =
            `<option value="">
                Selecciona un proyecto
            </option>`;


        proyectos.forEach(proyecto => {

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


            elementos.selectorProyecto
                .appendChild(opcion);

        });

    }


    function seleccionarProyecto(idProyecto) {

        const id =
            Number(idProyecto);


        proyectoActivo =
            proyectos.find(
                proyecto =>
                    Number(
                        proyecto.id_proyecto
                    ) === id
            ) || null;


        importacionActiva =
            null;


        limpiarPreview();


        if (!proyectoActivo) {

            actualizarUrlProyecto(null);

            mostrarHistorialVacio(
                "Selecciona un proyecto",
                "Aquí aparecerán sus importaciones geoespaciales."
            );

            return;

        }


        actualizarUrlProyecto(
            proyectoActivo.id_proyecto
        );


        if (
            elementos.btnVerProyectoMapa
        ) {

            elementos.btnVerProyectoMapa.href =
                `/pages/mapa.html?id_proyecto=${encodeURIComponent(
                    proyectoActivo.id_proyecto
                )}`;

        }


        cargarHistorial().catch(
            manejarError
        );

    }


    /* =====================================================
       TIPO DE OBJETIVO
    ====================================================== */

    function actualizarTipoObjetivo() {

        const tipo =
            elementos.tipoObjetivo?.value;


        const requiereMapeo =
            tipo === "nucleo_agrario" ||
            tipo === "parcela";


        if (elementos.grupoMapeo) {

            elementos.grupoMapeo.hidden =
                !requiereMapeo;

        }


        if (
            elementos.campoIdDestino
        ) {

            elementos.campoIdDestino.required =
                requiereMapeo;


            if (!requiereMapeo) {

                elementos.campoIdDestino.value =
                    "";

            }

        }


        if (
            elementos.ayudaMapeo &&
            requiereMapeo
        ) {

            if (
                tipo === "nucleo_agrario"
            ) {

                elementos.ayudaMapeo.textContent =
                    "Escribe el nombre de la columna del archivo que contiene el id_nucleo correspondiente en SSALFER.";

            } else {

                elementos.ayudaMapeo.textContent =
                    "Escribe el nombre de la columna del archivo que contiene el id_parcela correspondiente en SSALFER.";

            }

        }

    }


    /* =====================================================
       ARCHIVO
    ====================================================== */

    function actualizarVistaArchivo() {

        if (!archivoActivo) {

            if (
                elementos.archivoSeleccionado
            ) {

                elementos.archivoSeleccionado.hidden =
                    true;

            }


            if (
                elementos.archivoNombre
            ) {

                elementos.archivoNombre.textContent =
                    "—";

            }


            if (
                elementos.archivoTamano
            ) {

                elementos.archivoTamano.textContent =
                    "—";

            }


            return;

        }


        if (
            elementos.archivoNombre
        ) {

            elementos.archivoNombre.textContent =
                archivoActivo.name;

        }


        if (
            elementos.archivoTamano
        ) {

            elementos.archivoTamano.textContent =
                formatearTamano(
                    archivoActivo.size
                );

        }


        if (
            elementos.archivoSeleccionado
        ) {

            elementos.archivoSeleccionado.hidden =
                false;

        }

    }


    function validarArchivo(archivo) {

        if (!archivo) {

            throw new Error(
                "Selecciona un archivo geoespacial."
            );

        }


        const extension =
            obtenerExtension(
                archivo.name
            );


        if (
            !EXTENSIONES_PERMITIDAS.has(
                extension
            )
        ) {

            throw new Error(
                "Formato no permitido. Utiliza GeoJSON, JSON, KML, GeoPackage o un Shapefile comprimido en ZIP."
            );

        }


        return true;

    }


    function seleccionarArchivo(archivo) {

        limpiarMensajes();


        try {

            validarArchivo(
                archivo
            );


            archivoActivo =
                archivo;


            actualizarVistaArchivo();

        } catch (error) {

            archivoActivo =
                null;


            if (
                elementos.inputArchivo
            ) {

                elementos.inputArchivo.value =
                    "";

            }


            actualizarVistaArchivo();

            mostrarError(
                error.message
            );

        }

    }


    function quitarArchivo() {

        archivoActivo =
            null;


        if (
            elementos.inputArchivo
        ) {

            elementos.inputArchivo.value =
                "";

        }


        actualizarVistaArchivo();

    }


    /* =====================================================
       IMPORTACIONES - API
    ====================================================== */

    async function obtenerImportacionesProyecto(
        idProyecto
    ) {

        const limite = 200;

        const importaciones = [];

        let skip = 0;


        while (true) {

            const pagina =
                await window.ClienteAPI.get(
                    `/proyectos/${idProyecto}/importaciones?skip=${skip}&limit=${limite}`
                );


            const registros =
                Array.isArray(pagina)
                    ? pagina
                    : [];


            importaciones.push(
                ...registros
            );


            if (
                registros.length <
                limite
            ) {

                break;

            }


            skip += limite;

        }


        return importaciones;

    }


    async function obtenerImportacion(
        idImportacion
    ) {

        return window.ClienteAPI.get(
            `/importaciones/${idImportacion}`
        );

    }


    async function obtenerFeatures(
        idImportacion
    ) {

        const limite = 500;

        const features = [];

        let skip = 0;


        while (true) {

            const pagina =
                await window.ClienteAPI.get(
                    `/importaciones/${idImportacion}/features?skip=${skip}&limit=${limite}`
                );


            const registros =
                Array.isArray(pagina)
                    ? pagina
                    : [];


            features.push(
                ...registros
            );


            if (
                registros.length <
                limite
            ) {

                break;

            }


            skip += limite;

        }


        return features;

    }


    /* =====================================================
       HISTORIAL
    ====================================================== */

    function mostrarHistorialVacio(
        titulo,
        descripcion
    ) {

        if (
            elementos.listaImportaciones
        ) {

            elementos.listaImportaciones.innerHTML =
                "";

            elementos.listaImportaciones.hidden =
                true;

        }


        if (
            elementos.importacionesVacio
        ) {

            elementos.importacionesVacio.innerHTML = `
                <i class="bi bi-folder2-open"></i>

                <strong>
                    ${escaparTexto(titulo)}
                </strong>

                <p>
                    ${escaparTexto(descripcion)}
                </p>
            `;


            elementos.importacionesVacio.hidden =
                false;

        }

    }


    function crearItemHistorial(
        importacion
    ) {

        const contenedor =
            document.createElement(
                "article"
            );


        contenedor.className =
            "geoespacial-importacion-item";


        const estado =
            etiquetaEstado(
                importacion.estado
            );


        contenedor.innerHTML = `

            <div class="geoespacial-importacion-principal">

                <div class="geoespacial-importacion-icono">

                    <i class="bi bi-file-earmark-map"></i>

                </div>


                <div class="geoespacial-importacion-info">

                    <strong>
                        ${escaparTexto(
                            importacion.nombre_original
                        )}
                    </strong>


                    <span>
                        ${escaparTexto(
                            etiquetaTipo(
                                importacion.tipo_objetivo
                            )
                        )}
                    </span>


                    <small>
                        ${escaparTexto(
                            formatearFechaHora(
                                importacion.fecha_carga ||
                                importacion.creado_en
                            )
                        )}
                    </small>

                </div>

            </div>


            <div class="geoespacial-importacion-resumen">

                <span>
                    ${escaparTexto(estado)}
                </span>

                <small>
                    ${numero(importacion.validos)}
                    válidos ·
                    ${numero(importacion.advertencias)}
                    advertencias ·
                    ${numero(importacion.errores)}
                    errores
                </small>

            </div>


            <button
                type="button"
                class="btn-secundario js-ver-importacion"
                data-id-importacion="${Number(
                    importacion.id_importacion
                )}"
            >
                Ver detalle
            </button>
        `;


        return contenedor;

    }


    async function cargarHistorial() {

        if (!proyectoActivo) {

            mostrarHistorialVacio(
                "Selecciona un proyecto",
                "Aquí aparecerán sus importaciones geoespaciales."
            );

            return;

        }


        if (
            elementos.importacionesVacio
        ) {

            elementos.importacionesVacio.innerHTML = `
                <i class="bi bi-arrow-repeat"></i>

                <strong>
                    Consultando importaciones…
                </strong>
            `;

            elementos.importacionesVacio.hidden =
                false;

        }


        if (
            elementos.listaImportaciones
        ) {

            elementos.listaImportaciones.hidden =
                true;

        }


        const importaciones =
            await obtenerImportacionesProyecto(
                proyectoActivo.id_proyecto
            );


        if (
            importaciones.length === 0
        ) {

            mostrarHistorialVacio(
                "Sin importaciones",
                "Este proyecto todavía no tiene información geoespacial importada."
            );

            return;

        }


        if (
            elementos.listaImportaciones
        ) {

            elementos.listaImportaciones.innerHTML =
                "";


            importaciones.forEach(
                importacion => {

                    elementos.listaImportaciones.appendChild(
                        crearItemHistorial(
                            importacion
                        )
                    );

                }
            );


            elementos.listaImportaciones.hidden =
                false;

        }


        if (
            elementos.importacionesVacio
        ) {

            elementos.importacionesVacio.hidden =
                true;

        }

    }


    /* =====================================================
       PREVIEW
    ====================================================== */

    function limpiarPreview() {

        importacionActiva =
            null;


        if (
            elementos.seccionPreview
        ) {

            elementos.seccionPreview.hidden =
                true;

        }


        if (
            elementos.tablaFeatures
        ) {

            elementos.tablaFeatures.innerHTML =
                "";

        }


        if (
            elementos.aceptarAdvertencias
        ) {

            elementos.aceptarAdvertencias.checked =
                false;

        }


        if (
            elementos.btnConfirmar
        ) {

            elementos.btnConfirmar.disabled =
                true;

        }


        if (
            elementos.btnVerProyectoMapa
        ) {

            elementos.btnVerProyectoMapa.hidden =
                true;

        }

    }


    function configurarEstadoPreview(
        importacion
    ) {

        if (!elementos.previewEstado) {
            return;
        }


        elementos.previewEstado.textContent =
            etiquetaEstado(
                importacion.estado
            );


        elementos.previewEstado.dataset.estado =
            importacion.estado || "";

    }


    function llenarDatosPreview(
        importacion
    ) {

        elementos.previewNombreArchivo.textContent =
            texto(
                importacion.nombre_original,
                "Archivo geoespacial"
            );


        configurarEstadoPreview(
            importacion
        );


        elementos.previewFormato.textContent =
            texto(
                importacion.formato_detectado
            );


        elementos.previewObjetivo.textContent =
            etiquetaTipo(
                importacion.tipo_objetivo
            );


        elementos.previewCrsOriginal.textContent =
            texto(
                importacion.crs_original
            );


        elementos.previewCrsDestino.textContent =
            texto(
                importacion.crs_destino
            );


        elementos.previewFuente.textContent =
            texto(
                importacion.fuente
            );


        elementos.previewFechaFuente.textContent =
            formatearFecha(
                importacion.fecha_fuente
            );


        elementos.previewSha256.textContent =
            texto(
                importacion.sha256
            );


        elementos.previewTotal.textContent =
            String(
                numero(
                    importacion.total_features
                )
            );


        elementos.previewValidos.textContent =
            String(
                numero(
                    importacion.validos
                )
            );


        elementos.previewAdvertencias.textContent =
            String(
                numero(
                    importacion.advertencias
                )
            );


        elementos.previewErrores.textContent =
            String(
                numero(
                    importacion.errores
                )
            );


        elementos.previewImportados.textContent =
            String(
                numero(
                    importacion.importados
                )
            );

    }


    function observacionesFeature(
        feature
    ) {

        const observaciones = [];


        const errores =
            Array.isArray(feature.errores)
                ? feature.errores
                : [];


        const advertencias =
            Array.isArray(feature.advertencias)
                ? feature.advertencias
                : [];


        errores.forEach(error => {

            if (
                typeof error === "string"
            ) {

                observaciones.push(
                    `Error: ${error}`
                );

            } else {

                observaciones.push(
                    `Error: ${JSON.stringify(error)}`
                );

            }

        });


        advertencias.forEach(
            advertencia => {

                if (
                    typeof advertencia ===
                    "string"
                ) {

                    observaciones.push(
                        `Advertencia: ${advertencia}`
                    );

                } else {

                    observaciones.push(
                        `Advertencia: ${JSON.stringify(
                            advertencia
                        )}`
                    );

                }

            }
        );


        if (
            observaciones.length === 0
        ) {

            return "Sin observaciones";

        }


        return observaciones.join(" | ");

    }


    function renderizarFeatures(
        features
    ) {

        if (!elementos.tablaFeatures) {
            return;
        }


        elementos.tablaFeatures.innerHTML =
            "";


        if (
            !Array.isArray(features) ||
            features.length === 0
        ) {

            if (
                elementos.featuresVacio
            ) {

                elementos.featuresVacio.hidden =
                    false;

            }

            return;

        }


        if (
            elementos.featuresVacio
        ) {

            elementos.featuresVacio.hidden =
                true;

        }


        features.forEach(feature => {

            const fila =
                document.createElement(
                    "tr"
                );


            const indice =
                feature.indice_feature ??
                "—";


            const capa =
                feature.capa_origen ||
                "—";


            const geometria =
                feature.tipo_geometria ||
                "—";


            const estado =
                feature.estado ||
                "—";


            const observaciones =
                observacionesFeature(
                    feature
                );


            [
                indice,
                capa,
                geometria,
                estado,
                observaciones

            ].forEach(valor => {

                const celda =
                    document.createElement(
                        "td"
                    );


                celda.textContent =
                    String(valor);


                fila.appendChild(
                    celda
                );

            });


            elementos.tablaFeatures.appendChild(
                fila
            );

        });

    }


    function actualizarConfirmacion() {

        if (
            !importacionActiva ||
            !elementos.btnConfirmar
        ) {

            return;

        }


        const estado =
            importacionActiva.estado;


        const errores =
            numero(
                importacionActiva.errores
            );


        const advertencias =
            numero(
                importacionActiva.advertencias
            );


        /*
         * Una importación ya completa no debe confirmarse otra vez.
         */

        if (
            estado === "completo"
        ) {

            elementos.btnConfirmar.disabled =
                true;


            if (
                elementos.contenedorAceptarAdvertencias
            ) {

                elementos.contenedorAceptarAdvertencias.hidden =
                    true;

            }


            if (
                elementos.btnVerProyectoMapa
            ) {

                elementos.btnVerProyectoMapa.hidden =
                    false;

            }


            return;

        }


        /*
         * Si el backend encontró errores, no se permite confirmar.
         */

        if (
            errores > 0 ||
            estado === "error"
        ) {

            elementos.btnConfirmar.disabled =
                true;


            if (
                elementos.contenedorAceptarAdvertencias
            ) {

                elementos.contenedorAceptarAdvertencias.hidden =
                    true;

            }


            return;

        }


        /*
         * Sólo se confirma después de previsualización.
         */

        if (
            estado !== "previsualizado"
        ) {

            elementos.btnConfirmar.disabled =
                true;


            return;

        }


        /*
         * Advertencias requieren aceptación explícita.
         */

        if (
            advertencias > 0
        ) {

            if (
                elementos.contenedorAceptarAdvertencias
            ) {

                elementos.contenedorAceptarAdvertencias.hidden =
                    false;

            }


            elementos.btnConfirmar.disabled =
                !elementos.aceptarAdvertencias
                    ?.checked;


            return;

        }


        if (
            elementos.contenedorAceptarAdvertencias
        ) {

            elementos.contenedorAceptarAdvertencias.hidden =
                true;

        }


        elementos.btnConfirmar.disabled =
            false;

    }


    async function mostrarPreview(
        importacion
    ) {

        importacionActiva =
            importacion;


        limpiarMensajes();


        llenarDatosPreview(
            importacion
        );


        if (
            elementos.seccionPreview
        ) {

            elementos.seccionPreview.hidden =
                false;

        }


        if (
            proyectoActivo &&
            elementos.btnVerProyectoMapa
        ) {

            elementos.btnVerProyectoMapa.href =
                `/pages/mapa.html?id_proyecto=${encodeURIComponent(
                    proyectoActivo.id_proyecto
                )}`;

        }


        const features =
            await obtenerFeatures(
                importacion.id_importacion
            );


        renderizarFeatures(
            features
        );


        actualizarConfirmacion();


        elementos.seccionPreview
            ?.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

    }


    async function abrirImportacion(
        idImportacion
    ) {

        limpiarMensajes();


        mostrarInformativo(
            "Consultando importación…"
        );


        try {

            const importacion =
                await obtenerImportacion(
                    idImportacion
                );


            limpiarMensajes();


            await mostrarPreview(
                importacion
            );

        } catch (error) {

            limpiarMensajes();

            manejarError(
                error
            );

        }

    }


    /* =====================================================
       CREAR IMPORTACIÓN
    ====================================================== */

    function validarFormulario() {

        const idProyectoSeleccionado =
            obtenerIdProyectoSeleccionado();


        if (!idProyectoSeleccionado) {

            throw new Error(
                "Selecciona el proyecto al que pertenece la información geográfica."
            );

        }


        /*
        * Sincronizamos proyectoActivo cuando podamos encontrarlo,
        * pero ya no dependemos de él para poder hacer la carga.
        */
        const proyectoEncontrado =
            proyectos.find(
                proyecto =>
                    Number(proyecto.id_proyecto) ===
                    idProyectoSeleccionado
            );


        if (proyectoEncontrado) {

            proyectoActivo =
                proyectoEncontrado;

        }


        const tipo =
            elementos.tipoObjetivo?.value;


        if (
            !TIPOS_OBJETIVO.has(tipo)
        ) {

            throw new Error(
                "Selecciona un tipo de información válido."
            );

        }


        const fuente =
            elementos.fuente
                ?.value
                .trim();


        if (!fuente) {

            throw new Error(
                "Indica la fuente cartográfica."
            );

        }


        validarArchivo(
            archivoActivo
        );


        if (
            tipo !== "trazo_proyecto"
        ) {

            const campo =
                elementos.campoIdDestino
                    ?.value
                    .trim();


            if (!campo) {

                throw new Error(
                    tipo === "parcela"
                        ? "Indica el nombre de la columna que contiene el id_parcela."
                        : "Indica el nombre de la columna que contiene el id_nucleo."
                );

            }

        }


        /*
        * Ahora devolvemos explícitamente el proyecto
        * que realmente debe utilizarse.
        */
        return idProyectoSeleccionado;
    }


    function construirFormData() {

        const tipo =
            elementos.tipoObjetivo.value;


        const formData =
            new FormData();


        formData.append(
            "tipo_objetivo",
            tipo
        );


        formData.append(
            "fuente",
            elementos.fuente.value.trim()
        );


        if (
            elementos.fechaFuente
                ?.value
        ) {

            formData.append(
                "fecha_fuente",
                elementos.fechaFuente.value
            );

        }


        let mapeo = {};


        if (
            tipo !== "trazo_proyecto"
        ) {

            mapeo = {

                id_destino:
                    elementos.campoIdDestino
                        .value
                        .trim()

            };

        }


        formData.append(
            "mapeo",
            JSON.stringify(
                mapeo
            )
        );


        formData.append(
            "archivo",
            archivoActivo,
            archivoActivo.name
        );


        return formData;

    }


    async function prepararImportacion(
        evento
    ) {

        evento.preventDefault();


        if (procesando) {
            return;
        }


        limpiarMensajes();


        try {

            const idProyectoSeleccionado =
                validarFormulario();


            establecerProcesando(
                true
            );


            const formData =
                construirFormData();


            const importacion =
                await window.ClienteAPI.post(
                    `/proyectos/${idProyectoSeleccionado}/importaciones`,
                    formData
                );


            importacionActiva =
                importacion;


            if (
                importacion.estado ===
                "completo"
            ) {

                mostrarInformativo(
                    "Este archivo ya cuenta con una importación completa para el proyecto. Se muestra el registro existente."
                );

            } else if (
                importacion.estado ===
                "error"
            ) {

                mostrarError(
                    "El backend procesó el archivo, pero encontró errores que impiden su importación."
                );

            } else {

                mostrarExito(
                    "El archivo fue procesado. Revisa la previsualización antes de confirmar la importación."
                );

            }


            await mostrarPreview(
                importacion
            );


            await cargarHistorial();


        } catch (error) {

            manejarError(
                error
            );

        } finally {

            establecerProcesando(
                false
            );

        }

    }


    /* =====================================================
       CONFIRMAR IMPORTACIÓN
    ====================================================== */

    async function confirmarImportacion() {

        if (
            !importacionActiva ||
            procesando
        ) {

            return;

        }


        limpiarMensajes();


        const advertencias =
            numero(
                importacionActiva.advertencias
            );


        if (
            advertencias > 0 &&
            !elementos.aceptarAdvertencias
                ?.checked
        ) {

            mostrarError(
                "Debes aceptar las advertencias antes de confirmar la importación."
            );

            return;

        }


        if (
            numero(
                importacionActiva.errores
            ) > 0
        ) {

            mostrarError(
                "Esta importación contiene errores y no puede confirmarse."
            );

            return;

        }


        const continuar =
            window.confirm(
                "¿Confirmas la incorporación de estas geometrías a la información vigente del proyecto?"
            );


        if (!continuar) {
            return;
        }


        procesando = true;


        if (
            elementos.btnConfirmar
        ) {

            elementos.btnConfirmar.disabled =
                true;


            elementos.btnConfirmar.innerHTML = `
                <i class="bi bi-arrow-repeat"></i>
                Confirmando…
            `;

        }


        try {

            const actualizada =
                await window.ClienteAPI.post(
                    `/importaciones/${importacionActiva.id_importacion}/confirmar`,
                    {
                        confirmacion_explicita: true,

                        aceptar_advertencias:
                            advertencias > 0
                    }
                );


            importacionActiva =
                actualizada;


            llenarDatosPreview(
                actualizada
            );


            mostrarExito(
                "La importación fue confirmada correctamente y la información geoespacial quedó incorporada al proyecto."
            );


            if (
                elementos.btnVerProyectoMapa
            ) {

                elementos.btnVerProyectoMapa.hidden =
                    false;

            }


            await Promise.all([
                cargarHistorial(),

                obtenerFeatures(
                    actualizada.id_importacion
                ).then(
                    renderizarFeatures
                )
            ]);


            actualizarConfirmacion();


        } catch (error) {

            manejarError(
                error
            );

        } finally {

            procesando =
                false;


            if (
                elementos.btnConfirmar
            ) {

                elementos.btnConfirmar.innerHTML = `
                    <i class="bi bi-check-circle"></i>
                    Confirmar importación
                `;

            }


            actualizarConfirmacion();

        }

    }


    /* =====================================================
       EVENTOS - SELECTOR PROYECTO
    ====================================================== */

    elementos.selectorProyecto
        ?.addEventListener(
            "change",
            evento => {

                limpiarMensajes();


                const id =
                    Number(
                        evento.target.value
                    );


                if (
                    !Number.isInteger(id) ||
                    id <= 0
                ) {

                    proyectoActivo =
                        null;


                    seleccionarProyecto(
                        null
                    );


                    return;

                }


                seleccionarProyecto(
                    id
                );

            }
        );



            /* =====================================================
       EVENTOS - MOSTRAR/OCULTAR NUEVA IMPORTACIÓN
    ====================================================== */

    elementos.btnCrearImportacion
        ?.addEventListener(
            "click",
            () => {

                if (elementos.seccionNuevaImportacion) {

                    elementos.seccionNuevaImportacion.hidden =
                        false;

                    elementos.seccionNuevaImportacion.scrollIntoView(
                        { behavior: "smooth", block: "start" }
                    );

                }

            }
        );


    elementos.btnCerrarImportacion
        ?.addEventListener(
            "click",
            () => {

                if (elementos.seccionNuevaImportacion) {

                    elementos.seccionNuevaImportacion.hidden =
                        true;

                }

            }
        );


    /* =====================================================
       EVENTOS - TIPO
    ====================================================== */

    elementos.tipoObjetivo
        ?.addEventListener(
            "change",
            actualizarTipoObjetivo
        );


    /* =====================================================
       EVENTOS - ARCHIVO
    ====================================================== */

    elementos.inputArchivo
        ?.addEventListener(
            "change",
            evento => {

                const archivo =
                    evento.target.files?.[0];


                if (archivo) {

                    seleccionarArchivo(
                        archivo
                    );

                }

            }
        );


    elementos.btnQuitarArchivo
        ?.addEventListener(
            "click",
            quitarArchivo
        );


    /* =====================================================
       DRAG & DROP
    ====================================================== */

    if (
        elementos.zonaArchivo &&
        elementos.inputArchivo
    ) {

        [
            "dragenter",
            "dragover"

        ].forEach(tipoEvento => {

            elementos.zonaArchivo.addEventListener(
                tipoEvento,
                evento => {

                    evento.preventDefault();

                    evento.stopPropagation();

                    elementos.zonaArchivo.classList.add(
                        "arrastrando"
                    );

                }
            );

        });


        [
            "dragleave",
            "drop"

        ].forEach(tipoEvento => {

            elementos.zonaArchivo.addEventListener(
                tipoEvento,
                evento => {

                    evento.preventDefault();

                    evento.stopPropagation();

                    elementos.zonaArchivo.classList.remove(
                        "arrastrando"
                    );

                }
            );

        });


        elementos.zonaArchivo.addEventListener(
            "drop",
            evento => {

                const archivo =
                    evento.dataTransfer
                        ?.files?.[0];


                if (!archivo) {
                    return;
                }


                seleccionarArchivo(
                    archivo
                );

            }
        );

    }


    /* =====================================================
       EVENTOS - FORM
    ====================================================== */

    elementos.form
        ?.addEventListener(
            "submit",
            prepararImportacion
        );


    /* =====================================================
       EVENTOS - CONFIRMACIÓN
    ====================================================== */

    elementos.aceptarAdvertencias
        ?.addEventListener(
            "change",
            actualizarConfirmacion
        );


    elementos.btnConfirmar
        ?.addEventListener(
            "click",
            confirmarImportacion
        );


    /* =====================================================
       EVENTOS - HISTORIAL
    ====================================================== */

    elementos.listaImportaciones
        ?.addEventListener(
            "click",
            evento => {

                const boton =
                    evento.target.closest(
                        ".js-ver-importacion"
                    );


                if (!boton) {
                    return;
                }


                const id =
                    Number(
                        boton.dataset.idImportacion
                    );


                if (
                    Number.isInteger(id) &&
                    id > 0
                ) {

                    abrirImportacion(
                        id
                    );

                }

            }
        );


    elementos.btnActualizarImportaciones
        ?.addEventListener(
            "click",
            () => {

                limpiarMensajes();


                cargarHistorial()
                    .catch(
                        manejarError
                    );

            }
        );


    /* =====================================================
       INICIO
    ====================================================== */

    async function iniciar() {

        limpiarMensajes();

        actualizarTipoObjetivo();

        actualizarVistaArchivo();

        limpiarPreview();


        try {

            proyectos =
                await cargarTodosLosProyectos();


            llenarSelectorProyectos();


            const idProyectoUrl =
                obtenerIdProyectoUrl();


            if (idProyectoUrl) {

                const existe =
                    proyectos.some(
                        proyecto =>
                            Number(
                                proyecto.id_proyecto
                            ) === idProyectoUrl
                    );


                if (existe) {

                    elementos.selectorProyecto.value =
                        String(
                            idProyectoUrl
                        );


                    seleccionarProyecto(
                        idProyectoUrl
                    );


                    return;

                }

            }


            mostrarHistorialVacio(
                "Selecciona un proyecto",
                "Aquí aparecerán sus importaciones geoespaciales."
            );


        } catch (error) {

            manejarError(
                error
            );

        }

    }


    iniciar();

});