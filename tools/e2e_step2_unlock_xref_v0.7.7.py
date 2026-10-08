#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'step2_unlock_xref_e2e_v0.7.7.json'
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
    ctx=b.new_context(viewport={'width':width,'height':950}); pg=ctx.new_page(); pg.route('http://app.local/**',handler)
    pg.on('pageerror',lambda e,w=width:errs.append(f'{w}:pageerror:{e}'))
    pg.on('console',lambda m,w=width:errs.append(f'{w}:console:{m.text}') if m.type=='error' else None)
    pg.set_content(HTML,wait_until='load',timeout=120000)
    pg.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('스킬 시뮬레이터')",timeout=120000)

    # Quest -> unlock: Tetsucabra must show decoration facility + delivery request.
    pg.locator('[data-submenu="questSubNav"]').click(); pg.locator('#questSubNav [data-quest-view="village-detail"]').click()
    pg.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('여단상세')",timeout=30000)
    pg.locator('#questSearch').fill('위기! 테츠카브라를 사냥하라!'); pg.wait_for_timeout(180)
    txt=pg.locator('#questTable').inner_text(); facts[f'{width}:tetsu']=txt[:2000]
    for expected in ('장식주 생산/탈착','거래는 꿀맛'):
      if expected not in txt: errs.append(f'{width}:tetsu missing {expected}')

    # Quest -> multiple Wyporium unlocks.
    pg.locator('#questSearch').fill('못된 악동 기원호를 수렵하라'); pg.wait_for_timeout(180)
    qtxt=pg.locator('#questTable').inner_text(); facts[f'{width}:kecha']=qtxt[:2000]
    if '용인족 교환' not in qtxt: errs.append(f'{width}:kecha Wyporium unlock missing')

    # Wyporium -> quest reverse navigation.
    pg.locator('[data-submenu="dragonSubNav"]').click(); pg.locator('#dragonSubNav [data-dragon-view="exchange"]').click()
    pg.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('교환소재')",timeout=30000)
    pg.locator('#dragonSearch').fill('청웅수 갑각'); pg.wait_for_timeout(180)
    dtxt=pg.locator('#dragonTable').inner_text(); facts[f'{width}:dragon']=dtxt[:1500]
    if '못된 악동 기원호' not in dtxt: errs.append(f'{width}:dragon reverse quest link missing')
    if pg.locator('#dragonTable [data-item-nav="quest"]').count()<1: errs.append(f'{width}:dragon quest button missing')
    else:
      pg.locator('#dragonTable [data-item-nav="quest"]').first.click(); pg.wait_for_timeout(250)
      if '퀘스트' not in pg.locator('#pageTitle').inner_text(): errs.append(f'{width}:dragon quest navigation failed')

    # Decoration reverse prerequisite route. Pick first indexed decoration target dynamically.
    idx=json.loads((ROOT/'data/quest_unlock_index.json').read_text(encoding='utf-8'))
    deco=next((v for v in idx['targets'].values() if v.get('type')=='decoration'),None)
    if deco:
      pg.locator('[data-submenu="decoSubNav"]').click(); pg.locator('#decoSubNav [data-deco-view="type"]').click()
      pg.wait_for_function("document.querySelector('#page-decoration')?.classList.contains('active') || getComputedStyle(document.querySelector('#page-decoration')).display !== 'none'",timeout=30000)
      pg.locator('#decoSearch').fill(deco['name']); pg.wait_for_timeout(180)
      dectxt=pg.locator('#decoTable').inner_text(); facts[f'{width}:deco']={'name':deco['name'],'text':dectxt[:1500]}
      if '선행 퀘스트' not in dectxt: errs.append(f'{width}:decoration reverse prerequisite missing')
      if '직접 레시피 해금이 아니라' not in dectxt: errs.append(f'{width}:decoration indirect disclaimer missing')
    ctx.close()
  b.close()
report={'ok':not errs,'facts':facts,'errors':errs}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
