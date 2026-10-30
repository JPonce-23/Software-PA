# Imagen de producción del frontend SSALFER.
#
# Es un sitio 100% estático (HTML/CSS/JS puro, sin build step de
# npm/vite), así que la imagen solo copia los archivos a nginx y
# usa nginx.conf para servirlos y para reenviar /api/ al backend
# (mismo origen, necesario para las cookies __Host- de sesión).
#
# Construir (desde la carpeta "connected/"):
#   docker build -f deploy/Dockerfile -t ssalfer-frontend .
#
# Ya viene integrado en docker-compose.ssalfer.yml, así que en la
# práctica no hace falta correr este comando a mano: ver
# ENTREGA.md / DEPLOY.md para el flujo completo con Docker Desktop.

FROM nginx:1.27-alpine

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

# Sólo recursos de la aplicación. Documentación, QA y configuración operativa
# quedan fuera del document root; no se depende de borrarlos tras COPY global.
COPY Index.html dashboard.html /usr/share/nginx/html/
COPY pages /usr/share/nginx/html/pages/
COPY js /usr/share/nginx/html/js/
COPY styles /usr/share/nginx/html/styles/
COPY img /usr/share/nginx/html/img/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
