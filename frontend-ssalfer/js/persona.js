document.addEventListener("DOMContentLoaded", async () => {

    "use strict";


    /* =====================================================
       PARÁMETROS
    ====================================================== */

    const parametros =
        new URLSearchParams(
            window.location.search
        );


    const idProyecto =
        Number(
            parametros.get(
                "id_proyecto"
            )
        );


    const returnTo =
        parametros.get(
            "return_to"
        );


    /* =====================================================
       ELEMENTOS
    ====================================================== */

    const elementos = {

        modal:
            document.getElementById(
                "modalPersona"
            ),

        btnNueva:
            document.getElementById(
                "btnNuevaPersona"
            ),

        btnCerrar:
            document.getElementById(
                "btnCerrarModal"
            ),

        btnCancelar:
            document.getElementById(
                "btnCancelarPersona"
            ),

        form:
            document.getElementById(
                "formPersona"
            ),


        tituloModal:
            document.getElementById(
                "tituloModalPersona"
            ),


        busqueda:
            document.getElementById(
                "busqueda"
            ),

        btnConsultar:
            document.getElementById(
                "btnConsultarPersona"
            ),

        btnLimpiar:
            document.getElementById(
                "btnLimpiarBusqueda"
            ),


        personasContainer:
            document.getElementById(
                "personasContainer"
            ),

        sinPersonas:
            document.getElementById(
                "sinPersonas"
            ),

        contador:
            document.getElementById(
                "contadorPersonas"
            )

    };


    /* =====================================================
       ESTADO
    ====================================================== */

    let puedeCapturar =
        false;


    let esAdmin =
        false;


    let idPersonaEditando =
        null;


    /*
     * Personas que se han creado o consultado
     * durante esta visita a la pantalla.
     */

    const personas =
        new Map();


    /* =====================================================
       UTILIDADES
    ====================================================== */

    function escaparHTML(valor) {

        return String(
            valor ?? ""
        )
            .replaceAll(
                "&",
                "&amp;"
            )
            .replaceAll(
                "<",
                "&lt;"
            )
            .replaceAll(
                ">",
                "&gt;"
            )
            .replaceAll(
                '"',
                "&quot;"
            )
            .replaceAll(
                "'",
                "&#039;"
            );

    }


    function nombreCompleto(
        persona
    ) {

        return [

            persona?.nombre,

            persona?.apellido_paterno,

            persona?.apellido_materno

        ]
            .filter(Boolean)
            .join(" ")
            .trim() ||
            `Persona #${persona?.id_persona ?? "—"}`;

    }


    function obtenerCampo(
        nombre
    ) {

        return elementos.form
            ?.elements
            ?.namedItem(
                nombre
            ) ||
            null;

    }


    function valorCampo(
        nombre
    ) {

        const elemento =
            obtenerCampo(
                nombre
            );


        const valor =
            elemento
                ?.value
                ?.trim();


        return valor ||
            null;

    }


    function personaPorId(
        idPersona
    ) {

        return personas.get(
            Number(
                idPersona
            )
        ) || null;

    }


    /* =====================================================
       RENDER
    ====================================================== */

    function actualizarEstado() {

        const cantidad =
            personas.size;


        if (
            elementos.contador
        ) {

            elementos.contador.textContent =
                cantidad === 1
                    ? "1 persona"
                    : `${cantidad} personas`;

        }


        if (
            elementos.sinPersonas
        ) {

            elementos.sinPersonas.hidden =
                cantidad > 0;

        }

    }


    function renderPersonas() {

        if (
            !elementos.personasContainer
        ) {

            return;

        }


        elementos.personasContainer.innerHTML =
            "";


        personas.forEach(
            persona => {

                const article =
                    document.createElement(
                        "article"
                    );


                article.className =
                    "persona";


                article.dataset.persona =
                    "";


                article.dataset.personaId =
                    persona.id_persona;


                const identidadCompleta =
                    Boolean(
                        persona.curp &&
                        !persona
                            .datos_identidad_incompletos
                    );


                const activa =
                    persona.activo !==
                    false;


                article.innerHTML = `

                    <div class="persona-icono">

                        <i class="bi bi-person"></i>

                    </div>


                    <div class="persona-datos">

                        <h3>
                            ${escaparHTML(
                                nombreCompleto(
                                    persona
                                )
                            )}
                        </h3>

                        <span>
                            ID:
                            ${escaparHTML(
                                persona.id_persona
                            )}
                        </span>

                        <span>
                            CURP:
                            ${escaparHTML(
                                persona.curp ||
                                "Pendiente"
                            )}
                        </span>

                        <span>
                            RFC:
                            ${escaparHTML(
                                persona.rfc ||
                                "Pendiente"
                            )}
                        </span>

                        <span>
                            Teléfono:
                            ${escaparHTML(
                                persona.telefono ||
                                "Pendiente"
                            )}
                        </span>

                        <span>
                            Correo:
                            ${escaparHTML(
                                persona.correo_electronico ||
                                "Pendiente"
                            )}
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


                        <span>

                            ${
                                activa
                                    ? "Activa"
                                    : "Inactiva"
                            }

                        </span>


                        ${
                            puedeCapturar &&
                            activa

                                ? `
                                    <button
                                        type="button"
                                        class="btn-secundario"
                                        data-editar-persona="${persona.id_persona}"
                                    >

                                        <i class="bi bi-pencil"></i>

                                        Editar

                                    </button>
                                `

                                : ""
                        }


                        ${
                            esAdmin &&
                            activa

                                ? `
                                    <button
                                        type="button"
                                        class="btn-secundario"
                                        data-baja-persona="${persona.id_persona}"
                                    >

                                        <i class="bi bi-person-dash"></i>

                                        Dar de baja

                                    </button>
                                `

                                : ""
                        }


                        ${
                            esAdmin &&
                            !activa

                                ? `
                                    <button
                                        type="button"
                                        class="btn-secundario"
                                        data-reactivar-persona="${persona.id_persona}"
                                    >

                                        <i class="bi bi-person-check"></i>

                                        Reactivar

                                    </button>
                                `

                                : ""
                        }

                    </div>
                `;


                elementos
                    .personasContainer
                    .appendChild(
                        article
                    );

            }
        );


        actualizarEstado();

    }


    function guardarPersonaLocal(
        persona
    ) {

        if (
            !persona?.id_persona
        ) {

            return;

        }


        personas.set(
            Number(
                persona.id_persona
            ),
            persona
        );


        renderPersonas();

    }


    /* =====================================================
       MODAL
    ====================================================== */

    function configurarModalNuevo() {

        idPersonaEditando =
            null;


        elementos.form?.reset();


        if (
            elementos.tituloModal
        ) {

            elementos.tituloModal.textContent =
                "Nueva persona";

        }


        const botonGuardar =
            elementos.form
                ?.querySelector(
                    '[type="submit"]'
                );


        if (
            botonGuardar
        ) {

            botonGuardar.innerHTML = `
                <i class="bi bi-check-lg"></i>
                Guardar persona
            `;

        }

    }


    function configurarModalEdicion(
        persona
    ) {

        idPersonaEditando =
            Number(
                persona.id_persona
            );


        elementos.form?.reset();


        obtenerCampo(
            "nombre"
        ).value =
            persona.nombre ||
            "";


        obtenerCampo(
            "apellido_paterno"
        ).value =
            persona.apellido_paterno ||
            "";


        obtenerCampo(
            "apellido_materno"
        ).value =
            persona.apellido_materno ||
            "";


        obtenerCampo(
            "curp"
        ).value =
            persona.curp ||
            "";


        obtenerCampo(
            "rfc"
        ).value =
            persona.rfc ||
            "";


        obtenerCampo(
            "telefono"
        ).value =
            persona.telefono ||
            "";


        obtenerCampo(
            "correo_electronico"
        ).value =
            persona.correo_electronico ||
            "";


        const incompletos =
            obtenerCampo(
                "datos_identidad_incompletos"
            );


        if (
            incompletos
        ) {

            incompletos.checked =
                Boolean(
                    persona
                        .datos_identidad_incompletos
                );

        }


        if (
            elementos.tituloModal
        ) {

            elementos.tituloModal.textContent =
                "Editar persona";

        }


        const botonGuardar =
            elementos.form
                ?.querySelector(
                    '[type="submit"]'
                );


        if (
            botonGuardar
        ) {

            botonGuardar.innerHTML = `
                <i class="bi bi-check-lg"></i>
                Guardar cambios
            `;

        }

    }


    function abrirModal() {

        if (
            !puedeCapturar
        ) {

            return;

        }


        elementos.modal.hidden =
            false;


        document.body.style.overflow =
            "hidden";


        obtenerCampo(
            "nombre"
        )?.focus();

    }


    function abrirNuevaPersona() {

        if (
            !Number.isInteger(
                idProyecto
            ) ||
            idProyecto <= 0
        ) {

            alert(
                "No se puede registrar una persona porque falta id_proyecto."
            );

            return;

        }


        configurarModalNuevo();

        abrirModal();

    }


    function abrirEditarPersona(
        persona
    ) {

        if (
            !puedeCapturar ||
            !persona
        ) {

            return;

        }


        configurarModalEdicion(
            persona
        );


        abrirModal();

    }


    function cerrarModal() {

        if (
            elementos.modal
        ) {

            elementos.modal.hidden =
                true;

        }


        document.body.style.overflow =
            "";


        elementos.form?.reset();


        idPersonaEditando =
            null;

    }


    /* =====================================================
       PAYLOAD
    ====================================================== */

    function obtenerDatos() {

        return {

            curp:
                valorCampo(
                    "curp"
                ),

            rfc:
                valorCampo(
                    "rfc"
                ),

            nombre:
                valorCampo(
                    "nombre"
                ) ||
                "",

            apellido_paterno:
                valorCampo(
                    "apellido_paterno"
                ),

            apellido_materno:
                valorCampo(
                    "apellido_materno"
                ),

            telefono:
                valorCampo(
                    "telefono"
                ),

            correo_electronico:
                valorCampo(
                    "correo_electronico"
                ),

            datos_identidad_incompletos:
                Boolean(
                    obtenerCampo(
                        "datos_identidad_incompletos"
                    )?.checked
                )

        };

    }


    function validar(
        datos
    ) {

        if (
            !datos.nombre
        ) {

            return (
                "El nombre es obligatorio."
            );

        }


        if (
            datos.nombre.length >
            300
        ) {

            return (
                "El nombre no puede superar 300 caracteres."
            );

        }


        if (
            datos.apellido_paterno
                ?.length >
            200
        ) {

            return (
                "El apellido paterno no puede superar 200 caracteres."
            );

        }


        if (
            datos.apellido_materno
                ?.length >
            200
        ) {

            return (
                "El apellido materno no puede superar 200 caracteres."
            );

        }


        if (
            datos.curp?.length >
            18
        ) {

            return (
                "La CURP no puede superar 18 caracteres."
            );

        }


        if (
            datos.rfc?.length >
            13
        ) {

            return (
                "El RFC no puede superar 13 caracteres."
            );

        }


        if (
            datos.telefono?.length >
            30
        ) {

            return (
                "El teléfono no puede superar 30 caracteres."
            );

        }


        if (
            datos.correo_electronico
                ?.length >
            320
        ) {

            return (
                "El correo no puede superar 320 caracteres."
            );

        }


        return null;

    }


    /* =====================================================
       RETURN_TO
    ====================================================== */

    function volverConPersona(
        persona
    ) {

        if (
            !returnTo
        ) {

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
            nombreCompleto(
                persona
            )
        );


        window.location.href =
            `${destino.pathname}${destino.search}`;


        return true;

    }


    /* =====================================================
       CONSULTA
    ====================================================== */

    async function consultarPersona() {

        const idPersona =
            Number(
                elementos
                    .busqueda
                    ?.value
            );


        if (
            !Number.isInteger(
                idPersona
            ) ||
            idPersona <= 0
        ) {

            alert(
                "Indica un ID de persona válido."
            );

            return;

        }


        if (
            elementos.btnConsultar
        ) {

            elementos.btnConsultar.disabled =
                true;

        }


        try {

            const persona =
                await window
                    .PersonasAPI
                    .obtener(
                        idPersona
                    );


            guardarPersonaLocal(
                persona
            );


        } catch (error) {

            window.ClienteAPI
                .mostrarErrorAPI(
                    error
                );

        } finally {

            if (
                elementos.btnConsultar
            ) {

                elementos.btnConsultar.disabled =
                    false;

            }

        }

    }


    /* =====================================================
       GUARDAR
    ====================================================== */

    elementos.form?.addEventListener(
        "submit",
        async event => {

            event.preventDefault();


            if (
                !puedeCapturar
            ) {

                return;

            }


            if (
                !elementos.form
                    .checkValidity()
            ) {

                elementos.form
                    .reportValidity();

                return;

            }


            const datos =
                obtenerDatos();


            const error =
                validar(
                    datos
                );


            if (error) {

                alert(
                    error
                );

                return;

            }


            const submit =
                elementos.form
                    .querySelector(
                        '[type="submit"]'
                    );


            submit.disabled =
                true;


            try {

                let persona;


                /*
                 * EDICIÓN
                 *
                 * PersonaUpdate NO permite origen_registro,
                 * por eso no se incluye aquí.
                 */

                if (
                    idPersonaEditando
                ) {

                    persona =
                        await window
                            .PersonasAPI
                            .actualizar(
                                idPersonaEditando,
                                datos
                            );


                    alert(
                        "Persona actualizada correctamente."
                    );


                } else {

                    if (
                        !Number.isInteger(
                            idProyecto
                        ) ||
                        idProyecto <= 0
                    ) {

                        alert(
                            "No se puede registrar la persona porque falta id_proyecto."
                        );

                        return;

                    }


                    persona =
                        await window
                            .PersonasAPI
                            .crear(
                                idProyecto,
                                {
                                    ...datos,

                                    origen_registro:
                                        "captura_sistema"
                                }
                            );


                    if (
                        volverConPersona(
                            persona
                        )
                    ) {

                        return;

                    }


                    alert(
                        "Persona registrada correctamente."
                    );

                }


                guardarPersonaLocal(
                    persona
                );


                cerrarModal();


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


    /* =====================================================
       BAJA
    ====================================================== */

    async function darDeBajaPersona(
        idPersona
    ) {

        if (
            !esAdmin
        ) {

            return;

        }


        const persona =
            personaPorId(
                idPersona
            );


        if (!persona) {

            return;

        }


        const motivo =
            window.prompt(
                `Indica el motivo de baja de ${nombreCompleto(
                    persona
                )}:`
            );


        if (
            motivo === null
        ) {

            return;

        }


        const motivoLimpio =
            motivo.trim();


        if (
            motivoLimpio.length <
            3
        ) {

            alert(
                "El motivo de baja debe tener al menos 3 caracteres."
            );

            return;

        }


        if (
            motivoLimpio.length >
            500
        ) {

            alert(
                "El motivo de baja no puede superar 500 caracteres."
            );

            return;

        }


        const confirmar =
            window.confirm(
                `¿Confirmas dar de baja a ${nombreCompleto(
                    persona
                )}?`
            );


        if (!confirmar) {

            return;

        }


        try {

            await window
                .PersonasAPI
                .darDeBaja(
                    idPersona,
                    motivoLimpio
                );


            /*
             * DELETE devuelve únicamente un mensaje.
             * Conservamos la tarjeta localmente para que
             * el administrador pueda reactivarla sin perder
             * su identificador.
             */

            personas.set(
                Number(
                    idPersona
                ),
                {
                    ...persona,

                    activo:
                        false,

                    motivo_baja:
                        motivoLimpio
                }
            );


            renderPersonas();


            alert(
                "Persona dada de baja correctamente."
            );


        } catch (error) {

            window.ClienteAPI
                .mostrarErrorAPI(
                    error
                );

        }

    }


    /* =====================================================
       REACTIVAR
    ====================================================== */

    async function reactivarPersona(
        idPersona
    ) {

        if (
            !esAdmin
        ) {

            return;

        }


        const persona =
            personaPorId(
                idPersona
            );


        const confirmar =
            window.confirm(
                `¿Confirmas reactivar a ${nombreCompleto(
                    persona
                )}?`
            );


        if (!confirmar) {

            return;

        }


        try {

            const reactivada =
                await window
                    .PersonasAPI
                    .reactivar(
                        idPersona
                    );


            guardarPersonaLocal(
                reactivada
            );


            alert(
                "Persona reactivada correctamente."
            );


        } catch (error) {

            window.ClienteAPI
                .mostrarErrorAPI(
                    error
                );

        }

    }


    /* =====================================================
       EVENTOS
    ====================================================== */

    elementos.btnNueva?.addEventListener(
        "click",
        abrirNuevaPersona
    );


    elementos.btnCerrar?.addEventListener(
        "click",
        cerrarModal
    );


    elementos.btnCancelar?.addEventListener(
        "click",
        cerrarModal
    );


    elementos.btnConsultar?.addEventListener(
        "click",
        consultarPersona
    );


    elementos.busqueda?.addEventListener(
        "keydown",
        event => {

            if (
                event.key ===
                "Enter"
            ) {

                event.preventDefault();

                consultarPersona();

            }

        }
    );


    elementos.btnLimpiar?.addEventListener(
        "click",
        () => {

            if (
                elementos.busqueda
            ) {

                elementos.busqueda.value =
                    "";

            }

        }
    );


    elementos.modal?.addEventListener(
        "click",
        event => {

            if (
                event.target ===
                elementos.modal
            ) {

                cerrarModal();

            }

        }
    );


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key ===
                    "Escape" &&
                elementos.modal &&
                !elementos.modal.hidden
            ) {

                cerrarModal();

            }

        }
    );


    elementos
        .personasContainer
        ?.addEventListener(
            "click",
            event => {

                const editar =
                    event.target.closest(
                        "[data-editar-persona]"
                    );


                if (editar) {

                    const persona =
                        personaPorId(
                            editar
                                .dataset
                                .editarPersona
                        );


                    abrirEditarPersona(
                        persona
                    );


                    return;

                }


                const baja =
                    event.target.closest(
                        "[data-baja-persona]"
                    );


                if (baja) {

                    darDeBajaPersona(
                        baja
                            .dataset
                            .bajaPersona
                    );


                    return;

                }


                const reactivar =
                    event.target.closest(
                        "[data-reactivar-persona]"
                    );


                if (
                    reactivar
                ) {

                    reactivarPersona(
                        reactivar
                            .dataset
                            .reactivarPersona
                    );

                }

            }
        );


    /* =====================================================
       INICIALIZACIÓN
    ====================================================== */

    /*
     * Eliminamos cualquier tarjeta demostrativa
     * que pudiera permanecer en el HTML.
     */

    if (
        elementos.personasContainer
    ) {

        elementos.personasContainer.innerHTML =
            "";

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


        esAdmin =
            rol === "admin";


    } catch (error) {

        puedeCapturar =
            false;


        esAdmin =
            false;


        window.ClienteAPI
            .mostrarErrorAPI(
                error
            );

    }


    if (
        elementos.btnNueva
    ) {

        elementos.btnNueva.hidden =
            !puedeCapturar;

    }


    /*
     * Si llegamos desde otro módulo para crear una
     * persona y regresar, abrimos el modal directamente.
     */

    if (
        returnTo &&
        puedeCapturar
    ) {

        abrirNuevaPersona();

    }

});