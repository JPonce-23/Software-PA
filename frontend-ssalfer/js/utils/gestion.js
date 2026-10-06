(() => {
    "use strict";
    const e = valor => window.SSALFER_UI.escaparHTML(valor);
    const etiqueta = valor => window.SSALFER_FORMAT?.etiquetaCodigo(valor) || String(valor || "—");
    const opciones = valores => valores.map(valor => Array.isArray(valor) ? { valor: valor[0], texto: valor[1] } : { valor, texto: etiqueta(valor) });
    function control(c, inicial) {
        const valor = inicial[c.nombre] ?? c.valor ?? "";
        const attrs = `name="${e(c.nombre)}" ${c.requerido ? "required" : ""} ${c.soloLectura ? "disabled" : ""}`;
        let html;
        if (c.opciones) {
            const opciones = [...c.opciones];
            if (valor !== "" && valor !== null && !opciones.some(op => String(op.valor) === String(valor))) opciones.push({ valor, texto: "Valor registrado fuera del catálogo activo" });
            html = `<select ${attrs}><option value="">${c.requerido ? "Selecciona una opción" : "Sin especificar"}</option>${opciones.map(op => `<option value="${e(op.valor)}"${String(op.valor) === String(valor) ? " selected" : ""}>${e(op.texto)}</option>`).join("")}</select>`;
        } else if (c.tipo === "checkbox") html = `<input type="checkbox" ${attrs} ${valor === true ? "checked" : ""}>`;
        else if (c.tipo === "textarea") html = `<textarea ${attrs} rows="3" ${c.maximo ? `maxlength="${c.maximo}"` : ""}>${e(valor)}</textarea>`;
        else html = `<input ${attrs} type="${c.tipo || "text"}" value="${c.tipo === "file" ? "" : e(valor)}" ${c.min !== undefined ? `min="${c.min}"` : ""} ${c.max !== undefined ? `max="${c.max}"` : ""} ${c.paso ? `step="${c.paso}"` : ""} ${c.maximo ? `maxlength="${c.maximo}"` : ""}>`;
        return `<label class="ssalfer-gestion-campo"><span>${e(c.etiqueta)}${c.requerido ? " *" : ""}</span>${html}${c.ayuda ? `<small>${e(c.ayuda)}</small>` : ""}</label>`;
    }
    async function formulario({ titulo, campos, inicial = {}, editar = false, guardar, validar, preparar, introduccion = "" }) {
        let resultado = null;
        await window.SSALFER_UI.abrirModal({ titulo,
            contenido: `<form class="ssalfer-gestion-form"><p>${e(introduccion)}</p><div class="ssalfer-gestion-campos">${campos.map(c => control(c, inicial)).join("")}</div><p class="ssalfer-gestion-error" role="alert" hidden></p></form>`,
            acciones: [{ valor: false, texto: "Cancelar" }, { valor: true, texto: "Guardar", principal: true }],
            preparar: fondo => preparar?.(fondo.querySelector("form")),
            validar: async (aceptar, fondo) => {
                if (!aceptar) return true;
                const form = fondo.querySelector("form"), aviso = form.querySelector('[role="alert"]');
                if (!form.reportValidity()) return false;
                const datos = {};
                for (const c of campos) {
                    if (c.soloLectura) continue;
                    const campo = form.elements.namedItem(c.nombre);
                    let valor = c.tipo === "checkbox" ? campo.checked : c.tipo === "file" ? campo.files[0] : campo.value.trim();
                    if (valor === "") valor = null;
                    if (valor !== null && c.numerico) valor = Number(valor);
                    if (valor !== null && c.booleano) valor = valor === "true";
                    const anterior = inicial[c.nombre] ?? (c.tipo === "checkbox" ? false : null);
                    const iguales = c.numerico && valor != null && anterior != null ? Number(valor) === Number(anterior) : String(valor ?? "") === String(anterior ?? "");
                    if (!editar || !iguales) datos[c.nombre] = valor;
                }
                const error = validar?.({ ...inicial, ...datos }, form);
                aviso.textContent = error || ""; aviso.hidden = !error;
                if (error) return false;
                if (editar && !Object.keys(datos).length) { window.SSALFER_UI.toast("No hay cambios para guardar."); return true; }
                try { resultado = await guardar(datos); window.SSALFER_UI.toast("Los cambios se guardaron correctamente."); return true; }
                catch (errorGuardar) { aviso.textContent = errorGuardar.message || "No se pudo guardar. Revisa la información e intenta de nuevo."; aviso.hidden = false; return false; }
            }
        });
        return resultado;
    }
    async function baja(nombre, ejecutar) {
        const motivo = await window.SSALFER_UI.solicitarTexto(`Indica el motivo para retirar ${nombre}.`, { titulo: "Confirmar baja", minimo: 3 });
        if (!motivo) return false;
        try { await ejecutar(motivo); window.SSALFER_UI.toast("La baja quedó registrada."); return true; }
        catch (error) { window.ClienteAPI.mostrarErrorAPI(error); return false; }
    }
    async function catalogo(tipo) {
        const items = await window.CatalogosAPI.obtenerOperativo(tipo);
        return items.filter(i => i.activo !== false).map(i => ({ valor: i.id_catalogo_opcion, texto: i.nombre || i.descripcion || etiqueta(i.codigo) }));
    }
    function tabla(columnas, filas, acciones = () => "", vacio = "Aún no hay registros.") {
        if (!filas.length) return `<p class="ssalfer-gestion-ayuda">${e(vacio)}</p>`;
        return `<div class="ssalfer-gestion-tabla"><table><thead><tr>${columnas.map(c => `<th scope="col">${e(c.titulo)}</th>`).join("")}<th scope="col">Acciones</th></tr></thead><tbody>${filas.length ? filas.map(fila => `<tr>${columnas.map(c => `<td>${e(c.valor(fila) ?? "—")}</td>`).join("")}<td class="ssalfer-gestion-acciones">${acciones(fila)}</td></tr>`).join("") : `<tr><td colspan="${columnas.length + 1}">${e(vacio)}</td></tr>`}</tbody></table></div>`;
    }
    const boton = (texto, accion, id = "") => `<button type="button" class="ssalfer-modal__button" data-gestion="${e(accion)}" data-registro="${e(id)}">${e(texto)}</button>`;
    async function descargar(ruta, nombre) {
        const blob = await window.ClienteAPI.get(ruta, { tipoRespuesta: "blob" });
        const url = URL.createObjectURL(blob), a = document.createElement("a"); a.href = url; a.download = nombre; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    window.SSALFER_GESTION = Object.freeze({ formulario, baja, catalogo, opciones, tabla, boton, descargar, e });
})();
