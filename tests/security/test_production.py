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

    def test_production_docs_disabled(self):
        source = (ROOT / "backend/app/main.py").read_text()
        for option in ("docs_url", "redoc_url", "openapi_url"):
            self.assertIn(option + '=None if AUTH_SETTINGS.environment == "production"', source)

if __name__ == "__main__":
    unittest.main()
