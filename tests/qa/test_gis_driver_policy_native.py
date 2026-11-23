"""Native GDAL regressions. Synthetic files only; no DB, network or exploits.

Run explicitly in the backend image: python -B -m unittest discover -s tests/qa
-p test_gis_driver_policy_native.py -v. Deliberately outside offline CI discovery.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from app.services import gis_ingestion as ing


class NativeDriverPolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'legitimate.geojson'
        self.source.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'name': 'Sintético ñ'},
             'geometry': {'type': 'Point', 'coordinates': [-99, 20]}}]}))

    def convert_fixture(self, driver, suffix):
        target = self.root / ('legitimate.' + suffix)
        subprocess.run(['ogr2ogr', '-f', driver, str(target), str(self.source)],
                       check=True, capture_output=True, timeout=30,
                       env=ing._gdal_environment())
        return target

    def assert_rejected(self, path):
        with self.assertRaises(ing.IngestionError) as caught:
            ing.inspect_dataset(path)
        self.assertEqual(caught.exception.code, 'CONVERSION_OGR_FALLIDA')
        # Exercise the second open too, bypassing inspection with benign metadata.
        dataset = ing.inspect_dataset(self.source)
        with self.assertRaises(ing.IngestionError) as caught:
            list(ing.iter_features(path, dataset))
        self.assertEqual(caught.exception.code, 'CONVERSION_OGR_FALLIDA')

    def test_allowed_gis_formats_round_trip(self):
        paths = [('geojson', self.source)]
        paths.extend((fmt, self.convert_fixture(driver, suffix)) for fmt, driver, suffix in [
            ('kml', 'KML', 'kml'), ('kml', 'LIBKML', 'libkml.kml'), ('gpkg', 'GPKG', 'gpkg'),
            ('shp', 'ESRI Shapefile', 'shp')])
        for fmt, path in paths:
            with self.subTest(fmt=fmt):
                dataset = ing.inspect_dataset(path)
                self.assertEqual(dataset.format, fmt)
                features = list(ing.iter_features(path, dataset))
                self.assertEqual(len(features), 1)
                self.assertEqual(features[0][1]['geometry']['coordinates'][:2], [-99, 20])

    def test_allowed_formats_with_malformed_content_fail_closed(self):
        for suffix in ['geojson', 'kml', 'gpkg', 'shp']:
            with self.subTest(suffix=suffix):
                path = self.root / ('broken.' + suffix)
                path.write_bytes(b'benign truncated synthetic file')
                self.assert_rejected(path)

    def test_unneeded_drivers_are_not_compiled(self):
        # Unlike the vulnerable full package, the fixed minimal build must not
        # register these parsers even without the runtime GDAL_SKIP setting.
        env = dict(ing._gdal_environment());env.pop('GDAL_SKIP')
        for driver in ['netCDF','HDF4','HDF5','FlatGeobuf','CSV','OGR_VRT']:
            with self.subTest(driver=driver):
                control = subprocess.run(['ogrinfo','--format',driver], env=env,
                    capture_output=True, timeout=30)
                self.assertNotEqual(control.returncode,0)

    def test_vrt_and_disguised_csv_cannot_delegate_or_bypass(self):
        vrt = self.root/'delegating.vrt'
        vrt.write_text(f'<OGRVRTDataSource><OGRVRTLayer name="legitimate">'
            f'<SrcDataSource>{self.source}</SrcDataSource>'
            '</OGRVRTLayer></OGRVRTDataSource>')
        self.assert_rejected(vrt)
        csv = self.root/'disguised.gpkg';csv.write_text('name,x,y\nfixture,-99,20\n')
        self.assert_rejected(csv)

    def test_both_native_processes_receive_policy_before_input(self):
        original = ing.subprocess.Popen
        with patch.object(ing.subprocess, 'Popen', wraps=original) as launch:
            dataset = ing.inspect_dataset(self.source)
            list(ing.iter_features(self.source, dataset))
        self.assertEqual(launch.call_count, 2)
        for call in launch.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[1:11], [arg for d in ing.INPUT_DRIVERS for arg in ('-if', d)])
            self.assertLess(argv.index('-if'), argv.index(str(self.source)))
            self.assertEqual(call.kwargs['env']['GDAL_SKIP'], 'netCDF')


if __name__ == '__main__':
    unittest.main()
