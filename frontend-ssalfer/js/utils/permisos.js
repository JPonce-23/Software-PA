/* Presentación por rol. El servidor conserva la autorización por proyecto y operación. */
(() => {
    'use strict';
    const roles = ['admin', 'operador', 'visualizador', 'geografo'];
    const exclusivas = {
        'usuarios.html': ['admin'], 'catalogosOperativos.html': ['admin'],
        'auditoria.html': ['admin'], 'nuevoProyecto.html': ['admin'],
        'nuevoConvenio.html': ['admin', 'operador'],
        'tramiteRan.html': ['admin', 'operador'],
        'gestionGeoespacial.html': ['admin', 'geografo']
    };
    const consultaGeografica = new Set(['dashboard.html', 'fichaProyecto.html', 'nucleoAgrario.html', 'parcela.html', 'mapa.html', 'gestionGeoespacial.html', 'cambiarContrasena.html']);
    const rolesPagina = nombre => exclusivas[nombre] || roles.filter(r => r !== 'geografo' || consultaGeografica.has(nombre));
    let rol = null;
    const permite = lista => roles.includes(rol) && (rol === 'admin' || lista.split(/\s+/).includes(rol));
    function acceso(ruta, candidato = rol) {
        const nombre = new URL(ruta, location.href).pathname.split('/').pop();
        return roles.includes(candidato) && rolesPagina(nombre).includes(candidato);
    }
    function aplicar(raiz = document) {
        if (!raiz.querySelectorAll) return;
        const enlaces = [...raiz.querySelectorAll('a[href]')];
        if (raiz.matches?.('a[href]')) enlaces.push(raiz);
        enlaces.forEach(a => {
            const url = new URL(a.getAttribute('href'), location.href);
            const lista = url.origin === location.origin && url.pathname.endsWith('.html') && rolesPagina(url.pathname.split('/').pop());
            if (lista && a.dataset.role !== lista.join(' ')) a.dataset.role = lista.join(' ');
        });
    }
    function iniciar(sesion) {
        rol = sesion?.user?.rol;
        if (!acceso(location.href) || !permite(document.documentElement.dataset.role || '')) return false;
        document.documentElement.dataset.rolActual = rol;
        const style = document.createElement('style');
        style.textContent = rol === 'admin' ? '' : `[data-role]:not([data-role~="${rol}"]){display:none!important}`;
        document.head.append(style);
        aplicar();
        new MutationObserver(cambios => cambios.forEach(c => {
            if (c.type === 'attributes') aplicar(c.target);
            else c.addedNodes.forEach(aplicar);
        })).observe(document.documentElement, {subtree:true, childList:true, attributes:true, attributeFilter:['href']});
        return true;
    }
    for (const evento of ['click', 'submit']) document.addEventListener(evento, e => {
        if (!rol) return;
        const control = e.target.closest?.('[data-role]');
        const enlace = e.target.closest?.('a[href]');
        if ((control && !permite(control.dataset.role)) || (enlace && !acceso(enlace.href))) {
            e.preventDefault(); e.stopImmediatePropagation();
        }
    }, true);
    function puedeEscribir(ruta, metodo) {
        if (['GET','HEAD','OPTIONS'].includes(metodo.toUpperCase())) return true;
        const p = ruta.split('?')[0];
        if (/^\/auth\/(logout|logout-todas|cambiar-contrasena)$/.test(p)) return true;
        if (rol === 'admin') return true;
        const gis = /\/geoespacial(?:\/|$)|^\/importaciones(?:\/|$)|\/importaciones$|\/geometria$/.test(p);
        if (gis) return rol === 'geografo';
        if (rol !== 'operador') return false;
        if (/^\/(usuarios|catalogos)(\/|$)|^\/proyectos(?:\/\d+)?$|^\/proyectos\/\d+\/usuarios|^\/nucleos(?:\/\d+)?$/.test(p)) return false;
        if (/^\/(personas|orv-integrantes)\/\d+(?:\/reactivar|\/baja)?$/.test(p) && (metodo.toUpperCase() === 'DELETE' || /\/(reactivar|baja)$/.test(p))) return false;
        return true;
    }
    window.SSALFER_PERMISOS = {iniciar, acceso, permite, puedeEscribir};
})();
