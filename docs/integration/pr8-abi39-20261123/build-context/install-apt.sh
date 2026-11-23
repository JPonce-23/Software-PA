#!/bin/sh
set -eu
role=$1
. /etc/os-release
test "$ID" = debian && test "$VERSION_CODENAME" = trixie
test "$(dpkg --print-architecture)" = amd64
mkdir -p /tmp/apt-proof/lists /tmp/apt-proof/archives
cp -a /supply/apt/$role/lists/. /tmp/apt-proof/lists/
cp -a /supply/apt/$role/archives/. /tmp/apt-proof/archives/
python - "$role" <<'CHECK'
import hashlib,json,sys
from pathlib import Path
r=Path('/supply/apt')/sys.argv[1]
for row in json.loads((r/'downloaded-debs.json').read_text()):
 p=r/'archives'/row['filename'];assert p.stat().st_size==row['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
CHECK
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
set -- $(cat /supply/apt/$role/packages.lock)
DEBIAN_FRONTEND=noninteractive apt-get -o APT::Sandbox::User=root -o Dir::Etc::sourcelist=/supply/apt/$role/sources.list -o Dir::Etc::sourceparts=- -o Dir::State::lists=/tmp/apt-proof/lists -o Dir::Cache::archives=/tmp/apt-proof/archives --assume-yes --no-download --no-install-recommends install "$@"
rm -rf /tmp/apt-proof
