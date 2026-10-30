"""SS-03: stdlib-only, synthetic data, no conftest/app/DB/GDAL imports or network.
Run: python3 -B -m unittest discover -s tests/security -p 'test_gis_resource_limits.py' -v
"""
import ast
import asyncio
from contextlib import contextmanager, closing
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import MagicMock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services import gis_ingestion as ing, gis_archives as archives, gis_limits


class Stdout(io.BytesIO):
    def fileno(self):
        return 42


@contextmanager
def process_output(chunks, *, returncode=0):
    """No child is launched. Feed exact byte fragments through os.read doubles."""
    proc = SimpleNamespace(stdout=Stdout(), returncode=None)
    proc.poll = lambda: proc.returncode
    def wait(**kwargs):
        proc.returncode = returncode
        return returncode
    proc.wait = MagicMock(side_effect=wait)
    proc.kill = MagicMock()
    fragments = iter([*chunks, b''])
    with patch.object(ing.subprocess, 'Popen', return_value=proc) as popen, \
         patch.object(ing.select, 'select', return_value=([proc.stdout], [], [])), \
         patch.object(ing.os, 'read', side_effect=lambda *args: next(fragments)):
        yield proc, popen


def dataset(count=1, layers=1, fmt='geojson'):
    return ing.DatasetInfo(fmt, fmt, tuple(ing.LayerInfo(f'layer{i}', count, ('name',),
        'EPSG:4326', True, 'fid', 'geom', 'Polygon', 'synthetic WKT', 4326) for i in range(layers)))


def row(name='José ñ 😀'):
    return {'type': 'Feature', 'properties': {'name': name},
        'geometry': {'type': 'Polygon', 'coordinates': [[[0, 0, 17], [1, 0, 17], [1, 1, 17], [0, 0, 17]]]}}


def encoded(name='José ñ 😀'):
    return json.dumps(row(name), ensure_ascii=False).encode('utf-8')


def metadata(count=1, driver='GeoJSON', layers=1):
    return {'driverShortName': driver, 'layers': [dict(name=f'layer{i}', featureCount=count,
        geometryFields=[{'name': 'geom', 'type': 'Polygon'}], fields=[{'name': 'name'}],
        coordinateSystem={'wkt': 'synthetic WKT', 'projjson': {'id': {'authority': 'EPSG', 'code': 4326}}})
        for i in range(layers)]}


