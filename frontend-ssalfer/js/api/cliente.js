/**
 * cliente.js
 * ---------------------------------------------------------------------------
 * Cliente HTTP base para todo SSALFER. Centraliza:
 *   - URL base de la API.
 *   - credentials: "include" (para que viaje la cookie httponly de sesión).
 *   - Header X-CSRF-Token automático en POST/PATCH/DELETE, leído de la cookie
 *     legible (__Host-pa_csrf en producción, pa_csrf_dev en desarrollo).
 *   - Parseo uniforme de errores (422 de Pydantic, 400/403/404/409 con detail).
 *
 * Ningún archivo de página o de js/api/*.js debe usar fetch() directamente:
 * todos pasan por request() / get() / post() / patch() / del() de este módulo.
 * ---------------------------------------------------------------------------
 */

const API_BASE_URL =
    (window.SSALFER_CONFIG && window.SSALFER_CONFIG.API_BASE_URL)
        ? window.SSALFER_CONFIG.API_BASE_URL
        : "http://localhost:8000/api";

const NOMBRES_COOKIE_CSRF = ["__Host-pa_csrf", "pa_csrf_dev"];


/**
 * Lee el valor de una cookie por nombre (document.cookie no expone las
 * httponly, así que esto solo puede leer la cookie CSRF, que es legible
 * a propósito).
 */
function leerCookie(nombre) {

    const partes = document.cookie ? document.cookie.split("; ") : [];

    for (const parte of partes) {

        const igual = parte.indexOf("=");

        if (igual === -1) continue;

        const clave = decodeURIComponent(parte.slice(0, igual));

        if (clave === nombre) {

            return decodeURIComponent(parte.slice(igual + 1));

        }

    }

    return null;

}


/**
 * Devuelve el token CSRF vigente, probando primero la cookie de producción
 * y luego la de desarrollo.
 */
function obtenerTokenCSRF() {

    for (const nombre of NOMBRES_COOKIE_CSRF) {

        const valor = leerCookie(nombre);

        if (valor) return valor;

    }

    return null;

}


/**
 * Error tipado que representa una respuesta no exitosa del backend.
 * - status: código HTTP.
 * - detail: el campo "detail" del backend (string, o el arreglo de errores
 *   de validación de Pydantic en el caso de un 422).
 * - mensaje: un string ya listo para mostrar en pantalla, sea cual sea la
 *   forma que tenía "detail".
 */
class ErrorAPI extends Error {

    constructor(status, detail, mensaje) {

        super(mensaje);

        this.name = "ErrorAPI";

        this.status = status;

        this.detail = detail;

    }

}


/**
 * Convierte el "detail" que regresa FastAPI/Pydantic en un string legible.
 *
 * Casos:
 *   - 422: detail es un arreglo de objetos {loc, msg, type, ...}. Se arma
 *     una lista "campo: mensaje" por cada error.
 *   - 400/403/404/409: detail normalmente ya es un string.
 *   - Cualquier otra forma inesperada: se hace JSON.stringify como respaldo.
 */
function formatearDetalle(detail) {

    if (!detail) return "Ocurrió un error inesperado.";

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {

        return detail
            .map(err => {

                const campo =
                    Array.isArray(err.loc)
                        ? err.loc.filter(p => p !== "body").join(".")
                        : "campo";

                return `${campo}: ${err.msg}`;

            })
            .join(" | ");

    }

    try {

        return JSON.stringify(detail);

    } catch {

        return "Ocurrió un error inesperado.";

    }

}


/**
 * Petición base. Todas las funciones de este módulo y de js/api/*.js pasan
 * por aquí.
 *
 * @param {string} ruta - Ruta relativa a API_BASE_URL, ej. "/auth/sesiones".
 * @param {object} opciones
 * @param {string} [opciones.metodo="GET"]
 * @param {object|null} [opciones.cuerpo=null] - Se serializa a JSON salvo
 *        que se pase formUrlEncoded=true.
 * @param {boolean} [opciones.formUrlEncoded=false] - Para /auth/sesiones,
 *        que espera application/x-www-form-urlencoded (OAuth2PasswordRequestForm).
 * @returns {Promise<any>} El cuerpo ya parseado (JSON), o null si la
 *          respuesta no trae cuerpo (204, o 200 vacío).
 * @throws {ErrorAPI} Si la respuesta no es 2xx.
 */
async function request(
    ruta,
    {
        metodo = "GET",
        cuerpo = null,
        formUrlEncoded = false
    } = {}
) {

    const metodosConCSRF = ["POST", "PATCH", "DELETE", "PUT"];

    const encabezados = {};

    let cuerpoFinal = undefined;

    if (cuerpo !== null && cuerpo !== undefined) {

        if (formUrlEncoded) {

            encabezados["Content-Type"] =
                "application/x-www-form-urlencoded";

            cuerpoFinal = new URLSearchParams(cuerpo).toString();

        } else {

            encabezados["Content-Type"] = "application/json";

            cuerpoFinal = JSON.stringify(cuerpo);

        }

    }

    if (metodosConCSRF.includes(metodo.toUpperCase())) {

        const token = obtenerTokenCSRF();

        if (token) {

            encabezados["X-CSRF-Token"] = token;

        }

    }

    let respuesta;

    try {

        respuesta = await fetch(
            `${API_BASE_URL}${ruta}`,
            {
                method: metodo,
                headers: encabezados,
                credentials: "include",
                body: cuerpoFinal
            }
        );

    } catch (errorRed) {

        throw new ErrorAPI(
            0,
            null,
            "No se pudo conectar con el servidor. Verifica tu conexión o que el backend esté disponible."
        );

    }

    if (respuesta.status === 204) return null;

    const tipoContenido = respuesta.headers.get("content-type") || "";

    const cuerpoRespuesta =
        tipoContenido.includes("application/json")
            ? await respuesta.json().catch(() => null)
            : null;

    if (!respuesta.ok) {

        const detail = cuerpoRespuesta ? cuerpoRespuesta.detail : null;

        throw new ErrorAPI(
            respuesta.status,
            detail,
            formatearDetalle(detail)
        );

    }

    return cuerpoRespuesta;

}


function get(ruta) {

    return request(ruta, { metodo: "GET" });

}


function post(ruta, cuerpo, opciones = {}) {

    return request(ruta, { metodo: "POST", cuerpo, ...opciones });

}


function patch(ruta, cuerpo) {

    return request(ruta, { metodo: "PATCH", cuerpo });

}


function del(ruta, cuerpo = null) {
    return request(ruta, {
        metodo: "DELETE",
        cuerpo
    });
}


/**
 * Helper de UI: muestra el mensaje de un ErrorAPI (o error genérico) dentro
 * de un contenedor de la página, en vez de un alert(). Cada página decide
 * dónde tiene su contenedor de errores; si no se pasa uno, hace fallback a
 * alert() para no romper el flujo.
 */
function mostrarErrorAPI(error, contenedor = null) {

    const mensaje =
        error instanceof ErrorAPI
            ? error.mensaje || error.message
            : (error?.message || "Ocurrió un error inesperado.");

    if (contenedor) {

        contenedor.textContent = mensaje;

        contenedor.hidden = false;

    } else {

        alert(mensaje);

    }

    console.error("Error de API:", error);

}


window.ClienteAPI = {
    API_BASE_URL,
    ErrorAPI,
    get,
    post,
    patch,
    del,
    mostrarErrorAPI,
    obtenerTokenCSRF
};
