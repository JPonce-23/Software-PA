/* Limita la altura de las tablas, incluidas las cargadas o filtradas después. */
(() => {
    function iniciar() {
        const estados = new WeakMap();
        const pendientes = new Set();
        let programado = false;
        const opciones = {subtree:true, childList:true, attributes:true, attributeFilter:['hidden','style','class']};
        function actualizar(tabla) {
            if (!tabla.isConnected) return;
            const filas = [...tabla.tBodies].flatMap(cuerpo => [...cuerpo.rows])
                .filter(fila => !fila.hidden && getComputedStyle(fila).display !== 'none');
            const largo = filas.length > 15;
            let estado = estados.get(tabla);
            if (!estado && !largo) return;
            if (!estado) {
                let contenedor = tabla.parentElement;
                if (contenedor.tagName !== 'DIV' || contenedor.children.length !== 1) {
                    contenedor = document.createElement('div');
                    tabla.before(contenedor);
                    contenedor.append(tabla);
                }
                estado = {contenedor, atributos:Object.fromEntries(['tabindex','role','aria-label'].map(a => [a,contenedor.getAttribute(a)]))};
                estados.set(tabla, estado);
            }
            const {contenedor, atributos} = estado;
            contenedor.classList.toggle('ssalfer-tabla-scroll', largo);
            if (largo) {
                contenedor.tabIndex = 0;
                contenedor.setAttribute('role','region');
                contenedor.setAttribute('aria-label', atributos['aria-label'] ||
                    `${tabla.caption?.textContent.trim() || tabla.closest('section')?.querySelector('h2,h3')?.textContent.trim() || 'Tabla'}. Desplazamiento interno`);
            } else {
                for (const [nombre,valor] of Object.entries(atributos)) {
                    if (valor === null) contenedor.removeAttribute(nombre);
                    else contenedor.setAttribute(nombre,valor);
                }
                contenedor.scrollTop = 0;
            }
        }
        function agregar(nodo) {
            if (!(nodo instanceof Element)) return;
            const tabla = nodo.closest('table');
            if (tabla) pendientes.add(tabla);
            nodo.querySelectorAll('table').forEach(t => pendientes.add(t));
        }
        function ejecutar() {
            programado = false;
            observador.disconnect();
            pendientes.forEach(actualizar);
            pendientes.clear();
            observador.observe(document.body, opciones);
        }
        const observador = new MutationObserver(cambios => {
            cambios.forEach(c => { agregar(c.target); c.addedNodes.forEach(agregar); });
            if (pendientes.size && !programado) { programado = true; requestAnimationFrame(ejecutar); }
        });
        agregar(document.body);
        ejecutar();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar, {once:true});
    else iniciar();
})();
