document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(
            window.location.search
        );

    const idProyectoNucleo = Number(
        parametros.get("id_proyecto_nucleo") ||
        document.querySelector(".contenedor")
            ?.dataset.proyectoNucleoId
    );

    if (
        !Number.isInteger(idProyectoNucleo) ||
        idProyectoNucleo <= 0
    ) {
        alert(
            "Falta un id_proyecto_nucleo válido."
        );

        window.location.href =
            "/dashboard.html";

        return;
    }

    const elementos = {
        btnVolver:
            document.getElementById(
                "btnVolver"
            ),

        btnNuevoPadron:
            document.getElementById(
                "btnNuevoPadron"
            ),

        btnCancelarPadron:
            document.getElementById(
                "btnCancelarPadron"
            ),

        formulario:
            document.getElementById(
                "formularioPadron"
            ),

        form:
            document.getElementById(
                "formPadron"
            ),

        tabla:
            document.getElementById(
                "padronesTabla"
            ),

        nombreNucleo:
            document.getElementById(
                "nombreNucleo"
            ),

        nombreProyecto:
            document.getElementById(
                "nombreProyecto"
            ),

        totalPadrones:
            document.getElementById(
                "totalPadrones"
            ),

        totalPadronesTabla:
            document.getElementById(
                "totalPadronesTabla"
            ),

        padronReciente:
            document.getElementById(
                "padronReciente"
            ),

        fechaPadron:
            document.getElementById(
                "fechaPadron"
            ),

        numeroEjidatarios:
            document.getElementById(
                "numeroEjidatarios"
            ),

        fuente:
            document.getElementById(
                "fuente"
            ),

        idDocumento:
            document.getElementById(
                "idDocumento"
            )
    };

    const tituloFormulario =
        elementos.formulario
            ?.querySelector("h2");

    const descripcionFormulario =
        elementos.formulario
            ?.querySelector(
                ".bloque-titulo-info p"
            );

    const botonGuardar =
        elementos.form
            ?.querySelector(
                'button[type="submit"]'
            );

    let padrones = [];
    let nucleo = null;
    let idPadronEditando = null;
    let puedeCapturar = false;


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

    function texto(valor, respaldo = "—") {
        if (
            valor === null ||
            valor === undefined ||
            valor === ""
        ) {
            return respaldo;
        }

        return String(valor);
    }

    function mostrarFormularioVisible(
        visible
    ) {
        if (!elementos.formulario) {
            return;
        }

        elementos.formulario.hidden =
            !visible;

        elementos.formulario.style.display =
            visible ? "" : "none";
    }

    function numeroOpcional(elemento) {
        const valor =
            elemento?.value?.trim();

        if (!valor) {
            return null;
        }

        const numero =
            Number(valor);

        return Number.isInteger(numero) &&
            numero >= 0

            ? numero
            : NaN;
    }

    function idOpcional(elemento) {
        const valor =
            elemento?.value?.trim();

        if (!valor) {
            return null;
        }

        const numero =
            Number(valor);

        return Number.isInteger(numero) &&
            numero > 0

            ? numero
            : NaN;
    }

    function textoOpcional(elemento) {
        const valor =
            elemento?.value?.trim();

        return valor || null;
    }

    function formatoFecha(fecha) {
        return fecha || "—";
    }


    /* =====================================================
                        SESIÓN / PERMISOS
    ====================================================== */

    try {
        const sesion =
            await window.AuthAPI
                .obtenerSesionActual();

        const rol =
            sesion?.user?.rol;

        puedeCapturar =
            rol === "admin" ||
            rol === "operador";

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(error);

        return;
    }

    if (
        !puedeCapturar &&
        elementos.btnNuevoPadron
    ) {
        elementos.btnNuevoPadron.hidden =
            true;

        elementos.btnNuevoPadron
            .style.display = "none";
    }


    /* =====================================================
                        CONTEXTO
    ====================================================== */

    async function cargarContexto() {
        nucleo =
            await window.NucleosAPI
                .obtenerProyectoNucleo(
                    idProyectoNucleo
                );

        elementos.nombreNucleo.textContent =
            texto(
                nucleo.nombre_nucleo,
                "Núcleo agrario"
            );

        elementos.nombreProyecto.textContent =
            texto(
                nucleo.nombre_proyecto,
                "Proyecto"
            );
    }


    /* =====================================================
                        DOCUMENTOS
    ====================================================== */

    async function cargarDocumentos() {
        if (
            !elementos.idDocumento ||
            !window.DocumentosAPI
        ) {
            return;
        }

        elementos.idDocumento.innerHTML = `
            <option value="">
                Sin documento asociado
            </option>
        `;

        try {
            const consultas = [
                window.DocumentosAPI
                    .listarPorEntidad(
                        "proyecto_nucleo",
                        idProyectoNucleo
                    )
            ];

            if (nucleo?.id_nucleo) {
                consultas.push(
                    window.DocumentosAPI
                        .listarPorEntidad(
                            "nucleo_agrario",
                            nucleo.id_nucleo
                        )
                );
            }

            const resultados =
                await Promise.allSettled(
                    consultas
                );

            const documentos = [];
            const ids = new Set();

            resultados.forEach(resultado => {
                if (
                    resultado.status !==
                    "fulfilled"
                ) {
                    return;
                }

                const lista =
                    Array.isArray(
                        resultado.value
                    )
                        ? resultado.value
                        : [];

                lista.forEach(documento => {
                    const id =
                        Number(
                            documento.id_documento
                        );

                    if (
                        !id ||
                        ids.has(id)
                    ) {
                        return;
                    }

                    ids.add(id);
                    documentos.push(documento);
                });
            });

            documentos.forEach(documento => {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    documento.id_documento;

                option.textContent =
                    `#${documento.id_documento} — ${
                        documento.titulo ||
                        documento.tipo_documento ||
                        "Documento"
                    }`;

                elementos.idDocumento
                    .appendChild(option);
            });

        } catch (error) {
            console.warn(
                "No fue posible cargar documentos asociados al núcleo.",
                error
            );
        }
    }


    /* =====================================================
                        CARGAR PADRONES
    ====================================================== */

    async function cargarPadrones() {
        try {
            const respuesta =
                await window.PadronesAPI
                    .listarPorProyectoNucleo(
                        idProyectoNucleo
                    );

            padrones =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            mostrarPadrones();

        } catch (error) {
            window.ClienteAPI
                .mostrarErrorAPI(error);
        }
    }


    /* =====================================================
                        RESUMEN
    ====================================================== */

    function obtenerPadronReciente() {
        if (!padrones.length) {
            return null;
        }

        return [...padrones].sort(
            (a, b) => {
                const fechaA =
                    a.fecha_padron || "";

                const fechaB =
                    b.fecha_padron || "";

                if (fechaA !== fechaB) {
                    return fechaB.localeCompare(
                        fechaA
                    );
                }

                return Number(b.id_padron) -
                    Number(a.id_padron);
            }
        )[0];
    }

    function actualizarResumen() {
        const total =
            padrones.length;

        elementos.totalPadrones.textContent =
            total;

        elementos.totalPadronesTabla.textContent =
            total;

        const reciente =
            obtenerPadronReciente();

        elementos.padronReciente.textContent =
            reciente
                ? formatoFecha(
                    reciente.fecha_padron
                )
                : "—";
    }


    /* =====================================================
                        TABLA
    ====================================================== */

    function mostrarPadrones() {
        if (!elementos.tabla) {
            return;
        }

        elementos.tabla.innerHTML = "";

        if (!padrones.length) {
            elementos.tabla.innerHTML = `
                <tr>
                    <td
                        colspan="6"
                        class="tabla-vacia">
                        No hay padrones registrados.
                    </td>
                </tr>
            `;

            actualizarResumen();
            return;
        }

        padrones.forEach(padron => {
            const fila =
                document.createElement("tr");

            const accionesEdicion =
                puedeCapturar
                    ? `
                        <button
                            type="button"
                            class="btn-tabla"
                            title="Editar padrón"
                            data-editar-padron="${padron.id_padron}">
                            <i class="bi bi-pencil"></i>
                        </button>
                    `
                    : "";

            fila.innerHTML = `
                <td>
                    #${escaparHTML(
                        padron.id_padron
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        formatoFecha(
                            padron.fecha_padron
                        )
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        padron
                            .numero_ejidatarios_comuneros
                        ?? "—"
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        padron.fuente || "—"
                    )}
                </td>

                <td>
                    ${
                        padron.id_documento
                            ? `
                                <span class="etiqueta-documento">
                                    <i class="bi bi-paperclip"></i>
                                    Documento #${escaparHTML(
                                        padron.id_documento
                                    )}
                                </span>
                            `
                            : `
                                <span class="etiqueta-sin-documento">
                                    Sin documento
                                </span>
                            `
                    }
                </td>

                <td>
                    <div class="acciones-tabla">

                        <button
                            type="button"
                            class="btn-tabla"
                            title="Consultar padrón"
                            data-consultar-padron="${padron.id_padron}">
                            <i class="bi bi-eye"></i>
                        </button>

                        ${accionesEdicion}

                    </div>
                </td>
            `;

            elementos.tabla.appendChild(
                fila
            );
        });

        conectarAccionesTabla();
        actualizarResumen();
    }


    /* =====================================================
                        CONSULTAR
    ====================================================== */

    function consultarPadron(id) {
        const padron =
            padrones.find(
                item =>
                    Number(item.id_padron) ===
                    Number(id)
            );

        if (!padron) {
            return;
        }

        alert(
            [
                `Padrón #${padron.id_padron}`,
                "",
                `Fecha: ${padron.fecha_padron || "—"}`,
                `Ejidatarios / comuneros: ${padron.numero_ejidatarios_comuneros ?? "—"}`,
                `Fuente: ${padron.fuente || "—"}`,
                `Documento: ${padron.id_documento ? `#${padron.id_documento}` : "—"}`
            ].join("\n")
        );
    }


    /* =====================================================
                        FORMULARIO
    ====================================================== */

    function limpiarFormulario() {
        elementos.form?.reset();

        idPadronEditando = null;

        if (tituloFormulario) {
            tituloFormulario.textContent =
                "Registrar nuevo padrón";
        }

        if (descripcionFormulario) {
            descripcionFormulario.textContent =
                "Agrega una nueva versión del padrón al historial del núcleo.";
        }

        if (botonGuardar) {
            botonGuardar.innerHTML = `
                <i class="bi bi-check-lg"></i>
                Guardar padrón
            `;
        }

        document
            .querySelectorAll(".invalido")
            .forEach(elemento => {
                elemento.classList.remove(
                    "invalido"
                );
            });
    }

    function abrirNuevoPadron() {
        if (!puedeCapturar) {
            return;
        }

        limpiarFormulario();

        mostrarFormularioVisible(true);

        elementos.formulario?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

        elementos.fechaPadron?.focus();
    }

    function abrirEdicion(id) {
        if (!puedeCapturar) {
            return;
        }

        const padron =
            padrones.find(
                item =>
                    Number(item.id_padron) ===
                    Number(id)
            );

        if (!padron) {
            return;
        }

        idPadronEditando =
            Number(padron.id_padron);

        elementos.fechaPadron.value =
            padron.fecha_padron || "";

        elementos.numeroEjidatarios.value =
            padron
                .numero_ejidatarios_comuneros
            ?? "";

        elementos.fuente.value =
            padron.fuente || "";

        elementos.idDocumento.value =
            padron.id_documento || "";

        if (
            padron.id_documento &&
            elementos.idDocumento.value === ""
        ) {
            const option =
                document.createElement(
                    "option"
                );

            option.value =
                padron.id_documento;

            option.textContent =
                `Documento #${padron.id_documento}`;

            elementos.idDocumento
                .appendChild(option);

            elementos.idDocumento.value =
                padron.id_documento;
        }

        if (tituloFormulario) {
            tituloFormulario.textContent =
                `Editar padrón #${padron.id_padron}`;
        }

        if (descripcionFormulario) {
            descripcionFormulario.textContent =
                "Modifica los datos registrados para este corte de padrón.";
        }

        if (botonGuardar) {
            botonGuardar.innerHTML = `
                <i class="bi bi-check-lg"></i>
                Guardar cambios
            `;
        }

        mostrarFormularioVisible(true);

        elementos.formulario?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }


    /* =====================================================
                        VALIDACIÓN
    ====================================================== */

    function validarFormulario() {
        const fecha =
            elementos.fechaPadron.value.trim();

        const cantidad =
            numeroOpcional(
                elementos.numeroEjidatarios
            );

        const documento =
            idOpcional(
                elementos.idDocumento
            );

        elementos.fechaPadron
            .classList.remove("invalido");

        elementos.numeroEjidatarios
            .classList.remove("invalido");

        elementos.idDocumento
            ?.classList.remove("invalido");

        if (
            !fecha &&
            cantidad === null
        ) {
            elementos.fechaPadron
                .classList.add("invalido");

            elementos.numeroEjidatarios
                .classList.add("invalido");

            alert(
                "Debes indicar al menos la fecha del padrón o la cantidad de ejidatarios/comuneros."
            );

            return false;
        }

        if (Number.isNaN(cantidad)) {
            elementos.numeroEjidatarios
                .classList.add("invalido");

            alert(
                "La cantidad debe ser un número entero mayor o igual a cero."
            );

            return false;
        }

        if (Number.isNaN(documento)) {
            elementos.idDocumento
                ?.classList.add("invalido");

            alert(
                "El documento seleccionado no es válido."
            );

            return false;
        }

        return true;
    }


    /* =====================================================
                        GUARDAR
    ====================================================== */

    elementos.form?.addEventListener(
        "submit",
        async evento => {
            evento.preventDefault();

            if (!puedeCapturar) {
                return;
            }

            if (!validarFormulario()) {
                return;
            }

            const payload = {
                fecha_padron:
                    textoOpcional(
                        elementos.fechaPadron
                    ),

                numero_ejidatarios_comuneros:
                    numeroOpcional(
                        elementos.numeroEjidatarios
                    ),

                fuente:
                    textoOpcional(
                        elementos.fuente
                    ),

                id_documento:
                    idOpcional(
                        elementos.idDocumento
                    )
            };

            try {
                if (idPadronEditando) {
                    await window.PadronesAPI
                        .actualizar(
                            idPadronEditando,
                            payload
                        );

                    alert(
                        "Padrón actualizado correctamente."
                    );

                } else {
                    await window.PadronesAPI
                        .crear(
                            idProyectoNucleo,
                            payload
                        );

                    alert(
                        "Padrón registrado correctamente."
                    );
                }

                await cargarPadrones();

                limpiarFormulario();
                mostrarFormularioVisible(false);

            } catch (error) {
                window.ClienteAPI
                    .mostrarErrorAPI(error);
            }
        }
    );


    /* =====================================================
                        BOTONES
    ====================================================== */

    elementos.btnNuevoPadron
        ?.addEventListener(
            "click",
            abrirNuevoPadron
        );

    elementos.btnCancelarPadron
        ?.addEventListener(
            "click",
            () => {
                limpiarFormulario();
                mostrarFormularioVisible(false);
            }
        );

    elementos.btnVolver
        ?.addEventListener(
            "click",
            () => {
                window.location.href =
                    `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(
                        idProyectoNucleo
                    )}`;
            }
        );


    /* =====================================================
                    ACCIONES DE TABLA
    ====================================================== */

    function conectarAccionesTabla() {
        elementos.tabla
            ?.querySelectorAll(
                "[data-consultar-padron]"
            )
            .forEach(boton => {
                boton.addEventListener(
                    "click",
                    () => consultarPadron(
                        boton.dataset
                            .consultarPadron
                    )
                );
            });

        elementos.tabla
            ?.querySelectorAll(
                "[data-editar-padron]"
            )
            .forEach(boton => {
                boton.addEventListener(
                    "click",
                    () => abrirEdicion(
                        boton.dataset
                            .editarPadron
                    )
                );
            });
    }


    /* =====================================================
                        INICIALIZACIÓN
    ====================================================== */

    try {
        await cargarContexto();
        await cargarDocumentos();
        await cargarPadrones();

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(error);
    }
});