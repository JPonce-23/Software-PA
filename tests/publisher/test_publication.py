import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'publisher/pa5'))
import prepare
import registry
import controls


class IdentityTests(unittest.TestCase):
    def test_imported_verifiers_match_approved_commit(self):
        prepare.verify_imports()

    def test_wrong_archive_is_rejected_before_unpack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source.tar').write_bytes(b'not approved')
            with self.assertRaisesRegex(ValueError, 'SOURCE_ARCHIVE_HASH'):
                prepare.unpack(root / 'source.tar', root / 'oci')
            self.assertFalse((root / 'oci').exists())

    def test_labels_only_candidate_is_deterministic_and_preserves_execution_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'blobs/sha256').mkdir(parents=True)
            config = {'os': 'linux', 'architecture': 'amd64', 'rootfs': {'diff_ids': ['sha256:layer']},
                      'config': {'Labels': {'historical': 'retained'}, 'Entrypoint': ['entrypoint'],
                                 'Cmd': ['postgres'], 'Env': ['PATH=/bin'], 'User': 'postgres'},
                      'history': [{'created_by': 'historical build'}]}
            manifest = {'schemaVersion': 2, 'mediaType': registry.MANIFEST_TYPE,
                        'config': {'digest': prepare.CATALOG['config_digest'], 'size': 0,
                                   'mediaType': 'application/vnd.oci.image.config.v1+json'},
                        'layers': [{'digest': 'sha256:layer', 'size': 7}]}
            prepare.blob(root, prepare.CATALOG['config_digest']).write_text(json.dumps(config))
            prepare.blob(root, prepare.CATALOG['platform_manifest_digest']).write_text(json.dumps(manifest))
            first = prepare.derive(root)
            second = prepare.derive(root)
            self.assertEqual(first, second)
            candidate = json.loads(prepare.blob(root, first['candidate_config']).read_bytes())
            self.assertEqual(candidate['config']['Entrypoint'], config['config']['Entrypoint'])
            self.assertEqual(candidate['config']['Cmd'], config['config']['Cmd'])
            self.assertEqual(candidate['rootfs'], config['rootfs'])
            self.assertEqual(candidate['history'], config['history'])
            self.assertEqual(candidate['config']['Labels']['historical'], 'retained')
            self.assertEqual(candidate['config']['Labels']['org.opencontainers.image.revision'], prepare.SOURCE_COMMIT)
            self.assertFalse(first['historical_attestation_applies_to_candidate'])


