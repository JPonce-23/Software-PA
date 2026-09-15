document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idProyectoNucleo =
        parametros.get(
            "id_proyecto_nucleo"
        );

    const elementos = {
        mensajeError:
            document.getElementById(
                "mensajeError"
            ),

        nombreNucleo:
            document.getElementById(
                "nombreNucleo"
            ),

        nombreProyecto:
            document.getElementById(
                "nombreProyecto"
            ),

        entidad:
            document.getElementById(
                "entidad"
            ),

        municipio:
            document.getElementById(
                "municipio"
            ),

        tipoTenencia:
            document.getElementById(
                "tipoTenencia"
            ),

        residencia:
            document.getElementById(
                "residencia"
            ),

        referencia:
            document.getElementById(
                "referencia"
            ),

        responsableNombre:
            document.getElementById(
                "responsableNombre"
            ),

        responsableCargo:
            document.getElementById(
                "responsableCargo"
            ),

        responsableContacto:
            document.getElementById(
                "responsableContacto"
            ),

        totalParcelas:
            document.getElementById(
                "totalParcelas"
            ),

        totalAfectaciones:
            document.getElementById(
                "totalAfectaciones"
            ),

        afectacionesColectivas:
            document.getElementById(
                "afectacionesColectivas"
            ),

        afectacionesIndividuales:
            document.getElementById(
                "afectacionesIndividuales"
            ),

        superficiePreliminar:
            document.getElementById(
                "superficiePreliminar"
            ),

        superficieAfectada:
            document.getElementById(
                "superficieAfectada"
            ),

        totalAsambleas:
            document.getElementById(
                "totalAsambleas"
            ),

        totalConvenios:
            document.getElementById(
                "totalConvenios"
            ),

        totalUnidades:
            document.getElementById(
                "totalUnidades"
            ),

        btnVolver:
            document.getElementById(
                "btnVolver"
            ),

        migaProyecto:
            document.querySelector(
                ".js-miga-proyecto"
            ),

        btnOrv:
            document.getElementById(
                "btnOrv"
            ),

        btnPadron:
            document.getElementById(
                "btnPadron"
            ),

        btnSensibilizacion:
            document.getElementById(
                "btnSensibilizacion"
            ),

        btnCaminamiento:
            document.getElementById(
                "btnCaminamiento"
            ),

        btnAsamblea:
            document.getElementById(
                "btnAsamblea"
            ),

        btnSeguimiento:
            document.getElementById(
                "btnSeguimiento"
            ),

        btnPadrones:
            document.getElementById(
                "btnPadrones"
            ),

        btnParcelas:
            document.getElementById(
                "btnParcelas"
            ),

        btnUnidadesAgrarias:
            document.getElementById(
                "btnUnidadesAgrarias"
            ),


        btnAfectaciones:
            document.getElementById(
                "btnAfectaciones"
            ),

        btnFifonafe:
            document.getElementById(
                "btnFifonafe"
            ),

        btnPersona:
            document.getElementById(
                "btnPersonas"
            )
    };

    if (!idProyectoNucleo) {
        window.ClienteAPI.mostrarErrorAPI(
            new Error(
                "No se puede mostrar la ficha porque falta " +
                "id_proyecto_nucleo en la URL."
            ),
            elementos.mensajeError
        );

        return;
    }

    /* =====================================================
                        UTILIDADES
    ====================================================== */

    function texto(
        valor,
        respaldo = "—"
    ) {
        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return respaldo;
        }

        return String(valor);
    }

    function formatoSuperficie(valor) {
        const numero =
            Number(valor);

        return (
            `${
                Number.isFinite(numero)
                    ? numero.toFixed(6)
                    : "0.000000"
            } ha`
        );
    }

    function configurarEnlace(
        elemento,
        ruta
    ) {
        if (!elemento) {
            return;
        }

        elemento.href = ruta;
    }

    /* =====================================================
                CARGAR RESUMEN DEL NÚCLEO
    ====================================================== */

    let nucleo;

    try {
        /*
         * GET /proyecto-nucleo/{id}
         *
         * El backend ya devuelve ProyectoNucleoResponse
         * con el resumen necesario para esta ficha:
         *
         * - nombre_proyecto
         * - nombre_nucleo
         * - tipo_tenencia_codigo
         * - tipo_tenencia_nombre
         * - residencia_codigo
         * - residencia_nombre
         * - entidad
         * - municipio
         * - responsable_*
         * - referencia_principal
         * - KPIs
         */

        nucleo =
            await window.NucleosAPI
                .obtenerProyectoNucleo(
                    idProyectoNucleo
                );

    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(
            error,
            elementos.mensajeError
        );

        return;
    }

    const idProyecto =
        nucleo.id_proyecto;

    /* =====================================================
                    INFORMACIÓN GENERAL
    ====================================================== */

    document.title =
        `${texto(
            nucleo.nombre_nucleo,
            "Núcleo agrario"
        )} | SSALFER`;

    if (elementos.nombreNucleo) {
        elementos.nombreNucleo.textContent =
            texto(
                nucleo.nombre_nucleo
            );
    }

    if (elementos.nombreProyecto) {
        elementos.nombreProyecto.textContent =
            texto(
                nucleo.nombre_proyecto
            );
    }

    if (elementos.entidad) {
        elementos.entidad.textContent =
            texto(
                nucleo.entidad
            );
    }

    if (elementos.municipio) {
        elementos.municipio.textContent =
            texto(
                nucleo.municipio
            );
    }

    if (elementos.tipoTenencia) {
        elementos.tipoTenencia.textContent =
            texto(
                nucleo.tipo_tenencia_nombre ||
                nucleo.tipo_tenencia_codigo
            );
    }

    if (elementos.residencia) {
        elementos.residencia.textContent =
            texto(
                nucleo.residencia_nombre ||
                nucleo.residencia_codigo
            );
    }

    if (elementos.referencia) {
        elementos.referencia.textContent =
            texto(
                nucleo.referencia_principal
            );
    }

    /* =====================================================
                        RESPONSABLE
    ====================================================== */

    if (elementos.responsableNombre) {
        elementos.responsableNombre.textContent =
            texto(
                nucleo.responsable_nombre
            );
    }

    if (elementos.responsableCargo) {
        elementos.responsableCargo.textContent =
            texto(
                nucleo.responsable_cargo
            );
    }

    if (elementos.responsableContacto) {
        elementos.responsableContacto.textContent =
            texto(
                nucleo.responsable_contacto
            );
    }

    /* =====================================================
                            KPIs
    ====================================================== */

    if (elementos.totalParcelas) {
        elementos.totalParcelas.textContent =
            texto(
                nucleo.total_parcelas,
                "0"
            );
    }

    if (elementos.totalAfectaciones) {
        elementos.totalAfectaciones.textContent =
            texto(
                nucleo.total_afectaciones,
                "0"
            );
    }

    if (elementos.afectacionesColectivas) {
        elementos.afectacionesColectivas.textContent =
            texto(
                nucleo.afectaciones_colectivas,
                "0"
            );
    }

    if (elementos.afectacionesIndividuales) {
        elementos.afectacionesIndividuales.textContent =
            texto(
                nucleo.afectaciones_individuales,
                "0"
            );
    }

    if (elementos.superficiePreliminar) {
        elementos.superficiePreliminar.textContent =
            formatoSuperficie(
                nucleo.superficie_preliminar_ha
            );
    }

    if (elementos.superficieAfectada) {
        elementos.superficieAfectada.textContent =
            formatoSuperficie(
                nucleo.superficie_afectada_ha
            );
    }

    if (elementos.totalAsambleas) {
        elementos.totalAsambleas.textContent =
            texto(
                nucleo.total_asambleas,
                "0"
            );
    }

    if (elementos.totalConvenios) {
        elementos.totalConvenios.textContent =
            texto(
                nucleo.total_convenios,
                "0"
            );
    }

    if (elementos.totalUnidades) {
        elementos.totalUnidades.textContent =
            texto(
                nucleo.total_unidades_afectadas,
                "0"
            );
    }

    /* =====================================================
                BREADCRUMB / VOLVER
    ====================================================== */

    if (
        elementos.migaProyecto &&
        idProyecto
    ) {
        elementos.migaProyecto.textContent =
            texto(
                nucleo.nombre_proyecto,
                "Proyecto"
            );

        elementos.migaProyecto.href =
            `/pages/fichaProyecto.html?id=${encodeURIComponent(
                idProyecto
            )}`;
    }

    if (elementos.btnVolver) {
        elementos.btnVolver.addEventListener(
            "click",
            () => {
                window.location.href =
                    idProyecto
                        ? `/pages/fichaProyecto.html?id=${encodeURIComponent(
                            idProyecto
                        )}`
                        : "/dashboard.html";
            }
        );
    }

    /* =====================================================
                    MÓDULOS DEL NÚCLEO
    ====================================================== */

    const queryBase =
        `id_proyecto_nucleo=${encodeURIComponent(
            idProyectoNucleo
        )}`;

    configurarEnlace(
        elementos.btnOrv,
        `/pages/orv.html?${queryBase}`
    );

    configurarEnlace(
        elementos.btnPadron,
        `/pages/padrones.html?${queryBase}`
    );

    configurarEnlace(
        elementos.btnSensibilizacion,
        `/pages/actividades.html?${queryBase}&tipo_actividad=sensibilizacion`
    );

    configurarEnlace(
        elementos.btnCaminamiento,
        `/pages/actividades.html?${queryBase}&tipo_actividad=caminamiento`
    );

    configurarEnlace(
        elementos.btnAsamblea,
        `/pages/asamblea.html?${queryBase}`
    );

    configurarEnlace(
    elementos.btnSeguimiento,
    `/pages/seguimiento.html?${queryBase}`
    );

    configurarEnlace(
        elementos.btnPadrones,
        `/pages/padrones.html?${queryBase}`
    );

    configurarEnlace(
        elementos.btnParcelas,
        `/pages/parcela.html?${queryBase}`
    );

    configurarEnlace(
        elementos.btnUnidadesAgrarias,
        `/pages/unidadAgraria.html?${queryBase}`
    );

    configurarEnlace(
        elementos.btnAfectaciones,
        `/pages/afectacion.html?${queryBase}`
    );

    configurarEnlace(
        elementos.btnFifonafe,
        `/pages/fifonafe.html?${queryBase}`
    );

    configurarEnlace(
        elementos.btnPersonas,
        `/pages/persona.html?id_proyecto=${encodeURIComponent(
            idProyecto
        )}`
    );
});