/**
 * env.js: configuración del cliente, cargada ANTES de config.js.
 * window.SSALFER_API_URL = "/api" conserva las peticiones en el mismo origen.
 * El Nginx oficial sirve los estáticos y reenvía /api/ al backend.
 * docker-compose.ssalfer.yml está en la raíz del repositorio; ver DEPLOY.md.
 * Las variables del contenedor no reescriben automáticamente este JS empaquetado.
 * Un cambio de configuración del cliente requiere actualizar el artefacto servido.
 */

window.SSALFER_API_URL = "/api";
