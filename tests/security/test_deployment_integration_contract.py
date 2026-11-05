"""Focused delta checks. Live TLS/HTTP/PostGIS checks belong to isolated QA."""
import ast
from pathlib import Path
import unittest

from test_http_deployment_security import parse_config, values

ROOT=Path(__file__).resolve().parents[2]


class DeploymentIntegrationContract(unittest.TestCase):
    def test_edge_limits_cover_all_four_gis_uploads_and_documents(self):
        source=(ROOT/'deploy/tls/default.conf.template').read_text().replace('${PUBLIC_HOST}','ssalfer.example.invalid')
        conf=parse_config(source)
        tls=next(b for b in conf.children if b.words==['server'] and ['443','ssl','default_server'] in values(b,'listen'))
        self.assertEqual(values(tls,'client_max_body_size'),[['1m']])
        locations=[b for b in tls.children if b.words[0]=='location']
        import re
        for uri,limit in [('/api/documentos/1/versiones','26m'),
                ('/api/proyectos/1/importaciones','101m'),
                *[(f'/api/proyectos/1/geoespacial/{kind}/importaciones','101m') for kind in ('ddv','nucleos','parcelas')]]:
            for suffix in ('','/'):
                matched=next(b for b in locations if b.words[1]=='~' and re.search(b.words[2],uri+suffix))
                self.assertEqual(values(matched,'client_max_body_size'),[[limit]])
                self.assertEqual(values(matched,'proxy_pass'),[['http://backend:8000']])
        login=next(b for b in locations if 'sesiones' in ' '.join(b.words))
        self.assertEqual(values(login,'client_max_body_size'),[['16k']])
        self.assertEqual(values(login,'limit_req_status'),[['429']])

    def test_edge_canonical_headers_preserve_pr6_policy(self):
        inner=parse_config((ROOT/'frontend-ssalfer/deploy/nginx.conf').read_text())
        server=next(b for b in inner.children if b.words==['server'])
        edge=parse_config((ROOT/'deploy/tls/headers.conf').read_text())
        expected=values(server,'add_header')
        actual=values(edge,'add_header')
        self.assertEqual(actual[:-1],expected)
        self.assertEqual(actual[-1],['Strict-Transport-Security','max-age=31536000','always'])
        self.assertFalse(any(row[0]=='Content-Security-Policy' for row in actual))

    def test_25_mib_is_the_default_in_api_compose_and_ui(self):
        tree=ast.parse((ROOT/'backend/app/services/documents.py').read_text())
        value=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MAX_UPLOAD_BYTES' for t in n.targets))
        self.assertIn('25 * 1024 * 1024',ast.unparse(value))
        self.assertIn('Máximo 25 MiB (26 214 400 bytes).',(ROOT/'frontend-ssalfer/js/utils/gestorDocumentos.js').read_text())

    def test_edge_drops_forwarding_spoofs_and_rewrites_https_redirects(self):
        conf=parse_config((ROOT/'deploy/tls/proxy.conf').read_text())
        headers=dict(values(conf,'proxy_set_header'))
        self.assertEqual(headers['X-Forwarded-For'],'$remote_addr')
        self.assertEqual(headers['X-Forwarded-Proto'],'https')
        self.assertEqual(values(conf,'proxy_redirect'),[['http://$host/','https://$host/']])
        self.assertEqual(values(conf,'proxy_intercept_errors'),[['off']])
        hidden={r[0] for r in values(conf,'proxy_hide_header')}
        for header in ('Set-Cookie','Content-Disposition','X-Document-Operation-Id','Idempotency-Key'):
            self.assertNotIn(header,hidden)

    def test_runtime_code_is_readable_without_chowning_stored_data(self):
        docker=(ROOT/'backend/Dockerfile').read_text()
        self.assertIn('USER 10001:10001',docker)
        self.assertIn('-m 0700 /app/uploads',docker)
        self.assertNotIn('--reload',docker)
        self.assertNotIn('chown -R',docker)
        self.assertIn('--workers", "2"',docker)

    def test_production_dynamic_pool_excludes_the_trusted_static_proxy(self):
        import ipaddress
        import yaml
        from test_http_deployment_security import ComposeLoader
        source=yaml.load((ROOT/'docker-compose.prod.yml').read_text(),Loader=ComposeLoader)
        config=source['networks']['default']['ipam']['config'][0]
        def default(value):return value.split(':-',1)[1].rstrip('}')
        subnet=ipaddress.ip_network(default(config['subnet']))
        dynamic=ipaddress.ip_network(default(config['ip_range']))
        edge=ipaddress.ip_address(default(source['services']['tls_proxy']['networks']['default']['ipv4_address']))
        self.assertTrue(dynamic.subnet_of(subnet))
        self.assertIn(edge,subnet)
        self.assertNotIn(edge,dynamic)
        for name in ('backend','db','pgadmin','frontend_ssalfer'):
            self.assertEqual(source['services'][name]['ports'],[])

    def test_pool_budget_is_per_worker_and_parameters_remain_hidden(self):
        source=(ROOT/'backend/app/database.py').read_text()
        self.assertIn('_read_positive_int("DB_POOL_SIZE", 5)',source)
        self.assertIn('_read_positive_int("DB_POOL_MAX_OVERFLOW", 2)',source)
        self.assertIn('hide_parameters=True',source)
        self.assertIn('echo=False',source)


if __name__=='__main__':unittest.main()
