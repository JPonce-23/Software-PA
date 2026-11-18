#!/bin/bash
# Only on a fresh GitHub-hosted disposable runner; never the deployment Engine.
set -euo pipefail
image=$1
expected_config=$2
qa_dir=$(cd -- "$(dirname -- "$0")" && pwd)
[[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_ENVIRONMENT:-}" == github-hosted ]]
docker image inspect "$image" > inspect.json
python3 - "$expected_config" "$image" "$qa_dir" <<'PY'
import json,sys
from pathlib import Path
row=json.loads(Path('inspect.json').read_text())[0]
expected_ids={sys.argv[1]}
if '@sha256:' in sys.argv[2]: expected_ids.add(sys.argv[2].split('@')[1])
assert row['Id'] in expected_ids
catalog=json.loads((Path(sys.argv[3])/'pa5-supply-catalog.json').read_text())
assert row['RootFS']=={'Type':'layers','Layers':catalog['rootfs_diff_ids']}
assert row['Os']=='linux' and row['Architecture']=='amd64'
assert row['Config']['Labels']['org.opencontainers.image.version']=='3.10.3+dfsg-1+pa5'
assert row['Config']['Labels']['org.opencontainers.image.source']=='https://github.com/JPonce-23/Software-PA'
assert row['Config']['Labels']['org.opencontainers.image.revision']=='ae9cd6021b15d45f4091ab9854d394348cacfbc0'
PY
docker run --rm --pull never --network none --read-only --user postgres \
  --cap-drop ALL --security-opt no-new-privileges --memory 768m --cpus 2 --pids-limit 128 \
  --tmpfs /tmp:rw,nosuid,nodev,size=512m,mode=1777 \
  --mount "type=bind,src=$qa_dir,dst=/qa,readonly" \
  --entrypoint /bin/sh "$image" /qa/pa5-native-smoke.sh
# Full installed package inventory and dynamic ABI dependencies enter the evidence.
docker run --rm --pull never --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --entrypoint /bin/sh "$image" -ec \
  'dpkg --audit; dpkg-query -W; ldd /usr/lib/x86_64-linux-gnu/libgdal.so.36; ldd /usr/lib/postgresql/15/lib/postgis_raster-3.so' > packages-and-linkage.txt
! grep -F 'not found' packages-and-linkage.txt
