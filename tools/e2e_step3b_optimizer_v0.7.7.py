#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse,re
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'step3b_optimizer_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
EVASION='skill_977515684794'
CHARMS=[{'id':'ukau-evasion5-s3','skills':{EVASION:5},'slots':3}]
TARGETS=['심안','약점특효','회피성능+3','공격력UP【소】','예리도레벨+1']
UKAU=['우캄루X사쿠파케','카이저X메일','우캄루X사쿰페','카이저X펄드','우캄루X케마르']

def handler(route):
    u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ct='text/javascript'
    elif f.suffix=='.json': ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)

def add_target(pg,name):
    inp=pg.locator('#targetSkillPicker .search-select-input'); inp.click(); inp.fill(name); pg.wait_for_timeout(60)
    opt=pg.locator('#targetSkillPicker .search-select-option').filter(has_text=re.compile(r'^'+re.escape(name)+r' \(')).first
    if opt.count()!=1:return False
    opt.click(); pg.locator('#addTargetSkill').click(); pg.wait_for_timeout(50); return True

def run(browser,width):
    errs=[]; ctx=browser.new_context(viewport={'width':width,'height':1100})
    ctx.add_init_script(f"""(()=>{{const s={{'mh4g-owned-charms-v1':{json.dumps(json.dumps(CHARMS))}}};Object.defineProperty(window,'localStorage',{{value:{{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])}},configurable:true}});}})();""")
    pg=ctx.new_page();pg.route('http://app.local/**',handler)
    pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)))
    pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
    pg.set_content(HTML,wait_until='load',timeout=60000)
    pg.wait_for_function("document.querySelector('#targetSkillPicker .search-select-input')",timeout=60000)
    pg.locator('#clearTargets').click()
    for t in TARGETS:
        if not add_target(pg,t):errs.append('target add failed:'+t)
    pg.locator('#autoProgressionRank').select_option('g')
    pg.locator('#autoWeaponSlots').select_option('2')
    pg.locator('#ownedCharmsOnly').check()
    pg.locator('#runSearch').click();pg.wait_for_function("!document.querySelector('#runSearch').disabled",timeout=45000)
    cards=pg.locator('#searchResults [data-auto-build]')
    matched=None; texts=[]
    for i in range(cards.count()):
        txt=' '.join(cards.nth(i).inner_text().split());texts.append(txt[:1000])
        if all(n in txt for n in UKAU): matched=cards.nth(i);break
    if matched is None:errs.append('우카우카우 exact card missing')
    else:
        txt=' '.join(matched.inner_text().split())
        for t in TARGETS:
            if t not in txt:errs.append('target missing:'+t)
        if '내진' not in txt:errs.append('residual extra skill 내진 missing')
        if '항진주【1】' not in txt:errs.append('항진주【1】 missing')
        matched.click();pg.wait_for_timeout(200)
        manual=' '.join(pg.locator('#manualResult').inner_text().split())
        for t in TARGETS+['내진']:
            if t not in manual:errs.append('manual apply missing:'+t)
    result={'width':width,'ok':not errs,'errors':errs,'cards':cards.count(),'matchedText':(' '.join(matched.inner_text().split())[:1800] if matched else None),'sampleCards':texts[:3]}
    ctx.close();return result

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    runs=[run(browser,1365),run(browser,390)];browser.close()
report={'version':'0.7.7-step3b-optimizer','runs':runs,'ok':all(r['ok'] for r in runs)}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
