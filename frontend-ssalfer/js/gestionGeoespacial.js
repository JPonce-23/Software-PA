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

document.addEventListener("DOMContentLoaded", async () => {

    "use strict";

    const sesion = await window.SSALFER_SESION_LISTA;
    if (!["admin", "geografo"].includes(sesion?.user?.rol)) return;


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
        "ddv", "nucleos", "parcelas",
        "nucleo_agrario",
        "parcela"
    ]);


    /* =====================================================
       ESTADO
    ====================================================== */

    let proyectos = [];

    let proyectoActivo = null;
    let revisionProyecto = 0;
    let revisionHistorial = 0;
    let revisionPreview = 0;

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
            derecho_via_proyecto: "Derecho de vía", nucleo_agrario_gpkg: "Núcleos agrarios", parcela_gpkg: "Parcelas",

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
        if (elementos.selectorProyecto) elementos.selectorProyecto.disabled = valor;


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


        return window.ProyectosAPI.ordenar(resultados);

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
        window.SSALFER_GIS.cambiarProyecto(idProyecto);
        ++revisionProyecto;
        ++revisionHistorial;
        ++revisionPreview;

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


        const alcance = document.getElementById("alcanceEntregaGis");
        const ayudaTipo = document.getElementById("ayudaTipoGeoespacial");
        const explicacionTipo = {
            trazo_proyecto: "El trazo es la línea del recorrido; el derecho de vía es el polígono de su franja de terreno. Si solo tienes DDV, núcleos y parcelas, no necesitas cargar un trazo. El trazo debe contener líneas.",
            ddv: "Carga los polígonos del derecho de vía del proyecto en un archivo GPKG.",
            nucleos: "Primero registra y vincula los núcleos al proyecto. El sistema compara nombre, municipio, entidad y tipo de núcleo, o su clave oficial cuando esté disponible. Una diferencia puede dejar el polígono sin coincidencia; no significa que su geometría sea inválida.",
            parcelas: "Primero registra las parcelas y su relación con los núcleos del proyecto. Se comparan los datos del núcleo y el número de parcela. Cargar el GPKG no crea automáticamente esos registros; después debes revisar y confirmar sus asociaciones."
        }[tipo] || "Selecciona qué vas a cargar: derecho de vía, núcleos o parcelas.";
        if (ayudaTipo) ayudaTipo.textContent = {
            ddv: "Carga el archivo GPKG del derecho de vía.",
            nucleos: "Los núcleos deben estar registrados y vinculados al proyecto.",
            parcelas: "Las parcelas deben estar registradas y relacionadas con los núcleos."
        }[tipo] || "Selecciona qué vas a cargar: derecho de vía, núcleos o parcelas.";
        const detalleTipo = document.getElementById("detalleTipoGeoespacial");
        detalleTipo.textContent = explicacionTipo;
        detalleTipo.closest("details").open = false;
        alcance.closest("label").hidden = !["nucleos", "parcelas"].includes(tipo);
        alcance.required = ["nucleos", "parcelas"].includes(tipo);
        elementos.inputArchivo.accept = tipo === "trazo_proyecto" ? ".geojson,.json,.kml,.gpkg,.zip" : ".gpkg";

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

    async function obtenerImportacion(idImportacion, incluirInactivas=false) {
        return window.GeoespacialAPI.obtener(idImportacion,{incluir_inactivas:incluirInactivas});
    }

    async function obtenerFeatures(idImportacion, incluirInactivas=false) {
        const features=[];
        for(let skip=0;;skip+=500){const p=await window.GeoespacialAPI.paginaElementos(idImportacion,{skip,limit:500},{incluir_inactivas:incluirInactivas});features.push(...p.items);if(window.GeoespacialAPI.fin(p,skip,500))return features;}
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
                    ${escaparTexto(estado)}${["nucleo_agrario_gpkg","parcela_gpkg"].includes(importacion.tipo_objetivo)?` · Entrega ${importacion.alcance_entrega==="completa"?"completa":importacion.alcance_entrega==="parcial"?"parcial":"sin alcance informado"}`:""}<span class="gis-estado-publicacion">${numero(importacion.importados)} confirmados</span>
                </span>

                <small>
                    ${numero(importacion.validos)}
                    válidos ·
                    ${numero(importacion.advertencias)}
                    advertencias ·
                    ${numero(importacion.errores)}
                    errores de geometría o datos
                </small>

            </div>


            <button
                type="button"
                class="btn-secundario js-ver-importacion"
                data-id-importacion="${Number(
                    importacion.id_importacion
                )}"
            >
                Consultar carga
            </button>
        `;


        const consultar=contenedor.querySelector('.js-ver-importacion');
        consultar.dataset.inactiva=String(importacion.activo===false);
        if(importacion.activo===false){
            contenedor.classList.add('gis-inactiva');
            const baja=document.createElement('p');baja.className='gis-etiqueta';
            baja.textContent=`Dada de baja · Sólo lectura. ${formatearFechaHora(importacion.fecha_baja)}. Motivo: ${importacion.motivo_baja || 'No disponible'}`;
            contenedor.prepend(baja);
        } else if(window.SSALFER_GIS.puedeEditar()) {
            const boton=document.createElement('button');boton.type='button';boton.className='btn-secundario js-baja-importacion';boton.textContent='Dar de baja esta importación';
            boton.addEventListener('click',()=>darDeBaja(importacion));contenedor.append(boton);
        }
        const estadoCarga=document.createElement('details');
        estadoCarga.classList.add('gis-ayuda');
        const claseEstado=Number(importacion.errores)>0 || importacion.estado==='error' ? 'gis-etiqueta gis-error' : 'gis-etiqueta gis-informacion';
        const explicacionEstado=Number(importacion.errores)>0 || importacion.estado==='error' ? '✖ Hay errores de carga, geometría o datos: consulta el detalle.' : 'ℹ Sin errores informados. Las coincidencias administrativas se consultan en el detalle.';
        const rotuloEstado=Number(importacion.errores)>0 || importacion.estado==='error' ? '✖ Con errores' : 'ℹ Acerca de esta carga';
        estadoCarga.innerHTML=`<summary><span class="${claseEstado}">${rotuloEstado}</span></summary><p>${escaparTexto(explicacionEstado)}</p><p>${numero(importacion.importados)} elementos confirmados en esta carga. Consultar el detalle no activa ni reemplaza una versión del mapa.</p>`;
        contenedor.querySelector('.geoespacial-importacion-resumen').after(estadoCarga);
        return contenedor;

    }


    async function darDeBaja(importacion) {
        if(procesando || window.SSALFER_GIS.ocupado() || !window.SSALFER_GIS.puedeEditar() || importacion.activo===false) return;
        const contexto=revisionProyecto, id=importacion.id_importacion;
        await window.SSALFER_GIS.exclusivo(async()=>{
            ++revisionPreview; // Invalida consultas abiertas antes de iniciar la baja.
            establecerProcesando(true);
            try {
                const resultado=await window.SSALFER_GESTION.formulario({
                    titulo:'Dar de baja esta importación',
                    introduccion:`Vas a dar de baja ${importacion.nombre_original}. Atención: los polígonos de esta carga que sigan vigentes dejarán de verse en el mapa. Las geometrías que ya fueron reemplazadas por cargas posteriores no se cambiarán y no se reactivarán versiones antiguas. Si retiras el DDV, el proyecto puede quedar sin derecho de vía visible hasta confirmar otro. Se conserva el archivo y todo su historial; los núcleos y parcelas administrativos no se eliminan.`,
                    campos:[{nombre:'motivo',etiqueta:'Motivo de la baja',tipo:'textarea',requerido:true,maximo:500,ayuda:'Escribe entre 3 y 500 caracteres.'},{nombre:'aceptar',etiqueta:'Confirmo la baja y el retiro del mapa de sus geometrías vigentes',tipo:'checkbox',requerido:true}],
                    validar:d=>!d.motivo || d.motivo.length<3?'Escribe un motivo de al menos 3 caracteres.':null,
                    guardar:async d=>{
                        if(contexto!==revisionProyecto || importacion.activo===false)throw Error('La carga ya no está disponible para esta acción.');
                        return window.GeoespacialAPI.baja(id,{motivo:d.motivo});
                    }
                });
                if(!resultado || contexto!==revisionProyecto)return;
                Object.assign(importacion,resultado);
                const abierta=importacionActiva?.id_importacion===id;
                if(abierta)await mostrarPreview(resultado);
                await cargarHistorial();
                mostrarExito('La baja quedó registrada y sus geometrías vigentes se retiraron del mapa. Actualiza el mapa si lo tienes abierto. El archivo sigue disponible en Activas y dadas de baja.');
            } finally {establecerProcesando(false);actualizarConfirmacion();}
        });
    }
    let cacheHistorial = null;
    async function cargarHistorial(skip=0, actualizar=true) {
        const revision=++revisionHistorial, pid=proyectoActivo?.id_proyecto;
        const region=document.querySelector('.geoespacial-historial');
        const aviso=document.getElementById('estadoFiltrosHistorial');
        document.getElementById('detalleFiltrosHistorial').textContent='Las fechas usan la hora local del navegador.';
        const vigente=()=>revision===revisionHistorial && pid===proyectoActivo?.id_proyecto;
        document.getElementById('paginacionImportaciones')?.remove();
        if(!pid){cacheHistorial=null;region.setAttribute('aria-busy','false');aviso.textContent='Selecciona un proyecto para consultar el historial.';mostrarHistorialVacio('Selecciona un proyecto','Aquí aparecerán sus importaciones geoespaciales.');return;}
        const valor=id=>document.getElementById(id).value;
        const disponibilidad=valor('filtroHistorialDisponibilidad'),incluirInactivas=!!disponibilidad;
        const estado=valor('filtroHistorialEstado'),tipo=valor('filtroHistorialTipo'),desde=valor('filtroHistorialDesde'),hasta=valor('filtroHistorialHasta');
        elementos.listaImportaciones.hidden=true;
        if(desde && hasta && desde>hasta){region.setAttribute('aria-busy','false');aviso.textContent='La fecha Desde debe ser anterior o igual a Hasta.';mostrarHistorialVacio('Revisa las fechas','Corrige el intervalo para consultar el historial.');return;}
        region.setAttribute('aria-busy','true');aviso.textContent='Cargando historial…';
        try {
            if(actualizar || cacheHistorial?.proyecto!==pid || cacheHistorial.incluirInactivas!==incluirInactivas){
                const items=[];
                for(let offset=0;;offset+=200){
                    const p=await window.GeoespacialAPI.paginaImportaciones(pid,{skip:offset,limit:200},{incluir_inactivas:incluirInactivas});
                    if(!vigente())return;
                    items.push(...p.items);
                    aviso.textContent=`Cargando historial… (${items.length} recibidas)`;
                    if(window.GeoespacialAPI.fin(p,offset,200))break;
                }
                cacheHistorial={proyecto:pid,incluirInactivas,items};
            }
            if(!vigente())return;
            const dia=r=>{const f=new Date(r.fecha_carga || r.creado_en);return Number.isNaN(f.getTime())?'':`${f.getFullYear()}-${String(f.getMonth()+1).padStart(2,'0')}-${String(f.getDate()).padStart(2,'0')}`;};
            const filtradas=cacheHistorial.items.filter(r=>(disponibilidad==='inactivas'?r.activo===false:incluirInactivas || r.activo!==false) && (!estado || r.estado===estado) && (!tipo || r.tipo_objetivo===tipo) && (!desde || dia(r)>=desde) && (!hasta || (dia(r) && dia(r)<=hasta)));
            const inicio=Math.min(skip,Math.max(0,Math.floor((filtradas.length-1)/25)*25));
            const items=filtradas.slice(inicio,inicio+25);
            elementos.listaImportaciones.replaceChildren(...items.map(crearItemHistorial));
            elementos.listaImportaciones.hidden=!items.length;
            elementos.importacionesVacio.hidden=!!items.length;
            if(!items.length)mostrarHistorialVacio('Sin resultados con estos filtros','Prueba otro estado, tipo o intervalo de fechas.');
            aviso.textContent=filtradas.length===cacheHistorial.items.length ? 'Historial actualizado' : 'Filtros aplicados';
            document.getElementById('detalleFiltrosHistorial').textContent=`${filtradas.length} de ${cacheHistorial.items.length} cargas disponibles coinciden. Las fechas usan la hora local del navegador.`;
            const controles=document.createElement('div');controles.id='paginacionImportaciones';controles.className='ssalfer-gestion-barra';
            for(const [nombre,offset,disabled] of [['Anterior',-25,inicio===0],['Siguiente',25,inicio+25>=filtradas.length]]){
                const boton=document.createElement('button');boton.type='button';boton.className='btn-secundario';boton.textContent=nombre;boton.disabled=disabled;
                boton.setAttribute('aria-label',`${nombre}: página del historial de importaciones`);
                boton.onclick=async()=>{await cargarHistorial(inicio+offset,false);if(pid===proyectoActivo?.id_proyecto){elementos.listaImportaciones.scrollTop=0;const inicioTabla=region.querySelector('h2')||region;inicioTabla.tabIndex=-1;inicioTabla.focus({preventScroll:true});inicioTabla.scrollIntoView({block:'start',behavior:'smooth'});}};controles.append(boton);
            }
            const total=document.createElement('span');total.textContent=`${items.length?inicio+1:0}–${inicio+items.length} de ${filtradas.length} importaciones`;controles.append(total);elementos.listaImportaciones.after(controles);
        }catch(err){if(vigente()){cacheHistorial=null;aviso.textContent='No se pudo consultar el historial completo. Pulsa Actualizar importaciones para reintentar.';mostrarHistorialVacio('Historial no disponible','Vuelve a consultar las importaciones.');document.getElementById('detalleFiltrosHistorial').textContent='No se muestran resultados parciales como si fueran el historial completo.';manejarError(err);}}
        finally{if(vigente())region.setAttribute('aria-busy','false');}
    }
    document.getElementById('filtrosHistorial').addEventListener('change',()=>cargarHistorial(0,false));
    document.getElementById('limpiarFiltrosHistorial').addEventListener('click',()=>{
        document.querySelectorAll('#filtrosHistorial input, #filtrosHistorial select:not([disabled])').forEach(el=>el.value='');
        cargarHistorial(0,false);
    });

    /* =====================================================
       PREVIEW
    ====================================================== */

    function limpiarPreview() {
        ++revisionPreview;
        window.SSALFER_GIS?.limpiar();

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
            importacion.activo===false ? "Dada de baja · Sólo lectura" : etiquetaEstado(importacion.estado);


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

            const codigo = typeof error === "string" ? error : error?.codigo;
            if (codigo === "GEOMETRIA_INVALIDA_MULTILINESTRING") {
                observaciones.push("Esta carga espera líneas de un trazo. Si el archivo contiene polígonos de núcleos o parcelas, crea una carga con el tipo correspondiente. Este elemento no se incorporó al proyecto.");
                return;
            }

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


            const indice = Number.isInteger(feature.indice_feature)
                ? feature.indice_feature + 1 : "—";


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
                [window.SSALFER_GIS?.camposArchivo(feature,importacionActiva?.tipo_objetivo),feature.diagnostico?window.SSALFER_GIS.diagnosticoElemento(feature):'',observaciones].filter(Boolean).join(' · ')

            ].forEach((valor, columna) => {

                const celda =
                    document.createElement(
                        "td"
                    );


                celda.textContent =
                    String(valor);


                if(columna===3){
                    const marca=document.createElement('span');
                    marca.className=`gis-etiqueta ${feature.estado==='error'?'gis-error':feature.estado_conciliacion==='sin_coincidencia'?'gis-sin-coincidencia':'gis-informacion'}`;
                    marca.textContent=window.SSALFER_GIS?.resultadoTexto(feature) || String(valor);
                    celda.replaceChildren(marca);
                }
                fila.appendChild(celda);

            });


            elementos.tablaFeatures.appendChild(
                fila
            );

        });

    }


    function actualizarConfirmacion() {
        if(importacionActiva?.activo===false || !window.SSALFER_GIS.puedeEditar()){
            elementos.bloqueConfirmacion.hidden=true; elementos.btnConfirmar.disabled=true; return;
        }
        elementos.bloqueConfirmacion.hidden=false;

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
        if (Number(importacion.id_proyecto) !== Number(proyectoActivo?.id_proyecto)) return;
        limpiarPreview();
        elementos.seccionNuevaImportacion.hidden = true;
        if (importacion.version_pipeline !== "legacy-v1" && importacion.tipo_objetivo !== "trazo_proyecto") {
            importacionActiva = importacion; elementos.seccionPreview.hidden = true;
            await window.SSALFER_GIS.mostrar(importacion); return;
        }
        const revision = ++revisionPreview, contexto = revisionProyecto;

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
                importacion.id_importacion, importacion.activo===false
            );

        if (revision !== revisionPreview || contexto !== revisionProyecto) return;


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
        idImportacion, incluirInactivas=false
    ) {
        if (procesando || window.SSALFER_GIS?.ocupado()) return;
        limpiarPreview();
        elementos.seccionNuevaImportacion.hidden = true;
        const contexto = revisionProyecto, revision = ++revisionPreview;

        limpiarMensajes();


        mostrarInformativo(
            "Consultando importación…"
        );


        try {

            const importacion =
                await obtenerImportacion(
                    idImportacion, incluirInactivas
                );

            if (contexto !== revisionProyecto || revision !== revisionPreview) return;


            limpiarMensajes();


            await mostrarPreview(
                importacion
            );

        } catch (error) {
            if (contexto !== revisionProyecto) return;

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
        if (["ddv", "nucleos", "parcelas"].includes(tipo) && obtenerExtension(archivoActivo.name) !== "gpkg") throw new Error("Para esta carga selecciona un archivo GeoPackage (.gpkg).");


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


        formData.append(
            "archivo",
            archivoActivo,
            archivoActivo.name
        );


        if (["ddv", "nucleos", "parcelas"].includes(tipo)) {
            formData.delete("tipo_objetivo");
            if (tipo !== "ddv") formData.set("alcance_entrega", document.getElementById("alcanceEntregaGis").value);
        }
        return formData;

    }


    async function explicarConflictoAlcance(contexto) {
        const vigente = () => contexto.revision === revisionProyecto && contexto.proyecto === obtenerIdProyectoSeleccionado();
        if (!vigente()) return;
        mostrarInformativo("Este archivo ya se procesó con otro alcance. Parcial y Completa describen la entrega; no son opciones para corregir coincidencias. Puedes consultar la carga existente sin volver a subirla ni cambiar su alcance.");
        try {
            const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", await contexto.archivo.arrayBuffer())), b => b.toString(16).padStart(2,"0")).join("");
            const objetivo = {nucleos:"nucleo_agrario_gpkg",parcelas:"parcela_gpkg"}[contexto.tipo];
            const encontradas = [];
            for (let skip=0; vigente(); skip+=200) {
                const pagina = await window.GeoespacialAPI.paginaImportaciones(contexto.proyecto,{skip,limit:200});
                encontradas.push(...pagina.items.filter(r=>Number(r.id_proyecto)===contexto.proyecto && r.sha256===hash && r.tipo_objetivo===objetivo && r.activo!==false && r.estado!=="error"));
                if (window.GeoespacialAPI.fin(pagina,skip,200)) break;
            }
            if (!vigente()) return;
            for (const r of encontradas) {
                const texto = document.createElement("p");
                texto.textContent = `${r.nombre_original} · carga ${r.id_importacion} · alcance registrado: ${r.alcance_entrega === "completa" ? "Completa" : "Parcial"}. Abrirla solo consulta sus resultados.`;
                const boton = document.createElement("button");boton.type="button";boton.className="btn-secundario";
                boton.textContent=`Consultar carga ${r.id_importacion}`;
                boton.addEventListener("click",()=>{if(vigente())abrirImportacion(r.id_importacion);});
                elementos.mensajeInformativo.append(texto,boton);
            }
            if (!encontradas.length) elementos.mensajeInformativo.append(document.createTextNode(" No se pudo identificar una carga disponible con el mismo contenido. Revisa el historial del proyecto o solicita ayuda para corregir el alcance."));
        } catch (_) {
            if(vigente())elementos.mensajeInformativo.append(document.createTextNode(" No se pudo consultar la carga anterior. Revisa el historial cuando se recupere la consulta."));
        }
    }

    async function prepararImportacion(
        evento
    ) {

        evento.preventDefault();


        if (procesando) {
            return;
        }


        limpiarMensajes();


        let contextoCarga;
        try {

            const idProyectoSeleccionado =
                validarFormulario();


            establecerProcesando(
                true
            );


            const archivoCarga = archivoActivo, tipoCarga = elementos.tipoObjetivo.value;
            const nombreCarga = archivoCarga.name;
            contextoCarga = {archivo:archivoCarga,tipo:tipoCarga,proyecto:idProyectoSeleccionado,revision:revisionProyecto};
            const tipoSugerido = /parcel/i.test(nombreCarga) ? "parcelas" : /nucle/i.test(nombreCarga) ? "nucleos" : /ddv/i.test(nombreCarga) ? "ddv" : null;
            if (tipoSugerido && tipoSugerido !== elementos.tipoObjetivo.value) {
                const continuar = await window.SSALFER_UI.confirmar(
                    `El nombre del archivo ${nombreCarga} sugiere ${tipoSugerido}, pero seleccionaste ${elementos.tipoObjetivo.selectedOptions[0].textContent.trim()}. Cancela para revisar el tipo o confirma solo si esa elección es correcta. El nombre es una pista, no una validación del contenido.`,
                    "Revisa el tipo de información"
                );
                if (!continuar) return;
                if (archivoActivo !== archivoCarga || elementos.tipoObjetivo.value !== tipoCarga || obtenerIdProyectoSeleccionado() !== idProyectoSeleccionado) {
                    throw new Error("La selección cambió. Revisa el proyecto, el archivo y el tipo antes de volver a preparar la carga.");
                }
            }
            const formData =
                construirFormData();


            const importacion =
                await (["ddv", "nucleos", "parcelas"].includes(elementos.tipoObjetivo.value)
                    ? window.GeoespacialAPI.cargar(idProyectoSeleccionado, elementos.tipoObjetivo.value, formData)
                    : window.ClienteAPI.post(`/proyectos/${idProyectoSeleccionado}/importaciones`, formData));


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
                "error" || Number(importacion.errores) > 0
            ) {

                mostrarError(
                    "El archivo contiene errores que impiden su importación. Revisa el detalle de la previsualización."
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
            if (error.status === 409 && /mismo archivo.*otro alcance/i.test(error.message) && contextoCarga) {
                await explicarConflictoAlcance(contextoCarga);
            } else {
                manejarError(error);
            }

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
        if(importacionActiva?.activo===false || !window.SSALFER_GIS.puedeEditar())return;

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


        const importacionConfirmada = importacionActiva;
        const contextoConfirmado = revisionProyecto;
        if (Number(importacionConfirmada.id_proyecto) !== Number(proyectoActivo?.id_proyecto)) {
            mostrarError("Selecciona una importación del proyecto actual.");
            return;
        }
        const continuar = await window.SSALFER_UI.confirmar(
            `¿Confirmas incorporar estas geometrías al proyecto ${nombreProyecto(proyectoActivo)}?`,
            "Confirmar importación geoespacial"
        );
        if (importacionConfirmada.activo===false || contextoConfirmado !== revisionProyecto || importacionActiva !== importacionConfirmada || procesando) return;


        if (!continuar) {
            return;
        }


        establecerProcesando(true);


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
                    `/importaciones/${importacionConfirmada.id_importacion}/confirmar`,
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

            establecerProcesando(false);


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

                if (procesando || window.SSALFER_GIS?.ocupado()) return;
                limpiarPreview();
                limpiarMensajes();
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
                        id, boton.dataset.inactiva==='true'
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


    await iniciar();

});
