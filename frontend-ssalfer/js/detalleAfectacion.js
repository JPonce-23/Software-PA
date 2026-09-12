/**
 * detalleAfectacion.js
 *
 * Ficha de afectación conectada con datos reales.
 */

document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const contenedorPrincipal =
        document.querySelector(
            ".detalle-contenedor"
        );

    const idAfectacion =
        parametros.get("id") ||
        contenedorPrincipal
            ?.dataset
            .afectacionId ||
        null;

    const contenedorError =
        document.getElementById(
            "mensajeError"
        );

    if (!idAfectacion) {
        window.ClienteAPI
            ?.mostrarErrorAPI?.(
                new Error(
                    "No se encontró el ID de la afectación (falta ?id= en la URL)."
                ),
                contenedorError
            );

        return;
    }

    const formatoMoneda =
        new Intl.NumberFormat(
            "es-MX",
            {
                style: "currency",
                currency: "MXN",
                maximumFractionDigits: 2
            }
        );

    function moneda(valor) {
        return valor != null
            ? formatoMoneda.format(
                Number(valor)
            )
            : "—";
    }

    function superficie(valor) {
        return valor != null
            ? `${Number(valor).toFixed(
                6
            )} ha`
            : "—";
    }

    function fechaLegible(valorISO) {
        if (!valorISO) {
            return "—";
        }

        const partes =
            String(valorISO).split("-");

        if (partes.length !== 3) {
            return String(valorISO);
        }

        const [anio, mes, dia] =
            partes;

        return `${dia}/${mes}/${anio}`;
    }

    function textoOPendiente(
        valor,
        textoPendiente = "Pendiente"
    ) {
        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return {
                texto: textoPendiente,
                pendiente: true
            };
        }

        return {
            texto: valor,
            pendiente: false
        };
    }

    function aplicarDato(
        elemento,
        {
            texto,
            pendiente
        }
    ) {
        if (!elemento) {
            return;
        }

        elemento.textContent =
            texto;

        elemento.classList.toggle(
            "dato-pendiente",
            pendiente
        );
    }

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    const ETIQUETAS_TIPO_AFECTACION = {
        colectivo:
            "Colectiva",

        individual:
            "Individual"
    };

    const ETIQUETAS_CONDICION_ESPECIAL = {
        expropiacion_directa:
            "Expropiación directa",

        comunidad_indigena:
            "Comunidad indígena",

        otro:
            "Otro"
    };

    const ETIQUETAS_ESTATUS_INDEMNIZACION = {
        pendiente:
            "Pendiente",

        programado:
            "Programado",

        en_proceso:
            "En proceso",

        completo:
            "Completo",

        pagado:
            "Pagado",

        cancelado:
            "Cancelado",

        otro:
            "Otro"
    };

    const ETIQUETAS_TIPO_CONVENIO = {
        cop_original:
            "COP original",

        modificatorio:
            "Modificatorio",

        superficie_adicional:
            "Superficie adicional",

        obras_complementarias:
            "Obras complementarias",

        ampliacion:
            "Ampliación",

        ampliacion_remanente:
            "Ampliación remanente"
    };

    const ETIQUETAS_MEDIO_PAGO = {
        transferencia:
            "Transferencia",

        cheque:
            "Cheque",

        efectivo:
            "Efectivo",

        deposito:
            "Depósito",

        otro:
            "Otro"
    };

    let afectacion =
        null;

    try {
        afectacion =
            await window.AfectacionesAPI.obtener(
                idAfectacion
            );

    } catch (error) {
        window.ClienteAPI.mostrarErrorAPI(
            error,
            contenedorError
        );

        const titulo =
            document.getElementById(
                "tituloAfectacion"
            );

        if (titulo) {
            titulo.textContent =
                "No se pudo cargar la afectación";
        }

        return;
    }

    const enlaceVolver1 =
        document.getElementById(
            "enlaceVolverAfectaciones"
        );

    const enlaceVolver2 =
        document.getElementById(
            "enlaceVolverAfectacionesFinal"
        );

    const hrefAfectaciones =
        `/pages/afectacion.html?id_proyecto_nucleo=${encodeURIComponent(
            afectacion.id_proyecto_nucleo
        )}`;

    if (enlaceVolver1) {
        enlaceVolver1.href =
            hrefAfectaciones;
    }

    if (enlaceVolver2) {
        enlaceVolver2.href =
            hrefAfectaciones;
    }

    const enlaceFifonafeNucleo =
        document.getElementById(
            "enlaceFifonafeNucleo"
        );

    if (enlaceFifonafeNucleo) {
        enlaceFifonafeNucleo.href =
            `/pages/fifonafe.html?id_proyecto_nucleo=${encodeURIComponent(
                afectacion.id_proyecto_nucleo
            )}`;
    }

    function pintarEncabezadoEInformacionGeneral(
        datos
    ) {
        document.title =
            `Afectación #${datos.id_afectacion} | SSALFER`;

        const ruta =
            document.getElementById(
                "rutaAfectacion"
            );

        if (ruta) {
            ruta.textContent =
                `Núcleo ${datos.id_proyecto_nucleo} / Afectaciones / Afectación #${datos.id_afectacion}`;
        }

        const titulo =
            document.getElementById(
                "tituloAfectacion"
            );

        if (titulo) {
            titulo.textContent =
                `Afectación #${datos.id_afectacion}`;
        }

        const badge =
            document.getElementById(
                "estadoBadgeAfectacion"
            );

        const {
            texto: situacionTexto,
            pendiente: situacionPendiente
        } =
            textoOPendiente(
                datos.situacion,
                "Sin situación registrada"
            );

        if (badge) {
            badge.textContent =
                situacionTexto;

            badge.classList.toggle(
                "pendiente",
                situacionPendiente
            );
        }

        const tipo =
            document.getElementById(
                "datoTipoAfectacion"
            );

        if (tipo) {
            tipo.textContent =
                ETIQUETAS_TIPO_AFECTACION[
                    datos.tipo_afectacion
                ] ||
                datos.tipo_afectacion ||
                "—";
        }

        aplicarDato(
            document.getElementById(
                "datoSituacion"
            ),
            textoOPendiente(
                datos.situacion
            )
        );

        const preliminar =
            document.getElementById(
                "datoSuperficiePreliminar"
            );

        if (preliminar) {
            preliminar.textContent =
                superficie(
                    datos.superficie_preliminar_ha
                );
        }

        aplicarDato(
            document.getElementById(
                "datoSuperficieAfectada"
            ),
            {
                texto:
                    datos.superficie_afectada_ha !=
                    null
                        ? superficie(
                            datos.superficie_afectada_ha
                        )
                        : "Pendiente",

                pendiente:
                    datos.superficie_afectada_ha ==
                    null
            }
        );

        aplicarDato(
            document.getElementById(
                "datoCondicionEspecial"
            ),
            textoOPendiente(
                datos.condicion_especial
                    ? (
                        ETIQUETAS_CONDICION_ESPECIAL[
                            datos.condicion_especial
                        ] ||
                        datos.condicion_especial
                    )
                    : null,
                "Sin condición especial"
            )
        );

        aplicarDato(
            document.getElementById(
                "datoDescripcionCondicion"
            ),
            textoOPendiente(
                datos.descripcion_condicion,
                "Sin descripción"
            )
        );

        const estadoInfo =
            document.getElementById(
                "estadoSeccionInfo"
            );

        if (estadoInfo) {
            estadoInfo.textContent =
                situacionPendiente
                    ? "Pendiente"
                    : "Con información";

            estadoInfo.classList.toggle(
                "pendiente",
                situacionPendiente
            );
        }
    }

    pintarEncabezadoEInformacionGeneral(
        afectacion
    );

    const btnEditarAfectacion =
        document.getElementById(
            "btnEditarAfectacion"
        );

    const panelEdicion =
        document.getElementById(
            "panelEdicionAfectacion"
        );

    const formEditar =
        document.getElementById(
            "formEditarAfectacion"
        );

    const btnCancelarEdicion =
        document.getElementById(
            "btnCancelarEdicionAfectacion"
        );

    function abrirFormularioInfo() {
        formEditar
            .querySelector(
                "#inputSituacion"
            )
            .value =
            afectacion.situacion ||
            "";

        formEditar
            .querySelector(
                "#inputSuperficiePreliminar"
            )
            .value =
            afectacion.superficie_preliminar_ha ??
            "";

        formEditar
            .querySelector(
                "#inputSuperficieAfectada"
            )
            .value =
            afectacion.superficie_afectada_ha ??
            "";

        formEditar
            .querySelector(
                "#inputCondicionEspecial"
            )
            .value =
            afectacion.condicion_especial ||
            "";

        formEditar
            .querySelector(
                "#inputDescripcionCondicion"
            )
            .value =
            afectacion.descripcion_condicion ||
            "";

        panelEdicion.hidden =
            false;

        panelEdicion.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    btnEditarAfectacion
        ?.addEventListener(
            "click",
            abrirFormularioInfo
        );

    btnCancelarEdicion
        ?.addEventListener(
            "click",
            () => {
                panelEdicion.hidden =
                    true;
            }
        );

    formEditar?.addEventListener(
        "submit",
        async evento => {
            evento.preventDefault();

            const valorNumero =
                selector => {
                    const valor =
                        formEditar
                            .querySelector(
                                selector
                            )
                            .value;

                    return valor === ""
                        ? null
                        : Number(valor);
                };

            const payload = {
                situacion:
                    formEditar
                        .querySelector(
                            "#inputSituacion"
                        )
                        .value
                        .trim() ||
                    null,

                superficie_preliminar_ha:
                    valorNumero(
                        "#inputSuperficiePreliminar"
                    ),

                superficie_afectada_ha:
                    valorNumero(
                        "#inputSuperficieAfectada"
                    ),

                condicion_especial:
                    formEditar
                        .querySelector(
                            "#inputCondicionEspecial"
                        )
                        .value ||
                    null,

                descripcion_condicion:
                    formEditar
                        .querySelector(
                            "#inputDescripcionCondicion"
                        )
                        .value
                        .trim() ||
                    null
            };

            if (
                payload.condicion_especial !==
                "otro"
            ) {
                payload.descripcion_condicion =
                    null;
            }

            if (
                payload.superficie_preliminar_ha !=
                    null &&
                payload.superficie_preliminar_ha <
                    0
            ) {
                alert(
                    "La superficie preliminar no puede ser negativa."
                );

                return;
            }

            if (
                payload.superficie_afectada_ha !=
                    null &&
                payload.superficie_afectada_ha <
                    0
            ) {
                alert(
                    "La superficie afectada no puede ser negativa."
                );

                return;
            }

            if (
                payload.condicion_especial ===
                    "otro" &&
                !payload.descripcion_condicion
            ) {
                alert(
                    "La condición 'otro' requiere una descripción."
                );

                return;
            }

            try {
                afectacion =
                    await window.AfectacionesAPI.actualizar(
                        idAfectacion,
                        payload
                    );

                pintarEncabezadoEInformacionGeneral(
                    afectacion
                );

                panelEdicion.hidden =
                    true;

            } catch (error) {
                window.ClienteAPI.mostrarErrorAPI(
                    error,
                    contenedorError
                );
            }
        }
    );

    function pintarAvaluo(datos) {
        const hayAvaluo =
            datos.avaluo_monto !=
            null;

        const datoMonto =
            document.getElementById(
                "datoAvaluoMonto"
            );

        const datoFecha =
            document.getElementById(
                "datoAvaluoFecha"
            );

        const datoReferencia =
            document.getElementById(
                "datoAvaluoReferencia"
            );

        const datoInstitucion =
            document.getElementById(
                "datoAvaluoInstitucion"
            );

        if (datoMonto) {
            datoMonto.textContent =
                moneda(
                    datos.avaluo_monto
                );
        }

        if (datoFecha) {
            datoFecha.textContent =
                fechaLegible(
                    datos.avaluo_fecha
                );
        }

        if (datoReferencia) {
            datoReferencia.textContent =
                datos.avaluo_referencia ||
                "—";
        }

        if (datoInstitucion) {
            datoInstitucion.textContent =
                datos.avaluo_institucion ||
                "—";
        }

        const estadoAvaluo =
            document.getElementById(
                "estadoSeccionAvaluo"
            );

        if (estadoAvaluo) {
            estadoAvaluo.textContent =
                hayAvaluo
                    ? "Capturado"
                    : "Pendiente";

            estadoAvaluo.classList.toggle(
                "pendiente",
                !hayAvaluo
            );
        }

        const btnCapturar =
            document.getElementById(
                "btnCapturarAvaluo"
            );

        if (btnCapturar) {
            btnCapturar.innerHTML =
                hayAvaluo
                    ? '<i class="bi bi-pencil"></i> Editar avalúo'
                    : '<i class="bi bi-pencil"></i> Capturar avalúo';
        }
    }

    pintarAvaluo(
        afectacion
    );

    const btnCapturarAvaluo =
        document.getElementById(
            "btnCapturarAvaluo"
        );

    const formAvaluo =
        document.getElementById(
            "formAvaluo"
        );

    const btnCancelarAvaluo =
        document.getElementById(
            "btnCancelarAvaluo"
        );

    btnCapturarAvaluo
        ?.addEventListener(
            "click",
            () => {
                formAvaluo
                    .querySelector(
                        "#inputAvaluoMonto"
                    )
                    .value =
                    afectacion.avaluo_monto ??
                    "";

                formAvaluo
                    .querySelector(
                        "#inputAvaluoFecha"
                    )
                    .value =
                    afectacion.avaluo_fecha ||
                    "";

                formAvaluo
                    .querySelector(
                        "#inputAvaluoReferencia"
                    )
                    .value =
                    afectacion.avaluo_referencia ||
                    "";

                formAvaluo
                    .querySelector(
                        "#inputAvaluoInstitucion"
                    )
                    .value =
                    afectacion.avaluo_institucion ||
                    "";

                formAvaluo.hidden =
                    false;

                formAvaluo.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });
            }
        );

    btnCancelarAvaluo
        ?.addEventListener(
            "click",
            () => {
                formAvaluo.hidden =
                    true;
            }
        );

    formAvaluo?.addEventListener(
        "submit",
        async evento => {
            evento.preventDefault();

            const montoTexto =
                formAvaluo
                    .querySelector(
                        "#inputAvaluoMonto"
                    )
                    .value;

            const payload = {
                avaluo_monto:
                    montoTexto === ""
                        ? null
                        : Number(
                            montoTexto
                        ),

                avaluo_fecha:
                    formAvaluo
                        .querySelector(
                            "#inputAvaluoFecha"
                        )
                        .value ||
                    null,

                avaluo_referencia:
                    formAvaluo
                        .querySelector(
                            "#inputAvaluoReferencia"
                        )
                        .value
                        .trim() ||
                    null,

                avaluo_institucion:
                    formAvaluo
                        .querySelector(
                            "#inputAvaluoInstitucion"
                        )
                        .value
                        .trim() ||
                    null
            };

            if (
                payload.avaluo_monto !=
                    null &&
                (
                    !Number.isFinite(
                        payload.avaluo_monto
                    ) ||
                    payload.avaluo_monto <
                        0
                )
            ) {
                alert(
                    "El monto del avalúo debe ser un número igual o mayor a cero."
                );

                return;
            }

            try {
                afectacion =
                    await window.AfectacionesAPI.actualizar(
                        idAfectacion,
                        payload
                    );

                pintarAvaluo(
                    afectacion
                );

                formAvaluo.hidden =
                    true;

            } catch (error) {
                window.ClienteAPI.mostrarErrorAPI(
                    error,
                    contenedorError
                );
            }
        }
    );

    /*
     * CONVENIOS
     */

    (async () => {
        const contenedor =
            document.getElementById(
                "contenedorConvenios"
            );

        if (!contenedor) {
            return;
        }

        try {
            const convenios =
                await window.ConveniosAPI.listarPorAfectacion(
                    idAfectacion
                );

            if (
                !Array.isArray(
                    convenios
                ) ||
                convenios.length === 0
            ) {
                contenedor.innerHTML = `
                    <div class="tabla-vacia">

                        <i class="bi bi-file-earmark-text"></i>

                        <strong>
                            No hay convenios registrados.
                        </strong>

                        <span>
                            Los convenios asociados a esta afectación aparecerán aquí.
                        </span>

                    </div>
                `;

                return;
            }

            contenedor.innerHTML = `
                <div class="tabla-contenedor">

                    <table>

                        <thead>
                            <tr>
                                <th>Convenio</th>
                                <th>Tipo</th>
                                <th>Fecha de firma</th>
                                <th>Monto 90%</th>
                                <th>Monto 100%</th>
                                <th>Efecto</th>
                            </tr>
                        </thead>

                        <tbody>

                            ${convenios
                                .map(
                                    convenio => `
                                        <tr>

                                            <td>
                                                <a
                                                    href="/pages/fichaConvenio.html?id_convenio=${encodeURIComponent(
                                                        convenio.id_convenio
                                                    )}">

                                                    Convenio #${convenio.id_convenio}

                                                </a>
                                            </td>

                                            <td>
                                                ${escaparHTML(
                                                    convenio.tipo_convenio
                                                        ? (
                                                            ETIQUETAS_TIPO_CONVENIO[
                                                                convenio.tipo_convenio
                                                            ] ||
                                                            convenio.tipo_convenio
                                                        )
                                                        : "—"
                                                )}
                                            </td>

                                            <td>
                                                ${fechaLegible(
                                                    convenio.fecha_firma
                                                )}
                                            </td>

                                            <td>
                                                ${moneda(
                                                    convenio.monto_90
                                                )}
                                            </td>

                                            <td>
                                                ${moneda(
                                                    convenio.monto_100
                                                )}
                                            </td>

                                            <td>
                                                ${escaparHTML(
                                                    convenio.efecto_monto ||
                                                    "—"
                                                )}
                                            </td>

                                        </tr>
                                    `
                                )
                                .join("")}

                        </tbody>

                    </table>

                </div>
            `;

        } catch (error) {
            contenedor.innerHTML = `
                <div class="tabla-vacia">
                    <strong>
                        No se pudieron cargar los convenios.
                    </strong>
                </div>
            `;

            window.ClienteAPI.mostrarErrorAPI(
                error,
                contenedorError
            );
        }
    })();

    /*
     * INDEMNIZACIÓN Y PAGOS
     */

    (async () => {
        const contenedorPagos =
            document.getElementById(
                "contenedorPagos"
            );

        const btnIndemnizacion =
            document.getElementById(
                "btnRegistrarIndemnizacion"
            );

        const textoBtnIndemnizacion =
            document.getElementById(
                "textoBtnIndemnizacion"
            );

        let indemnizacion =
            null;

        try {
            indemnizacion =
                await window.IndemnizacionAPI.listarPorAfectacion(
                    idAfectacion
                );

        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(
                error,
                contenedorError
            );
        }

        const hayIndemnizacion =
            Boolean(
                indemnizacion
            );

        const estadoIndemnizacion =
            document.getElementById(
                "estadoSeccionIndemnizacion"
            );

        if (hayIndemnizacion) {
            const datoEstatus =
                document.getElementById(
                    "datoIndemnizacionEstatus"
                );

            const datoProgramada =
                document.getElementById(
                    "datoIndemnizacionFechaProgramada"
                );

            const datoResolucion =
                document.getElementById(
                    "datoIndemnizacionFechaResolucion"
                );

            const datoEntrega =
                document.getElementById(
                    "datoIndemnizacionEntregaExpediente"
                );

            if (datoEstatus) {
                datoEstatus.textContent =
                    ETIQUETAS_ESTATUS_INDEMNIZACION[
                        indemnizacion.estatus
                    ] ||
                    indemnizacion.estatus;
            }

            if (datoProgramada) {
                datoProgramada.textContent =
                    fechaLegible(
                        indemnizacion.fecha_programada
                    );
            }

            if (datoResolucion) {
                datoResolucion.textContent =
                    fechaLegible(
                        indemnizacion.fecha_resolucion
                    );
            }

            if (datoEntrega) {
                datoEntrega.textContent =
                    fechaLegible(
                        indemnizacion.fecha_entrega_expediente_pa
                    );
            }

            if (estadoIndemnizacion) {
                const esFinal =
                    [
                        "completo",
                        "pagado"
                    ].includes(
                        indemnizacion.estatus
                    );

                estadoIndemnizacion.textContent =
                    ETIQUETAS_ESTATUS_INDEMNIZACION[
                        indemnizacion.estatus
                    ] ||
                    indemnizacion.estatus;

                estadoIndemnizacion.classList.toggle(
                    "pendiente",
                    !esFinal
                );
            }

            if (textoBtnIndemnizacion) {
                textoBtnIndemnizacion.textContent =
                    "Ver / continuar indemnización";
            }

        } else if (
            estadoIndemnizacion
        ) {
            estadoIndemnizacion.textContent =
                "Sin registro";
        }

        if (btnIndemnizacion) {
            btnIndemnizacion.href =
                `/pages/indemnizacion.html?id_afectacion=${encodeURIComponent(
                    idAfectacion
                )}`;
        }

        if (!contenedorPagos) {
            return;
        }

        if (!hayIndemnizacion) {
            contenedorPagos.innerHTML = `
                <div class="tabla-vacia">

                    <i class="bi bi-credit-card"></i>

                    <strong>
                        Todavía no existe una indemnización registrada.
                    </strong>

                    <span>
                        Los pagos aparecerán aquí una vez que se registre la indemnización.
                    </span>

                </div>
            `;

            return;
        }

        try {
            const pagos =
                await window.IndemnizacionAPI.listarPagos(
                    indemnizacion.id_indemnizacion
                );

            if (
                !Array.isArray(pagos) ||
                pagos.length === 0
            ) {
                contenedorPagos.innerHTML = `
                    <div class="tabla-vacia">

                        <i class="bi bi-credit-card"></i>

                        <strong>
                            No hay pagos registrados.
                        </strong>

                        <span>
                            Los pagos aparecerán aquí cuando se registren desde indemnizacion.html.
                        </span>

                    </div>
                `;

                return;
            }

            contenedorPagos.innerHTML = `
                <div class="tabla-contenedor">

                    <table>

                        <thead>
                            <tr>
                                <th>Fecha de pago</th>
                                <th>Beneficiario</th>
                                <th>Monto</th>
                                <th>Medio de pago</th>
                                <th>Referencia</th>
                            </tr>
                        </thead>

                        <tbody>

                            ${pagos
                                .map(
                                    pago => `
                                        <tr>

                                            <td>
                                                ${fechaLegible(
                                                    pago.fecha_pago
                                                )}
                                            </td>

                                            <td>
                                                ${escaparHTML(
                                                    pago.beneficiario_nombre ||
                                                    "—"
                                                )}
                                            </td>

                                            <td>
                                                ${moneda(
                                                    pago.monto
                                                )}
                                            </td>

                                            <td>
                                                ${escaparHTML(
                                                    pago.medio_pago
                                                        ? (
                                                            ETIQUETAS_MEDIO_PAGO[
                                                                pago.medio_pago
                                                            ] ||
                                                            pago.medio_pago
                                                        )
                                                        : "—"
                                                )}
                                            </td>

                                            <td>
                                                ${escaparHTML(
                                                    pago.referencia ||
                                                    "—"
                                                )}
                                            </td>

                                        </tr>
                                    `
                                )
                                .join("")}

                        </tbody>

                    </table>

                </div>
            `;

        } catch (error) {
            contenedorPagos.innerHTML = `
                <div class="tabla-vacia">
                    <strong>
                        No se pudieron cargar los pagos.
                    </strong>
                </div>
            `;

            window.ClienteAPI.mostrarErrorAPI(
                error,
                contenedorError
            );
        }
    })();

    /*
     * UNIDADES AGRARIAS RELACIONADAS
     */

    function pintarUnidadesAgrarias() {
        const contenedor =
            document.getElementById(
                "contenedorUnidadesAgrarias"
            );

        if (!contenedor) {
            return;
        }

        const unidades =
            Array.isArray(
                afectacion.unidades_agrarias
            )
                ? afectacion.unidades_agrarias
                : [];

        if (unidades.length === 0) {
            contenedor.innerHTML = `
                <div class="tabla-vacia">

                    <i class="bi bi-folder2-open"></i>

                    <strong>
                        No hay unidades agrarias registradas.
                    </strong>

                    <span>
                        Las relaciones con unidades agrarias aparecerán aquí cuando existan.
                    </span>

                </div>
            `;

            return;
        }

        contenedor.innerHTML = `
            <div class="tabla-contenedor">

                <table>

                    <thead>
                        <tr>
                            <th>Unidad agraria</th>
                            <th>Superficie preliminar</th>
                            <th>Superficie afectada</th>
                            <th>Fuente</th>
                        </tr>
                    </thead>

                    <tbody>

                        ${unidades
                            .map(
                                unidad => `
                                    <tr>

                                        <td>
                                            ${escaparHTML(
                                                unidad.unidad_agraria
                                                    ?.referencia_alfanumerica ||
                                                unidad.unidad_agraria
                                                    ?.referencia_normalizada ||
                                                `Unidad #${unidad.id_unidad_agraria}`
                                            )}
                                        </td>

                                        <td>
                                            ${superficie(
                                                unidad.superficie_preliminar_ha
                                            )}
                                        </td>

                                        <td>
                                            ${superficie(
                                                unidad.superficie_afectada_ha
                                            )}
                                        </td>

                                        <td>
                                            ${escaparHTML(
                                                unidad.fuente ||
                                                "—"
                                            )}
                                        </td>

                                    </tr>
                                `
                            )
                            .join("")}

                    </tbody>

                </table>

            </div>
        `;
    }

    pintarUnidadesAgrarias();

    const btnAgregarUnidad =
        document.getElementById(
            "btnAgregarUnidad"
        );

    btnAgregarUnidad?.addEventListener(
        "click",
        () => {
            window.location.href =
                `/pages/unidadAgraria.html?id_proyecto_nucleo=${encodeURIComponent(
                    afectacion.id_proyecto_nucleo
                )}&id_afectacion=${encodeURIComponent(
                    idAfectacion
                )}`;
        }
    );

    const btnGuardar =
        document.getElementById(
            "btnGuardarCambios"
        );

    btnGuardar?.addEventListener(
        "click",
        () => {
            if (
                panelEdicion &&
                !panelEdicion.hidden
            ) {
                formEditar.requestSubmit();
                return;
            }

            if (
                formAvaluo &&
                !formAvaluo.hidden
            ) {
                formAvaluo.requestSubmit();
                return;
            }

            window.ClienteAPI.mostrarErrorAPI(
                new Error(
                    'No hay cambios abiertos para guardar. Usa "Continuar captura" o "Capturar avalúo" primero.'
                ),
                contenedorError
            );
        }
    );

    const btnNuevoConvenio =
        document.getElementById(
            "btnNuevoConvenio"
        );

    btnNuevoConvenio
        ?.addEventListener(
            "click",
            () => {
                window.location.href =
                    `/pages/nuevoConvenio.html?id_afectacion=${encodeURIComponent(
                        idAfectacion
                    )}`;
            }
        );

    try {
        const sesion =
            await window.AuthAPI.obtenerSesionActual();

        const rol =
            sesion?.user?.rol;

        const puedeCapturar =
            rol === "admin" ||
            rol === "operador";

        if (!puedeCapturar) {
            [
                btnEditarAfectacion,
                btnCapturarAvaluo,
                btnNuevoConvenio,
                document.getElementById(
                    "btnRegistrarIndemnizacion"
                ),
                btnAgregarUnidad,
                btnGuardar
            ].forEach(
                elemento => {
                    if (elemento) {
                        elemento.hidden =
                            true;
                    }
                }
            );

            if (panelEdicion) {
                panelEdicion.hidden =
                    true;
            }

            if (formAvaluo) {
                formAvaluo.hidden =
                    true;
            }
        }

    } catch {
        /*
         * requerirSesion()
         * ya protege la página.
         */
    }
});