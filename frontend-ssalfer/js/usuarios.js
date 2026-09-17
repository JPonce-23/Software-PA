document.addEventListener("DOMContentLoaded", async () => {
    "use strict";

    const LIMITE = 50;

    const estado = {
        pagina: 0,
        usuarios: [],
        cargando: false
    };

    const elementos = {
        error: document.getElementById("usuariosError"),
        ok: document.getElementById("usuariosOk"),
        tabla: document.getElementById("tablaUsuarios"),
        filtroEstado: document.getElementById("filtroEstadoUsuario"),
        busqueda: document.getElementById("busquedaUsuario"),
        btnRecargar: document.getElementById("btnRecargarUsuarios"),
        btnNuevo: document.getElementById("btnNuevoUsuario"),
        btnAnterior: document.getElementById("btnPaginaAnterior"),
        btnSiguiente: document.getElementById("btnPaginaSiguiente"),
        textoPagina: document.getElementById("textoPaginaUsuarios"),

        modalUsuario: document.getElementById("modalUsuario"),
        modalUsuarioTitulo: document.getElementById("modalUsuarioTitulo"),
        formUsuario: document.getElementById("formUsuario"),
        usuarioId: document.getElementById("usuarioId"),
        usuarioModo: document.getElementById("usuarioModo"),
        usuarioNombre: document.getElementById("usuarioNombre"),
        usuarioApellidoPaterno: document.getElementById("usuarioApellidoPaterno"),
        usuarioApellidoMaterno: document.getElementById("usuarioApellidoMaterno"),
        usuarioCorreo: document.getElementById("usuarioCorreo"),
        usuarioCorreoAyuda: document.getElementById("usuarioCorreoAyuda"),
        usuarioRol: document.getElementById("usuarioRol"),
        grupoContrasenaCrear: document.getElementById("grupoContrasenaCrear"),
        usuarioContrasena: document.getElementById("usuarioContrasena"),
        btnGuardarUsuario: document.getElementById("btnGuardarUsuario"),
        usuarioModalError: document.getElementById("usuarioModalError"),

        modalAccion: document.getElementById("modalAccion"),
        modalAccionTitulo: document.getElementById("modalAccionTitulo"),
        modalAccionDescripcion: document.getElementById("modalAccionDescripcion"),
        formAccion: document.getElementById("formAccionUsuario"),
        accionUsuarioId: document.getElementById("accionUsuarioId"),
        accionUsuarioTipo: document.getElementById("accionUsuarioTipo"),
        grupoAccionCorreo: document.getElementById("grupoAccionCorreo"),
        accionCorreo: document.getElementById("accionCorreo"),
        grupoAccionContrasena: document.getElementById("grupoAccionContrasena"),
        accionContrasena: document.getElementById("accionContrasena"),
        accionMotivo: document.getElementById("accionMotivo"),
        btnConfirmarAccion: document.getElementById("btnConfirmarAccion"),
        accionModalError: document.getElementById("accionModalError")
    };

    const acciones = {
        correo: {
            titulo: "Cambiar correo",
            descripcion: "El cambio de correo revoca las sesiones vigentes del usuario.",
            textoBoton: "Cambiar correo",
            usaCorreo: true,
            usaContrasena: false,
            motivoMaximo: 100,
            clasePeligro: false
        },

        desbloquear: {
            titulo: "Desbloquear cuenta",
            descripcion: "Elimina el bloqueo vigente de la cuenta.",
            textoBoton: "Desbloquear",
            usaCorreo: false,
            usaContrasena: false,
            motivoMaximo: 100,
            clasePeligro: false
        },

        revocar: {
            titulo: "Revocar sesiones",
            descripcion: "Revoca todas las sesiones activas del usuario.",
            textoBoton: "Revocar sesiones",
            usaCorreo: false,
            usaContrasena: false,
            motivoMaximo: 100,
            clasePeligro: true
        },

        password: {
            titulo: "Restablecer contraseña",
            descripcion: "Establece una nueva contraseña y revoca las sesiones vigentes.",
            textoBoton: "Restablecer contraseña",
            usaCorreo: false,
            usaContrasena: true,
            motivoMaximo: 100,
            clasePeligro: true
        },

        desactivar: {
            titulo: "Desactivar usuario",
            descripcion: "Desactiva al usuario, sus asignaciones activas y sus sesiones vigentes.",
            textoBoton: "Desactivar usuario",
            usaCorreo: false,
            usaContrasena: false,
            motivoMaximo: 500,
            clasePeligro: true
        },

        reactivar: {
            titulo: "Reactivar usuario",
            descripcion: "Vuelve a habilitar una cuenta previamente desactivada.",
            textoBoton: "Reactivar usuario",
            usaCorreo: false,
            usaContrasena: false,
            motivoMaximo: 100,
            clasePeligro: false
        }
    };

    function ocultarMensajes() {
        elementos.error.hidden = true;
        elementos.ok.hidden = true;
    }

    function mostrarExito(mensaje) {
        elementos.error.hidden = true;
        elementos.ok.textContent = mensaje;
        elementos.ok.hidden = false;
    }

    function mostrarError(error, contenedor = elementos.error) {
        elementos.ok.hidden = true;
        window.ClienteAPI.mostrarErrorAPI(error, contenedor);
    }

    function formatearFecha(valor) {
        if (!valor) return "—";

        const fecha = new Date(valor);

        if (Number.isNaN(fecha.getTime())) {
            return String(valor);
        }

        return fecha.toLocaleString("es-MX", {
            dateStyle: "medium",
            timeStyle: "short"
        });
    }

    function nombreCompleto(usuario) {
        return [
            usuario.nombre,
            usuario.apellido_paterno,
            usuario.apellido_materno
        ].filter(Boolean).join(" ");
    }

    function crearBotonAccion(texto, accion, idUsuario, variante = "secundario") {
        const boton = document.createElement("button");

        boton.type = "button";
        boton.className = `usuarios-btn usuarios-btn-${variante}`;
        boton.dataset.accion = accion;
        boton.dataset.idUsuario = String(idUsuario);
        boton.textContent = texto;

        return boton;
    }

    function renderUsuarios() {
        const termino = elementos.busqueda.value
            .trim()
            .toLocaleLowerCase("es-MX");

        const usuariosFiltrados = estado.usuarios.filter((usuario) => {
            if (!termino) return true;

            const bolsa = [
                nombreCompleto(usuario),
                usuario.correo,
                usuario.rol,
                usuario.activo ? "activo" : "inactivo",
                usuario.bloqueado ? "bloqueado" : "desbloqueado"
            ]
                .join(" ")
                .toLocaleLowerCase("es-MX");

            return bolsa.includes(termino);
        });

        elementos.tabla.replaceChildren();

        if (usuariosFiltrados.length === 0) {
            const fila = document.createElement("tr");
            const celda = document.createElement("td");

            celda.colSpan = 7;
            celda.className = "usuarios-tabla-estado";
            celda.textContent = termino
                ? "No hay coincidencias en esta página."
                : "No hay usuarios para este filtro.";

            fila.appendChild(celda);
            elementos.tabla.appendChild(fila);

            return;
        }

        for (const usuario of usuariosFiltrados) {
            const fila = document.createElement("tr");

            const tdUsuario = document.createElement("td");
            const bloqueNombre = document.createElement("div");
            bloqueNombre.className = "usuarios-nombre";

            const nombre = document.createElement("strong");
            nombre.textContent = nombreCompleto(usuario) || "Sin nombre";

            const id = document.createElement("small");
            id.textContent = `ID ${usuario.id_usuario}`;

            bloqueNombre.append(nombre, id);
            tdUsuario.appendChild(bloqueNombre);

            const tdCorreo = document.createElement("td");
            tdCorreo.textContent = usuario.correo || "—";

            const tdRol = document.createElement("td");
            const badgeRol = document.createElement("span");
            badgeRol.className = "usuarios-badge";
            badgeRol.textContent = usuario.rol || "—";
            tdRol.appendChild(badgeRol);

            const tdEstado = document.createElement("td");
            const badgeEstado = document.createElement("span");

            badgeEstado.className = usuario.activo
                ? "usuarios-badge"
                : "usuarios-badge usuarios-badge-inactivo";

            badgeEstado.textContent = usuario.activo
                ? "Activo"
                : "Inactivo";

            tdEstado.appendChild(badgeEstado);

            const tdBloqueo = document.createElement("td");

            if (usuario.bloqueado) {
                const badgeBloqueo = document.createElement("span");

                badgeBloqueo.className =
                    "usuarios-badge usuarios-badge-bloqueado";

                badgeBloqueo.textContent = "Bloqueado";

                tdBloqueo.appendChild(badgeBloqueo);

                const salto = document.createElement("br");
                const hasta = document.createElement("small");

                hasta.textContent =
                    `Hasta: ${formatearFecha(usuario.bloqueado_hasta)}`;

                tdBloqueo.append(salto, hasta);
            } else {
                tdBloqueo.textContent = "No";
            }

            const tdUltimoAcceso = document.createElement("td");

            tdUltimoAcceso.textContent =
                formatearFecha(usuario.ultimo_acceso_en);

            const tdAcciones = document.createElement("td");
            const accionesWrap = document.createElement("div");

            accionesWrap.className = "usuarios-acciones";

            if (usuario.activo) {
                accionesWrap.appendChild(
                    crearBotonAccion(
                        "Editar",
                        "editar",
                        usuario.id_usuario
                    )
                );

                accionesWrap.appendChild(
                    crearBotonAccion(
                        "Correo",
                        "correo",
                        usuario.id_usuario
                    )
                );

                if (usuario.bloqueado) {
                    accionesWrap.appendChild(
                        crearBotonAccion(
                            "Desbloquear",
                            "desbloquear",
                            usuario.id_usuario
                        )
                    );
                }

                accionesWrap.appendChild(
                    crearBotonAccion(
                        "Revocar sesiones",
                        "revocar",
                        usuario.id_usuario
                    )
                );

                accionesWrap.appendChild(
                    crearBotonAccion(
                        "Contraseña",
                        "password",
                        usuario.id_usuario
                    )
                );

                accionesWrap.appendChild(
                    crearBotonAccion(
                        "Desactivar",
                        "desactivar",
                        usuario.id_usuario,
                        "peligro"
                    )
                );
            } else {
                accionesWrap.appendChild(
                    crearBotonAccion(
                        "Reactivar",
                        "reactivar",
                        usuario.id_usuario,
                        "primario"
                    )
                );
            }

            tdAcciones.appendChild(accionesWrap);

            fila.append(
                tdUsuario,
                tdCorreo,
                tdRol,
                tdEstado,
                tdBloqueo,
                tdUltimoAcceso,
                tdAcciones
            );

            elementos.tabla.appendChild(fila);
        }
    }

    function actualizarPaginacion() {
        elementos.textoPagina.textContent =
            `Página ${estado.pagina + 1}`;

        elementos.btnAnterior.disabled =
            estado.cargando ||
            estado.pagina === 0;

        elementos.btnSiguiente.disabled =
            estado.cargando ||
            estado.usuarios.length < LIMITE;
    }

    async function cargarUsuarios({ conservarMensaje = false } = {}) {
        if (estado.cargando) return;

        estado.cargando = true;

        if (!conservarMensaje) {
            ocultarMensajes();
        }

        elementos.tabla.innerHTML = `
            <tr>
                <td colspan="7" class="usuarios-tabla-estado">
                    Cargando...
                </td>
            </tr>
        `;

        actualizarPaginacion();

        try {
            const respuesta =
                await window.UsuariosAPI.listar({
                    skip: estado.pagina * LIMITE,
                    limit: LIMITE,
                    estado: elementos.filtroEstado.value
                });

            estado.usuarios =
                Array.isArray(respuesta)
                    ? respuesta
                    : [];

            renderUsuarios();
        } catch (error) {
            estado.usuarios = [];

            elementos.tabla.innerHTML = `
                <tr>
                    <td colspan="7" class="usuarios-tabla-estado">
                        No fue posible cargar los usuarios.
                    </td>
                </tr>
            `;

            mostrarError(error);
        } finally {
            estado.cargando = false;
            actualizarPaginacion();
        }
    }

    function abrirModalUsuario(usuario = null) {
        elementos.formUsuario.reset();
        elementos.usuarioModalError.hidden = true;

        elementos.usuarioId.value =
            usuario
                ? String(usuario.id_usuario)
                : "";

        elementos.usuarioModo.value =
            usuario
                ? "editar"
                : "crear";

        elementos.modalUsuarioTitulo.textContent =
            usuario
                ? "Editar usuario"
                : "Nuevo usuario";

        elementos.btnGuardarUsuario.textContent =
            usuario
                ? "Guardar cambios"
                : "Crear usuario";

        if (usuario) {
            elementos.usuarioNombre.value =
                usuario.nombre || "";

            elementos.usuarioApellidoPaterno.value =
                usuario.apellido_paterno || "";

            elementos.usuarioApellidoMaterno.value =
                usuario.apellido_materno || "";

            elementos.usuarioCorreo.value =
                usuario.correo || "";

            elementos.usuarioCorreo.disabled = true;
            elementos.usuarioCorreo.required = false;

            elementos.usuarioCorreoAyuda.textContent =
                "El correo se cambia desde la acción «Correo» porque ese endpoint revoca sesiones.";

            elementos.usuarioRol.value =
                usuario.rol || "operador";

            elementos.grupoContrasenaCrear.hidden = true;
            elementos.usuarioContrasena.required = false;
            elementos.usuarioContrasena.value = "";
        } else {
            elementos.usuarioCorreo.disabled = false;
            elementos.usuarioCorreo.required = true;

            elementos.usuarioCorreoAyuda.textContent =
                "El backend normaliza el correo a minúsculas.";

            elementos.usuarioRol.value = "operador";

            elementos.grupoContrasenaCrear.hidden = false;
            elementos.usuarioContrasena.required = true;
        }

        elementos.modalUsuario.hidden = false;

        document.body.classList.add(
            "usuarios-modal-abierto"
        );

        elementos.usuarioNombre.focus();
    }

    function abrirModalAccion(tipo, usuario) {
        const config = acciones[tipo];

        if (!config) return;

        elementos.formAccion.reset();
        elementos.accionModalError.hidden = true;

        elementos.accionUsuarioId.value =
            String(usuario.id_usuario);

        elementos.accionUsuarioTipo.value = tipo;

        elementos.modalAccionTitulo.textContent =
            config.titulo;

        elementos.modalAccionDescripcion.textContent =
            `${config.descripcion} Usuario: ${nombreCompleto(usuario)} (${usuario.correo}).`;

        elementos.grupoAccionCorreo.hidden =
            !config.usaCorreo;

        elementos.accionCorreo.required =
            config.usaCorreo;

        elementos.accionCorreo.value =
            config.usaCorreo
                ? usuario.correo || ""
                : "";

        elementos.grupoAccionContrasena.hidden =
            !config.usaContrasena;

        elementos.accionContrasena.required =
            config.usaContrasena;

        elementos.accionContrasena.value = "";

        elementos.accionMotivo.maxLength =
            config.motivoMaximo;

        elementos.accionMotivo.value = "";

        elementos.btnConfirmarAccion.textContent =
            config.textoBoton;

        elementos.btnConfirmarAccion.className =
            config.clasePeligro
                ? "usuarios-btn usuarios-btn-peligro"
                : "usuarios-btn usuarios-btn-primario";

        elementos.modalAccion.hidden = false;

        document.body.classList.add(
            "usuarios-modal-abierto"
        );

        if (config.usaCorreo) {
            elementos.accionCorreo.focus();
            elementos.accionCorreo.select();
        } else if (config.usaContrasena) {
            elementos.accionContrasena.focus();
        } else {
            elementos.accionMotivo.focus();
        }
    }

    function cerrarModal(tipo) {
        if (tipo === "usuario") {
            elementos.modalUsuario.hidden = true;
        }

        if (tipo === "accion") {
            elementos.modalAccion.hidden = true;
        }

        if (
            elementos.modalUsuario.hidden &&
            elementos.modalAccion.hidden
        ) {
            document.body.classList.remove(
                "usuarios-modal-abierto"
            );
        }
    }

    function buscarUsuarioActual(idUsuario) {
        return (
            estado.usuarios.find(
                (usuario) =>
                    Number(usuario.id_usuario) ===
                    Number(idUsuario)
            ) || null
        );
    }

    elementos.btnNuevo.addEventListener(
        "click",
        () => {
            ocultarMensajes();
            abrirModalUsuario();
        }
    );

    elementos.btnRecargar.addEventListener(
        "click",
        () => {
            cargarUsuarios();
        }
    );

    elementos.filtroEstado.addEventListener(
        "change",
        () => {
            estado.pagina = 0;
            elementos.busqueda.value = "";
            cargarUsuarios();
        }
    );

    elementos.busqueda.addEventListener(
        "input",
        renderUsuarios
    );

    elementos.btnAnterior.addEventListener(
        "click",
        () => {
            if (
                estado.pagina === 0 ||
                estado.cargando
            ) {
                return;
            }

            estado.pagina -= 1;
            elementos.busqueda.value = "";

            cargarUsuarios();
        }
    );

    elementos.btnSiguiente.addEventListener(
        "click",
        () => {
            if (
                estado.cargando ||
                estado.usuarios.length < LIMITE
            ) {
                return;
            }

            estado.pagina += 1;
            elementos.busqueda.value = "";

            cargarUsuarios();
        }
    );

    elementos.formUsuario.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();
            ocultarMensajes();

            const modo =
                elementos.usuarioModo.value;

            const idUsuario =
                Number(elementos.usuarioId.value);

            elementos.btnGuardarUsuario.disabled = true;

            try {
                if (modo === "crear") {
                    await window.UsuariosAPI.crear({
                        nombre:
                            elementos.usuarioNombre.value.trim(),

                        apellido_paterno:
                            elementos.usuarioApellidoPaterno.value.trim(),

                        apellido_materno:
                            elementos.usuarioApellidoMaterno.value.trim() ||
                            null,

                        correo:
                            elementos.usuarioCorreo.value.trim(),

                        rol:
                            elementos.usuarioRol.value,

                        contrasena:
                            elementos.usuarioContrasena.value
                    });

                    cerrarModal("usuario");

                    estado.pagina = 0;

                    await cargarUsuarios({
                        conservarMensaje: true
                    });

                    mostrarExito(
                        "Usuario creado correctamente."
                    );
                } else {
                    await window.UsuariosAPI.actualizar(
                        idUsuario,
                        {
                            nombre:
                                elementos.usuarioNombre.value.trim(),

                            apellido_paterno:
                                elementos.usuarioApellidoPaterno.value.trim(),

                            apellido_materno:
                                elementos.usuarioApellidoMaterno.value.trim() ||
                                null,

                            rol:
                                elementos.usuarioRol.value
                        }
                    );

                    cerrarModal("usuario");

                    await cargarUsuarios({
                        conservarMensaje: true
                    });

                    mostrarExito(
                        "Usuario actualizado correctamente."
                    );
                }
            } catch (error) {
                mostrarError(
                    error,
                    elementos.usuarioModalError
                );
            } finally {
                elementos.btnGuardarUsuario.disabled = false;
            }
        }
    );

    elementos.tabla.addEventListener(
        "click",
        (event) => {
            const boton = event.target.closest(
                "button[data-accion][data-id-usuario]"
            );

            if (!boton) return;

            const usuario =
                buscarUsuarioActual(
                    boton.dataset.idUsuario
                );

            if (!usuario) return;

            const accion =
                boton.dataset.accion;

            ocultarMensajes();

            if (accion === "editar") {
                abrirModalUsuario(usuario);
                return;
            }

            abrirModalAccion(
                accion,
                usuario
            );
        }
    );

    elementos.formAccion.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();
            ocultarMensajes();

            const idUsuario =
                Number(
                    elementos.accionUsuarioId.value
                );

            const tipo =
                elementos.accionUsuarioTipo.value;

            const motivo =
                elementos.accionMotivo.value.trim();

            elementos.btnConfirmarAccion.disabled = true;

            try {
                let mensaje =
                    "Acción realizada correctamente.";

                if (tipo === "correo") {
                    const respuesta =
                        await window.UsuariosAPI.cambiarCorreo(
                            idUsuario,
                            elementos.accionCorreo.value.trim(),
                            motivo
                        );

                    mensaje =
                        `Correo actualizado. Sesiones revocadas: ${respuesta.sesiones_revocadas}.`;

                } else if (tipo === "desbloquear") {
                    await window.UsuariosAPI.desbloquear(
                        idUsuario,
                        motivo
                    );

                    mensaje =
                        "Cuenta desbloqueada correctamente.";

                } else if (tipo === "revocar") {
                    const respuesta =
                        await window.UsuariosAPI.revocarSesiones(
                            idUsuario,
                            motivo
                        );

                    mensaje =
                        `Sesiones revocadas: ${respuesta.sesiones_revocadas}.`;

                } else if (tipo === "password") {
                    const respuesta =
                        await window.UsuariosAPI.restablecerContrasena(
                            idUsuario,
                            elementos.accionContrasena.value,
                            motivo
                        );

                    mensaje =
                        `Contraseña restablecida. Sesiones revocadas: ${respuesta.sesiones_revocadas}.`;

                } else if (tipo === "desactivar") {
                    await window.UsuariosAPI.desactivar(
                        idUsuario,
                        motivo
                    );

                    mensaje =
                        "Usuario desactivado correctamente.";

                } else if (tipo === "reactivar") {
                    await window.UsuariosAPI.reactivar(
                        idUsuario,
                        motivo
                    );

                    mensaje =
                        "Usuario reactivado correctamente.";

                } else {
                    return;
                }

                cerrarModal("accion");

                await cargarUsuarios({
                    conservarMensaje: true
                });

                mostrarExito(mensaje);

            } catch (error) {
                mostrarError(
                    error,
                    elementos.accionModalError
                );
            } finally {
                elementos.btnConfirmarAccion.disabled = false;
            }
        }
    );

    document
        .querySelectorAll("[data-cerrar-modal]")
        .forEach((boton) => {
            boton.addEventListener(
                "click",
                () => {
                    cerrarModal(
                        boton.dataset.cerrarModal
                    );
                }
            );
        });

    elementos.modalUsuario.addEventListener(
        "click",
        (event) => {
            if (
                event.target ===
                elementos.modalUsuario
            ) {
                cerrarModal("usuario");
            }
        }
    );

    elementos.modalAccion.addEventListener(
        "click",
        (event) => {
            if (
                event.target ===
                elementos.modalAccion
            ) {
                cerrarModal("accion");
            }
        }
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (event.key !== "Escape") {
                return;
            }

            if (!elementos.modalAccion.hidden) {
                cerrarModal("accion");
                return;
            }

            if (!elementos.modalUsuario.hidden) {
                cerrarModal("usuario");
            }
        }
    );

    try {
        const sesion =
            await window.AuthAPI.requerirSesion();

        if (!sesion) return;

        await cargarUsuarios();

    } catch (error) {
        mostrarError(error);
    }
});