"""Fail-closed checks for the PA5-QA launcher; never calls Docker or WSL."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('pa5_native_local',ROOT/'tests/qa/pa5_native_premerge/run.py')
qa=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(qa)

class Pa5NativeLocalTests(unittest.TestCase):
    def arguments(self,root,engine):
        return ['run.py','--source',str(root/'source'),'--assets',str(root/'assets'),'--evidence',str(root/'evidence'),'--approved-engine-id',engine]

    def test_unapproved_engine_id_never_calls_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(sys,'argv',self.arguments(root,'38a3bf79-1712-4ce7-a5d7-a23d15d6395a')),patch.object(qa.subprocess,'run') as execute:
                with self.assertRaisesRegex(RuntimeError,'not authorized'):qa.main()
                execute.assert_not_called()
            self.assertFalse((root/'evidence').exists())

    def test_approved_argument_cannot_hide_a_different_actual_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            reply=SimpleNamespace(returncode=0,stdout='38a3bf79-1712-4ce7-a5d7-a23d15d6395a\n')
            with patch.object(sys,'argv',self.arguments(root,qa.APPROVED)),patch.object(qa.shutil,'which',return_value='/fixture/docker'),patch.object(qa.subprocess,'run',return_value=reply) as execute:
                with self.assertRaisesRegex(RuntimeError,'ENGINE_ID_MISMATCH'):qa.main()
                self.assertEqual(execute.call_count,1)
                self.assertEqual(execute.call_args.args[0],['/fixture/docker','--host',qa.SOCKET,'info','--format','{{.ID}}'])
            self.assertFalse((root/'evidence').exists())

    def test_corrupted_source_stops_before_any_container_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'assets').mkdir();(root/'source').mkdir()
            (root/'assets/source-sha256.json').write_text('{"canonical.sql":"'+('0'*64)+'"}')
            (root/'source/canonical.sql').write_text('-- substituted bytes')
            reply=SimpleNamespace(returncode=0,stdout=qa.APPROVED+'\n')
            with patch.object(sys,'argv',self.arguments(root,qa.APPROVED)),patch.object(qa.shutil,'which',return_value='/fixture/docker'),patch.object(qa.subprocess,'run',return_value=reply) as execute:
                with self.assertRaises(AssertionError):qa.main()
                self.assertEqual(execute.call_count,1)
            self.assertEqual((root/'evidence/stages.json').read_text(),'[]\n')

    def test_audit_failure_cannot_be_masked_by_other_success_markers(self):
        log='PA5_PRIVATE_DB_ROLES_LEDGER_034_ALL_OK\nPA5_AUDIT_TEMP_SHADOW_REPRODUCED'
        self.assertEqual(qa.assessment(log),'FAIL')

if __name__=='__main__':unittest.main()
