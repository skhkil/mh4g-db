#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'step3_auto_manual_parity_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)

def handler(route):
    u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ct='text/javascript'
    elif f.suffix=='.json': ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)

def wait_ready(pg):
    pg.wait_for_function("document.querySelector('#targetSkillPicker .search-select-input') && document.querySelector('#manualResult')",timeout=60000)

def add_target(pg,name):
    inp=pg.locator('#targetSkillPicker .search-select-input'); inp.click(); inp.fill(name); pg.wait_for_timeout(80)
    opt=pg.locator('#targetSkillPicker .search-select-option').filter(has_text=name).first
    if opt.count()!=1: return False
    opt.click(); pg.locator('#addTargetSkill').click(); pg.wait_for_timeout(60); return True

def table_points(loc):
    out={}
    rows=loc.locator('tbody tr')
    for i in range(rows.count()):
        cells=rows.nth(i).locator('td')
        if cells.count()<2: continue
        name=' '.join(cells.nth(0).inner_text().split())
        raw=''.join(cells.nth(1).inner_text().split()).replace('+','')
        try: out[name]=int(raw)
        except: pass
    return out

def run_case(browser,width,owned=False):
    errs=[]
    ctx=browser.new_context(viewport={'width':width,'height':1000})
    if owned:
        charms=[{'id':'step3c','skills':{'skill_0a0d7a1a0dde':5},'slots':0}]
        relics=[{'id':'step3r','decorationId':'relic_weapon_skill_0a0d7a1a0dde_3_5','skills':{'skill_0a0d7a1a0dde':5},'slots':3}]
        ctx.add_init_script(f"""(()=>{{const s={{'mh4g-owned-charms-v1':{json.dumps(json.dumps(charms))},'mh4g-owned-relic-weapons-v1':{json.dumps(json.dumps(relics))}}};Object.defineProperty(window,'localStorage',{{value:{{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])}},configurable:true}});}})();""")
    pg=ctx.new_page(); pg.route('http://app.local/**',handler)
    pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)))
    pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
    pg.set_content(HTML,wait_until='load',timeout=60000); wait_ready(pg)
    pg.locator('#clearTargets').click()
    targets=['명검'] if owned else ['고급귀마개','숫돌사용고속화']
    for t in targets:
        if not add_target(pg,t): errs.append('target add failed:'+t)
    pg.locator('#autoProgressionRank').select_option('g')
    if owned:
        pg.locator('#ownedCharmsOnly').check(); pg.locator('#ownedRelicWeaponsOnly').check()
    else:
        pg.locator('#autoWeaponSlots').select_option('3')
    pg.locator('#runSearch').click(); pg.wait_for_function("!document.querySelector('#runSearch').disabled",timeout=30000)
    exact=pg.locator('#searchResults [data-auto-build]')
    if exact.count()<1:
        errs.append('no exact auto build')
        result={'width':width,'owned':owned,'errors':errs}; ctx.close(); return result
    card=exact.first
    before=table_points(card.locator('.skill-points'))
    card_text=' '.join(card.inner_text().split())
    if owned:
        if '사용 호석:' not in card_text: errs.append('owned charm label missing')
        if '사용 발굴무기:' not in card_text: errs.append('owned relic label missing')
    card.click(); pg.wait_for_timeout(250)
    after=table_points(pg.locator('#manualResult .skill-points'))
    if before!=after: errs.append(f'auto/manual points differ before={before} after={after}')
    # explicit target thresholds remain active after application
    manual_text=' '.join(pg.locator('#manualResult').inner_text().split())
    for t in targets:
        if t not in manual_text: errs.append('target missing after apply:'+t)
    if owned:
        if pg.locator('#manualWeaponModeFilter').input_value()!='relic': errs.append('relic mode not applied')
        if pg.locator('#manualWeaponSlotFilter').input_value()!='3': errs.append('relic slot not applied')
        if pg.locator('#charmPoint1').input_value()!='5': errs.append('owned charm points not applied')
        if pg.locator('.weapon-card .deco-chip').count()!=1: errs.append('fixed relic decoration not applied')
    else:
        if pg.locator('#manualWeaponModeFilter').input_value()!='crafted': errs.append('crafted mode not applied')
        if pg.locator('#manualWeaponSlotFilter').input_value()!='3': errs.append('crafted weapon slots not applied')
    result={'width':width,'owned':owned,'before':before,'after':after,'cardText':card_text[:500],'ok':not errs,'errors':errs}
    ctx.close(); return result

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    runs=[run_case(browser,1365,False),run_case(browser,390,False),run_case(browser,1365,True),run_case(browser,390,True)]
    browser.close()
report={'version':'0.7.7-step3-auto-manual-parity','runs':runs,'ok':all(x.get('ok') for x in runs)}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2)); raise SystemExit(0 if report['ok'] else 1)
