// SS-01: real map functions and Leaflet's content renderer, with DOM/API doubles.
// Reads local sources only. No browser, network, database, dependencies or files written.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const normalizeSource = require('./helpers/source.cjs');
const root = path.resolve(__dirname, '../..');
const source = normalizeSource(fs.readFileSync(path.join(root, 'frontend-ssalfer/js/mapa.js'), 'utf8'));

function section(text, start, end) {
    const first = text.indexOf(start), last = text.indexOf(end, first);
    assert(first >= 0 && last > first, `Missing source section: ${start}`);
    return text.slice(first, last);
}

// Fail on any attempt to treat an API label as HTML. Text consists of text nodes.
class Element {
    constructor(tag) { this.nodeType = 1; this.tagName = tag.toUpperCase(); this.childNodes = []; }
    set textContent(value) {
        const text = value == null ? '' : String(value);
        this.childNodes = text ? [{nodeType: 3, textContent: text}] : [];
    }
    get textContent() { return this.childNodes.map(node => node.textContent).join(''); }
    set innerHTML(value) { assert.fail('Tooltip content must never reach innerHTML'); }
    get firstChild() { return this.childNodes[0]; }
    hasChildNodes() { return this.childNodes.length > 0; }
    appendChild(node) { this.childNodes.push(node); return node; }
    append(...nodes) { nodes.forEach(node => this.appendChild(node)); }
    removeChild(node) { this.childNodes.splice(this.childNodes.indexOf(node), 1); }
}

// This exact, inspected Leaflet 1.9.4 method assigns strings to innerHTML and
// appends DOM elements instead. Execute only that method, not the whole vendor.
const leaflet = fs.readFileSync(path.join(root, 'frontend-ssalfer/js/vendor/leaflet-1.9.4/leaflet.js'), 'utf8');
const rendererSource = section(leaflet, '_updateContent:function()', ',_updatePosition:')
    .slice('_updateContent:'.length);
const updateContent = vm.runInNewContext(`(${rendererSource})`);

function assertLiteralTooltip(node, expected) {
    assert(node instanceof Element, 'Leaflet must receive a DOM element, not an HTML string');
    assert.equal(node.tagName, 'SPAN');
    assert.equal(node.textContent, expected);
    assert(node.childNodes.every(child => child.nodeType === 3), 'Only text nodes inside the label');
    const container = new Element('div');
    container.textContent = 'Previous tooltip';
    const events = [];
    updateContent.call({_content: node, _contentNode: container, fire: event => events.push(event)});
    assert.equal(container.childNodes.length, 1);
    assert.equal(container.firstChild, node);
    assert.equal(container.textContent, expected);
    assert.deepEqual(events, ['contentupdate']);
}

const types = {
    parcela: 'Parcela',
    nucleo_agrario: 'Núcleo agrario',
    derecho_via_proyecto: 'Derecho de vía vigente',
};
const geometry = () => ({type: 'MultiPolygon', coordinates: [
    [[[-99.123456789, 20.123456789], [-99, 20], [-98, 20], [-99.123456789, 20.123456789]]],
]});
const feature = (tipo = 'parcela', nombre = 'Parcela 35') => ({
    type: 'Feature', id: `${tipo}:11`, geometry: geometry(),
    properties: {tipo, id: 11, nombre, superficie_afectada_ha: null},
});

function harness({parts = 1} = {}) {
    const calls = [], details = [], warnings = [], errors = [], groups = {}, indexes = {}, layers = [];
    for (const tipo of [...Object.keys(types), 'trazo_proyecto']) {
        groups[tipo] = {layers: [], addLayer(layer) { this.layers.push(layer); }};
        indexes[tipo] = new Map();
    }
    const project = {id_proyecto: 7, nombre_proyecto: '<b data-audit>Proyecto sintético</b>'};
    const context = vm.createContext({
        document: {createElement: tag => new Element(tag)},
        grupos: groups, capasPorTipoId: indexes, tokenCarga: 1, revisionDetalle: 0,
        mostrarDetalleFeature(f) { details.push(f); return Promise.resolve(); },
        limpiarSeleccionMapa() { calls.push('clear-selection'); },
        mostrarError(error) { errors.push(error); },
        console: {warn: (...args) => warnings.push(args), error: (...args) => errors.push(args)},
        window: {L: {geoJSON(data, options) {
            const vectorLayers = [];
            calls.push({data, options, style: options.style(data)});
            for (let i = 0; i < parts; i++) {
                const layer = {
                    handlers: {},
                    bindTooltip(content, tooltipOptions) {
                        this.content = content; this.tooltipOptions = tooltipOptions; return this;
                    },
                    on(event, handler) { this.handlers[event] = handler; return this; },
                };
                options.onEachFeature(data, layer);
                layers.push(layer);
                vectorLayers.push(layer);
            }
            return {eachLayer(callback) { vectorLayers.forEach(callback); }};
        }}},
    });
    for (const [start, end] of [
        ['    const ESTILOS =', '    const ESTILOS_SELECCION ='],
        ['    function valorPresente(', '    function numeroSeguro('],
        ['    function tipoLegible(', '    function obtenerIdProyectoUrl('],
        ['    function nombreProyecto(', '    function obtenerProyecto('],
        ['    function estiloParaFeature(', '    function aplicarEstiloACapas('],
        ['    function agregarFeature(', '    function ajustarMapaAGeometrias('],
    ]) vm.runInContext(section(source, start, end), context);
    return {context, project, calls, details, warnings, errors, groups, indexes, layers};
}

