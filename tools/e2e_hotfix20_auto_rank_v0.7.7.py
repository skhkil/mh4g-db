#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'hotfix20_auto_rank_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)

def handler(route):
    u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file():route.fulfill(status=404,body='not found',content_type='text/plain');return
    ctype=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js':ctype='text/javascript'
    elif f.suffix=='.json':ctype='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ctype)

def wait_ready(page):
    page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('스킬 시뮬레이터')",timeout=120000)
    page.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=120000)

def add_target(page,name):
    inp=page.locator('#targetSkillPicker .search-select-input')
    inp.click();inp.fill(name);page.wait_for_timeout(80)
    opt=page.locator('#targetSkillPicker .search-select-option').filter(has_text=name).first
    if opt.count()!=1:return False
    opt.click();page.locator('#addTargetSkill').click();page.wait_for_timeout(50);return True

def run_case(browser,cycle,viewport):
    errors=[];page=browser.new_page(viewport=viewport);page.route('http://app.local/**',handler)
    page.on('pageerror',lambda e:errors.append('pageerror:'+str(e)))
    page.on('console',lambda m:errors.append('console:'+m.text) if m.type=='error' else None)
    page.set_content(HTML,wait_until='load',timeout=120000);wait_ready(page)
    # progression UI
    opts=page.locator('#autoProgressionRank option').all_text_contents()
    if opts!=['하위','상위','G급']:errors.append('progression options mismatch:'+str(opts))
    if page.locator('#autoProgressionRank').input_value()!='g':errors.append('default progression is not G')
    # simulator armor picker shows individual resistances
    head=page.locator('#manual-head .search-select-input');head.click();head.fill('반역왕Ｊ해트');page.wait_for_timeout(120)
    option=page.locator('#manual-head .search-select-option').filter(has_text='반역왕Ｊ해트').first
    if option.count()!=1:errors.append('armor picker target missing')
    else:
        txt=' '.join(option.inner_text().split())
        for want in ['내성','화 -4','수 -4','뇌 -4','빙 -4','용 -4']:
            if want not in txt:errors.append('armor resistance display missing:'+want+' / '+txt)
        if viewport['width']<=420:
            box=option.bounding_box()
            if box and (box['x']< -1 or box['x']+box['width']>viewport['width']+1):errors.append('mobile armor option overflow')
        option.click();page.wait_for_timeout(80)
        summary=' '.join(page.locator('#manualResult .manual-loadout-summary').inner_text().split())
        for want in ['반역왕Ｊ해트','DEF 100','화 -4','용 -4']:
            if want not in summary:errors.append('selected armor resistance summary missing:'+want+' / '+summary[:500])
    page.keyboard.press('Escape')
    # automatic build scenario
    page.locator('#clearTargets').click()
    if not add_target(page,'세균연구가'):errors.append('failed to add 세균연구가')
    if not add_target(page,'명검'):errors.append('failed to add 명검')
    page.locator('#autoProgressionRank').select_option('g');page.locator('#resultLimit').select_option('10')
    page.locator('#runSearch').click();page.wait_for_function("document.querySelectorAll('#searchResults .build-card').length>0",timeout=120000)
    first=page.locator('#searchResults .build-card').first
    text=' '.join(first.inner_text().split())
    for want in ['반역왕Ｊ해트','리벨리언X메일','내성합']:
        if want not in text:errors.append('top auto build missing:'+want+' / '+text[:500])
    # exact resistance summary is visible in build calculation
    if not all(x in text for x in ['화 ','수 ','뇌 ','빙 ','용 ']):errors.append('build resistance detail missing')
    # card remains applicable to simulator
    first.click();page.wait_for_timeout(150)
    mtext=' '.join(page.locator('#manualResult').inner_text().split())
    if '방어력' not in mtext or '화 ' not in mtext or '용 ' not in mtext:errors.append('manual result resistance summary missing')
    st=page.locator('#appRuntimeStatus')
    if st.count() and not st.is_hidden():errors.append('runtime status visible:'+st.inner_text())
    page.close();return {'cycle':cycle,'viewport':viewport,'ok':not errors,'errors':errors}

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    runs=[]
    for i in range(3):runs.append(run_case(browser,i+1,{'width':1280,'height':900}))
    runs.append(run_case(browser,4,{'width':390,'height':844}))
    browser.close()
report={'version':'hotfix20','runs':runs,'ok':all(x['ok'] for x in runs)}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
