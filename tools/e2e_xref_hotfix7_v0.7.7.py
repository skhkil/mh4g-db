#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'tools'/'xref_hotfix7_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
 u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
 if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
 ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
 if f.suffix=='.js':ct='text/javascript'
 elif f.suffix=='.json':ct='application/json'
 route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def wait_page(pg,p):pg.wait_for_function("p=>document.querySelector('#page-'+p)?.classList.contains('active')",arg=p,timeout=30000)
errs=[];facts={}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 pg=b.new_page(viewport={'width':1365,'height':960});pg.route('http://app.local/**',handler)
 pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)))
 pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
 pg.set_content(HTML,wait_until='load',timeout=60000);pg.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=60000)
 # Monster reverse refs: generic all-large-monster quest must appear.
 pg.locator('[data-page="monster"]').click();wait_page(pg,'monster')
 pg.locator('#monsterSelect').select_option(label='도스이오스');pg.wait_for_timeout(100)
 pg.locator('[data-monster-tab="quests"]').click();pg.wait_for_timeout(250)
 txt=' '.join(pg.locator('#monsterTabBody').inner_text().split());facts['iodrome_quests']=txt[:2000]
 if '고난도: 검은 수렵' not in txt: errs.append('generic multi quest missing from 도스이오스 appearance list')
 # Base/subspecies separation.
 pg.locator('#monsterSelect').select_option(label='티가렉스');pg.wait_for_timeout(100);pg.locator('[data-monster-tab="quests"]').click();pg.wait_for_timeout(220)
 base=' '.join(pg.locator('#monsterTabBody').inner_text().split());facts['tigrex_quests']=base[:2000]
 if '고난도: 광기 어린 흑굉룡' in base: errs.append('base Tigrex still contains subspecies-only quest')
 pg.locator('#monsterSelect').select_option(label='티가렉스 아종');pg.wait_for_timeout(100);pg.locator('[data-monster-tab="quests"]').click();pg.wait_for_timeout(220)
 sub=' '.join(pg.locator('#monsterTabBody').inner_text().split());facts['brute_tigrex_quests']=sub[:2000]
 if '고난도: 광기 어린 흑굉룡' not in sub: errs.append('Brute Tigrex missing its quest')
 # Quest side: generic G3 quest should expose all 5 monsters.
 pg.locator('[data-route="quest-view"][data-quest-view="g-detail"]').evaluate('e=>e.click()');wait_page(pg,'quest');pg.locator('#questSearch').fill('고난도: 몬스터 헌터');pg.wait_for_timeout(180)
 row=pg.locator('#questTable tbody tr').first
 mons=[x.inner_text().strip() for x in row.locator('td.quest-monsters button').all()] if row.count() else []
 facts['monster_hunter_monsters']=mons
 expected=['티가렉스','진오우거','브라키디오스','고어·마가라','셀레기오스']
 if mons!=expected: errs.append('Monster Hunter quest monster list mismatch:'+repr(mons))
 b.close()
rep={'ok':not errs,'facts':facts,'errors':errs};OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rep,ensure_ascii=False,indent=2));raise SystemExit(0 if rep['ok'] else 1)
