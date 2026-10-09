/* Navegación común. Mantiene el estado visual separado de los datos del proyecto. */
window.SSALFER_MARCO = true;
document.addEventListener("DOMContentLoaded", () => {
    const aside = document.querySelector(".aside");
    if (!aside) return;
    aside.querySelectorAll(".btn-menu").forEach(b => b.remove());
    const soloInicial = location.pathname.endsWith("/afectacion.html");
    const accesos = document.createElement("nav"); accesos.className = "ssalfer-accesos"; accesos.ariaLabel = "Accesos directos";
    accesos.innerHTML = '<a href="/dashboard.html" title="Todos los proyectos" aria-label="Todos los proyectos"><i class="bi bi-train-front" aria-hidden="true"></i></a><a data-proyecto-actual href="/dashboard.html" title="Proyecto en curso" aria-label="Proyecto en curso"><i class="bi bi-folder2-open" aria-hidden="true"></i></a>';
    aside.prepend(accesos);
    const parametros = new URLSearchParams(location.search);
    const valido = n => Number.isSafeInteger(Number(n)) && Number(n)>0 ? Number(n) : null;
    let proyecto = valido(parametros.get("id_proyecto")) || (location.pathname.endsWith("/fichaProyecto.html") ? valido(parametros.get("id")) : null);
    const pn = valido(parametros.get("id_proyecto_nucleo"));
    function aplicarContexto(id) {
        proyecto = valido(id);
        if (proyecto) try { localStorage.setItem("ssalferUltimoProyecto", String(proyecto)); } catch {}
        const directo = accesos.querySelector('[data-proyecto-actual]');
        directo.href = proyecto ? `/pages/fichaProyecto.html?id=${proyecto}` : '/dashboard.html';
        directo.title = directo.ariaLabel = proyecto ? 'Proyecto en curso' : 'Listado de proyectos';
        aside.querySelectorAll('a').forEach(a => {
            const url = new URL(a.href, location.origin);
            const mapa = url.pathname.endsWith('/mapa.html') || (a.getAttribute('href') === '#' && /ver mapa/i.test(a.textContent));
            if (!mapa && !url.pathname.endsWith('/gestionGeoespacial.html')) return;
            if (mapa) url.pathname = '/pages/mapa.html';
            if (proyecto) url.searchParams.set('id_proyecto', proyecto); else url.searchParams.delete('id_proyecto');
            a.href = url.pathname + url.search;
        });
    }
    if (!proyecto && !pn) try { proyecto = valido(localStorage.getItem('ssalferUltimoProyecto')); } catch {}
    aplicarContexto(proyecto);
    if (pn && !proyecto) window.ClienteAPI.get(`/proyecto-nucleo/${pn}`,{silencioso:true}).then(n=>aplicarContexto(n.id_proyecto)).catch(()=>{});
    document.addEventListener('change', event => {
        if (event.target.matches('#selectorProyectoMapa,#selectorProyectoGeoespacial,[name="id_proyecto"],[data-asignacion-proyecto]')) aplicarContexto(event.target.value);
    });
    aside.addEventListener('click', event => { if(event.target.closest('a')) aplicarContexto(proyecto); },true);
    document.body.classList.add("ssalfer-marco");
    const movil = matchMedia("(max-width: 650px)");
    let cerrado = movil.matches;
    try { if (!movil.matches) cerrado = localStorage.getItem("sidebarColapsado") === "true"; } catch { /* Almacenamiento opcional. */ }
    const flecha = document.createElement("button");
    flecha.type = "button"; flecha.className = "ssalfer-menu-borde";
    document.body.appendChild(flecha);
    aside.id ||= "navegacionPrincipal";
    function actualizar() {
        const oculto = aside.classList.contains("collapsed");
        document.body.classList.toggle("ssalfer-menu-oculto", oculto);
        [flecha].forEach(b => {
            b.setAttribute("aria-expanded", String(!oculto)); b.setAttribute("aria-controls", aside.id);
            b.title = b.ariaLabel = oculto ? "Mostrar menú" : "Ocultar menú";
        });
        flecha.textContent = oculto ? "›" : "‹";
        try { if (!soloInicial) localStorage.setItem("sidebarColapsado", String(oculto)); } catch { /* No impide navegar. */ }
    }
    aside.classList.toggle("collapsed", soloInicial || cerrado); actualizar();
    [flecha].forEach(b => b.addEventListener("click", () => { aside.classList.toggle("collapsed"); actualizar(); }));
    new MutationObserver(actualizar).observe(aside, {attributes:true,attributeFilter:["class"]});
    const boton = aside.querySelector(".usuario-btn");
    if (!boton) return;
    const opciones = aside.querySelector(".opciones-usuario") || document.createElement("div");
    opciones.classList.add("opciones-usuario");
    opciones.replaceChildren();
    const cuenta = (texto,href,accion) => {const a=document.createElement('a');a.textContent=texto;a.href=href;if(accion)a.dataset.action=accion;opciones.append(a);return a;};
    cuenta('Cambiar contraseña','/pages/cambiarContrasena.html','cambiar-contrasena');
    cuenta('Cerrar sesión','#','logout');
    function usuarioCargado(usuario) {
        opciones.querySelectorAll('[data-usuarios]').forEach(a=>a.remove());
        if(location.pathname.endsWith('/dashboard.html') && usuario?.rol==='admin') cuenta('Gestión de usuarios','/pages/usuarios.html').dataset.usuarios='true';
        aside.querySelectorAll('.js-usuario-nombre').forEach(n=>n.textContent=[usuario?.nombre,usuario?.apellido_paterno].filter(Boolean).join(' ')||usuario?.correo||'Usuario');
    }
    document.addEventListener('ssalfer:usuario', e=>usuarioCargado(e.detail));
    if (soloInicial) window.AuthAPI.obtenerSesionActual().then(s=>usuarioCargado(s.user)).catch(()=>{});
    // Fuera del aside evita que su overflow recorte las opciones.
    document.body.appendChild(opciones); opciones.classList.add("ssalfer-menu-usuario");
    opciones.id ||= "opcionesUsuario"; boton.setAttribute("aria-controls", opciones.id);
    boton.querySelectorAll(".bi-chevron-up,.bi-chevron-down").forEach(i=>i.remove());
    const indicador = document.createElement("span"); indicador.className = "ssalfer-flecha-usuario"; indicador.setAttribute("aria-hidden", "true"); boton.appendChild(indicador);
    let abierto = false;
    function colocar() {
        const r = boton.getBoundingClientRect(), ancho = Math.min(270, innerWidth - 24);
        opciones.style.width = `${ancho}px`;
        opciones.style.left = `${Math.max(12, Math.min(r.left, innerWidth - ancho - 12))}px`;
        opciones.style.maxHeight = `${Math.max(80, innerHeight - 24)}px`;
        opciones.style.top = `${Math.max(12, Math.min(r.top - opciones.offsetHeight - 8, innerHeight - opciones.offsetHeight - 12))}px`;
    }
    function abrir(valor, restaurar = false) {
        abierto = valor; opciones.classList.toggle("mostrar", valor); opciones.hidden = !valor;
        boton.setAttribute("aria-expanded", String(valor)); indicador.textContent = valor ? "▾" : "▴";
        if (valor) { colocar(); opciones.querySelector("a,button")?.focus({preventScroll:true}); }
        else if (restaurar) boton.focus({preventScroll:true});
    }
    abrir(false);
    boton.addEventListener("click", e => { e.stopPropagation(); abrir(!abierto); });
    document.addEventListener("click", e => { if (!opciones.contains(e.target) && !boton.contains(e.target)) abrir(false); });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && abierto) { abrir(false, true); e.preventDefault(); } });
    window.addEventListener("resize", () => { if (abierto) colocar(); });
    window.addEventListener("scroll", () => { if (abierto) colocar(); }, true);
});
