document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros =
        new URLSearchParams(window.location.search);

    const idFifonafe = Number(
        parametros.get("id_fifonafe") ||
        parametros.get("id") ||
        document.querySelector(".contenedor")
            ?.dataset.fifonafeId
    );

    const idProyectoNucleo = Number(
        parametros.get("id_proyecto_nucleo")
    );

    if (
        !Number.isInteger(idFifonafe) ||
        idFifonafe <= 0 ||
        !Number.isInteger(idProyectoNucleo) ||
        idProyectoNucleo <= 0
    ) {
        await window.SSALFER_UI.verDatos("No se pudo abrir la pantalla", { "Mensaje": "Abre este registro desde la ficha de su proyecto o núcleo." });

        window.location.href = "/dashboard.html";
        return;
    }


    /* =====================================================
                        ELEMENTOS
    ====================================================== */

    const elementos = {
        btnVolver:
            document.getElementById("btnVolver"),

        btnEditar:
            document.getElementById(
                "btnEditarFifonafe"
            ),

        btnEditarDatos:
            document.getElementById(
                "btnEditarDatos"
            ),

        btnAgregarAfectacion:
            document.getElementById(
                "btnAgregarAfectacion"
            ),

        btnAgregarEvento:
            document.getElementById(
                "btnAgregarEvento"
            ),

        idTramite:
            document.getElementById(
                "idTramite"
            ),

        ambito:
            document.getElementById(
                "ambito"
            ),

        estatus:
            document.getElementById(
                "estatus"
            ),

        estadoFifonafe:
            document.getElementById(
                "estadoFifonafe"
            ),

        acuseFifonafe:
            document.getElementById(
                "acuseFifonafe"
            ),

        hayConflictos:
            document.getElementById(
                "hayConflictos"
            ),

        resultadoNoConflictos:
            document.getElementById(
                "resultadoNoConflictos"
            ),

        referenciaExpediente:
            document.getElementById(
                "referenciaExpediente"
            ),

        datoResultadoConflictos:
            document.getElementById(
                "datoResultadoConflictos"
            ),

        totalAfectaciones:
            document.getElementById(
                "totalAfectaciones"
            ),

        afectacionesTabla:
            document.getElementById(
                "afectacionesTabla"
            ),

        totalEventos:
            document.getElementById(
                "totalEventos"
            ),

        eventosTabla:
            document.getElementById(
                "eventosTabla"
            ),

        observaciones:
            document.getElementById(
                "observaciones"
            )
    };


    /* =====================================================
                        ESTADO
    ====================================================== */

    let tramite = null;
    let documentosRelacionados = new Map();
    let todasAfectaciones = [];
    let afectaciones = [];
    let eventos = [];

    let tiposEvento = [];
    let tipoEventoPorId = new Map();


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

    function texto(valor) {
        return (
            valor === null ||
            valor === undefined ||
            valor === ""
        )
            ? "—"
            : String(valor);
    }

    function formatoConflictos(valor) {
        if (valor === true) {
            return "Sí";
        }

        if (valor === false) {
            return "No";
        }

        return "Sin definir";
    }

    function nombreTipoEvento(id) {
        const opcion =
            tipoEventoPorId.get(
                Number(id)
            );

        return opcion?.nombre ||
            opcion?.codigo ||
            (id ? `#${id}` : "—");
    }


    /* =====================================================
                    CARGAR DATOS REALES
    ====================================================== */

    async function cargarDatos() {
        const [
            tramites,
            afectacionesNucleo,
            tipos,
            eventosReales
        ] = await Promise.all([
            window.FifonafeAPI
                .listarPorProyectoNucleo(
                    idProyectoNucleo
                ),

            window.AfectacionesAPI
                .listarPorProyectoNucleo(
                    idProyectoNucleo
                ),

            window.CatalogosAPI
                .obtenerOperativo(
                    "tipo_evento_fifonafe"
                ),

            window.FifonafeAPI
                .listarEventos(
                    idFifonafe
                )
        ]);

        tramite =
            (Array.isArray(tramites)
                ? tramites
                : []
            ).find(item =>
                Number(
                    item.id_tramite_fifonafe
                ) === idFifonafe
            );

        if (!tramite) {
            throw new Error(
                "El trámite FIFONAFE no fue encontrado."
            );
        }

        tiposEvento =
            Array.isArray(tipos)
                ? tipos
                : [];

        tipoEventoPorId =
            new Map(
                tiposEvento.map(item => [
                    Number(
                        item.id_catalogo_opcion
                    ),
                    item
                ])
            );

        eventos =
            Array.isArray(eventosReales)
                ? eventosReales
                : [];

        const idsRelacionados =
            new Set(
                (
                    Array.isArray(
                        tramite.afectaciones
                    )
                        ? tramite.afectaciones
                        : []
                ).map(item =>
                    Number(
                        item.id_afectacion
                    )
                )
            );

        todasAfectaciones =
            Array.isArray(afectacionesNucleo)
                ? afectacionesNucleo
                : [];

        afectaciones =
            todasAfectaciones.filter(item =>
                idsRelacionados.has(
                    Number(
                        item.id_afectacion
                    )
                )
            );

        const contexto = await window.NucleosAPI.obtenerProyectoNucleo(idProyectoNucleo);
        documentosRelacionados = await window.SSALFER_DOCUMENTOS.cargar([
            ["proyecto_nucleo", idProyectoNucleo],
            ["nucleo_agrario", contexto.id_nucleo],
            ["tramite_fifonafe", idFifonafe],
            ...eventos.map(evento => ["tramite_fifonafe_evento", evento.id_evento_fifonafe])
        ]);
    }


    /* =====================================================
                    INFORMACIÓN GENERAL
    ====================================================== */

    function mostrarInformacion() {
        elementos.idTramite.textContent =
            tramite.referencia_expediente || "Trámite FIFONAFE";

        elementos.ambito.textContent =
            texto(tramite.ambito);

        elementos.estatus.textContent =
            texto(tramite.estatus);

        elementos.estadoFifonafe.textContent =
            texto(tramite.estatus);

        elementos.acuseFifonafe.textContent =
            window.SSALFER_FORMAT?.formatearFecha(
                tramite.acuse_fifonafe_fecha
            ) || texto(tramite.acuse_fifonafe_fecha);

        elementos.hayConflictos.textContent =
            formatoConflictos(
                tramite.hay_conflictos
            );

        elementos.resultadoNoConflictos
            .textContent =
            texto(
                tramite.resultado_no_conflictos
            );

        elementos.datoResultadoConflictos
            .style.opacity =
            tramite.hay_conflictos === false
                ? "1"
                : ".55";

        if (elementos.referenciaExpediente) {
            elementos.referenciaExpediente.textContent =
                texto(tramite.referencia_expediente);
        }

        if (elementos.observaciones) {
            elementos.observaciones.textContent =
                tramite.observaciones?.trim()
                    ? tramite.observaciones
                    : "No hay observaciones registradas.";
        }
    }


    /* =====================================================
                        AFECTACIONES
    ====================================================== */

    function mostrarAfectaciones() {
        elementos.totalAfectaciones.textContent =
            afectaciones.length;

        elementos.afectacionesTabla.innerHTML =
            "";

        if (!afectaciones.length) {
            elementos.afectacionesTabla.innerHTML = `
                <tr>
                    <td
                        colspan="4"
                        class="tabla-vacia">
                        No hay afectaciones relacionadas.
                    </td>
                </tr>
            `;

            return;
        }

        afectaciones.forEach(afectacion => {
            const fila =
                document.createElement("tr");

            const referencia =
                afectacion.situacion || "Sin descripción registrada";

            const tipo =
                afectacion.tipo_afectacion ||
                "—";

            fila.innerHTML = `
                <td>
                    ${escaparHTML(
                        [window.SSALFER_FORMAT.etiquetaCodigo(afectacion.tipo_afectacion),
                            afectacion.superficie_afectada_ha == null ? null : `${Number(afectacion.superficie_afectada_ha).toLocaleString("es-MX")} ha`].filter(Boolean).join(" · ")
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        referencia
                    )}
                </td>

                <td>
                    ${escaparHTML(
                        tipo
                    )}
                </td>

                <td>
                    <button
                        type="button"
                        class="btn-tabla"
                        data-ver-afectacion="${afectacion.id_afectacion}">
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            `;

            elementos.afectacionesTabla
                .appendChild(fila);
        });
    }


    elementos.afectacionesTabla?.addEventListener("click", event => {
        const boton = event.target.closest("[data-ver-afectacion]");
        if (!boton) return;

        const idAfectacion = Number(boton.dataset.verAfectacion);

        if (!Number.isInteger(idAfectacion) || idAfectacion <= 0) {
            return;
        }

        window.location.href =
            `/pages/detalleAfectacion.html?id=${encodeURIComponent(idAfectacion)}`;
    });


    /* =====================================================
                        EVENTOS
    ====================================================== */

    function mostrarEventos() {
        elementos.totalEventos.textContent =
            eventos.length;

        elementos.eventosTabla.innerHTML =
            "";

        if (!eventos.length) {
            elementos.eventosTabla.innerHTML = `
                <tr>
                    <td
                        colspan="8"
                        class="tabla-vacia">
                        No hay eventos registrados.
                    </td>
                </tr>
            `;

            return;
        }

        [...eventos]
            .sort(
                (a, b) =>
                    Number(a.ordinal) -
                    Number(b.ordinal)
            )
            .forEach(evento => {
                const fila =
                    document.createElement("tr");

                const fechaOficio =
                    window.SSALFER_FORMAT?.formatearFecha(
                        evento.fecha_oficio
                    ) || texto(evento.fecha_oficio);

                const fechaEvento =
                    window.SSALFER_FORMAT?.formatearFecha(
                        evento.fecha_evento
                    ) || texto(evento.fecha_evento);

                fila.innerHTML = `
                    <td>
                        ${escaparHTML(
                            evento.ordinal
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            nombreTipoEvento(
                                evento.id_tipo_evento
                            )
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            evento.origen || "—"
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            evento.destino || "—"
                        )}
                    </td>

                    <td>
                        ${escaparHTML(
                            evento.numero_oficio || "—"
                        )}
                    </td>

                    <td>
                        ${escaparHTML(fechaOficio)}
                    </td>

                    <td>
                        ${escaparHTML(fechaEvento)}
                    </td>

                    <td>
                        ${
                            evento.id_documento
                                ? `
                                    <span class="etiqueta-tabla">
                                        <i class="bi bi-paperclip"></i>
                                        ${escaparHTML(
                                            window.SSALFER_DOCUMENTOS.nombre(documentosRelacionados, evento.id_documento)
                                        )}
                                    </span>
                                `
                                : "—"
                        }
                    </td>

                    <td>
                        <div class="acciones-tabla">

                            <button
                                type="button"
                                class="btn-tabla"
                                data-ver-evento="${evento.id_evento_fifonafe}">
                                <i class="bi bi-eye"></i>
                            </button>

                            <button
                                type="button"
                                class="btn-tabla"
                                data-editar-evento="${evento.id_evento_fifonafe}"
                                aria-label="Editar evento">
                                <i class="bi bi-pencil"></i>
                            </button>

                            <button
                                type="button"
                                class="btn-tabla"
                                data-eliminar-evento="${evento.id_evento_fifonafe}"
                                aria-label="Dar de baja evento">
                                <i class="bi bi-trash"></i>
                            </button>

                        </div>
                    </td>
                `;

                elementos.eventosTabla
                    .appendChild(fila);
            });
    }


    /* =====================================================
                    FORMULARIOS MODALES
    ====================================================== */

    function formularioModal({ titulo, contenido, textoGuardar = "Guardar", onSubmit }) {
        return new Promise(resolve => {
            const fondo = document.createElement("div");
            fondo.className = "ssalfer-modal-backdrop";

            fondo.innerHTML = `
                <section class="ssalfer-modal" role="dialog" aria-modal="true" aria-labelledby="fifonafeModalTitle">
                    <form class="fifonafe-modal-form">
                        <header class="ssalfer-modal__header">
                            <h2 id="fifonafeModalTitle" class="ssalfer-modal__title">${escaparHTML(titulo)}</h2>
                            <button type="button" class="ssalfer-modal__close" data-cerrar aria-label="Cerrar">×</button>
                        </header>
                        <div class="ssalfer-modal__body">${contenido}</div>
                        <footer class="ssalfer-modal__footer">
                            <button type="button" class="ssalfer-modal__button" data-cerrar>Cancelar</button>
                            <button type="submit" class="ssalfer-modal__button ssalfer-modal__button--primary">${escaparHTML(textoGuardar)}</button>
                        </footer>
                    </form>
                </section>
            `;

            const form = fondo.querySelector("form");
            const datosIniciales = new FormData(form);
            const submit = form.querySelector('button[type="submit"]');
            let cerrando = false;

            const cerrar = valor => {
                if (cerrando) return;
                cerrando = true;
                document.removeEventListener("keydown", onKeydown);
                fondo.remove();
                resolve(valor);
            };

            const onKeydown = event => {
                if (event.key === "Escape") cerrar(false);
            };

            fondo.addEventListener("click", event => {
                if (event.target === fondo || event.target.closest("[data-cerrar]")) {
                    cerrar(false);
                }
            });

            form.addEventListener("submit", async event => {
                event.preventDefault();
                if (submit.disabled) return;
                submit.disabled = true;
                try {
                    const resultado = await onSubmit(new FormData(form), form, datosIniciales);
                    cerrar(resultado !== false);
                } catch (error) {
                    window.SSALFER_UI?.toast(
                        error?.mensaje || error?.message || "No fue posible guardar los cambios.",
                        { tipo: "error" }
                    );
                    submit.disabled = false;
                }
            });

            document.addEventListener("keydown", onKeydown);
            document.body.appendChild(fondo);
            form.querySelector("input, select, textarea, button")?.focus();
        });
    }

    async function recargarFicha(mensaje) {
        await cargarDatos();
        mostrarInformacion();
        mostrarAfectaciones();
        mostrarEventos();
        if (mensaje) {
            window.SSALFER_UI?.toast(mensaje);
        }
    }

    function valorBooleanoFormulario(valor) {
        if (valor === "true") return true;
        if (valor === "false") return false;
        return null;
    }

    function opcionSeleccionada(valor, esperado) {
        return String(valor ?? "") === String(esperado) ? " selected" : "";
    }

    /* =====================================================
                    EDITAR TRÁMITE
    ====================================================== */

    async function editarTramite() {
        const conflictoActual = tramite.hay_conflictos === true
            ? "true"
            : (tramite.hay_conflictos === false ? "false" : "");

        await formularioModal({
            titulo: "Editar trámite FIFONAFE",
            contenido: `
                <div class="fifonafe-form-grid">
                    <label class="fifonafe-campo">
                        <span>Estatus *</span>
                        <select name="estatus" required>
                            <option value="pendiente"${opcionSeleccionada(tramite.estatus, "pendiente")}>Pendiente</option>
                            <option value="programado"${opcionSeleccionada(tramite.estatus, "programado")}>Programado</option>
                            <option value="completo"${opcionSeleccionada(tramite.estatus, "completo")}>Completo</option>
                            <option value="cancelado"${opcionSeleccionada(tramite.estatus, "cancelado")}>Cancelado</option>
                            <option value="otro"${opcionSeleccionada(tramite.estatus, "otro")}>Otro</option>
                        </select>
                    </label>

                    <label class="fifonafe-campo">
                        <span>Fecha de acuse FIFONAFE</span>
                        <input type="date" name="acuse_fifonafe_fecha" value="${escaparHTML(tramite.acuse_fifonafe_fecha || "")}">
                    </label>

                    <label class="fifonafe-campo">
                        <span>¿Hay conflictos?</span>
                        <select name="hay_conflictos">
                            <option value=""${opcionSeleccionada(conflictoActual, "")}>Sin definir</option>
                            <option value="true"${opcionSeleccionada(conflictoActual, "true")}>Sí</option>
                            <option value="false"${opcionSeleccionada(conflictoActual, "false")}>No</option>
                        </select>
                    </label>

                    <label class="fifonafe-campo fifonafe-campo--ancho">
                        <span>Resultado / detalle</span>
                        <textarea name="resultado_no_conflictos" rows="3">${escaparHTML(tramite.resultado_no_conflictos || "")}</textarea>
                    </label>

                    <label class="fifonafe-campo fifonafe-campo--ancho">
                        <span>Referencia de expediente</span>
                        <input type="text" name="referencia_expediente" maxlength="200" value="${escaparHTML(tramite.referencia_expediente || "")}">
                    </label>
                </div>
            `,
            onSubmit: async datos => {
                await window.FifonafeAPI.actualizar(idFifonafe, {
                    estatus: datos.get("estatus"),
                    acuse_fifonafe_fecha: datos.get("acuse_fifonafe_fecha") || null,
                    hay_conflictos: valorBooleanoFormulario(datos.get("hay_conflictos")),
                    resultado_no_conflictos: String(datos.get("resultado_no_conflictos") || "").trim() || null,
                    referencia_expediente: String(datos.get("referencia_expediente") || "").trim() || null
                });
            }
        }).then(async guardado => {
            if (guardado) await recargarFicha("Trámite FIFONAFE actualizado correctamente.");
        });
    }

    elementos.btnEditar?.addEventListener("click", editarTramite);
    elementos.btnEditarDatos?.addEventListener("click", editarTramite);

    /* =====================================================
                    AGREGAR AFECTACIÓN
    ====================================================== */

    elementos.btnAgregarAfectacion?.addEventListener("click", async () => {
        const relacionadas = new Set(afectaciones.map(item => Number(item.id_afectacion)));
        const disponibles = todasAfectaciones.filter(item =>
            !relacionadas.has(Number(item.id_afectacion)) &&
            item.tipo_afectacion === tramite.ambito
        );

        if (!disponibles.length) {
            await window.SSALFER_UI?.abrirModal({
                titulo: "Agregar afectación",
                contenido: "<p>No hay afectaciones adicionales disponibles para este núcleo.</p>"
            });
            return;
        }

        const opciones = disponibles.map(item => {
            const superficie = item.superficie_afectada_ha ?? item.superficie_preliminar_ha;
            const etiquetaSuperficie = superficie === null || superficie === undefined
                ? "sin superficie registrada"
                : `${superficie} ha`;
            return `<option value="${item.id_afectacion}">${escaparHTML(`${item.tipo_afectacion || "Afectación"} · ${etiquetaSuperficie} · #${item.id_afectacion}`)}</option>`;
        }).join("");

        await formularioModal({
            titulo: "Agregar afectación al trámite",
            contenido: `
                <label class="fifonafe-campo">
                    <span>Afectación *</span>
                    <select name="id_afectacion" required>
                        <option value="">Seleccionar afectación</option>
                        ${opciones}
                    </select>
                </label>
            `,
            textoGuardar: "Agregar",
            onSubmit: async datos => {
                const id = Number(datos.get("id_afectacion"));
                if (!Number.isInteger(id) || id <= 0) {
                    throw new Error("Selecciona una afectación válida.");
                }
                await window.FifonafeAPI.agregarAfectacion(idFifonafe, id);
            }
        }).then(async guardado => {
            if (guardado) await recargarFicha("Afectación agregada al trámite.");
        });
    });

    /* =====================================================
                    EVENTOS: FORMULARIO
    ====================================================== */

    function opcionesTiposEvento(idActual = null) {
        return tiposEvento.map(item => `
            <option value="${item.id_catalogo_opcion}"${opcionSeleccionada(idActual, item.id_catalogo_opcion)}>
                ${escaparHTML(item.nombre || item.codigo || `#${item.id_catalogo_opcion}`)}
            </option>
        `).join("");
    }

    function contenidoFormularioEvento(evento = null) {
        const esNuevo = !evento;
        const siguienteOrdinal = eventos.length
            ? Math.max(...eventos.map(item => Number(item.ordinal) || 0)) + 1
            : 1;
        const conflicto = evento?.conflicto_impide_retiro === true
            ? "true"
            : (evento?.conflicto_impide_retiro === false ? "false" : "");

        return `
            <div class="fifonafe-form-grid">
                ${esNuevo ? `
                    <label class="fifonafe-campo">
                        <span>Ordinal *</span>
                        <input type="number" name="ordinal" min="1" step="1" required value="${siguienteOrdinal}">
                    </label>
                ` : `
                    <div class="fifonafe-campo">
                        <span>Ordinal</span>
                        <strong>${escaparHTML(evento.ordinal)}</strong>
                    </div>
                `}

                <label class="fifonafe-campo">
                    <span>Tipo de evento *</span>
                    <select name="id_tipo_evento" required>
                        <option value="">Seleccionar tipo</option>
                        ${opcionesTiposEvento(evento?.id_tipo_evento)}
                    </select>
                </label>

                <label class="fifonafe-campo">
                    <span>Origen</span>
                    <input type="text" name="origen" maxlength="200" value="${escaparHTML(evento?.origen || "")}">
                </label>

                <label class="fifonafe-campo">
                    <span>Destino</span>
                    <input type="text" name="destino" maxlength="200" value="${escaparHTML(evento?.destino || "")}">
                </label>

                <label class="fifonafe-campo">
                    <span>Número de oficio</span>
                    <input type="text" name="numero_oficio" maxlength="150" value="${escaparHTML(evento?.numero_oficio || "")}">
                </label>

                <label class="fifonafe-campo">
                    <span>Fecha de oficio</span>
                    <input type="date" name="fecha_oficio" value="${escaparHTML(evento?.fecha_oficio || "")}">
                </label>

                <label class="fifonafe-campo">
                    <span>Fecha del evento</span>
                    <input type="date" name="fecha_evento" value="${escaparHTML(evento?.fecha_evento || "")}">
                </label>

                <label class="fifonafe-campo">
                    <span>Ciclo de consulta</span>
                    <input type="number" name="ciclo_consulta" min="1" step="1" value="${escaparHTML(evento?.ciclo_consulta || "")}">
                </label>

                <label class="fifonafe-campo">
                    <span>Documento relacionado</span>
                    <select name="id_documento">${window.SSALFER_DOCUMENTOS.opciones(documentosRelacionados, evento?.id_documento)}</select>
                    <small>Selecciona un documento registrado y vinculado al trámite o a su núcleo.</small>
                </label>

                <label class="fifonafe-campo fifonafe-campo--ancho">
                    <span>Observaciones</span>
                    <textarea name="observaciones" rows="3">${escaparHTML(evento?.observaciones || "")}</textarea>
                </label>

                <label class="fifonafe-campo">
                    <span>¿Conflicto impide retiro?</span>
                    <select name="conflicto_impide_retiro">
                        <option value=""${opcionSeleccionada(conflicto, "")}>Sin definir</option>
                        <option value="true"${opcionSeleccionada(conflicto, "true")}>Sí</option>
                        <option value="false"${opcionSeleccionada(conflicto, "false")}>No</option>
                    </select>
                </label>
            </div>
            <p class="fifonafe-evidencia" role="note"><strong>Evidencia: al menos un dato obligatorio.</strong> Captura número de oficio, fecha de oficio, fecha del evento, documento u observaciones.</p>
        `;
    }

    function payloadEvento(datos, incluirOrdinal) {
        const payload = {
            id_tipo_evento: Number(datos.get("id_tipo_evento")),
            origen: String(datos.get("origen") || "").trim() || null,
            destino: String(datos.get("destino") || "").trim() || null,
            numero_oficio: String(datos.get("numero_oficio") || "").trim() || null,
            fecha_oficio: datos.get("fecha_oficio") || null,
            id_documento: datos.get("id_documento") ? Number(datos.get("id_documento")) : null,
            ciclo_consulta: datos.get("ciclo_consulta") ? Number(datos.get("ciclo_consulta")) : null,
            fecha_evento: datos.get("fecha_evento") || null,
            observaciones: String(datos.get("observaciones") || "").trim() || null,
            conflicto_impide_retiro: valorBooleanoFormulario(datos.get("conflicto_impide_retiro"))
        };

        if (!Number.isInteger(payload.id_tipo_evento) || payload.id_tipo_evento <= 0) {
            throw new Error("Selecciona un tipo de evento.");
        }

        const tieneEvidencia = Boolean(
            payload.numero_oficio ||
            payload.fecha_oficio ||
            payload.fecha_evento ||
            payload.id_documento ||
            payload.observaciones
        );

        if (!tieneEvidencia) {
            throw new Error(
                "Indica al menos un dato de evidencia: número de oficio, fecha de oficio, fecha del evento, documento relacionado u observaciones."
            );
        }

        if (incluirOrdinal) {
            payload.ordinal = Number(datos.get("ordinal"));
            if (!Number.isInteger(payload.ordinal) || payload.ordinal <= 0) {
                throw new Error("El ordinal debe ser un entero mayor que cero.");
            }
            if (eventos.some(evento => evento.activo !== false && Number(evento.ordinal) === payload.ordinal)) {
                throw new Error(`Ya existe un evento con el ordinal ${payload.ordinal}.`);
            }
        }

        return payload;
    }

    async function guardarEvento(operacion) {
        try {
            return await operacion();
        } catch (error) {
            if (error?.status === 409) {
                throw new Error("No se pudo guardar el evento. Revisa que el ordinal no esté ocupado y que los datos de evidencia sean válidos. Actualiza la ficha si otra persona realizó cambios.");
            }
            throw error;
        }
    }

    elementos.btnAgregarEvento?.addEventListener("click", async () => {
        await formularioModal({
            titulo: "Registrar evento FIFONAFE",
            contenido: contenidoFormularioEvento(),
            onSubmit: async datos => {
                const payload = payloadEvento(datos, true);
                await guardarEvento(() => window.FifonafeAPI.crearEvento(idFifonafe, payload));
            }
        }).then(async guardado => {
            if (guardado) await recargarFicha("Evento FIFONAFE registrado correctamente.");
        });
    });

    /* =====================================================
                    EVENTOS: VER / EDITAR / ELIMINAR
    ====================================================== */

    elementos.eventosTabla?.addEventListener("click", async event => {
        const botonVer = event.target.closest("[data-ver-evento]");
        const botonEditar = event.target.closest("[data-editar-evento]");
        const botonEliminar = event.target.closest("[data-eliminar-evento]");
        const boton = botonVer || botonEditar || botonEliminar;
        if (!boton) return;

        const id = Number(
            boton.dataset.verEvento ||
            boton.dataset.editarEvento ||
            boton.dataset.eliminarEvento
        );
        const eventoFifonafe = eventos.find(item => Number(item.id_evento_fifonafe) === id);
        if (!eventoFifonafe) return;

        if (botonVer) {
            await window.SSALFER_UI?.verDatos(
                `Evento FIFONAFE · ${nombreTipoEvento(eventoFifonafe.id_tipo_evento)}`,
                {
                    "Ordinal": eventoFifonafe.ordinal,
                    "Tipo": nombreTipoEvento(eventoFifonafe.id_tipo_evento),
                    "Origen": eventoFifonafe.origen || "—",
                    "Destino": eventoFifonafe.destino || "—",
                    "Número de oficio": eventoFifonafe.numero_oficio || "—",
                    "Fecha de oficio": window.SSALFER_FORMAT?.formatearFecha(eventoFifonafe.fecha_oficio) || "—",
                    "Fecha del evento": window.SSALFER_FORMAT?.formatearFecha(eventoFifonafe.fecha_evento) || "—",
                    "Ciclo de consulta": eventoFifonafe.ciclo_consulta || "—",
                    "Conflicto impide retiro": formatoConflictos(eventoFifonafe.conflicto_impide_retiro),
                    "Documento": window.SSALFER_DOCUMENTOS.nombre(documentosRelacionados, eventoFifonafe.id_documento),
                    "Observaciones": eventoFifonafe.observaciones || "—"
                }
            );
            return;
        }

        if (botonEditar) {
            await formularioModal({
                titulo: `Editar evento FIFONAFE · ordinal ${eventoFifonafe.ordinal}`,
                contenido: contenidoFormularioEvento(eventoFifonafe),
                onSubmit: async (datos, form, iniciales) => {
                    const cambiados = new Set([...datos.keys()].filter(campo => datos.get(campo) !== iniciales.get(campo)));
                    if (!cambiados.size) {
                        window.SSALFER_UI.toast("No hay cambios que guardar.");
                        return false;
                    }
                    const completo = payloadEvento(datos, false);
                    const cambios = Object.fromEntries(Object.entries(completo).filter(([campo]) => cambiados.has(campo)));
                    await guardarEvento(() => window.FifonafeAPI.actualizarEvento(
                        eventoFifonafe.id_evento_fifonafe,
                        cambios
                    ));
                }
            }).then(async guardado => {
                if (guardado) await recargarFicha("Evento FIFONAFE actualizado correctamente.");
            });
            return;
        }

        if (botonEliminar) {
            await formularioModal({
                titulo: `Dar de baja evento FIFONAFE · ordinal ${eventoFifonafe.ordinal}`,
                contenido: `
                    <p>Esta acción conserva el historial y marca el evento como dado de baja.</p>
                    <label class="fifonafe-campo">
                        <span>Motivo de baja *</span>
                        <textarea name="motivo" rows="3" minlength="3" maxlength="500" required>Corrección del evento</textarea>
                    </label>
                `,
                textoGuardar: "Dar de baja",
                onSubmit: async datos => {
                    const motivo = String(datos.get("motivo") || "").trim();
                    if (motivo.length < 3) {
                        throw new Error("El motivo de baja debe tener al menos 3 caracteres.");
                    }
                    await window.FifonafeAPI.eliminarEvento(
                        eventoFifonafe.id_evento_fifonafe,
                        motivo
                    );
                }
            }).then(async guardado => {
                if (guardado) await recargarFicha("Evento FIFONAFE dado de baja.");
            });
        }
    });

    /* =====================================================
                        VOLVER
    ====================================================== */

    elementos.btnVolver
        ?.addEventListener(
            "click",
            () => {
                window.location.href =
                    `/pages/fifonafe.html?id_proyecto_nucleo=${encodeURIComponent(
                        idProyectoNucleo
                    )}`;
            }
        );


    /* =====================================================
                        INICIALIZACIÓN
    ====================================================== */

    try {
        await cargarDatos();

        mostrarInformacion();
        mostrarAfectaciones();
        mostrarEventos();

    } catch (error) {
        window.ClienteAPI
            .mostrarErrorAPI(error);
    }
});
