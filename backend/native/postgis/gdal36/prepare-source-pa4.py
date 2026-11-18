"""Prepare the immutable Debian -> pa2 -> pa3 -> additional pa4 source chain.

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
spec = json.loads((HERE / 'backport-pa4.json').read_text())
loader = importlib.util.spec_from_file_location('preserved_pa3_preparer', HERE / 'prepare-source.py')
parent = importlib.util.module_from_spec(loader)
loader.loader.exec_module(parent)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def integrity():
    parent.chain_integrity()
    for name, key in [('prepare-source.py', 'parent_preparer_sha256'),
                      ('backport-pa3.json', 'parent_manifest_sha256'),
                      ('security-metadata-pa3.patch', 'parent_patch_sha256'),
                      (spec['additional_patch'], 'additional_patch_sha256')]:
        if sha(HERE / name) != spec[key]:
            raise ValueError('PA4_CHAIN_DRIFT: ' + name)

def hashes(phase):
    result = parent.phase_hashes(phase if phase != 'pa4' else 'pa3')
    for name, values in spec['files'].items():
        result[name] = values['after' if phase == 'pa4' else 'before'] if name not in result or phase == 'pa4' else result[name]
    return result

def verify(root, phase):
    integrity()
    for name, expected in hashes(phase).items():
        path = root / name
        if path.is_symlink() or not path.is_file() or sha(path) != expected:
            raise ValueError('PA4_SOURCE_' + phase.upper() + '_DRIFT: ' + name)

def apply(root, debian=False):
    verify(root, 'original')
    parent.apply(root, debian)
    verify(root, 'pa3')
    parent._patch(root, spec['additional_patch'], debian, 'software-pa-enumeration-pa4.patch')
    verify(root, 'pa4')
    print('GDAL36_PA2_PA3_PA4_SOURCE_OK', len(hashes('pa4')))

def record(root, phase, output):
    verify(root, phase)
    if output.exists():
        raise ValueError('EVIDENCE_ALREADY_EXISTS')
    output.write_text(json.dumps(dict(source_phase=phase, local_version=spec['local_version'],
        scope='Source hash attestation only; not native validation',
        pa2_patch_sha256=parent.spec['adapted_patch_sha256'],
        pa3_patch_sha256=spec['parent_patch_sha256'],
        pa4_patch_sha256=spec['additional_patch_sha256'],files=hashes(phase)),indent=2)+'\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--debian', action='store_true')
    parser.add_argument('--verify-phase', choices=['original','pa2','pa3','pa4'])
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    if args.record and not args.verify_phase:
        parser.error('--record requires --verify-phase')
    if args.verify_phase:
        if args.record: record(args.source, args.verify_phase, args.record)
        else: verify(args.source, args.verify_phase)
    else: apply(args.source, args.debian)
