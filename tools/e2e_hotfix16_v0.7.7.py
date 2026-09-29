#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,time,urllib.parse
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools/hotfix16_e2e_v0.7.7.json'
from playwright.sync_api import sync_playwright
html=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
errors=[]; metrics={}
def handler(route):
    u=urllib.parse.urlparse(route.request.url)
    rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'
    f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file():
        route.fulfill(status=404,body='not found');return
    ctype=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ctype='text/javascript'
    elif f.suffix=='.json': ctype='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ctype)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.route('http://app.local/**',handler)
    page.on('pageerror',lambda e: errors.append('pageerror:'+str(e)))
    page.on('console',lambda m: errors.append('console:'+m.text) if m.type=='error' else None)
    t0=time.perf_counter();page.set_content(html,wait_until='load',timeout=120000)
    page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('스킬 시뮬레이터')",timeout=120000)
    metrics['initialLoadMs']=round((time.perf_counter()-t0)*1000,2)
    # Existing repeated navigation regression: recommendation -> simulator -> back.
    for i in range(15):
        if '추천 장비' not in page.locator('#pageTitle').inner_text():
            page.locator('[data-page="recommend"]').click();page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('추천 장비')",timeout=30000)
        page.locator('[data-recommend-sim]').first.click();page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('스킬 시뮬레이터')",timeout=30000)
        page.go_back(wait_until='commit',timeout=30000);page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('추천 장비')",timeout=30000)
        page.locator('#recommendRank').select_option('high' if i%2 else 'low');page.wait_for_timeout(20)
        if page.locator('[data-recommend-sim]').count()<1: errors.append(f'nav cycle {i}: controls dead')
    # Open armor DB and test row-click detail UX on Empress.
    page.locator('[data-submenu="bladeArmorSubNav"]').click()
    page.locator('#bladeArmorSubNav [data-route="armor-detail"][data-rank="high"]').click()
    page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('방어구 상세')",timeout=30000)
    t1=time.perf_counter();page.locator('#armorSearch').fill('엠프러스메일');page.wait_for_timeout(220);metrics['armorSearchMs']=round((time.perf_counter()-t1)*1000,2)
    row=page.locator('#armorTable tr.armor-db-row').filter(has_text='엠프러스메일').first
    if row.count()!=1: errors.append('Empress row not found')
    else:
        # Click ordinary cell, not the old text link.
        row.locator('td').nth(1).click()
        detail=row.locator('xpath=following-sibling::tr[1]')
        page.wait_for_timeout(120)
        if detail.get_attribute('hidden') is not None: errors.append('armor detail did not open by row click')
        txt=detail.inner_text()
        for required in ['엠프러스메일 제작 진행','교환 재료','창화룡 날개','염비룡 갈기','고난도: 광기 어린 흑굉룡']:
            if required not in txt: errors.append('missing detail text: '+required)
        # Close/open repeatedly to ensure no duplicate fetch/event lock.
        for j in range(8):
            row.locator('td').nth(1).click();page.wait_for_timeout(10)
            row.locator('td').nth(1).click();page.wait_for_timeout(10)
        if detail.get_attribute('hidden') is not None: errors.append('detail did not remain open after repeat toggle')
    # Search still responsive after detail toggles.
    page.locator('#armorSearch').fill('몸통배가');page.wait_for_timeout(220)
    if page.locator('#armorTable tr.armor-db-row').count()<1: errors.append('armor search dead after detail toggle')
    # Back/forward after armor detail workflow and re-use controls.
    page.go_back(wait_until='commit',timeout=30000);page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('추천 장비')",timeout=30000)
    page.go_forward(wait_until='commit',timeout=30000);page.wait_for_function("document.querySelector('#pageTitle')?.textContent?.includes('방어구 상세')",timeout=30000)
    page.locator('#armorSearch').fill('예리도');page.wait_for_timeout(220)
    if page.locator('#armorTable tr.armor-db-row').count()<1: errors.append('armor search dead after forward')
    browser.close()
report={'ok':not errors,'errors':errors,'metrics':metrics,'cycles':15}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
