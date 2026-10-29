FROM nginx:1.27-alpine
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY headers.conf /etc/nginx/security-headers.conf
COPY proxy.conf /etc/nginx/proxy-settings.conf
COPY validate-host.sh /docker-entrypoint.d/19-validate-host.sh
COPY run.sh /docker-entrypoint.d/40-certificate-reload.sh
RUN chmod 755 /docker-entrypoint.d/19-validate-host.sh /docker-entrypoint.d/40-certificate-reload.sh
CMD ["nginx", "-g", "daemon off;"]
