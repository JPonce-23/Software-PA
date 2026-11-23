"""Offline preparation contracts only. Does not execute GDAL or any HDF fixture."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'backend/native/postgis/gdal36'
loader = importlib.util.spec_from_file_location('gdal36_pa3_prepare', NATIVE / 'prepare-source.py')
prepare = importlib.util.module_from_spec(loader)
loader.loader.exec_module(prepare)


class Pa3SourceContracts(unittest.TestCase):
    def test_preserved_parent_and_new_patch_are_verified(self):
        prepare.chain_integrity()
        self.assertEqual(prepare.spec['local_version'], '3.10.3+dfsg-1+pa2')
        self.assertEqual(prepare.pa3['local_version'], '3.10.3+dfsg-1+pa3')
        self.assertEqual(prepare.pa3['soname'], 'libgdal.so.36')

    def test_phase_chain_has_eight_sources_and_capacity_header(self):
        phases = [prepare.phase_hashes(p) for p in ['original', 'pa2', 'pa3']]
        self.assertEqual([len(p) for p in phases], [8, 8, 8])
        self.assertTrue(all(set(p) == set(phases[0]) for p in phases))
        for name, record in prepare.pa3['files'].items():
            self.assertEqual(phases[1][name], record['before'])
            self.assertEqual(phases[2][name], record['after'])
        self.assertIn('frmts/hdf4/hdf-eos/HdfEosDef.h', phases[2])

    def test_unknown_source_rejected_without_writing_anything(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'SOURCE_ORIGINAL_DRIFT'):
                prepare.apply(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_wrong_function_is_rejected_even_when_context_is_identical(self):
        before = {}
        after = {}
        for path, names in prepare.pa3['function_scope'].items():
            old = '#include <errno.h>\n'
            old += '\n'.join('int\n' + n + '(void)\n{\n return 0;\n}\n'
                             for n in sorted(set(names) | {'UnreviewedFunction'}))
            before[path] = old
            after[path] = old.replace('return 0;', 'return 1;')
            if path in prepare.pa3['allowed_prologue_changes']:
                after[path] = after[path].replace('#include <errno.h>',
                                                '#include <errno.h>\n#include <limits.h>')
        with self.assertRaisesRegex(ValueError, 'PA3_FUNCTION_SCOPE_MISMATCH'):
            prepare.verify_pa3_functions(before, after)

    def test_final_source_attestation_is_not_runtime_acceptance(self):
        self.assertEqual(prepare.pa3['native_validation'], 'NOT_RUN_F1')
        self.assertIsNone(prepare.pa3['package_hashes'])
        self.assertIsNone(prepare.pa3['image_digest'])
        self.assertEqual(prepare.pa3['internal_interface']['call_sites'], 48)

    def test_record_rejects_wrong_phase_before_creating_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / 'attestation.json'
            with self.assertRaisesRegex(ValueError, 'SOURCE_PA3_DRIFT'):
                prepare.record_phase(root, 'pa3', out)
            self.assertFalse(out.exists())

    def test_precompile_capture_precedes_build_and_unapply_is_separate(self):
        recipe = (NATIVE / 'build-packages.sh').read_text()
        self.assertLess(recipe.index('--verify-phase pa3'), recipe.index('dpkg-buildpackage -b'))
        self.assertGreater(recipe.index('--verify-phase original'), recipe.index('dpkg-buildpackage -b'))
        self.assertNotIn('patched-source.sha256', recipe)
        self.assertIn('source-precompile-pa3.json', recipe)
        self.assertIn('source-after-quilt-unapply.json', recipe)

    def test_candidate_reuses_exact_postgis_core_without_rebuilding_it(self):
        recipe = (NATIVE.parent / 'Dockerfile.gdal36-candidate').read_text()
        self.assertEqual(recipe.count('FROM software-pa-residual-postgis@sha256:'), 2)
        self.assertIn('dbad7ae0ac6f3ba9da2c52215750115862328940703a603bc5a5bfb875e627ef', recipe)
        self.assertNotIn('./configure', recipe)
        self.assertNotIn('make -C postgis', recipe)
        self.assertIn('3.10.3+dfsg-1+pa3', recipe)


if __name__ == '__main__':
    unittest.main()
