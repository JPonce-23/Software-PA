"""SS-09 read-only standard-library audit of local declarations, never a build/SCA.

No environment loading, connectors, network, subprocesses, package tools or writes.
The small Compose/ignore recognizers cover this repository's reviewed subset;
Docker/Compose/npm/pip remain the authorities for actual resolution in QA.
"""
import argparse
import ast
import base64
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from urllib.parse import urlsplit

MAX_SOURCE_BYTES=8*1024*1024
VENDOR_PREFIX='frontend-ssalfer/js/vendor/'
SOURCES=('backend/requirements.txt','backend/tests/requirements-convenio-report.txt','backend/Dockerfile','backend/.dockerignore',
 'frontend-ssalfer/.dockerignore','frontend-ssalfer/deploy/Dockerfile','docker-compose.yml','docker-compose.override.yml',
 'docker-compose.prod.yml','docker-compose.ssalfer.yml',
 'backend/tests/convenio_report_compose.yml','backend/tests/lineage_compose.yml')
LEGACY_SOURCES=('frontend/package.json','frontend/package-lock.json','frontend/Dockerfile','frontend/.dockerignore')
APP_IMPORTS={'PIL':'pillow','pypdf':'pypdf','fastapi':'fastapi','sqlalchemy':'sqlalchemy','pydantic':'pydantic',
 'geoalchemy2':'geoalchemy2','psycopg2':'psycopg2-binary','bcrypt':'bcrypt',
 'dotenv':'python-dotenv','pandas':'pandas','numpy':'numpy','openpyxl':'openpyxl',
 'httpx':'httpx','aiofiles':'aiofiles','starlette':'starlette','passlib':'passlib'}
IMAGE_ROOTS={'python','node','nginx','postgis/postgis','dpage/pgadmin4','software-pa-backend'}
ALLOWED_SERVICES={'backend','frontend','frontend_ssalfer','db','pgadmin','worker'}
REQUIRED_IGNORE={'.env','.env.*','**/.env','**/.env.*','.git','**/.git','.ssh','**/.ssh',
 '.aws','**/.aws','.pgpass','**/.pgpass','.npmrc','**/.npmrc','.pypirc','**/.pypirc',
 '.netrc','**/.netrc','.git-credentials','**/.git-credentials',
 '*.pem','**/*.pem','*.key','**/*.key','/tests/','/db/tests/'}

class AuditError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)

class QuietParser(argparse.ArgumentParser):
    def error(self,message):raise AuditError('ARGUMENTS_INVALID')


