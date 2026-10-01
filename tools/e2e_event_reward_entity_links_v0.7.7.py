#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'event_reward_entity_links_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
    u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain');return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js':ct='text/javascript'
    elif f.suffix=='.json':ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
errs=[];facts={}
with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  pg=b.new_page(viewport={'width':1365,'height':960});pg.route('http://app.local/**',handler)
  pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)));pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
  pg.set_content(HTML,wait_until='load',timeout=30000);pg.wait_for_function("document.querySelector('[data-route=\"quest-view\"]')",timeout=30000)
  tests=[
    ('event-high','오늘의 특선: 고기','빈티지고기티켓','item'),
    ('event-g','태고의 달인: 배북 난타전','축제북악보','item'),
    ('event-episodic','코드 퍼플','네코트티켓','item'),
    ('event-episodic','코드 화이트','응견의 피어스','armor'),
    ('event-episodic','개기일식','Pride of Harth','weapon'),
  ]
  for view,qtext,label,kind in tests:
    pg.locator(f'[data-route="quest-view"][data-quest-view="{view}"]').evaluate('e=>e.click()');pg.wait_for_function("document.querySelector('#page-quest').classList.contains('active')",timeout=15000)
    pg.locator('#questSearch').fill(qtext);pg.wait_for_timeout(150)
    row=pg.locator('#questTable tbody tr').first
    txt=' '.join(row.inner_text().split()) if row.count() else ''
    buttons=row.locator('td').nth(5).locator('button') if row.count() else pg.locator('___none')
    btxt=[x.inner_text().strip() for x in buttons.all()]
    facts[qtext]={'row':txt[:400],'buttons':btxt}
    if label not in btxt: errs.append(f'{qtext}: expected linked label {label!r}, got {btxt!r}')
    if label in btxt:
      btn=buttons.filter(has_text=label).first
      nav=btn.get_attribute('data-item-nav'); openitem=btn.get_attribute('data-open-item')
      if kind=='item' and not openitem: errs.append(f'{qtext}: item button missing data-open-item')
      if kind in ('armor','weapon') and nav!=kind: errs.append(f'{qtext}: expected nav {kind}, got {nav}')
  b.close()
rep={'ok':not errs,'facts':facts,'errors':errs};OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rep,ensure_ascii=False,indent=2));raise SystemExit(0 if rep['ok'] else 1)
