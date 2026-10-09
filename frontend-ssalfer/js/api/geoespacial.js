(() => {
    "use strict";
    const base = window.ClienteAPI, id = encodeURIComponent;
    const c = { get:(ruta,o)=>base.get(ruta,{carga:"#conciliacionGeoespacial",...o}), post:(ruta,d,o)=>base.post(ruta,d,{carga:"#conciliacionGeoespacial",...o}) };
    const query = p => { const q = new URLSearchParams(); Object.entries(p || {}).forEach(([k,v]) => { if (v !== "" && v != null) q.set(k,v); }); return q.size ? `?${q}` : ""; };
    const proyecto = p => `/proyectos/${id(p)}/geoespacial`;
    const imp = i => `/importaciones/${id(i)}`;
    const feature = (i,f) => `${imp(i)}/features/${id(f)}`;
    async function paginada(ruta,o){const r=await c.get(ruta,{...o,conMetadatos:true});const h=r.headers['x-total-count'];return {items:r.data,total:h!=null&&/^\d+$/.test(h)?Number(h):null};}
    const fin=(p,skip,limit)=>p.total==null?p.items.length<limit:skip+p.items.length>=p.total;
    window.GeoespacialAPI = {
        fin,
        paginaImportaciones:(p,f,o)=>paginada(`/proyectos/${id(p)}/importaciones${query(f)}`,o),
        paginaElementos:(i,f,o)=>paginada(`${imp(i)}/features${query(f)}`,o),
        paginaCiclos:(i,f,o)=>paginada(`${imp(i)}/conciliaciones${query(f)}`,o),
        paginaRevisiones:(p,f,o)=>paginada(`${proyecto(p)}/revisiones${query(f)}`,o),
        configuracion: (p,o) => c.get(`${proyecto(p)}/configuracion`,o),
        configurar: (p,d,o) => c.post(`${proyecto(p)}/configuracion`,d,{...o,metodo:"PUT"}),
        cargar: (p,t,d,o) => { if (!["ddv","nucleos","parcelas"].includes(t)) throw Error("Tipo de carga no disponible"); return c.post(`${proyecto(p)}/${t}/importaciones`,d,o); },
        importaciones: (p,f,o) => c.get(`/proyectos/${id(p)}/importaciones${query(f)}`,o),
        obtener: (i,o) => c.get(imp(i),o),
        resumen: (i,o) => c.get(`${imp(i)}/resumen`,o),
        elementos: (i,f,o) => c.get(`${imp(i)}/features${query(f)}`,o),
        candidatos: (i,f,o) => c.get(`${feature(i,f)}/candidatos`,o),
        decisiones: (i,f,o) => c.get(`${feature(i,f)}/decisiones`,o),
        decidir: (i,f,d,o) => c.post(`${feature(i,f)}/decisiones`,d,o),
        geometria: (i,f,o) => c.get(`${feature(i,f)}/geometria`,o),
        reconciliar: (i,d,o) => c.post(`${imp(i)}/reconciliar`,d,o),
        ciclos: (i,f,o) => c.get(`${imp(i)}/conciliaciones${query(f)}`,o),
        ciclo: (i,k,o) => c.get(`${imp(i)}/conciliaciones/${id(k)}`,o),
        confirmar: (i,d,o) => c.post(`${imp(i)}/confirmar`,d,o),
        revisiones: (p,f,o) => c.get(`${proyecto(p)}/revisiones${query(f)}`,o),
        revision: (r,o) => c.get(`/geoespacial/revisiones/${id(r)}`,o),
        resolver: (r,d,o) => c.post(`/geoespacial/revisiones/${id(r)}/decisiones`,d,o)
    };
})();
