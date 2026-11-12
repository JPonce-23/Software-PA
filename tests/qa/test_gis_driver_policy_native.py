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
            ('kml', 'KML', 'kml'), ('gpkg', 'GPKG', 'gpkg'),
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

    def test_valid_forbidden_formats_and_disguised_extension_are_rejected(self):
        for driver, suffix in [('FlatGeobuf', 'fgb'), ('CSV', 'csv')]:
            path = self.convert_fixture(driver, suffix)
            # Positive control: the same binary can open this benign fixture.
            result = subprocess.run(['ogrinfo', '-ro', '-so', '-al', '-json', str(path)],
                                    capture_output=True, check=True, timeout=30,
                                    env=ing._gdal_environment())
            self.assertEqual(json.loads(result.stdout)['driverShortName'], driver)
            self.assert_rejected(path)
            disguised = path.with_suffix('.gpkg')
            disguised.write_bytes(path.read_bytes())
            self.assert_rejected(disguised)

    def test_vrt_cannot_delegate_to_an_allowed_file(self):
        path = self.root / 'delegating.vrt'
        path.write_text(f'<OGRVRTDataSource><OGRVRTLayer name="legitimate">'
                        f'<SrcDataSource>{self.source}</SrcDataSource>'
                        '</OGRVRTLayer></OGRVRTDataSource>')
        subprocess.run(['ogrinfo', '-ro', '-so', str(path)], check=True,
                       capture_output=True, timeout=30, env=ing._gdal_environment())
        self.assert_rejected(path)

    def test_netcdf_is_unregistered_before_any_user_file_is_opened(self):
        # No NetCDF payload is needed: verify registration without opening input.
        env = ing._gdal_environment()
        baseline = dict(env)
        baseline.pop('GDAL_SKIP')
        command = ['ogrinfo', '--format', 'netCDF']
        control = subprocess.run(command, env=baseline, capture_output=True, timeout=30)
        self.assertEqual(control.returncode, 0, control.stderr)
        blocked = subprocess.run(command, env=env, capture_output=True, timeout=30)
        self.assertNotEqual(blocked.returncode, 0)

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
