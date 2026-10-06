#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse,sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'tools'/'monster_links_hotfix11_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
INDEX=json.loads((ROOT/'data'/'monster_reference_index.json').read_text(encoding='utf-8'))['items']
def handler(route):
 u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
 if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
 ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
 if f.suffix=='.js': ct='text/javascript'
 elif f.suffix=='.json': ct='application/json'
 route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def wait_page(pg,p): pg.wait_for_function("p=>document.querySelector('#page-'+p)?.classList.contains('active')",arg=p,timeout=30000)
errs=[]; facts={}; bad=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 pg=b.new_page(viewport={'width':1365,'height':960}); pg.route('http://app.local/**',handler)
 pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)))
 pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
 pg.on('response',lambda r: bad.append((r.status,r.url)) if r.status>=400 else None)
 pg.set_content(HTML,wait_until='load',timeout=60000); pg.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=60000)
 pg.locator('[data-page="monster"]').click(); wait_page(pg,'monster')
 # Every monster must load exactly the quest count advertised by the index.
 mism=[]
 for name,meta in INDEX.items():
  pg.locator('#monsterSelect').select_option(label=name); pg.wait_for_timeout(10)
  pg.locator('[data-monster-tab="quests"]').click();
  want=int(meta.get('quests',0))
  pg.wait_for_function("want=>document.querySelectorAll('#monsterTabBody .monster-quest-row').length===want",arg=want,timeout=10000)
  got=pg.locator('#monsterTabBody .monster-quest-row').count()
  if got!=want: mism.append({'monster':name,'expected':want,'actual':got,'text':pg.locator('#monsterTabBody').inner_text()[:500]})
 facts['all_monster_ui_mismatch_count']=len(mism); facts['all_monster_ui_mismatches']=mism[:20]
 if mism: errs.append('monster UI quest-count mismatches: '+repr(mism[:5]))
 # User-reported Silver Rathalos path.
 pg.locator('#monsterSelect').select_option(label='리오레우스 희소종'); pg.wait_for_timeout(20); pg.locator('[data-monster-tab="quests"]').click(); pg.wait_for_function("()=>!document.querySelector('#monsterTabBody .monster-ref-loading')",timeout=10000)
 silver=' '.join(pg.locator('#monsterTabBody').inner_text().split()); facts['silver_rathalos']=silver
 if '이벤트 G★3 · 은빛 왕의 잠' not in silver: errs.append('Silver Rathalos missing G-event row')
 if '이벤트 ★7 · 탑의 재앙' not in silver: errs.append('Silver Rathalos missing Tower of Trouble')
 # Gold Rathian upstream correction regression.
 pg.locator('#monsterSelect').select_option(label='리오레이아 희소종'); pg.wait_for_timeout(20); pg.locator('[data-monster-tab="quests"]').click(); pg.wait_for_function("()=>!document.querySelector('#monsterTabBody .monster-ref-loading')",timeout=10000)
 gold=' '.join(pg.locator('#monsterTabBody').inner_text().split()); facts['gold_rathian']=gold
 if '이벤트 ★7 · 왕가의 부흥' not in gold: errs.append('Gold Rathian missing Royal Restoration')
 # Event quest special-form leakage regression.
 pg.locator('[data-route="quest-view"][data-quest-view="event-high"]').evaluate('e=>e.click()'); wait_page(pg,'quest'); pg.locator('#questSearch').fill('분노의 극치'); pg.wait_for_timeout(150)
 row=pg.locator('#questTable tbody tr').first
 mons=[x.inner_text().strip() for x in row.locator('td.quest-monsters button').all()] if row.count() else []
 facts['all_the_rage_monsters']=mons
 if mons!=['격앙 라잔']: errs.append('All The Rage monster list '+repr(mons))
 if any('.json.json' in u for _,u in bad): errs.append('double-json shard request found')
 facts['bad_requests']=bad[:20]
 b.close()
rep={'ok':not errs,'facts':facts,'errors':errs}; OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'ok':rep['ok'],'mismatchCount':facts['all_monster_ui_mismatch_count'],'allTheRage':facts['all_the_rage_monsters'],'errors':errs[:10]},ensure_ascii=False,indent=2)); raise SystemExit(0 if rep['ok'] else 1)