const labels = [
    ['legitimate label', 'Parcela 35'],
    ['accents and Unicode', 'Núcleo San José — vía Ñandú'],
    ['special characters', 'A & B < C > D "dobles" \'simples\''],
    ['literal entities', '&lt;b&gt;Parcela&lt;/b&gt; &amp;'],
    ['inert HTML markup', '<b data-audit="SS-01">Parcela sintética</b>'],
    ['whitespace', '   '],
    ['empty string', ''],
    ['null', null],
    ['missing value', undefined],
];

for (const [tipo, fallback] of Object.entries(types)) {
    for (const [name, label] of labels) test(`${tipo}: ${name} stays literal with the existing fallback`, () => {
        const h = harness(), input = feature(tipo, label);
        // Explicit undefined must remain missing rather than use feature()'s default.
        if (label === undefined) delete input.properties.nombre;
        const snapshot = JSON.stringify(input);
        assert.equal(h.context.agregarFeature(input, h.project), true);
        assert.equal(h.layers.length, 1);
        assertLiteralTooltip(h.layers[0].content, label || fallback);
        assert.equal(h.layers[0].tooltipOptions.sticky, true);
        assert.equal(JSON.stringify(input), snapshot, 'Labels must not mutate the API data');
        assert.deepEqual(h.warnings, []);
    });
}

test('geometry, styles, layer indexes and click detail are preserved for every published type', () => {
    for (const tipo of Object.keys(types)) {
        const h = harness({parts: 2}), input = feature(tipo, '<b data-audit>Texto</b>');
        const snapshot = JSON.stringify(input);
        assert.equal(h.context.agregarFeature(input, h.project), true);
        const {data, options, style} = h.calls[0];
        assert.equal(data.geometry, input.geometry);
        assert.equal(data.id, input.id);
        assert.equal(JSON.stringify(input), snapshot);
        assert.equal(data.properties.id_proyecto, h.project.id_proyecto);
        assert.equal(data.properties.nombre_proyecto, h.project.nombre_proyecto);
        assert.equal(data.properties.nombre, input.properties.nombre);
        assert.equal(data.properties.superficie_afectada_ha, null);
        assert.equal(options.style, h.context.estiloParaFeature);
        assert.equal(style, h.context.estiloParaFeature(input));
        assert.deepEqual(h.groups[tipo].layers, h.layers);
        assert.deepEqual([...h.indexes[tipo].get(11)], h.layers);
        assert.notEqual(h.layers[0].content, h.layers[1].content, 'Each layer owns its label node');
        for (const layer of h.layers) {
            assertLiteralTooltip(layer.content, input.properties.nombre);
            assert.deepEqual(Object.keys(layer.handlers), ['click']);
            layer.handlers.click();
        }
        assert.deepEqual(h.details, [data, data]);
        assert.deepEqual(h.errors, []);
    }
});

test('click failures and stale-detail protection still follow the existing interaction flow', async () => {
    for (const stale of [null, 'project', 'selection']) {
        const h = harness();
        h.context.mostrarDetalleFeature = () => {
            // The real detail function increments revisionDetalle when selecting.
            h.context.revisionDetalle++;
            return Promise.reject(new Error('Fallo sintético'));
        };
        h.context.agregarFeature(feature(), h.project);
        h.layers[0].handlers.click();
        if (stale === 'project') h.context.tokenCarga++;
        if (stale === 'selection') h.context.revisionDetalle++;
        await new Promise(resolve => setImmediate(resolve));
        assert.equal(h.calls.includes('clear-selection'), !stale);
        assert.equal(h.errors.length, stale ? 0 : 2);
    }
});

test('excluded traces and invalid/missing features do not add layers or tooltips', () => {
    for (const input of [null, {...feature(), properties: null}, {...feature(), geometry: null},
        {...feature(), properties: {tipo: 'parcela', id: ''}}, feature('unknown'), feature('trazo_proyecto')]) {
        const h = harness();
        assert.equal(h.context.agregarFeature(input, h.project), false);
        assert.deepEqual(h.layers, []);
        assert.deepEqual(h.calls, []);
    }
});

