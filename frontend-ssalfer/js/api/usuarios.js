/**
 * js/api/usuarios.js
 * Administración de usuarios.
 *
 * No usa fetch() directamente: todas las peticiones pasan por ClienteAPI.
 */
(function () {
    "use strict";

    const { get, post, patch, del } = window.ClienteAPI;

    function listar({ skip = 0, limit = 50, estado = "activos" } = {}) {
        const query = new URLSearchParams({
            skip: String(skip),
            limit: String(limit),
            estado
        });

        return get(`/usuarios?${query.toString()}`);
    }

    function crear(payload) {
        return post("/usuarios", payload);
    }

    function actualizar(idUsuario, payload) {
        return patch(`/usuarios/${encodeURIComponent(idUsuario)}`, payload);
    }

    function cambiarCorreo(idUsuario, correo, motivo) {
        return patch(`/usuarios/${encodeURIComponent(idUsuario)}/correo`, {
            correo,
            motivo
        });
    }

    function reactivar(idUsuario, motivo) {
        return post(`/usuarios/${encodeURIComponent(idUsuario)}/reactivar`, {
            motivo
        });
    }

    function desactivar(idUsuario, motivo) {
        return del(`/usuarios/${encodeURIComponent(idUsuario)}`, {
            motivo
        });
    }

    function desbloquear(idUsuario, motivo) {
        return post(`/usuarios/${encodeURIComponent(idUsuario)}/desbloquear`, {
            motivo
        });
    }

    function revocarSesiones(idUsuario, motivo) {
        return post(`/usuarios/${encodeURIComponent(idUsuario)}/revocar-sesiones`, {
            motivo
        });
    }

    function restablecerContrasena(idUsuario, contrasenaNueva, motivo) {
        return post(`/usuarios/${encodeURIComponent(idUsuario)}/restablecer-contrasena`, {
            contrasena_nueva: contrasenaNueva,
            motivo
        });
    }

    window.UsuariosAPI = {
        listar,
        crear,
        actualizar,
        cambiarCorreo,
        reactivar,
        desactivar,
        desbloquear,
        revocarSesiones,
        restablecerContrasena
    };
})();