"""Prepare the exact Debian -> preserved +pa2 -> additional +pa3 source chain.

No downloads, compilation, package installation or running-library changes.
"""
import argparse
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = json.loads((HERE / 'backport.json').read_text())  # Historical +pa2, immutable.
pa3 = json.loads((HERE / 'backport-pa3.json').read_text())
EXPECTED_HDF_FUNCTIONS = {
    'frmts/hdf4/hdf-eos/GDapi.c': {'GDSDfldsrch', 'GDfieldinfo', 'GDnentries'},
    'frmts/hdf4/hdf-eos/SWapi.c': {'SWSDfldsrch', 'SWfinfo', 'SWinqfields', 'SWnentries'},
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_functions(before, after):
    """Upstream function names begin at column zero, on their own line."""
    old, new = before.splitlines(), after.splitlines()
    names = set()
    for tag, _, _, start, _ in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        headers = list(re.finditer(r'^([A-Za-z_]\w*)\(', '\n'.join(new[:start + 1]), re.M))
        if not headers:
            raise ValueError('CHANGE_OUTSIDE_KNOWN_C_FUNCTION')
        names.add(headers[-1][1])
    return names


def verify_hdf_functions(before, after):
    """Retain the original +pa2 scope gate, including the SWinqfields correction."""
    for name, expected in EXPECTED_HDF_FUNCTIONS.items():
        if changed_functions(before[name], after[name]) != expected:
            raise ValueError('UPSTREAM_HDF_FUNCTION_SCOPE_MISMATCH: ' + name)


def verify_pa3_functions(before, after):
    for name, expected in pa3['function_scope'].items():
        old, new = before[name], after[name]
        if name in pa3['allowed_prologue_changes']:
            # The sole allowed non-function edit is the checked-allocation include.
            first_function = re.search(r'^([A-Za-z_]\w*)\(', old, re.M)
            boundary = first_function.start()
            expected_prefix = old[:boundary].replace('#include <errno.h>',
                                                     '#include <errno.h>\n#include <limits.h>')
            new_boundary = re.search(r'^([A-Za-z_]\w*)\(', new, re.M).start()
            if new[:new_boundary] != expected_prefix:
                raise ValueError('PA3_PROLOGUE_DRIFT: ' + name)
            old = old.replace('#include <errno.h>', '#include <errno.h>\n#include <limits.h>', 1)
        if changed_functions(old, new) != set(expected):
            raise ValueError('PA3_FUNCTION_SCOPE_MISMATCH: ' + name)


def chain_integrity():
    if sha(HERE / 'backport.json') != pa3['parent_manifest_sha256']:
        raise ValueError('PA2_MANIFEST_DRIFT')
    if (sha(HERE / 'security-backport.patch') != spec['adapted_patch_sha256'] or
            spec['adapted_patch_sha256'] != pa3['parent_patch_sha256']):
        raise ValueError('PA2_PATCH_DRIFT')
    if sha(HERE / pa3['additional_patch']) != pa3['additional_patch_sha256']:
        raise ValueError('PA3_PATCH_DRIFT')
    for upstream in spec['upstream']:
        if sha(HERE / upstream['file']) != upstream['sha256']:
            raise ValueError('UPSTREAM_PATCH_DRIFT: ' + upstream['file'])


def phase_hashes(phase):
    result = {name: record['before' if phase == 'original' else 'after']
              for name, record in spec['files'].items()}
    for name, record in pa3['files'].items():
        result[name] = record[{'original': 'original', 'pa2': 'before', 'pa3': 'after'}[phase]]
    return result


def verify_phase(root, phase):
    for name, expected in phase_hashes(phase).items():
        path = root / name
        if path.is_symlink() or not path.is_file() or sha(path) != expected:
            raise ValueError('SOURCE_' + phase.upper() + '_DRIFT: ' + name)


def _patch(root, filename, debian, target_name):
    if debian:
        target = root / 'debian/patches' / target_name
        if target.exists():
            raise ValueError('QUILT_TARGET_ALREADY_EXISTS: ' + target_name)
        target.write_bytes((HERE / filename).read_bytes())
        with (root / 'debian/patches/series').open('a') as stream:
            stream.write(target_name + '\n')
        subprocess.run(['dpkg-source', '--before-build', '.'], cwd=root, check=True)
    else:
        subprocess.run(['patch', '-p1', '--batch', '--forward', '--fuzz=0',
                        '--no-backup-if-mismatch', '-i', str(HERE / filename)],
                       cwd=root, check=True)


def apply(root, debian=False):
    root = Path(root)
    chain_integrity()  # Validate both patches BEFORE any source modification.
    verify_phase(root, 'original')
    before = {name: (root / name).read_text() for name in EXPECTED_HDF_FUNCTIONS}
    _patch(root, 'security-backport.patch', debian, 'software-pa-security.patch')
    verify_phase(root, 'pa2')
    verify_hdf_functions(before, {name: (root / name).read_text() for name in before})
    parent = {name: (root / name).read_text() for name in pa3['function_scope']}
    _patch(root, pa3['additional_patch'], debian, 'software-pa-hdf-metadata-pa3.patch')
    verify_phase(root, 'pa3')
    verify_pa3_functions(parent, {name: (root / name).read_text() for name in parent})
    print('GDAL36_PA2_CHAIN_AND_PA3_SOURCE_OK', len(phase_hashes('pa3')))


def record_phase(root, phase, output):
    chain_integrity()
    verify_phase(root, phase)
    record = {
        'source_phase': phase,
        'scope': 'Source hash attestation only; not compiled/runtime proof',
        'local_version': pa3['local_version'],
        'pa2_manifest_sha256': pa3['parent_manifest_sha256'],
        'pa2_patch_sha256': pa3['parent_patch_sha256'],
        'pa3_patch_sha256': pa3['additional_patch_sha256'],
        'files': phase_hashes(phase),
    }
    if output.exists():
        raise ValueError('EVIDENCE_ALREADY_EXISTS: ' + str(output))
    output.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--debian', action='store_true')
    parser.add_argument('--verify-phase', choices=['original', 'pa2', 'pa3'])
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    if args.record and not args.verify_phase:
        parser.error('--record requires --verify-phase')
    if args.verify_phase:
        if args.record:
            record_phase(args.source, args.verify_phase, args.record)
        else:
            chain_integrity()
            verify_phase(args.source, args.verify_phase)
    else:
        apply(args.source, args.debian)
