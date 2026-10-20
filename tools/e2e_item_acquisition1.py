from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text().replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
 u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
 if not str(f).startswith(str(ROOT)) or not f.is_file():route.fulfill(status=404,body='not found');return
 ct='text/javascript' if f.suffix=='.js' else ('application/json' if f.suffix=='.json' else mimetypes.guess_type(str(f))[0] or 'application/octet-stream')
 route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
results=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for width in (1365,390):
  page=b.new_page(viewport={'width':width,'height':844});page.route('http://app.local/**',handler);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(HTML,wait_until='load',timeout=60000)
  page.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=60000)
  page.locator('[data-page="item"]').first.evaluate('(x)=>x.click()')
  page.wait_for_function("document.querySelector('#page-item')?.classList.contains('active')",timeout=15000)
  target=page.evaluate('''async()=>{const r=await fetch('./data/item_references.json').then(r=>r.json()); const row=Object.entries(r.items).find(([k,v])=>v.acquire.some(x=>x.type==='monster'&&x.method==='최대 3회'));return {id:row?.[0],name:row?.[1]?.name}}''')
  if not target['id']:raise RuntimeError('no ambiguous record')
  page.locator('#itemSearch').fill(target['name']);page.wait_for_timeout(350)
  button=page.locator('#itemTable [data-item-id="'+target['id']+'"]')
  button.evaluate('(x)=>x.click()')
  page.locator('#itemTable details[data-xref-kind="acq-monster"]').wait_for(timeout=20000)
  page.locator('#itemTable details[data-xref-kind="acq-monster"] summary').evaluate('(x)=>x.click()')
  page.locator('#itemTable .item-acq-entry').first.wait_for(timeout=15000)
  txt=page.locator('#itemTable details[data-xref-kind="acq-monster"]').inner_text()
  is_ok=('원본: 최대 3회' in txt and '획득 방식 미확인' in txt and '표기 확률' in txt and not errors)
  results.append({'width':width,'item':target,'ok':is_ok,'errors':errors,'sample':txt[:260]})
  page.close()
 b.close()
(ROOT/'tools/item_acquisition1_e2e.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
assert all(x['ok'] for x in results)
