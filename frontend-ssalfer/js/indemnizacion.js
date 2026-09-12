document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idAfectacion =
        Number(
            parametros.get("id_afectacion") ||
            parametros.get("id")
        );

    const elementos = {
        nombreProyecto:
            document.getElementById("nombreProyecto"),

        identificadorAfectacion:
            document.getElementById("identificadorAfectacion"),

        btnVolver:
            document.getElementById("btnVolver"),

        valorFinanciero:
            document.getElementById("valorFinanciero"),

        totalPagado:
            document.getElementById("totalPagado"),

        saldoPendiente:
            document.getElementById("saldoPendiente"),

        avanceFinanciero:
            document.getElementById("avanceFinanciero"),

        sinIndemnizacion:
            document.getElementById("sinIndemnizacion"),

        btnCrearIndemnizacion:
            document.getElementById("btnCrearIndemnizacion"),

        formIndemnizacion:
            document.getElementById("formIndemnizacion"),

        estatus:
            document.getElementById("estatus"),

        campoDescripcionEstatus:
            document.getElementById("campoDescripcionEstatus"),

        descripcionEstatus:
            document.getElementById("descripcionEstatus"),

        fechaProgramada:
            document.getElementById("fechaProgramada"),

        fechaResolucion:
            document.getElementById("fechaResolucion"),

        fechaEntrega:
            document.getElementById("fechaEntrega"),

        btnCancelarIndemnizacion:
            document.getElementById("btnCancelarIndemnizacion"),

        indemnizacionRegistrada:
            document.getElementById("indemnizacionRegistrada"),

        estatusActual:
            document.getElementById("estatusActual"),

        btnEditarIndemnizacion:
            document.getElementById("btnEditarIndemnizacion"),

        datoFechaProgramada:
            document.getElementById("datoFechaProgramada"),

        datoFechaResolucion:
            document.getElementById("datoFechaResolucion"),

        datoFechaEntrega:
            document.getElementById("datoFechaEntrega"),

        datoDescripcionEstatus:
            document.getElementById("datoDescripcionEstatus"),

        seccionPagos:
            document.getElementById("seccionPagos"),

        btnRegistrarPago:
            document.getElementById("btnRegistrarPago"),

        pagosBody:
            document.getElementById("pagosBody"),

        sinPagos:
            document.getElementById("sinPagos"),

        formPago:
            document.getElementById("formPago"),

        btnCerrarPago:
            document.getElementById("btnCerrarPago"),

        fechaPago:
            document.getElementById("fechaPago"),

        montoPago:
            document.getElementById("montoPago"),

        idPersonaBeneficiaria:
            document.getElementById("idPersonaBeneficiaria"),

        beneficiarioNombre:
            document.getElementById("beneficiarioNombre"),

        referencia:
            document.getElementById("referencia"),

        medioPago:
            document.getElementById("medioPago"),

        btnCancelarPago:
            document.getElementById("btnCancelarPago")
    };

    if (
        !Number.isInteger(idAfectacion) ||
        idAfectacion <= 0
    ) {
        window.ClienteAPI.mostrarErrorAPI(
            new Error(
                "No se puede abrir Indemnización porque falta un id_afectacion válido."
            )
        );

        return;
    }

    let afectacion = null;
    let contextoPN = null;
    let indemnizacion = null;
    let pagos = [];
    let convenios = [];
    let puedeCapturar = false;

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function moneda(valor) {
        return new Intl.NumberFormat(
            "es-MX",
            {
                style: "currency",
                currency: "MXN"
            }
        ).format(
            Number(valor || 0)
        );
    }

    function fechaVisual(valor) {
        if (!valor) {
            return "—";
        }

        const partes =
            String(valor).split("-");

        return partes.length === 3
            ? `${partes[2]}/${partes[1]}/${partes[0]}`
            : String(valor);
    }

    function etiquetaEstatus(valor) {
        return {
            pendiente: "Pendiente",
            programado: "Programado",
            en_proceso: "En proceso",
            completo: "Completo",
            pagado: "Pagado",
            cancelado: "Cancelado",
            otro: "Otro"
        }[valor] || valor || "—";
    }

    function etiquetaMedioPago(valor) {
        return {
            transferencia: "Transferencia",
            cheque: "Cheque",
            efectivo: "Efectivo",
            deposito: "Depósito",
            otro: "Otro"
        }[valor] || "—";
    }

    async function cargarRol() {
        try {
            const sesion =
                await window.AuthAPI
                    .obtenerSesionActual();

            const rol =
                sesion?.user?.rol;

            puedeCapturar =
                rol === "admin" ||
                rol === "operador";

        } catch {
            puedeCapturar = false;
        }

        [
            elementos.btnCrearIndemnizacion,
            elementos.btnEditarIndemnizacion,
            elementos.btnRegistrarPago
        ].forEach(
            boton => {
                if (boton) {
                    boton.hidden =
                        !puedeCapturar;
                }
            }
        );
    }

    async function cargarContexto() {
        afectacion =
            await window.AfectacionesAPI.obtener(
                idAfectacion
            );

        contextoPN =
            await window.NucleosAPI
                .obtenerProyectoNucleo(
                    afectacion.id_proyecto_nucleo
                );

        elementos.nombreProyecto.textContent =
            contextoPN.nombre_proyecto ||
            "Proyecto";

        elementos.identificadorAfectacion.textContent =
            `AF-${String(
                idAfectacion
            ).padStart(
                3,
                "0"
            )}`;

        document.title =
            `Indemnización | AF-${idAfectacion} | SSALFER`;
    }

    function actualizarDescripcionEstatus() {
        const otro =
            elementos.estatus.value ===
            "otro";

        elementos.campoDescripcionEstatus.hidden =
            !otro;

        elementos.descripcionEstatus.required =
            otro;

        if (!otro) {
            elementos.descripcionEstatus.value =
                "";
        }
    }

    function abrirFormularioIndemnizacion(
        datos = null
    ) {
        if (!puedeCapturar) {
            return;
        }

        elementos.sinIndemnizacion.hidden =
            true;

        elementos.indemnizacionRegistrada.hidden =
            true;

        elementos.formIndemnizacion.hidden =
            false;

        elementos.estatus.value =
            datos?.estatus ||
            "pendiente";

        elementos.descripcionEstatus.value =
            datos?.descripcion_estatus ||
            "";

        elementos.fechaProgramada.value =
            datos?.fecha_programada ||
            "";

        elementos.fechaResolucion.value =
            datos?.fecha_resolucion ||
            "";

        elementos.fechaEntrega.value =
            datos?.fecha_entrega_expediente_pa ||
            "";

        actualizarDescripcionEstatus();

        elementos.formIndemnizacion.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function cerrarFormularioIndemnizacion() {
        elementos.formIndemnizacion.hidden =
            true;

        if (indemnizacion) {
            elementos.indemnizacionRegistrada.hidden =
                false;

        } else {
            elementos.sinIndemnizacion.hidden =
                false;
        }
    }

    function renderIndemnizacion() {
        if (!indemnizacion) {
            elementos.sinIndemnizacion.hidden =
                false;

            elementos.formIndemnizacion.hidden =
                true;

            elementos.indemnizacionRegistrada.hidden =
                true;

            elementos.seccionPagos.hidden =
                true;

            return;
        }

        elementos.sinIndemnizacion.hidden =
            true;

        elementos.formIndemnizacion.hidden =
            true;

        elementos.indemnizacionRegistrada.hidden =
            false;

        elementos.seccionPagos.hidden =
            false;

        elementos.estatusActual.textContent =
            etiquetaEstatus(
                indemnizacion.estatus
            );

        elementos.datoFechaProgramada.textContent =
            fechaVisual(
                indemnizacion.fecha_programada
            );

        elementos.datoFechaResolucion.textContent =
            fechaVisual(
                indemnizacion.fecha_resolucion
            );

        elementos.datoFechaEntrega.textContent =
            fechaVisual(
                indemnizacion.fecha_entrega_expediente_pa
            );

        if (
            indemnizacion.estatus ===
                "otro" &&
            indemnizacion.descripcion_estatus
        ) {
            elementos.datoDescripcionEstatus.hidden =
                false;

            elementos.datoDescripcionEstatus.textContent =
                indemnizacion.descripcion_estatus;

        } else {
            elementos.datoDescripcionEstatus.hidden =
                true;

            elementos.datoDescripcionEstatus.textContent =
                "";
        }
    }

    function actualizarResumenFinanciero() {
        /*
         * La propia página documenta que este indicador
         * es provisional.
         *
         * Valor financiero =
         * Σ(monto_100 + monto_bdt)
         * de los convenios de la afectación.
         */
        const valor =
            convenios.reduce(
                (
                    total,
                    convenio
                ) =>
                    total +
                    Number(
                        convenio.monto_100 ||
                        0
                    ) +
                    Number(
                        convenio.monto_bdt ||
                        0
                    ),
                0
            );

        const totalPagado =
            pagos.reduce(
                (
                    total,
                    pago
                ) =>
                    total +
                    Number(
                        pago.monto ||
                        0
                    ),
                0
            );

        const saldo =
            Math.max(
                valor -
                totalPagado,
                0
            );

        const avance =
            valor > 0
                ? Math.min(
                    (
                        totalPagado /
                        valor
                    ) * 100,
                    100
                )
                : 0;

        elementos.valorFinanciero.textContent =
            moneda(valor);

        elementos.totalPagado.textContent =
            moneda(totalPagado);

        elementos.saldoPendiente.textContent =
            moneda(saldo);

        elementos.avanceFinanciero.textContent =
            `${avance.toFixed(1)}%`;
    }

    function renderPagos() {
        elementos.pagosBody.innerHTML =
            "";

        const tabla =
            elementos.pagosBody.closest(
                ".tabla-contenedor"
            );

        if (!pagos.length) {
            if (tabla) {
                tabla.hidden =
                    true;

                tabla.style.display =
                    "none";
            }

            elementos.sinPagos.hidden =
                false;

            elementos.sinPagos.style.display =
                "";

            actualizarResumenFinanciero();

            return;
        }

        if (tabla) {
            tabla.hidden =
                false;

            tabla.style.display =
                "";
        }

        elementos.sinPagos.hidden =
            true;

        elementos.sinPagos.style.display =
            "none";

        pagos.forEach(
            pago => {
                const fila =
                    document.createElement(
                        "tr"
                    );

                fila.innerHTML = `
                    <td>
                        ${fechaVisual(
                            pago.fecha_pago
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            pago.beneficiario_nombre
                        )}
                    </td>

                    <td>
                        ${moneda(
                            pago.monto
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            etiquetaMedioPago(
                                pago.medio_pago
                            )
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            pago.referencia ||
                            "—"
                        )}
                    </td>
                `;

                elementos.pagosBody.appendChild(
                    fila
                );
            }
        );

        actualizarResumenFinanciero();
    }

    async function cargarDatos() {
        [
            indemnizacion,
            convenios
        ] =
            await Promise.all([
                window.IndemnizacionAPI
                    .listarPorAfectacion(
                        idAfectacion
                    ),

                window.ConveniosAPI
                    .listarPorAfectacion(
                        idAfectacion
                    )
            ]);

        convenios =
            Array.isArray(convenios)
                ? convenios
                : [];

        if (
            indemnizacion?.id_indemnizacion
        ) {
            const respuestaPagos =
                await window.IndemnizacionAPI
                    .listarPagos(
                        indemnizacion.id_indemnizacion
                    );

            pagos =
                Array.isArray(respuestaPagos)
                    ? respuestaPagos
                    : [];

        } else {
            pagos = [];
        }

        renderIndemnizacion();
        renderPagos();
        actualizarResumenFinanciero();
    }

    function abrirFormularioPago() {
        if (
            !puedeCapturar ||
            !indemnizacion
        ) {
            return;
        }

        elementos.formPago.reset();

        elementos.formPago.hidden =
            false;

        elementos.formPago.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function cerrarFormularioPago() {
        elementos.formPago.hidden =
            true;

        elementos.formPago.reset();
    }

    elementos.estatus
        ?.addEventListener(
            "change",
            actualizarDescripcionEstatus
        );

    elementos.btnCrearIndemnizacion
        ?.addEventListener(
            "click",
            () =>
                abrirFormularioIndemnizacion()
        );

    elementos.btnEditarIndemnizacion
        ?.addEventListener(
            "click",
            () =>
                abrirFormularioIndemnizacion(
                    indemnizacion
                )
        );

    elementos.btnCancelarIndemnizacion
        ?.addEventListener(
            "click",
            cerrarFormularioIndemnizacion
        );

    elementos.btnRegistrarPago
        ?.addEventListener(
            "click",
            abrirFormularioPago
        );

    elementos.btnCerrarPago
        ?.addEventListener(
            "click",
            cerrarFormularioPago
        );

    elementos.btnCancelarPago
        ?.addEventListener(
            "click",
            cerrarFormularioPago
        );

    elementos.formIndemnizacion
        ?.addEventListener(
            "submit",
            async event => {
                event.preventDefault();

                if (!puedeCapturar) {
                    return;
                }

                if (
                    !elementos.formIndemnizacion
                        .checkValidity()
                ) {
                    elementos.formIndemnizacion
                        .reportValidity();

                    return;
                }

                if (
                    elementos.estatus.value ===
                        "otro" &&
                    !elementos.descripcionEstatus
                        .value
                        .trim()
                ) {
                    alert(
                        "El estatus 'Otro' requiere una descripción."
                    );

                    return;
                }

                const payload = {
                    estatus:
                        elementos.estatus.value,

                    descripcion_estatus:
                        elementos.descripcionEstatus
                            .value
                            .trim() ||
                        null,

                    fecha_programada:
                        elementos.fechaProgramada.value ||
                        null,

                    fecha_resolucion:
                        elementos.fechaResolucion.value ||
                        null,

                    fecha_entrega_expediente_pa:
                        elementos.fechaEntrega.value ||
                        null
                };

                const submit =
                    event.currentTarget.querySelector(
                        '[type="submit"]'
                    );

                submit.disabled =
                    true;

                try {
                    if (
                        indemnizacion?.id_indemnizacion
                    ) {
                        indemnizacion =
                            await window.IndemnizacionAPI
                                .actualizar(
                                    indemnizacion.id_indemnizacion,
                                    payload
                                );

                    } else {
                        indemnizacion =
                            await window.IndemnizacionAPI
                                .crear(
                                    idAfectacion,
                                    payload
                                );
                    }

                    renderIndemnizacion();

                    elementos.formIndemnizacion.hidden =
                        true;

                    elementos.seccionPagos.hidden =
                        false;

                    alert(
                        "La indemnización se guardó correctamente."
                    );

                } catch (error) {
                    window.ClienteAPI
                        .mostrarErrorAPI(
                            error
                        );

                } finally {
                    submit.disabled =
                        false;
                }
            }
        );

    elementos.formPago
        ?.addEventListener(
            "submit",
            async event => {
                event.preventDefault();

                if (
                    !puedeCapturar ||
                    !indemnizacion
                ) {
                    return;
                }

                if (
                    !elementos.formPago
                        .checkValidity()
                ) {
                    elementos.formPago
                        .reportValidity();

                    return;
                }

                const monto =
                    Number(
                        elementos.montoPago.value
                    );

                if (
                    !Number.isFinite(monto) ||
                    monto <= 0
                ) {
                    alert(
                        "El monto debe ser mayor a cero."
                    );

                    return;
                }

                const payload = {
                    fecha_pago:
                        elementos.fechaPago.value,

                    monto,

                    id_persona_beneficiaria:
                        elementos.idPersonaBeneficiaria
                            .value
                            ? Number(
                                elementos.idPersonaBeneficiaria
                                    .value
                            )
                            : null,

                    beneficiario_nombre:
                        elementos.beneficiarioNombre
                            .value
                            .trim(),

                    referencia:
                        elementos.referencia
                            .value
                            .trim() ||
                        null,

                    medio_pago:
                        elementos.medioPago.value ||
                        null
                };

                if (
                    !payload.beneficiario_nombre
                ) {
                    alert(
                        "El nombre del beneficiario es obligatorio."
                    );

                    return;
                }

                const submit =
                    event.currentTarget.querySelector(
                        '[type="submit"]'
                    );

                submit.disabled =
                    true;

                try {
                    await window.IndemnizacionAPI
                        .registrarPago(
                            indemnizacion.id_indemnizacion,
                            payload
                        );

                    const respuesta =
                        await window.IndemnizacionAPI
                            .listarPagos(
                                indemnizacion.id_indemnizacion
                            );

                    pagos =
                        Array.isArray(respuesta)
                            ? respuesta
                            : [];

                    cerrarFormularioPago();

                    renderPagos();

                    alert(
                        "El pago se guardó correctamente."
                    );

                } catch (error) {
                    window.ClienteAPI
                        .mostrarErrorAPI(
                            error
                        );

                } finally {
                    submit.disabled =
                        false;
                }
            }
        );

    elementos.btnVolver
        ?.addEventListener(
            "click",
            () => {
                window.location.href =
                    `/pages/detalleAfectacion.html?id=${encodeURIComponent(
                        idAfectacion
                    )}`;
            }
        );

    actualizarDescripcionEstatus();

    try {
        await cargarRol();
        await cargarContexto();
        await cargarDatos();

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(
                error
            );
    }
});