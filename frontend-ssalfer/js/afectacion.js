document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const btnNueva =
        document.getElementById(
            "btnNuevaAfectacion"
        );

    const btnCerrar =
        document.getElementById(
            "btnCerrarFormulario"
        );

    const btnCancelar =
        document.getElementById(
            "btnCancelar"
        );

    const formulario =
        document.getElementById(
            "formularioContenedor"
        );

    const form =
        document.getElementById(
            "formAfectacion"
        );

    const condicionEspecial =
        document.getElementById(
            "condicionEspecial"
        );

    const descripcionCondicionCampo =
        document.getElementById(
            "descripcionCondicionCampo"
        );

    const descripcionCondicion =
        document.getElementById(
            "descripcionCondicion"
        );

    const revisionPendiente =
        document.getElementById(
            "revisionPendiente"
        );

    const detalleRevisionCampo =
        document.getElementById(
            "detalleRevisionCampo"
        );

    const filtroEstado =
        document.getElementById(
            "filtroEstado"
        );

    const grid =
        document.getElementById(
            "afectacionesGrid"
        );

    const tipoCop =
        document.getElementById(
            "tipoCop"
        );

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idProyectoNucleo =
        parametros.get(
            "id_proyecto_nucleo"
        );

    function mostrarFormulario() {
        formulario.hidden =
            false;

        btnNueva.innerHTML =
            '<i class="bi bi-x-lg"></i> Cancelar nueva afectación';

        formulario.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    function ocultarFormulario() {
        formulario.hidden =
            true;

        btnNueva.innerHTML =
            '<i class="bi bi-plus-lg"></i> Nueva afectación';

        form.reset();

        actualizarCondicionEspecial();
        actualizarRevisionCOP();
    }

    btnNueva?.addEventListener(
        "click",
        () => {
            if (formulario.hidden) {
                mostrarFormulario();

            } else {
                ocultarFormulario();
            }
        }
    );

    btnCerrar?.addEventListener(
        "click",
        ocultarFormulario
    );

    btnCancelar?.addEventListener(
        "click",
        ocultarFormulario
    );

    function actualizarCondicionEspecial() {
        const esOtro =
            condicionEspecial.value ===
            "otro";

        descripcionCondicionCampo.hidden =
            !esOtro;

        descripcionCondicion.required =
            esOtro;

        if (!esOtro) {
            descripcionCondicion.value =
                "";
        }
    }

    condicionEspecial?.addEventListener(
        "change",
        actualizarCondicionEspecial
    );

    actualizarCondicionEspecial();

    function actualizarRevisionCOP() {
        const requiereRevision =
            revisionPendiente.checked;

        detalleRevisionCampo.hidden =
            !requiereRevision;

        if (!requiereRevision) {
            const detalle =
                document.getElementById(
                    "revisionDetalle"
                );

            if (detalle) {
                detalle.value =
                    "";
            }
        }
    }

    revisionPendiente?.addEventListener(
        "change",
        actualizarRevisionCOP
    );

    actualizarRevisionCOP();

    filtroEstado?.addEventListener(
        "change",
        () => {
            const filtro =
                filtroEstado.value;

            const tarjetas =
                grid.querySelectorAll(
                    ".tarjeta-afectacion"
                );

            tarjetas.forEach(
                tarjeta => {
                    const estado =
                        tarjeta.dataset.estado;

                    tarjeta.style.display =
                        (
                            filtro ===
                            "todas" ||
                            filtro ===
                            estado
                        )
                            ? ""
                            : "none";
                }
            );
        }
    );

    const ETIQUETAS_TIPO_AFECTACION = {
        colectivo:
            "Afectación colectiva",

        individual:
            "Afectación individual"
    };

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatoSuperficie(valor) {
        return valor != null
            ? `${Number(valor).toFixed(6)} ha`
            : "Pendiente";
    }

    function formatoMonto(valor) {
        return valor != null
            ? new Intl.NumberFormat(
                "es-MX",
                {
                    style: "currency",
                    currency: "MXN"
                }
            ).format(
                Number(valor)
            )
            : "Pendiente";
    }

    /*
     * El backend no expone un estatus
     * de afectación propiamente dicho.
     *
     * Esta clasificación solo sirve
     * para la UI.
     */
    function estaCompleta(afectacion) {
        return Boolean(
            afectacion.situacion &&
            afectacion.superficie_afectada_ha !=
                null &&
            afectacion.avaluo_monto !=
                null
        );
    }

    async function cargarAfectaciones() {
        if (!grid) {
            return;
        }

        if (!idProyectoNucleo) {
            grid.innerHTML = `
                <p class="proyectos-lista-vacia">
                    No se especificó el núcleo
                    (falta ?id_proyecto_nucleo=
                    en la URL).
                </p>
            `;

            return;
        }

        try {
            const afectaciones =
                await window.AfectacionesAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            const lista =
                Array.isArray(afectaciones)
                    ? afectaciones
                    : [];

            const completas =
                lista.filter(
                    estaCompleta
                );

            const pendientes =
                lista.filter(
                    afectacion =>
                        !estaCompleta(
                            afectacion
                        )
                );

            const superficieTotal =
                lista.reduce(
                    (
                        acumulado,
                        afectacion
                    ) =>
                        acumulado +
                        Number(
                            afectacion
                                .superficie_afectada_ha ||
                            0
                        ),
                    0
                );

            const elTotal =
                document.getElementById(
                    "totalAfectaciones"
                );

            const elCompletas =
                document.getElementById(
                    "afectacionesCompletas"
                );

            const elPendientes =
                document.getElementById(
                    "afectacionesPendientes"
                );

            const elSuperficie =
                document.getElementById(
                    "superficieTotal"
                );

            if (elTotal) {
                elTotal.textContent =
                    lista.length;
            }

            if (elCompletas) {
                elCompletas.textContent =
                    completas.length;
            }

            if (elPendientes) {
                elPendientes.textContent =
                    pendientes.length;
            }

            if (elSuperficie) {
                elSuperficie.textContent =
                    `${superficieTotal.toFixed(
                        2
                    )} ha`;
            }

            if (lista.length === 0) {
                grid.innerHTML = `
                    <p class="proyectos-lista-vacia">
                        Este núcleo todavía no tiene
                        afectaciones registradas.
                    </p>
                `;

                return;
            }

            grid.innerHTML =
                lista
                    .map(
                        afectacion => {
                            const completa =
                                estaCompleta(
                                    afectacion
                                );

                            const estado =
                                completa
                                    ? "completa"
                                    : "pendiente";

                            return `
                                <article
                                    class="tarjeta-afectacion ${estado}"
                                    data-estado="${estado}">

                                    <div class="tarjeta-superior">

                                        <div>

                                            <span class="identificador">
                                                AF-${String(
                                                    afectacion.id_afectacion
                                                ).padStart(
                                                    3,
                                                    "0"
                                                )}
                                            </span>

                                            <h3>
                                                ${escaparHTML(
                                                    ETIQUETAS_TIPO_AFECTACION[
                                                        afectacion.tipo_afectacion
                                                    ] ||
                                                    afectacion.tipo_afectacion
                                                )}
                                            </h3>

                                        </div>

                                        <span class="estado-badge">
                                            ${
                                                completa
                                                    ? "Completa"
                                                    : "Pendiente"
                                            }
                                        </span>

                                    </div>

                                    <div class="datos-afectacion">

                                        <div>
                                            <span>
                                                Situación
                                            </span>

                                            <strong>
                                                ${escaparHTML(
                                                    afectacion.situacion ||
                                                    "Pendiente"
                                                )}
                                            </strong>
                                        </div>

                                        <div>
                                            <span>
                                                Superficie preliminar
                                            </span>

                                            <strong>
                                                ${formatoSuperficie(
                                                    afectacion.superficie_preliminar_ha
                                                )}
                                            </strong>
                                        </div>

                                        <div>
                                            <span>
                                                Superficie afectada
                                            </span>

                                            <strong>
                                                ${formatoSuperficie(
                                                    afectacion.superficie_afectada_ha
                                                )}
                                            </strong>
                                        </div>

                                        <div>
                                            <span>
                                                Avalúo
                                            </span>

                                            <strong>
                                                ${formatoMonto(
                                                    afectacion.avaluo_monto
                                                )}
                                            </strong>
                                        </div>

                                    </div>

                                    <div class="tarjeta-acciones">

                                        <a
                                            href="/pages/detalleAfectacion.html?id=${encodeURIComponent(
                                                afectacion.id_afectacion
                                            )}"
                                            class="btn-detalle">

                                            <i class="bi bi-eye"></i>
                                            Ver detalle

                                        </a>

                                    </div>

                                </article>
                            `;
                        }
                    )
                    .join("");

        } catch (error) {
            grid.innerHTML = `
                <p class="proyectos-lista-vacia">
                    No se pudieron cargar
                    las afectaciones.
                </p>
            `;

            window.ClienteAPI.mostrarErrorAPI(
                error
            );
        }
    }

    cargarAfectaciones();

    async function prepararCatalogoCOP() {
        if (!tipoCop) {
            return;
        }

        tipoCop.innerHTML = `
            <option value="">
                Seleccionar
            </option>
        `;

        try {
            const opciones =
                await window.CatalogosAPI
                    .obtenerOperativo(
                        "tipo_cop_operativo"
                    );

            (
                Array.isArray(opciones)
                    ? opciones
                    : []
            ).forEach(
                opcion => {
                    const valor =
                        opcion.id_catalogo_opcion;

                    const texto =
                        opcion.nombre ??
                        opcion.codigo ??
                        String(valor);

                    const option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        valor;

                    option.textContent =
                        texto;

                    tipoCop.appendChild(
                        option
                    );
                }
            );

        } catch (error) {
            console.error(
                'No se pudo cargar el catálogo "tipo_cop_operativo":',
                error
            );
        }
    }

    prepararCatalogoCOP();

    function obtenerDatosFormulario() {
        const datos =
            new FormData(form);

        const valorNumerico =
            nombre => {
                const valor =
                    datos.get(nombre);

                if (
                    valor === null ||
                    valor === ""
                ) {
                    return null;
                }

                return Number(valor);
            };

        const idCop =
            datos.get(
                "id_tipo_cop_operativo"
            );

        const resultado = {
            tipo_afectacion:
                datos.get(
                    "tipo_afectacion"
                ),

            superficie_preliminar_ha:
                valorNumerico(
                    "superficie_preliminar_ha"
                ),

            superficie_afectada_ha:
                valorNumerico(
                    "superficie_afectada_ha"
                ),

            situacion:
                datos
                    .get("situacion")
                    ?.trim() ||
                null,

            condicion_especial:
                datos.get(
                    "condicion_especial"
                ) ||
                null,

            descripcion_condicion:
                datos
                    .get(
                        "descripcion_condicion"
                    )
                    ?.trim() ||
                null,

            avaluo_monto:
                valorNumerico(
                    "avaluo_monto"
                ),

            avaluo_fecha:
                datos.get(
                    "avaluo_fecha"
                ) ||
                null,

            avaluo_referencia:
                datos
                    .get(
                        "avaluo_referencia"
                    )
                    ?.trim() ||
                null,

            avaluo_institucion:
                datos
                    .get(
                        "avaluo_institucion"
                    )
                    ?.trim() ||
                null,

            id_tipo_cop_operativo:
                idCop
                    ? Number(idCop)
                    : null,

            tipo_cop_revision_pendiente:
                datos.get(
                    "tipo_cop_revision_pendiente"
                ) === "on",

            tipo_cop_revision_detalle:
                datos
                    .get(
                        "tipo_cop_revision_detalle"
                    )
                    ?.trim() ||
                null,

            observaciones:
                datos
                    .get("observaciones")
                    ?.trim() ||
                null
        };

        if (
            resultado.condicion_especial !==
            "otro"
        ) {
            resultado.descripcion_condicion =
                null;
        }

        if (
            !resultado.tipo_cop_revision_pendiente
        ) {
            resultado.tipo_cop_revision_detalle =
                null;
        }

        return resultado;
    }

    function validarDatos(datos) {
        const errores = [];

        if (
            datos.tipo_afectacion !==
                "individual" &&
            datos.tipo_afectacion !==
                "colectivo"
        ) {
            errores.push(
                "Selecciona un tipo de afectación válido."
            );
        }

        if (
            datos.condicion_especial ===
                "otro" &&
            !datos.descripcion_condicion
        ) {
            errores.push(
                "Debes describir la condición especial."
            );
        }

        if (
            datos.superficie_preliminar_ha !==
                null &&
            datos.superficie_preliminar_ha <
                0
        ) {
            errores.push(
                "La superficie preliminar no puede ser negativa."
            );
        }

        if (
            datos.superficie_afectada_ha !==
                null &&
            datos.superficie_afectada_ha <
                0
        ) {
            errores.push(
                "La superficie afectada no puede ser negativa."
            );
        }

        if (
            datos.avaluo_monto !==
                null &&
            datos.avaluo_monto <
                0
        ) {
            errores.push(
                "El monto del avalúo no puede ser negativo."
            );
        }

        return errores;
    }

    form?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            const datos =
                obtenerDatosFormulario();

            const errores =
                validarDatos(datos);

            if (errores.length > 0) {
                alert(
                    errores.join("\n")
                );

                return;
            }

            if (!idProyectoNucleo) {
                alert(
                    "No se puede registrar la afectación porque falta el id_proyecto_nucleo."
                );

                return;
            }

            const btnGuardar =
                form.querySelector(
                    "[type='submit']"
                );

            if (btnGuardar) {
                btnGuardar.disabled =
                    true;
            }

            try {
                const afectacionCreada =
                    await window.AfectacionesAPI.crear(
                        Number(
                            idProyectoNucleo
                        ),
                        datos
                    );

                alert(
                    "La afectación se guardó correctamente."
                );

                window.location.href =
                    `/pages/detalleAfectacion.html?id=${encodeURIComponent(
                        afectacionCreada.id_afectacion
                    )}`;

            } catch (error) {
                window.ClienteAPI.mostrarErrorAPI(
                    error
                );

            } finally {
                if (btnGuardar) {
                    btnGuardar.disabled =
                        false;
                }
            }
        }
    );

    (async () => {
        try {
            const sesion =
                await window.AuthAPI.obtenerSesionActual();

            const rol =
                sesion?.user?.rol;

            const puedeCapturar =
                rol === "admin" ||
                rol === "operador";

            if (!puedeCapturar) {
                if (btnNueva) {
                    btnNueva.hidden =
                        true;
                }

                if (formulario) {
                    formulario.hidden =
                        true;
                }
            }

        } catch {
            /*
             * requerirSesion()
             * ya protege la página.
             */
        }
    })();

    if (formulario) {
        formulario.hidden =
            true;
    }
});