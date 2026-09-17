/**
 * env.js
 *
 * Punto ÚNICO de inyección de la URL del backend en producción.
 * Se carga ANTES de config.js en todas las páginas.
 *
 * En desarrollo local: deja window.SSALFER_API_URL sin definir
 * (o comentado) y config.js caerá de forma automática a
 * "http://localhost:8000/api".
 *
 * En producción, sustituye la línea de abajo por la URL real del
 * backend (debe ser el MISMO origen/dominio que sirve este frontend,
 * o estar detrás del mismo reverse proxy — ver notas de despliegue
 * en ENTREGA.md sobre cookies __Host- y CORS).
 *
 * Ejemplos de cómo definir esto en un despliegue real, en orden de
 * preferencia:
 *
 *   1) RECOMENDADO — usar este mismo despliegue con Docker
 *      (ver deploy/docker-compose.ssalfer.yml y DEPLOY.md): nginx
 *      sirve este frontend Y reenvía /api/ al backend, por lo que
 *      basta con una ruta relativa:
 *
 *        window.SSALFER_API_URL = "/api";
 *
 *   2) Generar este archivo en un pipeline de CI/CD a partir de una
 *      variable de entorno, p. ej.:
 *
 *        echo "window.SSALFER_API_URL = \"$SSALFER_API_URL\";" > js/env.js
 *
 *   3) Definirlo manualmente aquí antes de cada build, como último
 *      recurso:
 *
 *        window.SSALFER_API_URL = "https://ssalfer.pa.gob.mx/api";
 */

window.SSALFER_API_URL = "/api";
