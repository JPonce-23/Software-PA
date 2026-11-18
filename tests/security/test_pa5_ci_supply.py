"""Offline supply-chain negatives. Never contacts Docker, registry or a live database."""
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
import tarfile
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / 'deploy/ci'
spec = importlib.util.spec_from_file_location('pa5_supply', CI/'pa5_supply.py')
supply = importlib.util.module_from_spec(spec);spec.loader.exec_module(supply)


class Pa5SupplyTests(unittest.TestCase):
    def fixture(self):
        directory = tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root = Path(directory.name);(root/'blobs/sha256').mkdir(parents=True)
        def blob(data, media):
            digest = supply.digest_bytes(data)
            (root/'blobs/sha256'/digest.split(':')[1]).write_bytes(data)
            return dict(mediaType=media, digest=digest, size=len(data))
        def document(data, media):return blob(json.dumps(data).encode(), media)
        target = 'usr/lib/qa-library.so';payload = b'reviewed synthetic binary bytes'
        status = b'Package: qa-package\nStatus: install ok installed\nVersion: 1.0\n\n'
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as tar:
            for name, raw in [(target, payload), ('var/lib/dpkg/status', status)]:
                info = tarfile.TarInfo(name);info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
        raw = buffer.getvalue();layer=blob(gzip.compress(raw), 'application/vnd.oci.image.layer.v1.tar+gzip')
        diff=supply.digest_bytes(raw)
        config=document(dict(os='linux',architecture='amd64',rootfs=dict(type='layers',diff_ids=[diff])), 'application/vnd.oci.image.config.v1+json')
        manifest=document(dict(schemaVersion=2,config=config,layers=[layer]), 'application/vnd.oci.image.manifest.v1+json')
        manifest['platform']=dict(os='linux',architecture='amd64')
        index=document(dict(schemaVersion=2,manifests=[manifest]), 'application/vnd.oci.image.index.v1+json')
        (root/'index.json').write_text(json.dumps(dict(schemaVersion=2,manifests=[index])))
        (root/'oci-layout').write_text('{"imageLayoutVersion":"1.0.0"}')
        catalog=dict(index_manifests=[manifest],platform_manifest_digest=manifest['digest'],config_digest=config['digest'],layers=[layer],rootfs_diff_ids=[diff],local_index_digest=index['digest'],protected_payloads={target:hashlib.sha256(payload).hexdigest()},package_versions={'qa-package':'1.0'})
        return root,index['digest'],catalog

    def test_complete_offline_layout_and_package_version_pass(self):
        root,digest,catalog=self.fixture();result=supply.validate_layout(root,digest,catalog)
        self.assertEqual(result['state'],'PASS');self.assertEqual(result['layers'],1)

    def test_corrupt_registry_blob_is_rejected_before_execution(self):
        root,digest,catalog=self.fixture();p=root/'blobs/sha256'/catalog['layers'][0]['digest'].split(':')[1]
        raw=p.read_bytes();p.write_bytes(bytes([raw[0]^1])+raw[1:])
        with self.assertRaisesRegex(ValueError,'BLOB_HASH_MISMATCH'):supply.validate_layout(root,digest,catalog)

    def test_substituted_protected_library_fails(self):
        root,digest,catalog=self.fixture();catalog['protected_payloads']['usr/lib/qa-library.so']='0'*64
        with self.assertRaisesRegex(ValueError,'PROTECTED_PAYLOAD_MISMATCH'):supply.validate_layout(root,digest,catalog)

    def test_wrong_installed_package_fails(self):
        root,digest,catalog=self.fixture();catalog['package_versions']['qa-package']='2.0'
        with self.assertRaisesRegex(ValueError,'INSTALLED_PACKAGE_MISMATCH'):supply.validate_layout(root,digest,catalog)

    def test_symlink_blob_cannot_escape_layout(self):
        root,digest,catalog=self.fixture();p=root/'blobs/sha256'/catalog['layers'][0]['digest'].split(':')[1]
        target=root/'elsewhere';p.rename(target);p.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'BLOB_SYMLINK'):supply.validate_layout(root,digest,catalog)

    def test_local_id_is_not_implicitly_an_approved_registry_digest(self):
        for approved, requested in [('', 'sha256:'+'1'*64),('sha256:'+'1'*64,'sha256:'+'2'*64),('latest','latest')]:
            with self.subTest(approved=approved),self.assertRaises(ValueError):supply.reference(approved,requested)
        digest='sha256:'+'3'*64
        self.assertEqual(supply.reference(digest,digest),supply.REPOSITORY+'@'+digest)

    def test_same_engine_in_another_context_is_not_independent(self):
        info=dict(ID='main',OSType='linux',Architecture='x86_64',DriverStatus=[['driver-type','io.containerd.snapshotter.v1']])
        with self.assertRaisesRegex(ValueError,'ENGINE_NOT_INDEPENDENT'):supply.engine_contract(info,'main','','','')

    def test_nonempty_or_classic_engine_fails_without_cleanup(self):
        info=dict(ID='ci',OSType='linux',Architecture='x86_64',DriverStatus=[['driver-type','io.containerd.snapshotter.v1']])
        for resources in [('image','',''),('','container',''),('','','volume')]:
            with self.assertRaisesRegex(ValueError,'ENGINE_NOT_EMPTY'):supply.engine_contract(info,'main',*resources)
        info['DriverStatus']=[]
        with self.assertRaisesRegex(ValueError,'CONTAINERD_STORE_REQUIRED'):supply.engine_contract(info,'main','','','')

    def engine_fixture(self):
        digest='sha256:'+'1'*64;config='sha256:'+'2'*64;diff='sha256:'+'3'*64
        catalog=dict(config_digest=config,rootfs_diff_ids=[diff],local_index_digest='sha256:'+'4'*64)
        row=dict(Id=config,Descriptor=dict(digest=digest),Os='linux',Architecture='amd64',RootFS=dict(Type='layers',Layers=[diff]),RepoDigests=[supply.REPOSITORY+'@'+digest])
        return row,digest,catalog

    def test_remote_digest_is_separate_from_engine_config_id_and_local_index(self):
        row,digest,catalog=self.engine_fixture()
        result=supply.validate_inspect([row],supply.REPOSITORY+'@'+digest,digest,catalog)
        self.assertNotEqual(result['registry_index_digest'],result['engine_image_id'])
        self.assertNotEqual(result['registry_index_digest'],result['local_recorded_image_id'])

    def test_image_id_alone_does_not_prove_compose_resolution(self):
        row,digest,catalog=self.engine_fixture();row['RepoDigests']=[]
        with self.assertRaisesRegex(ValueError,'ENGINE_COMPOSE_DIGEST_NOT_RESOLVED'):supply.validate_inspect([row],supply.REPOSITORY+'@'+digest,digest,catalog)

    def test_wrong_platform_and_rootfs_rejected(self):
        row,digest,catalog=self.engine_fixture();row['Architecture']='arm64'
        with self.assertRaisesRegex(ValueError,'ENGINE_IMAGE_PLATFORM'):supply.validate_inspect([row],supply.REPOSITORY+'@'+digest,digest,catalog)
        row['Architecture']='amd64';row['RootFS']['Layers']=[]
        with self.assertRaisesRegex(ValueError,'ENGINE_ROOTFS_MISMATCH'):supply.validate_inspect([row],supply.REPOSITORY+'@'+digest,digest,catalog)

    def workflow(self):
        return yaml.load((ROOT/'.github/workflows/pa5-verify.yml').read_text(),Loader=yaml.BaseLoader)

    def test_pull_request_to_dev_runs_without_dispatch_registration(self):
        workflow=self.workflow()
        self.assertEqual(set(workflow['on']),{'pull_request','workflow_dispatch'})
        self.assertEqual(workflow['on']['pull_request']['branches'],['dev'])
        self.assertEqual(set(workflow['on']['pull_request']['types']),{'opened','synchronize','reopened','ready_for_review'})
        self.assertNotIn('pull_request_target',workflow['on'])
        job=workflow['jobs']['pa5-supply']
        self.assertIn("github.event_name == 'pull_request'",job['if'])
        self.assertIn('github.event.pull_request.head.repo.full_name == github.repository',job['if'])
        self.assertIn('!github.event.pull_request.draft',job['if'])

    def test_pr_contracts_do_not_receive_package_credentials_or_dedicated_runner(self):
        job=self.workflow()['jobs']['pa5-contracts']
        self.assertEqual(job['permissions'],{'contents':'read'})
        self.assertEqual(job['runs-on'],'ubuntu-24.04')
        self.assertNotIn('environment',job)
        self.assertNotIn('REGISTRY_TOKEN',json.dumps(job))
        self.assertNotIn('secrets.',json.dumps(job))
        self.assertEqual(job['steps'][0]['with']['persist-credentials'],'false')

    def test_native_consumer_pins_tooling_to_independently_approved_sha(self):
        job=self.workflow()['jobs']['pa5-supply']
        self.assertEqual(job['needs'],'pa5-contracts')
        self.assertEqual(job['permissions'],{'contents':'read','packages':'read'})
        self.assertIn('pa5-disposable',job['runs-on']);self.assertEqual(job['environment'],'pa5-verification')
        self.assertIn('^[0-9a-f]{40}$',job['steps'][0]['run'])
        checkout=job['steps'][1]
        self.assertRegex(checkout['uses'],r'actions/checkout@[0-9a-f]{40}$')
        self.assertEqual(checkout['with']['ref'],'${{ vars.PA5_APPROVED_VERIFIER_SHA }}')
        self.assertEqual(checkout['with']['persist-credentials'],'false')
        self.assertNotIn('github.event.pull_request.head.sha',json.dumps(job))
        env=job['steps'][2]['env']
        self.assertEqual(env['REGISTRY_TOKEN'],'${{ github.token }}')
        self.assertIn('vars.PA5_APPROVED_REMOTE_DIGEST',env['PA5_REQUESTED_REMOTE_DIGEST'])
        self.assertFalse(job['concurrency']['cancel-in-progress']=='true')

    def test_existing_three_jobs_are_preserved(self):
        existing=yaml.load((ROOT/'.github/workflows/pr-regressions.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(set(existing['jobs']),{'python-security','ssalfer-node','supply-chain-config'})

    def test_consumer_rejects_main_daemon_before_any_docker_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);calls=root/'calls.jsonl';stub=root/'docker'
            stub.write_text('#!/usr/bin/env python3\nimport os,sys,json\nwith open(os.environ["PA5_TEST_CALLS"],"a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\nif sys.argv[1]=="info":print(json.dumps(dict(ID="main",OSType="linux",Architecture="x86_64",DriverStatus=[["driver-type","io.containerd.snapshotter.v1"]])))\n')
            stub.chmod(0o755)
            digest='sha256:'+'1'*64
            env=dict(PATH=str(root)+os.pathsep+os.environ['PATH'],PA5_RUNNER_APPROVED='yes',PA5_PROTECTED_ENGINE_ID='main',PA5_APPROVED_REMOTE_DIGEST=digest,PA5_REQUESTED_REMOTE_DIGEST=digest,PA5_SKOPEO_SHA256='0'*64,REGISTRY_TOKEN='SYNTHETIC_TEST_ONLY',PA5_TEST_CALLS=str(calls))
            result=subprocess.run(['sh',str(CI/'pa5-ci-verify.sh')],env=env,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            invocations=[json.loads(line) for line in calls.read_text().splitlines()]
            self.assertTrue(invocations)
            self.assertTrue(all(command[0] in {'info','image','ps','volume'} for command in invocations))
            self.assertTrue(all(command[1:2] in [['ls'],['--format'],['-aq']] for command in invocations))
            self.assertNotIn(b'SYNTHETIC_TEST_ONLY',result.stdout+result.stderr)

    def run_failed_consumer(self, scenario):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name);calls=root/'calls.jsonl';auth=root/'auth-path'
        docker=root/'docker'
        docker.write_text("""#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:];scenario=os.environ['PA5_TEST_SCENARIO'];root=Path(os.environ['PA5_TEST_ROOT'])
with (root/'calls.jsonl').open('a') as f:f.write(json.dumps(args)+'\\n')
if args[0]=='info':
    if args[-1]=='{{json .}}':print(json.dumps(dict(ID='ci',OSType='linux',Architecture='x86_64',DriverStatus=[['driver-type','io.containerd.snapshotter.v1']])))
    else:
        counter=root/'id-count';n=int(counter.read_text())+1 if counter.exists() else 1;counter.write_text(str(n))
        if scenario=='endpoint-change':print('main')
        elif scenario=='cleanup-error' and n>1:sys.exit(9)
        else:print('ci')
elif args[:2]==['image','ls']:
    if scenario=='discovery-error':sys.exit(8)
elif args[0] in {'ps','volume'}:pass
elif args[0]=='version':print('fixture-engine')
elif args[0]=='login':
    sys.stdin.read();auth=Path(os.environ['DOCKER_CONFIG']);(auth/'config.json').write_text('{"auths":{}}');(root/'auth-path').write_text(str(auth))
elif args[:2]==['container','inspect']:sys.exit(1)
else:sys.exit(91)
""")
        skopeo=root/'skopeo'
        skopeo.write_text("""#!/usr/bin/env python3
import os,sys,json
from pathlib import Path
args=sys.argv[1:];root=Path(os.environ['PA5_TEST_ROOT'])
with (root/'skopeo-calls').open('a') as f:f.write(json.dumps(args)+'\\n')
if args==['--version']:print('fixture-skopeo');sys.exit(0)
if os.environ['PA5_TEST_SCENARIO']=='bad-layout':
    target=Path(args[-1].removeprefix('oci:').rsplit(':',1)[0]);target.mkdir(parents=True)
    (target/'oci-layout').write_text('{"imageLayoutVersion":"1.0.0"}')
    (target/'index.json').write_text('{"schemaVersion":2,"manifests":[]}')
    sys.exit(0)
sys.exit(7)
""")
        docker.chmod(0o755);skopeo.chmod(0o755)
        digest='sha256:'+'1'*64
        env=dict(PATH=str(root)+os.pathsep+os.environ['PATH'],PA5_RUNNER_APPROVED='yes',PA5_PROTECTED_ENGINE_ID='main',PA5_APPROVED_REMOTE_DIGEST=digest,PA5_REQUESTED_REMOTE_DIGEST=digest,PA5_SKOPEO_SHA256=hashlib.sha256(skopeo.read_bytes()).hexdigest(),REGISTRY_TOKEN='SYNTHETIC_TEST_ONLY',GITHUB_ACTOR='fixture-user',PA5_TEST_ROOT=str(root),PA5_TEST_SCENARIO=scenario)
        result=subprocess.run(['sh',str(CI/'pa5-ci-verify.sh')],env=env,capture_output=True)
        invocations=[json.loads(line) for line in calls.read_text().splitlines()]
        self.assertNotIn(b'SYNTHETIC_TEST_ONLY',result.stdout+result.stderr)
        self.assertFalse(any(c[0] in {'pull','run','rm'} or c[:2]==['image','rm'] for c in invocations))
        if auth.exists():self.assertFalse(Path(auth.read_text()).exists(),'temporary auth must always be removed')
        return result,invocations

    def test_resource_discovery_failure_is_not_an_empty_engine(self):
        result,calls=self.run_failed_consumer('discovery-error')
        self.assertEqual(result.returncode,8)
        self.assertNotIn('login',[c[0] for c in calls])

    def test_auth_config_cannot_redirect_commands_to_another_engine(self):
        result,calls=self.run_failed_consumer('endpoint-change')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('login',[c[0] for c in calls])

    def test_registry_download_failure_stops_before_docker_pull(self):
        result,calls=self.run_failed_consumer('download-error')
        self.assertEqual(result.returncode,7)
        self.assertIn('login',[c[0] for c in calls])
        self.assertNotIn(b'PA5_REGISTRY_DOWNLOAD_IDENTITY_AND_SYNTHETIC_SMOKE_OK',result.stdout)

    def test_corrupt_download_is_not_replaced_by_a_docker_fallback(self):
        result,calls=self.run_failed_consumer('bad-layout')
        self.assertEqual(result.returncode,2)
        self.assertIn('login',[c[0] for c in calls])

    def test_auth_removed_and_original_failure_retained_when_cleanup_fails(self):
        result,calls=self.run_failed_consumer('cleanup-error')
        self.assertEqual(result.returncode,7)
        self.assertIn(b'refusing Docker cleanup',result.stderr)

    def test_catalog_binds_the_previously_approved_binary_and_core(self):
        catalog=json.loads((CI/'pa5-supply-catalog.json').read_text());native=json.loads((ROOT/'docs/security/ss09/native-pa5.json').read_text())
        self.assertEqual(catalog['local_index_digest'],native['image_identity']['index']['digest'])
        self.assertEqual(catalog['config_digest'],native['image_identity']['config_digest'])
        self.assertEqual(catalog['rootfs_diff_ids'],native['image_identity']['rootfs']['Layers'])
        self.assertEqual(catalog['protected_payloads']['usr/lib/x86_64-linux-gnu/libgdal.so.36.3.10.3'],native['library']['sha256'])
        self.assertIsNone(catalog['remote_digest']);self.assertFalse(catalog['remote_publication_verified'])

    def test_compose_activation_requires_a_parameter_and_preserves_base_policy(self):
        override=yaml.safe_load((CI/'compose.ghcr.yml').read_text())['services']['db']
        self.assertEqual(override['pull_policy'],'never');self.assertIn('${PA5_GHCR_IMAGE:?',override['image'])
        base=yaml.safe_load((ROOT/'docker-compose.yml').read_text())['services']
        self.assertIn('software-pa-libgdal36-candidate:20261117-pa5@sha256:',base['db']['image'])
        self.assertEqual(base['pgadmin']['profiles'],['admin-tools'])


if __name__=='__main__':unittest.main()
