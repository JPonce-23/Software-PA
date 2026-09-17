document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const parametros = new URLSearchParams(window.location.search);
    const idProyecto = parametros.get("id_proyecto");
    const returnTo = parametros.get("return_to");

    const elementos = {
        modal: document.getElementById("modalPersona"),
        btnNueva: document.getElementById("btnNuevaPersona"),
        btnCerrar: document.getElementById("btnCerrarModal"),
        btnCancelar: document.getElementById("btnCancelarPersona"),
        form: document.getElementById("formPersona"),
        busqueda: document.getElementById("busqueda"),
        btnLimpiar: document.getElementById("btnLimpiarBusqueda"),
        personasContainer: document.getElementById("personasContainer"),
        sinPersonas: document.getElementById("sinPersonas"),
        contador: document.getElementById("contadorPersonas")
    };

    let puedeCapturar = false;

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function nombreCompleto(persona) {
        return [
            persona.nombre,
            persona.apellido_paterno,
            persona.apellido_materno
        ]
            .filter(Boolean)
            .join(" ");
    }

    function actualizarEstado() {
        const cards =
            elementos.personasContainer.querySelectorAll("[data-persona]");

        elementos.contador.textContent =
            cards.length === 1
                ? "1 persona"
                : `${cards.length} personas`;

        elementos.sinPersonas.hidden =
            cards.length > 0;
    }

    function agregarPersonaVisual(persona) {
        const article =
            document.createElement("article");

        article.className = "persona";
        article.dataset.persona = "";

        const identidadCompleta = Boolean(
            persona.curp &&
            !persona.datos_identidad_incompletos
        );

        article.innerHTML = `
            <div class="persona-icono">
                <i class="bi bi-person"></i>
            </div>

            <div class="persona-datos">
                <h3>${escaparHTML(nombreCompleto(persona))}</h3>
                <span>
                    CURP:
                    ${escaparHTML(persona.curp || "Pendiente")}
                </span>
                <span>
                    Teléfono:
                    ${escaparHTML(persona.telefono || "Pendiente")}
                </span>
                <span>
                    Correo:
                    ${escaparHTML(persona.correo_electronico || "Pendiente")}
                </span>
            </div>

            <div class="persona-estado">
                <span class="estado-identidad ${
                    identidadCompleta
                        ? "completa"
                        : "incompleta"
                }">
                    ${
                        identidadCompleta
                            ? "Identidad completa"
                            : "Identidad incompleta"
                    }
                </span>
            </div>
        `;

        elementos.personasContainer.appendChild(article);

        actualizarEstado();
    }

    function abrirModal() {
        if (!puedeCapturar) {
            return;
        }

        if (!idProyecto) {
            alert(
                "No se puede registrar una persona porque falta id_proyecto en la URL."
            );

            return;
        }

        elementos.modal.hidden = false;
        document.body.style.overflow = "hidden";

        document
            .getElementById("nombre")
            ?.focus();
    }

    function cerrarModal() {
        elementos.modal.hidden = true;
        document.body.style.overflow = "";

        elementos.form.reset();
    }

    function obtenerDatos() {
        const data =
            new FormData(elementos.form);

        return {
            curp:
                data.get("curp")?.trim() ||
                null,

            rfc:
                data.get("rfc")?.trim() ||
                null,

            nombre:
                data.get("nombre")?.trim() ||
                "",

            apellido_paterno:
                data.get("apellido_paterno")?.trim() ||
                null,

            apellido_materno:
                data.get("apellido_materno")?.trim() ||
                null,

            telefono:
                data.get("telefono")?.trim() ||
                null,

            correo_electronico:
                data.get("correo_electronico")?.trim() ||
                null,

            datos_identidad_incompletos:
                document
                    .getElementById("datosIdentidadIncompletos")
                    ?.checked ||
                false,

            origen_registro:
                "captura_sistema"
        };
    }

    function validar(datos) {
        if (!datos.nombre) {
            return "El nombre es obligatorio.";
        }

        if (datos.nombre.length > 300) {
            return "El nombre no puede superar 300 caracteres.";
        }

        if (
            datos.apellido_paterno?.length > 200
        ) {
            return "El apellido paterno no puede superar 200 caracteres.";
        }

        if (
            datos.apellido_materno?.length > 200
        ) {
            return "El apellido materno no puede superar 200 caracteres.";
        }

        if (datos.curp?.length > 18) {
            return "La CURP no puede superar 18 caracteres.";
        }

        if (datos.rfc?.length > 13) {
            return "El RFC no puede superar 13 caracteres.";
        }

        if (datos.telefono?.length > 30) {
            return "El teléfono no puede superar 30 caracteres.";
        }

        if (
            datos.correo_electronico?.length > 320
        ) {
            return "El correo no puede superar 320 caracteres.";
        }

        return null;
    }

    function volverConPersona(persona) {
        if (!returnTo) {
            return false;
        }

        const destino =
            new URL(
                returnTo,
                window.location.origin
            );

        destino.searchParams.set(
            "id_persona_creada",
            persona.id_persona
        );

        destino.searchParams.set(
            "persona_nombre",
            nombreCompleto(persona)
        );

        window.location.href =
            `${destino.pathname}${destino.search}`;

        return true;
    }

    elementos.btnNueva?.addEventListener(
        "click",
        abrirModal
    );

    elementos.btnCerrar?.addEventListener(
        "click",
        cerrarModal
    );

    elementos.btnCancelar?.addEventListener(
        "click",
        cerrarModal
    );

    elementos.modal?.addEventListener(
        "click",
        event => {
            if (
                event.target === elementos.modal
            ) {
                cerrarModal();
            }
        }
    );

    document.addEventListener(
        "keydown",
        event => {
            if (
                event.key === "Escape" &&
                elementos.modal &&
                !elementos.modal.hidden
            ) {
                cerrarModal();
            }
        }
    );

    elementos.busqueda?.addEventListener(
        "input",
        () => {
            const texto =
                elementos.busqueda.value
                    .trim()
                    .toLowerCase();

            let visibles = 0;

            elementos.personasContainer
                .querySelectorAll("[data-persona]")
                .forEach(card => {
                    const coincide =
                        !texto ||
                        card.textContent
                            .toLowerCase()
                            .includes(texto);

                    card.style.display =
                        coincide
                            ? ""
                            : "none";

                    if (coincide) {
                        visibles += 1;
                    }
                });

            elementos.contador.textContent =
                visibles === 1
                    ? "1 persona"
                    : `${visibles} personas`;
        }
    );

    elementos.btnLimpiar?.addEventListener(
        "click",
        () => {
            elementos.busqueda.value = "";

            elementos.personasContainer
                .querySelectorAll("[data-persona]")
                .forEach(card => {
                    card.style.display = "";
                });

            actualizarEstado();
        }
    );

    elementos.form?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            if (
                !elementos.form.checkValidity()
            ) {
                elementos.form.reportValidity();
                return;
            }

            if (!idProyecto) {
                alert(
                    "No se puede registrar la persona porque falta id_proyecto."
                );

                return;
            }

            const datos =
                obtenerDatos();

            const error =
                validar(datos);

            if (error) {
                alert(error);
                return;
            }

            const submit =
                elementos.form.querySelector(
                    '[type="submit"]'
                );

            submit.disabled = true;

            try {
                const creada =
                    await window.PersonasAPI.crear(
                        Number(idProyecto),
                        datos
                    );

                if (
                    volverConPersona(creada)
                ) {
                    return;
                }

                agregarPersonaVisual(creada);
                cerrarModal();

            } catch (err) {
                window.ClienteAPI.mostrarErrorAPI(
                    err
                );

            } finally {
                submit.disabled = false;
            }
        }
    );

    /*
     * El backend actual no expone:
     *
     * GET /proyectos/{id}/personas
     *
     * Por eso eliminamos cualquier persona
     * demostrativa del HTML.
     */
    elementos.personasContainer.innerHTML = "";

    if (elementos.sinPersonas) {
        const tituloVacio =
            elementos.sinPersonas.querySelector(
                "p"
            );

        const detalleVacio =
            elementos.sinPersonas.querySelector(
                "span"
            );

        if (tituloVacio) {
            tituloVacio.textContent =
                "No hay personas cargadas en esta vista.";
        }

        if (detalleVacio) {
            detalleVacio.textContent =
                "Registra una nueva persona para continuar con la captura.";
        }
    }

    actualizarEstado();

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

    if (elementos.btnNueva) {
        elementos.btnNueva.hidden =
            !puedeCapturar;
    }

    if (
        returnTo &&
        puedeCapturar
    ) {
        abrirModal();
    }
});