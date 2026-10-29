#!/bin/sh
set -eu
(while sleep 3600; do nginx -t && nginx -s reload; done) &
