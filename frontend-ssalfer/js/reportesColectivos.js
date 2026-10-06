document.addEventListener("DOMContentLoaded", () => {
    const raiz = document.getElementById("reporteColectivo");
    window.SSALFER_REPORTE_COLECTIVO.montar(raiz, Number(new URLSearchParams(location.search).get("id_proyecto"))).catch(error => { raiz.textContent = error.message || "No fue posible consultar el reporte."; raiz.setAttribute("role", "alert"); });
});