def read_bytes(root,relative):
    """Bounded descriptor walk; reject secret-like paths and symlinks before reading."""
    parts=PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or any(p in ('.','..') or '\\' in p for p in parts):
        raise AuditError('SOURCE_PATH_INVALID')
    if any(p.startswith('.env') or p in {'.aws','.ssh','.pgpass','.npmrc','.pypirc','.netrc','.git-credentials'} for p in parts):
        raise AuditError('SECRET_PATH_FORBIDDEN')
    if Path(parts[-1]).suffix.lower() in {'.pem','.key','.p12','.pfx','.jks','.dump','.backup'}:
        raise AuditError('SECRET_PATH_FORBIDDEN')
    # Opening a FIFO without NONBLOCK could hang before fstat rejects its type.
    flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK
    fd=os.open(root,flags|os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            nxt=os.open(part,flags|os.O_DIRECTORY,dir_fd=fd);os.close(fd);fd=nxt
        source=os.open(parts[-1],flags,dir_fd=fd)
        try:
            info=os.fstat(source)
            if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_SOURCE_BYTES:raise AuditError('SOURCE_TYPE_OR_SIZE_INVALID')
            chunks=[];count=0
            while True:
                chunk=os.read(source,min(65536,MAX_SOURCE_BYTES-count+1))
                if not chunk:break
                count+=len(chunk)
                if count>MAX_SOURCE_BYTES:raise AuditError('SOURCE_TYPE_OR_SIZE_INVALID')
                chunks.append(chunk)
            return b''.join(chunks)
        finally:os.close(source)
    finally:os.close(fd)


def read_text(root,name):return read_bytes(root,name).decode('utf-8')


def optional_legacy_sources(root):
    """Absent retired frontend is valid; a present tree must remain inspectable.

    Never silently drop a partial/altered legacy tree or bypass descriptor safety.
    SSALFER sources and vendor integrity remain mandatory independently.
    """
    directory=root/'frontend'
    if directory.is_symlink():raise AuditError('LEGACY_DIRECTORY_SYMLINK')
    if not directory.exists():return {}
    if not directory.is_dir():raise AuditError('LEGACY_DIRECTORY_NOT_DIRECTORY')
    return {name:read_text(root,name) for name in LEGACY_SOURCES}


def canonical_name(value):return re.sub(r'[-_.]+','-',value).lower()
def safe_version(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9][0-9A-Za-z.+_-]{0,49}',value):raise AuditError('VERSION_FORMAT_INVALID')
    return value


def python_inventory(text):
    result=[];seen=set()
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        match=re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9_.-]*)==([0-9][0-9A-Za-z.+_-]{0,49})',line.strip())
        if not match:raise AuditError('PYTHON_REQUIREMENT_NOT_REVIEWED_EXACT_PIN')
        name=canonical_name(match[1]);version=safe_version(match[2])
        if name in seen:raise AuditError('PYTHON_DUPLICATE_PIN')
        seen.add(name);result.append(dict(name=name,declared_version=version,installed_version=None,
            distribution_hash=None,dependency_topology='flat_unverified',vulnerability_review='pending'))
    return sorted(result,key=lambda r:r['name'])


def semver_subset(requirement,resolved):
    """Only exact/^/~ three-part stable versions; other npm syntax stays pending."""
    match=re.fullmatch(r'([\^~]?)([0-9]+)\.([0-9]+)\.([0-9]+)',requirement)
    actual=re.fullmatch(r'([0-9]+)\.([0-9]+)\.([0-9]+)',resolved)
    if not match or not actual:return None
    op=match[1];minimum=tuple(map(int,match.groups()[1:]));version=tuple(map(int,actual.groups()))
    if not op:return version==minimum
    if op=='~':upper=(minimum[0],minimum[1]+1,0)
    elif minimum[0]:upper=(minimum[0]+1,0,0)
    elif minimum[1]:upper=(0,minimum[1]+1,0)
    else:upper=(0,0,minimum[2]+1)
    return minimum<=version<upper


def node_inventory(package,lock):
    if lock.get('lockfileVersion')!=3 or not isinstance(lock.get('packages'),dict):raise AuditError('NODE_LOCK_SCHEMA_UNSUPPORTED')
    tree=lock['packages'];declared=[]
    for section in ('dependencies','devDependencies'):
        values=package.get(section,{})
        if not isinstance(values,dict) or values!=tree.get('',{}).get(section,{}):raise AuditError('NODE_ROOT_DECLARATION_MISMATCH')
        for name,requirement in sorted(values.items()):
            if not re.fullmatch(r'(?:@[a-z0-9._-]+/)?[a-z0-9._-]+',name):raise AuditError('NODE_PACKAGE_NAME_INVALID')
            resolved=tree.get('node_modules/'+name,{}).get('version')
            if resolved is None:raise AuditError('NODE_DIRECT_RESOLUTION_MISSING')
            version=safe_version(resolved)
            if not isinstance(requirement,str) or not re.fullmatch(r'[\^~]?[0-9]+\.[0-9]+\.[0-9]+',requirement):
                status='unsupported_range_pending_npm';display=None
            else:
                valid=semver_subset(requirement,version);status='matches_reviewed_range' if valid else 'mismatch'
                display=requirement
            declared.append(dict(name=name,kind=section,declared_range=display,lock_version=version,coherence=status))
    resolved=[]
    for path,record in sorted(tree.items()):
        if not path:continue
        if not re.fullmatch(r'node_modules/(?:[a-z0-9@._-]+/)*[a-z0-9@._-]+',path):raise AuditError('NODE_LOCK_PATH_UNSUPPORTED')
        version=safe_version(record.get('version'))
        integrity=record.get('integrity','');match=re.fullmatch(r'(sha256|sha384|sha512)-([A-Za-z0-9+/]+={0,2})',integrity) if isinstance(integrity,str) else None
        valid=False
        if match:
            try:valid=len(base64.b64decode(match[2],validate=True))=={'sha256':32,'sha384':48,'sha512':64}[match[1]]
            except ValueError:pass
        try:
            url=urlsplit(record.get('resolved',''))
            origin_ok=(url.scheme=='https' and url.hostname=='registry.npmjs.org' and not url.username
                and not url.password and not url.query and not url.fragment and url.port in (None,443))
        except (ValueError,TypeError):origin_ok=False
        resolved.append(dict(path=path,lock_version=version,installed_version=None,
            integrity=integrity if valid else None,integrity_format_valid=valid,
            distribution_bytes_verified=False,origin='registry.npmjs.org' if origin_ok else 'unapproved_or_credentialed',
            has_install_script=record.get('hasInstallScript') is True,dev=record.get('dev') is True,
            optional=record.get('optional') is True,vulnerability_review='pending'))
    return dict(lockfile_version=3,direct=declared,locked=resolved,installed_tree='not_observed')


