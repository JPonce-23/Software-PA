/* Referencias legibles del núcleo. Las consultas fallidas no quedan en caché. */
(() => {
    "use strict";
    const nombres = { actividad_campo:"Actividades de campo", proyecto_nucleo: "Núcleo en el proyecto", nucleo_agrario: "Núcleo agrario", afectacion: "Afectaciones", parcela: "Parcelas", unidad_agraria: "Unidades agrarias", asamblea: "Asambleas", tramite_ran: "Trámites RAN", tramite_fifonafe: "Trámites FIFONAFE", orv: "Órganos de representación", padron_historial: "Padrones", parcela_titular: "Titulares de parcela", unidad_agraria_titular: "Titulares de unidad", asamblea_convocatoria: "Convocatorias", convenio: "Convenios", convenio_compareciente: "Comparecientes", tramite_ran_evento: "Eventos RAN", tramite_fifonafe_evento: "Eventos FIFONAFE", tramite_fifonafe_interviniente: "Intervinientes FIFONAFE", indemnizacion: "Indemnizaciones", pago: "Pagos", afectacion_unidad_agraria: "Destinos de afectación", expediente_requisito: "Requisitos documentales" };
    const directos = { actividad_campo:["ActividadesAPI","id_actividad"],
        afectacion: ["AfectacionesAPI", "id_afectacion"], parcela: ["ParcelasAPI", "id_parcela"], unidad_agraria: ["UnidadesAgrariasAPI", "id_unidad_agraria"], asamblea: ["AsambleasAPI", "id_asamblea"], tramite_ran: ["TramitesRanAPI", "id_tramite_ran"], tramite_fifonafe: ["FifonafeAPI", "id_tramite_fifonafe"], orv: ["OrvAPI", "id_orv"], padron_historial: ["PadronesAPI", "id_padron"], expediente_requisito: ["DocumentosAPI", "id_expediente_requisito", "listarRequisitosPorProyectoNucleo"]
    };
    const hijos = {
        parcela_titular: ["parcela", "ParcelasAPI", "listarTitulares", "id_parcela_titular"], unidad_agraria_titular: ["unidad_agraria", "UnidadesAgrariasAPI", "listarTitulares", "id_unidad_titular"], asamblea_convocatoria: ["asamblea", "AsambleasAPI", "listarConvocatorias", "id_convocatoria"], convenio: ["afectacion", "ConveniosAPI", "listarPorAfectacion", "id_convenio"], convenio_compareciente: ["convenio", "ConveniosAPI", "listarComparecientes", "id_compareciente"], tramite_ran_evento: ["tramite_ran", "TramitesRanAPI", "listarEventos", "id_evento_ran"], tramite_fifonafe_evento: ["tramite_fifonafe", "FifonafeAPI", "listarEventos", "id_evento_fifonafe"], tramite_fifonafe_interviniente: ["tramite_fifonafe", "FifonafeAPI", "listarIntervinientes", "id_interviniente_fifonafe"], indemnizacion: ["afectacion", "IndemnizacionAPI", "listarPorAfectacion", "id_indemnizacion"], pago: ["indemnizacion", "IndemnizacionAPI", "listarPagos", "id_pago"], afectacion_unidad_agraria: ["afectacion", "UnidadesAgrariasAPI", "listarPorAfectacion", "id_afectacion_unidad"]
    };
    const nombrePersona = p => [p.nombre, p.apellido_paterno, p.apellido_materno].filter(Boolean).join(" ");
    const personas = new Map();
    function persona(id) {
        if (!personas.has(Number(id))) personas.set(Number(id), window.PersonasAPI.obtener(id).catch(error => { personas.delete(Number(id)); throw error; }));
        return personas.get(Number(id));
    }
    function crear(idNucleo) {
        const cache = new Map();
        const fecha = valor => valor ? window.SSALFER_FORMAT.formatearFecha(valor) : "";
        const texto = partes => partes.filter(v => v !== null && v !== undefined && v !== "").join(" · ");
        async function etiqueta(tipo, item) {
            if (tipo === "actividad_campo") return texto([window.SSALFER_FORMAT.etiquetaCodigo(item.tipo_actividad),fecha(item.fecha_realizada||item.fecha_programada),item.resultado,item.observaciones]);
            if (tipo === "afectacion") return texto([window.SSALFER_FORMAT.etiquetaCodigo(item.tipo_afectacion), item.superficie_afectada_ha == null ? "" : `${Number(item.superficie_afectada_ha).toLocaleString("es-MX")} ha`, item.situacion]);
            if (tipo === "convenio") return texto([window.SSALFER_FORMAT.etiquetaCodigo(item.tipo_convenio), `Consecutivo ${item.consecutivo}`, fecha(item.fecha_firma)]);
            if (item.id_persona) return texto([nombrePersona(await persona(item.id_persona)), item.rol, item.tipo_derecho]);
            if (item.id_parcela_titular) return (await listar("parcela_titular")).find(p => p.id === Number(item.id_parcela_titular))?.etiqueta || "Titular de parcela";
            return texto([item.nombre_nucleo || item.no_parcela || item.referencia_alfanumerica || item.referencia_normalizada || item.proposito || item.referencia_expediente || item.beneficiario_nombre || item.nombre_requisito || item.numero_orv || nombres[tipo], item.ordinal ? `Evento ${item.ordinal}` : "", item.numero_folio || item.numero_oficio || item.folio_referencia, fecha(item.fecha_pago || item.fecha_padron || item.fecha_evento || item.fecha_realizacion || item.fecha_programada)]);
        }
        async function listar(tipo) {
            if (cache.has(tipo)) return cache.get(tipo);
            const consulta = (async () => {
                if (["proyecto_nucleo", "nucleo_agrario"].includes(tipo)) {
                    const item = await window.NucleosAPI.obtenerProyectoNucleo(idNucleo);
                    return [{ id: Number(tipo === "proyecto_nucleo" ? idNucleo : item.id_nucleo), etiqueta: item.nombre_nucleo, item }];
                }
                let registros = [];
                if (directos[tipo]) {
                    const [api, campo, metodo = "listarPorProyectoNucleo"] = directos[tipo];
                    for (const item of await window[api][metodo](idNucleo)) registros.push({ id: Number(item[campo]), etiqueta: await etiqueta(tipo, item), item });
                } else if (hijos[tipo]) {
                    const [padreTipo, api, metodo, campo] = hijos[tipo];
                    for (const padre of await listar(padreTipo)) {
                        const respuesta = await window[api][metodo](padre.id);
                        for (const item of Array.isArray(respuesta) ? respuesta : respuesta ? [respuesta] : []) registros.push({ id: Number(item[campo]), etiqueta: texto([padre.etiqueta, await etiqueta(tipo, item)]), item, padre });
                    }
                }
                return [...new Map(registros.map(r => [r.id, r])).values()];
            })().catch(error => { cache.delete(tipo); throw error; });
            cache.set(tipo, consulta);
            return consulta;
        }
        return { listar, limpiar: () => cache.clear(), idProyectoNucleo: Number(idNucleo) };
    }
    window.SSALFER_CONTEXTO = Object.freeze({ crear, nombres, persona, nombrePersona, invalidarPersona: id => personas.delete(Number(id)) });
})();