class RegistryTests(unittest.TestCase):
    def client(self):
        return object.__new__(registry.Registry)

    def test_existing_tag_rejected_even_if_same_digest(self):
        client = self.client()
        with patch.object(client, 'call', return_value=(200, {}, b'{}')):
            with self.assertRaisesRegex(ValueError, 'TAG_EXISTS'):
                client.absent_tag()

    def test_auth_failure_and_server_failure_are_not_absence(self):
        for status in [401, 403, 429, 500, 503]:
            with self.subTest(status=status):
                client = self.client()
                with patch.object(client, 'call', return_value=(status, {}, b'{}')):
                    with self.assertRaises(ValueError):
                        client.absent_tag()

    def test_unrelated_404_is_not_absence(self):
        client = self.client()
        with patch.object(client, 'call', return_value=(404, {}, b'{"errors":[{"code":"DENIED"}]}')):
            with self.assertRaisesRegex(ValueError, 'ABSENCE_NOT_PROVEN'):
                client.absent_tag()

    def test_manifest_unknown_allows_first_publication(self):
        client = self.client()
        with patch.object(client, 'call', return_value=(404, {}, b'{"errors":[{"code":"MANIFEST_UNKNOWN"}]}')):
            client.absent_tag()

    def test_registry_upload_cannot_leak_token_to_another_host(self):
        client = self.client()
        client.token = 'dummy-test-token'
        for url in ['https://evil.example/v2/' + registry.REPOSITORY + '/blobs',
                    'https://ghcr.io@evil.example/v2/' + registry.REPOSITORY + '/blobs',
                    'https://ghcr.io/v2/other/package/blobs']:
            with self.subTest(url=url), patch.object(registry, 'request') as request:
                with self.assertRaisesRegex(ValueError, 'UNTRUSTED_REGISTRY_URL'):
                    client.call(url)
                request.assert_not_called()

    def package(self):
        return {'name': 'software-pa-native-postgis', 'package_type': 'container',
                'owner': {'login': 'JPonce-23'}, 'visibility': 'private',
                'repository': {'full_name': 'JPonce-23/Software-PA'}}

    def test_wrong_visibility_or_repository_fails(self):
        values = [dict(self.package(), visibility='public'),
                  dict(self.package(), repository={'full_name': 'other/repo'}),
                  dict(self.package(), repository=None), dict(self.package(), repository={})]
        for value in values:
            with patch.dict(os.environ, {'GH_TOKEN': 'dummy'}), patch.object(registry, 'request',
                    return_value=(200, {}, json.dumps(value).encode())):
                with self.assertRaises(ValueError):
                    registry.package_state()

    def test_private_metadata_uses_authenticated_endpoint_and_job_token(self):
        # Private metadata must use the documented authenticated route.
        def response(url, **kwargs):
            self.assertEqual(url, 'https://api.github.com/user/packages/container/software-pa-native-postgis')
            self.assertEqual(kwargs['headers']['Authorization'], 'Bearer ghs_dummy_job_token')
            self.assertEqual(kwargs['headers']['Accept'], 'application/vnd.github+json')
            return 200, {}, json.dumps(self.package()).encode()
        with patch.dict(os.environ, {'GH_TOKEN': 'ghs_dummy_job_token', 'GITHUB_ACTOR': 'DrMannx'}, clear=True), \
                patch.object(registry, 'request', side_effect=response) as request:
            result = registry.package_state()
        request.assert_called_once()
        self.assertEqual(result['visibility'], 'private')
        self.assertEqual(result['repository'], 'JPonce-23/Software-PA')
        self.assertEqual(result['owner'], 'JPonce-23')
        self.assertEqual(result['metadata_api'], registry.PACKAGE_METADATA_URL)

    def test_authenticated_namespace_cannot_substitute_another_package(self):
        values = [dict(self.package(), owner={'login': 'DrMannx'}),
                  dict(self.package(), owner=None),
                  dict(self.package(), name='another-package'),
                  dict(self.package(), package_type='npm')]
        for value in values:
            with self.subTest(value=value), patch.dict(os.environ, {'GH_TOKEN': 'dummy'}), \
                    patch.object(registry, 'request', return_value=(200, {}, json.dumps(value).encode())):
                with self.assertRaisesRegex(ValueError, 'PACKAGE_IDENTITY_MISMATCH'):
                    registry.package_state()

    def test_metadata_auth_and_service_errors_fail_even_before_publication(self):
        for status in [401, 403, 429, 500, 503]:
            for preflight in [False, True]:
                with self.subTest(status=status, preflight=preflight), \
                        patch.dict(os.environ, {'GH_TOKEN': 'dummy'}), \
                        patch.object(registry, 'request', return_value=(status, {}, b'{}')):
                    with self.assertRaisesRegex(ValueError, 'PACKAGE_METADATA_NOT_READABLE'):
                        registry.package_state(allow_absent=preflight)

    def test_preflight_404_does_not_claim_privacy_or_proven_absence(self):
        with patch.dict(os.environ, {'GH_TOKEN': 'dummy'}), \
                patch.object(registry, 'request', return_value=(404, {}, b'{}')):
            result = registry.package_state(allow_absent=True)
            self.assertIsNone(result['visibility'])
            self.assertEqual(result['state'], 'absent-or-not-readable')
            with self.assertRaisesRegex(ValueError, 'PACKAGE_METADATA_NOT_READABLE'):
                registry.package_state()

    def test_private_metadata_does_not_confuse_repository_visibility(self):
        value = self.package()
        value['repository']['private'] = False
        with patch.dict(os.environ, {'GH_TOKEN': 'dummy'}), \
                patch.object(registry, 'request', return_value=(200, {}, json.dumps(value).encode())):
            self.assertEqual(registry.package_state()['visibility'], 'private')
        value['visibility'] = 'public'
        value['repository']['private'] = True
        with patch.dict(os.environ, {'GH_TOKEN': 'dummy'}), \
                patch.object(registry, 'request', return_value=(200, {}, json.dumps(value).encode())):
            with self.assertRaisesRegex(ValueError, 'PACKAGE_MUST_BE_PRIVATE'):
                registry.package_state()

    def test_post_publication_metadata_must_be_readable(self):
        with patch.dict(os.environ, {'GH_TOKEN': 'dummy'}), patch.object(registry, 'request', return_value=(404, {}, b'{}')):
            with self.assertRaisesRegex(ValueError, 'NOT_READABLE'):
                registry.package_state()

    def test_existing_tag_prevents_any_blob_upload(self):
        client = self.client()
        with patch.object(registry, 'package_state'), patch.object(client, 'absent_tag',
                side_effect=ValueError('TAG_EXISTS')), patch.object(client, 'upload_blob') as upload:
            with self.assertRaises(ValueError):
                client.publish(Path('/unused'), {})
            upload.assert_not_called()


    def test_tag_created_during_blob_upload_prevents_manifest_put(self):
        client = self.client()
        digest = 'sha256:' + 'a' * 64
        report = {'candidate': {'digest': digest}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'blobs/sha256').mkdir(parents=True)
            prepare.blob(root, digest).write_text(json.dumps({'config': {'digest': 'sha256:'+'b'*64},
                                                             'layers': []}))
            with patch.object(registry, 'package_state'), patch.object(client, 'absent_tag',
                    side_effect=[None, ValueError('TAG_CREATED_BY_OTHER_WRITER')]), \
                    patch.object(client, 'upload_blob') as upload, patch.object(client, 'call') as call:
                with self.assertRaisesRegex(ValueError, 'TAG_CREATED_BY_OTHER_WRITER'):
                    client.publish(root, report)
                upload.assert_called_once()
                call.assert_not_called()


