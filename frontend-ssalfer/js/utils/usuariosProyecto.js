(() => {
    const nombre=u=>[u.nombre,u.apellido_paterno,u.apellido_materno].filter(Boolean).join(" ")||u.correo;
    let consulta;
    const listar=()=>consulta ||= (async()=>{const rows=[];for(let skip=0;;skip+=50){const lote=await window.UsuariosAPI.listar({skip,limit:50,estado:"todos"});rows.push(...lote);if(lote.length<50)return rows;}})().catch(e=>{consulta=null;throw e;});
    async function asignarPendientes(pid,seleccion,salida){
        const g=window.SSALFER_GESTION,usuarios=await listar(),resultados=[];
        const existentes=await window.ProyectosAPI.listarUsuarios(pid);
        for(const id of seleccion){try{if(!existentes.some(r=>r.id_usuario===id))await window.ProyectosAPI.agregarUsuario(pid,{id_usuario:id});resultados.push({id,ok:true});}catch(error){resultados.push({id,ok:false,error:error.message});}}
        salida.innerHTML=g.tabla([{titulo:"Usuario",valor:r=>nombre(usuarios.find(u=>u.id_usuario===r.id)||{})},{titulo:"Resultado",valor:r=>r.ok?"Asignado":r.error}],resultados,null);
        return resultados.filter(r=>!r.ok).map(r=>r.id);
    }
    window.SSALFER_USUARIOS_PROYECTO={nombre,listar,asignarPendientes};
    document.addEventListener("DOMContentLoaded",async()=>{
        const pagina=location.pathname.split('/').pop(),g=window.SSALFER_GESTION;
        if(!['nuevoProyecto.html','fichaProyecto.html'].includes(pagina))return;
        try{const sesion=await window.AuthAPI.requerirSesion();if(sesion?.user?.rol!=='admin')return;
            if(pagina==='nuevoProyecto.html'){
                const usuarios=await listar(),form=document.getElementById('formNuevoProyecto'),label=document.createElement('label');label.className='ssalfer-gestion-campo';
                label.innerHTML=`Usuarios responsables (opcional)<select id="usuariosNuevoProyecto" multiple size="5">${usuarios.filter(u=>u.activo!==false).map(u=>`<option value="${u.id_usuario}">${g.e(nombre(u))} · ${g.e(u.correo)}</option>`).join('')}</select><small>Selecciona uno o varios usuarios. Se asignarán después de crear el proyecto.</small>`;form.insertBefore(label,form.querySelector(".acciones-formulario"));
            }else{
                const id=Number(new URLSearchParams(location.search).get('id'));if(!id)return;
                const s=document.createElement('section');s.className='ssalfer-gestion-seccion';s.innerHTML=`<h2>Administrar proyecto</h2><p>Completar un proyecto requiere una función que aún no está disponible. La fecha de fin no cambia su estado.</p>${g.boton('Dar de baja proyecto','baja-proyecto')}`;document.querySelector('main').appendChild(s);
                s.querySelector('button').onclick=async event=>{const b=event.currentTarget;b.disabled=true;try{if(await g.baja('este proyecto. Dejará de aparecer en las listas activas y sus núcleos y asignaciones no darán acceso operativo al proyecto; el historial se conserva',motivo=>window.ProyectosAPI.eliminar(id,motivo)))location.href='/dashboard.html';}finally{b.disabled=false;}};
            }
        }catch(error){window.ClienteAPI.mostrarErrorAPI(error);}
    });
})();
