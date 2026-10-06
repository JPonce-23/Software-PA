document.addEventListener("DOMContentLoaded", async () => {
    "use strict";
    const sesion = await window.AuthAPI.requerirSesion();
    if (sesion?.user?.rol !== "admin") return;
    const g = window.SSALFER_GESTION, seccion = document.createElement("section"); seccion.className = "ssalfer-gestion-seccion"; seccion.id = "asignacionesProyecto";
    document.querySelector("main").appendChild(seccion);
    let revision = 0, usuarios = [], asignados = [], ocupado = false;
    const nombre = u => [u.nombre, u.apellido_paterno, u.apellido_materno].filter(Boolean).join(" ") || u.correo;
    try {
        const proyectos = [];
        for (let skip = 0; ; skip += 200) { const lote = await window.ProyectosAPI.listar({ skip, limit: 200 }); proyectos.push(...lote); if (lote.length < 200) break; }
        for (let skip = 0; ; skip += 50) { const lote = await window.UsuariosAPI.listar({ skip, limit: 50, estado: "todos" }); usuarios.push(...lote); if (lote.length < 50) break; }
        seccion.innerHTML = `<h2>Proyectos asignados</h2><p>Administra el acceso de usuarios al proyecto. Esta asignación es independiente de los responsables del núcleo.</p><label class="ssalfer-gestion-campo">Proyecto<select data-asignacion-proyecto><option value="">Selecciona un proyecto</option>${proyectos.map(p => `<option value="${p.id_proyecto}">${g.e(p.nombre_proyecto)}</option>`).join("")}</select></label><div data-asignaciones aria-live="polite"></div>`;
        const proyecto = seccion.querySelector("[data-asignacion-proyecto]"), salida = seccion.querySelector("[data-asignaciones]");
        async function cargar() {
            const actual = ++revision, pid = Number(proyecto.value); salida.replaceChildren(); asignados = []; if (!pid) return;
            try {
                const respuesta = await window.ProyectosAPI.listarUsuarios(pid); if (actual !== revision) return; asignados = respuesta;
                salida.innerHTML = `${g.boton("Asignar usuario", "asignar")}${g.tabla([{ titulo: "Usuario", valor: r => nombre(usuarios.find(u => u.id_usuario === r.id_usuario) || {}) || "Usuario sin ficha disponible" }, { titulo: "Correo", valor: r => usuarios.find(u => u.id_usuario === r.id_usuario)?.correo }, { titulo: "Estado de usuario", valor: r => usuarios.find(u => u.id_usuario === r.id_usuario)?.activo === false ? "Inactivo" : "Activo" }], asignados, r => g.boton("Revocar asignación", "revocar", r.id_usuario), "Aún no hay usuarios asignados a este proyecto.")}`;
            } catch(error) { if (actual === revision) salida.innerHTML = `<p role="alert">${g.e(error.message)}</p>${g.boton("Reintentar", "reintentar")}`; }
        }
        proyecto.addEventListener("change", cargar);
        salida.addEventListener("click", async event => {
            const b = event.target.closest("[data-gestion]"); if (!b || ocupado) return; ocupado = true; proyecto.disabled = true;
            try {
                const pid = Number(proyecto.value); let resultado;
                if (b.dataset.gestion === "asignar") resultado = await g.formulario({ titulo: `Asignar usuario a ${proyecto.selectedOptions[0].textContent}`, campos: [{ nombre: "id_usuario", etiqueta: "Usuario", requerido: true, numerico: true, opciones: usuarios.filter(u => u.activo !== false && !asignados.some(a => a.id_usuario === u.id_usuario)).map(u => ({ valor: u.id_usuario, texto: `${nombre(u)} · ${u.correo}` })) }], guardar: datos => window.ProyectosAPI.agregarUsuario(pid, datos) });
                else if (b.dataset.gestion === "revocar") resultado = await g.baja(`la asignación de ${nombre(usuarios.find(u => u.id_usuario === Number(b.dataset.registro)) || {})} a este proyecto`, motivo => window.ProyectosAPI.revocarUsuario(pid, Number(b.dataset.registro), motivo));
                if (resultado || b.dataset.gestion === "reintentar") await cargar();
            } catch(error) { window.ClienteAPI.mostrarErrorAPI(error); }
            finally { ocupado = false; proyecto.disabled = false; }
        });
    } catch(error) { seccion.textContent = error.message || "No fue posible consultar las asignaciones."; seccion.setAttribute("role", "alert"); }
});
