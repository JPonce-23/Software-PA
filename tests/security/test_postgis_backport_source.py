"""Offline integrity/preconditions; binary vulnerability status remains unverified."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2];N=ROOT/'backend/native/postgis'
spec=importlib.util.spec_from_file_location('backport_source',N/'verify-source.py');verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
class PostgisBackportTests(unittest.TestCase):
    def test_reviewed_patch_integrity(self):
        m=json.loads((N/'backport.json').read_text())
        for file,key in [('CVE-2026-73515.patch','adapted_patch_sha256'),('upstream-stable36.patch','upstream_patch_sha256')]:
            self.assertEqual(hashlib.sha256((N/file).read_bytes()).hexdigest(),m[key])
        self.assertIn('SOURCE_PATCH_ONLY',m['status'])
    def test_source_preconditions_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'source.c';p.write_text('original')
            manifest={'files':{'source.c':{'before':verify.digest(p),'after':'0'*64}}}
            verify.verify_tree(root,manifest,'before')
            p.write_text('different')
            with self.assertRaises(ValueError):verify.verify_tree(root,manifest,'before')
    def test_backport_preserves_364_type_fixes(self):
        patch=(N/'CVE-2026-73515.patch').read_text()
        self.assertIn('+\t\t\tvalue = flatgeobuf_read_le32(data + offset);',patch)
        self.assertIn('values[ci] = UInt32GetDatum(value);',patch)
        self.assertIn('getBaseType(TupleDescAttr(ctx->tupdesc, ci)->atttypid) == FLOAT8OID',patch)
        self.assertIn('if (len > size - offset)',patch)
    def test_optional_recipe_preserves_pg_major_and_extension_sql(self):
        docker=(N/'Dockerfile').read_text()
        self.assertEqual(docker.count('FROM postgis/postgis:15-3.6@sha256:'),2)
        self.assertIn('sha256sum -c -',docker)
        copies=[x for x in docker.splitlines() if x.startswith('COPY --from=backport-build')]
        self.assertFalse(any('/extension' in x or 'migrations' in x for x in copies))
        self.assertNotIn('docker-compose.postgis-backport.yml',(ROOT/'.github/workflows/pr-regressions.yml').read_text())
if __name__=='__main__':unittest.main()
