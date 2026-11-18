import base64
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]

class ProductionSecurity(unittest.TestCase):
    def test_production_requires_exact_https_origin(self):
        for origin, valid in [("https://ssalfer.example.org", True),
                              ("https://203.0.113.10", True),
                              ("http://ssalfer.example.org", False),
                              ("https://ssalfer.example.org/", False),
                              ("https://*.example.org", False),
                              ("https://one.example,https://two.example", False)]:
            with self.subTest(origin=origin):
                env = dict(os.environ, APP_ENV="production", AUTH_COOKIE_SECURE="true", CORS_ORIGINS=origin)
                result = subprocess.run([sys.executable, "-c", "from app.config import AUTH_SETTINGS"],
                                        cwd=ROOT / "backend", env=env, capture_output=True)
                self.assertEqual(result.returncode == 0, valid)

    def test_inline_scripts_have_csp_hash(self):
        policy = (ROOT / "deploy/tls/headers.conf").read_text(encoding="utf-8")
        self.assertNotIn("script-src 'self' 'unsafe-inline'", policy)
        for page in (ROOT / "frontend-ssalfer").rglob("*.html"):
            if "deploy" in page.parts:
                continue
            for script in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>', page.read_text(encoding="utf-8")):
                if script.strip():
                    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                    self.assertIn("sha256-" + digest, policy, str(page))

    def test_csp_hash_inventory_matches_published_scripts_and_both_policies(self):
        import json
        from test_http_deployment_security import parse_config, values

        web=ROOT/'frontend-ssalfer'
        scripts=[]
        # Same runtime HTML roots copied by the frontend Dockerfile. Build tools
        # and their ignored node_modules are never published by this image.
        for page in sorted([*web.glob('*.html'),*(web/'pages').rglob('*.html')]):
            source=page.read_text(encoding='utf-8')
            for match in re.finditer(r'<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>',source):
                if match[1].strip():
                    body=match[1].encode('utf-8')
                    scripts.append(dict(page=str(page.relative_to(web)),
                                        line=source[:match.start()].count('\n')+1,bytes=len(body),
                                        sha256=base64.b64encode(hashlib.sha256(body).digest()).decode()))
        inventory=json.loads((ROOT/'docs/security/ss09/csp-inline-sha256.json').read_text())
        self.assertEqual(scripts,inventory['scripts'])
        self.assertTrue(scripts)
        expected={"'sha256-"+script['sha256']+"'" for script in scripts} | {"'self'"}
        for file in ('deploy/tls/headers.conf','frontend-ssalfer/deploy/nginx.conf'):
            with self.subTest(file=file):
                config=parse_config((ROOT/file).read_text())
                if file.startswith('frontend'):
                    config=next(block for block in config.children if block.words==['server'])
                headers=values(config,'add_header')
                self.assertFalse(any(row[0]=='Content-Security-Policy' for row in headers))
                policies=[row for row in headers if row[0]=='Content-Security-Policy-Report-Only']
                self.assertEqual(len(policies),1)
                self.assertEqual(policies[0][2],'always')
                directives=[part.split() for part in policies[0][1].split(';') if part.strip()]
                script_src=[tokens[1:] for tokens in directives if tokens[0]=='script-src']
                self.assertEqual(len(script_src),1)
                self.assertCountEqual(script_src[0],expected)

    def test_production_docs_disabled(self):
        source = (ROOT / "backend/app/main.py").read_text()
        for option in ("docs_url", "redoc_url", "openapi_url"):
            self.assertIn(option + '=None if AUTH_SETTINGS.environment == "production"', source)

if __name__ == "__main__":
    unittest.main()
