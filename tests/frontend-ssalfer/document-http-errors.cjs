const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../frontend-ssalfer/js/api/cliente.js'), 'utf8');
function client(status, detail = null) {
  const window = { SSALFER_CONFIG: { API_BASE_URL: '/api' } };
  vm.runInNewContext(source, { window, document: { cookie: '' }, console, URLSearchParams,
    fetch: async () => ({ status, ok: false, headers: new Headers({ 'Content-Type': detail ? 'application/json' : 'text/html' }), json: async () => ({ detail }) }) });
  return window.ClienteAPI;
}
for (const [status, fragment] of [[413, 'tamaño permitido'], [429, 'demasiados intentos'], [502, 'no está disponible'], [503, 'no está disponible'], [504, 'tardó demasiado'], [507, 'almacenar']]) {
  test(`Respuesta HTML ${status} conserva el código y explica la acción`, async () => {
    await assert.rejects(client(status).get('/prueba'), error => error.status === status && error.message.includes(fragment));
  });
}
test('El detalle específico del backend tiene prioridad sobre el mensaje genérico', async () => {
  const detail = 'El contenido no corresponde a un formato documental permitido.';
  await assert.rejects(client(422, detail).post('/documentos/1/versiones', null), error => error.status === 422 && error.message === detail);
});
