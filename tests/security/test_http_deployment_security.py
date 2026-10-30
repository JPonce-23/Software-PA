"""SS-08 configuration/source checks, not nginx/Docker/browser execution.

Reads checked-in text only; no dotenv, interpolation, sockets or app startup.
"""
import ast
from dataclasses import dataclass, field
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import shlex
import unittest
from urllib.parse import unquote, urlsplit
import yaml

ROOT=Path(__file__).resolve().parents[2]
WEB=ROOT/'frontend-ssalfer'


@dataclass
class Block:
    words:list
    directives:list=field(default_factory=list)
    children:list=field(default_factory=list)


def parse_config(source):
    """Small lexer for this config's blocks/directives; NOT nginx -t."""
    lexer=shlex.shlex(source,posix=True,punctuation_chars='{};')
    lexer.whitespace_split=True;lexer.commenters='#'
    root=Block([]);stack=[root];pending=[]
    for token in lexer:
        if token==';':
            if not pending:raise AssertionError('empty directive')
            stack[-1].directives.append(pending);pending=[]
        elif token=='{':
            if not pending:raise AssertionError('unnamed block')
            block=Block(pending);stack[-1].children.append(block);stack.append(block);pending=[]
        elif token=='}':
            if pending or len(stack)==1:raise AssertionError('invalid closure')
            stack.pop()
        else:pending.append(token)
    if pending or len(stack)!=1:raise AssertionError('incomplete configuration')
    return root


def values(block,directive):return [row[1:] for row in block.directives if row[0]==directive]


class Resources(HTMLParser):
    def __init__(self):super().__init__();self.resources=[];self.inline=0;self.frames=[]
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if tag=='script':
            if data.get('src'):self.resources.append(('script',data['src']))
            else:self.inline+=1
        if tag=='link' and 'stylesheet' in data.get('rel',''):self.resources.append(('style',data.get('href','')))
        if tag=='img' and data.get('src'):self.resources.append(('image',data['src']))
        if tag in ('iframe','object','embed'):self.frames.append(tag)


class HttpDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.text=(WEB/'deploy/nginx.conf').read_text()
        self.conf=parse_config(self.text)
        self.server=next(b for b in self.conf.children if b.words==['server'])
        self.locations={tuple(b.words[1:]):b for b in self.server.children if b.words[0]=='location'}
        self.api=self.locations[('/api/',)]
        self.headers={row[0]:row[1:] for row in values(self.server,'add_header')}
        self.compose={name:yaml.safe_load((ROOT/name).read_text()) for name in (
            'docker-compose.yml','docker-compose.override.yml','docker-compose.prod.yml','docker-compose.ssalfer.yml')}

    def test_security_headers_are_unique_server_directives(self):
        rows=values(self.server,'add_header')
        self.assertEqual(len(rows),len(self.headers))
        self.assertEqual(self.headers['X-Content-Type-Options'],['nosniff','always'])
        self.assertEqual(self.headers['Cache-Control'],['private, no-store','always'])
        self.assertEqual(self.headers['Referrer-Policy'],['no-referrer','always'])
        self.assertEqual(self.headers['X-Frame-Options'],['SAMEORIGIN','always'])
        self.assertEqual(self.headers['Permissions-Policy'],['camera=(), microphone=(), geolocation=()','always'])

    def test_header_inheritance_model_covers_success_and_error_statuses(self):
        for location in self.locations.values():
            self.assertFalse(values(location,'add_header'),'child would replace server headers on nginx1.27')
            for status in (200,401,403,404,413,500,502):
                with self.subTest(location=location.words,status=status):
                    modeled={name:row[0] for name,row in self.headers.items() if row[-1]=='always'}
                    self.assertEqual(modeled['Cache-Control'],'private, no-store')
                    self.assertEqual(modeled['X-Content-Type-Options'],'nosniff')
                    self.assertIn('Content-Security-Policy-Report-Only',modeled)

    def test_health_uses_content_type_without_losing_headers(self):
        health=self.locations[('=','/health')]
        self.assertEqual(values(health,'default_type'),[['text/plain']])
        self.assertEqual(values(health,'access_log'),[['off']])
        self.assertFalse(values(health,'add_header'))

    def test_proxy_pass_and_peer_headers_preserve_ss04(self):
        self.assertEqual(values(self.api,'proxy_pass'),[['http://backend:8000/api/']])
        self.assertEqual(values(self.api,'proxy_http_version'),[['1.1']])
        forwarded={row[0]:row[1] for row in values(self.api,'proxy_set_header')}
        self.assertEqual(forwarded,{'Host':'$host','X-Real-IP':'$remote_addr',
            'X-Forwarded-For':'$proxy_add_x_forwarded_for','X-Forwarded-Proto':'$scheme'})
        self.assertNotIn('real_ip_header',self.text)
        for name in ('docker-compose.yml','docker-compose.override.yml'):
            command=self.compose[name]['services']['backend']['command']
            self.assertIn('--no-proxy-headers',command)
            self.assertIn('--no-access-log',command)
            self.assertIn('/app/logging.json',command)
        self.assertIn('"--no-proxy-headers"',(ROOT/'backend/Dockerfile').read_text())

    def test_forwarded_spoof_is_not_restored_as_client_identity(self):
        spec=importlib.util.spec_from_file_location('ss08_peer',ROOT/'backend/app/services/request_origin.py')
        origin=importlib.util.module_from_spec(spec);spec.loader.exec_module(origin)
        spoof='192.0.2.199';actual='198.51.100.7';peer='10.0.0.2'
        appended=f'{spoof}, {actual}'
        self.assertEqual(origin.resolve_client_ip(peer,[appended],[peer]),actual)
        self.assertEqual(origin.resolve_client_ip(peer,[appended],[]),peer)

    def test_private_api_is_not_cached_or_stored_and_has_canonical_headers(self):
        self.assertEqual(values(self.api,'proxy_cache'),[['off']])
        self.assertEqual(values(self.api,'proxy_store'),[['off']])
        self.assertEqual(values(self.api,'proxy_intercept_errors'),[['off']])
        hidden={r[0].lower() for r in values(self.api,'proxy_hide_header')}
        self.assertEqual(hidden,{'cache-control','x-content-type-options'})
        self.assertNotIn('proxy_ignore_headers',self.text)
        self.assertNotIn('expires ',self.text)
        for protected in ('content-disposition','content-type','set-cookie','x-total-count'):
            self.assertNotIn(protected,hidden)

    def test_document_download_contract_and_authorization_are_preserved(self):
        tree=ast.parse((ROOT/'backend/app/routers/documents.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='download_version')
        code=ast.unparse(node)
        self.assertIn('require_document_access(db, user, version.id_documento)',code)
        self.assertIn('service.safe_version_path(version)',code)
        response=next(n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='FileResponse')
        kwargs={kw.arg:kw.value for kw in response.keywords}
        self.assertEqual(ast.literal_eval(kwargs['content_disposition_type']),'attachment')
        self.assertEqual(ast.literal_eval(kwargs['headers']),{'X-Content-Type-Options':'nosniff','Cache-Control':'private, no-store'})
        source=(ROOT/'backend/app/services/document_validation.py').read_text()
        tree=ast.parse(source);media=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='download_media_type')
        self.assertIn('application/octet-stream',ast.unparse(media))
        self.assertNotIn('uploads',self.text)
        self.assertNotIn('alias ',self.text)

    def test_no_unverified_tls_redirect_or_enforced_csp(self):
        self.assertEqual(values(self.server,'listen'),[['80']])
        self.assertNotIn('Strict-Transport-Security',self.headers)
        self.assertNotIn('Content-Security-Policy',self.headers)
        self.assertNotIn('ssl_certificate',self.text)
        self.assertNotIn('return 301 https',self.text)
        self.assertEqual(values(self.server,'server_tokens'),[['off']])

    def test_csp_candidate_covers_observed_resource_classes_without_blocking(self):
        policy=self.headers['Content-Security-Policy-Report-Only'][0]
        directives={part.split()[0]:part.split()[1:] for part in policy.split(';') if part.strip()}
        for key in ('script-src','style-src','img-src','font-src','connect-src','worker-src','frame-src'):
            self.assertIn("'self'",directives[key])
        self.assertIn("'unsafe-inline'",directives['style-src'])
        self.assertNotIn("'unsafe-inline'",directives['script-src'])
        self.assertIn('https://*.tile.openstreetmap.org',directives['img-src'])
        for token in ('data:','blob:'):self.assertIn(token,directives['img-src'])
        self.assertIn('blob:',directives['frame-src'])
        self.assertNotIn('report-uri',directives)
        self.assertNotIn('report-to',directives)
        self.assertNotIn('upgrade-insecure-requests',directives)

    def test_html_inventory_matches_pages_inline_scripts_and_hashes(self):
        inventory=json.loads((ROOT/'docs/security/ss08/inventario-recursos.json').read_text())
        actual={str(p.relative_to(WEB)) for p in [*WEB.glob('*.html'),*(WEB/'pages').rglob('*.html')]}
        self.assertEqual(actual,{p['path'] for p in inventory['pages']})
        total=0
        for page in inventory['pages']:
            path=WEB/page['path'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),page['sha256'])
            parser=Resources();parser.feed(path.read_text());total+=parser.inline
            self.assertFalse(parser.frames,'review frame policy before changing this assertion')
            for kind,url in parser.resources:
                self.assertFalse(urlsplit(url).scheme,'external source requires CSP review')
        self.assertEqual(total,inventory['summary']['inline_script_blocks'])
        self.assertGreater(total,0,'RO must not be mistaken for inline-compatible enforcement')

    def test_image_contains_all_existing_html_resources_but_not_operational_docs(self):
        docker=(WEB/'deploy/Dockerfile').read_text()
        copies=[shlex.split(line)[1:] for line in docker.splitlines() if line.startswith('COPY ')]
        published=set()
        for words in copies:
            *sources,destination=words
            if not destination.startswith('/usr/share/nginx/html'):continue
            for source in sources:
                path=WEB/source
                if path.is_dir():published.update(str(p.relative_to(WEB)) for p in path.rglob('*') if p.is_file())
                else:published.add(source)
        self.assertNotIn('.', {word for row in copies for word in row[:-1]})
        for denied in ('DEPLOY.md','ENTREGA.md','TESTING.md','deploy/nginx.conf','deploy/Dockerfile'):
            self.assertNotIn(denied,published)
        for page in [*WEB.glob('*.html'),*(WEB/'pages').rglob('*.html')]:
            self.assertIn(str(page.relative_to(WEB)),published)
            parser=Resources();parser.feed(page.read_text())
            for kind,url in parser.resources:
                parsed=urlsplit(url)
                if parsed.scheme or not parsed.path:continue
                target=(WEB/unquote(parsed.path).lstrip('/')) if parsed.path.startswith('/') else page.parent/unquote(parsed.path)
                if target.is_file():self.assertIn(str(target.resolve().relative_to(WEB.resolve())),published)
        self.assertIn('Index.html',published)
        self.assertIn('js/vendor/leaflet-1.9.4/leaflet.js',published)

    def test_ports_volumes_and_networks_are_declared_without_expansion(self):
        for doc in self.compose.values():
            for service in doc['services'].values():
                for port in service.get('ports',[]):self.assertTrue(port.startswith('127.0.0.1:'),port)
                self.assertNotIn('privileged',service)
                self.assertNotIn('network_mode',service)
                self.assertNotIn('/var/run/docker.sock',str(service.get('volumes',[])))
        base=self.compose['docker-compose.yml']['services']
        self.assertIn('uploads_data:/app/uploads',base['backend']['volumes'])
        self.assertIn('postgres_data:/var/lib/postgresql/data',base['db']['volumes'])
        self.assertFalse(self.compose['docker-compose.ssalfer.yml']['services']['frontend_ssalfer'].get('volumes'))
        self.assertNotIn('networks',self.compose['docker-compose.yml'])

    def test_ss10_logging_and_compose_environment_remain_separate(self):
        config=json.loads((ROOT/'backend/logging.json').read_text())
        self.assertEqual(config['formatters']['safe']['()'],'app.safe_logging.SafeJSONFormatter')
        base=self.compose['docker-compose.yml']
        self.assertEqual(base['x-default-logging']['options']['max-size'],'${DOCKER_LOG_MAX_SIZE:-10m}')
        self.assertEqual(base['x-default-logging']['options']['max-file'],'${DOCKER_LOG_MAX_FILES:-3}')
        environment=base['services']['backend']['environment']
        self.assertNotIn('POSTGRES_ADMIN_PASSWORD',environment)
        for key in ('AUTH_TRUSTED_PROXY_IPS','IMPORT_MAX_RECORD_BYTES','DOCUMENT_INSPECTION_ENTRIES','REPORT_MAX_ROWS'):
            self.assertIn(key,environment)

    def test_access_log_template_uses_only_generated_safe_metadata(self):
        row=values(self.conf,'log_format')[0]
        self.assertEqual(row[:2],['ssalfer_safe','escape=json'])
        template=''.join(row[2:]);variables=set(re.findall(r'\$\w+',template))
        self.assertEqual(variables,{'$request_id','$status','$body_bytes_sent','$request_time'})
        sentinel='SS08_QUERY_COOKIE_PERSON_SENTINEL_7842'
        replacements={'$request_id':'a'*32,'$status':'403','$body_bytes_sent':'29','$request_time':'0.012',
                      '$request':sentinel,'$args':sentinel,'$http_cookie':sentinel,'$remote_addr':sentinel}
        rendered=template
        for key,value in replacements.items():rendered=rendered.replace(key,value)
        self.assertNotIn(sentinel,rendered)
        record=json.loads(rendered)
        self.assertEqual(record,dict(component='ssalfer_proxy',request_id='a'*32,status=403,bytes=29,duration=0.012))
        self.assertEqual(values(self.server,'access_log'),[['/var/log/nginx/access.log','ssalfer_safe']])

    def test_upload_limits_are_scoped_to_document_and_gis_routes(self):
        self.assertEqual(values(self.server,'client_max_body_size'),[['1m']])
        self.assertIn('client_max_body_size 26m;',self.text)
        self.assertIn('client_max_body_size 101m;',self.text)
        self.assertFalse(values(self.api,'proxy_read_timeout'))
        environment=self.compose['docker-compose.yml']['services']['backend']['environment']
        self.assertEqual(environment['MAX_UPLOAD_BYTES'],'${MAX_UPLOAD_BYTES:-26214400}')
        self.assertEqual(environment['IMPORT_MAX_FILE_SIZE_MB'],'${IMPORT_MAX_FILE_SIZE_MB:-100}')
        # Candidate arithmetic, not real upload: largest documented default +
        # bounded multipart fixture overhead. Actual overrides need QA review.
        for file_bytes,outer_bytes in ((25*1024**2,26*1024**2),(100*1024**2,101*1024**2)):
            boundary=b'--SS08-SYNTHETIC-BOUNDARY\r\nContent-Disposition: form-data; name="archivo"; filename="sintetico.bin"\r\n\r\n'
            overhead=len(boundary)+len(b'\r\n--SS08-SYNTHETIC-BOUNDARY--\r\n')+65536
            self.assertLess(file_bytes+overhead,outer_bytes)
            self.assertGreater(file_bytes+overhead,1024**2)


if __name__=='__main__':unittest.main()
