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

    def test_wrong_visibility_or_repository_fails(self):
        values = [{'visibility': 'public', 'repository': {'full_name': 'JPonce-23/Software-PA'}},
                  {'visibility': 'private', 'repository': {'full_name': 'other/repo'}}]
        for value in values:
            with patch.dict(os.environ, {'GH_TOKEN': 'dummy'}), patch.object(registry, 'request',
                    return_value=(200, {}, json.dumps(value).encode())):
                with self.assertRaises(ValueError):
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
