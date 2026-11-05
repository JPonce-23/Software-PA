const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '../..');

test('SSALFER conserva URL de descarga y solicita el blob original', async () => {
  const calls = [], clicked = [], revoked = [];
  const payload = new Blob([new Uint8Array([0, 255, 65])]);
  const window = { ClienteAPI: { API_BASE_URL: '/api',
    get: async (...args) => { calls.push(args); return payload; }, post(){}, patch(){}, del(){} } };
  const document = { createElement: () => ({ click(){ clicked.push([this.href, this.download]); } }) };
  const URL = { createObjectURL: blob => { assert.equal(blob, payload); return 'blob:synthetic'; },
    revokeObjectURL: url => revoked.push(url) };
  const context = { window, document, URL, console, setTimeout: callback => callback() };
  vm.runInNewContext(fs.readFileSync(path.join(root,'frontend-ssalfer/js/api/documentos.js'),'utf8'),context);
  vm.runInNewContext(fs.readFileSync(path.join(root,'frontend-ssalfer/js/utils/gestion.js'),'utf8'),context);
  assert.equal(window.DocumentosAPI.urlDescargaVersion(7),'/api/documentos/versiones/7/descarga');
  await window.SSALFER_GESTION.descargar('/documentos/versiones/7/descarga','legitimo.pdf');
  assert.equal(calls[0][0],'/documentos/versiones/7/descarga');
  assert.equal(calls[0][1].tipoRespuesta,'blob');
  assert.deepEqual(clicked,[['blob:synthetic','legitimo.pdf']]);
  assert.deepEqual(revoked,['blob:synthetic']);
});

test('ClienteAPI conserva cookies y bytes binarios sin reinterpretar la respuesta', async () => {
  const binary = new Blob([new Uint8Array([0, 255, 66])]); let captured;
  const window = { SSALFER_CONFIG: { API_BASE_URL: '/api' } };
  vm.runInNewContext(fs.readFileSync(path.join(root,'frontend-ssalfer/js/api/cliente.js'),'utf8'), {
    window, document:{cookie:''}, console, URLSearchParams, Headers, FormData,
    fetch: async (url, options) => { captured = [url,options]; return { ok:true,status:200,
      headers:new Headers({'Content-Type':'application/octet-stream'}),blob:async()=>binary }; }
  });
  const result = await window.ClienteAPI.get('/documentos/versiones/7/descarga',{tipoRespuesta:'blob'});
  assert.equal(result,binary);assert.equal(captured[0],'/api/documentos/versiones/7/descarga');
  assert.equal(captured[1].credentials,'include');
  assert.equal(captured[1].method,'GET');
});
