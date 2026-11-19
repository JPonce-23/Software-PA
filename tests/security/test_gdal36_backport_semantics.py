"""Identical patch context must not silently move a fix to another function."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'backend/native/postgis/gdal36/prepare-source.py'
spec=importlib.util.spec_from_file_location('gdal36_prepare',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class BackportSemanticTests(unittest.TestCase):
    def fixture(self,functions):
        return '\n'.join('\nint32\n'+name+'(int id)\n{\n    while (1) {}\n}\n' for name in functions)
    def test_identical_context_in_wrong_function_is_rejected(self):
        before={p:self.fixture(sorted(names|{'SWinqmaps'})) for p,names in module.EXPECTED_HDF_FUNCTIONS.items()}
        after={p:content.replace('while (1)','while (metaptrs[0])') for p,content in before.items()}
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):module.verify_hdf_functions(before,after)
    def test_only_intended_upstream_functions_are_accepted(self):
        before={p:self.fixture(sorted(names)) for p,names in module.EXPECTED_HDF_FUNCTIONS.items()}
        after={p:content.replace('while (1)','while (metaptrs[0])') for p,content in before.items()}
        module.verify_hdf_functions(before,after)

if __name__=='__main__':unittest.main()
