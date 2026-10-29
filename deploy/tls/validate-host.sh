#!/bin/sh
set -eu
case "${PUBLIC_HOST:-}" in
  ""|*[!a-zA-Z0-9.:-]*) echo "PUBLIC_HOST debe ser una IP o dominio, sin esquema ni ruta" >&2; exit 1;;
esac
case "$PUBLIC_HOST" in
  *:*) echo "Usa IPv4 o un dominio para esta configuración" >&2; exit 1;;
esac
