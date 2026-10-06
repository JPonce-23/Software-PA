(() => {
    "use strict";
    async function montar(raiz, proyectoInicial, nucleoInicial) {
        const { e, tabla } = window.SSALFER_GESTION, f = window.SSALFER_FORMAT;
        const filtros = [["id_proyecto", "Proyecto"], ["id_proyecto_nucleo", "Núcleo"], ["id_convenio", "Convenio"], ["id_asamblea", "Asamblea"], ["tipo_convenio", "Tipo de convenio"], ["tipo_cop_operativo", "Tipo de COP"], ["destino_superficie", "Destino de superficie"], ["anio", "Año"], ["mes", "Mes"], ["trimestre", "Trimestre"]];
        raiz.innerHTML = `<h2>Destino de la superficie colectiva</h2><p>El monto declarado corresponde al convenio completo. Se muestra una sola vez por convenio y es no aditivo entre destinos.</p><form><div class="ssalfer-gestion-campos">${filtros.map(([nombre, etiqueta]) => `<label class="ssalfer-gestion-campo">${etiqueta}<select name="${nombre}"><option value="">Todos</option></select></label>`).join("")}</div><div class="ssalfer-gestion-barra"><button class="btn-secundario" type="submit">Consultar</button><button class="btn-secundario" type="button" data-exportar disabled>Exportar CSV</button></div></form><div data-resultados aria-live="polite"></div>`;
        const form = raiz.querySelector("form"), salida = raiz.querySelector("[data-resultados]"), exportar = raiz.querySelector("[data-exportar]");
        const campo = nombre => form.elements.namedItem(nombre);
        let revision = 0, filas = [], referencias = new Map(), columnas = [];
        const llenar = (nombre, lista, seleccionado = "") => { const select = campo(nombre); select.replaceChildren(new Option("Todos", "")); lista.forEach(([id, texto]) => select.add(new Option(texto, id))); select.value = String(seleccionado || ""); };
        const numero = v => v == null ? "—" : `${Number(v).toLocaleString("es-MX", { maximumFractionDigits: 6 })} ha`;
        const fallo = error => { salida.textContent = error.message || "No fue posible consultar el reporte. Vuelve a consultar para reintentar."; salida.setAttribute("role", "alert"); exportar.disabled = true; };
        async function cargarReferencias(nucleos) {
            const mapa = new Map();
            for (const n of nucleos) {
                const contexto = window.SSALFER_CONTEXTO.crear(n.id_proyecto_nucleo);
                const [convenios, asambleas] = await Promise.all([contexto.listar("convenio"), contexto.listar("asamblea")]);
                convenios.filter(c => c.item.ambito === "colectivo" || c.padre?.item.tipo_afectacion === "colectivo").forEach(c => mapa.set(`convenio:${c.id}`, { ...c, etiqueta: `${n.nombre_nucleo} · ${c.etiqueta}` }));
                asambleas.forEach(a => mapa.set(`asamblea:${a.id}`, { ...a, etiqueta: `${n.nombre_nucleo} · ${a.etiqueta}` }));
            }
            return mapa;
        }
        async function cambiarProyecto(nucleo = "") {
            const actual = ++revision; filas = []; exportar.disabled = true; salida.replaceChildren(); referencias = new Map();
            ["id_proyecto_nucleo", "id_convenio", "id_asamblea", "tipo_convenio", "tipo_cop_operativo", "destino_superficie"].forEach(n => { llenar(n, []); campo(n).disabled = true; });
            const pid = campo("id_proyecto").value; if (!pid) return;
            try {
                const [nucleos, datos] = await Promise.all([window.NucleosAPI.listarPorProyecto(pid), window.ReportesAPI.obtenerColectivosDestino({ id_proyecto: pid })]);
                const refs = await cargarReferencias(nucleos);
                if (actual !== revision) return;
                referencias = refs; llenar("id_proyecto_nucleo", nucleos.map(n => [n.id_proyecto_nucleo, n.nombre_nucleo]), nucleo);
                for (const nombre of ["tipo_convenio", "tipo_cop_operativo", "destino_superficie"]) llenar(nombre, [...new Set(datos.map(d => d[nombre]).filter(Boolean))].map(v => [v, f.etiquetaCodigo(v)]));
                ["id_proyecto_nucleo", "id_convenio", "id_asamblea", "tipo_convenio", "tipo_cop_operativo", "destino_superficie"].forEach(n => { campo(n).disabled = false; });
                cambiarNucleo(); await consultar();
            } catch (error) { if (actual === revision) fallo(error); }
        }
        function cambiarNucleo() {
            ++revision; filas = []; exportar.disabled = true; salida.replaceChildren();
            const nid = Number(campo("id_proyecto_nucleo").value);
            for (const tipo of ["convenio", "asamblea"]) llenar(`id_${tipo}`, [...referencias].filter(([clave, r]) => clave.startsWith(`${tipo}:`) && (!nid || Number(r.item.id_proyecto_nucleo || r.padre?.item.id_proyecto_nucleo) === nid)).map(([,r]) => [r.id, r.etiqueta]));
        }
        async function consultar() {
            if (!campo("id_proyecto").value) { salida.textContent = "Selecciona un proyecto para consultar sus destinos colectivos."; return; }
            const actual = ++revision, params = Object.fromEntries([...new FormData(form)].filter(([,valor]) => valor));
            exportar.disabled = true; salida.replaceChildren();
            try {
                const datos = await window.ReportesAPI.obtenerColectivosDestino(params);
                if (actual !== revision) return;
                const vistos = new Set();
                filas = datos.map(d => { const primero = !vistos.has(d.id_convenio); vistos.add(d.id_convenio); return { ...d, montoVisible: primero ? d.monto_declarado : null }; });
                columnas = [{ titulo: "Convenio", valor: r => referencias.get(`convenio:${r.id_convenio}`)?.etiqueta || "Convenio sin referencia disponible" }, { titulo: "Asamblea", valor: r => r.id_asamblea ? referencias.get(`asamblea:${r.id_asamblea}`)?.etiqueta || "Asamblea sin referencia disponible" : "Sin asamblea" }, { titulo: "Tipo de convenio", valor: r => f.etiquetaCodigo(r.tipo_convenio) }, { titulo: "Tipo de COP", valor: r => f.etiquetaCodigo(r.tipo_cop_operativo) }, { titulo: "Destino", valor: r => f.etiquetaCodigo(r.destino_superficie) }, { titulo: "Superficie", valor: r => numero(r.superficie_ha) }, { titulo: "Superficie declarada", valor: r => numero(r.superficie_declarada_ha) }, { titulo: "Monto del convenio (no aditivo)", valor: r => r.montoVisible == null ? "—" : Number(r.montoVisible).toLocaleString("es-MX", { style: "currency", currency: "MXN" }) }, { titulo: "Fecha de firma", valor: r => f.formatearFecha(r.fecha_firma) }];
                salida.removeAttribute("role"); salida.innerHTML = tabla(columnas, filas, r => `<a href="/pages/fichaConvenio.html?id_convenio=${r.id_convenio}">Consultar convenio</a>`, "No hay destinos colectivos para los filtros seleccionados."); exportar.disabled = !filas.length;
            } catch (error) { if (actual === revision) fallo(error); }
        }
        form.addEventListener("submit", event => { event.preventDefault(); consultar(); });
        campo("id_proyecto").addEventListener("change", () => cambiarProyecto());
        campo("id_proyecto_nucleo").addEventListener("change", cambiarNucleo);
        form.addEventListener("change", event => {
            if (["id_proyecto", "id_proyecto_nucleo"].includes(event.target.name)) return;
            ++revision; exportar.disabled = true; salida.replaceChildren();
        });
        exportar.addEventListener("click", () => {
            const celda = valor => { let texto = String(valor ?? ""); if (/^[\s]*[=+@-]/.test(texto)) texto = `'${texto}`; return `"${texto.replaceAll('"', '""')}"`; };
            const csv = [columnas.map(c => c.titulo), ...filas.map(r => columnas.map(c => c.valor(r)))].map(fila => fila.map(celda).join(",")).join("\r\n");
            const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" })); const a = document.createElement("a"); a.href = url; a.download = "destinos-colectivos.csv"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        const proyectos = await window.ProyectosAPI.listar();
        llenar("id_proyecto", proyectos.map(p => [p.id_proyecto, p.nombre_proyecto]), proyectoInicial);
        llenar("anio", Array.from({ length: 201 }, (_,i) => [2000+i, String(2000+i)]));
        llenar("mes", Array.from({ length: 12 }, (_,i) => [i+1, new Intl.DateTimeFormat("es-MX", { month: "long", timeZone: "UTC" }).format(new Date(Date.UTC(2020,i,1)))]));
        llenar("trimestre", [1,2,3,4].map(i => [i, `Trimestre ${i}`]));
        await cambiarProyecto(nucleoInicial);
    }
    window.SSALFER_REPORTE_COLECTIVO = Object.freeze({ montar });
})();