def vendor_inventory(root):
    manifest=json.loads(read_text(root,'docs/security/ss09/vendors-sha256.json'))
    if manifest.get('schema_version')!=1 or not isinstance(manifest.get('files'),list):raise AuditError('VENDOR_MANIFEST_INVALID')
    results=[];seen=set()
    families={'leaflet','bootstrap-icons','sheetjs','exceljs','html2canvas','vendor-documentation'}
    for entry in manifest['files']:
        path=entry.get('path');digest=entry.get('sha256');size=entry.get('size')
        if not isinstance(path,str) or not path.startswith(VENDOR_PREFIX) or not re.fullmatch(r'[A-Za-z0-9_./-]+',path):raise AuditError('VENDOR_PATH_INVALID')
        if Path(path).suffix not in {'.js','.css','.woff','.woff2','.png','.txt','.md'}:raise AuditError('VENDOR_PATH_INVALID')
        if path in seen:raise AuditError('VENDOR_DUPLICATE_PATH')
        seen.add(path)
        if not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest) or type(size) is not int:raise AuditError('VENDOR_DIGEST_INVALID')
        if entry.get('family') not in families:raise AuditError('VENDOR_FAMILY_INVALID')
        version=entry.get('declared_version')
        if version is not None:version=safe_version(version)
        content=read_bytes(root,path)
        results.append(dict(path=path,family=entry['family'],declared_version=version,size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),matches_local_baseline=(len(content)==size and hashlib.sha256(content).hexdigest()==digest),
            version_literal_present=version.encode() in content if version and path.endswith(('.js','.css')) else None,
            upstream_authenticity='not_verified',vulnerability_review='pending'))
    # Names of unreviewed files are not echoed, and their contents are not read.
    directory=root/VENDOR_PREFIX
    if directory.is_symlink():raise AuditError('VENDOR_DIRECTORY_SYMLINK')
    actual={str(p.relative_to(root)) for p in directory.rglob('*') if p.is_file() or p.is_symlink()}
    return dict(files=results,unmanifested_count=len(actual-seen),missing_count=len(seen-actual),
                baseline_is_authenticity_proof=False)


def image_record(value,source):
    # Fixed registry families used in the reviewed repository; do not echo new
    # credentialed registry refs/URLs/variables before they receive review.
    match=re.fullmatch(r'([a-z0-9./-]+)(?::([a-z0-9._-]+))?(?:@sha256:([0-9a-f]{64}))?',value)
    if not match or match[1] not in IMAGE_ROOTS:
        return dict(source=source,reference=None,immutable_reference=False,actual_digest_verified=False,review='unapproved_reference')
    return dict(source=source,reference=value,immutable_reference=bool(match[3]),
        actual_digest_verified=False,platform='not_observed',review='digest_pending' if not match[3] else 'digest_reference_only')


