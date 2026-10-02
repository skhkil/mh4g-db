#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'material_event_quest_links_hotfix5_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
    u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js':ct='text/javascript'
    elif f.suffix=='.json':ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def wait_page(pg,p): pg.wait_for_function("p=>document.querySelector('#page-'+p)?.classList.contains('active')",arg=p,timeout=30000)
errs=[]; facts={}
with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  pg=b.new_page(viewport={'width':1365,'height':960});pg.route('http://app.local/**',handler)
  pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)))
  pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
  pg.set_content(HTML,wait_until='load',timeout=60000);pg.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=60000)
  # 1) Event page must contain true missing JUMP quest and reward links.
  pg.locator('[data-route="quest-view"][data-quest-view="event-g"]').evaluate('e=>e.click()');wait_page(pg,'quest')
  for query,want in [('JUMP·작열연투!','JUMP·작열연투!'),('JUMP・작열열투!','JUMP·작열연투!'),('헌터 일지 괴조 편','헌터의 기록: 얀쿡크')]:
      pg.locator('#questSearch').fill(query);pg.wait_for_timeout(150)
      rows=pg.locator('#questTable tbody tr');
      if rows.count()<1: errs.append('event search no row:'+query);continue
      text=' '.join(rows.first.inner_text().split()); facts['search:'+query]=text[:500]
      if want not in text: errs.append(f'event search mismatch {query}: {text}')
  # Kirin typo alias lives in high events.
  pg.locator('[data-route="quest-view"][data-quest-view="event-high"]').evaluate('e=>e.click()');wait_page(pg,'quest')
  pg.locator('#questSearch').fill('Kirin Aquisition');pg.wait_for_timeout(150)
  text=' '.join(pg.locator('#questTable tbody tr').first.inner_text().split()) if pg.locator('#questTable tbody tr').count() else ''
  facts['kirin_typo']=text[:500]
  if '키린 쟁탈전' not in text: errs.append('Kirin typo alias not resolved')
  # Back to JUMP and validate monster/rewards.
  pg.locator('[data-route="quest-view"][data-quest-view="event-g"]').evaluate('e=>e.click()');wait_page(pg,'quest');pg.locator('#questSearch').fill('JUMP·작열연투!');pg.wait_for_timeout(150)
  row=pg.locator('#questTable tbody tr').first
  mons=[x.inner_text().strip() for x in row.locator('td.quest-monsters button').all()]; rewards=[x.inner_text().strip() for x in row.locator('td.quest-rewards button').all()]
  facts['jump_monsters']=mons;facts['jump_rewards']=rewards
  if mons!=['테오·테스카토르']: errs.append('JUMP monster mismatch:'+repr(mons))
  if '반역Ｊ티켓' not in rewards: errs.append('JUMP Treason J reward link missing')
  # 2) Material sourcing button from Rebellion King J armor must land on the actual quest.
  pg.locator('[data-submenu="bladeArmorSubNav"]').click();pg.locator('#bladeArmorSubNav [data-route="armor-detail"][data-rank="g"]').click();wait_page(pg,'armor')
  pg.locator('#armorSearch').fill('반역왕Ｊ해트');pg.wait_for_timeout(160)
  ar=pg.locator('#armorTable tr.armor-db-row').filter(has_text='반역왕Ｊ해트').first
  if not ar.count(): errs.append('Rebellion King J armor missing')
  else:
      ar.click();pg.wait_for_timeout(220);detail=ar.locator('xpath=following-sibling::tr[1]')
      # Locate exact source button by text.
      btn=detail.locator('[data-item-nav="quest"], [data-item-nav="questfilter"]').filter(has_text='JUMP·작열연투!').first
      if not btn.count(): errs.append('JUMP material source button missing')
      else:
          btn.click();wait_page(pg,'quest');pg.wait_for_timeout(180)
          rows=pg.locator('#questTable tbody tr');txt=' '.join(rows.first.inner_text().split()) if rows.count() else ''
          facts['material_nav_result']=txt[:600]
          if 'JUMP·작열연투!' not in txt: errs.append('material source did not land on JUMP quest')
  st=pg.locator('#appRuntimeStatus')
  if st.count() and not st.is_hidden(): errs.append('runtime status visible:'+st.inner_text())
  b.close()
rep={'ok':not errs,'facts':facts,'errors':errs};OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rep,ensure_ascii=False,indent=2));raise SystemExit(0 if rep['ok'] else 1)
