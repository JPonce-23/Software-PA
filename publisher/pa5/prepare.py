"""Verify F2-E1 bytes and derive a deterministic metadata-only candidate. No rebuild."""
import argparse
import copy
import gzip
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from pa5_supply import require, validate_layout, digest_bytes

HERE = Path(__file__).resolve().parent
SOURCE_COMMIT = 'ae9cd6021b15d45f4091ab9854d394348cacfbc0'
VERSION = '3.10.3+dfsg-1+pa5'
TAG = '3.10.3-dfsg-1-pa5'  # OCI tags cannot contain '+'.
SOURCE_URL = 'https://github.com/JPonce-23/Software-PA'
CATALOG = json.loads((HERE / 'pa5-supply-catalog.json').read_text())


def verify_imports():
    record = json.loads((HERE / 'imported-files.json').read_text())
    require(record['commit'] == SOURCE_COMMIT, 'SOURCE_COMMIT_CHANGED')
    for name, entry in record['files'].items():
        require(hashlib.sha256((HERE / Path(name).name).read_bytes()).hexdigest() == entry['sha256'],
                'IMPORTED_VERIFIER_CHANGED: ' + name)


def unpack(archive, root):
    h = hashlib.sha256()
    with Path(archive).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    require(h.hexdigest() == CATALOG['archive_sha256'], 'SOURCE_ARCHIVE_HASH')
    require(Path(archive).stat().st_size == CATALOG['archive_size_bytes'], 'SOURCE_ARCHIVE_SIZE')
    root.mkdir(parents=True, exist_ok=False)
    seen = set()
    with tarfile.open(archive, 'r:') as tar:
        for member in tar:
            require(member.name not in seen, 'DUPLICATE_ARCHIVE_PATH')
            seen.add(member.name)
            require(member.name in {'index.json', 'oci-layout', 'manifest.json', 'blobs', 'blobs/sha256'} or
                    re.fullmatch(r'blobs/sha256/[0-9a-f]{64}', member.name), 'UNSAFE_ARCHIVE_PATH')
            if member.isdir():
                continue
            require(member.isfile(), 'UNSAFE_ARCHIVE_TYPE')
            target = root / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, target.open('xb') as out:
                for chunk in iter(lambda: source.read(1048576), b''):
                    out.write(chunk)
    return validate_layout(root, CATALOG['local_index_digest'], CATALOG)


def blob(root, digest):
    require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', digest)), 'INVALID_DIGEST')
    return root / 'blobs' / 'sha256' / digest.split(':')[1]


def put(root, obj, media_type):
    data = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    digest = digest_bytes(data)
    blob(root, digest).write_bytes(data)
    return {'mediaType': media_type, 'digest': digest, 'size': len(data)}


def derive(root):
    original = json.loads(blob(root, CATALOG['platform_manifest_digest']).read_bytes())
    config = json.loads(blob(root, CATALOG['config_digest']).read_bytes())
    updated = copy.deepcopy(config)
    labels = updated.setdefault('config', {}).setdefault('Labels', {})
    labels.update({'org.opencontainers.image.source': SOURCE_URL,
                   'org.opencontainers.image.revision': SOURCE_COMMIT,
                   'org.opencontainers.image.version': VERSION,
                   'org.software-pa.f2e1.index': CATALOG['local_index_digest']})
    manifest = copy.deepcopy(original)
    manifest['config'] = put(root, updated, original['config']['mediaType'])
    # The historical attestation describes the historical manifest, never this candidate.
    desc = put(root, manifest, 'application/vnd.oci.image.manifest.v1+json')
    require(manifest['layers'] == original['layers'], 'LAYERS_CHANGED')
    require(updated['rootfs'] == config['rootfs'], 'ROOTFS_CHANGED')
    restored = copy.deepcopy(updated)
    restored['config']['Labels'] = config.get('config', {}).get('Labels', {})
    if 'Labels' not in config.get('config', {}):
        restored['config'].pop('Labels')
    require(restored == config, 'NON_LABEL_CONFIG_CHANGE')
    return dict(schema_version=1, source_commit=SOURCE_COMMIT, version=VERSION, tag=TAG,
                source_index=CATALOG['local_index_digest'], source_config=CATALOG['config_digest'],
                source_archive_sha256=CATALOG['archive_sha256'], candidate=desc,
                candidate_config=manifest['config']['digest'], platform='linux/amd64',
                rootfs_unchanged=True, layers_unchanged=True,
                historical_attestation_applies_to_candidate=False)


def docker_archive(root, report, target):
    """Classic docker-save archive, with verified uncompressed layers, for any Docker store."""
    manifest = json.loads(blob(root, report['candidate']['digest']).read_bytes())
    def add(tar, name, data):
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(data))
    with tarfile.open(target, 'w') as tar:
        config_name = report['candidate_config'].split(':')[1] + '.json'
        add(tar, config_name, blob(root, report['candidate_config']).read_bytes())
        names = []
        for layer, diff_id in zip(manifest['layers'], CATALOG['rootfs_diff_ids'], strict=True):
            name = diff_id.split(':')[1] + '/layer.tar'
            names.append(name)
            if names.count(name) > 1:  # repeated empty layers share bytes
                continue
            path = blob(root, layer['digest'])
            with gzip.open(path, 'rb') if layer['mediaType'].endswith('+gzip') else path.open('rb') as src:
                data = src.read()
            require(digest_bytes(data) == diff_id, 'DOCKER_LAYER_MISMATCH')
            add(tar, name, data)
        add(tar, 'manifest.json', json.dumps([{'Config': config_name, 'RepoTags': ['pa5-publish-candidate:verified'],
                                             'Layers': names}], sort_keys=True).encode())


def prepare(archive, output, make_docker=False):
    verify_imports()
    output.mkdir(parents=True, exist_ok=False)
    verified = unpack(archive, output / 'oci')
    report = derive(output / 'oci')
    (output / 'source-verification.json').write_text(json.dumps(verified, indent=2) + '\n')
    (output / 'candidate.json').write_text(json.dumps(report, indent=2) + '\n')
    if make_docker:
        docker_archive(output / 'oci', report, output / 'candidate.docker.tar')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--docker-archive', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, args.output, args.docker_archive), indent=2))
