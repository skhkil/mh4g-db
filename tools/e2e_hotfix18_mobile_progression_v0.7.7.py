#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'hotfix18_mobile_progression_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)

def handler(route):
    u=urllib.parse.urlparse(route.request.url)
    rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'
    f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file():
        route.fulfill(status=404,body='not found',content_type='text/plain');return
    ctype=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ctype='text/javascript'
    elif f.suffix=='.json': ctype='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ctype)

def wait_page(page,pid,timeout=60000):
    page.wait_for_function("p=>document.querySelector('#page-'+p)?.classList.contains('active')",arg=pid,timeout=timeout)

def run(browser):
    errs=[]; metrics={}
    page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    page.route('http://app.local/**',handler)
    page.on('pageerror',lambda e: errs.append('pageerror:'+str(e)))
    page.on('console',lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
    page.set_content(HTML,wait_until='load',timeout=120000)
    page.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=120000)
    # Open blade/high armor page from the actual menu.
    page.locator('[data-submenu="bladeArmorSubNav"]').click()
    page.locator('#bladeArmorSubNav [data-route="armor-detail"][data-rank="high"]').click()
    wait_page(page,'armor')
    page.locator('#armorSearch').fill('엠프러스메일'); page.wait_for_timeout(250)
    row=page.locator('#armorTable tr.armor-db-row').filter(has_text='엠프러스메일').first
    if row.count()!=1:
        errs.append('Empress row missing')
        page.close(); return {'ok':False,'errors':errs}
    row.click(); page.wait_for_timeout(250)
    detail=row.locator('xpath=following-sibling::tr[1]')
    page.wait_for_function("()=>document.querySelector('#armorTable .armor-detail-row:not([hidden]) .armor-progress-panel')!==null",timeout=30000)
    row_box=row.bounding_box(); detail_box=detail.locator('.armor-progress-panel').bounding_box()
    if not row_box or not detail_box or detail_box['width'] < row_box['width']*.94:
        errs.append(f'armor detail not full width row={row_box} detail={detail_box}')
    cards=detail.locator('.armor-progress-material')
    if cards.count()<2: errs.append('not enough material cards')
    else:
        a=cards.nth(0).bounding_box(); b=cards.nth(1).bounding_box()
        if not a or not b or b['x'] <= a['x']+20 or abs(b['y']-a['y'])>30:
            errs.append(f'material cards not using both columns: {a} {b}')
        metrics['materialCardX']=[round(a['x'],1) if a else None,round(b['x'],1) if b else None]
    # No-id MH4U reward quest must now be a clickable project-quest filter.
    qlink=detail.locator('[data-item-nav="questfilter"]').first
    if qlink.count()!=1:
        errs.append('questfilter link missing in armor progression')
    else:
        for i in range(8):
            if i:
                page.evaluate('history.forward()');wait_page(page,'quest');page.evaluate('history.back()');wait_page(page,'armor')
            # reopen if history restoration collapsed it
            if row.get_attribute('aria-expanded')!='true': row.click(); page.wait_for_timeout(100)
            qlink=detail.locator('[data-item-nav="questfilter"]').first
            qlink.click();wait_page(page,'quest')
            page.wait_for_timeout(120)
            if page.locator('#questTypeFilter').input_value() not in ('village','hub','g','event','challenge','all'):
                errs.append('invalid quest type filter')
            if page.locator('#questTable tbody tr').count()<1:
                errs.append(f'quest filter produced no rows cycle {i}')
            page.evaluate('history.back()');wait_page(page,'armor')
        metrics['questLinkCycles']=8
    st=page.locator('#appRuntimeStatus')
    if st.count() and not st.is_hidden(): errs.append('runtime status visible:'+st.inner_text())
    page.close();return {'ok':not errs,'errors':errs,'metrics':metrics}

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    report={'version':'hotfix18','mobileArmorQuest':run(browser)}
    browser.close()
report['ok']=report['mobileArmorQuest']['ok']
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
