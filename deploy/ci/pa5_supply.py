"""Offline PA5 identity contracts. Registry digest is approved separately from local ID."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

REPOSITORY = 'ghcr.io/jponce-23/software-pa-native-postgis'
INDEX_TYPES = {'application/vnd.oci.image.index.v1+json',
               'application/vnd.docker.distribution.manifest.list.v2+json'}
MANIFEST_TYPES = {'application/vnd.oci.image.manifest.v1+json',
                  'application/vnd.docker.distribution.manifest.v2+json'}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest_bytes(value):
    return 'sha256:' + hashlib.sha256(value).hexdigest()


def digest_stream(stream):
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1048576), b''):
        value.update(chunk)
    return 'sha256:' + value.hexdigest()


def reference(approved, requested):
    require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', approved)), 'APPROVED_DIGEST_REQUIRED')
    require(requested == approved, 'REQUESTED_DIGEST_NOT_APPROVED')
    return REPOSITORY + '@' + approved


def engine_contract(info, protected_id, images, containers, volumes):
    require(bool(protected_id), 'PROTECTED_ENGINE_ID_REQUIRED')
    require(bool(info.get('ID')) and info['ID'] != protected_id, 'ENGINE_NOT_INDEPENDENT')
    require(info.get('OSType') == 'linux' and info.get('Architecture') in {'x86_64', 'amd64'},
            'ENGINE_PLATFORM_MISMATCH')
    require(['driver-type', 'io.containerd.snapshotter.v1'] in info.get('DriverStatus', []),
            'CONTAINERD_STORE_REQUIRED')
    require(not images.strip() and not containers.strip() and not volumes.strip(), 'ENGINE_NOT_EMPTY')


def validate_layout(root, index_digest, catalog):
    """Verify all reachable OCI descriptors, exact platform manifest, rootfs and final payloads."""
    root = Path(root)
    require(not root.is_symlink(), 'LAYOUT_SYMLINK')
    require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', index_digest)), 'INDEX_DIGEST_INVALID')
    visited = set()

    def path(digest):
        require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', digest)), 'BLOB_DIGEST_INVALID')
        p = root / 'blobs' / 'sha256' / digest.split(':')[1]
        require(not any(q.is_symlink() for q in [p, p.parent, p.parent.parent]), 'BLOB_SYMLINK')
        require(p.is_file(), 'BLOB_MISSING')
        return p

    def visit(desc):
        p = path(desc['digest'])
        require(p.stat().st_size == desc['size'], 'BLOB_SIZE_MISMATCH')
        with p.open('rb') as stream:
            require(digest_stream(stream) == desc['digest'], 'BLOB_HASH_MISMATCH')
        if desc['digest'] in visited:
            return
        visited.add(desc['digest'])
        if desc['mediaType'] in INDEX_TYPES | MANIFEST_TYPES:
            obj = json.loads(p.read_text())
            for child in obj.get('manifests', []):
                visit(child)
            if 'config' in obj:
                visit(obj['config'])
            for child in obj.get('layers', []):
                visit(child)

    require(json.loads((root / 'oci-layout').read_text()) == {'imageLayoutVersion': '1.0.0'},
            'OCI_LAYOUT_VERSION')
    wrapper = json.loads((root / 'index.json').read_text())
    roots = [d for d in wrapper['manifests'] if d['digest'] == index_digest]
    require(len(roots) == 1, 'APPROVED_INDEX_MISSING')
    visit(roots[0])
    index = json.loads(path(index_digest).read_text())
    # A changed outer-index hash is never treated as the local Engine ID.
    # Its child descriptors must still equal the entire reviewed set, including attestation.
    require(index['manifests'] == catalog['index_manifests'], 'INDEX_CHILDREN_CHANGED')
    selected = [d for d in index['manifests'] if d.get('platform') == {'os': 'linux', 'architecture': 'amd64'}]
    require(len(selected) == 1 and selected[0]['digest'] == catalog['platform_manifest_digest'],
            'PLATFORM_MANIFEST_MISMATCH')
    manifest = json.loads(path(selected[0]['digest']).read_text())
    require(manifest['config']['digest'] == catalog['config_digest'], 'CONFIG_MISMATCH')
    require(manifest['layers'] == catalog['layers'], 'ORDERED_LAYERS_CHANGED')
    config = json.loads(path(manifest['config']['digest']).read_text())
    require(config['os'] == 'linux' and config['architecture'] == 'amd64', 'CONFIG_PLATFORM_MISMATCH')
    require(config['rootfs']['diff_ids'] == catalog['rootfs_diff_ids'], 'ROOTFS_CHANGED')
    wanted = catalog['protected_payloads']
    effective = {}
    status = None
    for layer, diff_id in zip(manifest['layers'], config['rootfs']['diff_ids'], strict=True):
        p = path(layer['digest'])
        with gzip.open(p, 'rb') if layer['mediaType'].endswith('+gzip') else p.open('rb') as stream:
            require(digest_stream(stream) == diff_id, 'LAYER_DIFF_ID_MISMATCH')
        with tarfile.open(p, 'r|*') as tar:
            for member in tar:
                name = member.name.removeprefix('./').rstrip('/')
                parts = PurePosixPath(name).parts
                require(not name.startswith('/') and '..' not in parts, 'UNSAFE_LAYER_PATH')
                parent, _, leaf = name.rpartition('/')
                if leaf.startswith('.wh.'):
                    removed = parent if leaf == '.wh..wh..opq' else (parent + '/' + leaf[4:]).lstrip('/')
                    for target in list(effective):
                        if target == removed or target.startswith(removed + '/'):
                            effective.pop(target)
                    if 'var/lib/dpkg/status' == removed or 'var/lib/dpkg/status'.startswith(removed + '/'):
                        status = None
                if name in wanted:
                    effective.pop(name, None)
                    if member.isfile():
                        with tar.extractfile(member) as stream:
                            effective[name] = digest_stream(stream).removeprefix('sha256:')
                if name == 'var/lib/dpkg/status':
                    require(member.isfile() and member.size < 16 * 1024 * 1024, 'DPKG_STATUS_TYPE')
                    status = tar.extractfile(member).read().decode()
                if member.issym() or member.islnk():
                    for target in list(effective):
                        if target.startswith(name + '/'):
                            effective.pop(target)
    require(effective == wanted, 'PROTECTED_PAYLOAD_MISMATCH')
    packages = {}
    require(status is not None, 'DPKG_STATUS_MISSING')
    for paragraph in status.split('\n\n'):
        values = dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
        if values.get('Status') == 'install ok installed':
            packages[values['Package']] = values.get('Version')
    require(all(packages.get(p) == version for p, version in catalog['package_versions'].items()),
            'INSTALLED_PACKAGE_MISMATCH')
    return dict(state='PASS',scope='offline OCI bytes and final-layer packages; not Engine import or smoke',
                supplied_index_digest=index_digest,local_index_digest=catalog['local_index_digest'],
                platform='linux/amd64',blobs=len(visited),layers=len(manifest['layers']),
                protected_payloads=effective,packages={p: packages[p] for p in catalog['package_versions']})


def validate_inspect(rows, image, remote_digest, catalog):
    require(len(rows) == 1, 'ENGINE_INSPECT_AMBIGUOUS')
    row = rows[0]
    require(image == REPOSITORY + '@' + remote_digest, 'ENGINE_REFERENCE_CHANGED')
    require(row.get('Descriptor', {}).get('digest') == remote_digest, 'ENGINE_INDEX_MISMATCH')
    require(row['Os'] == 'linux' and row['Architecture'] == 'amd64', 'ENGINE_IMAGE_PLATFORM')
    require(row['Id'] in {remote_digest, catalog['config_digest']}, 'ENGINE_IMAGE_ID_UNEXPECTED')
    require(row['RootFS'] == {'Type': 'layers', 'Layers': catalog['rootfs_diff_ids']}, 'ENGINE_ROOTFS_MISMATCH')
    require(image in row.get('RepoDigests', []), 'ENGINE_COMPOSE_DIGEST_NOT_RESOLVED')
    # Id semantics vary by image store. The independently validated index/config/rootfs are authoritative.
    return dict(state='PASS',engine_image_id=row['Id'],registry_index_digest=remote_digest,
                local_recorded_image_id=catalog['local_index_digest'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=Path(__file__).with_name('pa5-supply-catalog.json'))
    sub = parser.add_subparsers(dest='command', required=True)
    ref = sub.add_parser('reference');ref.add_argument('approved');ref.add_argument('requested')
    layout = sub.add_parser('layout');layout.add_argument('root', type=Path);layout.add_argument('digest')
    inspect = sub.add_parser('inspect');inspect.add_argument('file', type=Path);inspect.add_argument('digest')
    engine = sub.add_parser('engine');engine.add_argument('file', type=Path);engine.add_argument('protected_id')
    engine.add_argument('images');engine.add_argument('containers');engine.add_argument('volumes')
    args = parser.parse_args()
    try:
        catalog = json.loads(args.catalog.read_text())
        if args.command == 'reference':
            print(reference(args.approved, args.requested));return 0
        if args.command == 'layout':result = validate_layout(args.root, args.digest, catalog)
        elif args.command == 'inspect':result = validate_inspect(json.loads(args.file.read_text()), REPOSITORY + '@' + args.digest, args.digest, catalog)
        else:
            engine_contract(json.loads(args.file.read_text()), args.protected_id, args.images, args.containers, args.volumes)
            result = dict(state='PASS', scope='different Engine identity and empty store; authorization required separately')
        print(json.dumps(result, sort_keys=True));return 0
    except (ValueError, OSError, KeyError, TypeError, EOFError, tarfile.TarError):
        print(json.dumps(dict(state='FAIL',command=args.command)));return 2


if __name__ == '__main__':
    raise SystemExit(main())
