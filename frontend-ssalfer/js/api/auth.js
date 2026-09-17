/**
 * auth.js — POST /auth/sesiones, GET /auth/sesion, POST /auth/logout[-todas]
 *
 * El login usa application/x-www-form-urlencoded (OAuth2PasswordRequestForm
 * de FastAPI), NO JSON. El resto del sistema (todas las demás páginas) debe
 * llamar a requerirSesion() al cargar, para redirigir a Index.html si no hay
 * sesión activa.
 */

(function () {

    const { get, post, ErrorAPI } = window.ClienteAPI;


    async function login(usuario, password) {

        return post(
            "/auth/sesiones",
            { username: usuario, password },
            { formUrlEncoded: true }
        );

    }


    async function obtenerSesionActual() {

        return get("/auth/sesion");

    }


    async function logout() {

        return post("/auth/logout", null);

    }


    async function logoutTodas() {

        return post("/auth/logout-todas", null);

    }


    /**
     * Llamar al inicio de cada página protegida (dashboard.html y todo lo
     * que cuelga de pages/). Si no hay sesión válida, redirige al login.
     * Devuelve los datos de sesión si sí la hay, para que la página pueda
     * mostrar el nombre de usuario / rol si lo necesita.
     */
    async function requerirSesion() {

        try {

            return await obtenerSesionActual();

        } catch (error) {

            if (error instanceof ErrorAPI && (error.status === 401 || error.status === 403)) {

                window.location.href = "/Index.html";

                return null;

            }

            throw error;

        }

    }


    document.addEventListener("click", async function (evento) {

        const enlace = evento.target.closest("a");

        if (!enlace) {
            return;
        }

        const esLogout =
            enlace.dataset.action === "logout" ||
            enlace.textContent.trim().toLowerCase().includes("cerrar sesión");

        if (!esLogout) {
            return;
        }

        evento.preventDefault();

        try {

            await logout();
            window.location.href = "/Index.html";

        } catch (error) {

            console.error("No se pudo cerrar la sesión:", error);
            alert("No se pudo cerrar la sesión. Intenta nuevamente.");

        }

    });



    window.AuthAPI = {
        login,
        obtenerSesionActual,
        logout,
        logoutTodas,
        requerirSesion
    };

})();
