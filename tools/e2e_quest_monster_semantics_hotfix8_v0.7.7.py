#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'tools'/'quest_monster_semantics_hotfix8_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
 u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
 if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
 ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
 if f.suffix=='.js':ct='text/javascript'
 elif f.suffix=='.json':ct='application/json'
 route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def wait_page(pg,p): pg.wait_for_function("p=>document.querySelector('#page-'+p)?.classList.contains('active')",arg=p,timeout=30000)
def monster_quests(pg,label):
 pg.locator('[data-page="monster"]').click(); wait_page(pg,'monster'); pg.locator('#monsterSelect').select_option(label=label); pg.wait_for_timeout(100); pg.locator('[data-monster-tab="quests"]').click(); pg.wait_for_timeout(250); return ' '.join(pg.locator('#monsterTabBody').inner_text().split())
def quest_mons(pg,term):
 pg.locator('[data-route="quest-view"][data-quest-view="g-detail"]').evaluate('e=>e.click()'); wait_page(pg,'quest'); pg.locator('#questSearch').fill(term); pg.wait_for_timeout(250); row=pg.locator('#questTable tbody tr').first
 if not row.count(): return []
 return [x.inner_text().strip() for x in row.locator('td.quest-monsters button').all()]
errs=[];facts={};bad_requests=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 pg=b.new_page(viewport={'width':1365,'height':960}); pg.route('http://app.local/**',handler)
 pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)))
 pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
 pg.on('response',lambda r: bad_requests.append((r.status,r.url)) if r.status>=400 else None)
 pg.set_content(HTML,wait_until='load',timeout=60000); pg.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=60000)
 rust=monster_quests(pg,'녹슨크샬다오라'); facts['rusted_kushala']=rust
 for name in ['결전! 크샬다오라!','고난도: 불협화음 바람이 불다','녹슨강룡 대비 방위 작전!']:
  if name not in rust: errs.append('Rusted Kushala missing '+name)
 if '고난도: 강철 모래 폭풍' in rust: errs.append('Rusted Kushala wrongly contains normal quest 고난도: 강철 모래 폭풍')
 if 'G급 ★3 · 강룡 대비 방위 작전!' in rust: errs.append('Rusted Kushala wrongly contains exact normal Operation Windbreaker row')
 normal=monster_quests(pg,'크샬다오라'); facts['normal_kushala']=normal
 for name in ['고난도: 강철 모래 폭풍','강룡 대비 방위 작전!']:
  if name not in normal: errs.append('Normal Kushala missing '+name)
 for name in ['고난도: 불협화음 바람이 불다','녹슨강룡 대비 방위 작전!']:
  if name in normal: errs.append('Normal Kushala wrongly contains rusted quest '+name)
 chaotic=monster_quests(pg,'혼돈의 고어·마가라'); facts['chaotic_gore']=chaotic
 for name in ['하늘을 보듯 그들을 보라','고난도: 숙환, 자각은 멀고','고난도: 벗겨지는 재앙의 외투','고난도: 혼돈의 고어·마가라']:
  if name not in chaotic: errs.append('Chaotic Gore missing '+name)
 raging=monster_quests(pg,'임계 브라키디오스'); facts['raging_brachy']=raging
 if '고난도: 흩날리는 연폭의 꽃' not in raging: errs.append('Raging Brachydios missing standard quest')
 facts['winds_monsters']=quest_mons(pg,'불협화음')
 if facts['winds_monsters']!=['녹슨크샬다오라']: errs.append('Winds of Discord monsters '+repr(facts['winds_monsters']))
 facts['into_heavens_monsters']=quest_mons(pg,'하늘을 보듯')
 if set(facts['into_heavens_monsters'])!=set(['진오우거 아종','혼돈의 고어·마가라']): errs.append('Into the Heavens monsters '+repr(facts['into_heavens_monsters']))
 facts['achy_brachy_monsters']=quest_mons(pg,'흩날리는 연폭')
 if facts['achy_brachy_monsters']!=['임계 브라키디오스']: errs.append('Achy Brachy monsters '+repr(facts['achy_brachy_monsters']))
 if any('.json.json' in u for _,u in bad_requests): errs.append('monster shard .json.json request found')
 facts['bad_requests']=bad_requests[:20]
 b.close()
rep={'ok':not errs,'facts':facts,'errors':errs}; OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(rep,ensure_ascii=False,indent=2)); raise SystemExit(0 if rep['ok'] else 1)
