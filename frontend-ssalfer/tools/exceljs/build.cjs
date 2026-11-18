'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const browserify = require('browserify');
const builtins = require('browserify/lib/builtins');
const uglify = require('uglify-js');
const acorn = require('acorn');
function dependencies(source) {
    const deps = new Set();
    const tree = acorn.parse(source, {ecmaVersion: 2022, allowReturnOutsideFunction: true, allowHashBang: true});
    function visit(node) {
        if (!node || typeof node !== 'object') return;
        if (node.type === 'CallExpression' && node.callee.type === 'Identifier' && node.callee.name === 'require' &&
            node.arguments.length === 1 && typeof node.arguments[0].value === 'string') deps.add(node.arguments[0].value);
        for (const value of Object.values(node)) {
            if (Array.isArray(value)) value.forEach(visit);
            else if (value && typeof value === 'object') visit(value);
        }
    }
    visit(tree);return [...deps];
}
const root = __dirname;
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const vendor = path.resolve(root, '../../js/vendor');
const output = path.join(vendor, 'exceljs-4.4.0-ssalfer.min.js');
const records = [];
const forbidden = new Set(['elliptic', 'crypto-browserify', 'browserify-sign', 'create-ecdh']);
// Browserify only resolves this unused default builtin; executing it fails closed.
// ExcelJS receives the explicit limited adapter below. No general signing/ECDH
// implementation is installed in the toolchain or shipped to the browser.
if (require.resolve('crypto-browserify') !== path.join(root, 'crypto-build-disabled/index.cjs')) {
    throw new Error('Unexpected general crypto implementation in build');
}
const b = browserify(path.join(root, 'entry.cjs'), {
    basedir: root, standalone: 'ExcelJS', detect: dependencies,
    builtins: {...builtins, crypto: path.join(root, 'crypto.cjs')},
});
b.on('dep', row => {
    records.push({file: path.relative(root, row.file).split(path.sep).join('/'), sha256: hash(row.source)});
});
b.bundle((error, source) => {
    if (error) throw error;
    const result = uglify.minify(source.toString(), {compress: true, mangle: true,
        output: {comments: /^!|@license/}});
    if (result.error) throw result.error;
    const bytes = Buffer.from('/*! ExcelJS 4.4.0; MIT. SSALFER build; see ExcelJS-build-LICENSES.txt and tools/exceljs. */\n' + result.code + '\n');
    const lockBytes = fs.readFileSync(path.join(root, 'package-lock.json'));
    const lock = JSON.parse(lockBytes);
    const packages = new Map();
    for (const record of records) {
        let dir = path.dirname(path.join(root, record.file));
        while (dir.startsWith(root + path.sep)) {
            const candidate = path.join(dir, 'package.json');
            if (fs.existsSync(candidate)) {
                const meta = JSON.parse(fs.readFileSync(candidate));
                if (meta.name && meta.version) break;
            }
            dir = path.dirname(dir);
        }
        if (!dir.includes(path.sep + 'node_modules' + path.sep)) continue;
        const meta = JSON.parse(fs.readFileSync(path.join(dir, 'package.json')));
        if (forbidden.has(meta.name)) throw new Error(`Forbidden runtime module: ${meta.name}`);
        const key = path.relative(root, dir).split(path.sep).join('/');
        const pinned = lock.packages[key];
        if (!pinned || pinned.version !== meta.version || !pinned.integrity || !pinned.resolved.startsWith('https://registry.npmjs.org/')) throw new Error(`Unverified lock entry: ${key}`);
        const license = fs.readdirSync(dir).find(name => /^(licen[cs]e|copying)(\.|$)/i.test(name));
        const readme = path.join(dir, 'README.md');
        const readmeText = fs.existsSync(readme) ? fs.readFileSync(readme, 'utf8') : '';
        let licenseText = license ? fs.readFileSync(path.join(dir, license), 'utf8') :
            (/^## License/m.test(readmeText) ? readmeText.slice(readmeText.search(/^## License/m)) : '');
        if (!licenseText) {
            const extra = JSON.parse(fs.readFileSync(path.join(root, 'license-sources.json')))[meta.name+'@'+meta.version];
            if (extra) {
                licenseText = fs.readFileSync(path.join(root, extra.file), 'utf8');
                if (hash(licenseText) !== extra.sha256) throw new Error('License integrity failure');
            }
        }
        if (!licenseText) throw new Error(`Missing license: ${meta.name}`);
        packages.set(key, {name: meta.name, version: meta.version, license: meta.license,
            integrity: pinned.integrity, resolved: pinned.resolved, text: licenseText});
    }
    const sorted = [...packages.values()].sort((a,b) => (a.name+'@'+a.version).localeCompare(b.name+'@'+b.version, 'en'));
    const licenses = sorted.map(p => `${p.name}@${p.version} (${JSON.stringify(p.license)})\n${p.text}`).join('\n\n---\n\n');
    const graph = JSON.stringify({schema_version: 1, artifact: path.basename(output), sha256: hash(bytes),
        package_lock_sha256: hash(lockBytes),
        build_inputs: Object.fromEntries(['package.json','build.cjs','crypto.cjs','entry.cjs','license-sources.json',
            'crypto-build-disabled/package.json','crypto-build-disabled/index.cjs'].map(name => [name, hash(fs.readFileSync(path.join(root,name)))])),
        modules: records.sort((a,b) => a.file.localeCompare(b.file,'en')),
        packages: sorted.map(({text,...p}) => p)}, null, 2)+'\n';
    const files = [[output, bytes], [path.join(vendor,'ExcelJS-build-LICENSES.txt'), licenses], [path.join(root,'runtime-graph.json'), graph]];
    for (const [file, content] of files) {
        if (process.argv.includes('--check')) {
            if (!fs.readFileSync(file).equals(Buffer.from(content))) throw new Error(`Non-reproducible: ${path.basename(file)}`);
        } else fs.writeFileSync(file, content);
    }
    console.log(`EXCELJS_BUILD_OK ${records.length} modules ${packages.size} packages ${hash(bytes)}`);
});
