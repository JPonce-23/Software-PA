"""SS-09 stdlib-only synthetic checks; no installs, network, Docker or app engine."""
import ast
import base64
from contextlib import redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'docs/security/ss09'
spec=importlib.util.spec_from_file_location('ss09_offline',ASSETS/'verificar_cadena.py')
chain=importlib.util.module_from_spec(spec);spec.loader.exec_module(chain)


def synthetic_node():
    """Exercise legacy lock rules without requiring retired production sources."""
    package={'dependencies':{'react':'^18.3.0'}}
    lock={'lockfileVersion':3,'packages':{
        '':copy.deepcopy(package),
        'node_modules/react':{'version':'18.3.1',
          'resolved':'https://registry.npmjs.org/react/-/react-18.3.1.tgz',
          'integrity':'sha512-'+base64.b64encode(bytes(64)).decode()}}}
    return package,lock


class SupplyChainTests(unittest.TestCase):
    def fixture(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);target=Path(directory.name)
        for name in (*chain.SOURCES,'docs/security/ss09/vendors-sha256.json'):
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        shutil.copytree(ROOT/'frontend-ssalfer/js/vendor',target/'frontend-ssalfer/js/vendor')
        (target/'backend/app').mkdir(parents=True);(target/'backend/app/synthetic.py').write_text('import fastapi\nimport sqlalchemy\n')
        return target

    def add_legacy(self,root):
        package,lock=synthetic_node()
        directory=root/'frontend';directory.mkdir()
        (directory/'package.json').write_text(json.dumps(package))
        (directory/'package-lock.json').write_text(json.dumps(lock))
        (directory/'Dockerfile').write_text('FROM node:22-alpine\nRUN npm ci\n')
        (directory/'.dockerignore').write_text('.env\n.env.*\n')
        return directory

    def test_inventory_is_deterministic_and_separates_actual_state(self):
        one=chain.audit(ROOT);two=chain.audit(ROOT)
        self.assertEqual(json.dumps(one,sort_keys=True),json.dumps(two,sort_keys=True))
        self.assertEqual(one['assessment'],'incomplete_requires_qa')
        self.assertTrue(one['local_integrity_ok'])
        self.assertEqual(len(one['python']),42);self.assertEqual(len(one['node']['locked']),0)
        self.assertEqual(one['node']['source_status'],'absent_retired')
        self.assertEqual(len(one['vendors']['files']),20)
        self.assertTrue(all(p['installed_version'] is None and p['distribution_hash'] is None for p in one['python']))
        self.assertTrue(all(p['installed_version'] is None and not p['distribution_bytes_verified'] for p in one['node']['locked']))
        self.assertIn('CVE_SCA_NOT_PERFORMED',one['issues'])

    def test_saved_inventory_is_current_and_no_profile_is_activated(self):
        recorded=json.loads((ASSETS/'inventario-declarado.json').read_text())
        self.assertEqual(recorded,chain.audit(ROOT))
        proposal=json.loads((ASSETS/'perfiles-despliegue-propuestos.json').read_text())
        self.assertEqual(proposal['status'],'design_only_not_applied')
        self.assertIsNone(proposal['selected_profile'])
        self.assertIsNone(proposal['actual_image_digests'])
        self.assertEqual(proposal['official_frontend'],'frontend-ssalfer')

    def test_current_vendor_hashes_match_actual_local_bytes(self):
        report=chain.vendor_inventory(ROOT)
        self.assertEqual(report['unmanifested_count'],0)
        for row in report['files']:
            self.assertEqual(row['sha256'],hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest())
            self.assertTrue(row['matches_local_baseline'])
            self.assertEqual(row['upstream_authenticity'],'not_verified')
        excel=next(p for p in report['files'] if p['path'].endswith('exceljs-4.4.0.min.js'))
        self.assertFalse(excel['version_literal_present'],'filename/README must not become an internal version assertion')

    def test_synthetic_vendor_alteration_is_detected_without_accepting_new_hash(self):
        root=self.fixture();path=root/'frontend-ssalfer/js/vendor/leaflet-1.9.4/leaflet.js'
        path.write_bytes(path.read_bytes()+b'\n/* SS09 SYNTHETIC ALTERATION */')
        report=chain.audit(root)
        self.assertFalse(report['local_integrity_ok'])
        self.assertIn('VENDOR_LOCAL_INTEGRITY_FAILURE',report['issues'])

    def test_new_unreviewed_file_is_not_hashed_or_echoed(self):
        root=self.fixture();sentinel='SS09_UNREVIEWED_PRIVATE_NAME_4157'
        (root/f'frontend-ssalfer/js/vendor/{sentinel}.js').write_text('SYNTHETIC CONTENT')
        report=chain.audit(root);output=json.dumps(report)
        self.assertEqual(report['vendors']['unmanifested_count'],1)
        self.assertNotIn(sentinel,output);self.assertFalse(report['local_integrity_ok'])

    def test_manifest_escape_and_symlink_are_refused(self):
        for kind in ('escape','symlink'):
            with self.subTest(kind=kind):
                root=self.fixture();manifest=root/'docs/security/ss09/vendors-sha256.json'
                obj=json.loads(manifest.read_text())
                if kind=='escape':obj['files'][0]['path']='frontend-ssalfer/js/vendor/../../../../.env'
                else:
                    path=root/obj['files'][0]['path'];path.unlink();path.symlink_to(root/'backend/requirements.txt')
                manifest.write_text(json.dumps(obj))
                with self.assertRaises((chain.AuditError,OSError)):chain.vendor_inventory(root)

    def test_sensitive_paths_and_oversize_reads_are_refused(self):
        root=self.fixture()
        for name in ('.env','backend/.env.production','backend/.ssh/id_rsa','backend/key.pem','../other','/tmp/private'):
            with self.subTest(name=name),self.assertRaises(chain.AuditError):chain.read_bytes(root,name)
        old=chain.MAX_SOURCE_BYTES
        try:
            chain.MAX_SOURCE_BYTES=2
            with self.assertRaises(chain.AuditError):chain.read_bytes(root,'backend/requirements.txt')
        finally:chain.MAX_SOURCE_BYTES=old

    def test_fifo_source_is_rejected_without_waiting_for_a_writer(self):
        root=self.fixture();path=root/'backend/requirements.txt'
        path.unlink();chain.os.mkfifo(path,mode=0o600)
        with self.assertRaises(chain.AuditError):chain.read_bytes(root,'backend/requirements.txt')

    def test_credentialed_lock_urls_and_unknown_metadata_do_not_leak(self):
        package,lock=synthetic_node()
        sentinel='SS09_SYNTHETIC_PASSWORD_COOKIE_TOKEN_2783'
        first=next(k for k in lock['packages'] if k)
        lock['packages'][first]['resolved']=f'https://user:{sentinel}@registry.npmjs.org/p.tgz?token={sentinel}'
        lock['packages'][first]['password']=sentinel;package['secret']=sentinel
        report=chain.node_inventory(package,lock);output=json.dumps(report)
        self.assertNotIn(sentinel,output)
        self.assertIn('unapproved_or_credentialed',output)

    def test_invalid_requirements_and_errors_do_not_echo_sensitive_values(self):
        sentinel='SS09_REQUIREMENTS_SECRET_9824'
        with self.assertRaises(chain.AuditError):chain.python_inventory(f'--extra-index-url https://x:{sentinel}@invalid/\n')
        stream=io.StringIO()
        with redirect_stdout(stream):status=chain.main(['--password',sentinel])
        self.assertEqual(status,2);self.assertNotIn(sentinel,stream.getvalue())
        self.assertEqual(json.loads(stream.getvalue())['status'],'inspection_failed')

    def test_lock_root_and_range_coherence(self):
        package,lock=synthetic_node()
        report=chain.node_inventory(package,lock)
        self.assertTrue(all(p['coherence']=='matches_reviewed_range' for p in report['direct']))
        self.assertTrue(all(p['integrity_format_valid'] for p in report['locked']))
        broken=copy.deepcopy(lock);broken['packages']['']['dependencies']['react']='^1.0.0'
        with self.assertRaises(chain.AuditError):chain.node_inventory(package,broken)
        broken=copy.deepcopy(lock);broken['packages']['node_modules/react']['version']='1.0.0'
        self.assertEqual(next(p for p in chain.node_inventory(package,broken)['direct'] if p['name']=='react')['coherence'],'mismatch')

    def test_bad_lock_integrity_and_production_drift_are_not_success(self):
        root=self.fixture();lockfile=self.add_legacy(root)/'package-lock.json'
        lock=json.loads(lockfile.read_text());lock['packages']['node_modules/react']['integrity']='sha512-invalid'
        lockfile.write_text(json.dumps(lock))
        result=chain.audit(root)
        self.assertFalse(result['local_integrity_ok'])
        self.assertIn('NODE_RESOLUTION_METADATA_REQUIRES_REVIEW',result['issues'])
        root=self.fixture();prod=root/'docker-compose.prod.yml'
        prod.write_text(prod.read_text().replace('AUTH_COOKIE_SECURE: "true"','AUTH_COOKIE_SECURE: "false"'))
        result=chain.audit(root)
        self.assertFalse(result['local_integrity_ok'])
        self.assertIn('PRODUCTION_SETTINGS_DRIFT',result['issues'])

    def test_reviewed_semver_subset_has_correct_boundaries(self):
        for spec,version,wanted in [('^1.2.3','1.9.0',True),('^1.2.3','2.0.0',False),
             ('^0.2.3','0.3.0',False),('^0.0.3','0.0.4',False),('~1.2.3','1.3.0',False),
             ('1.2.3','1.2.3',True),('>=1','2.0.0',None)]:
            with self.subTest(spec=spec,version=version):self.assertEqual(chain.semver_subset(spec,version),wanted)

    def test_images_distinguish_tag_digest_and_unknown_reference(self):
        self.assertFalse(chain.image_record('nginx:1.27-alpine','synthetic')['immutable_reference'])
        digest=chain.image_record('nginx@sha256:'+'a'*64,'synthetic')
        self.assertTrue(digest['immutable_reference']);self.assertFalse(digest['actual_digest_verified'])
        sentinel='SS09_REGISTRY_CREDENTIAL_6148'
        report=chain.image_record(f'https://user:{sentinel}@registry.invalid/image','synthetic')
        self.assertIsNone(report['reference']);self.assertNotIn(sentinel,json.dumps(report))

    def test_context_exclusions_and_required_runtime_files(self):
        source=(ROOT/'backend/.dockerignore').read_text()
        for path in ('.env','.env.production','sub/.env.production','sub/.ssh/key','sub/.aws/credentials',
                     'certs/private.pem','keys/private.key','a/.pgpass','tests/fake.py','db/tests/fake.sql','backups/db.dump'):
            with self.subTest(path=path):self.assertTrue(chain.ignore_subset(path,source))
        for path in ('requirements.txt','logging.json','app/main.py','app/safe_logging.py',
                     'app/services/document_storage.py','db/init/001_bootstrap_roles.sh',
                     'db/migrations/030_rbac_gis_revisiones.sql','scripts/create_admin.py','scripts/run_migrations.sh'):
            with self.subTest(path=path):self.assertFalse(chain.ignore_subset(path,source))

    def test_all_current_application_and_migration_resources_remain_in_context(self):
        source=(ROOT/'backend/.dockerignore').read_text()
        for folder in ('app','db/migrations','db/init','scripts'):
            for path in (ROOT/'backend'/folder).rglob('*'):
                if path.is_file() and path.suffix in ('.py','.sql','.sh'):
                    self.assertFalse(chain.ignore_subset(str(path.relative_to(ROOT/'backend')),source),str(path))

    def test_compose_combinations_and_ss08_selective_copy(self):
        result=chain.audit(ROOT)
        self.assertTrue(result['contexts']['ssalfer_selective_copy'])
        deployment=result['deployment']
        self.assertTrue(deployment['uvicorn_no_proxy_headers_in_base'])
        self.assertTrue(deployment['uvicorn_no_access_log_in_base'])
        self.assertTrue(deployment['production_mode_literal'])
        self.assertTrue(deployment['secure_cookie_literal_in_prod'])
        self.assertTrue(deployment['explicit_cors_required_in_prod'])
        self.assertTrue(deployment['development_reload'])
        self.assertEqual(len(deployment['combinations']),4)
        profile=json.loads((ASSETS/'perfiles-despliegue-propuestos.json').read_text())
        self.assertIsNone(profile['selected_profile']);self.assertFalse(profile['functional_approval_required'])
        self.assertTrue(profile['deployment_approval_required'])
        self.assertNotIn('frontend',deployment['base_services'])
        self.assertEqual(deployment['frontend_selection'],'ssalfer_official')
        self.assertNotIn('react_candidate_if_approved',profile['profiles'])

    def test_absent_legacy_is_explicit_and_ssalfer_remains_required(self):
        root=self.fixture();report=chain.audit(root)
        self.assertTrue(report['local_integrity_ok'])
        self.assertEqual(report['node']['source_status'],'absent_retired')
        self.assertFalse(report['node']['functional_qa_required_for_ssalfer'])
        self.assertIsNone(report['contexts']['react_uses_npm_ci'])
        (root/'frontend-ssalfer/deploy/Dockerfile').unlink()
        with self.assertRaises(OSError):chain.audit(root)

    def test_present_legacy_keeps_lock_integrity_checks(self):
        root=self.fixture();self.add_legacy(root)
        report=chain.audit(root)
        self.assertTrue(report['local_integrity_ok'])
        self.assertEqual(report['node']['source_status'],'present_audited')
        self.assertEqual(len(report['node']['locked']),1)
        self.assertTrue(report['node']['locked'][0]['integrity_format_valid'])

    def test_partial_legacy_is_not_silently_ignored(self):
        root=self.fixture();directory=root/'frontend';directory.mkdir()
        (directory/'package.json').write_text('{}')
        with self.assertRaises(OSError):chain.audit(root)

    def test_legacy_directory_symlink_is_not_followed(self):
        root=self.fixture();(root/'frontend').symlink_to(root/'backend',target_is_directory=True)
        with self.assertRaises(chain.AuditError):chain.audit(root)

    def test_required_vendor_absence_still_rejects(self):
        root=self.fixture()
        manifest=json.loads((root/'docs/security/ss09/vendors-sha256.json').read_text())
        (root/manifest['files'][0]['path']).unlink()
        with self.assertRaises(OSError):chain.audit(root)

    def test_missing_official_service_is_a_failure(self):
        root=self.fixture();(root/'docker-compose.ssalfer.yml').write_text('services:\n')
        report=chain.audit(root)
        self.assertFalse(report['local_integrity_ok'])
        self.assertIn('SSALFER_SERVICE_MISSING',report['issues'])

    def test_no_connections_installs_subprocesses_env_or_file_writes_in_verifier(self):
        tree=ast.parse((ASSETS/'verificar_cadena.py').read_text());imports=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.update(a.name for a in node.names)
            if isinstance(node,ast.ImportFrom):imports.add(node.module)
            if isinstance(node,ast.Attribute):self.assertNotIn(node.attr,{'environ','getenv','system','popen','connect','execv','write','write_text','write_bytes','mkdir','unlink'})
        self.assertLessEqual(imports,{'argparse','ast','base64','fnmatch','hashlib','json','os','pathlib','re','stat','sys','urllib.parse'})
        self.assertEqual(chain.os.O_RDONLY,0)

    def test_remote_github_policies_remain_unobserved(self):
        result=chain.audit(ROOT)['github']
        self.assertEqual(result['effective_branch_protection'],'not_observed')
        self.assertEqual(result['rulesets'],'not_observed')
        self.assertEqual(result['secrets'],'not_accessed')


if __name__=='__main__':unittest.main()
