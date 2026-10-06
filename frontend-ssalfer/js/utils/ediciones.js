(() => {
    "use strict";
    const c = (nombre, etiqueta, extra = {}) => ({ nombre, etiqueta, ...extra });
    const numero = (nombre, etiqueta, extra = {}) => c(nombre, etiqueta, { tipo: "number", numerico: true, paso: "any", ...extra });
    const fecha = (nombre, etiqueta) => c(nombre, etiqueta, { tipo: "date" });
    const obs = () => c("observaciones", "Observaciones", { tipo: "textarea" });
    const editar = (titulo, item, campos, guardar, extra = {}) => window.SSALFER_GESTION.formulario({ titulo, inicial: item, editar: true, campos, guardar, ...extra });
    async function pago(item, idNucleo) {
        const directorio = await window.SSALFER_DIRECTORIO.listar(idNucleo);
        if (item.id_persona_beneficiaria && !directorio.personas.some(p => p.id_persona === item.id_persona_beneficiaria)) directorio.personas.push(await window.SSALFER_CONTEXTO.persona(item.id_persona_beneficiaria));
        return editar("Editar pago", item, [fecha("fecha_pago", "Fecha de pago"), numero("monto", "Monto pagado", { requerido: true, min: 0.01 }), c("beneficiario_nombre", "Nombre del beneficiario", { requerido: true, maximo: 300 }), c("id_persona_beneficiaria", "Persona beneficiaria", { numerico: true, opciones: directorio.personas.map(p => ({ valor: p.id_persona, texto: window.SSALFER_CONTEXTO.nombrePersona(p) })) }), c("medio_pago", "Medio de pago", { opciones: window.SSALFER_GESTION.opciones(["transferencia", "cheque", "efectivo", "deposito", "otro"]) }), c("referencia", "Referencia", { maximo: 150 }), obs()], datos => window.IndemnizacionAPI.actualizarPago(item.id_pago, datos), { preparar: form => { form.elements.fecha_pago.required = true; } });
    }
    function parcela(item) {
        return editar("Editar titular de parcela", item, [c("tipo_derecho", "Tipo de derecho", { maximo: 50 }), numero("porcentaje_participacion", "Participación (%)", { min: 0.000001, max: 100 }), fecha("fecha_inicio", "Inicio"), fecha("fecha_fin", "Fin"), obs()], datos => window.ParcelasAPI.actualizarTitular(item.id_parcela_titular, datos), { validar: d => d.fecha_inicio && d.fecha_fin && d.fecha_fin < d.fecha_inicio ? "La fecha de fin no puede ser anterior al inicio." : null });
    }
    async function unidad(item, unidad, idNucleo) {
        const g = window.SSALFER_GESTION;
        const directorio = await window.SSALFER_DIRECTORIO.listar(idNucleo);
        const titulares = unidad.id_parcela ? await window.ParcelasAPI.listarTitulares(unidad.id_parcela) : [];
        const opciones = [];
        for (const t of titulares) { const p = await window.SSALFER_CONTEXTO.persona(t.id_persona); opciones.push({ valor: t.id_parcela_titular, texto: `${window.SSALFER_CONTEXTO.nombrePersona(p)} · ${t.tipo_derecho || "Titular de parcela"}` }); }
        const campos = [c("id_persona", "Persona del núcleo", { numerico: true, opciones: directorio.personas.map(p => ({ valor: p.id_persona, texto: window.SSALFER_CONTEXTO.nombrePersona(p) })) }), c("id_parcela_titular", "Titular de la parcela asociada", { numerico: true, opciones }), numero("porcentaje_participacion", "Participación (%)", { min: 0, max: 100 }), c("es_principal", "Titular principal", { tipo: "checkbox" }), obs()];
        return g.formulario({ titulo: item ? "Editar titular de unidad" : "Agregar titular de unidad", inicial: item || {}, editar: Boolean(item), campos, validar: d => Boolean(d.id_persona) === Boolean(d.id_parcela_titular) ? "Elige una persona o un titular de parcela." : null, preparar: form => {
            form.elements.id_persona.addEventListener("change", () => { if (form.elements.id_persona.value) form.elements.id_parcela_titular.value = ""; });
            form.elements.id_parcela_titular.addEventListener("change", () => { if (form.elements.id_parcela_titular.value) form.elements.id_persona.value = ""; });
            const b = document.createElement("button"); b.type = "button"; b.className = "btn-secundario"; b.textContent = "Registrar persona nueva"; form.elements.id_persona.after(b);
            b.addEventListener("click", async () => { b.disabled = true; try { const p = await window.SSALFER_DIRECTORIO.registrar(idNucleo); if (p) { form.elements.id_persona.add(new Option(window.SSALFER_CONTEXTO.nombrePersona(p), p.id_persona)); form.elements.id_persona.value = p.id_persona; form.elements.id_parcela_titular.value = ""; } } catch(error) { window.ClienteAPI.mostrarErrorAPI(error); } finally { b.disabled = false; } });
        }, guardar: datos => item ? window.UnidadesAgrariasAPI.actualizarTitular(item.id_unidad_titular, datos) : window.UnidadesAgrariasAPI.agregarTitular(unidad.id_unidad_agraria, datos) });
    }
    async function compareciente(item) {
        const g = window.SSALFER_GESTION;
        const [calidades, acreditaciones] = await Promise.all([g.catalogo("calidad_compareciente_convenio"), g.catalogo("tipo_acreditacion_derecho_individual")]);
        return editar("Editar compareciente", item, [c("id_tipo_calidad", "Calidad", { opciones: calidades, numerico: true, requerido: true }), c("id_tipo_acreditacion", "Acreditación", { opciones: acreditaciones, numerico: true }), c("referencia_acreditacion", "Referencia de acreditación", { maximo: 200 }), fecha("fecha_acreditacion", "Fecha de acreditación"), c("nombre_en_instrumento", "Nombre en el instrumento", { maximo: 300 }), c("es_firmante", "Es firmante", { tipo: "checkbox" }), c("es_beneficiario_pago", "Es beneficiario del pago", { tipo: "checkbox" }), c("requiere_revision", "Requiere revisión", { tipo: "checkbox" }), c("motivo_revision", "Motivo de revisión", { tipo: "textarea" }), obs()], datos => window.ConveniosAPI.actualizarCompareciente(item.id_compareciente, datos));
    }
    function afectacionConvenio(item) {
        return editar("Editar afectación del convenio", item, [c("efecto_superficie", "Efecto sobre la superficie", { requerido: true, opciones: window.SSALFER_GESTION.opciones(["adicion", "sustitucion", "correccion", "sin_cambio", "pendiente"]) }), numero("superficie_impacto_ha", "Superficie de impacto (ha)"), obs()], datos => window.ConveniosAPI.actualizarAfectacionAdicional(item.id_convenio_afectacion, { ...datos, ...(datos.efecto_superficie ? { superficie_impacto_ha: datos.superficie_impacto_ha === undefined ? item.superficie_impacto_ha : datos.superficie_impacto_ha } : {}) }), { validar: d => d.efecto_superficie === "pendiente" && d.superficie_impacto_ha != null ? "Deja la superficie vacía mientras el efecto esté pendiente." : d.efecto_superficie === "sin_cambio" && (d.superficie_impacto_ha == null || Number(d.superficie_impacto_ha) !== 0) ? "Sin cambio requiere superficie cero." : d.efecto_superficie === "adicion" && !(Number(d.superficie_impacto_ha) > 0) ? "La adición requiere superficie mayor que cero." : ["sustitucion", "correccion"].includes(d.efecto_superficie) && d.superficie_impacto_ha == null ? "Indica la superficie de impacto." : null });
    }
    function ran(item) { return editar("Editar fecha programada de ingreso RAN", item, [fecha("fecha_programada_ingreso", "Fecha programada de ingreso")], datos => window.TramitesRanAPI.actualizar(item.id_tramite_ran, datos)); }
    window.SSALFER_EDICIONES = Object.freeze({ pago, parcela, unidad, compareciente, afectacionConvenio, ran });
})();
