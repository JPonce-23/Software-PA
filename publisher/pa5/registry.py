"""Minimal fixed-destination GHCR client. No code from the source image is executed here."""
import argparse
import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from prepare import CATALOG, SOURCE_COMMIT, SOURCE_URL, TAG, VERSION, blob, prepare
from pa5_supply import digest_bytes, require

REPOSITORY = 'jponce-23/software-pa-native-postgis'
ROOT = 'https://ghcr.io/v2/' + REPOSITORY
MANIFEST_TYPE = 'application/vnd.oci.image.manifest.v1+json'


class NoCredentialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(newurl.startswith('https://'), 'HTTPS_REDIRECT_REQUIRED')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        redirected.remove_header('Authorization')
        return redirected


def request(url, method='GET', data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.build_opener(NoCredentialRedirect()).open(req, timeout=180) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        # The caller must explicitly handle status. Transport failures always propagate.
        return exc.code, dict(exc.headers), exc.read()


def package_state(allow_absent=False):
    url = 'https://api.github.com/users/JPonce-23/packages/container/software-pa-native-postgis'
    status, _, payload = request(url, headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'software-pa-pa5-publisher'})
    if status == 404 and allow_absent:
        return {'state': 'absent-or-not-readable', 'visibility': None}
    require(status == 200, 'PACKAGE_METADATA_NOT_READABLE')
    obj = json.loads(payload)
    require(obj.get('visibility') == 'private', 'PACKAGE_MUST_BE_PRIVATE')
    require(obj.get('repository', {}).get('full_name', '').lower() == 'jponce-23/software-pa',
            'PACKAGE_REPOSITORY_LINK_REQUIRED')
    return {'visibility': obj['visibility'], 'repository': obj['repository']['full_name']}


class Registry:
    def __init__(self, write=False):
        credential = os.environ['GITHUB_ACTOR'] + ':' + os.environ['GH_TOKEN']
        basic = base64.b64encode(credential.encode()).decode()
        scope = 'repository:' + REPOSITORY + (':pull,push' if write else ':pull')
        url = 'https://ghcr.io/token?' + urllib.parse.urlencode({'service': 'ghcr.io', 'scope': scope})
        status, _, payload = request(url, headers={'Authorization': 'Basic ' + basic})
        require(status == 200, 'REGISTRY_AUTH_FAILED')
        self.token = json.loads(payload)['token']

    def call(self, path, method='GET', data=None, headers=None):
        url = path if path.startswith('https://') else ROOT + path
        parsed = urllib.parse.urlsplit(url)
        require(parsed.scheme == 'https' and parsed.netloc == 'ghcr.io' and
                parsed.path.startswith('/v2/' + REPOSITORY + '/'), 'UNTRUSTED_REGISTRY_URL')
        return request(url, method, data, {'Authorization': 'Bearer ' + self.token,
                       'Accept': MANIFEST_TYPE, **(headers or {})})

    def absent_tag(self):
        status, _, data = self.call('/manifests/' + TAG)
        require(status == 404, 'TAG_EXISTS_OR_LOOKUP_FAILED')
        errors = json.loads(data).get('errors', [])
        require(bool(errors) and all(e.get('code') in {'MANIFEST_UNKNOWN', 'NAME_UNKNOWN'} for e in errors),
                'REGISTRY_ABSENCE_NOT_PROVEN')

    def upload_blob(self, path, digest):
        status, _, _ = self.call('/blobs/' + digest, method='HEAD')
        if status == 200:
            return
        require(status == 404, 'BLOB_LOOKUP_FAILED')
        status, headers, _ = self.call('/blobs/uploads/', method='POST', data=b'')
        require(status == 202, 'BLOB_UPLOAD_START_FAILED')
        location = next(v for k, v in headers.items() if k.lower() == 'location')
        location = urllib.parse.urljoin(ROOT + '/', location)
        location += ('&' if '?' in location else '?') + urllib.parse.urlencode({'digest': digest})
        data = path.read_bytes()
        require(digest_bytes(data) == digest, 'UPLOAD_BLOB_HASH')
        status, _, _ = self.call(location, method='PUT', data=data,
                                 headers={'Content-Type': 'application/octet-stream'})
        require(status == 201, 'BLOB_UPLOAD_FAILED')

    def verify(self, root, report):
        digest = report['candidate']['digest']
        status, _, data = self.call('/manifests/' + digest)
        require(status == 200 and digest_bytes(data) == digest, 'REMOTE_MANIFEST_DIGEST')
        require(data == blob(root, digest).read_bytes(), 'REMOTE_MANIFEST_BYTES')
        status, _, data = self.call('/blobs/' + report['candidate_config'])
        require(status == 200 and digest_bytes(data) == report['candidate_config'], 'REMOTE_CONFIG_DIGEST')
        config = json.loads(data)
        labels = config['config']['Labels']
        require(labels['org.opencontainers.image.source'] == SOURCE_URL, 'REMOTE_SOURCE_LABEL')
        require(labels['org.opencontainers.image.revision'] == SOURCE_COMMIT, 'REMOTE_SOURCE_COMMIT')
        require(labels['org.opencontainers.image.version'] == VERSION, 'REMOTE_VERSION')
        require(config['os'] == 'linux' and config['architecture'] == 'amd64', 'REMOTE_PLATFORM')
        require(config['rootfs']['diff_ids'] == CATALOG['rootfs_diff_ids'], 'REMOTE_ROOTFS')
        status, _, tagged = self.call('/manifests/' + TAG)
        require(status == 200 and digest_bytes(tagged) == digest, 'REMOTE_TAG_DIGEST')
        return {'digest': digest, 'version': VERSION, 'source_commit': SOURCE_COMMIT,
                'platform': 'linux/amd64', 'package': package_state()}

    def publish(self, root, report):
        package_state(allow_absent=True)
        self.absent_tag()
        manifest = json.loads(blob(root, report['candidate']['digest']).read_bytes())
        for desc in [manifest['config'], *manifest['layers']]:
            self.upload_blob(blob(root, desc['digest']), desc['digest'])
        # Check immediately before PUT as well; concurrency serializes this workflow.
        self.absent_tag()
        data = blob(root, report['candidate']['digest']).read_bytes()
        status, _, _ = self.call('/manifests/' + TAG, method='PUT', data=data,
            headers={'Content-Type': MANIFEST_TYPE, 'If-None-Match': '*'})
        require(status == 201, 'MANIFEST_PUBLICATION_FAILED')
        return self.verify(root, report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['publish', 'verify'])
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('approved_digest')
    args = parser.parse_args()
    require(os.environ.get('GITHUB_REPOSITORY') == 'JPonce-23/Software-PA', 'WRONG_REPOSITORY')
    require(os.environ.get('GITHUB_REF') == 'refs/heads/main', 'MAIN_ONLY')
    require(os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch', 'MANUAL_ONLY')
    report = prepare(args.archive, args.output)
    require(args.approved_digest == report['candidate']['digest'], 'NEW_IDENTITY_APPROVAL_REQUIRED')
    registry = Registry(write=args.mode == 'publish')
    if args.mode == 'publish':
        require(os.environ.get('PA5_EXCLUSIVE_WRITER') == 'confirmed', 'EXCLUSIVE_WRITER_REQUIRED')
        result = registry.publish(args.output / 'oci', report)
    else:
        result = registry.verify(args.output / 'oci', report)
    (args.output / 'registry-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
