"""Prepare the immutable Debian -> pa2 -> pa3 -> pa4 -> additional pa5 source chain.

Source patching/verification only. This tool never builds packages or images.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = json.loads((HERE / 'backport-pa5.json').read_text())
loader = importlib.util.spec_from_file_location('preserved_pa4_preparer', HERE / 'prepare-source-pa4.py')
parent = importlib.util.module_from_spec(loader)
loader.loader.exec_module(parent)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def integrity():
    parent.integrity()
    for name, key in [('prepare-source-pa4.py', 'parent_preparer_sha256'),
                      ('backport-pa4.json', 'parent_manifest_sha256'),
                      ('security-enumeration-pa4.patch', 'parent_patch_sha256'),
                      (spec['additional_patch'], 'additional_patch_sha256')]:
        if sha(HERE / name) != spec[key]:
            raise ValueError('PA5_CHAIN_DRIFT: ' + name)

def hashes(phase):
    result = parent.hashes(phase if phase != 'pa5' else 'pa4')
    for name, values in spec['files'].items():
        result[name] = values['after' if phase == 'pa5' else 'before'] if name not in result or phase == 'pa5' else result[name]
    return result

def verify(root, phase):
    integrity()
    for name, expected in hashes(phase).items():
        path = root / name
        if path.is_symlink() or not path.is_file() or sha(path) != expected:
            raise ValueError('PA5_SOURCE_' + phase.upper() + '_DRIFT: ' + name)

def apply(root, debian=False):
    verify(root, 'original')
    parent.apply(root, debian)
    verify(root, 'pa4')
    parent.parent._patch(root, spec['additional_patch'], debian, 'software-pa-inventory-pa5.patch')
    verify(root, 'pa5')
    print('GDAL36_PA2_PA3_PA4_PA5_SOURCE_OK', len(hashes('pa5')))

def record(root, phase, output):
    verify(root, phase)
    if output.exists():
        raise ValueError('EVIDENCE_ALREADY_EXISTS')
    output.write_text(json.dumps(dict(source_phase=phase, local_version=spec['local_version'],
        scope='Source hash attestation only; not native validation',
        pa2_patch_sha256=parent.parent.spec['adapted_patch_sha256'],
        pa3_patch_sha256=parent.spec['parent_patch_sha256'],
        pa4_patch_sha256=spec['parent_patch_sha256'],
        pa5_patch_sha256=spec['additional_patch_sha256'],files=hashes(phase)),indent=2)+'\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--debian', action='store_true')
    parser.add_argument('--verify-phase', choices=['original','pa2','pa3','pa4','pa5'])
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    if args.record and not args.verify_phase:
        parser.error('--record requires --verify-phase')
    if args.verify_phase:
        if args.record: record(args.source, args.verify_phase, args.record)
        else: verify(args.source, args.verify_phase)
    else: apply(args.source, args.debian)
