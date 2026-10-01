#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'ui_rewards_hotfix_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
weapons=json.loads((ROOT/'data'/'weapons.json').read_text(encoding='utf-8'))
bow_names={x['name'] for x in weapons if x.get('weaponType')=='활'}
def handler(route):
    u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file():route.fulfill(status=404,body='not found',content_type='text/plain');return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js':ct='text/javascript'
    elif f.suffix=='.json':ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def add_target(page,name):
    inp=page.locator('#targetSkillPicker .search-select-input');inp.click();inp.fill(name);page.wait_for_timeout(80);page.locator('#targetSkillPicker .search-select-option').filter(has_text=name).first.click();page.locator('#addTargetSkill').click()
errs=[];facts={}
with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  ctx=b.new_context(viewport={'width':1365,'height':960})
  ctx.add_init_script("""(()=>{const s={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])},configurable:true});})();""")
  pg=ctx.new_page();pg.route('http://app.local/**',handler)
  pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)));pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
  pg.set_content(HTML,wait_until='load',timeout=30000);pg.wait_for_function("document.querySelector('#charmSkill1Picker .search-select-input')",timeout=30000)
  # owned charm storage moved inline below manual charm; old panel absent
  facts['inlineCharmSave']=pg.locator('[data-save-owned-charm]').count()==1 and pg.locator('.owned-charm-inline').count()==1
  facts['oldOwnedPanelAbsent']=pg.locator('.owned-charm-panel').count()==0
  if not facts['inlineCharmSave']: errs.append('owned charm inline save missing')
  if not facts['oldOwnedPanelAbsent']: errs.append('old owned charm panel remains')
  # Auto weapon type is independent from manual simulator weapon filter.
  pg.locator('#manualWeaponTypeFilter').select_option('대검');pg.locator('#manualWeaponSearchButton').click();pg.wait_for_timeout(80)
  pg.locator('#autoWeaponType').select_option('활')
  add_target(pg,'고급귀마개');pg.locator('#autoProgressionRank').select_option('g')
  st=time.perf_counter();pg.locator('#runSearch').click();pg.wait_for_function("!document.querySelector('#runSearch')?.disabled",timeout=30000);facts['searchSec']=round(time.perf_counter()-st,2)
  cards=pg.locator('#searchResults .build-card-clickable');facts['cards']=cards.count()
  if not cards.count(): errs.append('no exact auto build result')
  else:
    txt=' '.join(cards.first.inner_text().split())
    # weapon is first value after label; compare any bow name contained in card
    matched=next((n for n in bow_names if n in txt),None);facts['autoBow']=matched
    if not matched: errs.append('auto build did not choose a bow independently:'+txt[:500])
    if '완성 커스텀 구성' in txt: errs.append('duplicate full custom box/text remains')
    th=[x.inner_text().strip() for x in cards.first.locator('table.skill-points thead th').all()]
    facts['compactHeaders']=th
    if th!=['스킬 계통','포인트','발동 스킬']: errs.append('compact skill headers unexpected:'+repr(th))
  # decoration route UI
  pg.locator('[data-route="decoration-view"][data-deco-view="type"]').evaluate('e=>e.click()');pg.wait_for_function("document.querySelector('#page-decoration').classList.contains('active')",timeout=15000)
  deco_head=' '.join(pg.locator('#decoTable').inner_text().split()[:40]);facts['decoHeader']=deco_head
  if '해금/소재 경로' not in pg.locator('#decoTable').inner_text(): errs.append('decoration unlock route column missing')
  if '직접 레시피 해금 조건' not in pg.locator('#page-decoration').inner_text(): errs.append('decoration unlock disclaimer missing')
  # event rewards/no note column: Ruby of my Eye is a known previously-empty reward row.
  pg.locator('[data-route="quest-view"][data-quest-view="event-g"]').evaluate('e=>e.click()');pg.wait_for_function("document.querySelector('#page-quest').classList.contains('active')",timeout=15000)
  pg.locator('#questSearch').fill('나의 루비');pg.wait_for_timeout(120)
  qtext=' '.join(pg.locator('#questTable').inner_text().split());facts['rubyText']=qtext[:500]
  if '비고' in pg.locator('#questTable thead').inner_text(): errs.append('event notes header remains')
  if '대장로티켓' not in qtext or ('은알' not in qtext and 'Silver Egg' not in qtext): errs.append('Ruby event major rewards missing:'+qtext[:500])
  # episodic special reward
  pg.locator('[data-route="quest-view"][data-quest-view="event-episodic"]').evaluate('e=>e.click()');pg.wait_for_timeout(100);pg.locator('#questSearch').fill('개기일식');pg.wait_for_timeout(120)
  et=' '.join(pg.locator('#questTable').inner_text().split());facts['eclipseText']=et[:500]
  if '점보티켓' not in et or 'Pride of Harth' not in et: errs.append('Total Eclipse special rewards missing:'+et[:500])
  b.close()
report={'ok':not errs,'facts':facts,'errors':errs};OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