def service_blocks(text):
    """Extract simple service blocks only; no YAML merge/interpolation/resolution."""
    lines=text.splitlines();inside=False;current=None;blocks={}
    for line in lines:
        if line=='services:':inside=True;continue
        if inside and line and not line[0].isspace() and not line.startswith('#'):inside=False
        if not inside:continue
        match=re.fullmatch(r'  ([a-z_][a-z0-9_]*):\s*',line)
        if match:
            current=match[1]
            if current not in ALLOWED_SERVICES:raise AuditError('COMPOSE_SERVICE_UNREVIEWED')
            blocks[current]=[]
        elif current:blocks[current].append(line)
    return {key:'\n'.join(value) for key,value in blocks.items()}


def inspect_images(sources):
    images=[]
    for name,text in sources.items():
        if name.endswith('Dockerfile'):
            stages=set()
            for line in text.splitlines():
                match=re.fullmatch(r'FROM\s+(\S+)(?:\s+AS\s+(\w+))?',line,re.I)
                if match:
                    if match[1] not in stages:images.append(image_record(match[1],name))
                    if match[2]:stages.add(match[2])
        elif name.endswith('.yml'):
            for line in text.splitlines():
                match=re.fullmatch(r'\s+image:\s+([^\s#]+)\s*',line)
                if match:images.append(image_record(match[1],name))
    return images


def ignore_subset(path,source):
    """Model the current simple patterns only; Docker matcher still requires QA."""
    candidates=[path,*[str(p) for p in PurePosixPath(path).parents if str(p)!='.']]
    for raw in source.splitlines():
        pattern=raw.strip()
        if not pattern or pattern.startswith('#'):continue
        if pattern.startswith('!'):raise AuditError('IGNORE_NEGATION_NEEDS_REVIEW')
        pattern=pattern.strip('/')
        if any(fnmatch.fnmatchcase(candidate,pattern) for candidate in candidates):return True
    return False


def deployment_inventory(sources):
    base=service_blocks(sources['docker-compose.yml']);prod=service_blocks(sources['docker-compose.prod.yml'])
    dev=service_blocks(sources['docker-compose.override.yml']);ssalfer=service_blocks(sources['docker-compose.ssalfer.yml'])
    return dict(compose_parser='reviewed_literal_subset_not_compose_resolution',
        base_services=sorted(base),additional_ssalfer_services=sorted(ssalfer),
        uvicorn_no_proxy_headers_in_base='--no-proxy-headers' in base.get('backend',''),
        uvicorn_no_access_log_in_base='--no-access-log' in base.get('backend',''),
        secure_cookie_literal_in_prod=bool(re.search(r'AUTH_COOKIE_SECURE:\s*"true"',prod.get('backend',''))),
        production_mode_literal='APP_ENV: production' in prod.get('backend',''),
        explicit_cors_required_in_prod='CORS_ORIGINS: ${CORS_ORIGINS:?' in prod.get('backend',''),
        development_reload='--reload' in dev.get('backend',''),
        frontend_selection='ssalfer_official',
        legacy_service_declared=any('frontend' in doc for doc in (base,prod,dev,ssalfer)),
        ssalfer_service_declared='frontend_ssalfer' in ssalfer,combinations=[
          dict(profile='implicit_base_override',files=['docker-compose.yml','docker-compose.override.yml'],review='development_not_production'),
          dict(profile='base_prod',files=['docker-compose.yml','docker-compose.prod.yml'],review='ssalfer_overlay_required'),
          dict(profile='base_ssalfer',files=['docker-compose.yml','docker-compose.ssalfer.yml'],review='production_settings_not_guaranteed'),
          dict(profile='base_prod_ssalfer',files=['docker-compose.yml','docker-compose.prod.yml','docker-compose.ssalfer.yml'],review='ssalfer_official_explicit_services_and_qa_required')])


