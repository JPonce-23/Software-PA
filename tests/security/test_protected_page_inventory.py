"""Focused page inventory contracts; copies only reviewed synthetic test fixtures."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('protected_inventory',ROOT/'docs/security/ss09/verificar_paginas_protegidas.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class ProtectedPageInventoryTests(unittest.TestCase):
    def fixture(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);root=Path(directory.name)
        report=json.loads((ROOT/audit.REPORT).read_text());files={audit.REPORT,audit.INVENTORY}
        for page in report['pages']:
            files.add('frontend-ssalfer/'+page['local']['path'])
            files.update(r['path'] for r in page['resources']+page['css_dependencies']+page['licenses'] if 'path' in r)
            files.update([page['exceljs']['runtime_graph'],page['exceljs']['licenses'],'frontend-ssalfer/js/vendor/exceljs-4.4.0-ssalfer.min.js'])
        for name in files:
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        return root

    def test_current_pages_and_all_recorded_dependencies_match(self):
        result=audit.verify(ROOT)
        self.assertEqual(result['pages'],2)
        self.assertGreater(result['resource_records_checked'],90)

    def test_page_script_addition_fails_without_changing_inventory(self):
        root=self.fixture();p=root/'frontend-ssalfer/pages/fichaProyecto.html'
        p.write_text(p.read_text()+'<script src="https://example.invalid/unreviewed.js"></script>')
        with self.assertRaisesRegex(ValueError,'PAGE_INVENTORY_DRIFT'):audit.verify(root)

    def test_transitive_font_bytes_cannot_change_silently(self):
        root=self.fixture();p=root/'frontend-ssalfer/js/vendor/bootstrap-icons-1.13.1/fonts/bootstrap-icons.woff2'
        p.write_bytes(p.read_bytes()+b'SYNTHETIC_CHANGE')
        with self.assertRaisesRegex(ValueError,'RESOURCE_OR_LICENSE_DRIFT'):audit.verify(root)

    def test_dependency_symlink_is_rejected(self):
        root=self.fixture();p=root/'frontend-ssalfer/js/vendor/bootstrap-icons-1.13.1/fonts/bootstrap-icons.woff2'
        p.unlink();p.symlink_to(root/'frontend-ssalfer/pages/fichaProyecto.html')
        with self.assertRaisesRegex(ValueError,'SYMLINK'):audit.verify(root)

if __name__=='__main__':unittest.main()
