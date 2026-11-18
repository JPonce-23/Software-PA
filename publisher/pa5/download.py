"""Download only a same-repository release asset by numeric ID; fixed hash checked downstream."""
import os
import re
import shutil
import sys
import urllib.request
from pa5_supply import require

asset_id, target = sys.argv[1:]
require(bool(re.fullmatch(r'[1-9][0-9]*', asset_id)), 'NUMERIC_RELEASE_ASSET_ID_REQUIRED')
url = 'https://api.github.com/repos/JPonce-23/Software-PA/releases/assets/' + asset_id
# GitHub's signed asset redirect must not receive the repository Authorization header.
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        require(newurl.startswith('https://'), 'HTTPS_REDIRECT_REQUIRED')
        redirected.remove_header('Authorization')
        return redirected
request = urllib.request.Request(url, headers={'Accept': 'application/octet-stream',
    'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'software-pa-pa5-publisher'})
with urllib.request.build_opener(Redirect()).open(request, timeout=120) as source, open(target, 'xb') as out:
    shutil.copyfileobj(source, out, 1048576)
