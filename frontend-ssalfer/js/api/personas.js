/**
 * personas.js
 *
 * Personas registradas en SSALFER.
 *
 * Backend disponible:
 *
 * POST   /proyectos/{id_proyecto}/personas
 * GET    /personas/{id_persona}
 * PATCH  /personas/{id_persona}
 * DELETE /personas/{id_persona}
 * POST   /personas/{id_persona}/reactivar
 *
 * GET /personas: búsqueda autorizada por un único criterio.
 */

(function () {

    "use strict";


    const {
        get,
        post,
        patch,
        del
    } = window.ClienteAPI;


    function crear(
        idProyecto,
        payload
    ) {

        return post(
            `/proyectos/${encodeURIComponent(
                idProyecto
            )}/personas`,
            payload
        ).catch(error=>{if(error.status===409)error.message="Ya existe una persona con esta identidad. Búscala por CURP o RFC antes de intentar registrarla nuevamente. Si no aparece, solicita revisión de acceso al administrador.";throw error;});

    }


    function obtener(
        idPersona
    ) {

        return get(
            `/personas/${encodeURIComponent(
                idPersona
            )}`
        );

    }


    function actualizar(
        idPersona,
        payload
    ) {

        return patch(
            `/personas/${encodeURIComponent(
                idPersona
            )}`,
            payload
        );

    }


    function darDeBaja(
        idPersona,
        motivo
    ) {

        return del(
            `/personas/${encodeURIComponent(
                idPersona
            )}`,
            {
                motivo
            }
        );

    }


    function reactivar(
        idPersona
    ) {

        return post(
            `/personas/${encodeURIComponent(
                idPersona
            )}/reactivar`
        );

    }


    function buscar(params={},opciones={}) {
        const criterios=['q','curp','rfc'].filter(k=>String(params[k]??'').trim());
        if(criterios.length!==1)throw Error('Elige sólo un criterio de búsqueda.');
        const k=criterios[0],v=String(params[k]).trim().replace(/\s+/g,' '),max={q:300,curp:18,rfc:13}[k];
        if(v.length>(max)||k==='q'&&v.length<2)throw Error(k==='q'?'Escribe entre 2 y 300 caracteres del nombre.':'Revisa la longitud del criterio.');
        return get(`/personas?${new URLSearchParams({[k]:v,limit:Math.min(100,Math.max(1,Number(params.limit)||20)),skip:Math.max(0,Number(params.skip)||0)})}`,opciones);
    }
    window.PersonasAPI = {
        buscar,

        crear,

        obtener,

        actualizar,

        darDeBaja,

        reactivar

    };

})();