(() => {
    "use strict";
    const colecciones = new Map();
    let secuencia = 0;

    async function cargar(objetivos) {
        const unicos = new Map(objetivos.filter(([, id]) => Number(id) > 0)
            .map(([tipo, id]) => [`${tipo}:${id}`, [tipo, id]]));
        const resultados = await Promise.allSettled([...unicos.values()]
            .map(([tipo, id]) => window.DocumentosAPI.listarPorEntidad(tipo, id)));
        const documentos = new Map();
        resultados.forEach(resultado => {
            if (resultado.status !== "fulfilled") return;
            for (const documento of resultado.value || []) {
                documentos.set(Number(documento.id_documento), documento);
            }
        });
        if (resultados.some(resultado => resultado.status === "rejected")) {
            window.SSALFER_UI.toast("No se pudieron cargar todos los documentos. Vuelve a abrir la ficha para reintentar.", { tipo: "error" });
        }
        colecciones.set(++secuencia, { documentos, objetivos: [...unicos.values()] });
        const nucleo = [...unicos.values()].find(([tipo]) => tipo === "proyecto_nucleo");
        if (nucleo) window.dispatchEvent(new CustomEvent("ssalfer:contexto-documentos", { detail: { idProyectoNucleo: Number(nucleo[1]) } }));
        return documentos;
    }

    function nombre(documentos, id) {
        if (!id) return "Sin documento asociado";
        const documento = documentos.get(Number(id));
        return documento?.titulo || documento?.tipo_documento || "Documento asociado no disponible en el listado";
    }

    function opciones(documentos, actual = null) {
        const escape = window.SSALFER_UI.escaparHTML;
        const clave = [...colecciones].find(([, c]) => c.documentos === documentos)?.[0] || "";
        let html = `<option value="" data-documentos-coleccion="${clave}">Sin documento asociado</option>`;
        const ids = [...documentos.keys()];
        if (Number(actual) > 0 && !documentos.has(Number(actual))) ids.push(Number(actual));
        for (const id of ids) {
            html += `<option value="${id}"${Number(actual) === id ? " selected" : ""}>${escape(nombre(documentos, id))}</option>`;
        }
        return html;
    }

    async function refrescar(tipo, id) {
        const resultado = await window.DocumentosAPI.listarPorEntidad(tipo, id);
        for (const [clave, coleccion] of colecciones) {
            if (!coleccion.objetivos.some(([t, i]) => t === tipo && Number(i) === Number(id))) continue;
            resultado.forEach(d => coleccion.documentos.set(Number(d.id_documento), d));
            document.querySelectorAll(`option[data-documentos-coleccion="${clave}"]`).forEach(opcion => {
                const select = opcion.parentElement, actual = select.value;
                select.innerHTML = opciones(coleccion.documentos, actual);
            });
        }
    }
    window.SSALFER_DOCUMENTOS = Object.freeze({ cargar, nombre, opciones, refrescar });
})();
