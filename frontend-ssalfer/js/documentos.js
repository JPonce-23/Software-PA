document.addEventListener("DOMContentLoaded", async () => {
    const id = Number(new URLSearchParams(location.search).get("id_proyecto_nucleo"));
    const raiz = document.getElementById("documentosContenido");
    if (!Number.isSafeInteger(id) || id <= 0) { raiz.textContent = "Abre Documentos desde la ficha de un núcleo."; return; }
    try {
        const nucleo = await window.NucleosAPI.obtenerProyectoNucleo(id);
        document.getElementById("documentosContexto").textContent = nucleo.nombre_nucleo;
        await window.SSALFER_GESTOR_DOCUMENTOS.montar(raiz, id);
    } catch (error) { raiz.textContent = error.message || "No se pudo cargar el núcleo."; raiz.setAttribute("role", "alert"); }
});