def audit(root):
    root=Path(root)
    sources={name:read_text(root,name) for name in SOURCES}
    legacy=optional_legacy_sources(root)
    sources.update(legacy)
    py=python_inventory(sources['backend/requirements.txt'])
    observed=set()
    for path in sorted((root/'backend/app').rglob('*.py')):
        tree=ast.parse(read_text(root,str(path.relative_to(root))))
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):observed.update(a.name.split('.')[0] for a in node.names)
            if isinstance(node,ast.ImportFrom) and node.level==0 and node.module:observed.add(node.module.split('.')[0])
    for row in py:row['app_import_observed']=row['name'] in {APP_IMPORTS[n] for n in observed if n in APP_IMPORTS}
    node=(node_inventory(json.loads(legacy['frontend/package.json']),json.loads(legacy['frontend/package-lock.json']))
          if legacy else dict(direct=[],locked=[],installed_tree='not_observed'))
    node.update(role='legacy_not_official_frontend',source_status='present_audited' if legacy else 'absent_retired',
                functional_qa_required_for_ssalfer=False)
    vendors=vendor_inventory(root);images=inspect_images(sources)
    ignore=sources['backend/.dockerignore'];patterns={s.strip() for s in ignore.splitlines() if s.strip() and not s.lstrip().startswith('#')}
    docker=sources['backend/Dockerfile'];ssalfer=sources['frontend-ssalfer/deploy/Dockerfile']
    preserved=('requirements.txt','Dockerfile','logging.json','app/main.py','app/safe_logging.py',
               'app/services/document_storage.py','db/init/001_bootstrap_roles.sh',
               'db/migrations/001_baseline_v1.sql','scripts/run_migrations.sh')
    context=dict(root='./backend',global_copy='COPY . .' in docker,missing_required_ignore_patterns=len(REQUIRED_IGNORE-patterns),
        required_resources_excluded=[name for name in preserved if ignore_subset(name,ignore)],
        test_sources_excluded=ignore_subset('tests/test_synthetic.py',ignore),
        build_reconstruction='pending_native_docker',scan_is_not_secret_scanner=True)
    workflow_dir=root/'.github/workflows'
    if workflow_dir.is_symlink():raise AuditError('WORKFLOW_DIRECTORY_SYMLINK')
    workflows=sum(1 for p in workflow_dir.iterdir() if p.suffix in ('.yml','.yaml')) if workflow_dir.is_dir() else 0
    issues=['PYTHON_DISTRIBUTION_HASHES_UNVERIFIED','PYTHON_GRAPH_UNVERIFIED','NATIVE_AND_INSTALLED_ARTIFACTS_UNOBSERVED',
            'CVE_SCA_NOT_PERFORMED','GITHUB_EFFECTIVE_POLICIES_UNOBSERVED','INSTITUTIONAL_PROFILE_PENDING_APPROVAL']
    if any(not r['immutable_reference'] for r in images):issues.append('MUTABLE_IMAGE_REFERENCES')
    if any(r['reference'] is None for r in images):issues.append('UNAPPROVED_IMAGE_REFERENCE')
    if context['missing_required_ignore_patterns']:issues.append('BACKEND_IGNORE_POLICY_INCOMPLETE')
    if context['required_resources_excluded']:issues.append('BACKEND_REQUIRED_RESOURCE_EXCLUDED')
    if not workflows:issues.append('NO_LOCAL_WORKFLOW_CONFIGURATION')
    if any(not r['integrity_format_valid'] or r['origin']!='registry.npmjs.org' for r in node['locked']):issues.append('NODE_RESOLUTION_METADATA_REQUIRES_REVIEW')
    if any(r['coherence']!='matches_reviewed_range' for r in node['direct']):issues.append('NODE_DIRECT_RANGE_MISMATCH_OR_UNSUPPORTED')
    if vendors['unmanifested_count'] or vendors['missing_count'] or any(not r['matches_local_baseline'] for r in vendors['files']):issues.append('VENDOR_LOCAL_INTEGRITY_FAILURE')
    deployment=deployment_inventory(sources)
    if not deployment['ssalfer_service_declared']:issues.append('SSALFER_SERVICE_MISSING')
    if deployment['legacy_service_declared']:issues.append('LEGACY_SERVICE_DECLARED_REVIEW_SELECTION')
    if not deployment['uvicorn_no_proxy_headers_in_base'] or not deployment['uvicorn_no_access_log_in_base']:
        issues.append('SS04_SS10_RUNTIME_COMMAND_DRIFT')
    if not all(deployment[k] for k in ('secure_cookie_literal_in_prod','production_mode_literal','explicit_cors_required_in_prod')):
        issues.append('PRODUCTION_SETTINGS_DRIFT')
    if 'COPY . ' in ssalfer or 'COPY Index.html dashboard.html' not in ssalfer:
        issues.append('SS08_SELECTIVE_COPY_DRIFT')
    if not (root/'frontend-ssalfer/.dockerignore').is_file():
        issues.append('SSALFER_BUILD_CONTEXT_IGNORE_NOT_DECLARED')
    if '--reload' in docker:issues.append('DOCKERFILE_DEFAULT_RELOAD_DECLARED')
    integrity_failure=any(code in issues for code in ('VENDOR_LOCAL_INTEGRITY_FAILURE',
        'NODE_DIRECT_RANGE_MISMATCH_OR_UNSUPPORTED','NODE_RESOLUTION_METADATA_REQUIRES_REVIEW',
        'BACKEND_REQUIRED_RESOURCE_EXCLUDED','BACKEND_IGNORE_POLICY_INCOMPLETE',
        'UNAPPROVED_IMAGE_REFERENCE','SS04_SS10_RUNTIME_COMMAND_DRIFT',
        'PRODUCTION_SETTINGS_DRIFT','SS08_SELECTIVE_COPY_DRIFT','SSALFER_SERVICE_MISSING'))
    return dict(schema_version=1,scope='local_declarations_not_installed_sbom_or_deployment',
        assessment='incomplete_requires_qa',local_integrity_ok=not integrity_failure,
        python=py,qa_python=python_inventory(sources['backend/tests/requirements-convenio-report.txt']),
        node=node,vendors=vendors,images=images,
        native=dict(apt_declared_packages=[p for p in ('gdal-bin','libpq-dev','gcc') if re.search(r'\b'+re.escape(p)+r'\b',docker)],
                    apt_versions=None,gdal_geos_proj_libpq_versions=None,postgresql_postgis_installed_versions=None,
                    build_tools_in_backend_runtime='gcc' in docker),
        contexts=dict(backend=context,ssalfer_selective_copy=('COPY . ' not in ssalfer and 'COPY Index.html dashboard.html' in ssalfer),
            ssalfer_ignore_file_present=(root/'frontend-ssalfer/.dockerignore').is_file(),
            react_source_status=node['source_status'],
            react_uses_npm_ci=('RUN npm ci' in legacy['frontend/Dockerfile']) if legacy else None,
            react_dockerignore_env_patterns=(all(p in legacy['frontend/.dockerignore'].splitlines() for p in ('.env','.env.*'))
                                             if legacy else None)),
        deployment=deployment,github=dict(local_workflow_count=workflows,
            dependabot_file_present=(root/'.github/dependabot.yml').is_file() or (root/'.github/dependabot.yaml').is_file(),
            effective_branch_protection='not_observed',rulesets='not_observed',secrets='not_accessed'),
        issues=sorted(issues))


def main(argv=None):
    parser=QuietParser(description='SS-09 offline read-only inspection; no build or SCA.')
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    try:
        args=parser.parse_args(argv);result=audit(args.root)
    except (AuditError,OSError,ValueError,TypeError,KeyError,SyntaxError,AttributeError):
        print(json.dumps({'schema_version':1,'status':'inspection_failed','code':'SOURCE_OR_ARGUMENTS_INVALID'},sort_keys=True))
        return 2
    print(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2))
    return 0 if result['local_integrity_ok'] else 2


if __name__=='__main__':raise SystemExit(main())
