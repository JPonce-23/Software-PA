"""SS-02 stage 1: synthetic environment/OGR responses, no native child or services.
Run with unittest discovery outside backend/tests (never loads its DB conftest).
"""
import ast
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from test_gis_resource_limits import process_output, dataset, metadata, encoded, row
from app.services import gis_ingestion as ing


FIXED_KEYS = {
    'PATH', 'LANG', 'LC_ALL', 'TZ', 'HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME',
    'TMPDIR', 'CPL_TMPDIR', 'GDAL_CONFIG_FILE', 'PROJ_NETWORK',
    'GDAL_DISABLE_READDIR_ON_OPEN', 'CPL_VSIL_CURL_ALLOWED_EXTENSIONS',
    'CPL_CURL_VERBOSE', 'OGR_GEOJSON_MAX_OBJ_SIZE',
}
SECRET_NAMES = (
    'DB_RUNTIME_USER', 'DB_RUNTIME_PASSWORD', 'DATABASE_URL', 'PGPASSWORD',
    'POSTGRES_PASSWORD', 'POSTGRES_ADMIN_PASSWORD', 'SECRET_KEY', 'ADMIN_PASSWORD',
    'TEST_ADMIN_PASSWORD', 'PGADMIN_DEFAULT_PASSWORD', 'SESSION_TOKEN',
    'AUTH_COOKIE', 'AUTH_SECRET', 'INSTITUTIONAL_API_TOKEN', 'AWS_SECRET_ACCESS_KEY',
)


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def assert_restricted(self, env):
        self.assertEqual(set(env), FIXED_KEYS)
        self.assertTrue(set(SECRET_NAMES).isdisjoint(env))
        self.assertNotIn('SYNTHETIC-SECRET-ONLY', env.values())
        self.assertEqual(env['PROJ_NETWORK'], 'OFF')
        self.assertEqual(env['GDAL_CONFIG_FILE'], '/dev/null')

    def test_all_credentials_and_unknown_institutional_settings_excluded(self):
        with patch.dict(os.environ, {key: 'SYNTHETIC-SECRET-ONLY' for key in SECRET_NAMES}):
            self.assert_restricted(ing._gdal_environment())

    def test_exact_default_environment_without_inheritance(self):
        env = ing._gdal_environment()
        self.assert_restricted(env)
        self.assertEqual(env['PATH'], '/usr/local/bin:/usr/bin:/bin')
        self.assertEqual((env['LANG'], env['LC_ALL'], env['TZ']), ('C.UTF-8', 'C.UTF-8', 'UTC'))
        self.assertEqual(env['HOME'], '/nonexistent')
        self.assertEqual(env['XDG_CONFIG_HOME'], '/nonexistent')
        self.assertEqual(env['XDG_CACHE_HOME'], '/nonexistent')
        self.assertEqual((env['TMPDIR'], env['CPL_TMPDIR']), ('/tmp', '/tmp'))

    def test_only_optional_resource_paths_preserved(self):
        technical = {'GDAL_DATA': '/opt/gdal data', 'PROJ_DATA': '/opt/proj:/usr/share/proj',
                     'PROJ_LIB': '/opt/legacy-proj'}
        with patch.dict(os.environ, technical): env = ing._gdal_environment()
        self.assertEqual(set(env), FIXED_KEYS | set(technical))
        for key, value in technical.items(): self.assertEqual(env[key], value)

    def test_empty_optional_paths_use_compiled_package_defaults(self):
        with patch.dict(os.environ, dict.fromkeys(['GDAL_DATA', 'PROJ_DATA', 'PROJ_LIB'], '')):
            self.assert_restricted(ing._gdal_environment())

    def test_remote_relative_vsi_and_invalid_paths_rejected_without_values_in_error(self):
        for name in ['GDAL_DATA', 'PROJ_DATA', 'PROJ_LIB']:
            for value in ['relative/path', 'https://synthetic.invalid/data', '/vsicurl/remote',
                          '/local\x00invalid', '/local\ninvalid', ':/absolute']:
                with self.subTest(name=name, kind=repr(value)), patch.object(ing.os, 'getenv',
                        side_effect=lambda key, default=None: value if key == name else default):
                    with self.assertRaises(ing.IngestionError) as error: ing._gdal_environment()
                    self.assertEqual(error.exception.code, 'GDAL_CONFIG_INVALIDA')
                    self.assertNotIn(value, str(error.exception))

    def test_loader_proxy_plugin_config_and_locale_injections_not_forwarded(self):
        inherited = {k: 'SYNTHETIC-SECRET-ONLY' for k in (
            'PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'HOME', 'TMPDIR',
            'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'GDAL_CONFIG_FILE', 'GDAL_DRIVER_PATH',
            'OGR_DRIVER_PATH', 'PROJ_AUX_DB', 'PROJ_NETWORK_ENDPOINT', 'GDAL_HTTP_HEADERS',
            'CPL_CURL_HEADER_FILE', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'GDAL_SKIP',
            'OGR_SKIP', 'LANG', 'LC_ALL', 'TZ', 'PROJ_NETWORK', 'GDAL_VRT_ENABLE_PYTHON')}
        with patch.dict(os.environ, inherited): self.assert_restricted(ing._gdal_environment())

    def test_ss03_feature_limit_is_derived_not_inherited(self):
        with patch.dict(os.environ, {'IMPORT_GEOJSON_MAX_FEATURE_MB': '7',
                'IMPORT_MAX_FILE_SIZE_MB': '100', 'OGR_GEOJSON_MAX_OBJ_SIZE': '0'}):
            env = ing._gdal_environment()
        self.assertEqual(env['OGR_GEOJSON_MAX_OBJ_SIZE'], '7')
        self.assertNotIn('IMPORT_MAX_FILE_SIZE_MB', env)
        self.assertNotIn('IMPORT_GEOJSON_MAX_FEATURE_MB', env)

    def test_ogrinfo_uses_restricted_environment_and_argv_for_every_input_driver(self):
        for driver, fmt in [('GeoJSON', 'geojson'), ('KML', 'kml'), ('GPKG', 'gpkg'), ('ESRI Shapefile', 'shp')]:
            with self.subTest(driver=driver), patch.dict(os.environ, dict.fromkeys(SECRET_NAMES, 'SYNTHETIC-SECRET-ONLY')):
                source = Path('/tmp/staging/synthetic input.' + fmt)
                with process_output([json.dumps(metadata(driver=driver)).encode()]) as (proc, popen):
                    result = ing.inspect_dataset(source)
                command = popen.call_args.args[0]
                self.assertIsInstance(command, list)
                self.assertEqual(command, ['ogrinfo', '-ro', '-so', '-al', '-json', str(source)])
                self.assertEqual(result.format, fmt)
                self.assertFalse(popen.call_args.kwargs['shell'])
                self.assert_restricted(popen.call_args.kwargs['env'])
                self.assertTrue(proc.stdout.closed)

    def test_ogr2ogr_preserves_coordinates_arguments_and_restricted_environment(self):
        for fmt in ['geojson', 'kml', 'gpkg', 'shp']:
            with self.subTest(fmt=fmt), patch.dict(os.environ, dict.fromkeys(SECRET_NAMES, 'SYNTHETIC-SECRET-ONLY')):
                with process_output([encoded()]) as (proc, popen):
                    result = list(ing.iter_features(Path('/tmp/staging/synthetic.' + fmt), dataset(fmt=fmt),
                        preserve_source_geometry=(fmt == 'gpkg')))
                command = popen.call_args.args[0]
                self.assertEqual(result, [('layer0', row())])
                self.assertEqual(command[0], 'ogr2ogr')
                self.assertIn('GeoJSONSeq', command)
                self.assertIn('EPSG:4326', command)
                self.assertIn('COORDINATE_PRECISION=15', command)
                self.assertNotIn('-limit', command)
                self.assertFalse(popen.call_args.kwargs['shell'])
                self.assert_restricted(popen.call_args.kwargs['env'])
                self.assertTrue(proc.stdout.closed)

    def test_layer_shell_metacharacters_remain_one_argument(self):
        name = 'Capa ñ; $(synthetic) & "texto"'
        d = dataset();d = replace(d, layers=(replace(d.layers[0], name=name),))
        with process_output([encoded()]) as (_, popen): list(ing.iter_features(Path('/tmp/staging/data.geojson'), d))
        self.assertEqual(popen.call_args.args[0].count(name), 1)
        self.assertFalse(popen.call_args.kwargs['shell'])

    def test_option_like_generic_layers_rejected_before_launch(self):
        for name in ['-skipfailures', '--config', '-sql']:
            d = dataset();d = replace(d, layers=(replace(d.layers[0], name=name),))
            with self.subTest(name=name), process_output([]) as (_, popen):
                with self.assertRaises(ing.IngestionError) as error: list(ing.iter_features(Path('/tmp/staging/data'), d))
                self.assertEqual(error.exception.code, 'CAPA_NO_SEGURA')
                popen.assert_not_called()

    def test_gpkg_quoted_identifiers_cannot_add_shell_arguments(self):
        name, geom, fid = '-name"; SELECT synthetic', 'g"eom', 'f"id'
        d = dataset(fmt='gpkg');d = replace(d, layers=(replace(d.layers[0], name=name, geometry_column=geom, fid_column=fid),))
        with process_output([encoded()]) as (_, popen):
            list(ing.iter_features(Path('/tmp/staging/data.gpkg'), d, preserve_source_geometry=True))
        command = popen.call_args.args[0];sql = command[command.index('-sql') + 1]
        self.assertIn('FROM "-name""; SELECT synthetic"', sql)
        self.assertIn('"g""eom"', sql)
        self.assertIn('"f""id"', sql)
        self.assertFalse(popen.call_args.kwargs['shell'])

    def test_invalid_resource_environment_does_not_start_child(self):
        with patch.dict(os.environ, {'GDAL_DATA': 'relative'}), process_output([]) as (_, popen):
            with self.assertRaises(ing.IngestionError): ing._run_json(['ogrinfo', 'synthetic'])
            popen.assert_not_called()

    def test_budget_failure_still_kills_reaps_and_closes_restricted_child(self):
        with patch.dict(os.environ, {'IMPORT_MAX_RECORD_BYTES': '2', 'SECRET_KEY': 'SYNTHETIC-SECRET-ONLY'}):
            with process_output([encoded()]) as (proc, popen):
                with self.assertRaises(ing.IngestionError) as error: list(ing.iter_features(Path('/tmp/staging/data'), dataset()))
                self.assertEqual(error.exception.code, 'LIMITE_REGISTRO')
                self.assert_restricted(popen.call_args.kwargs['env'])
            proc.kill.assert_called_once();proc.wait.assert_called_once()
            self.assertTrue(proc.stdout.closed)

    def test_missing_binary_returns_controlled_error(self):
        with patch.object(ing.subprocess, 'Popen', side_effect=FileNotFoundError()):
            with self.assertRaises(ing.IngestionError) as error: ing._run_json(['ogrinfo', 'synthetic'])
        self.assertEqual(error.exception.code, 'GDAL_NO_DISPONIBLE')

    def test_one_subprocess_entry_point_with_explicit_policy(self):
        tree = ast.parse(Path(ing.__file__).read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == 'subprocess'
                 and n.func.attr in ('Popen', 'run', 'call', 'check_call', 'check_output')]
        self.assertEqual(len(calls), 1)
        keywords = {k.arg: k.value for k in calls[0].keywords}
        self.assertEqual(ast.unparse(keywords['env']), '_gdal_environment()')
        self.assertIs(ast.literal_eval(keywords['shell']), False)

    def test_no_database_or_application_loaded(self):
        self.assertNotIn('app.database', sys.modules)
        self.assertNotIn('app.main', sys.modules)


if __name__ == '__main__':
    unittest.main()
