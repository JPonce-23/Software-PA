"""Static integrity contract for two reviewed local pages; no browser/network/SCA."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

PAGES={'pages/fichaProyecto.html','pages/fichaFifonafe.html'}
REPORT='docs/security/ss09/paginas-protegidas.json'
INVENTORY='docs/security/ss08/inventario-recursos.json'

def read(root,relative):
    parts=PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or '..' in parts or '\\' in relative:
        raise ValueError('UNSAFE_PATH')
    path=root
    for part in parts:
        path=path/part
        if path.is_symlink():raise ValueError('SYMLINK')
    if not path.is_file() or path.stat().st_size>8*1024*1024:raise ValueError('SOURCE_TYPE_OR_SIZE')
    if relative not in {REPORT,INVENTORY} and not relative.startswith('frontend-ssalfer/'):
        raise ValueError('SOURCE_OUT_OF_SCOPE')
    if any(part.startswith('.env') or part in {'.git','.ssh','.aws'} for part in parts):raise ValueError('PRIVATE_SOURCE')
    return path.read_bytes()

def digest(root,name):return hashlib.sha256(read(root,name)).hexdigest()

class Resources(HTMLParser):
    def __init__(self):
        super().__init__();self.scripts=[];self.styles=[];self.images=[]
        self.inline_scripts=0;self.inline_styles=0;self.style_attributes=0;self.events=[];self.frames=[]
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if tag=='script':
            if data.get('src'):self.scripts.append(data['src'])
            else:self.inline_scripts+=1
        if tag=='style':self.inline_styles+=1
        if 'style' in data:self.style_attributes+=1
        self.events.extend(k for k,v in attrs if k.lower().startswith('on'))
        if tag=='link' and 'stylesheet' in data.get('rel',''):self.styles.append(data.get('href',''))
        if tag=='img' and data.get('src'):self.images.append(data['src'])
        if tag in ('iframe','object','embed'):self.frames.append(tag)
    def row(self,name,sha256):
        return dict(path=name,sha256=sha256,scripts=self.scripts,styles=self.styles,images=self.images,
            inline_scripts=self.inline_scripts,inline_styles=self.inline_styles,
            style_attributes=self.style_attributes,events=self.events,frames=self.frames)

def verify(root):
    root=Path(root);report=json.loads(read(root,REPORT));inventory=json.loads(read(root,INVENTORY))
    if report['schema_version']!=1 or {p['local']['path'] for p in report['pages']}!=PAGES or len(report['pages'])!=2:
        raise ValueError('PAGE_SET_DRIFT')
    checked=0
    for page in report['pages']:
        expected=page['local'];name=expected['path'];parser=Resources()
        parser.feed(read(root,'frontend-ssalfer/'+name).decode())
        observed=parser.row(name,digest(root,'frontend-ssalfer/'+name))
        saved=next(r for r in inventory['pages'] if r['path']==name)
        if observed!=expected or observed!=saved:raise ValueError('PAGE_INVENTORY_DRIFT')
        urls=[(kind,url) for kind,values in [('script',parser.scripts),('style',parser.styles),('image',parser.images)] for url in values]
        if urls!=[(r['kind'],r['url']) for r in page['resources']]:raise ValueError('RESOURCE_SET_DRIFT')
        for kind,url in urls:
            origin=urlsplit(url)
            if origin.scheme or origin.netloc:raise ValueError('EXTERNAL_RESOURCE_REQUIRES_REVIEW')
        for row in page['resources']+page['css_dependencies']+page['licenses']:
            if row.get('url')=='data:':continue
            if digest(root,row['path'])!=row['sha256']:raise ValueError('RESOURCE_OR_LICENSE_DRIFT')
            checked+=1
        excel=page['exceljs']
        for path,key in [('frontend-ssalfer/js/vendor/exceljs-4.4.0-ssalfer.min.js','bundle_sha256'),
                         (excel['runtime_graph'],'runtime_graph_sha256'),
                         (excel['licenses'],'licenses_sha256')]:
            if digest(root,path)!=excel[key]:raise ValueError('SHARED_EXCELJS_REFERENCE_DRIFT')
        if excel['loaded_by_page'] or any('exceljs' in url.lower() for url in parser.scripts):
            raise ValueError('EXCELJS_PAGE_LOADING_CHANGED_REVIEW_REQUIRED')
        if parser.frames or parser.events:raise ValueError('ACTIVE_HTML_REQUIRES_REVIEW')
        # Keep the existing inline scripts visible; this is not enforcement QA.
        if page['csp']['mode']!='Report-Only' or page['csp']['inline_scripts']!=parser.inline_scripts:
            raise ValueError('CSP_INVENTORY_DRIFT')
    return dict(status='PROTECTED_PAGES_INVENTORY_OK',pages=2,resource_records_checked=checked,
        scope='local static integrity; remote comparison stored separately; browser/CSP enforcement/SCA pending')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3]);args=parser.parse_args()
    try:result=verify(args.root)
    except (OSError,ValueError,KeyError,TypeError,StopIteration):
        print(json.dumps(dict(status='PROTECTED_PAGES_INVENTORY_FAILED')));return 2
    print(json.dumps(result,sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