class RemoteIntegrityTests(unittest.TestCase):
    def verify(self, change_config=None, corrupt=None):
        config = {'os': 'linux', 'architecture': 'amd64',
                  'rootfs': {'diff_ids': prepare.CATALOG['rootfs_diff_ids']},
                  'config': {'Labels': {'org.opencontainers.image.source': prepare.SOURCE_URL,
                                        'org.opencontainers.image.revision': prepare.SOURCE_COMMIT,
                                        'org.opencontainers.image.version': prepare.VERSION}}}
        if change_config:
            change_config(config)
        config_bytes = json.dumps(config, sort_keys=True).encode()
        config_digest = registry.digest_bytes(config_bytes)
        manifest_bytes = json.dumps({'config': {'digest': config_digest}}, sort_keys=True).encode()
        manifest_digest = registry.digest_bytes(manifest_bytes)
        report = {'candidate': {'digest': manifest_digest}, 'candidate_config': config_digest}
        package = RegistryTests().package()
        replies = {registry.ROOT + '/manifests/' + manifest_digest: manifest_bytes,
                   registry.ROOT + '/blobs/' + config_digest: config_bytes,
                   registry.ROOT + '/manifests/' + prepare.TAG: manifest_bytes,
                   registry.PACKAGE_METADATA_URL: json.dumps(package).encode()}
        if corrupt:
            key = {'manifest': registry.ROOT + '/manifests/' + manifest_digest,
                   'config': registry.ROOT + '/blobs/' + config_digest,
                   'tag': registry.ROOT + '/manifests/' + prepare.TAG}[corrupt]
            replies[key] += b' '
        seen = []
        def response(url, method='GET', data=None, headers=None):
            seen.append(url)
            return 200, {}, replies[url]
        client = object.__new__(registry.Registry)
        client.token = 'dummy-registry-token'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'blobs/sha256').mkdir(parents=True)
            prepare.blob(root, manifest_digest).write_bytes(manifest_bytes)
            with patch.dict(os.environ, {'GH_TOKEN': 'dummy-job-token'}), \
                    patch.object(registry, 'request', side_effect=response):
                result = client.verify(root, report)
        return result, seen

    def test_remote_verification_includes_authenticated_private_package_metadata(self):
        result, seen = self.verify()
        self.assertEqual(result['package']['visibility'], 'private')
        self.assertIn(registry.PACKAGE_METADATA_URL, seen)
        self.assertEqual(result['source_commit'], prepare.SOURCE_COMMIT)

    def test_corrupt_remote_manifest_config_or_tag_remains_rejected(self):
        for target, error in [('manifest', 'REMOTE_MANIFEST_DIGEST'),
                              ('config', 'REMOTE_CONFIG_DIGEST'), ('tag', 'REMOTE_TAG_DIGEST')]:
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, error):
                self.verify(corrupt=target)

    def test_remote_provenance_platform_and_rootfs_remain_mandatory(self):
        changes = [(lambda c: c['config']['Labels'].update({'org.opencontainers.image.source': 'other'}),
                    'REMOTE_SOURCE_LABEL'),
                   (lambda c: c['config']['Labels'].update({'org.opencontainers.image.revision': '0'*40}),
                    'REMOTE_SOURCE_COMMIT'),
                   (lambda c: c['config']['Labels'].update({'org.opencontainers.image.version': 'other'}),
                    'REMOTE_VERSION'),
                   (lambda c: c.update({'architecture': 'arm64'}), 'REMOTE_PLATFORM'),
                   (lambda c: c['rootfs'].update({'diff_ids': []}), 'REMOTE_ROOTFS')]
        for change, error in changes:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.verify(change_config=change)


class EnvironmentTests(unittest.TestCase):
    def fixture(self):
        return ({'protection_rules': [{'type': 'required_reviewers', 'reviewers': [
            {'type': 'User', 'reviewer': {'login': 'JPonce-23'}}]}], 'can_admins_bypass': False,
            'deployment_branch_policy': {'protected_branches': False, 'custom_branch_policies': True}},
            {'branch_policies': [{'name': 'main', 'type': 'branch'}]})

    def test_owner_review_exact_main_only(self):
        controls.validate(*self.fixture())

    def test_implicitly_created_unprotected_environment_is_rejected(self):
        with self.assertRaises(ValueError):
            controls.validate({'protection_rules': []}, {'branch_policies': []})

    def test_other_reviewers_cannot_replace_owner_approval(self):
        env, branches = self.fixture()
        env['protection_rules'][0]['reviewers'].append({'type': 'User', 'reviewer': {'login': 'other'}})
        with self.assertRaises(ValueError):
            controls.validate(env, branches)

    def test_bypass_or_wildcard_branch_is_rejected(self):
        env, branches = self.fixture()
        env['can_admins_bypass'] = True
        with self.assertRaises(ValueError):
            controls.validate(env, branches)
        env, branches = self.fixture()
        branches['branch_policies'][0]['name'] = '*'
        with self.assertRaises(ValueError):
            controls.validate(env, branches)


if __name__ == '__main__':
    unittest.main()
