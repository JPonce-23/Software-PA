/**
 * proyectos.js — /proyectos, /proyectos/{id}, /proyectos/{id}/usuarios, /proyectos/{id}/trazos
 * (No incluye /proyectos/{id}/mapa: excluido de esta ronda por falta de
 * autorización de mapas, ver docs del proyecto.)
 */

(function () {

    const { get, post, patch, del } = window.ClienteAPI;

    function ordenar(items) {
        return [...items].sort((a,b) => {
            const fa=Date.parse(a.creado_en), fb=Date.parse(b.creado_en);
            return ((Number.isFinite(fb)?fb:0)-(Number.isFinite(fa)?fa:0)) || Number(b.id_proyecto)-Number(a.id_proyecto);
        });
    }
    async function listar(params = {}) {
        if (params.skip !== undefined || params.limit !== undefined) {
            return get(`/proyectos?${new URLSearchParams(params)}`);
        }
        const todos=[];
        for(let skip=0;;skip+=200){
            const lote=await get(`/proyectos?${new URLSearchParams({...params,skip,limit:200})}`);
            todos.push(...lote); if(lote.length<200)return ordenar(todos);
        }
    }

    function obtener(idProyecto) {
        return get(`/proyectos/${idProyecto}`);
    }

    function crear(payload) {
        return post("/proyectos", payload);
    }

    function actualizar(idProyecto, payload) {
        return patch(`/proyectos/${idProyecto}`, payload);
    }

    function eliminar(idProyecto, motivo) {
        return del(`/proyectos/${idProyecto}`, { motivo });
    }

    function listarUsuarios(idProyecto) {
        return get(`/proyectos/${idProyecto}/usuarios`);
    }

    function agregarUsuario(idProyecto, payload) {
        return post(`/proyectos/${idProyecto}/usuarios`, payload);
    }

    function listarTrazos(idProyecto) {
        return get(`/proyectos/${idProyecto}/trazos`);
    }

    function crearTrazo(idProyecto, payload) {
        return post(`/proyectos/${idProyecto}/trazos`, payload);
    }

    window.ProyectosAPI = {
        revocarUsuario: (idProyecto, idUsuario, motivo) => del(`/proyectos/${idProyecto}/usuarios/${idUsuario}`, { motivo }),
        listar, ordenar,
        obtener,
        crear,
        actualizar,
        eliminar,
        listarUsuarios,
        agregarUsuario,
        listarTrazos,
        crearTrazo
    };

})();
