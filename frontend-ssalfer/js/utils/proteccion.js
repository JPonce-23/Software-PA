/* Barrera de presentación. La API sigue autorizando cada operación. */
(() => {
    const estilo=document.createElement('style');estilo.id='ssalferProteccion';estilo.textContent='html{visibility:hidden!important}';document.head.append(estilo);
    let resolver;
    window.SSALFER_SESION_LISTA=new Promise(r=>resolver=r);
    window.SSALFER_PROTECCION={
        permitir(sesion){estilo.remove();resolver(sesion);},
        cerrar(){resolver(null);},
        iniciarSesion(){this.cerrar();const retorno=location.pathname+location.search;location.replace('/Index.html?return_to='+encodeURIComponent(retorno));},
        fallo(){this.cerrar();const mostrar=()=>{document.body.replaceChildren();const p=document.createElement('p');p.textContent='No se pudo comprobar tu sesión. Vuelve a intentar para entrar al sistema.';const b=document.createElement('button');b.textContent='Reintentar';b.onclick=()=>location.reload();document.body.append(p,b);estilo.remove();};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mostrar,{once:true});else mostrar();}
    };
    window.addEventListener('pageshow',e=>{if(e.persisted)location.reload();});
})();
