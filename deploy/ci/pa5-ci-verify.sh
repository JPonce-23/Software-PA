#!/bin/sh
# Consumer only. Run after explicit approval on a certified disposable CI Engine.
set -eu
test "${PA5_RUNNER_APPROVED:-}" = yes
: "${PA5_PROTECTED_ENGINE_ID:?Supply the protected main Engine ID for comparison}"
: "${PA5_APPROVED_REMOTE_DIGEST:?Publication must be independently verified first}"
: "${PA5_REQUESTED_REMOTE_DIGEST:?Pass the manually requested digest}"
: "${PA5_SKOPEO_SHA256:?Pin the reviewed preinstalled skopeo binary}"
: "${REGISTRY_TOKEN:?A read-only consumer token is required}"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=$(python3 -B "$script_dir/pa5_supply.py" reference "$PA5_APPROVED_REMOTE_DIGEST" "$PA5_REQUESTED_REMOTE_DIGEST")
temporary=$(mktemp -d)
container_name=pa5-ci-$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
pulled=no
engine_approved=no
verified_engine_id=
cleanup() {
  pa5_exit_code=$?
  pa5_cleanup_error=0
  if [ "$engine_approved" = yes ]; then
    pa5_cleanup_engine_id=$(docker info --format '{{.ID}}') || pa5_cleanup_error=1
    if [ "$pa5_cleanup_engine_id" = "$verified_engine_id" ]; then
      if docker container inspect "$container_name" >/dev/null 2>&1; then
        docker rm -fv "$container_name" >/dev/null || pa5_cleanup_error=1
      fi
      if [ "$pulled" = yes ]; then docker image rm "$image" >/dev/null || pa5_cleanup_error=1; fi
    else
      echo 'Engine identity unavailable or changed; refusing Docker cleanup.' >&2
      pa5_cleanup_error=1
    fi
  fi
  # Always remove temporary authentication, even if Docker cleanup failed.
  rm -rf "$temporary" || pa5_cleanup_error=1
  trap - EXIT
  if [ "$pa5_exit_code" -ne 0 ]; then exit "$pa5_exit_code"; fi
  exit "$pa5_cleanup_error"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
# Independent identity, approved platform/store and genuinely empty resources.
docker info --format '{{json .}}' > "$temporary/engine.json"
# Separate commands preserve a nonzero discovery status under set -e.
docker image ls -aq > "$temporary/images"
docker ps -aq > "$temporary/containers"
docker volume ls -q > "$temporary/volumes"
python3 -B "$script_dir/pa5_supply.py" engine "$temporary/engine.json" "$PA5_PROTECTED_ENGINE_ID" "$(cat "$temporary/images")" "$(cat "$temporary/containers")" "$(cat "$temporary/volumes")"
verified_engine_id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ID"])' "$temporary/engine.json")
skopeo_binary=$(command -v skopeo)
printf '%s  %s\n' "$PA5_SKOPEO_SHA256" "$skopeo_binary" | sha256sum -c -
skopeo --version
docker version --format '{{.Server.Version}}'
# Auth is temporary and never printed; no write-capable credentials belong here.
export DOCKER_CONFIG=$temporary/auth
mkdir -m 700 "$DOCKER_CONFIG"
# A changed config directory must never redirect later commands to another daemon.
test "$(docker info --format '{{.ID}}')" = "$verified_engine_id"
engine_approved=yes
printf '%s' "$REGISTRY_TOKEN" | docker login ghcr.io -u "${GITHUB_ACTOR:?}" --password-stdin
unset REGISTRY_TOKEN
# Independent registry download to OCI files; no mutable tags, no conversion fallback.
skopeo copy --all --preserve-digests --authfile "$DOCKER_CONFIG/config.json" "docker://$image" "oci:$temporary/received:pa5-received"
python3 -B "$script_dir/pa5_supply.py" layout "$temporary/received" "$PA5_APPROVED_REMOTE_DIGEST"
docker pull "$image"
pulled=yes
docker image inspect "$image" > "$temporary/inspect.json"
python3 -B "$script_dir/pa5_supply.py" inspect "$temporary/inspect.json" "$PA5_APPROVED_REMOTE_DIGEST"
# No host ports, no network, no application env or institutional mounts.
docker run --rm --pull never --name "$container_name" --network none --read-only \
  --user postgres --cap-drop ALL --security-opt no-new-privileges \
  --memory 768m --cpus 2 --pids-limit 128 \
  --tmpfs /tmp:rw,nosuid,nodev,size=512m,mode=1777 \
  --mount "type=bind,src=$script_dir,dst=/qa,readonly" \
  --entrypoint /bin/sh "$image" /qa/pa5-native-smoke.sh
printf '%s\n' 'PA5_REGISTRY_DOWNLOAD_IDENTITY_AND_SYNTHETIC_SMOKE_OK'
