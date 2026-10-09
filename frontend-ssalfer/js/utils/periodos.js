(() => {
    const periodo=fecha=>{const m=/^(\d{4})-(\d{2})-\d{2}/.exec(fecha||'');return m?{anio:Number(m[1]),mes:Number(m[2]),trimestre:Math.ceil(Number(m[2])/3),clave:`${m[1]}-${Math.ceil(Number(m[2])/3)}`}:{clave:'',anio:'',mes:'',trimestre:''};};
    function tabla(columnas,filas,acciones,campoFecha,baseFecha,vacio){
        const g=window.SSALFER_GESTION,grupos=new Map();for(const fila of filas){const p=periodo(fila[campoFecha]);if(!grupos.has(p.clave))grupos.set(p.clave,[]);grupos.get(p.clave).push(fila);}
        if(!filas.length)return g.tabla(columnas,[],acciones,vacio);
        return `<p class="ssalfer-gestion-ayuda">Periodo según ${g.e(baseFecha)}.</p>`+[...grupos].sort(([a],[b])=>b.localeCompare(a)).map(([clave,rows])=>{
            rows.sort((a,b)=>String(b[campoFecha]||'').localeCompare(String(a[campoFecha]||'')));
            const p=periodo(rows[0][campoFecha]);return `<section><h4>${clave?`${p.anio} · Trimestre ${p.trimestre}`:'Sin fecha registrada'}</h4>${g.tabla([...columnas,{titulo:'Mes',valor:r=>{const p=periodo(r[campoFecha]);return p.mes?new Intl.DateTimeFormat('es-MX',{month:'long',timeZone:'UTC'}).format(new Date(Date.UTC(p.anio,p.mes-1,1))):'Sin fecha';}},{titulo:'Trimestre',valor:r=>periodo(r[campoFecha]).trimestre||'Sin fecha'},{titulo:'Año',valor:r=>periodo(r[campoFecha]).anio||'Sin fecha'}],rows,acciones)}</section>`;
        }).join('');
    }
    window.SSALFER_PERIODOS={periodo,tabla};
})();
