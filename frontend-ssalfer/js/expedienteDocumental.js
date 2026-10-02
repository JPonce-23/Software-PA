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
    let idRequisitoEditando = null;


    let catalogoRequisitos = [];
    const referencias = new Map();
    const listasEntidad = new Map();
    let revisionEntidad = 0;
    let revisionDocumento = 0;

    async function listarRegistros(tipo) {
        if (listasEntidad.has(tipo)) return listasEntidad.get(tipo);
        const consulta = (async () => {
            const f = window.SSALFER_FORMAT;
            const fecha = valor => valor ? f.formatearFecha(valor) : null;
            const texto = partes => partes.filter(Boolean).join(" · ");
            const nombre = item => texto([item.nombre, item.apellido_paterno, item.apellido_materno]).replaceAll(" · ", " ");
            const directos = {
                afectacion: ["AfectacionesAPI", "id_afectacion", item => texto([f.etiquetaCodigo(item.tipo_afectacion), item.superficie_afectada_ha == null ? null : `${Number(item.superficie_afectada_ha).toLocaleString("es-MX")} ha`, item.situacion])],
                parcela: ["ParcelasAPI", "id_parcela", item => texto([item.no_parcela, item.certificado_parcelario])],
                unidad_agraria: ["UnidadesAgrariasAPI", "id_unidad_agraria", item => item.referencia_alfanumerica || item.referencia_normalizada],
                asamblea: ["AsambleasAPI", "id_asamblea", item => item.proposito],
                tramite_ran: ["TramitesRanAPI", "id_tramite_ran", item => item.referencia_expediente],
                tramite_fifonafe: ["FifonafeAPI", "id_tramite_fifonafe", item => texto([item.referencia_expediente, f.etiquetaCodigo(item.estatus)])],
                orv: ["OrvAPI", "id_orv", item => item.numero_orv],
                padron_historial: ["PadronesAPI", "id_padron", item => texto(["Padrón", fecha(item.fecha_padron), item.numero_ejidatarios_comuneros == null ? null : `${item.numero_ejidatarios_comuneros} integrantes`])],
                actividad_campo: ["ActividadesAPI", "id_actividad", item => texto([f.etiquetaCodigo(item.tipo_actividad), fecha(item.fecha_realizada || item.fecha_programada), item.resultado])]
            };
            let registros = [];
            if (tipo === "proyecto_nucleo") {
                const item = await window.NucleosAPI.obtenerProyectoNucleo(idNucleo);
                registros = [{ id: Number(idNucleo), etiqueta: item.nombre_nucleo, item }];
            } else if (directos[tipo]) {
                const [api, campo, etiqueta] = directos[tipo];
                registros = (await window[api].listarPorProyectoNucleo(idNucleo)).map(item => ({
                    id: Number(item[campo]), etiqueta: etiqueta(item) || nombresEntidad[tipo], item
                }));
            } else {
                const dependientes = {
                    parcela_titular: ["parcela", "ParcelasAPI", "listarTitulares", "id_parcela_titular"],
                    unidad_agraria_titular: ["unidad_agraria", "UnidadesAgrariasAPI", "listarTitulares", "id_unidad_titular"],
                    asamblea_convocatoria: ["asamblea", "AsambleasAPI", "listarConvocatorias", "id_convocatoria"],
                    convenio: ["afectacion", "ConveniosAPI", "listarPorAfectacion", "id_convenio"],
                    convenio_compareciente: ["convenio", "ConveniosAPI", "listarComparecientes", "id_compareciente"],
                    tramite_ran_evento: ["tramite_ran", "TramitesRanAPI", "listarEventos", "id_evento_ran"],
                    tramite_fifonafe_evento: ["tramite_fifonafe", "FifonafeAPI", "listarEventos", "id_evento_fifonafe"],
                    tramite_fifonafe_interviniente: ["tramite_fifonafe", "FifonafeAPI", "listarIntervinientes", "id_interviniente_fifonafe"],
                    indemnizacion: ["afectacion", "IndemnizacionAPI", "listarPorAfectacion", "id_indemnizacion"],
                    pago: ["indemnizacion", "IndemnizacionAPI", "listarPagos", "id_pago"]
                };
                const config = dependientes[tipo];
                if (!config) return [];
                const [padreTipo, api, metodo, campo] = config;
                for (const padre of await listarRegistros(padreTipo)) {
                    const respuesta = await window[api][metodo](padre.id);
                    const hijos = Array.isArray(respuesta) ? respuesta : respuesta ? [respuesta] : [];
                    for (const item of hijos) {
                        let etiqueta;
                        if (tipo === "parcela_titular") etiqueta = texto([nombre(item), item.tipo_derecho]);
                        if (tipo === "convenio") etiqueta = texto([f.etiquetaCodigo(item.tipo_convenio), `Consecutivo ${item.consecutivo}`, item.descripcion_instrumento]);
                        if (tipo === "asamblea_convocatoria") etiqueta = texto([`Convocatoria ${item.ordinal}`, fecha(item.fecha_realizacion || item.fecha_programada)]);
                        if (tipo === "tramite_ran_evento") etiqueta = texto([`Evento ${item.ordinal}`, item.folio_referencia || item.numero_solicitud, fecha(item.fecha_evento)]);
                        if (tipo === "tramite_fifonafe_evento") etiqueta = texto([`Evento ${item.ordinal}`, item.numero_oficio, fecha(item.fecha_evento || item.fecha_oficio)]);
                        if (tipo === "indemnizacion") etiqueta = texto(["Indemnización", f.etiquetaCodigo(item.estatus), fecha(item.fecha_programada)]);
                        if (tipo === "pago") etiqueta = texto([item.referencia || "Pago", item.beneficiario_nombre, fecha(item.fecha_pago)]);
                        if (["convenio_compareciente", "tramite_fifonafe_interviniente", "unidad_agraria_titular"].includes(tipo)) {
                            etiqueta = item.nombre_en_instrumento;
                            if (!etiqueta && item.id_persona) etiqueta = nombre(await window.PersonasAPI.obtener(item.id_persona));
                            if (!etiqueta && item.id_parcela_titular) etiqueta = (await listarRegistros("parcela_titular")).find(titular => titular.id === Number(item.id_parcela_titular))?.etiqueta;
                            etiqueta = texto([etiqueta || "Nombre no disponible", item.rol ? f.etiquetaCodigo(item.rol) : null]);
                        }
                        registros.push({ id: Number(item[campo]), etiqueta: texto([padre.etiqueta, etiqueta || nombresEntidad[tipo]]), item });
                    }
                }
            }
            registros = [...new Map(registros.map(item => [item.id, item])).values()];
            registros.forEach(item => referencias.set(`${tipo}:${item.id}`, item.etiqueta));
            return registros;
        })().catch(error => { listasEntidad.delete(tipo); throw error; });
        listasEntidad.set(tipo, consulta);
        return consulta;
    }

    async function cargarSelectorEntidad(actual = null) {
        const revision = ++revisionEntidad;
        ++revisionDocumento;
        const tipo = document.getElementById("entidadTipo").value;
        const select = document.getElementById("entidadId");
        select.disabled = true;
        select.replaceChildren(new Option(tipo ? "Cargando registros..." : "Selecciona primero el tipo de entidad", ""));
        elementoIdDocumento().replaceChildren(new Option("Sin documento relacionado", ""));
        if (!tipo) return;
        try {
            const registros = await listarRegistros(tipo);
            if (revision !== revisionEntidad) return;
            select.replaceChildren(new Option(registros.length ? "Selecciona un registro" : "No hay elementos disponibles", ""));
            registros.forEach(item => select.add(new Option(item.etiqueta, String(item.id))));
            if (actual && !registros.some(item => item.id === Number(actual))) {
                select.add(new Option("Registro asociado no disponible en el listado", String(actual)));
            }
            select.value = actual ? String(actual) : "";
            select.disabled = Boolean(idRequisitoEditando) || !registros.length;
        } catch (error) {
            if (revision !== revisionEntidad) return;
            select.replaceChildren(new Option("No fue posible cargar los registros", ""));
            window.SSALFER_UI.toast("No fue posible cargar los registros relacionados. Vuelve a seleccionar el tipo para reintentar.", { tipo: "error" });
        }
    }
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

            listasEntidad.clear();
            referencias.clear();
            const resultados = await Promise.allSettled([...new Set(requisitos.map(item => item.entidad_tipo))].map(listarRegistros));
            if (resultados.some(resultado => resultado.status === "rejected")) {
                window.SSALFER_UI.toast("Algunas referencias no están disponibles. Vuelve a abrir el expediente para reintentar.", { tipo: "error" });
            }

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
                            window.SSALFER_UI.escaparHTML(referencias.get(`${requisito.entidad_tipo}:${requisito.entidad_id}`) || "Referencia no disponible")
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


                        const requisitoCatalogo =
                            requisitoPorId.get(
                                Number(requisito.id_requisito)
                            );

                        const estadoCatalogo =
                            estadoPorId.get(
                                Number(requisito.id_estado)
                            );

                        window.SSALFER_UI?.verDatos(
                            "Consultar requisito",
                            {
                                Requisito:
                                    requisitoCatalogo?.nombre
                                    || requisitoCatalogo?.codigo
                                    || `Requisito #${requisito.id_requisito}`,
                                Estado:
                                    estadoCatalogo?.nombre
                                    || estadoCatalogo?.codigo
                                    || `Estado #${requisito.id_estado}`,
                                Entidad:
                                    nombresEntidad[requisito.entidad_tipo]
                                    || requisito.entidad_tipo
                                    || "—",
                                "Registro relacionado":
                                    referencias.get(`${requisito.entidad_tipo}:${requisito.entidad_id}`) || "Referencia no disponible",
                                Documento:
                                    requisito.documento
                                    || (requisito.id_documento
                                        ? "Documento asociado"
                                        : "Sin documento"),
                                Detalle:
                                    requisito.detalle
                                    || "Sin detalle adicional."
                            }
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
                    async () => {

                        const id =
                            boton.dataset
                                .editar;

                        const requisito =
                            requisitos.find(
                                item =>
                                    String(item.id_expediente_requisito) ===
                                    String(id)
                            );

                        if (!requisito) return;

                        idRequisitoEditando =
                            Number(requisito.id_expediente_requisito);

                        mostrarFormulario();

                        document.getElementById("idRequisito").value =
                            String(requisito.id_requisito || "");
                        document.getElementById("idEstado").value =
                            String(requisito.id_estado || "");
                        document.getElementById("entidadTipo").value =
                            requisito.entidad_tipo || "";
                        await cargarSelectorEntidad(requisito.entidad_id);
                        document.getElementById("idRequisito").disabled = true;
                        document.getElementById("entidadTipo").disabled = true;
                        document.getElementById("detalle").value =
                            requisito.detalle || "";

                        await cargarDocumentosDeEntidad();

                        if (requisito.id_documento && !Array.from(elementoIdDocumento().options).some(opcion => Number(opcion.value) === Number(requisito.id_documento))) {
                            elementoIdDocumento().add(new Option("Documento asociado no disponible en el listado", String(requisito.id_documento)));
                        }

                        document.getElementById("idDocumento").value =
                            requisito.id_documento
                                ? String(requisito.id_documento)
                                : "";

                        const titulo =
                            formulario.querySelector("h2");
                        const botonGuardar =
                            form.querySelector('[type="submit"]');

                        if (titulo) {
                            titulo.textContent =
                                "Editar requisito documental";
                        }

                        if (botonGuardar) {
                            botonGuardar.textContent =
                                "Guardar cambios";
                        }
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


        window.SSALFER_UI?.desplazarA(formulario);


        document.getElementById(
            "idRequisito"
        )?.focus({ preventScroll: true });

    }


    function ocultarFormulario() {

        if (!formulario) {

            return;

        }


        formulario.hidden =
            true;

        idRequisitoEditando = null;
        limpiarFormulario();

    }



    if (btnNuevoRequisito) {

        btnNuevoRequisito.addEventListener(
            "click",
            () => {
                idRequisitoEditando = null;
                limpiarFormulario();

                const titulo =
                    formulario?.querySelector("h2");
                const botonGuardar =
                    form?.querySelector('[type="submit"]');

                if (titulo) {
                    titulo.textContent =
                        "Registrar requisito documental";
                }

                if (botonGuardar) {
                    botonGuardar.textContent =
                        "Registrar requisito";
                }

                mostrarFormulario();
            }
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


            window.SSALFER_UI?.toast(
                "Selecciona el requisito documental.",
                { tipo: "error" }
            );


            return false;

        }


        if (!idEstado.value) {

            idEstado.classList.add(
                "invalido"
            );


            window.SSALFER_UI?.toast(
                "Selecciona el estado del requisito.",
                { tipo: "error" }
            );


            return false;

        }


        if (!entidadTipo.value) {

            entidadTipo.classList.add(
                "invalido"
            );


            window.SSALFER_UI?.toast(
                "Selecciona el tipo de entidad.",
                { tipo: "error" }
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


            window.SSALFER_UI?.toast(
                "Selecciona el registro relacionado.",
                { tipo: "error" }
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
        const revision = ++revisionDocumento;

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

            if (revision !== revisionDocumento) return;

            (Array.isArray(documentos) ? documentos : []).forEach(
                documento => {

                    const opcion =
                        document.createElement("option");

                    opcion.value = documento.id_documento;

                    opcion.textContent =
                        documento.nombre
                        || documento.titulo
                        || documento.tipo_documento || "Documento";

                    selectDocumento.appendChild(opcion);

                }
            );

        } catch (error) {

            window.ClienteAPI.mostrarErrorAPI(error);

        }

    }


    document.getElementById("entidadTipo")
        ?.addEventListener("change", () => cargarSelectorEntidad());

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

        document.getElementById("idRequisito").disabled = false;
        document.getElementById("entidadTipo").disabled = false;
        void cargarSelectorEntidad();


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

                    window.SSALFER_UI?.toast(
                        "No se puede registrar el requisito porque falta el contexto del núcleo.",
                        { tipo: "error" }
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

                    const estabaEditando =
                        Number.isInteger(idRequisitoEditando)
                        && idRequisitoEditando > 0;

                    if (estabaEditando) {
                        await window.DocumentosAPI.actualizarRequisito(
                            idRequisitoEditando,
                            {
                                id_estado: nuevoRequisito.id_estado,
                                id_documento: nuevoRequisito.id_documento,
                                detalle: nuevoRequisito.detalle
                            }
                        );
                    } else {
                        await window.DocumentosAPI.crearRequisito(
                            idNucleo,
                            nuevoRequisito
                        );
                    }

                    await cargarRequisitos();

                    ocultarFormulario();

                    window.SSALFER_UI?.toast(
                        estabaEditando
                            ? "El requisito se actualizó correctamente."
                            : "El requisito se guardó correctamente."
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

                window.location.href = idNucleo ? `/pages/nucleoAgrario.html?id_proyecto_nucleo=${encodeURIComponent(idNucleo)}` : "/dashboard.html";

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
