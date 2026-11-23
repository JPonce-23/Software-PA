#!/bin/sh
# Run only on a previously authorized disposable engine, never the existing daemon.
set -eu
archive=${1:?Pass frozen pa5-validated-image.tar}
test "${PA5_DISPOSABLE_ENGINE_APPROVED:-}" = yes
# Refuse existing resources; never remove them to manufacture a clean engine.
# Assign separately so a failed discovery command cannot look like an empty store.
images=$(docker image ls -aq)
containers=$(docker ps -aq)
volumes=$(docker volume ls -q)
test -z "$images"
test -z "$containers"
test -z "$volumes"
docker info --format '{{json .DriverStatus}}' | python3 -c 'import json,sys; assert ["driver-type","io.containerd.snapshotter.v1"] in json.load(sys.stdin)'
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT HUP INT TERM
python3 -B "$script_dir/validar-pa5-oci.py" "$archive" --store "$temporary/oci" > "$temporary/archive-report.json"
# This frozen docker-save archive includes OCI metadata + manifest.json; preserve index.
docker image load --input "$archive"
reference=software-pa-libgdal36-candidate:20261117-pa5@sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c
sh "$script_dir/verificar-pa5-engine.sh" "$reference"
