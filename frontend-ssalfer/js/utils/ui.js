(() => {
    "use strict";

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function obtenerRegionToast() {
        let region = document.getElementById("ssalferToastRegion");

        if (!region) {
            region = document.createElement("div");
            region.id = "ssalferToastRegion";
            region.className = "ssalfer-toast-region";
            region.setAttribute("aria-live", "polite");
            region.setAttribute("aria-atomic", "false");
            document.body.appendChild(region);
        }

        return region;
    }

    function toast(mensaje, opciones = {}) {
        if (!mensaje) return null;

        const tipo = opciones.tipo === "error" ? "error" : "success";
        const duracion = Number.isFinite(opciones.duracion)
            ? opciones.duracion
            : (tipo === "error" ? 6500 : 3500);

        const elemento = document.createElement("div");
        elemento.className = `ssalfer-toast ssalfer-toast--${tipo}`;
        elemento.setAttribute("role", tipo === "error" ? "alert" : "status");

        elemento.innerHTML = `
            <span aria-hidden="true">${tipo === "error" ? "⚠" : "✓"}</span>
            <span>${escaparHTML(mensaje)}</span>
            <button type="button" class="ssalfer-toast__close" aria-label="Cerrar">×</button>
        `;

        const cerrar = () => elemento.remove();
        elemento.querySelector(".ssalfer-toast__close")?.addEventListener("click", cerrar);
        obtenerRegionToast().appendChild(elemento);

        if (duracion > 0) {
            window.setTimeout(cerrar, duracion);
        }

        return elemento;
    }

    function contenidoDatos(datos) {
        const filas = Object.entries(datos || {})
            .map(([etiqueta, valor]) => `
                <dt>${escaparHTML(etiqueta)}</dt>
                <dd>${escaparHTML(valor ?? "—")}</dd>
            `)
            .join("");

        return `<dl class="ssalfer-modal__grid">${filas}</dl>`;
    }

    let secuenciaModal = 0;
    function abrirModal({ titulo = "Detalle", contenido = "", acciones = [], validar, preparar } = {}) {
        return new Promise(resolve => {
            const fondo = document.createElement("div");
            fondo.className = "ssalfer-modal-backdrop";
            const tituloId = `ssalferModalTitle-${++secuenciaModal}`;

            const botones = (acciones.length ? acciones : [
                { valor: true, texto: "Cerrar", principal: true }
            ]).map((accion, indice) => `
                <button
                    type="button"
                    class="ssalfer-modal__button${accion.principal ? " ssalfer-modal__button--primary" : ""}"
                    data-modal-accion="${indice}">
                    ${escaparHTML(accion.texto || "Aceptar")}
                </button>
            `).join("");

            fondo.innerHTML = `
                <section class="ssalfer-modal" role="dialog" aria-modal="true" aria-labelledby="${tituloId}">
                    <header class="ssalfer-modal__header">
                        <h2 id="${tituloId}" class="ssalfer-modal__title">${escaparHTML(titulo)}</h2>
                        <button type="button" class="ssalfer-modal__close" data-modal-cerrar aria-label="Cerrar">×</button>
                    </header>
                    <div class="ssalfer-modal__body">${contenido}</div>
                    <footer class="ssalfer-modal__footer">${botones}</footer>
                </section>
            `;

            let resuelto = false;
            let pendiente = false;
            const focoAnterior = document.activeElement;
            const cerrar = valor => {
                if (resuelto) return;
                resuelto = true;
                document.removeEventListener("keydown", onKeydown);
                fondo.remove();
                if (focoAnterior?.isConnected) focoAnterior.focus({ preventScroll: true });
                resolve(valor);
            };

            const onKeydown = event => {
                if (fondo !== [...document.querySelectorAll(".ssalfer-modal-backdrop")].at(-1)) return;
                if (event.key === "Escape" && !pendiente) { event.preventDefault(); cerrar(null); }
                if (event.key === "Tab") {
                    const controles = [...fondo.querySelectorAll('button, input, select, textarea, a[href], [tabindex="0"]')].filter(n => !n.disabled && n.getClientRects().length);
                    const primero = controles[0], ultimo = controles.at(-1);
                    if (event.shiftKey && document.activeElement === primero) { event.preventDefault(); ultimo?.focus(); }
                    else if (!event.shiftKey && document.activeElement === ultimo) { event.preventDefault(); primero?.focus(); }
                }
            };

            fondo.addEventListener("click", async event => {
                if (pendiente) return;
                if (event.target === fondo || event.target.closest("[data-modal-cerrar]")) {
                    cerrar(null);
                    return;
                }

                const boton = event.target.closest("[data-modal-accion]");
                if (!boton) return;

                const indice = Number(boton.dataset.modalAccion);
                const valor = acciones.length ? acciones[indice]?.valor : true;
                pendiente = true;
                const controles = [...fondo.querySelectorAll("[data-modal-accion], [data-modal-cerrar]")];
                controles.forEach(control => { control.disabled = true; });
                try {
                    if (validar && !await validar(valor, fondo)) return;
                    cerrar(valor);
                } catch (error) {
                    toast(error.message || "No se pudo completar la acción.", { tipo: "error" });
                } finally {
                    pendiente = false;
                    controles.forEach(control => { control.disabled = false; });
                }
            });

            fondo.addEventListener("submit", event => {
                event.preventDefault();
                fondo.querySelector(".ssalfer-modal__button--primary")?.click();
            });

            document.addEventListener("keydown", onKeydown);
            document.body.appendChild(fondo);
            preparar?.(fondo);
            fondo.querySelector("[data-modal-accion], [data-modal-cerrar]")?.focus();
        });
    }

    function verDatos(titulo, datos) {
        return abrirModal({
            titulo,
            contenido: contenidoDatos(datos)
        });
    }

    function confirmar(mensaje, titulo = "Confirmar acción") {
        return abrirModal({
            titulo,
            contenido: `<p>${escaparHTML(mensaje)}</p>`,
            acciones: [
                { valor: false, texto: "Cancelar" },
                { valor: true, texto: "Confirmar", principal: true }
            ]
        });
    }

    async function solicitarTexto(mensaje, { titulo = "Confirmar acción", minimo = 3, maximo = 500, validar, textoAceptar = "Confirmar" } = {}) {
        let valor = null;
        const confirmado = await abrirModal({
            titulo,
            contenido: `<label class="ssalfer-modal__campo">${escaparHTML(mensaje)}
                <textarea data-modal-texto rows="3" maxlength="${maximo}" required></textarea></label>
                <p data-modal-error role="alert" hidden></p>`,
            acciones: [
                { valor: false, texto: "Cancelar" },
                { valor: true, texto: textoAceptar, principal: true }
            ],
            validar: (aceptar, fondo) => {
                if (!aceptar) return true;
                const campo = fondo.querySelector("[data-modal-texto]");
                valor = campo.value.trim();
                const error = valor.length < minimo || valor.length > maximo
                    ? `Escribe entre ${minimo} y ${maximo} caracteres.`
                    : validar?.(valor);
                const mensajeError = fondo.querySelector("[data-modal-error]");
                mensajeError.textContent = error || "";
                mensajeError.hidden = !error;
                if (error) campo.focus();
                return !error;
            }
        });
        return confirmado ? valor : null;
    }

    // Una entrada por destino: las peticiones paralelas comparten contador y tiempos.
    const cargas = new Map();
    const TEXTO_CARGA = "Cargando...";
    let peticiones = 0;
    let accionUsuario = null;
    let temporizadorAccion;
    const reglasAcciones = [];
    const resolverElemento = valor => typeof valor === "function" ? valor() :
        typeof valor === "string" ? document.querySelector(valor) : valor;
    const visible = elemento => Boolean(elemento?.isConnected && elemento.getClientRects().length &&
        getComputedStyle(elemento).visibility !== "hidden");
    const esModal = elemento => elemento?.closest('[role="dialog"], .ssalfer-modal-backdrop, [id^="modal"], .fifonafe-modal-backdrop');

    function crearIndicador(enLinea) {
        const nodo = document.createElement("div");
        nodo.className = `ssalfer-cargando ${enLinea ? "ssalfer-cargando-inline" : "ssalfer-cargando-pantalla"}`;
        nodo.setAttribute("role", "status");
        nodo.setAttribute("aria-live", "polite");
        nodo.innerHTML = `<div class="ssalfer-cargando-contenido">
            <svg viewBox="0 0 160 105" aria-hidden="true" focusable="false">
                <g class="ssalfer-cargando-humo" fill="currentColor" opacity=".45">
                    <circle cx="105" cy="32" r="7"/><circle cx="105" cy="32" r="7"/><circle cx="105" cy="32" r="7"/>
                </g>
                <path fill="currentColor" d="M20 46h42v31H20z M15 40h52v8H15z M62 54h62v23H62z M99 38h14v22H99z M94 36h24v6H94z M124 68l16 12H15v-7h109z"/>
                <path fill="#eef6f0" d="M28 49h12v13H28z M46 49h10v13H46z"/>
                <g fill="#eef6f0" stroke="currentColor" stroke-width="5">
                    <g class="ssalfer-cargando-rueda"><circle cx="38" cy="80" r="10"/><path d="M38 73v14M31 80h14" stroke-width="2"/></g>
                    <g class="ssalfer-cargando-rueda"><circle cx="74" cy="80" r="10"/><path d="M74 73v14M67 80h14" stroke-width="2"/></g>
                    <g class="ssalfer-cargando-rueda"><circle cx="110" cy="80" r="10"/><path d="M110 73v14M103 80h14" stroke-width="2"/></g>
                </g><path d="M10 94h140" stroke="currentColor" stroke-width="3"/>
            </svg><span>${TEXTO_CARGA}</span></div>`;
        return nodo;
    }

    function programarDesplazamiento() {
        clearTimeout(temporizadorAccion);
        temporizadorAccion = setTimeout(() => {
            if (!accionUsuario || peticiones || cargas.size) return;
            const accion = accionUsuario;
            accionUsuario = null;
            if (accion.condicion && !accion.condicion()) return;
            const destino = resolverElemento(accion.destino);
            if (visible(destino) && !esModal(destino)) moverVista(destino);
        }, 100); // El consumidor de la promesa termina de renderizar antes del enfoque.
    }

    function iniciarCarga({ silencioso = false, carga, metodo = "GET" } = {}) {
        if (silencioso || /(?:gestionGeoespacial|mapa)\.html$/i.test(location.pathname)) return () => {};
        peticiones++;
        const solicitado = resolverElemento(carga ?? (metodo.toUpperCase() === "GET" ? accionUsuario?.carga : null));
        const destino = visible(solicitado) ? solicitado : document.body;
        let estado = cargas.get(destino);
        if (!estado) {
            estado = { cuenta: 0, nodo: null, inicio: 0, solicitado: performance.now() };
            cargas.set(destino, estado);
        }
        if (!estado.cuenta && !estado.nodo) {
            estado.mostrar = setTimeout(() => {
                estado.nodo = crearIndicador(destino !== document.body);
                estado.inicio = performance.now();
                if (destino === document.body) destino.appendChild(estado.nodo);
                else destino.prepend(estado.nodo);
            }, Math.max(0, 300 - (performance.now() - estado.solicitado)));
        }
        clearTimeout(estado.ocultar);
        estado.cuenta++;
        let finalizada = false;
        return () => {
            if (finalizada) return;
            finalizada = true;
            peticiones--;
            if (--estado.cuenta === 0) {
                clearTimeout(estado.mostrar);
                const quitar = () => {
                    estado.nodo?.remove();
                    cargas.delete(destino);
                    programarDesplazamiento();
                };
                estado.ocultar = setTimeout(quitar, estado.nodo ? Math.max(0, 400 - (performance.now() - estado.inicio)) : 0);
            }
            programarDesplazamiento();
        };
    }

    function moverVista(elemento) {
        const rect = elemento.getBoundingClientRect();
        // Solo barras que realmente cruzan el destino; una barra lateral no es un encabezado.
        let margen = 16;
        document.querySelectorAll('header, nav, aside, .menu, .sidebar, .encabezado, [data-scroll-cabecera]').forEach(barra => {
            const css = getComputedStyle(barra), r = barra.getBoundingClientRect();
            if (["fixed", "sticky"].includes(css.position) && r.top < innerHeight * .5 && r.bottom > 0 &&
                r.height < innerHeight * .75 && r.right > rect.left && r.left < rect.right) margen = Math.max(margen, r.bottom + 16);
        });
        const foco = elemento.matches('input, select, textarea, button, a, h1, h2, h3, h4') ? elemento :
            [...elemento.querySelectorAll('h1, h2, h3, h4, input:not([type="hidden"]):not(:disabled), select:not(:disabled), textarea:not(:disabled)')].find(visible) || elemento;
        if (!foco.matches('input, select, textarea, button, a[href]')) foco.setAttribute("tabindex", "-1");
        foco.focus({ preventScroll: true });
        if (rect.top < margen || rect.bottom > innerHeight - 16) {
            window.scrollTo({ top: Math.max(0, scrollY + rect.top - margen),
                behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
        }
    }

    function desplazarA(elemento) {
        // Sin un evento de usuario pendiente, los refrescos y cargas iniciales no desplazan.
        if (!accionUsuario || !elemento || esModal(elemento)) return;
        accionUsuario.destino ||= elemento;
        programarDesplazamiento();
    }

    function registrarAcciones(reglas) { reglasAcciones.push(...reglas); }

    ["click", "change", "submit"].forEach(tipo => document.addEventListener(tipo, event => {
        if (!event.isTrusted || !(event.target instanceof Element)) return;
        const regla = reglasAcciones.find(item => (item.evento || "click") === tipo && event.target.closest(item.selector));
        accionUsuario = { ...regla };
        if (esModal(event.target)) accionUsuario = null;
        programarDesplazamiento();
    }, true));
    // No quitar el foco a alguien que ya continuó escribiendo o desplazándose manualmente.
    ["wheel", "touchstart", "keydown"].forEach(tipo => document.addEventListener(tipo, event => {
        if (event.isTrusted && (tipo !== "keydown" || !["Enter", " "].includes(event.key))) accionUsuario = null;
    }, { capture: true, passive: true }));

    window.SSALFER_UI = Object.freeze({
        cargando: Object.freeze({ iniciar: iniciarCarga }),
        desplazarA,
        registrarAcciones,
        escaparHTML,
        toast,
        abrirModal,
        verDatos,
        confirmar,
        solicitarTexto,
        contenidoDatos
    });
})();
