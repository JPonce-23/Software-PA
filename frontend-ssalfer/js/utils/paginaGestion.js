document.addEventListener("DOMContentLoaded", () => {
    if (!document.body.classList.contains("ssalfer-gestion-pagina")) return;
    const aside = document.querySelector(".aside"), boton = document.querySelector(".btn-menu");
    if (!aside || !boton) return;
    if (matchMedia("(max-width: 650px)").matches) aside.classList.add("collapsed");
    boton.setAttribute("aria-label", "Abrir o cerrar navegación");
    const actualizar = () => boton.setAttribute("aria-expanded", String(!aside.classList.contains("collapsed")));
    actualizar(); new MutationObserver(actualizar).observe(aside, { attributes: true, attributeFilter: ["class"] });
});
