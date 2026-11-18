"""Validate the frozen Etapa4-R OCI archive offline, without Docker or extraction to host paths."""
import argparse,hashlib,json,os,re,tarfile
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive',type=Path)
parser.add_argument('--store',required=True,type=Path)
args=parser.parse_args();ARCHIVE=args.archive
def content_sha(p):
 h=hashlib.sha256()
 with p.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
def snap(root):return {str(p.relative_to(root)):content_sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
EXPECTED='d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c'
EXPECTED_ARCHIVE_SHA256='4099c542cf891338320396fca45fac0bc47bd1064217e70b331259981ad025b2'
assert content_sha(ARCHIVE)==EXPECTED_ARCHIVE_SHA256,'ARCHIVE_CHECKSUM_MISMATCH'
I={'platform_manifest': {'digest': 'sha256:27e9ca0702414c9515cf205df5635af7ad7509385dffcf7dcf6fb048c185f9b7'}, 'config_digest': 'sha256:dfe80e1feb214799ba101b037f0b72e2499de606a63ef88497f4e13bb1ed3f19'}
wanted={'usr/lib/postgresql/15/lib/bitcode/postgis-3/flatgeobuf.bc': '9f3a0c2f303bb1159ae662dcb9024f7904b03da3cab05b30e5f557a4e542bd42', 'usr/lib/postgresql/15/lib/bitcode/postgis-3/lwgeom_in_flatgeobuf.bc': 'd994e2eb001a679d6cf5a414fc8dd2702cc79e65825ee46dfdb00c8545f092df', 'usr/lib/postgresql/15/lib/postgis-3.so': 'f302aca21231b7855fa66644b5cfd58085cf12fa4fda70627ec21b437cb636e0', 'usr/lib/x86_64-linux-gnu/libgdal.so.36.3.10.3': '10c9bc0c0bbafe2f16b51c130ad5f4ba2030c204cbbac5a271a79e6418abadeb', 'usr/lib/postgresql/15/lib/bitcode/postgis-3.index.bc': 'b95e9e68087c1e6e491775a10e71936f573c970a5dab0c84cda1dba35220e578'}
store=args.store;store.mkdir(parents=True,exist_ok=False);blobs={};document={};effective={};occurrences=[]
with tarfile.open(ARCHIVE,'r:') as archive:
 members=archive.getmembers();assert len({m.name for m in members})==len(members),'duplicate member'
 for m in members:
  assert not m.issym() and not m.islnk() and not m.name.startswith('/') and '..' not in Path(m.name).parts,m.name
  if m.isdir():continue
  assert m.isfile(),m.name
  if re.fullmatch(r'blobs/sha256/[0-9a-f]{64}',m.name):
   h=hashlib.sha256();target=store/m.name;target.parent.mkdir(parents=True,exist_ok=True)
   with archive.extractfile(m) as source,target.open('xb') as out:
    for chunk in iter(lambda:source.read(1048576),b''):h.update(chunk);out.write(chunk)
   assert h.hexdigest()==m.name.rsplit('/',1)[1],m.name
   blobs['sha256:'+h.hexdigest()]=dict(size=m.size,path=str(target.relative_to(store)))
  else:
   assert m.name in {'index.json','oci-layout','manifest.json'},m.name
   payload=archive.extractfile(m).read();(store/m.name).write_bytes(payload);document[m.name]=json.loads(payload)
 assert document['oci-layout']['imageLayoutVersion']=='1.0.0'
 assert 'sha256:'+EXPECTED in blobs
 visited=set()
 def visit(desc):
  digest=desc['digest'];assert digest in blobs,digest;assert blobs[digest]['size']==desc['size'];visited.add(digest)
  if desc['mediaType'] in {'application/vnd.oci.image.index.v1+json','application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json','application/vnd.docker.distribution.manifest.list.v2+json'}:
   obj=json.loads((store/blobs[digest]['path']).read_text())
   for child in obj.get('manifests',[]):visit(child)
   if 'config' in obj:visit(obj['config'])
   for child in obj.get('layers',[]):visit(child)
 for desc in document['index.json']['manifests']:visit(desc)
 assert set(blobs)==visited,('unreferenced',set(blobs)-visited)
 index=json.loads((store/'blobs/sha256'/EXPECTED).read_text())
 platform=next(d for d in index['manifests'] if d.get('platform')=={'architecture':'amd64','os':'linux'})
 assert platform['digest']==I['platform_manifest']['digest']
 manifest=json.loads((store/blobs[platform['digest']]['path']).read_text());assert manifest['config']['digest']==I['config_digest']
 config=json.loads((store/blobs[manifest['config']['digest']]['path']).read_text())
 assert config['os']=='linux' and config['architecture']=='amd64'
 legacy=document['manifest.json'];assert len(legacy)==1
 assert legacy[0]['RepoTags']==['software-pa-libgdal36-candidate:20261117-pa5']
 assert legacy[0]['Config']==blobs[manifest['config']['digest']]['path']
 assert legacy[0]['Layers']==[blobs[l['digest']]['path'] for l in manifest['layers']]
 for layer in manifest['layers']:
  with tarfile.open(store/blobs[layer['digest']]['path'],'r|*') as payload:
   for member in payload:
    name=member.name.removeprefix('./')
    # Track replacement/removal of protected targets across ordered layers.
    if '/.wh.' in name:
     removed=name.replace('/.wh.','/')
     if removed in wanted:effective.pop(removed,None)
    if name in wanted and member.isfile():
     h=hashlib.sha256()
     with payload.extractfile(member) as source:
      for chunk in iter(lambda:source.read(1048576),b''):h.update(chunk)
     effective[name]=h.hexdigest();occurrences.append(dict(path=name,layer=layer['digest'],sha256=h.hexdigest()))
 assert effective==wanted,('payload mismatch',effective,wanted)
 result=dict(state='PASS',scope='Local export and offline OCI content-store materialization; no Docker load or remote runner',archive_file=ARCHIVE.name,archive_sha256=content_sha(ARCHIVE),archive_size_bytes=ARCHIVE.stat().st_size,oci_index_digest='sha256:'+EXPECTED,platform_manifest_digest=platform['digest'],config_digest=manifest['config']['digest'],archive_wrapper_index_sha256=content_sha(store/'index.json'),blobs_verified=len(blobs),all_descriptors_and_sizes_verified=True,attestation_descriptors=[d for d in index['manifests'] if d.get('platform',{}).get('architecture')=='unknown'],effective_protected_payloads=effective,protected_payload_layer_occurrences=occurrences,offline_store_files=snap(store),docker_engine_import_tested=False,github_actions_availability_tested=False,new_image_created=False)
 print(json.dumps(result,sort_keys=True,indent=2))
