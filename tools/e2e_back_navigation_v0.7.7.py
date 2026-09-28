#!/usr/bin/env python3
from pathlib import Path
import json, mimetypes, sys, time, urllib.parse
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'hotfix15_backnav_e2e_v0.7.7.json'
try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    OUT.write_text(json.dumps({'ok':False,'reason':'playwright unavailable','error':str(e)},ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(2)
html=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
errors=[]; timings=[]

def handler(route):
    u=urllib.parse.urlparse(route.request.url)
    rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'
    f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file():
        route.fulfill(status=404,body='not found'); return
    ctype=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ctype='text/javascript'
    elif f.suffix=='.json': ctype='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ctype)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1400,'height':1000})
    page.route('http://app.local/**',handler)
    page.on('pageerror',lambda e: errors.append('pageerror:'+str(e)))
    page.on('console',lambda m: errors.append('console:'+m.text) if m.type=='error' else None)
    page.set_content(html,wait_until='load',timeout=120000)
    page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('스킬 시뮬레이터')",timeout=120000)
    # Main regression path: recommendation -> simulator -> browser back, repeated.
    for i in range(15):
        t=time.perf_counter()
        if '추천 장비' not in page.locator('#pageTitle').inner_text():
            page.locator('[data-page="recommend"]').click()
            page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('추천 장비')",timeout=30000)
        page.locator('[data-recommend-sim]').first.click()
        page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('스킬 시뮬레이터')",timeout=30000)
        page.go_back(wait_until='commit',timeout=30000)
        page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('추천 장비')",timeout=30000)
        # Verify controls are still live after every restoration.
        page.locator('#recommendRank').select_option('high' if i%2 else 'low')
        page.locator('#recommendWeaponType').select_option('태도' if i%2 else '대검')
        page.wait_for_timeout(40)
        if page.locator('[data-recommend-sim]').count()<1:
            errors.append(f'cycle {i}: recommendation cards disappeared')
        timings.append(round((time.perf_counter()-t)*1000,2))
    # Route menu after repeated back operations.
    page.locator('[data-submenu="bladeArmorSubNav"]').click()
    page.locator('#bladeArmorSubNav [data-route="armor-detail"][data-rank="g"]').click()
    page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('방어구 상세')",timeout=30000)
    page.locator('#armorSearch').fill('예리도'); page.wait_for_timeout(250)
    armor_rows=page.locator('#armorTable tbody tr').count()
    page.go_back(wait_until='commit',timeout=30000)
    page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('추천 장비')",timeout=30000)
    page.go_forward(wait_until='commit',timeout=30000)
    page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('방어구 상세')",timeout=30000)
    page.locator('#armorPartFilter').select_option('head'); page.wait_for_timeout(150)
    head_rows=page.locator('#armorTable tbody tr').count()
    browser.close()

report={
    'ok':not errors and armor_rows>0 and head_rows>0,
    'cycles':15,
    'errors':errors,
    'timingMs':{'min':min(timings),'max':max(timings),'avg':round(sum(timings)/len(timings),2)},
    'armorRowsAfterBackNav':armor_rows,
    'headRowsAfterForwardNav':head_rows,
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
