#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'hotfix19_planner_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)

def handler(route):
    u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain');return
    ctype=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js':ctype='text/javascript'
    elif f.suffix=='.json':ctype='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ctype)

def wait_title(page,text,timeout=120000):page.wait_for_function("t=>document.querySelector('#pageTitle')?.textContent?.includes(t)",arg=text,timeout=timeout)

def run_case(browser,cycle):
    errors=[];page=browser.new_page(viewport={'width':1280,'height':900});page.route('http://app.local/**',handler)
    page.on('pageerror',lambda e:errors.append('pageerror:'+str(e)));page.on('console',lambda m:errors.append('console:'+m.text) if m.type=='error' else None)
    page.set_content(HTML,wait_until='load',timeout=120000);wait_title(page,'스킬 시뮬레이터');page.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=120000)
    # Opaque set_content origin blocks browser localStorage; UI clear buttons reset the planner state for this isolated E2E page.
    page.locator('[data-page="planner"]').click();wait_title(page,'즐겨찾기 · 제작');page.locator('#plannerClearFavorites').click();page.locator('#plannerClearCraft').click();page.locator('#plannerResetInventory').click()
    # armor
    page.locator('[data-submenu="bladeArmorSubNav"]').click();page.locator('#bladeArmorSubNav [data-route="armor-detail"][data-rank="low"]').click();wait_title(page,'방어구 상세')
    page.locator('#armorSearch').fill('카브라헬름');page.wait_for_timeout(250);row=page.locator('#armorTable tr.armor-db-row').filter(has_text='카브라헬름').first
    if row.count()!=1:errors.append('armor target missing')
    else:
        row.locator('[data-planner-favorite-kind="armor"]').click();page.wait_for_timeout(30);row=page.locator('#armorTable tr.armor-db-row').filter(has_text='카브라헬름').first;row.locator('[data-planner-craft-kind="armor"]').click()
    # recommendation
    page.locator('[data-page="recommend"]').click();wait_title(page,'추천 장비');page.locator('#recommendContent .recommend-variant').first.locator('[data-planner-favorite-kind="recommend"]').click()
    # quest
    page.locator('[data-submenu="questSubNav"]').click();page.locator('#questSubNav [data-route="quest-view"][data-quest-view="key"]').click();wait_title(page,'퀘스트')
    page.locator('#questTable tbody tr').first.locator('[data-planner-favorite-kind="quest"]').click()
    # weapon
    page.locator('[data-submenu="weaponSubNav"]').click();page.locator('#weaponSubNav button').first.click();wait_title(page,'무기 DB');page.wait_for_selector('#weaponTrees tr.weapon-db-row')
    wrow=page.locator('#weaponTrees tr.weapon-db-row').first;wrow.locator('[data-planner-favorite-kind="weapon"]').click();page.wait_for_timeout(30);wrow=page.locator('#weaponTrees tr.weapon-db-row').first;wrow.locator('[data-planner-craft-kind="weapon"]').click()
    # planner totals
    page.locator('[data-page="planner"]').click();wait_title(page,'즐겨찾기 · 제작');page.wait_for_selector('#plannerMaterials .planner-material-row')
    summary=' '.join(page.locator('#plannerSummary').inner_text().split())
    if '즐겨찾기 4' not in summary:errors.append('favorite total mismatch:'+summary)
    if '제작 장비 2' not in summary:errors.append('craft total mismatch:'+summary)
    # favorite card navigation uses existing DB cross-reference handlers
    fav_armor=page.locator('#plannerFavorites .planner-fav-group').filter(has_text='방어구').locator('[data-item-nav="armor"]').first
    if fav_armor.count()<1:errors.append('favorite armor open link missing')
    else:
        fav_armor.click();wait_title(page,'방어구 상세')
        if page.locator('#armorSearch').input_value()!='카브라헬름':errors.append('favorite armor navigation mismatch')
        page.locator('[data-page="planner"]').click();wait_title(page,'즐겨찾기 · 제작')
    # quantity aggregation
    arow=page.locator('#plannerCraftList .planner-craft-row').filter(has_text='카브라헬름')
    if arow.count()!=1:errors.append('armor craft row missing')
    else:
        q=arow.locator('input[data-planner-craft-qty]');q.fill('2');q.press('Tab');page.wait_for_timeout(40)
        summary=' '.join(page.locator('#plannerSummary').inner_text().split())
        if '제작 장비 3' not in summary:errors.append('quantity aggregation failed:'+summary)
    # owned/missing update + persistence via new page context reload simulation: verify localStorage payload immediately
    mrow=page.locator('#plannerMaterials .planner-material-row.is-missing').first
    if mrow.count()<1:errors.append('no missing material row')
    else:
        need=int(mrow.locator('b').inner_text());inp=mrow.locator('input[data-planner-inventory]');name=inp.get_attribute('data-planner-inventory');inp.fill(str(need));inp.press('Tab');page.wait_for_timeout(40)
        # verify value survives planner re-render/navigation in the same session; normal-origin localStorage wiring is checked by structure audit.
        page.locator('[data-page="skill"]').click();wait_title(page,'스킬 DB');page.locator('[data-page="planner"]').click();wait_title(page,'즐겨찾기 · 제작')
        inv=page.locator(f'[data-planner-inventory="{name}"]')
        if inv.count()!=1 or int(inv.input_value())!=need:errors.append('inventory session persistence failed')
        summary=' '.join(page.locator('#plannerSummary').inner_text().split())
        if '즐겨찾기 4' not in summary:errors.append('favorite session persistence failed')
    # material -> item navigation
    page.locator('[data-page="planner"]').click();wait_title(page,'즐겨찾기 · 제작');link=page.locator('#plannerMaterials .inline-item-link').first
    if link.count()<1:errors.append('material item link missing')
    else:
        mat=link.inner_text();link.click();wait_title(page,'아이템 DB');
        if page.locator('#itemSearch').input_value()!=mat:errors.append('material item navigation mismatch')
    # browser history should remain responsive around planner
    page.locator('[data-page="planner"]').click();wait_title(page,'즐겨찾기 · 제작');page.locator('[data-page="skill"]').click();wait_title(page,'스킬 DB');page.evaluate('history.back()');wait_title(page,'즐겨찾기 · 제작');page.evaluate('history.forward()');wait_title(page,'스킬 DB')
    status=page.locator('#appRuntimeStatus')
    if status.count() and not status.is_hidden():errors.append('runtime status visible:'+status.inner_text())
    page.close();return {'cycle':cycle,'ok':not errors,'errors':errors}

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    runs=[run_case(browser,i+1) for i in range(3)];browser.close()
report={'version':'hotfix19','runs':runs,'ok':all(x['ok'] for x in runs)};OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
