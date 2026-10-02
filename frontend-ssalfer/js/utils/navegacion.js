(() => {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        const parametros = new URLSearchParams(window.location.search);
        const idValido = nombre => {
            const id = Number(parametros.get(nombre));
            return Number.isSafeInteger(id) && id > 0 ? id : null;
        };
        const proyecto = idValido("id_proyecto");
        const nucleo = idValido("id_proyecto_nucleo");
        const destinoProyecto = proyecto ? `/pages/fichaProyecto.html?id=${proyecto}` : "/dashboard.html";
        const destinoNucleo = nucleo ? `/pages/nucleoAgrario.html?id_proyecto_nucleo=${nucleo}` : destinoProyecto;
        const boton = document.getElementById("btnVolver");
        if (boton?.dataset.volver) {
            let destino = "/dashboard.html";
            if (boton.dataset.volver === "proyecto") destino = destinoProyecto;
            if (boton.dataset.volver === "nucleo") destino = destinoNucleo;
            if (boton.dataset.volver === "persona") {
                destino = destinoNucleo;
                const origen = parametros.get("return_to");
                if (origen) {
                    try {
                        const url = new URL(origen, window.location.origin);
                        if (url.origin === window.location.origin && url.pathname.startsWith("/pages/") && url.pathname !== "/pages/persona.html") {
                            destino = url.pathname + url.search;
                        }
                    } catch { /* Un origen inválido conserva el regreso al proyecto. */ }
                }
            }
            boton.addEventListener("click", () => { window.location.href = destino; });
        }

        // Conserva el contexto del proyecto en la navegación entre reportes.
        if (proyecto) {
            document.querySelectorAll('a[href^="/pages/reportesConvenios.html"], a[href^="/pages/reportesFifonafe.html"], a[href^="/pages/reporteActividadesPeriodo.html"]').forEach(enlace => {
                const url = new URL(enlace.href);
                url.searchParams.set("id_proyecto", proyecto);
                enlace.href = url.pathname + url.search;
            });
        }
    });
})();
