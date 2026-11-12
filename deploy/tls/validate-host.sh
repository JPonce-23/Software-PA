#!/bin/sh
set -eu
# Restrict values substituted into nginx syntax and redirects, including $/;/{}.
case "${PUBLIC_HOST:-}" in
  ""|*[!a-zA-Z0-9.-]*|.*|*.) echo "PUBLIC_HOST requiere un dominio o IPv4 sin esquema, ruta ni puerto" >&2; exit 1;;
esac