test('the real API/GeoJSON loader keeps geometry and literal labels, and discards stale projects', async () => {
    const h = harness(), urls = [];
    const data = {type: 'FeatureCollection', features: [
        ...Object.keys(types).map(tipo => feature(tipo, '<b data-audit>Etiqueta API</b>')),
        feature('trazo_proyecto'),
    ]};
    const snapshot = JSON.stringify(data);
    h.context.window.ClienteAPI = {get: async url => { urls.push(url); return data; }};
    vm.runInContext(section(source, '    async function obtenerMapaProyecto(',
        '    async function obtenerNucleosProyecto('), h.context);
    vm.runInContext(section(source, '    async function cargarMapaDeProyecto(',
        '    /* =====================================================\n       RESUMEN DEL PROYECTO'), h.context);
    const result = await h.context.cargarMapaDeProyecto(h.project, 1);
    assert.deepEqual(urls, ['/proyectos/7/mapa']);
    assert.equal(result.total, 3);
    assert.equal(result.agregadas, 3);
    assert.equal(result.geojson, data);
    assert.equal(JSON.stringify(data), snapshot);
    for (const [i, tipo] of Object.keys(types).entries()) {
        assert.equal(h.calls[i].data.geometry, data.features[i].geometry);
        assert.deepEqual(h.groups[tipo].layers, [h.layers[i]]);
        assertLiteralTooltip(h.layers[i].content, data.features[i].properties.nombre);
    }
    h.context.tokenCarga = 2;
    const stale = await h.context.cargarMapaDeProyecto(h.project, 1);
    assert.equal(stale.agregadas, 0);
    assert.equal(h.layers.length, 3);
});

test('coincidence preview labels from imported attributes also stay literal', async () => {
    const preview = section(source, '        const vista = new URLSearchParams(location.search)',
        '        /*\n         * Resumen administrativo.');
    for (const [, label] of labels) {
        const contents = [], nodes = [];
        const map = {}, data = {type: 'FeatureCollection', features: [feature('parcela', label)]};
        if (label === undefined) delete data.features[0].properties.nombre;
        const context = vm.createContext({URLSearchParams, location: {search: '?id_importacion=9&vista=coincidencias'},
            proyecto: {id_proyecto: 7}, cargaActual: 1, tokenCarga: 1, capaTemporal: null,
            mapaLeaflet: map, errores: [], resultadoMapa: {status: 'fulfilled', value: {geojson: data}},
            document: {createElement: tag => new Element(tag), querySelector: () => ({prepend: n => nodes.push(n)})},
            elementos: {}, window: {
                SSALFER_SESION_LISTA: Promise.resolve({user: {rol: 'geografo'}}),
                SSALFER_MAPA_CONCILIACION: {detalle() {}, coincidencias: async () => ({geo: data, sin: 0, ambiguos: 0})},
                L: {geoJSON(received, options) {
                    assert.equal(received, data);
                    options.onEachFeature(data.features[0], {bindTooltip: content => contents.push(content)});
                    return {addTo(target) { assert.equal(target, map); return this; }};
                }},
            }});
        await vm.runInContext(`(async () => {${preview}})()`, context);
        assert.equal(contents.length, 1);
        assertLiteralTooltip(contents[0], `${label} · previsualización de coincidencia`);
        assert.equal(nodes.length, 1);
        assert.equal(context.errores.length, 0);
    }
});

test('individual historical previews use only constant tooltip text and keep map bounds', async () => {
    const preview = section(source, '        const vista = new URLSearchParams(location.search)',
        '        /*\n         * Resumen administrativo.');
    for (const active of [true, false]) {
        const contents = [], nodes = [], fitted = [];
        const bounds = {isValid: () => true}, map = {fitBounds: value => fitted.push(value)};
        const data = feature('parcela', '<b data-audit>Etiqueta de origen</b>');
        const context = vm.createContext({URLSearchParams,
            location: {search: '?id_importacion=9&id_feature=11&incluir_inactivas=true'},
            proyecto: {id_proyecto: 7}, cargaActual: 1, tokenCarga: 1, capaTemporal: null,
            mapaLeaflet: map, errores: [], resultadoMapa: {status: 'fulfilled', value: {geojson: {}}},
            document: {createElement: tag => new Element(tag), querySelector: () => ({prepend: n => nodes.push(n)})},
            elementos: {}, window: {
                SSALFER_SESION_LISTA: Promise.resolve({user: {rol: 'geografo'}}),
                GeoespacialAPI: {
                    obtener: async () => ({id_proyecto: 7, activo: active, nombre: data.properties.nombre}),
                    geometria: async () => data,
                },
                L: {geoJSON(received) {
                    assert.equal(received, data);
                    return {addTo(target) { assert.equal(target, map); return this; },
                        bindTooltip: content => contents.push(content), getBounds: () => bounds};
                }},
            }});
        await vm.runInContext(`(async () => {${preview}})()`, context);
        const expected = active ? 'Previsualización, aún no confirmada · capa temporal'
            : 'Importación dada de baja · Geometría histórica de sólo lectura · capa temporal';
        assert.deepEqual(contents, [expected]);
        assert.equal(nodes[0].textContent, expected);
        assert.deepEqual(fitted, [bounds]);
        assert.equal(context.errores.length, 0);
    }
});
