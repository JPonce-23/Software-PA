document.addEventListener("DOMContentLoaded", async () => {
    const id = Number(new URLSearchParams(location.search).get("id_proyecto_nucleo"));
    const raiz = document.getElementById("documentosContenido");
    if (!Number.isSafeInteger(id) || id <= 0) { raiz.textContent = "Abre Documentos desde la ficha de un núcleo."; return; }
    try {
        const nucleo = await window.NucleosAPI.obtenerProyectoNucleo(id);
        document.getElementById("documentosContexto").textContent = nucleo.nombre_nucleo;
        raiz.innerHTML='<details><summary>Registrar y gestionar documentos</summary><div data-gestor></div></details>';
        const gestion=raiz.querySelector('details');let montado=false;
        gestion.addEventListener('toggle',async()=>{if(!gestion.open||montado)return;montado=true;try{await window.SSALFER_GESTOR_DOCUMENTOS.montar(gestion.querySelector('[data-gestor]'),id);}catch(error){montado=false;window.ClienteAPI.mostrarErrorAPI(error);}});
        const listado = document.createElement("section"); listado.className="ssalfer-gestion-seccion"; raiz.after(listado);
        await window.SSALFER_LISTADO_DOCUMENTOS.montar(listado, id);
    } catch (error) { raiz.textContent = error.message || "No se pudo cargar el núcleo."; raiz.setAttribute("role", "alert"); }
});
