"""Release checks reject altered vendors and restored decoder privileges."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

sheet = load('sheet_preflight', 'frontend-ssalfer/tools/verificar_sheetjs.py')
postgis = load('postgis_preflight', 'backend/scripts/check_postgis_access.py')

class SheetJSChecks(unittest.TestCase):
    def test_exact_archive_and_members_then_modified_vendor(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for member in sheet.FILES:
                info = tarfile.TarInfo(member)
                info.size = 3
                archive.addfile(info, io.BytesIO(b'abc'))
        data = buffer.getvalue()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in sheet.FILES.values():
                (root / filename).write_bytes(b'abc')
            with patch.object(sheet, 'ARCHIVE_SHA256', hashlib.sha256(data).hexdigest()):
                self.assertEqual(sheet.verify(data, root), 2)
                (root / next(iter(sheet.FILES.values()))).write_bytes(b'abd')
                with self.assertRaisesRegex(ValueError, 'COPIA_LOCAL_NO_COINCIDE'):
                    sheet.verify(data, root)

    def test_wrong_archive_rejected_before_parsing(self):
        with self.assertRaisesRegex(ValueError, 'ARCHIVO_OFICIAL_NO_COINCIDE'):
            sheet.verify(b'not an archive', ROOT)

class Cursor:
    def __init__(self, role=(False, False), rows=None):
        self.role = role
        self.rows = rows if rows is not None else [
            ('public', 'st_fromflatgeobuf', False, False),
            ('public', 'st_fromflatgeobuftotable', False, False)]
    def execute(self, sql):
        if not sql.lstrip().startswith('SELECT'):
            raise AssertionError('Preflight must only query metadata')
    def fetchone(self): return self.role
    def fetchall(self): return self.rows

class PostGISChecks(unittest.TestCase):
    def test_restricted_runtime(self):
        self.assertEqual(postgis.verify(Cursor()), 2)
    def test_admin_and_role_creator_rejected(self):
        for role in [(True, False), (False, True)]:
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, 'ROL_RUNTIME_PRIVILEGIADO'):
                postgis.verify(Cursor(role=role))
    def test_restored_grants_or_owner_membership_rejected(self):
        for execute, owner in [(True, False), (False, True)]:
            rows = Cursor().rows
            rows[0] = ('public', 'st_fromflatgeobuf', execute, owner)
            with self.subTest(execute=execute, owner=owner), self.assertRaisesRegex(ValueError, 'DECODIFICADORES_ACCESIBLES'):
                postgis.verify(Cursor(rows=rows))
    def test_missing_or_new_decoder_inventory_requires_review(self):
        for rows in [[], Cursor().rows[:1], Cursor().rows * 2]:
            with self.subTest(count=len(rows)), self.assertRaisesRegex(ValueError, 'INVENTARIO_POSTGIS'):
                postgis.verify(Cursor(rows=rows))

if __name__ == '__main__': unittest.main()