class ResourceTests(unittest.TestCase):
    def setUp(self):
        # Tests do not consume runtime .env; isolate all limit overrides to defaults.
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def assert_code(self, code, call):
        with self.assertRaises(ing.IngestionError) as ctx:
            call()
        self.assertEqual(ctx.exception.code, code)

    def test_gdal_megabytes_independent_of_upload_bytes(self):
        with patch.dict(os.environ, {'IMPORT_MAX_FILE_SIZE_MB': '100', 'IMPORT_GEOJSON_MAX_FEATURE_MB': '7'}):
            self.assertEqual(ing._gdal_environment()['OGR_GEOJSON_MAX_OBJ_SIZE'], '7')
            limits = gis_limits.load_limits()
            self.assertEqual(limits.record_bytes, 64 * 1024 * 1024)
            self.assertEqual(limits.output_bytes, 512 * 1024 * 1024)

    def test_default_feature_unit_is_mb(self):
        self.assertEqual(ing._gdal_environment()['OGR_GEOJSON_MAX_OBJ_SIZE'], '16')

    def test_invalid_configuration_rejected(self):
        for value in ['0', '-1', 'oops']:
            with self.subTest(value=value), patch.dict(os.environ, {'IMPORT_MAX_RECORD_BYTES': value}):
                with self.assertRaises(ValueError): gis_limits.load_limits()

    def test_fragmented_utf8_and_final_unterminated_record(self):
        data = encoded()
        with process_output([data[i:i+1] for i in range(len(data))]) as (proc, _):
            result = list(ing.iter_features(Path('synthetic.geojson'), dataset()))
        self.assertEqual(result, [('layer0', row())])
        self.assertTrue(proc.stdout.closed)
        proc.kill.assert_not_called()

    def test_multiple_records_crlf_rs_and_trailing_newline(self):
        with process_output([b'\x1e' + encoded() + b'\r\n' + encoded('Dos') + b'\n']):
            values = list(ing.iter_features(Path('synthetic'), dataset(2)))
        self.assertEqual([v for _, v in values], [row(), row('Dos')])

    def test_record_at_limit_accepted(self):
        data = encoded('geometría legítima')
        with patch.dict(os.environ, {'IMPORT_MAX_RECORD_BYTES': str(len(data))}), process_output([data]):
            self.assertEqual(list(ing.iter_features(Path('synthetic'), dataset()))[0][1], row('geometría legítima'))

    def test_record_over_limit_kills_and_closes(self):
        with patch.dict(os.environ, {'IMPORT_MAX_RECORD_BYTES': '10'}), process_output([b'x' * 11]) as (proc, _):
            self.assert_code('LIMITE_REGISTRO', lambda: list(ing.iter_features(Path('synthetic'), dataset())))
        proc.kill.assert_called_once()
        self.assertTrue(proc.stdout.closed)

    def test_fragmented_record_limit_counts_bytes_not_characters(self):
        data = encoded('é' * 10)
        with patch.dict(os.environ, {'IMPORT_MAX_RECORD_BYTES': str(len(data) - 1)}), process_output([data[:20], data[20:]]):
            self.assert_code('LIMITE_REGISTRO', lambda: list(ing.iter_features(Path('synthetic'), dataset())))

    def test_output_limit(self):
        with patch.dict(os.environ, {'IMPORT_MAX_OUTPUT_BYTES': '5'}), process_output([b'123456']) as (proc, _):
            self.assert_code('LIMITE_SALIDA_GDAL', lambda: list(ing.iter_features(Path('synthetic'), dataset())))
        self.assertTrue(proc.stdout.closed)

    def test_output_budget_is_shared_across_layers(self):
        data = encoded()
        with patch.dict(os.environ, {'IMPORT_MAX_OUTPUT_BYTES': str(2 * len(data) - 1)}):
            original = ing._process_chunks
            commands = []
            def per_layer(command, budget):
                commands.append(command)
                with process_output([data]): yield from original(command, budget)
            with patch.object(ing, '_process_chunks', side_effect=per_layer):
                self.assert_code('LIMITE_SALIDA_GDAL', lambda: list(ing.iter_features(Path('synthetic'), dataset(layers=2))))
            self.assertEqual(len(commands), 2)

    def test_cancel_close_and_consumer_error_reap_child(self):
        for failure in [None, RuntimeError('consumer'), asyncio.CancelledError()]:
            with self.subTest(failure=type(failure).__name__), process_output([encoded() + b'\n']) as (proc, _):
                try:
                    with closing(ing.iter_features(Path('synthetic'), dataset())) as stream:
                        next(stream)
                        if failure is not None: raise failure
                except (RuntimeError, asyncio.CancelledError): pass
                proc.kill.assert_called_once()
                self.assertTrue(proc.stdout.closed)
                proc.wait.assert_called_once()

    def test_timeout_reaps_child(self):
        with process_output([]) as (proc, _), patch.object(ing.select, 'select', return_value=([], [], [])):
            self.assert_code('GDAL_TIMEOUT', lambda: list(ing.iter_features(Path('synthetic'), dataset())))
        self.assertTrue(proc.stdout.closed)
        proc.kill.assert_called_once()

    def test_invalid_json_utf8_or_non_feature(self):
        for payload in [b'{', b'\xff', b'[]', b'{"type":"Point"}']:
            with self.subTest(payload=payload), process_output([payload]) as (proc, _):
                self.assert_code('FEATURE_OGR_INVALIDO', lambda: list(ing.iter_features(Path('synthetic'), dataset())))
            self.assertTrue(proc.stdout.closed)

    def test_inspection_stdout_budget(self):
        with patch.dict(os.environ, {'IMPORT_MAX_INSPECTION_BYTES': '5'}), process_output([b'123456']) as (proc, _):
            self.assert_code('LIMITE_SALIDA_GDAL', lambda: ing._run_json(['ogrinfo', 'synthetic']))
        self.assertTrue(proc.stdout.closed)

    def test_inspection_valid_and_invalid_metadata(self):
        with process_output([json.dumps(metadata()).encode()]):
            self.assertEqual(ing._run_json(['ogrinfo']), metadata())
        for payload in [b'[]', b'\xff', b'{']:
            with process_output([payload]): self.assert_code('METADATOS_INVALIDOS', lambda: ing._run_json(['ogrinfo']))

    def test_inspection_layer_and_feature_limits(self):
        for options, info, code in [({'IMPORT_MAX_LAYERS': '1'}, metadata(layers=2), 'LIMITE_CAPAS'),
                                  ({'IMPORT_MAX_FEATURES': '1'}, metadata(2), 'LIMITE_FEATURES')]:
            with patch.dict(os.environ, options), patch.object(ing, '_run_json', return_value=info):
                self.assert_code(code, lambda: ing.inspect_dataset(Path('synthetic')))

    def test_driver_crs_and_columns_compatibility(self):
        for driver, fmt in [('GeoJSON', 'geojson'), ('KML', 'kml'), ('GPKG', 'gpkg'), ('ESRI Shapefile', 'shp')]:
            with patch.object(ing, '_run_json', return_value=metadata(driver=driver)):
                d = ing.inspect_dataset(Path('synthetic'))
            self.assertEqual((d.format, d.total_features, d.columns, d.layers[0].srid), (fmt, 1, ['name'], 4326))

    def test_unknown_counts_observed_and_mismatches_rejected(self):
        for count in [None, -1]:
            with patch.object(ing, '_run_json', return_value=metadata(count)):
                d = ing.inspect_dataset(Path('synthetic'))
            self.assertFalse(d.counts_known)
            with process_output([encoded()]): self.assertEqual(len(list(ing.iter_features(Path('synthetic'), d))), 1)
        for count in [0, 2]:
            with process_output([encoded()]):
                self.assert_code('CONTEO_FEATURES_INCONSISTENTE', lambda: list(ing.iter_features(Path('synthetic'), dataset(count))))

    def test_observed_feature_limit_rejects_unknown_metadata(self):
        with patch.dict(os.environ, {'IMPORT_MAX_FEATURES': '1'}), process_output([encoded() + b'\n' + encoded()]):
            self.assert_code('LIMITE_FEATURES', lambda: list(ing.iter_features(Path('synthetic'), dataset(-1))))

    def test_per_layer_cap_rejects_instead_of_silent_ogr_limit(self):
        with process_output([encoded() + b'\n' + encoded()]) as (_, popen):
            self.assert_code('LIMITE_FEATURES', lambda: list(ing.iter_features(Path('synthetic'), dataset(2), limit_per_layer=1)))
            command = popen.call_args.args[0]
            self.assertNotIn('-limit', command)
            self.assertIn('EPSG:4326', command)

    def test_wkb_sql_quoting_and_dimensions_not_rewritten(self):
        source = row();source['properties']['__pa_source_wkb'] = '010203'
        payload = json.dumps(source).encode()
        d = dataset(fmt='gpkg')
        with process_output([payload]) as (_, popen):
            self.assertEqual(list(ing.iter_features(Path('synthetic'), d, preserve_source_geometry=True))[0][1], source)
            self.assertIn('hex(ST_AsBinary("geom"))', popen.call_args.args[0][popen.call_args.args[0].index('-sql') + 1])

    def test_nonzero_exit_rejected(self):
        with process_output([encoded()], returncode=1):
            self.assert_code('CONVERSION_OGR_FALLIDA', lambda: list(ing.iter_features(Path('synthetic'), dataset())))

    def zip_file(self, directory, entries):
        p = Path(directory) / 'synthetic.zip'
        with zipfile.ZipFile(p, 'w') as z:
            for name, data in entries: z.writestr(name, data)
        return p

    def test_zip_legitimate_shapefile_bytes_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.zip_file(tmp, [('nested/data.shp', b'synthetic shape'), ('nested/data.dbf', b'attributes')])
            result = archives.extract_shapefile_zip(p)
            self.assertEqual(result.read_bytes(), b'synthetic shape')
            self.assertEqual(result.with_suffix('.dbf').read_bytes(), b'attributes')

    def test_zip_entry_count_member_and_declared_total_limits(self):
        options = [{'IMPORT_ZIP_MAX_ENTRIES': '1'}, {'IMPORT_ZIP_MAX_MEMBER_BYTES': '1'}, {'IMPORT_MAX_UNCOMPRESSED_MB': '1'}]
        for setting in options:
            with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, setting):
                p = self.zip_file(tmp, [('data.shp', b'ab'), ('data.dbf', b'x' * (1024 * 1024))])
                with self.assertRaises(ing.IngestionError): archives.extract_shapefile_zip(p)
                self.assertFalse(p.with_suffix('').exists())
                self.assertTrue(p.exists())

    def test_zip_observed_budget_does_not_trust_metadata(self):
        for individual in [True, False]:
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / 'synthetic.zip'
                info = zipfile.ZipInfo('data.shp');info.file_size = 0
                fake = MagicMock()
                fake.__enter__.return_value = fake
                fake.infolist.return_value = [info]
                fake.open.return_value = io.BytesIO(b'actual bytes exceed the declared size')
                limits = gis_limits.load_limits()
                from dataclasses import replace
                limits = replace(limits, zip_member_bytes=4 if individual else 100, zip_total_bytes=100 if individual else 4)
                with patch.object(archives, 'load_limits', return_value=limits), patch.object(archives.zipfile, 'ZipFile', return_value=fake):
                    self.assert_code('LIMITE_ZIP_BYTES', lambda: archives.extract_shapefile_zip(p))
                self.assertFalse(p.with_suffix('').exists())

    def test_zip_real_total_accumulates_across_members(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'synthetic.zip'
            entries = [zipfile.ZipInfo('data.shp'), zipfile.ZipInfo('data.dbf')]
            fake = MagicMock();fake.__enter__.return_value = fake
            fake.infolist.return_value = entries
            fake.open.side_effect = [io.BytesIO(b'abcd'), io.BytesIO(b'efgh')]
            limits = replace(gis_limits.load_limits(), zip_member_bytes=6, zip_total_bytes=6)
            with patch.object(archives, 'load_limits', return_value=limits), patch.object(archives.zipfile, 'ZipFile', return_value=fake):
                # Bypass only the first member's metadata consistency check: 4+4
                # actual bytes must exceed the total even though each member fits.
                entries[0].file_size = 4
                self.assert_code('LIMITE_ZIP_BYTES', lambda: archives.extract_shapefile_zip(p))
            self.assertFalse(p.with_suffix('').exists())

    def test_zip_paths_symlinks_duplicates_and_bad_archives_clean_up(self):
        link = zipfile.ZipInfo('link.shp');link.external_attr = (stat.S_IFLNK | 0o777) << 16
        for entries in [[('../outside.shp', b'x')], [('C:\\outside.shp', b'x')], [(link, b'target')],
                        [('data.shp', b'a'), ('data.shp', b'b')], [('no-shape.txt', b'x')]]:
            with tempfile.TemporaryDirectory() as tmp:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    p = self.zip_file(tmp, entries)
                with self.assertRaises(ing.IngestionError): archives.extract_shapefile_zip(p)
                self.assertFalse(p.with_suffix('').exists())
                self.assertFalse((Path(tmp).parent / 'outside.shp').exists())
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.zip';p.write_bytes(b'not zip')
            with self.assertRaises(ing.IngestionError): archives.extract_shapefile_zip(p)
            self.assertFalse(p.with_suffix('').exists())

    def test_zip_existing_directory_and_foreign_files_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.zip_file(tmp, [('data.shp', b'valid')])
            target = p.with_suffix('');target.mkdir();keep = target / 'foreign';keep.write_bytes(b'keep')
            self.assert_code('ZIP_DESTINO_EXISTENTE', lambda: archives.extract_shapefile_zip(p))
            self.assertEqual(keep.read_bytes(), b'keep')

    def test_zip_cancellation_cleans_created_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.zip_file(tmp, [('data.shp', b'valid')])
            with patch.object(zipfile.ZipFile, 'open', side_effect=asyncio.CancelledError()):
                with self.assertRaises(asyncio.CancelledError): archives.extract_shapefile_zip(p)
            self.assertFalse(p.with_suffix('').exists())

    def load_function(self, file, name, namespace):
        tree = ast.parse((ROOT / file).read_text())
        function = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
        future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
        code = ast.fix_missing_locations(ast.Module(body=[future, function], type_ignores=[]))
        exec(compile(code, file, 'exec'), namespace)
        return namespace[name]

    def test_legacy_staging_error_closes_reader_rolls_back_and_cleans_owned_files(self):
        from unittest.mock import AsyncMock
        class HTTPError(Exception):
            def __init__(self, status_code, detail): self.status_code, self.detail = status_code, detail
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'upload.geojson';path.write_bytes(b'synthetic')
            record = SimpleNamespace(id_importacion=1, estado='procesando')
            models = MagicMock()
            models.ImportacionArchivo.side_effect = lambda **kwargs: record
            db = MagicMock();db.query.return_value.filter.return_value.first.return_value = None
            db.get.return_value = record
            commits = []
            db.commit.side_effect = lambda: commits.append(record.estado)
            closed = []
            def reader(*args):
                try:
                    yield 'layer0', row()
                    raise ing.IngestionError('LIMITE_FEATURES', 'Limite sintetico')
                finally: closed.append(True)
            ns = dict(HTTPException=HTTPError, ALLOWED_TARGETS={'trazo_proyecto'},
                _store_upload=AsyncMock(return_value=(path, '0'*64, 9, path.name, 'geojson')),
                require_project_access=MagicMock(), models=models, _extract_zip=archives.extract_shapefile_zip,
                inspect_dataset=lambda p: dataset(), set_audit_context=MagicMock(), iter_features=reader,
                closing=closing, _normalize_geometry=lambda *a: ('POINT(0 0)', None),
                WKTElement=lambda *a, **kw: None, datetime=__import__('datetime').datetime,
                timezone=__import__('datetime').timezone, IngestionError=ing.IngestionError,
                zipfile=zipfile, shutil=__import__('shutil'))
            stage = self.load_function('backend/app/services/geospatial_imports.py', 'stage_import', ns)
            with self.assertRaises(HTTPError) as error:
                asyncio.run(stage(db, 1, 'trazo_proyecto', 'Synthetic', None, {}, None, SimpleNamespace(id_usuario=1)))
            self.assertEqual(error.exception.detail, 'Limite sintetico')
            self.assertEqual(record.estado, 'error')
            self.assertNotIn('previsualizado', commits)
            db.rollback.assert_called_once()
            self.assertEqual(closed, [True])
            self.assertFalse(path.exists())

    def test_reconciliation_inspection_failure_rolls_back_without_residue(self):
        from unittest.mock import AsyncMock
        class HTTPError(Exception):
            def __init__(self, status_code, detail): self.status_code, self.detail = status_code, detail
        with tempfile.TemporaryDirectory() as tmp:
            path = self.zip_file(tmp, [('data.shp', b'synthetic')])
            legacy = ModuleType('app.services.geospatial_imports')
            legacy._store_upload = AsyncMock(return_value=(path, '0'*64, path.stat().st_size, path.name, 'zip'))
            legacy._extract_zip = archives.extract_shapefile_zip
            db = MagicMock();db.query.return_value.filter_by.return_value.first.return_value = None
            ns = dict(__package__='app.services', HTTPException=HTTPError, require_project_access=lambda *a, **k: SimpleNamespace(id_proyecto=1),
                working_srid=lambda *a: 4326, models=MagicMock(), set_audit_context=MagicMock(),
                PIPELINE_VERSION='synthetic', inspect_dataset=MagicMock(side_effect=ing.IngestionError('LIMITE_CAPAS','Limite sintetico')))
            stage = self.load_function('backend/app/services/gis_reconciliation.py', 'stage', ns)
            with patch.dict(sys.modules, {'app.services.geospatial_imports': legacy}):
                with self.assertRaises(HTTPError) as error:
                    asyncio.run(stage(db, 1, 'Synthetic', None, None, SimpleNamespace(id_usuario=1), target='nucleo_agrario', strict=False))
            self.assertEqual(error.exception.detail, 'Limite sintetico')
            db.rollback.assert_called_once()
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix('').exists())
            db.commit.assert_not_called()

    def test_no_database_or_application_loaded(self):
        for name in ['app.database', 'app.main', 'sqlalchemy', 'app.models']:
            self.assertNotIn(name, sys.modules)


if __name__ == '__main__':
    unittest.main()
