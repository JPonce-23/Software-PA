document.addEventListener(
    "DOMContentLoaded",
    async () => {

        "use strict";


        /* =====================================================
                            ELEMENTOS
        ====================================================== */

        const elementos = {

            form:
                document.getElementById(
                    "formCambiarContrasena"
                ),

            actual:
                document.getElementById(
                    "contrasenaActual"
                ),

            nueva:
                document.getElementById(
                    "contrasenaNueva"
                ),

            confirmar:
                document.getElementById(
                    "confirmarContrasena"
                ),

            boton:
                document.getElementById(
                    "btnGuardarContrasena"
                ),

            error:
                document.getElementById(
                    "mensajeCambioError"
                ),

            exito:
                document.getElementById(
                    "mensajeCambioExito"
                ),

            enlaceUsuarios:
                document.getElementById(
                    "enlaceUsuarios"
                )

        };


        /* =====================================================
                            SESIÓN
        ====================================================== */

        let sesion;


        try {

            sesion =
                await window.AuthAPI
                    .requerirSesion();


            if (!sesion) {

                return;

            }

        } catch (error) {

            window.ClienteAPI
                .mostrarErrorAPI(
                    error
                );


            return;

        }


        /*
         * Usuarios y permisos únicamente para admin.
         */

        if (
            elementos.enlaceUsuarios
        ) {

            elementos
                .enlaceUsuarios
                .hidden =
                sesion?.user?.rol !==
                "admin";

        }


        /* =====================================================
                            UTILIDADES
        ====================================================== */

        function limpiarMensajes() {

            if (
                elementos.error
            ) {

                elementos.error.hidden =
                    true;


                elementos.error.textContent =
                    "";

            }


            if (
                elementos.exito
            ) {

                elementos.exito.hidden =
                    true;


                elementos.exito.textContent =
                    "";

            }

        }


        function mostrarError(
            mensaje
        ) {

            if (
                !elementos.error
            ) {

                return;

            }


            elementos.error.textContent =
                mensaje;


            elementos.error.hidden =
                false;

        }


        function mostrarExito(
            mensaje
        ) {

            if (
                !elementos.exito
            ) {

                return;

            }


            elementos.exito.textContent =
                mensaje;


            elementos.exito.hidden =
                false;

        }


        function bytesUtf8(
            texto
        ) {

            return new TextEncoder()
                .encode(
                    texto
                )
                .length;

        }


        function cumplePolitica(
            contrasena
        ) {

            if (
                contrasena.length < 8
            ) {

                return false;

            }


            if (
                !/[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/u
                    .test(
                        contrasena
                    )
            ) {

                return false;

            }


            if (
                !/\d/
                    .test(
                        contrasena
                    )
            ) {

                return false;

            }


            if (
                bytesUtf8(
                    contrasena
                ) > 72
            ) {

                return false;

            }


            return true;

        }


        function validar() {

            const actual =
                elementos.actual.value;


            const nueva =
                elementos.nueva.value;


            const confirmar =
                elementos.confirmar.value;


            if (!actual) {

                return (
                    "Ingresa tu contraseña actual."
                );

            }


            if (
                bytesUtf8(
                    actual
                ) > 72
            ) {

                return (
                    "La contraseña actual supera el límite permitido."
                );

            }


            if (!nueva) {

                return (
                    "Ingresa una nueva contraseña."
                );

            }


            if (
                !cumplePolitica(
                    nueva
                )
            ) {

                return (
                    "La nueva contraseña debe tener al menos 8 caracteres, una letra y un número, y no superar 72 bytes."
                );

            }


            if (
                nueva === actual
            ) {

                return (
                    "La nueva contraseña debe ser diferente de la contraseña actual."
                );

            }


            if (
                nueva !== confirmar
            ) {

                return (
                    "La confirmación no coincide con la nueva contraseña."
                );

            }


            return null;

        }


        /* =====================================================
                            GUARDAR
        ====================================================== */

        elementos.form
            ?.addEventListener(
                "submit",
                async event => {

                    event.preventDefault();


                    limpiarMensajes();


                    if (
                        !elementos.form
                            .checkValidity()
                    ) {

                        elementos.form
                            .reportValidity();


                        return;

                    }


                    const error =
                        validar();


                    if (error) {

                        mostrarError(
                            error
                        );


                        return;

                    }


                    elementos.boton.disabled =
                        true;


                    try {

                        const respuesta =
                            await window.AuthAPI
                                .cambiarContrasena(
                                    elementos
                                        .actual
                                        .value,

                                    elementos
                                        .nueva
                                        .value
                                );


                        /*
                         * El backend revoca las sesiones y
                         * elimina la cookie de autenticación.
                         *
                         * No llamamos logout() nuevamente.
                         */

                        elementos.form.reset();


                        const sesiones =
                            Number(
                                respuesta
                                    ?.sesiones_revocadas
                            );


                        mostrarExito(
                            Number.isFinite(
                                sesiones
                            )
                                ? (
                                    `Contraseña actualizada correctamente. ` +
                                    `Se cerraron ${sesiones} sesión(es). ` +
                                    `Serás enviado al inicio de sesión.`
                                )
                                : (
                                    "Contraseña actualizada correctamente. " +
                                    "Por seguridad, deberás iniciar sesión nuevamente."
                                )
                        );


                        window.setTimeout(
                            () => {

                                window.location.href =
                                    "/Index.html";

                            },
                            1600
                        );


                    } catch (error) {

                        window.ClienteAPI
                            .mostrarErrorAPI(
                                error,
                                elementos.error
                            );


                    } finally {

                        elementos.boton.disabled =
                            false;

                    }

                }
            );

    }
);