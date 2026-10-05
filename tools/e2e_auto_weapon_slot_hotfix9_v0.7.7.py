#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'auto_weapon_slot_hotfix9_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
    u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js':ct='text/javascript'
    elif f.suffix=='.json':ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def add_target(pg,name):
    inp=pg.locator('#targetSkillPicker .search-select-input');inp.click();inp.fill(name);pg.wait_for_timeout(80)
    pg.locator('#targetSkillPicker .search-select-option').filter(has_text=name).first.click();pg.locator('#addTargetSkill').click()
errs=[];results=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    ctx=b.new_context(viewport={'width':1365,'height':950})
    ctx.add_init_script("""(()=>{const s={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])},configurable:true});})();""")
    pg=ctx.new_page();pg.route('http://app.local/**',handler)
    pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)));pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
    pg.set_content(HTML,wait_until='load',timeout=30000);pg.wait_for_function("document.querySelector('#targetSkillPicker .search-select-input')",timeout=30000)
    add_target(pg,'고급귀마개');pg.locator('#autoWeaponType').select_option(label='대검');pg.locator('#autoProgressionRank').select_option('g')
    for slot in range(4):
        pg.locator('#autoWeaponSlots').select_option(str(slot));st=time.perf_counter();pg.locator('#runSearch').click();pg.wait_for_function("!document.querySelector('#runSearch')?.disabled",timeout=30000);elapsed=time.perf_counter()-st
        cards=pg.locator('#searchResults .build-card-clickable').count();status=' '.join(pg.locator('#searchStats').inner_text().split())
        if cards<1: errs.append(f'{slot}slot:no cards:{status}')
        weapon=''
        if cards:
            weapon=' '.join(pg.locator('#searchResults .build-card-clickable').first.locator('.build-equipment span').nth(1).inner_text().split())
            expected='O'*slot+'-'*(3-slot)
            if expected not in weapon: errs.append(f'{slot}slot:weapon mismatch expected {expected}: {weapon}')
            pg.locator('#searchResults .build-card-clickable').first.click();pg.wait_for_timeout(100)
            manual_weapon=' '.join(pg.locator('#manual-weapon .search-select-input').input_value().split()) if pg.locator('#manual-weapon .search-select-input').count() else ''
            if manual_weapon and manual_weapon not in weapon: errs.append(f'{slot}slot:applied weapon mismatch:{manual_weapon} != {weapon}')
        if f'무기 슬롯 {slot} 고정' not in status: errs.append(f'{slot}slot:status missing fixed slot:{status}')
        results.append({'slot':slot,'cards':cards,'weapon':weapon,'elapsedSec':round(elapsed,2),'status':status})
    b.close()
report={'ok':not errs,'results':results,'errors':errs};OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
