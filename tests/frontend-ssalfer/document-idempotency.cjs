const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const { webcrypto } = require('node:crypto');
const source = name => fs.readFileSync(path.join(__dirname, '../../frontend-ssalfer/js', name), 'utf8');

function context(extra = {}) {
  const window = { SSALFER_CONFIG: { API_BASE_URL: '/api' }, crypto: webcrypto, addEventListener() {}, ...extra };
  const document = { cookie: 'pa_csrf_dev=synthetic-csrf', addEventListener() {}, getElementById() { return null; }, querySelector() { return null; } };
  return vm.createContext({ window, document, console, URLSearchParams, Headers, FormData, File, Uint8Array, location: {}, ...extra.globals });
}

test('ClienteAPI conserva multipart y CSRF y envía la clave sólo cuando se solicita', async () => {
  const calls = [], ctx = context({ globals: { fetch: async (url, options) => {
    calls.push({ url, options }); return { ok: true, status: 201, headers: new Headers({ 'Content-Type': 'application/json' }), json: async () => ({ id_documento_version: 1 }) };
  } } });
  vm.runInContext(source('api/cliente.js'), ctx);
  const form = new FormData(); form.append('archivo', new File(['synthetic'], 'a.pdf'));
  const key = webcrypto.randomUUID();
  await ctx.window.ClienteAPI.post('/documentos/7/versiones', form, { idempotencyKey: key });
  assert.equal(calls[0].options.headers['Idempotency-Key'], key);
  assert.equal(calls[0].options.headers['X-CSRF-Token'], 'synthetic-csrf');
  assert.equal(calls[0].options.headers['Content-Type'], undefined);
  assert.equal(calls[0].options.body, form); assert.equal(calls[0].options.credentials, 'include');
  await ctx.window.ClienteAPI.post('/otra-operacion', { nombre: 'synthetic' });
  assert.equal(calls[1].options.headers['Idempotency-Key'], undefined);
});

