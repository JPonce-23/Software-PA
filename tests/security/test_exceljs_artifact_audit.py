"""SCA gate distinguishes installed tooling from actual shipped package versions."""
import importlib.util
import copy
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('exceljs_verify',ROOT/'frontend-ssalfer/tools/exceljs/verify.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class ArtifactAuditTests(unittest.TestCase):
    def test_current_artifact_has_verified_provenance(self):
        graph,lock=v.verify();self.assertTrue(graph['modules']);self.assertTrue(lock['packages'])
    def test_toolchain_rejects_vulnerable_crypto_at_any_depth(self):
        lock=json.loads((v.ROOT/'package-lock.json').read_text())
        for name in v.FORBIDDEN:
            changed=copy.deepcopy(lock)
            changed['packages']['node_modules/parent/node_modules/'+name]={'version':'6.6.1'}
            with self.subTest(name=name),self.assertRaises(ValueError):v.verify_toolchain(changed)
    def test_toolchain_rejects_registry_crypto_instead_of_disabled_local_package(self):
        lock=json.loads((v.ROOT/'package-lock.json').read_text())
        lock['packages']['node_modules/crypto-browserify']={'version':'3.12.1','resolved':'https://registry.npmjs.org/crypto-browserify/-/crypto-browserify-3.12.1.tgz'}
        with self.assertRaises(ValueError):v.verify_toolchain(lock)
    def fixture(self):
        graph={'packages':[{'name':'shared','version':'2.0.0'}]}
        lock={'packages':{'node_modules/shared':{'version':'1.0.0'},'node_modules/a/node_modules/shared':{'version':'2.0.0'},'node_modules/tool':{'version':'1.0.0'}}}
        return graph,lock
    def audit(self,name,nodes):return {'auditReportVersion':2,'vulnerabilities':{name:{'severity':'low','nodes':nodes,'via':[]}}}
    def test_even_low_shipped_advisory_is_not_ignored(self):
        graph,lock=self.fixture();r=v.classify(self.audit('shared',['node_modules/a/node_modules/shared']),graph,lock)
        self.assertEqual(len(r['runtime_findings']),1)
    def test_unshipped_version_of_same_package_is_reported_separately(self):
        graph,lock=self.fixture();r=v.classify(self.audit('shared',['node_modules/shared']),graph,lock)
        self.assertFalse(r['runtime_findings']);self.assertEqual(len(r['build_or_node_only_findings']),1)
    def test_network_error_cannot_be_mistaken_for_clean_sca(self):
        graph,lock=self.fixture()
        for data in [{},{'error':{'code':'ECONNRESET'}},{'auditReportVersion':1,'vulnerabilities':{}},{'auditReportVersion':2,'vulnerabilities':None}]:
            with self.subTest(data=data),self.assertRaises(ValueError):v.classify(data,graph,lock)
if __name__=='__main__':unittest.main()
