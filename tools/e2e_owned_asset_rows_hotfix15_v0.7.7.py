#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'owned_asset_rows_hotfix15_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)

def handler(route):
    u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ct='text/javascript'
    elif f.suffix=='.json': ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)

errs=[]; rows=[]
seed_charms=[{'id':'t1','skills':{'skill_fd6b9f4f574f':10},'slots':0},{'id':'t2','skills':{'skill_2a9c189a93d7':5},'slots':2}]
seed_relic=[{'id':'r1','decorationId':'relic_weapon_skill_dfbf20468c93_1_2','skills':{'skill_dfbf20468c93':2},'slots':1}]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    for width in (984,390):
        ctx=b.new_context(viewport={'width':width,'height':900})
        ctx.add_init_script(f"""(()=>{{const s={{'mh4g-owned-charms-v1':{json.dumps(json.dumps(seed_charms))},'mh4g-owned-relic-weapons-v1':{json.dumps(json.dumps(seed_relic))}}};Object.defineProperty(window,'localStorage',{{value:{{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])}},configurable:true}});}})();""")
        pg=ctx.new_page(); pg.route('http://app.local/**',handler)
        pg.on('pageerror',lambda e,w=width:errs.append(f'{w}:pageerror:{e}'))
        pg.on('console',lambda m,w=width:errs.append(f'{w}:console:{m.text}') if m.type=='error' else None)
        pg.set_content(HTML,wait_until='load',timeout=30000)
        pg.wait_for_function("document.querySelector('#manualWeaponModeFilter') && document.querySelector('#ownedCharmList details')",timeout=30000)
        # Charm list: open and row-click apply; no Apply buttons.
        pg.locator('#ownedCharmList summary').click()
        if pg.locator('#ownedCharmList [data-owned-charm-apply]').count()!=0: errs.append(f'{width}:legacy charm apply button remains')
        charmrow=pg.locator('#ownedCharmList [data-owned-charm-row="0"]')
        label=' '.join(charmrow.locator('.owned-item-label').inner_text().split())
        if '가드강화 +10' not in label: errs.append(f'{width}:charm label missing:{label}')
        charmrow.locator('.owned-item-label').click(); pg.wait_for_timeout(80)
        if pg.locator('#charmPoint1').input_value()!='10': errs.append(f'{width}:charm row click did not apply')
        # Relic mode and save button layout/text.
        pg.locator('#manualWeaponModeFilter').select_option('relic'); pg.wait_for_timeout(120)
        btn=pg.locator('[data-save-owned-relic]')
        if btn.inner_text().strip()!='무기저장': errs.append(f'{width}:save button text:{btn.inner_text()!r}')
        box=btn.bounding_box()
        if not box or box['width'] < 60 or box['height'] > 50: errs.append(f'{width}:save button bad box:{box}')
        # Saved relic row click applies, only delete button remains.
        pg.locator('#ownedRelicWeaponList summary').click()
        if pg.locator('#ownedRelicWeaponList [data-owned-relic-apply]').count()!=0: errs.append(f'{width}:legacy relic apply button remains')
        rrow=pg.locator('#ownedRelicWeaponList [data-owned-relic-row="0"]')
        rlabel=' '.join(rrow.locator('.owned-item-label').inner_text().split())
        rrow.locator('.owned-item-label').click(); pg.wait_for_timeout(100)
        mode=pg.locator('#manualWeaponModeFilter').input_value(); slots=pg.locator('#manualWeaponSlotFilter').input_value()
        if mode!='relic' or slots!='1': errs.append(f'{width}:relic row click failed mode={mode} slots={slots}')
        # Delete must not trigger row apply, and leaves zero relics.
        pg.locator('#ownedRelicWeaponList summary').click() if not pg.locator('#ownedRelicWeaponList details').get_attribute('open') else None
        if pg.locator('#ownedRelicWeaponList [data-owned-relic-remove]').count():
            pg.locator('#ownedRelicWeaponList [data-owned-relic-remove]').click(); pg.wait_for_timeout(80)
            if pg.locator('#ownedRelicWeaponList [data-owned-relic-row]').count()!=0: errs.append(f'{width}:relic delete failed')
        # mobile/Desktop row layout must keep visible label and delete button.
        pg.locator('#ownedCharmList summary').click() if not pg.locator('#ownedCharmList details').get_attribute('open') else None
        crow=pg.locator('#ownedCharmList [data-owned-charm-row="0"]'); cbox=crow.bounding_box(); db= crow.locator('[data-owned-charm-remove]').bounding_box()
        if not cbox or not db or db['x']+db['width'] > cbox['x']+cbox['width']+1: errs.append(f'{width}:charm delete overflows row')
        rows.append({'width':width,'saveButtonBox':box,'charmLabel':label,'relicLabel':rlabel,'rowBox':cbox,'deleteBox':db})
        ctx.close()
    b.close()
report={'ok':not errs,'results':rows,'errors':errs}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
