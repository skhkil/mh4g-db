from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text().replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
 u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
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
  page.locator('#itemSearch').fill('공폭룡 강고리발톱');page.wait_for_timeout(400)
  page.locator('#itemTable [data-item-id="item_mh4u_0921"]').evaluate('(x)=>x.click()')
  page.locator('#itemTable details[data-xref-kind="acq-monster"] summary').evaluate('(x)=>x.click()')
  page.locator('#itemTable .item-acq-entry').first.wait_for(timeout=15000)
  txt=page.locator('#itemTable details[data-xref-kind="acq-monster"]').inner_text()
  ok=all(v in txt for v in ['유실물','유실물 최대 3회','포식 시 또는 구속공격 종료 시','G급 · 극한상태','42%','36%','32%']) and not errors
  results.append({'width':width,'ok':ok,'errors':errors,'evidence':txt[:1100]})
  page.close()
 b.close()
(ROOT/'tools/item_acquisition2_e2e.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps([{'width':x['width'],'ok':x['ok'],'errors':x['errors']} for x in results],ensure_ascii=False))
assert all(x['ok'] for x in results)
