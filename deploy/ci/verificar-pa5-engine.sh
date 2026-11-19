#!/bin/sh
# Future clean-runner verification only. No services are started.
set -eu
reference=${1:?Pass the exact immutable reference consumed by Compose}
expected=sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c
case "$reference" in *@"$expected") ;; *) exit 2 ;; esac
docker info --format '{{json .DriverStatus}}' | python3 -c 'import json,sys; assert ["driver-type","io.containerd.snapshotter.v1"] in json.load(sys.stdin), "containerd store required; do not reconfigure daemon"'
temporary=$(mktemp -d)
container_id=
cleanup() {
  if [ -n "$container_id" ]; then docker rm -v "$container_id" >/dev/null; fi
  rm -rf "$temporary"
}
trap cleanup EXIT HUP INT TERM
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker image inspect "$reference" > "$temporary/inspect.json"
python3 - "$temporary/inspect.json" "$reference" "$script_dir/../../docs/security/ss09/native-pa5.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))[0];ref=sys.argv[2];expected='sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c'
assert r['Id']==expected and r['Descriptor']['digest']==expected
assert r['Os']=='linux' and r['Architecture']=='amd64'
repository=ref.split('@')[0];last=repository.rsplit('/',1)[-1]
if ':' in last:repository=repository.rsplit(':',1)[0]
assert repository+'@'+expected in r.get('RepoDigests',[]),'Compose repository digest missing'
catalog=json.load(open(sys.argv[3]))
assert r['RootFS']==catalog['image_identity']['rootfs']
PY
# docker create never starts the database; remove only its own container/volumes.
container_id=$(docker create --network none --entrypoint /bin/true "$reference")
docker cp "$container_id:/usr/lib/x86_64-linux-gnu/libgdal.so.36.3.10.3" "$temporary/libgdal.so.36.3.10.3"
printf '%s  %s\n' 10c9bc0c0bbafe2f16b51c130ad5f4ba2030c204cbbac5a271a79e6418abadeb "$temporary/libgdal.so.36.3.10.3" | sha256sum -c -
printf '%s\n' 'PA5_ENGINE_ID_PLATFORM_LIBRARY_COMPOSE_REFERENCE_OK'
