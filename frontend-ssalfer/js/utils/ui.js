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

    function abrirModal({ titulo = "Detalle", contenido = "", acciones = [], validar } = {}) {
        return new Promise(resolve => {
            const fondo = document.createElement("div");
            fondo.className = "ssalfer-modal-backdrop";

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
                <section class="ssalfer-modal" role="dialog" aria-modal="true" aria-labelledby="ssalferModalTitle">
                    <header class="ssalfer-modal__header">
                        <h2 id="ssalferModalTitle" class="ssalfer-modal__title">${escaparHTML(titulo)}</h2>
                        <button type="button" class="ssalfer-modal__close" data-modal-cerrar aria-label="Cerrar">×</button>
                    </header>
                    <div class="ssalfer-modal__body">${contenido}</div>
                    <footer class="ssalfer-modal__footer">${botones}</footer>
                </section>
            `;

            let resuelto = false;
            const cerrar = valor => {
                if (resuelto) return;
                resuelto = true;
                document.removeEventListener("keydown", onKeydown);
                fondo.remove();
                resolve(valor);
            };

            const onKeydown = event => {
                if (event.key === "Escape") cerrar(null);
            };

            fondo.addEventListener("click", event => {
                if (event.target === fondo || event.target.closest("[data-modal-cerrar]")) {
                    cerrar(null);
                    return;
                }

                const boton = event.target.closest("[data-modal-accion]");
                if (!boton) return;

                const indice = Number(boton.dataset.modalAccion);
                const valor = acciones.length ? acciones[indice]?.valor : true;
                if (validar && !validar(valor, fondo)) return;
                cerrar(valor);
            });

            document.addEventListener("keydown", onKeydown);
            document.body.appendChild(fondo);
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

    window.SSALFER_UI = Object.freeze({
        escaparHTML,
        toast,
        abrirModal,
        verDatos,
        confirmar,
        solicitarTexto,
        contenidoDatos
    });
})();
