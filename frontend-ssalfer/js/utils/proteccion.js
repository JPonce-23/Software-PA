/* Barrera de presentación. La API sigue autorizando cada operación. */
(() => {
    if (window.SSALFER_PROTECCION) return;
    const estilo = document.createElement('style');
    estilo.id = 'ssalferProteccion';
    estilo.textContent = 'html{visibility:hidden!important}';
    document.head.append(estilo);
    let resolver, iniciada = false, salida = false, edicion = false;
    window.SSALFER_SESION_LISTA = new Promise(r => resolver = r);
    const alCargar = fn => document.readyState === 'loading'
        ? document.addEventListener('DOMContentLoaded', fn, { once: true }) : fn();
    // Solo una marca en memoria. Nunca se copian ni persisten valores del formulario.
    for (const evento of ['input', 'change']) document.addEventListener(evento, e => {
        if (e.isTrusted && e.target.closest?.('form') && !e.target.closest('[role="search"]')) edicion = true;
    });
    function irAlLogin() {
        const retorno = location.pathname + location.search;
        location.replace('/Index.html?return_to=' + encodeURIComponent(retorno));
    }
    function mostrarFallo(titulo, mensaje, destino) {
        alCargar(() => {
            const main = document.createElement('main');
            const h = document.createElement('h1'); h.textContent = titulo;
            const p = document.createElement('p'); p.textContent = mensaje;
            const b = document.createElement(destino ? 'a' : 'button');
            b.textContent = destino ? 'Volver a mis proyectos' : 'Reintentar';
            if (destino) b.href = destino; else { b.type = 'button'; b.onclick = () => location.reload(); }
            main.append(h, p, b); document.body.replaceChildren(main); estilo.remove();
        });
    }
    window.SSALFER_PROTECCION = {
        permitir(sesion) {
            if (!window.SSALFER_PERMISOS?.iniciar(sesion)) {
                this.cerrar();
                mostrarFallo('Acceso no permitido', 'Tu rol no tiene acceso a esta pantalla.', '/dashboard.html');
                return;
            }
            iniciada = true;
            estilo.remove(); resolver(sesion);
        },
        cerrar() { resolver(null); },
        confirmarSalida() {
            return !edicion || window.confirm('Has editado un formulario. Revisa que hayas guardado los cambios antes de cerrar sesión. ¿Quieres salir?');
        },
        iniciarSesion() {
            if (salida) return;
            salida = true;
            window.SSALFER_SESION_INVALIDA = true;
            this.cerrar();
            if (!iniciada || !edicion) { irAlLogin(); return; }
            // No sustituir el formulario ni redirigir sin aviso al perder una sesión.
            alCargar(() => {
                const dialogo = document.createElement('dialog');
                dialogo.id = 'avisoSesionTerminada';
                dialogo.setAttribute('aria-labelledby', 'tituloSesionTerminada');
                dialogo.setAttribute('aria-describedby', 'detalleSesionTerminada');
                dialogo.style.cssText = 'max-width:32rem;width:calc(100% - 3rem);box-sizing:border-box;padding:24px;border:1px solid #285438;border-radius:12px;';
                const h = document.createElement('h2'); h.id = 'tituloSesionTerminada'; h.textContent = 'Tu sesión terminó';
                const p = document.createElement('p'); p.id = 'detalleSesionTerminada';
                p.textContent = 'Has editado un formulario. Los cambios que no hayas guardado se perderán al ir al inicio de sesión. No se guardó una copia en este navegador.';
                const b = document.createElement('button'); b.type = 'button'; b.textContent = 'Ir al inicio de sesión'; b.onclick = irAlLogin;
                dialogo.addEventListener('cancel', e => e.preventDefault());
                dialogo.append(h, p, b); document.body.append(dialogo); dialogo.showModal(); b.focus();
            });
        },
        fallo(error) {
            // Una comprobación fallida no es una revocación ni un cierre de sesión.
            this.cerrar();
            const prohibido = error?.status === 403;
            mostrarFallo(prohibido ? 'No se pudo autorizar el acceso' : 'No se pudo comprobar tu sesión',
                prohibido ? 'El servidor rechazó el acceso. Tu sesión no se ha cerrado. Si persiste, consulta al administrador.'
                    : 'Comprueba tu conexión y vuelve a intentar. Tu sesión no se ha cerrado.');
        }
    };
    window.addEventListener('pageshow', e => { if (e.persisted) location.reload(); });
})();
