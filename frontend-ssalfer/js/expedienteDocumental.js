document.addEventListener("DOMContentLoaded", () => {


    /* =====================================================
                OBTENER ID DEL PROYECTO NÚCLEO
    ====================================================== */

    const parametros =
        new URLSearchParams(
            window.location.search
        );


    const idProyectoNucleo =
        parametros.get(
            "id_proyecto_nucleo"
        );


    const contenedor =
        document.querySelector(
            ".contenedor"
        );


    const idHTML =
        contenedor?.dataset.proyectoNucleoId
        || null;


    const idNucleo =
        idProyectoNucleo
        || idHTML;



    /* =====================================================
                        ELEMENTOS
    ====================================================== */

    const btnVolver =
        document.getElementById(
            "btnVolver"
        );


    const btnNuevoRequisito =
        document.getElementById(
            "btnNuevoRequisito"
        );


    const btnCancelar =
        document.getElementById(
            "btnCancelarRequisito"
        );


    const formulario =
        document.getElementById(
            "formularioRequisito"
        );


    const form =
        document.getElementById(
            "formRequisito"
        );


    const tabla =
        document.getElementById(
            "requisitosTabla"
        );


    const filtroEntidad =
        document.getElementById(
            "filtroAmbito"
        );


    const filtroEstado =
        document.getElementById(
            "filtroEstado"
        );



    /* =====================================================
                    DATOS SIMULADOS
    ====================================================== */

    /*
     * Estos datos son únicamente para visualizar
     * el funcionamiento de la pantalla.
     *
     * Posteriormente se sustituirán por:
     *
     * GET
     * /proyecto-nucleo/{id_proyecto_nucleo}/requisitos-documentales
     *
     * POST
     * /proyecto-nucleo/{id_proyecto_nucleo}/requisitos-documentales
     *
     * PATCH
     * /requisitos-documentales/{id_expediente_requisito}
     */


    let requisitos = [];


    let catalogoRequisitos = [];
let estadosRequisito = [];

let requisitoPorId = new Map();
let estadoPorId = new Map();

async function cargarCatalogos() {

    const [requisitosCatalogo, estados] =
        await Promise.all([
            window.DocumentosAPI
                .listarCatalogoRequisitos(),

            window.CatalogosAPI
                .obtenerOperativo(
                    "estado_requisito_documental"
                )
        ]);

    catalogoRequisitos =
        Array.isArray(requisitosCatalogo)
            ? requisitosCatalogo
            : [];

    estadosRequisito =
        Array.isArray(estados)
            ? estados
            : [];

    requisitoPorId = new Map(
        catalogoRequisitos.map(item => [
            Number(item.id_requisito),
            item
        ])
    );

    estadoPorId = new Map(
        estadosRequisito.map(item => [
            Number(item.id_catalogo_opcion),
            item
        ])
    );


    /* ==============================
            REQUISITOS
    ============================== */

    const selectRequisito =
        document.getElementById(
            "idRequisito"
        );

    if (selectRequisito) {

        selectRequisito.replaceChildren();

        const opcionInicial =
            document.createElement(
                "option"
            );

        opcionInicial.value = "";
        opcionInicial.textContent =
            "Selecciona un requisito";

        selectRequisito.appendChild(
            opcionInicial
        );

        catalogoRequisitos.forEach(item => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                item.id_requisito;

            option.textContent =
                item.nombre ||
                item.codigo ||
                `Requisito #${item.id_requisito}`;

            selectRequisito.appendChild(
                option
            );
        });
    }


    /* ==============================
        ESTADO DEL FORMULARIO
    ============================== */

    const selectEstado =
        document.getElementById(
            "idEstado"
        );

    if (selectEstado) {

        selectEstado.replaceChildren();

        const opcionInicial =
            document.createElement(
                "option"
            );

        opcionInicial.value = "";
        opcionInicial.textContent =
            "Selecciona un estado";

        selectEstado.appendChild(
            opcionInicial
        );

        estadosRequisito.forEach(item => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                item.id_catalogo_opcion;

            option.textContent =
                item.nombre ||
                item.codigo ||
                `Estado #${item.id_catalogo_opcion}`;

            selectEstado.appendChild(
                option
            );
        });
    }


    /* ==============================
            FILTRO ESTADO
    ============================== */

    const selectFiltroEstado =
        document.getElementById(
            "filtroEstado"
        );

    if (selectFiltroEstado) {

        selectFiltroEstado.replaceChildren();

        const opcionTodos =
            document.createElement(
                "option"
            );

        opcionTodos.value = "";
        opcionTodos.textContent =
            "Todos";

        selectFiltroEstado.appendChild(
            opcionTodos
        );

        estadosRequisito.forEach(item => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                String(
                    item.id_catalogo_opcion
                );

            option.textContent =
                item.nombre ||
                item.codigo ||
                `Estado #${item.id_catalogo_opcion}`;

            selectFiltroEstado.appendChild(
                option
            );
        });
    }

    console.log(
        "Catálogos documentales cargados:",
        {
            requisitos:
                catalogoRequisitos.length,

            estados:
                estadosRequisito.length
        }
    );
}


    async function cargarRequisitos() {

        if (!idNucleo) return;

        try {

            const reales =
                await window.DocumentosAPI.listarRequisitosPorProyectoNucleo(idNucleo);

            requisitos = Array.isArray(reales) ? reales : [];

            mostrarRequisitos();

            actualizarResumen();

        } catch (error) {

            window.ClienteAPI.mostrarErrorAPI(error);

        }

    }



    /* =====================================================
                NOMBRES DE ENTIDADES
    ====================================================== */

    const nombresEntidad = {

        proyecto_nucleo:
            "Núcleo del proyecto",

        afectacion:
            "Afectación",

        parcela:
            "Parcela",

        parcela_titular:
            "Titular de parcela",

        unidad_agraria:
            "Unidad agraria",

        unidad_agraria_titular:
            "Titular de unidad agraria",

        convenio:
            "Convenio",

        convenio_compareciente:
            "Compareciente de convenio",

        tramite_ran:
            "Trámite RAN",

        tramite_ran_evento:
            "Evento RAN",

        tramite_fifonafe:
            "Trámite FIFONAFE",

        tramite_fifonafe_evento:
            "Evento FIFONAFE",

        tramite_fifonafe_interviniente:
            "Interviniente FIFONAFE",

        indemnizacion:
            "Indemnización",

        pago:
            "Pago",

        orv:
            "ORV",

        padron_historial:
            "Padrón",

        actividad_campo:
            "Actividad de campo",

        asamblea:
            "Asamblea",

        asamblea_convocatoria:
            "Convocatoria"

    };



    /* =====================================================
                    ESTADOS VISUALES
    ====================================================== */

    const nombresEstado = {

        pendiente:
            "Pendiente",

        cumplido:
            "Cumplido",

        "en-revision":
            "En revisión",

        "no-aplica":
            "No aplica"

    };



    /* =====================================================
                    RESUMEN
    ====================================================== */

    function actualizarResumen() {

            const total =
                document.getElementById(
                    "totalRequisitos"
                );

            const cumplidos =
                document.getElementById(
                    "totalCumplidos"
                );

            const pendientes =
                document.getElementById(
                    "totalPendientes"
                );

            const documentos =
                document.getElementById(
                    "totalDocumentos"
                );

            const codigoEstado = requisito => {
                return estadoPorId.get(
                    Number(requisito.id_estado)
                )?.codigo;
            };

            if (total) {
                total.textContent =
                    requisitos.length;
            }

            if (cumplidos) {
                cumplidos.textContent =
                    requisitos.filter(
                        requisito =>
                            codigoEstado(requisito) ===
                            "disponible"
                    ).length;
            }

            if (pendientes) {
                pendientes.textContent =
                    requisitos.filter(
                        requisito => {
                            const codigo =
                                codigoEstado(requisito);

                            return (
                                codigo === "pendiente" ||
                                codigo === "faltante"
                            );
                        }
                    ).length;
            }

            if (documentos) {
                documentos.textContent =
                    requisitos.filter(
                        requisito =>
                            requisito.id_documento
                    ).length;
            }
        }



    /* =====================================================
                    FILTRADO
    ====================================================== */

    function obtenerRequisitosFiltrados() {

        const entidad =
            filtroEntidad?.value
            || "";


        const estado =
            filtroEstado?.value
            || "";


        return requisitos.filter(
            requisito => {

                const coincideEntidad =
                    !entidad
                    ||
                    requisito.entidad_tipo ===
                    entidad;


                const coincideEstado =
                    !estado ||
                    String(requisito.id_estado) ===
                        String(estado);


                return (
                    coincideEntidad
                    &&
                    coincideEstado
                );

            }
        );

    }



    /* =====================================================
                    MOSTRAR TABLA
    ====================================================== */

    function mostrarRequisitos() {

        if (!tabla) {

            return;

        }


        tabla.innerHTML = "";


        const lista =
            obtenerRequisitosFiltrados();


        if (!lista.length) {

            tabla.innerHTML = `

                <tr>

                    <td
                        colspan="7"
                        class="tabla-vacia">

                        No hay requisitos que coincidan
                        con los filtros seleccionados.

                    </td>

                </tr>

            `;


            actualizarResumen();

            return;

        }


        lista.forEach(
            requisito => {

                const fila =
                    document.createElement(
                        "tr"
                    );


                const estadoCatalogo =
                    estadoPorId.get(
                        Number(requisito.id_estado)
                    );

                const estado =
                    estadoCatalogo?.codigo || "otro";

                const nombreEstado =
                    estadoCatalogo?.nombre ||
                    estadoCatalogo?.codigo ||
                    `#${requisito.id_estado}`;

                const requisitoCatalogo =
                    requisitoPorId.get(
                        Number(requisito.id_requisito)
                    );

                const nombreRequisito =
                    requisitoCatalogo?.nombre ||
                    `Requisito #${requisito.id_requisito}`;


                const entidad =
                    nombresEntidad[
                        requisito.entidad_tipo
                    ]
                    ||
                    requisito.entidad_tipo
                    ||
                    "—";


                fila.innerHTML = `

                    <td>

                        <strong>

                            ${
                                nombreRequisito
                            }

                        </strong>

                    </td>


                    <td>

                        ${entidad}

                    </td>


                    <td>

                        ${
                            requisito.entidad_id
                            || "—"
                        }

                    </td>


                    <td>

                        <span
                            class="estado-documental ${estado}">

                            ${
                                nombresEstado[
                                    estado
                                ]
                                || estado
                            }

                        </span>

                    </td>


                    <td>

                        ${
                            requisito.id_documento

                            ? `

                                <span
                                    class="documento-asociado">

                                    <i
                                        class="bi bi-file-earmark-text">
                                    </i>

                                    ${
                                        requisito.documento
                                        || "Documento asociado"
                                    }

                                </span>

                            `

                            : `

                                <span
                                    class="sin-documento">

                                    Sin documento

                                </span>

                            `
                        }

                    </td>


                    <td>

                        ${
                            requisito.detalle
                            || "—"
                        }

                    </td>


                    <td>

                        <div
                            class="acciones-tabla">


                            <button
                                type="button"
                                class="btn-tabla"
                                title="Consultar requisito"
                                data-consultar="${requisito.id_expediente_requisito}">

                                <i class="bi bi-eye"></i>

                            </button>


                            <button
                                type="button"
                                class="btn-tabla"
                                title="Editar requisito"
                                data-editar="${requisito.id_expediente_requisito}">

                                <i class="bi bi-pencil"></i>

                            </button>

                        </div>

                    </td>

                `;


                tabla.appendChild(
                    fila
                );

            }
        );


        agregarEventosTabla();

        actualizarResumen();

    }



    /* =====================================================
                    ACCIONES DE TABLA
    ====================================================== */

    function agregarEventosTabla() {


        document.querySelectorAll(
            "[data-consultar]"
        ).forEach(
            boton => {

                boton.addEventListener(
                    "click",
                    () => {

                        const id =
                            boton.dataset
                                .consultar;


                        const requisito =
                            requisitos.find(
                                item =>
                                    String(
                                        item.id_expediente_requisito
                                    )
                                    ===
                                    String(id)
                            );


                        if (!requisito) {

                            return;

                        }


                        alert(

                            `Requisito: ${
                                requisito.requisito
                            }\n\n` +

                            `Estado: ${
                                nombresEstado[
                                    requisito.estado
                                ]
                                || requisito.estado
                            }\n\n` +

                            `Detalle: ${
                                requisito.detalle
                                || "Sin detalle adicional."
                            }`

                        );

                    }
                );

            }
        );



        document.querySelectorAll(
            "[data-editar]"
        ).forEach(
            boton => {

                boton.addEventListener(
                    "click",
                    () => {

                        const id =
                            boton.dataset
                                .editar;


                        alert(
                            "La edición se habilitará al conectar el backend."
                        );

                    }
                );

            }
        );

    }



    /* =====================================================
                MOSTRAR / OCULTAR FORMULARIO
    ====================================================== */

    function mostrarFormulario() {

        if (!formulario) {

            return;

        }


        formulario.hidden =
            false;


        formulario.scrollIntoView({

            behavior:
                "smooth",

            block:
                "start"

        });


        document.getElementById(
            "idRequisito"
        )?.focus();

    }


    function ocultarFormulario() {

        if (!formulario) {

            return;

        }


        formulario.hidden =
            true;


        limpiarFormulario();

    }



    if (btnNuevoRequisito) {

        btnNuevoRequisito.addEventListener(
            "click",
            mostrarFormulario
        );

    }


    if (btnCancelar) {

        btnCancelar.addEventListener(
            "click",
            ocultarFormulario
        );

    }



    /* =====================================================
                    VALIDACIÓN
    ====================================================== */

    function validarFormulario() {

        const idRequisito =
            document.getElementById(
                "idRequisito"
            );


        const idEstado =
            document.getElementById(
                "idEstado"
            );


        const entidadTipo =
            document.getElementById(
                "entidadTipo"
            );


        const entidadId =
            document.getElementById(
                "entidadId"
            );


        document.querySelectorAll(
            ".invalido"
        ).forEach(
            elemento => {

                elemento.classList.remove(
                    "invalido"
                );

            }
        );


        if (!idRequisito.value) {

            idRequisito.classList.add(
                "invalido"
            );


            alert(
                "Selecciona el requisito documental."
            );


            return false;

        }


        if (!idEstado.value) {

            idEstado.classList.add(
                "invalido"
            );


            alert(
                "Selecciona el estado del requisito."
            );


            return false;

        }


        if (!entidadTipo.value) {

            entidadTipo.classList.add(
                "invalido"
            );


            alert(
                "Selecciona el tipo de entidad."
            );


            return false;

        }


        if (
            !entidadId.value
            ||
            Number(entidadId.value) <= 0
        ) {

            entidadId.classList.add(
                "invalido"
            );


            alert(
                "Indica el identificador de la entidad relacionada."
            );


            return false;

        }


        return true;

    }



    /* =====================================================
            CARGAR DOCUMENTOS DE LA ENTIDAD SELECCIONADA
    ====================================================== */

    function elementoIdDocumento() {

        return document.getElementById("idDocumento");

    }


    async function cargarDocumentosDeEntidad() {

        const entidadTipo =
            document.getElementById("entidadTipo").value;

        const entidadId =
            document.getElementById("entidadId").value;

        const selectDocumento =
            elementoIdDocumento();

        if (!selectDocumento) return;

        selectDocumento.innerHTML =
            '<option value="">Sin documento relacionado</option>';

        if (!entidadTipo || !entidadId) {

            return;

        }

        try {

            const documentos =
                await window.DocumentosAPI.listarPorEntidad(
                    entidadTipo,
                    entidadId
                );

            (Array.isArray(documentos) ? documentos : []).forEach(
                documento => {

                    const opcion =
                        document.createElement("option");

                    opcion.value = documento.id_documento;

                    opcion.textContent =
                        documento.nombre
                        || documento.titulo
                        || `Documento #${documento.id_documento}`;

                    selectDocumento.appendChild(opcion);

                }
            );

        } catch (error) {

            window.ClienteAPI.mostrarErrorAPI(error);

        }

    }


    document.getElementById("entidadTipo")
        ?.addEventListener("change", cargarDocumentosDeEntidad);

    document.getElementById("entidadId")
        ?.addEventListener("change", cargarDocumentosDeEntidad);



    /* =====================================================
                    LIMPIAR FORMULARIO
    ====================================================== */

    function limpiarFormulario() {

        if (!form) {

            return;

        }


        form.reset();


        document.querySelectorAll(
            ".invalido"
        ).forEach(
            elemento => {

                elemento.classList.remove(
                    "invalido"
                );

            }
        );

    }



    /* =====================================================
                    ENVÍO
    ====================================================== */

    if (form) {

        form.addEventListener(
            "submit",
            async evento => {

                evento.preventDefault();


                if (
                    !validarFormulario()
                ) {

                    return;

                }


                const idRequisito =
                    document.getElementById(
                        "idRequisito"
                    ).value;


                const idEstado =
                    document.getElementById(
                        "idEstado"
                    ).value;


                const entidadTipo =
                    document.getElementById(
                        "entidadTipo"
                    ).value;


                const entidadId =
                    document.getElementById(
                        "entidadId"
                    ).value;


                const idDocumento =
                    document.getElementById(
                        "idDocumento"
                    ).value;


                const detalle =
                    document.getElementById(
                        "detalle"
                    ).value.trim();


                if (!idNucleo) {

                    alert(
                        "No se puede registrar el requisito porque falta el id_proyecto_nucleo."
                    );

                    return;

                }



                /* =================================================
                        OBJETO PARA BACKEND
                ================================================== */

                const nuevoRequisito = {

                    id_requisito:
                        Number(
                            idRequisito
                        ),

                    id_estado:
                        Number(
                            idEstado
                        ),

                    entidad_tipo:
                        entidadTipo,

                    entidad_id:
                        Number(
                            entidadId
                        ),

                    id_documento:
                        idDocumento
                        ? Number(
                            idDocumento
                        )
                        : null,

                    detalle:
                        detalle
                        || null

                };


                const btnGuardarRequisito =
                    form.querySelector("[type='submit']");

                if (btnGuardarRequisito) btnGuardarRequisito.disabled = true;

                try {

                    await window.DocumentosAPI.crearRequisito(
                        idNucleo,
                        nuevoRequisito
                    );

                    await cargarRequisitos();

                    ocultarFormulario();

                    alert(
                        "El requisito se guardó correctamente."
                    );

                } catch (error) {

                    window.ClienteAPI.mostrarErrorAPI(error);

                } finally {

                    if (btnGuardarRequisito) btnGuardarRequisito.disabled = false;

                }

            }
        );

    }



    /* =====================================================
                    FILTROS
    ====================================================== */

    if (filtroEntidad) {

        filtroEntidad.addEventListener(
            "change",
            mostrarRequisitos
        );

    }


    if (filtroEstado) {

        filtroEstado.addEventListener(
            "change",
            mostrarRequisitos
        );

    }



    /* =====================================================
                    VOLVER
    ====================================================== */

    if (btnVolver) {

        btnVolver.addEventListener(
            "click",
            () => {

                window.history.back();

            }
        );

    }



    /* =====================================================
                    INICIALIZACIÓN
    ====================================================== */

    (async () => {
        try {
            await cargarCatalogos();
            await cargarRequisitos();
        } catch (error) {
            window.ClienteAPI.mostrarErrorAPI(error);
        }
    })();

});