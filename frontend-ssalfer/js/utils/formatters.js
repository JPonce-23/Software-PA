(() => {
    "use strict";

    function formatearFecha(valor, respaldo = "—") {
        if (valor === null || valor === undefined || valor === "") {
            return respaldo;
        }

        const texto = String(valor).trim();
        const fecha = texto.slice(0, 10);
        const coincidencia = /^(\d{4})-(\d{2})-(\d{2})$/.exec(fecha);

        if (!coincidencia) {
            return texto;
        }

        const [, anio, mes, dia] = coincidencia;
        return `${dia}-${mes}-${anio}`;
    }

    function formatearPorcentaje(valor, maxDecimales = 2, respaldo = "—") {
        if (valor === null || valor === undefined || valor === "") {
            return respaldo;
        }

        const numero = Number(valor);
        if (!Number.isFinite(numero)) {
            return String(valor);
        }

        return `${numero.toLocaleString("es-MX", {
            minimumFractionDigits: 0,
            maximumFractionDigits: maxDecimales
        })}%`;
    }

    function etiquetaCodigo(valor, diccionario = {}) {
        if (valor === null || valor === undefined || valor === "") {
            return "—";
        }

        const clave = String(valor);
        if (Object.prototype.hasOwnProperty.call(diccionario, clave)) {
            return diccionario[clave];
        }

        return clave
            .replaceAll("_", " ")
            .replace(/\b\w/g, letra => letra.toUpperCase());
    }

    window.SSALFER_FORMAT = Object.freeze({
        formatearFecha,
        formatearPorcentaje,
        etiquetaCodigo
    });
})();
