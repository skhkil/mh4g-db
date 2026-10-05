#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'hotfix21_complex_search_e2e_v0.7.7.json'
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
    inp=page.locator('#targetSkillPicker .search-select-input');inp.click();inp.fill(name);page.wait_for_timeout(100)
    opt=page.locator('#targetSkillPicker .search-select-option').filter(has_text=name).first
    if opt.count()!=1:return False
    opt.click();page.locator('#addTargetSkill').click();page.wait_for_timeout(50);return True

def run_case(browser,cycle,viewport):
    errors=[];page=browser.new_page(viewport=viewport);page.route('http://app.local/**',handler)
    page.on('pageerror',lambda e:errors.append('pageerror:'+str(e)))
    page.on('console',lambda m:errors.append('console:'+m.text) if m.type=='error' else None)
    page.set_content(HTML,wait_until='load',timeout=120000);wait_ready(page)
    page.locator('#clearTargets').click()
    for name in ['고급귀마개','통찰력+1','회피성능+3','숫돌사용고속화']:
        if not add_target(page,name):errors.append('failed target:'+name)
    page.locator('#autoProgressionRank').select_option('g')
    page.evaluate("window.__hf21Ticks=0; window.__hf21Timer=setInterval(()=>window.__hf21Ticks++,25)")
    started=time.perf_counter();page.locator('#runSearch').click()
    page.wait_for_function("!document.querySelector('#runSearch')?.disabled",timeout=15000)
    elapsed=time.perf_counter()-started
    ticks=page.evaluate("clearInterval(window.__hf21Timer); window.__hf21Ticks")
    stats=' '.join(page.locator('#searchStats').inner_text().split())
    body=' '.join(page.locator('#searchResults').inner_text().split())
    if elapsed>10:errors.append(f'search too slow:{elapsed:.2f}s')
    if ticks<5:errors.append(f'ui did not yield enough:ticks={ticks}')
    if '고속 후보검색' not in stats:errors.append('search status missing approximate notice:'+stats)
    if '무기종 대검' not in stats or '무기 슬롯 0 고정' not in stats or '호석 슬롯 0' not in stats:errors.append('search condition summary missing:'+stats)
    exact=page.locator('#searchResults .build-card-clickable').count()
    near=page.locator('#searchResults .near-miss-card').count()
    if exact==0:
        if near<1:errors.append('no exact result and no near miss')
        for want in ['현재 조건에서 완성 조합을 찾지 못했습니다','회피성능','pt 부족','자동조합은 선택한 무기종·진행도·무기 슬롯 수를 고정해서 실제 무기를 함께 찾고']:
            if want not in body:errors.append('near miss guidance missing:'+want+' / '+body[:1000])
    if page.locator('#runSearch').is_disabled():errors.append('search button remained disabled')
    st=page.locator('#appRuntimeStatus')
    if st.count() and not st.is_hidden():errors.append('runtime status visible:'+st.inner_text())
    result={'cycle':cycle,'viewport':viewport,'elapsedSec':round(elapsed,2),'ticks':ticks,'exact':exact,'near':near,'stats':stats,'ok':not errors,'errors':errors}
    page.close();return result

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    runs=[run_case(browser,1,{'width':1280,'height':900}),run_case(browser,2,{'width':1280,'height':900}),run_case(browser,3,{'width':390,'height':844})]
    browser.close()
report={'version':'hotfix21','runs':runs,'ok':all(x['ok'] for x in runs)}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
