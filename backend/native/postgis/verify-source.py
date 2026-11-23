"""Apply the reviewed backport only to exact known source bytes; no network/build."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify_tree(root, manifest, phase):
    for name, hashes in manifest['files'].items():
        p=root/name
        if p.is_symlink() or not p.is_file() or digest(p)!=hashes[phase]:
            raise ValueError('source mismatch: '+name)

def apply(root):
    here=Path(__file__).resolve().parent
    manifest=json.loads((here/'backport.json').read_text())
    patch=here/'CVE-2026-73515.patch'
    if digest(patch)!=manifest['adapted_patch_sha256'] or digest(here/'upstream-stable36.patch')!=manifest['upstream_patch_sha256']:
        raise ValueError('patch integrity failure')
    verify_tree(root,manifest,'before')
    subprocess.run(['patch','--batch','--fuzz=0','--no-backup-if-mismatch','-p1','-d',str(root),'-i',str(patch)],check=True,timeout=30)
    verify_tree(root,manifest,'after')
    print('POSTGIS_BACKPORT_SOURCE_OK (not a binary attestation)')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);args=parser.parse_args();apply(args.source.resolve())
