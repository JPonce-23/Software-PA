"""Verify a built image's actual GDAL entrypoints/driver registration; no input files."""
import json
import re
import subprocess

def capture(*argv):
    return subprocess.check_output(argv, text=True, timeout=20)

def verify(version, formats, linked):
    if not re.search(r'GDAL 3\.13\.3(?:,|\s)', version):
        raise ValueError('unexpected GDAL build')
    drivers = {line.strip().split(' -', 1)[0] for line in formats.splitlines() if ' -' in line}
    required = {'GeoJSON', 'GeoJSONSeq', 'KML', 'LIBKML', 'GPKG', 'ESRI Shapefile', 'SQLite'}
    if not required <= drivers:
        raise ValueError('required vector driver missing')
    if drivers & {'netCDF', 'HDF4', 'HDF4Image', 'HDF5', 'HDF5Image', 'OGR_VRT', 'FlatGeobuf'}:
        raise ValueError('unreviewed parser registered')
    if 'not found' in linked or '/opt/gdal/lib/libgdal.so' not in linked:
        raise ValueError('unexpected GDAL linkage')
    return sorted(drivers)

if __name__ == '__main__':
    version = capture('ogrinfo', '--version')
    linked = capture('ldd', '/opt/gdal/bin/ogr2ogr')
    drivers = verify(version, capture('ogrinfo', '--formats'), linked)
    print(json.dumps({'marker': 'GDAL_NATIVE_OK', 'version': version.strip(), 'drivers': drivers}))