test('DocumentosAPI reutiliza explícitamente una clave sin regenerarla por petición', async () => {
  const calls = [], ctx = context({ ClienteAPI: { post: async (...args) => { calls.push(args); return {}; } } });
  vm.runInContext(source('api/documentos.js'), ctx);
  const api = ctx.window.DocumentosAPI, key = api.nuevaClaveCarga();
  assert.match(key, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  await api.subirVersion(7, new FormData(), key); await api.subirVersion(7, new FormData(), key);
  assert.equal(calls[0][2].idempotencyKey, calls[1][2].idempotencyKey);
  await api.subirVersion(7, new FormData()); assert.equal(calls[2][2].idempotencyKey, null);
  assert.notEqual(key, api.nuevaClaveCarga());
});

test('Fallback UUID usa getRandomValues y fija versión y variante', () => {
  const ctx = context({ crypto: { getRandomValues: a => { a.fill(255); return a; } }, ClienteAPI: {} });
  vm.runInContext(source('api/documentos.js'), ctx);
  assert.equal(ctx.window.DocumentosAPI.nuevaClaveCarga(), 'ffffffff-ffff-4fff-bfff-ffffffffffff');
});

test('Sin CSPRNG se rechaza la carga, sin clave débil ni fallback silencioso', () => {
  const ctx = context({ crypto: {}, ClienteAPI: {} }); vm.runInContext(source('api/documentos.js'), ctx);
  assert.throws(() => ctx.window.DocumentosAPI.nuevaClaveCarga(), /clave segura/);
});

test('El guardar real del gestor conserva la clave tras error y cambia al seleccionar otro archivo', async () => {
  const calls = [], keys = [], fileA = new File(['A'], 'a.pdf'), fileB = new File(['B'], 'b.pdf');
  let rootClick, modalClick;
  const select = { value: '', disabled: false, selectedOptions: [{ textContent: 'QA' }],
    replaceChildren() {}, add() {}, addEventListener() {} };
  const tipo = { ...select }, registro = { ...select }, contenido = { replaceChildren() {} };
  const root = { isConnected: true, querySelector: s => s.includes('tipo') ? tipo : s.includes('registro') ? registro : contenido,
    addEventListener: (name, fn) => { rootClick = fn; } };
  const api = { listarPorEntidad: async () => [{ id_documento: 7, titulo: 'QA' }], listarVersiones: async () => [], nombreTipo: () => 'QA',
    nuevaClaveCarga: () => { const k = webcrypto.randomUUID(); keys.push(k); return k; },
    subirVersion: async (doc, payload, key) => { calls.push({ doc, key }); throw new Error('synthetic network failure'); } };
  const ctx = context({ DocumentosAPI: api, AuthAPI: { requerirSesion: async () => ({ user: { rol: 'admin' } }) },
    SSALFER_CONTEXTO: { nombres: { proyecto_nucleo: 'QA' }, crear: () => ({ listar: async () => [{ id: 1, etiqueta: 'QA' }] }) },
    SSALFER_FORMAT: { formatearFecha: () => '', etiquetaCodigo: s => s },
    SSALFER_GESTION: { e: s => s, boton: () => '', tabla: () => '', opciones: a => a,
      formulario: async options => {
        for (const archivo of [fileA, fileA, fileB]) { try { await options.guardar({ archivo }); } catch {} }
        return null;
      } },
    SSALFER_UI: { abrirModal: async options => options.preparar({ addEventListener: (name, fn) => { modalClick = fn; } }) },
    ClienteAPI: { mostrarErrorAPI: e => { throw e; } },
    globals: { Option: function (text, value) { this.value = value; this.text = text; } }
  });
  vm.runInContext(source('utils/gestorDocumentos.js'), ctx);
  await ctx.window.SSALFER_GESTOR_DOCUMENTOS.montar(root, 1);
  await rootClick({ target: { closest: () => ({ dataset: { gestion: 'versiones', registro: '7' } }) } });
  await modalClick({ target: { closest: () => ({ disabled: false, dataset: { gestion: 'subir' } }) } });
  assert.equal(calls.length, 3); assert.equal(keys.length, 2);
  assert.equal(calls[0].key, calls[1].key); assert.notEqual(calls[1].key, calls[2].key);
});

for (const [code, status, fragment] of [
  ['DOCUMENT_DUPLICATE', 409, 'ya está registrado'],
  ['DOCUMENT_IDEMPOTENCY_CONFLICT', 409, 'corresponde a otra carga'],
  ['DOCUMENT_RECONCILIATION_REQUIRED', 409, 'requiere revisión'],
  ['DOCUMENT_OPERATION_PENDING', 425, 'sigue pendiente'],
  ['DOCUMENT_OPERATION_REJECTED', 409, 'fue rechazada'],
  ['DOCUMENT_INTEGRITY_CONFLICT', 409, 'conflicto de integridad'],
  ['DOCUMENT_REQUEST_CONFLICT', 409, 'estado actual']
]) {
  test(`La carga interpreta ${code} conservando status, detail y clave`, async () => {
    const calls = [], detail = 'Un texto compatible que puede cambiar o traducirse.';
    const ctx = context({ globals: { fetch: async (url, options) => {
      calls.push({ url, options });
      return { ok: false, status, headers: new Headers({ 'Content-Type': 'application/json', 'X-Document-Error-Code': code }), json: async () => ({ detail }) };
    } } });
    vm.runInContext(source('api/cliente.js'), ctx);vm.runInContext(source('api/documentos.js'), ctx);
    const key = webcrypto.randomUUID();
    await assert.rejects(ctx.window.DocumentosAPI.subirVersion(7, new FormData(), key), error => {
      assert.equal(error.status, status);assert.equal(error.detail, detail);
      assert.equal(error.documentErrorCode, code);assert.ok(error.message.includes(fragment));
      assert.notEqual(error.message, detail);return true;
    });
    assert.equal(calls.length, 1);assert.equal(calls[0].options.headers['Idempotency-Key'], key);
  });
}

test('Sin cabecera o con código desconocido/inválido la carga conserva el detalle previo', async () => {
  for (const code of [null, 'DOCUMENT_UNKNOWN', '../../synthetic-path', '__proto__']) {
    const detail = 'Mensaje legado específico.';
    const ctx = context({ globals: { fetch: async () => ({ ok: false, status: 409,
      headers: new Headers({ 'Content-Type': 'application/json', ...(code ? { 'X-Document-Error-Code': code } : {}) }),
      json: async () => ({ detail }) }) } });
    vm.runInContext(source('api/cliente.js'), ctx);vm.runInContext(source('api/documentos.js'), ctx);
    await assert.rejects(ctx.window.DocumentosAPI.subirVersion(7, new FormData()), error => error.message === detail && error.detail === detail);
  }
});

test('Un código de carga no cambia mensajes de otras operaciones ni reclasifica un status incompatible', async () => {
  const detail = 'Mensaje que debe conservarse.';
  const ctx = context({ globals: { fetch: async () => ({ ok: false, status: 403,
    headers: new Headers({ 'Content-Type': 'application/json', 'X-Document-Error-Code': 'DOCUMENT_DUPLICATE' }), json: async () => ({ detail }) }) } });
  vm.runInContext(source('api/cliente.js'), ctx);vm.runInContext(source('api/documentos.js'), ctx);
  await assert.rejects(ctx.window.ClienteAPI.post('/otra-operacion', {}), error => error.status === 403 && error.message === detail);
  await assert.rejects(ctx.window.DocumentosAPI.subirVersion(7, new FormData()), error => error.status === 403 && error.message === detail);
});
