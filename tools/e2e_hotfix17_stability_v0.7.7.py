#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,time,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'hotfix17_stability_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)

def make_handler(fail_suffix=None):
    def handler(route):
        u=urllib.parse.urlparse(route.request.url)
        rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'
        if fail_suffix and rel.endswith(fail_suffix):
            route.fulfill(status=503,body='temporary unavailable',content_type='text/plain');return
        f=(ROOT/rel).resolve()
        if not str(f).startswith(str(ROOT)) or not f.is_file():
            route.fulfill(status=404,body='not found');return
        ctype=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
        if f.suffix=='.js': ctype='text/javascript'
        elif f.suffix=='.json': ctype='application/json'
        route.fulfill(status=200,body=f.read_bytes(),content_type=ctype)
    return handler

def wait_title(page,text,timeout=30000):
    page.wait_for_function("t=>document.querySelector('#pageTitle')?.textContent?.includes(t)",arg=text,timeout=timeout)

def normal_case(browser):
    errs=[];metrics={}
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.route('http://app.local/**',make_handler())
    page.on('pageerror',lambda e: errs.append('pageerror:'+str(e)))
    page.on('console',lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
    t=time.perf_counter();page.set_content(HTML,wait_until='load',timeout=120000);wait_title(page,'스킬 시뮬레이터',120000)
    page.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=120000)
    metrics['initialMs']=round((time.perf_counter()-t)*1000,2)
    for i in range(25):
        if '추천 장비' not in page.locator('#pageTitle').inner_text():
            page.locator('[data-page="recommend"]').click();wait_title(page,'추천 장비')
        page.locator('#recommendRank').select_option(['low','high','g'][i%3])
        page.locator('#recommendWeaponType').select_option(['대검','태도','랜스'][i%3])
        if page.locator('[data-recommend-sim]').count()<1:
            errs.append(f'cycle {i}: no recommendation card');break
        page.locator('[data-recommend-sim]').first.click();wait_title(page,'스킬 시뮬레이터')
        page.evaluate('history.back()');wait_title(page,'추천 장비')
        page.locator('#recommendRank').select_option(['g','high','low'][i%3]);page.wait_for_timeout(15)
        if page.locator('[data-recommend-sim]').count()<1:errs.append(f'cycle {i}: dead after back')
    page.locator('[data-submenu="bladeArmorSubNav"]').click()
    page.locator('#bladeArmorSubNav [data-route="armor-detail"][data-rank="high"]').click();wait_title(page,'방어구 상세')
    page.locator('#armorSearch').fill('엠프러스메일');page.wait_for_timeout(250)
    row=page.locator('#armorTable tr.armor-db-row').filter(has_text='엠프러스메일').first
    if row.count()!=1:errs.append('Empress row missing')
    else:
        detail=row.locator('xpath=following-sibling::tr[1]')
        for _ in range(12):
            row.locator('td').nth(1).click();page.wait_for_timeout(15)
            row.locator('td').nth(1).click();page.wait_for_timeout(15)
        row.locator('td').nth(1).click();page.wait_for_timeout(100)
        if detail.get_attribute('hidden') is not None:errs.append('armor detail open failed')
        txt=detail.inner_text()
        for want in ['엠프러스메일 제작 진행','교환 재료','염비룡 갈기']:
            if want not in txt:errs.append('missing detail:'+want)
    page.evaluate("const x=document.querySelector('#rankFilter');x.value='all';x.dispatchEvent(new Event('change',{bubbles:true}));");page.wait_for_timeout(80)
    for q in ['예리도','몸통배가','GX']:
        page.locator('#armorSearch').fill(q);page.wait_for_timeout(180)
        if page.locator('#armorTable tr.armor-db-row').count()<1:errs.append('search dead:'+q)
    for i in range(10):
        page.locator('[data-page="recommend"]').click();wait_title(page,'추천 장비')
        page.locator('[data-page="skill"]').click();wait_title(page,'스킬 DB')
        page.evaluate('history.back()');wait_title(page,'추천 장비')
        page.evaluate('history.forward()');wait_title(page,'스킬 DB')
        page.locator('#skillSearch').fill('장인' if i%2 else '예리도');page.wait_for_timeout(20)
    st=page.locator('#appRuntimeStatus')
    if st.count() and not st.is_hidden():errs.append('status visible:'+st.inner_text())
    page.close();return {'ok':not errs,'errors':errs,'metrics':metrics,'recommendBackCycles':25,'armorToggleCycles':12,'backForwardCycles':10}

def missing_ui_case(browser):
    errs=[]
    page=browser.new_page(viewport={'width':1200,'height':800});page.route('http://app.local/**',make_handler())
    html=HTML.replace('<input id="jsonImport"','<input id="jsonImportRemoved"',1)
    page.set_content(html,wait_until='load',timeout=120000);wait_title(page,'스킬 시뮬레이터',120000);page.wait_for_timeout(150)
    page.locator('[data-page="recommend"]').click();wait_title(page,'추천 장비')
    page.locator('[data-page="skill"]').click();wait_title(page,'스킬 DB')
    st=page.locator('#appRuntimeStatus')
    if st.count()==0 or st.is_hidden():errs.append('expected isolated binding warning missing')
    page.close();return {'ok':not errs,'errors':errs}

def data_failure_case(browser):
    errs=[]
    page=browser.new_page(viewport={'width':1200,'height':800});page.route('http://app.local/**',make_handler('data/sim_armors.json'))
    page.set_content(HTML,wait_until='load',timeout=120000);wait_title(page,'스킬 시뮬레이터',120000);page.wait_for_timeout(500)
    page.locator('[data-page="recommend"]').click();wait_title(page,'추천 장비')
    page.locator('[data-page="skill"]').click();wait_title(page,'스킬 DB')
    st=page.locator('#appRuntimeStatus')
    if st.count()==0 or st.is_hidden():errs.append('expected data load warning missing')
    page.close();return {'ok':not errs,'errors':errs}

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    report={'version':'hotfix17','normal':normal_case(browser),'missingUiIsolation':missing_ui_case(browser),'dataFailureIsolation':data_failure_case(browser)}
    browser.close()
report['ok']=all(v.get('ok',True) for v in report.values() if isinstance(v,dict))
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
