#!/bin/sh
# Dedicated build stage only. Native validation is mandatory before acceptance.
set -eu
cd /tmp
for file in 'gdal_3.10.3+dfsg-1.dsc' 'gdal_3.10.3+dfsg.orig.tar.xz' 'gdal_3.10.3+dfsg-1.debian.tar.xz'; do
  curl --fail --location --proto '=https' --tlsv1.2 --retry 3 "https://deb.debian.org/debian/pool/main/g/gdal/$file" -o "$file"
done
sha256sum -c <<'HASH'
748ae62ac5c542e3ee3cf527efc97404dc34ea3cc836288bb7d5abb01ecef1f8  gdal_3.10.3+dfsg-1.dsc
5ef1d6bf67d9d4d9394f90c96b9873e60aeed7e44b04df04ffd777b3c79c9588  gdal_3.10.3+dfsg.orig.tar.xz
1b65b043df16ce17614735f20d46f8f52c237b9d7dcf2fea51e62c7ccb7a4877  gdal_3.10.3+dfsg-1.debian.tar.xz
HASH
keyring=/usr/share/keyrings/debian-keyring.pgp
if [ ! -f "$keyring" ]; then keyring=/usr/share/keyrings/debian-keyring.gpg; fi
gpgv --keyring "$keyring" gdal_3.10.3+dfsg-1.dsc
dpkg-source -x gdal_3.10.3+dfsg-1.dsc /tmp/gdal36
python3 /opt/gdal36/prepare-source-pa4.py /tmp/gdal36 --debian
cd /tmp/gdal36
# Preserve Debian build flags, full driver set and ABI; package metadata must
# describe the installed patched library rather than a manually replaced .so.
# dpkg-source records the patch in quilt state before the binary package build.
DEBFULLNAME='Software-PA local QA' DEBEMAIL='qa@example.invalid' 
export DEBFULLNAME DEBEMAIL
dch --newversion '3.10.3+dfsg-1+pa4' --distribution UNRELEASED \
  'Local HDF-EOS enumeration/error contracts on preserved pa2 and pa3; see backport-pa4.json. Not an official Debian update.'
export DEB_CFLAGS_MAINT_APPEND='-g0' DEB_CXXFLAGS_MAINT_APPEND='-g0'
export DEB_BUILD_OPTIONS='parallel=2 noddebs'
dpkg-buildflags > /tmp/gdal-buildflags.txt
# Capture the actual ten source/header hashes while all three local quilt patches are applied.
mkdir -p /opt/gdal36-output/packages /opt/gdal36-output/provenance
python3 /opt/gdal36/prepare-source-pa4.py /tmp/gdal36 --verify-phase pa4 \
  --record /opt/gdal36-output/provenance/source-precompile-pa4.json
cp /tmp/gdal36/debian/patches/series /opt/gdal36-output/provenance/quilt-series-precompile.txt
cp /tmp/gdal36/.pc/applied-patches /opt/gdal36-output/provenance/quilt-applied-precompile.txt
cp /opt/gdal36/backport.json /opt/gdal36/backport-pa3.json /opt/gdal36/backport-pa4.json /opt/gdal36/*.patch /opt/gdal36-output/provenance/
dpkg-buildpackage -b -uc -us
# This separate record describes the source AFTER quilt unapply, never patched code.
python3 /opt/gdal36/prepare-source-pa4.py /tmp/gdal36 --verify-phase original \
  --record /opt/gdal36-output/provenance/source-after-quilt-unapply.json
# Only matching GDAL library/data/plugins enter runtime. Python/CLI/dev packages
# stay in the build stage and all artifacts remain available there for QA.
for pkg in libgdal36 gdal-data gdal-plugins; do
  cp /tmp/"${pkg}"_3.10.3+dfsg-1+pa4_*.deb /opt/gdal36-output/packages/
done
cp /tmp/gdal_3.10.3+dfsg-1+pa4_*.buildinfo /tmp/gdal_3.10.3+dfsg-1+pa4_*.changes /opt/gdal36-output/provenance/
dpkg-query -W -f='${binary:Package}\t${Version}\n' > /opt/gdal36-output/provenance/build-packages.tsv
cp /opt/gdal36/backport.json /tmp/gdal-buildflags.txt /opt/gdal36-output/provenance/
cp /tmp/gdal36/build-py*/CMakeCache.txt /opt/gdal36-output/provenance/
sha256sum /opt/gdal36-output/packages/*.deb > /opt/gdal36-output/provenance/packages.sha256
