"""Verify local provenance/integrity and classify npm audit against shipped packages."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FORBIDDEN={'elliptic','crypto-browserify','browserify-sign','create-ecdh'}
BUILD_INPUTS={'package.json','build.cjs','crypto.cjs','entry.cjs','license-sources.json',
              'crypto-build-disabled/package.json','crypto-build-disabled/index.cjs'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify_toolchain(lock):
    packages=lock['packages']
    alias=packages.get('node_modules/crypto-browserify',{})
    if alias!={'resolved':'crypto-build-disabled','link':True}:
        raise ValueError('UNAPPROVED_CRYPTO_TOOLCHAIN')
    local=packages.get('crypto-build-disabled',{})
    if local.get('name')!='@ssalfer/crypto-build-disabled' or local.get('version')!='1.0.0' or local.get('dependencies'):
        raise ValueError('UNAPPROVED_CRYPTO_TOOLCHAIN')
    for name,entry in packages.items():
        if name=='node_modules/crypto-browserify':continue
        if any(name.endswith('node_modules/'+p) for p in FORBIDDEN):
            raise ValueError('FORBIDDEN_TOOLCHAIN_PACKAGE')
def verify(root=ROOT):
    graph=json.loads((root/'runtime-graph.json').read_text());lock=json.loads((root/'package-lock.json').read_text())
    vendor=root.parents[1]/'js/vendor';artifact=vendor/graph['artifact']
    if graph['artifact']!='exceljs-4.4.0-ssalfer.min.js' or sha(artifact)!=graph['sha256'] or sha(root/'package-lock.json')!=graph['package_lock_sha256']:
        raise ValueError('BUNDLE_OR_LOCK_INTEGRITY_FAILURE')
    if (vendor/'exceljs-4.4.0.min.js').exists():raise ValueError('OLD_BUNDLE_STILL_DISTRIBUTED')
    verify_toolchain(lock)
    if set(graph['build_inputs'])!=BUILD_INPUTS:raise ValueError('BUILD_INPUT_DRIFT')
    for name,digest in graph['build_inputs'].items():
        if sha(root/name)!=digest:raise ValueError('BUILD_INPUT_DRIFT')
    packages=graph['packages']
    if not packages or FORBIDDEN & {p['name'] for p in packages}:raise ValueError('FORBIDDEN_RUNTIME_PACKAGE')
    for p in packages:
        if not any(v.get('version')==p['version'] and v.get('integrity')==p['integrity'] and v.get('resolved')==p['resolved'] for v in lock['packages'].values()):
            raise ValueError('RUNTIME_PACKAGE_NOT_LOCKED')
    for p in graph['modules']:
        if Path(p['file']).is_absolute() or '..' in Path(p['file']).parts or any('/'+n+'/' in '/'+p['file'] for n in FORBIDDEN):
            raise ValueError('MODULE_GRAPH_INVALID')
    for name,entry in json.loads((root/'license-sources.json').read_text()).items():
        if sha(root/entry['file'])!=entry['sha256']:raise ValueError('LICENSE_DRIFT')
    return graph,lock

def classify(audit,graph,lock):
    if audit.get('auditReportVersion')!=2 or not isinstance(audit.get('vulnerabilities'),dict) or audit.get('error'):
        raise ValueError('SCA_REPORT_UNAVAILABLE')
    shipped=[];build=[]
    for name,v in audit['vulnerabilities'].items():
        versions={lock['packages'].get(n,{}).get('version') for n in v['nodes']}
        row={'name':name,'severity':v['severity'],'nodes':v['nodes'],'via':v['via']}
        target=shipped if any(p['name']==name and p['version'] in versions for p in graph['packages']) else build
        target.append(row)
    return {'runtime_findings':shipped,'build_or_node_only_findings':build,'scope':'npm advisory snapshot; not native SBOM, reachability proof or risk acceptance'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--audit-file',type=Path);args=parser.parse_args()
    try:
        graph,lock=verify();result={'marker':'EXCELJS_RUNTIME_GRAPH_OK','packages':len(graph['packages']),'modules':len(graph['modules']),'sha256':graph['sha256']}
        if args.audit_file:
            result.update(classify(json.loads(args.audit_file.read_text()),graph,lock))
        print(json.dumps(result,indent=2))
        return 1 if result.get('runtime_findings') or result.get('build_or_node_only_findings') else 0
    except (ValueError,OSError,KeyError,TypeError):
        print('EXCELJS_VERIFY_FAILED');return 2
if __name__=='__main__':raise SystemExit(main())
