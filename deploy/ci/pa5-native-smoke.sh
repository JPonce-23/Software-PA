#!/bin/sh
# Only inside a disposable, network-none CI container. Never use project databases.
set -eu
export PATH=/usr/lib/postgresql/15/bin:$PATH
python3 - <<'PY'
import ctypes,hashlib,json,subprocess
from pathlib import Path
catalog=json.loads(Path('/qa/pa5-supply-catalog.json').read_text())
for name,wanted in catalog['protected_payloads'].items():
    assert hashlib.sha256(Path('/'+name).read_bytes()).hexdigest()==wanted,name
for package,version in catalog['package_versions'].items():
    assert subprocess.check_output(['dpkg-query','-W','-f=${Version}',package],text=True)==version,package
lib=ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libgdal.so.36.3.10.3')
lib.GDALVersionInfo.argtypes=[ctypes.c_char_p];lib.GDALVersionInfo.restype=ctypes.c_char_p
assert lib.GDALVersionInfo(b'RELEASE_NAME')==b'3.10.3'
lib.GDALAllRegister.argtypes=[];lib.GDALAllRegister.restype=None;lib.GDALAllRegister()
lib.GDALGetDriverByName.argtypes=[ctypes.c_char_p];lib.GDALGetDriverByName.restype=ctypes.c_void_p
lib.GDALCreate.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_char_p)];lib.GDALCreate.restype=ctypes.c_void_p
lib.GDALGetRasterBand.argtypes=[ctypes.c_void_p,ctypes.c_int];lib.GDALGetRasterBand.restype=ctypes.c_void_p
lib.GDALRasterIO.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int];lib.GDALRasterIO.restype=ctypes.c_int
lib.GDALClose.argtypes=[ctypes.c_void_p];lib.GDALClose.restype=None
driver=lib.GDALGetDriverByName(b'MEM');assert driver
dataset=lib.GDALCreate(driver,b'',2,2,1,1,None);assert dataset
try:
    band=lib.GDALGetRasterBand(dataset,1);assert band
    source=(ctypes.c_ubyte*4)(1,2,3,4);actual=(ctypes.c_ubyte*4)()
    assert lib.GDALRasterIO(band,1,0,0,2,2,source,2,2,1,0,0)==0
    assert lib.GDALRasterIO(band,0,0,0,2,2,actual,2,2,1,0,0)==0
    assert bytes(actual)==bytes(source)
finally:lib.GDALClose(dataset)
print('PA5_PACKAGES_CORE_LLVM_HASHES_AND_GDAL_MEM_SMOKE_OK')
PY
# PostgreSQL is bootstrapped only in private tmpfs; no TCP listener or project migrations.
temporary=$(mktemp -d /tmp/pa5-smoke.XXXXXX)
started=no
cleanup() {
  if [ "$started" = yes ]; then pg_ctl -D "$temporary/data" -m immediate -w stop >/dev/null; fi
  rm -rf "$temporary"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir "$temporary/socket"
initdb -D "$temporary/data" --auth-local=trust --auth-host=reject --no-locale > "$temporary/init.log"
pg_ctl -D "$temporary/data" -l "$temporary/server.log" -o "-F -h '' -k $temporary/socket -c listen_addresses='' -c shared_buffers=16MB -c max_connections=10 -c jit=on" -w start
started=yes
psql -X -h "$temporary/socket" -d postgres -v ON_ERROR_STOP=1 > "$temporary/sql.log" <<'SQL'
SET statement_timeout='15s';
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_raster;
DO $$ BEGIN
 IF current_setting('server_version_num')::int NOT BETWEEN 150000 AND 159999 THEN RAISE EXCEPTION 'PG15 required'; END IF;
 IF postgis_lib_version()<>'3.6.4' THEN RAISE EXCEPTION 'PostGIS3.6.4 required'; END IF;
 IF NOT pg_jit_available() THEN RAISE EXCEPTION 'LLVM JIT unavailable'; END IF;
 IF ST_SRID(ST_Transform(ST_SetSRID(ST_Point(-99,20),4326),3857))<>3857 THEN RAISE EXCEPTION 'transform'; END IF;
 IF NOT ST_Intersects(ST_Buffer(ST_Point(0,0),1),ST_Point(0,0)) THEN RAISE EXCEPTION 'synthetic geometry'; END IF;
END $$;
SET jit_above_cost=0;
SET jit_inline_above_cost=0;
SET jit_optimize_above_cost=0;
EXPLAIN (ANALYZE,COSTS ON,TIMING OFF,SUMMARY ON) SELECT sum(sqrt(i::double precision)) FROM generate_series(1,300) AS i;
SELECT 'PA5_POSTGIS_SYNTHETIC_SMOKE_OK';
SQL
cat "$temporary/sql.log"
grep -E 'Inlining[ :]+true' "$temporary/sql.log" >/dev/null
grep 'PA5_POSTGIS_SYNTHETIC_SMOKE_OK' "$temporary/sql.log" >/dev/null
printf '%s\n' 'PA5_NATIVE_SMOKE_OK'
