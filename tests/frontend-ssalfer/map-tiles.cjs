// Real tile declarations and bundled Leaflet image creation, without network requests.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');

const leaflet = read('frontend-ssalfer/js/vendor/leaflet-1.9.4/leaflet.js');
const start = leaflet.indexOf('createTile:function(t,e){var i=document.createElement("img")');
const end = leaflet.indexOf(',getTileUrl:', start);
assert(start >= 0 && end > start, 'Locate bundled Leaflet tile creation');
const createTileSource = leaflet.slice(start + 'createTile:'.length, end);

for (const file of ['mapa.js', 'conciliacionGeoespacial.js']) {
    test(`${file}: Leaflet applies an origin-only referrer before requesting the canonical OSM tile`, () => {
        const source = read(`frontend-ssalfer/js/${file}`);
        const declarations = [...source.matchAll(/(?:window\.)?L\.tileLayer\([\s\S]*?\)\.addTo\(/g)];
        assert.equal(declarations.length, 1);
        let url, options;
        const L = { tileLayer(value, config) { url = value; options = config; } };
        vm.runInNewContext(declarations[0][0].replace(/\.addTo\($/, ''), { L, window: { L } });
        assert.equal(url, 'https://tile.openstreetmap.org/{z}/{x}/{y}.png');
        assert.match(options.attribution, /href="https:\/\/www.openstreetmap.org\/copyright"/);

        const assignments = [];
        const image = { set src(value) { assignments.push({ url: value, policy: this.referrerPolicy }); } };
        const createTile = vm.runInNewContext(`(${createTileSource})`, {
            document: { createElement(tag) { assert.equal(tag, 'img'); return image; } },
            S() {}, a() {} // Event binding does not affect request attributes.
        });
        const coords = { z: 9, x: 114, y: 226 };
        assert.equal(createTile.call({ options,
            getTileUrl: point => url.replace(/\{([zxy])\}/g, (_, key) => point[key])
        }, coords, () => {}), image);
        assert.deepEqual(assignments, [{
            url: 'https://tile.openstreetmap.org/9/114/226.png', policy: 'strict-origin'
        }]);
    });
}

test('Both proxies allow the canonical tile host while retaining the site-wide no-referrer policy', () => {
    for (const file of ['frontend-ssalfer/deploy/nginx.conf', 'deploy/tls/headers.conf']) {
        const config = read(file);
        assert.match(config, /add_header Referrer-Policy "no-referrer" always;/);
        const images = config.match(/img-src ([^;]+);/)[1].split(/\s+/);
        assert(images.includes('https://tile.openstreetmap.org'));
        assert(!images.includes('https://*.tile.openstreetmap.org'));
    }
});
