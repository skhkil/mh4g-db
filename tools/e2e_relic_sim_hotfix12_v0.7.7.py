#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text().replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
 u=urllib.parse.urlparse(route.request.url); f=(ROOT/urllib.parse.unquote(u.path.lstrip('/'))).resolve()
 if not f.is_relative_to(ROOT) or not f.is_file(): return route.fulfill(status=404,body='not found')
 return route.fulfill(status=200,body=f.read_bytes(),content_type='text/javascript' if f.suffix=='.js' else (mimetypes.guess_type(str(f))[0] or 'application/octet-stream'))
reports=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for width in (1365,390):
  errors=[];ctx=b.new_context(viewport={'width':width,'height':1000});pg=ctx.new_page();pg.route('http://app.local/**',handler);pg.on('pageerror',lambda e:errors.append(str(e)))
  pg.set_content(HTML,wait_until='load',timeout=30000)
  pg.locator('#manualWeaponModeFilter').wait_for(timeout=30000)
  pg.locator('#manualWeaponModeFilter').select_option('relic')
  pg.locator('#manualRelicDecorationPicker .search-select-input').wait_for(timeout=20000)
  assert pg.locator('#manualWeaponSlotFilter').input_value()=='3'
  pg.locator('#manualRelicDecorationPicker .search-select-input').click()
  options=pg.locator('#manualRelicDecorationPicker .search-select-option:not(.empty-option)')
  count=options.count();assert count>0,'3-slot relic options absent'
  texts=[options.nth(i).inner_text() for i in range(count)]
  assert all('3' in t for t in texts),'non-3-slot option leaked'
  options.first.click()
  assert pg.locator('#deco-editor-weapon .deco-chip').count()==1,'selection not applied'
  pg.locator('#manualWeaponSlotFilter').select_option('2')
  assert pg.locator('#deco-editor-weapon .deco-chip').count()==0,'slot switch not pruned'
  pg.locator('#manualRelicDecorationPicker .search-select-input').click()
  count2=pg.locator('#manualRelicDecorationPicker .search-select-option:not(.empty-option)').count()
  assert count2>0,'2-slot options missing'
  pg.locator('#manualWeaponModeFilter').select_option('crafted')
  assert pg.locator('#manualRelicDecorationPicker').count()==0,'relic UI left in crafted mode'
  reports.append({'width':width,'relic3Options':count,'relic2Options':count2,'errors':errors,'ok':not errors});ctx.close()
 b.close()
result={'ok':all(x['ok'] for x in reports),'runs':reports};(ROOT/'tools/relic_sim_hotfix12_e2e_v0.7.7.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['ok'] else 1)
