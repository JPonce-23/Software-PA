"""Offline build-policy checks; these do not attest that a native image was built."""
import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('gdal_check', ROOT/'backend/native/check-gdal.py')
check = importlib.util.module_from_spec(spec);spec.loader.exec_module(check)

class FixedBuildTests(unittest.TestCase):
    def fixture(self):
        return ('GDAL 3.13.3, released 2026/08/18', '\n'.join(f'  {d} -vector- (rw+v): fixture' for d in ['GeoJSON','GeoJSONSeq','KML','LIBKML','GPKG','ESRI Shapefile','SQLite']), 'libgdal.so => /opt/gdal/lib/libgdal.so.39')
    def test_positive_and_missing_required_driver(self):
        v,f,l=self.fixture();self.assertIn('GPKG',check.verify(v,f,l))
        with self.assertRaises(ValueError):check.verify(v,f.replace('LIBKML','Absent'),l)
    def test_vulnerable_version_and_unexpected_linkage_fail(self):
        v,f,l=self.fixture()
        for vv,ll in [('GDAL 3.10.3',l),(v,'libgdal.so => /lib/libgdal.so.36'),(v,l+' not found')]:
            with self.subTest(v=vv,l=ll), self.assertRaises(ValueError):check.verify(vv,f,ll)
    def test_disabled_drivers_cannot_reappear(self):
        v,f,l=self.fixture()
        for d in ['netCDF','HDF4','HDF5','OGR_VRT','FlatGeobuf']:
            with self.subTest(d=d),self.assertRaises(ValueError):check.verify(v,f+'\n'+d+' -vector- (ro): bad',l)
    def test_fixed_source_and_required_build_options(self):
        s=(ROOT/'backend/native/build-gdal.sh').read_text()
        self.assertIn('5e0c388d83da2d686cc00a40272882432cdb54edff43d4af173e532844a0a0ea',s)
        self.assertIn('sha256sum -c -',s)
        for d in ['GEOJSON','SHAPE','KML','LIBKML','SQLITE','GPKG']:self.assertIn('-DOGR_ENABLE_DRIVER_'+d+'=ON',s)
        for d in ['NETCDF','HDF4','HDF5','CURL']:self.assertIn('-DGDAL_USE_'+d+'=OFF',s)
        self.assertNotIn('gdal-bin',(ROOT/'backend/Dockerfile').read_text())
if __name__ == '__main__':unittest.main()
