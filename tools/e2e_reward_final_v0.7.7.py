#!/usr/bin/env python3
from pathlib import Path
from playwright.sync_api import sync_playwright
import urllib.parse,mimetypes,json
R=Path(__file__).resolve().parents[1]; HTML=(R/'index.html').read_text().replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
 f=(R/urllib.parse.unquote(urllib.parse.urlparse(route.request.url).path.lstrip('/'))).resolve()
 if not f.is_relative_to(R) or not f.is_file():return route.fulfill(status=404,body='missing')
 return route.fulfill(status=200,body=f.read_bytes(),content_type='text/javascript' if f.suffix=='.js' else (mimetypes.guess_type(str(f))[0] or 'application/octet-stream'))
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 runs=[]
 for width in (1365,390):
  ctx=b.new_context(viewport={'width':width,'height':900});pg=ctx.new_page();errors=[];pg.on('pageerror',lambda e:errors.append(str(e)));pg.route('http://app.local/**',handler);pg.set_content(HTML,wait_until='load');
  # Use original guide navigation selector from existing E2E
  pg.locator('.nav-group-toggle[data-submenu="weaponSubNav"]').click();pg.locator('#weaponSubNav [data-special-page="relic-equipment"]').click();pg.locator('#page-relic-equipment.active').wait_for(timeout=15000)
  pg.wait_for_timeout(400)
  body=pg.locator('body').inner_text()
  for s in ('추천 파밍 조합','몬스터별 기타 보상','라잔×2','12~16','테오'):
   assert s in body,(width,s)
  runs.append({'width':width,'ok':not errors,'errors':errors});ctx.close()
 b.close()
 (R/'tools/relic_reward_final_e2e.json').write_text(json.dumps({'ok':all(x['ok'] for x in runs),'runs':runs},ensure_ascii=False,indent=2));print(runs)
