"""Isolated reconciliation checks: no engine, app startup, network or services."""
import ast
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]


class ReconciledCandidateTests(unittest.TestCase):
    def config(self,environment,origin,secure='true'):
        spec=importlib.util.spec_from_file_location('ss_reconciled_config',ROOT/'backend/app/config.py')
        module=importlib.util.module_from_spec(spec)
        settings={'APP_ENV':environment,'AUTH_COOKIE_SECURE':secure,'CORS_ORIGINS':origin}
        with patch.dict(os.environ,settings,clear=True),patch.dict(sys.modules,{'ss_reconciled_config':module}):
            spec.loader.exec_module(module)
        return module.AUTH_SETTINGS

    def test_production_exact_https_and_cookie_contract(self):
        for value in ('https://ssalfer.example.org','https://203.0.113.10','https://ssalfer.example.org:8443'):
            with self.subTest(origin=value):
                settings=self.config('production',value)
                self.assertEqual(settings.allowed_origins,(value,))
                self.assertEqual(settings.session_cookie_name,'__Host-pa_session')
                self.assertEqual(settings.csrf_cookie_name,'__Host-pa_csrf')
                self.assertTrue(settings.cookie_secure)

    def test_ambiguous_or_non_https_production_origins_rejected(self):
        for value in ('http://ssalfer.example.org','https://ssalfer.example.org/',
                      'https://*.example.org','https://one.example,https://two.example',
                      'https://ssalfer.example.org/path','https://ssalfer.example.org?x=1',
                      'https://ssalfer.example.org#fragment','https://user:synthetic@example.org'):
            with self.subTest(origin=value),self.assertRaises(RuntimeError):self.config('production',value)
        with self.assertRaises(RuntimeError):self.config('production','https://ssalfer.example.org','false')

    def test_development_origins_and_cookie_names_unchanged(self):
        settings=self.config('test','http://localhost:5174,http://localhost:8000','false')
        self.assertEqual(settings.allowed_origins,('http://localhost:5174','http://localhost:8000'))
        self.assertEqual(settings.session_cookie_name,'pa_session_dev')

    def test_docs_conditional_and_safe_logging_coexist(self):
        tree=ast.parse((ROOT/'backend/app/main.py').read_text())
        app=next(n for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call)
                 and isinstance(n.value.func,ast.Name) and n.value.func.id=='FastAPI')
        options={k.arg:ast.unparse(k.value) for k in app.value.keywords}
        for key,path in (('docs_url','/docs'),('redoc_url','/redoc'),('openapi_url','/openapi.json')):
            self.assertEqual(options[key],f"None if AUTH_SETTINGS.environment == 'production' else '{path}'")
        source=(ROOT/'backend/app/main.py').read_text()
        self.assertEqual(source.count('app.add_middleware(SafeDiagnosticsMiddleware'),1)
        self.assertIn('log_request_error(request.scope, category, 500)',source)

    def test_staging_and_runtime_hardening_are_preserved(self):
        self.assertFalse((ROOT/'frontend').exists())
        self.assertFalse((ROOT/'deploy/tls').exists(),'TLS stack remains an independent reviewed proposal')
        for filename in ('backend/Dockerfile','docker-compose.yml','docker-compose.override.yml'):
            text=(ROOT/filename).read_text()
            for value in ('--no-proxy-headers','--no-access-log','/app/logging.json'):
                self.assertIn(value,text,filename)
            self.assertNotIn('--workers',text)
        base=(ROOT/'docker-compose.yml').read_text()
        for key in ('REPORT_MAX_ROWS','DOCUMENT_INSPECTION_ENTRIES','IMPORT_MAX_RECORD_BYTES'):
            self.assertIn(key,base)

    def test_selected_publication_rules_preserve_report_only(self):
        text=(ROOT/'frontend-ssalfer/deploy/nginx.conf').read_text()
        self.assertIn('Content-Security-Policy-Report-Only',text)
        self.assertNotIn('add_header Content-Security-Policy ',text)
        for suffix in ('(md|cjs|map)$','^/(deploy|outputs|docs|tests)(/|$)'):
            self.assertIn(suffix,text)
        self.assertIn('proxy_hide_header Cache-Control;',text)
        self.assertIn('proxy_hide_header X-Content-Type-Options;',text)
        self.assertIn('proxy_cache off;',text)
        self.assertIn('log_format ssalfer_safe',text)


if __name__=='__main__':unittest.main()
