document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
                    ELEMENTOS
    ====================================================== */

    const formulario =
        document.getElementById("formNuevoProyecto");

    const claveProyecto =
        document.getElementById("clave_proyecto");

    const nombreProyecto =
        document.getElementById("nombre_proyecto");

    const descripcion =
        document.getElementById("descripcion");

    const fechaInicio =
        document.getElementById("fecha_inicio");

    const fechaFin =
        document.getElementById("fecha_fin");

    const btnCrear =
        document.getElementById("btnCrearProyecto");


    /* =====================================================
                    FUNCIONES DE VALIDACIÓN
    ====================================================== */

    function mostrarError(campo, mensaje) {

        campo.classList.add("invalido");

        let error =
            campo.parentElement.querySelector(
                ".mensaje-error"
            );

        if (!error) {

            error =
                document.createElement("small");

            error.className =
                "mensaje-error";

            campo.parentElement.appendChild(error);

        }

        error.textContent = mensaje;

        error.classList.add("mostrar");

    }


    function limpiarError(campo) {

        campo.classList.remove("invalido");

        const error =
            campo.parentElement.querySelector(
                ".mensaje-error"
            );

        if (error) {

            error.textContent = "";

            error.classList.remove("mostrar");

        }

    }


    function validarCampoTexto(
        campo,
        nombre,
        maximo
    ) {

        const valor =
            campo.value.trim();


        if (!valor) {

            mostrarError(
                campo,
                `${nombre} es obligatorio.`
            );

            return false;

        }


        if (valor.length > maximo) {

            mostrarError(
                campo,
                `${nombre} no puede superar los ${maximo} caracteres.`
            );

            return false;

        }


        limpiarError(campo);

        return true;

    }


    function validarFechas() {

        limpiarError(fechaInicio);
        limpiarError(fechaFin);


        /*
         * Las fechas son opcionales.
         * Solamente validamos su relación
         * cuando ambas fueron proporcionadas.
         */

        if (
            fechaInicio.value &&
            fechaFin.value
        ) {

            const inicio =
                new Date(fechaInicio.value);

            const fin =
                new Date(fechaFin.value);


            if (fin < inicio) {

                mostrarError(
                    fechaFin,
                    "La fecha de finalización no puede ser anterior a la fecha de inicio."
                );

                return false;

            }

        }

        return true;

    }


    /* =====================================================
                    VALIDACIÓN COMPLETA
    ====================================================== */

    function validarFormulario() {

        let valido = true;


        /*
         * Backend:
         *
         * clave_proyecto:
         * min 1 / max 30
         */

        if (
            !validarCampoTexto(
                claveProyecto,
                "La clave del proyecto",
                30
            )
        ) {

            valido = false;

        }


        /*
         * Backend:
         *
         * nombre_proyecto:
         * min 1 / max 200
         */

        if (
            !validarCampoTexto(
                nombreProyecto,
                "El nombre del proyecto",
                200
            )
        ) {

            valido = false;

        }


        /*
         * Descripción es opcional.
         */

        if (descripcion.value.length > 0) {

            limpiarError(descripcion);

        }


        /*
         * Validación de fechas.
         */

        if (!validarFechas()) {

            valido = false;

        }


        return valido;

    }


    /* =====================================================
                    LIMPIAR ERRORES AL ESCRIBIR
    ====================================================== */

    claveProyecto.addEventListener(
        "input",
        () => {

            limpiarError(claveProyecto);

        }
    );


    nombreProyecto.addEventListener(
        "input",
        () => {

            limpiarError(nombreProyecto);

        }
    );


    descripcion.addEventListener(
        "input",
        () => {

            limpiarError(descripcion);

        }
    );


    fechaInicio.addEventListener(
        "change",
        validarFechas
    );


    fechaFin.addEventListener(
        "change",
        validarFechas
    );


    /* =====================================================
                    ENVÍO DEL FORMULARIO
    ====================================================== */

    formulario.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();


            if (!validarFormulario()) {

                return;

            }


            const proyecto = {

                clave_proyecto:
                    claveProyecto.value.trim(),

                nombre_proyecto:
                    nombreProyecto.value.trim(),

                descripcion:
                    descripcion.value.trim() || null,

                fecha_inicio:
                    fechaInicio.value || null,

                fecha_fin:
                    fechaFin.value || null

            };


            const confirmar =
                confirm(
                    "¿Deseas registrar este proyecto?"
                );


            if (!confirmar) {

                return;

            }


            const btnGuardar =
                formulario.querySelector("[type='submit']");

            if (btnGuardar) btnGuardar.disabled = true;

            try {

                await window.ProyectosAPI.crear(proyecto);

                alert(
                    "El proyecto se registró correctamente."
                );

                window.location.href =

                "/dashboard.html";

            } catch (error) {

                window.ClienteAPI.mostrarErrorAPI(error);

            } finally {

                if (btnGuardar) btnGuardar.disabled = false;

            }

        }
    );


});