#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'auto_build_stage3_5_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
    u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file():route.fulfill(status=404,body='not found',content_type='text/plain');return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js':ct='text/javascript'
    elif f.suffix=='.json':ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def add_target(page,name):
    inp=page.locator('#targetSkillPicker .search-select-input');inp.click();inp.fill(name);page.wait_for_timeout(80);page.locator('#targetSkillPicker .search-select-option').filter(has_text=name).first.click();page.locator('#addTargetSkill').click()
def set_charm(pg,skill,point,slots):
    inp=pg.locator('#charmSkill1Picker .search-select-input');inp.click();inp.fill(skill);pg.wait_for_timeout(80);pg.locator('#charmSkill1Picker .search-select-option').filter(has_text=skill).first.click();pg.locator('#charmPoint1').fill(str(point));pg.locator('#charmSlots').select_option(str(slots));pg.wait_for_timeout(80)
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    ctx=b.new_context(viewport={'width':1280,'height':900})
    ctx.add_init_script("""(()=>{const s={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])},configurable:true});})();""")
    pg=ctx.new_page();pg.route('http://app.local/**',handler)
    pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)));pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
    pg.set_content(HTML,wait_until='load',timeout=30000);pg.wait_for_function("document.querySelector('#charmSkill1Picker .search-select-input')",timeout=30000)
    set_charm(pg,'청각보호',5,3);pg.locator('#saveOwnedCharm').click();pg.wait_for_timeout(80)
    set_charm(pg,'회피성능',5,3);pg.locator('#saveOwnedCharm').click();pg.wait_for_timeout(80)
    cnt=pg.locator('#ownedCharmList .owned-charm-row').count()
    if cnt!=2:errs.append(f'owned charms not rendered:{cnt}')
    pg.locator('#ownedCharmsOnly').check();add_target(pg,'고급귀마개');pg.locator('#autoProgressionRank').select_option('g')
    st=time.perf_counter();pg.locator('#runSearch').click();pg.wait_for_function("!document.querySelector('#runSearch')?.disabled",timeout=30000);elapsed=time.perf_counter()-st
    body=' '.join(pg.locator('#searchResults').inner_text().split());cards=pg.locator('#searchResults .build-card-clickable').count()
    if cards<1:errs.append('owned charm search no exact result:'+body[:700])
    for want in ['사용 호석','완성 커스텀 구성','머리','몸통','호석']:
        if cards and want not in body:errs.append('missing full custom text:'+want)
    if cards:
        pg.locator('#searchResults .build-card-clickable').first.click();pg.wait_for_timeout(150);manual=' '.join(pg.locator('#manualResult').inner_text().split())
        if not ('청각보호 +5' in manual or '회피성능 +5' in manual):errs.append('selected owned charm not applied:'+manual[:500])
    if elapsed>25:errs.append(f'owned charm search too slow:{elapsed:.2f}')
    report={'ok':not errs,'elapsedSec':round(elapsed,2),'ownedCount':cnt,'exactCards':cards,'errors':errs};b.close()
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
