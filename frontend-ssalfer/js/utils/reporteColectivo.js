(() => {
    "use strict";
    async function montar(raiz, proyectoInicial, nucleoInicial) {
        const { e, tabla } = window.SSALFER_GESTION, f = window.SSALFER_FORMAT;
        const filtros = [["id_proyecto", "Proyecto"], ["id_proyecto_nucleo", "Núcleo"], ["id_convenio", "Convenio"], ["id_asamblea", "Asamblea"], ["tipo_convenio", "Tipo de convenio"], ["tipo_cop_operativo", "Tipo de COP"], ["destino_superficie", "Destino de superficie"], ["anio", "Año"], ["mes", "Mes"], ["trimestre", "Trimestre"]];
        raiz.innerHTML = `<h2>Destino de la superficie colectiva</h2><p>El monto declarado corresponde al convenio completo. Se muestra una sola vez por convenio y es no aditivo entre destinos.</p><form><div class="ssalfer-gestion-campos">${filtros.map(([nombre, etiqueta]) => `<label class="ssalfer-gestion-campo">${etiqueta}<select name="${nombre}"><option value="">Todos</option></select></label>`).join("")}</div><p class="reporte-ayuda-periodo">Año, mes y trimestre salen de la fecha de firma del convenio. Para que aparezcan, registra la fecha de firma en el convenio. Enero–marzo: trimestre 1; abril–junio: 2; julio–septiembre: 3; octubre–diciembre: 4.</p><div data-enlace-fecha></div><div class="ssalfer-gestion-barra"><button class="btn-secundario" type="submit">Consultar</button><button class="btn-secundario" type="button" data-exportar disabled>Exportar CSV</button></div></form><p data-sin-fecha class="reporte-aviso-fecha" role="status" hidden>Estos convenios no tienen fecha de firma, por eso no aparecen al filtrar por año, mes o trimestre.</p><div data-resultados aria-live="polite"></div>`;
        const form = raiz.querySelector("form"), salida = raiz.querySelector("[data-resultados]"), exportar = raiz.querySelector("[data-exportar]");
        const campo = nombre => form.elements.namedItem(nombre);
        let baseReporte = [], cargandoContexto = false;
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
            const actual = ++revision; cargandoContexto = true; baseReporte = []; filas = []; exportar.disabled = true; salida.replaceChildren(); referencias = new Map();
            filtros.slice(1).map(([nombre])=>nombre).forEach(n => { llenar(n, []); campo(n).disabled = true; });
            const pid = campo("id_proyecto").value; if (!pid) { cargandoContexto=false; return; }
            try {
                const [nucleos, datos] = await Promise.all([window.NucleosAPI.listarPorProyecto(pid), window.ReportesAPI.obtenerColectivosDestino({ id_proyecto: pid })]);
                const refs = await cargarReferencias(nucleos);
                if (actual !== revision) return;
                baseReporte = datos; referencias = refs; llenar("id_proyecto_nucleo", nucleos.map(n => [n.id_proyecto_nucleo, n.nombre_nucleo]), nucleo);
                for (const nombre of ["tipo_convenio", "tipo_cop_operativo", "destino_superficie"]) llenar(nombre, [...new Set(datos.map(d => d[nombre]).filter(Boolean))].map(v => [v, f.etiquetaCodigo(v)]));
                filtros.slice(1).map(([nombre])=>nombre).forEach(n => { campo(n).disabled = false; });
                cargandoContexto=false; cambiarNucleo(); await consultar();
            } catch (error) { if (actual === revision) { cargandoContexto=false; fallo(error); } }
        }
        function actualizarOpciones() {
            const nid = Number(campo("id_proyecto_nucleo").value);
            const datos = baseReporte.filter(r => !nid || Number(r.id_proyecto_nucleo) === nid);
            const sinFecha = new Set(datos.filter(r=>!r.fecha_firma && filtros.slice(2,7).every(([n])=>!campo(n).value || String(r[n])===campo(n).value)).map(r=>r.id_convenio));
            const aviso=raiz.querySelector('[data-sin-fecha]');aviso.hidden=!sinFecha.size;
            aviso.textContent=`${sinFecha.size} convenio(s) sin fecha de firma: no aparecen al filtrar por año, mes o trimestre.`;
            const cid=campo('id_convenio').value || (sinFecha.size===1 ? [...sinFecha][0] : null);
            raiz.querySelector('[data-enlace-fecha]').innerHTML=cid?`<a href="/pages/fichaConvenio.html?id_convenio=${Number(cid)}">Consultar convenio y su fecha de firma</a>`:'';
            for (const [nombre] of filtros.slice(2)) {
                const previo = campo(nombre).value;
                const posibles = datos.filter(r => filtros.slice(2).every(([otro]) => otro === nombre || !campo(otro).value || String(r[otro]) === campo(otro).value));
                const valores = [...new Set(posibles.map(r => r[nombre]).filter(v => v != null && v !== ""))];
                valores.sort((a,b) => nombre === "anio" ? Number(b)-Number(a) : String(a).localeCompare(String(b),'es',{numeric:true}));
                llenar(nombre, valores.map(v => [v, nombre === "id_convenio" ? referencias.get('convenio:'+v)?.etiqueta || "Convenio del reporte" : nombre === "id_asamblea" ? referencias.get('asamblea:'+v)?.etiqueta || "Asamblea del reporte" : nombre === "mes" ? new Intl.DateTimeFormat('es-MX',{month:'long',timeZone:'UTC'}).format(new Date(Date.UTC(2020,Number(v)-1,1))) : nombre === "trimestre" ? 'Trimestre '+v : f.etiquetaCodigo(v)]), previo);
            }
        }
        function cambiarNucleo() {
            ++revision; filas = []; exportar.disabled = true; salida.replaceChildren();
            filtros.slice(2).forEach(([n]) => llenar(n, [])); actualizarOpciones();
        }
        async function consultar() {
            if (cargandoContexto) { salida.textContent="Espera a que se carguen los filtros del proyecto."; return; }
            if (!campo("id_proyecto").value) { salida.textContent = "Selecciona un proyecto para consultar sus destinos colectivos."; return; }
            const actual = ++revision, params = Object.fromEntries([...new FormData(form)].filter(([,valor]) => valor));
            exportar.disabled = true; salida.replaceChildren();
            try {
                const datos = await window.ReportesAPI.obtenerColectivosDestino(params);
                if (actual !== revision) return;
                const vistos = new Set();
                filas = datos.map(d => { const primero = !vistos.has(d.id_convenio); vistos.add(d.id_convenio); return { ...d, montoVisible: primero ? d.monto_declarado : null }; });
                columnas = [{ titulo: "Convenio", valor: r => referencias.get(`convenio:${r.id_convenio}`)?.etiqueta || "Convenio sin referencia disponible" }, { titulo: "Asamblea", valor: r => r.id_asamblea ? referencias.get(`asamblea:${r.id_asamblea}`)?.etiqueta || "Asamblea sin referencia disponible" : "Sin asamblea" }, { titulo: "Tipo de convenio", valor: r => f.etiquetaCodigo(r.tipo_convenio) }, { titulo: "Tipo de COP", valor: r => f.etiquetaCodigo(r.tipo_cop_operativo) }, { titulo: "Destino", valor: r => f.etiquetaCodigo(r.destino_superficie) }, { titulo: "Superficie", valor: r => numero(r.superficie_ha) }, { titulo: "Superficie declarada", valor: r => numero(r.superficie_declarada_ha) }, { titulo: "Monto del convenio (no aditivo)", valor: r => r.montoVisible == null ? "—" : Number(r.montoVisible).toLocaleString("es-MX", { style: "currency", currency: "MXN" }) }, { titulo: "Fecha de firma", valor: r => f.formatearFecha(r.fecha_firma) }];
                columnas[0].html = r => {const c=referencias.get(`convenio:${r.id_convenio}`)?.item || r;const nombre=`${f.etiquetaCodigo(c.tipo_convenio)} · consecutivo ${c.consecutivo??'sin registrar'}`;return `<span class="colectivo-texto-corto" title="${e(nombre)}">${e(nombre)}</span> <button type="button" class="btn-secundario" data-ver-convenio="${r.id_convenio}" aria-label="Ver convenio ${e(nombre)}">Ver</button>`;};
                columnas[5].csv=r=>r.superficie_ha==null?'':Number(r.superficie_ha);columnas[5].numerico=true;
                columnas[6].csv=r=>r.superficie_declarada_ha==null?'':Number(r.superficie_declarada_ha);columnas[6].numerico=true;
                columnas[7].csv=r=>r.montoVisible==null?'':Number(r.montoVisible).toFixed(2);columnas[7].numerico=true;
                for(const c of columnas.slice(1)) {if(c.numerico)continue;c.html=r=>{const completo=String(c.valor(r)??'—');return completo.length>100?`<span class="colectivo-texto-corto">${e(completo)}</span> <button type="button" class="btn-secundario" data-texto-completo="${e(completo)}">Ver</button>`:e(completo);};}
                salida.removeAttribute("role"); salida.innerHTML = window.SSALFER_PERIODOS.tabla(columnas, filas, r => `<a href="/pages/fichaConvenio.html?id_convenio=${r.id_convenio}">Consultar convenio</a>`, "fecha_firma", "la fecha de firma del convenio", "No hay destinos colectivos para esta combinación. Prueba con Todos; los convenios sin fecha de firma no aparecen al filtrar por periodo."); exportar.disabled = !filas.length;
            } catch (error) { if (actual === revision) fallo(error); }
        }
        form.addEventListener("submit", event => { event.preventDefault(); consultar(); });
        campo("id_proyecto").addEventListener("change", () => cambiarProyecto());
        campo("id_proyecto_nucleo").addEventListener("change", cambiarNucleo);
        form.addEventListener("change", event => {
            if (["id_proyecto", "id_proyecto_nucleo"].includes(event.target.name)) return;
            ++revision; exportar.disabled = true; salida.replaceChildren(); actualizarOpciones();
        });
        exportar.addEventListener("click", () => {
            const celda = (valor,numerico=false) => { let texto = String(valor ?? ""); if (!numerico && /^[\s]*[=+@-]/.test(texto)) texto = `'${texto}`; return `"${texto.replaceAll('"', '""')}"`; };
            const titulos=columnas.map(c=>c.titulo);titulos[5]='Superficie (ha)';titulos[6]='Superficie declarada (ha)';titulos[7]='Monto del convenio (MXN, no aditivo)';
            const csv = [titulos.map(v=>celda(v)).join(','), ...filas.map(r=>columnas.map(c=>celda((c.csv||c.valor)(r),c.numerico)).join(','))].join('\r\n');
            const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" })); const a = document.createElement("a"); a.href = url; a.download = "destinos-colectivos.csv"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        salida.addEventListener('click',event=>{
            const b=event.target.closest('[data-ver-convenio],[data-texto-completo]');if(!b)return;
            if(b.dataset.textoCompleto){window.SSALFER_UI.abrirModal({titulo:'Texto completo',contenido:`<p>${e(b.dataset.textoCompleto)}</p>`,acciones:[{texto:'Cerrar',valor:true}]});return;}
            const id=Number(b.dataset.verConvenio),ref=referencias.get(`convenio:${id}`),c=ref?.item||filas.find(r=>r.id_convenio===id)||{};
            window.SSALFER_UI.abrirModal({titulo:'Detalle del convenio',contenido:`<p>${e(ref?.etiqueta||'Convenio del reporte')}</p><dl><dt>Tipo</dt><dd>${e(f.etiquetaCodigo(c.tipo_convenio))}</dd><dt>Consecutivo</dt><dd>${e(c.consecutivo??'Sin registrar')}</dd><dt>Descripción</dt><dd>${e(c.descripcion_instrumento||c.descripcion||'Sin descripción')}</dd><dt>Ámbito</dt><dd>${e(f.etiquetaCodigo(c.ambito))}</dd><dt>Fecha de firma</dt><dd>${e(f.formatearFecha(c.fecha_firma))}</dd></dl>`,acciones:[{texto:'Cerrar',valor:true}]});
        });
        const proyectos = await window.ProyectosAPI.listar();
        llenar("id_proyecto", proyectos.map(p => [p.id_proyecto, p.nombre_proyecto]), proyectoInicial);
        await cambiarProyecto(nucleoInicial);
    }
    window.SSALFER_REPORTE_COLECTIVO = Object.freeze({ montar });
})();
