/* Sesiones por cookie HttpOnly. No se guardan identificadores de sesión en el navegador. */
(() => {
    'use strict';
    if (window.AuthAPI) return;
    const { get, post } = window.ClienteAPI;
    let sesionActual;
    let cierreEnCurso;
    let canal;
    try { canal = new BroadcastChannel('ssalfer-sesion'); } catch { /* Sin sincronización opcional. */ }

    function invalidarSesion() {
        sesionActual = null;
        window.SSALFER_PROTECCION?.iniciarSesion();
    }
    if (canal) canal.onmessage = evento => {
        // Notifica un cierre confirmado; jamás envía otra petición de logout.
        if (evento.data === 'sesion-cerrada') invalidarSesion();
    };
    document.addEventListener('ssalfer:sesion-invalida', invalidarSesion);

    function login(usuario, password) {
        return post('/auth/sesiones', { username: usuario, password }, { formUrlEncoded: true });
    }
    function obtenerSesionActual() {
        return sesionActual ||= get('/auth/sesion', { silencioso: true }).catch(error => {
            sesionActual = null;
            throw error;
        });
    }
    function cerrarSesion(ruta) {
        if (cierreEnCurso) return cierreEnCurso;
        cierreEnCurso = post(ruta, null).then(resultado => {
            sesionActual = null;
            try { canal?.postMessage('sesion-cerrada'); } catch { /* El cierre ya se confirmó en el servidor. */ }
            return resultado;
        }).catch(error => {
            cierreEnCurso = null; // Reintentar no borra la sesión por un error de red/403.
            throw error;
        });
        return cierreEnCurso;
    }
    const logout = () => cerrarSesion('/auth/logout');
    const logoutTodas = () => cerrarSesion('/auth/logout-todas');
    function cambiarContrasena(contrasenaActual, contrasenaNueva) {
        return post('/auth/cambiar-contrasena', {
            contrasena_actual: contrasenaActual, contrasena_nueva: contrasenaNueva
        });
    }
    function falloSesion(error) {
        if (error.status === 401) invalidarSesion();
        else window.SSALFER_PROTECCION?.fallo(error);
    }
    async function requerirSesion() {
        try {
            const sesion = await obtenerSesionActual();
            if (window.SSALFER_PERMISOS && !window.SSALFER_PERMISOS.acceso(location.href, sesion?.user?.rol)) return null;
            return sesion;
        } catch (error) {
            if (!window.SSALFER_PROTECCION) throw error;
            falloSesion(error);
            return null;
        }
    }

    document.addEventListener('click', async evento => {
        const control = evento.target.closest?.('a[data-action],button[data-action]');
        if (!control || evento.defaultPrevented || !evento.isTrusted || evento.button !== 0 ||
            evento.ctrlKey || evento.metaKey || evento.altKey || evento.shiftKey ||
            control.disabled || control.closest('[hidden],[inert]') || !control.getClientRects().length) return;
        if (control.dataset.action !== 'logout') return;
        evento.preventDefault();
        if (cierreEnCurso) return;
        if (window.SSALFER_PROTECCION?.confirmarSalida?.() === false) return;
        control.setAttribute('aria-disabled', 'true');
        control.setAttribute('aria-busy', 'true');
        try {
            await logout();
            window.location.href = '/Index.html';
        } catch (error) {
            if (error.status === 401) invalidarSesion();
            else window.ClienteAPI.mostrarErrorAPI(new Error('No se pudo cerrar la sesión. Intenta nuevamente.'));
        } finally {
            control.removeAttribute('aria-disabled');
            control.removeAttribute('aria-busy');
        }
    });

    window.AuthAPI = { login, obtenerSesionActual, logout, logoutTodas, cambiarContrasena, requerirSesion };
    if (window.SSALFER_PROTECCION) obtenerSesionActual().then(sesion => {
        if (sesion?.user) window.SSALFER_PROTECCION.permitir(sesion);
        else window.SSALFER_PROTECCION.fallo(new Error('Respuesta de sesión incompleta.'));
    }).catch(falloSesion);
})();
