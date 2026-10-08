#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'tools'/'step2_final_merge_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
errs=[]; facts={}
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
  pg.set_content(HTML,wait_until='load',timeout=120000); pg.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('스킬 시뮬레이터')",timeout=120000)
  tests=[('event-high','선데이·어둠에 둥지 튼 자','선데이티켓'),('event-g','패미통·특별취재, 천회룡!','패미통쿠폰'),('event-high','OP·얼음 나라에서 온 아수','현상범수배서')]
  for view,qtext,reward in tests:
   pg.locator(f'[data-route="quest-view"][data-quest-view="{view}"]').evaluate('e=>e.click()'); pg.wait_for_function("document.querySelector('#page-quest').classList.contains('active')",timeout=30000)
   pg.locator('#questSearch').fill(qtext); pg.wait_for_timeout(220)
   rows=pg.locator('#questTable tbody tr')
   if rows.count()<1: errs.append(f'{width}:{qtext}:no row'); continue
   row=rows.first; txt=' '.join(row.inner_text().split()); buttons=[x.inner_text().strip() for x in row.locator('button').all()]
   facts[f'{width}:{qtext}']={'row':txt[:700],'buttons':buttons}
   if reward not in txt and reward not in buttons: errs.append(f'{width}:{qtext}:missing reward {reward}')
   btn=row.locator('button').filter(has_text=reward)
   if btn.count():
    btn.first.click(); pg.wait_for_timeout(350)
    det=pg.locator('.item-detail-inline details[data-xref-kind=\"acq-quest\"]')
    if det.count():
     det.first.locator('summary').click(); pg.wait_for_timeout(250)
     body=det.first.inner_text()
     if qtext not in body: errs.append(f'{width}:{qtext}:item reverse quest missing after reward click')
    else: errs.append(f'{width}:{qtext}:quest acquisition group missing after reward click')
  # Search all event data for restored Japanese marker.
  pg.locator('[data-route="quest-view"][data-quest-view="event-high"]').evaluate('e=>e.click()'); pg.wait_for_timeout(120); pg.locator('#questSearch').fill('JUMP'); pg.wait_for_timeout(180)
  if pg.locator('#questTable tbody tr').count()<1: errs.append(f'{width}:JUMP restored event search empty')
  ctx.close()
 b.close()
rep={'ok':not errs,'facts':facts,'errors':errs}; OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(rep,ensure_ascii=False,indent=2)); raise SystemExit(0 if rep['ok'] else 1)
