#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'armor_monster_search_step15_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
errs=[];facts={}
def handler(route):
    u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ct='text/javascript'
    elif f.suffix=='.json': ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  for width in (1365,390):
    ctx=b.new_context(viewport={'width':width,'height':900}); pg=ctx.new_page(); pg.route('http://app.local/**',handler)
    pg.on('pageerror',lambda e,w=width:errs.append(f'{w}:pageerror:{e}'))
    pg.on('console',lambda m,w=width:errs.append(f'{w}:console:{m.text}') if m.type=='error' else None)
    pg.set_content(HTML,wait_until='load',timeout=120000)
    for hunter,submenu in [('blade','bladeArmorSubNav'),('gunner','gunnerArmorSubNav')]:
      pg.locator(f'[data-submenu="{submenu}"]').click()
      pg.locator(f'#{submenu} [data-route="armor-set"]').click()
      pg.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('방어구 세트')",timeout=30000)
      for q in ['모노블로스 아종','백일각룡','White Monoblos','모노데블']:
        pg.locator('#armorSetSearch').fill(q); pg.wait_for_timeout(150)
        rows=pg.locator('#armorSetTable tbody tr'); n=rows.count(); txt=' | '.join(rows.nth(i).inner_text() for i in range(n))
        facts[f'{width}:{hunter}:{q}']={'rows':n,'text':txt[:1200]}
        if n!=1: errs.append(f'{width}:{hunter}:{q}: expected 1 row, got {n}')
        if '모노데블' not in txt: errs.append(f'{width}:{hunter}:{q}: monodevil label missing')
        if '모노블로Z' in txt: errs.append(f'{width}:{hunter}:{q}: stale label visible')
      pg.locator(f'[data-submenu="{submenu}"]').click()
      pg.locator(f'#{submenu} [data-route="armor-detail"][data-rank="g"]').evaluate('(el)=>el.click()')
      pg.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('방어구 상세')",timeout=30000)
      pg.locator('#armorSearch').fill('모노데블'); pg.wait_for_timeout(150); atxt=pg.locator('#armorTable').inner_text()
      expected='모노데블암' if hunter=='blade' else '모노데블가드'
      if expected not in atxt: errs.append(f'{width}:{hunter}: corrected arm missing')
      if '모노블로Z암' in atxt or '모노블로Z가드' in atxt: errs.append(f'{width}:{hunter}: stale arm visible')
    ctx.close()
  b.close()
report={'ok':not errs,'facts':facts,'errors':errs}; OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
