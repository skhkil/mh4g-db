#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'relic_sim_hotfix12_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)

def handler(route):
    u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ct='text/javascript'
    elif f.suffix=='.json': ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)

errs=[]; results=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    for width in (1365,390):
        ctx=b.new_context(viewport={'width':width,'height':1000})
        ctx.add_init_script("""(()=>{const s={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])},configurable:true});})();""")
        pg=ctx.new_page(); pg.route('http://app.local/**',handler)
        pg.on('pageerror',lambda e,w=width:errs.append(f'{w}:pageerror:'+str(e)))
        pg.on('console',lambda m,w=width:errs.append(f'{w}:console:'+m.text) if m.type=='error' else None)
        pg.set_content(HTML,wait_until='load',timeout=30000)
        pg.wait_for_function("document.querySelector('#targetSkillPicker .search-select-input') && document.querySelector('#manualWeaponModeFilter')",timeout=30000)

        # 1) 스킬 추가: 복합스킬 + 발굴 슬롯 필터
        pg.locator('#targetSkillTypeFilter').select_option('composite')
        pg.locator('#targetRelicSlotFilter').select_option('3')
        inp=pg.locator('#targetSkillPicker .search-select-input'); inp.click(); pg.wait_for_timeout(100)
        opts=pg.locator('#targetSkillPicker .search-select-option:not(.empty-option)')
        count=opts.count()
        if count<=0: errs.append(f'{width}:composite slot3 has no options')
        metas=[]
        for i in range(min(count,50)):
            txt=' '.join(opts.nth(i).inner_text().split()); metas.append(txt)
            if '발굴무기' not in txt or '3슬롯' not in txt: errs.append(f'{width}:slot3 option lacks relic metadata:{txt}')
        results.append({'width':width,'compositeSlot3Count':count,'sample':metas[:4]})
        pg.keyboard.press('Escape')

        # 2) 수동장비계산: 발굴무기 고정 + 정확 슬롯 복합 장식만
        pg.locator('#manualWeaponModeFilter').select_option('relic'); pg.wait_for_timeout(120)
        if not pg.locator('#manualWeaponTypeFilter').is_disabled(): errs.append(f'{width}:relic type filter not disabled')
        if not pg.locator('#manualWeaponRankFilter').is_disabled(): errs.append(f'{width}:relic rank filter not disabled')
        if not pg.locator('#manualWeaponElementFilter').is_disabled(): errs.append(f'{width}:relic element filter not disabled')
        weapon_inp=pg.locator('#manual-weapon .search-select-input')
        if weapon_inp.input_value().strip()!='발굴무기': errs.append(f'{width}:relic weapon not fixed:{weapon_inp.input_value()}')

        pg.locator('#manualWeaponSlotFilter').select_option('3'); pg.locator('#manualWeaponSearchButton').click(); pg.wait_for_timeout(120)
        deco_inp=pg.locator('#deco-picker-weapon .search-select-input'); deco_inp.click(); pg.wait_for_timeout(80)
        deco_opts=pg.locator('#deco-picker-weapon .search-select-option:not(.empty-option)')
        dcount=deco_opts.count(); dtexts=[]
        if dcount<=0: errs.append(f'{width}:relic slot3 decoration list empty')
        for i in range(dcount):
            t=' '.join(deco_opts.nth(i).inner_text().split()); dtexts.append(t)
            if '발굴무기 고정 복합장식' not in t: errs.append(f'{width}:normal decoration leaked:{t}')
            if '【3】' not in t: errs.append(f'{width}:non-slot3 relic decoration leaked:{t}')
        # 실제 도공 +5 고정 장식 선택
        target=None
        for i,t in enumerate(dtexts):
            if '발굴 도공주【3】 (+5)' in t: target=i; break
        if target is None: errs.append(f'{width}:missing edgemaster +5 relic jewel')
        else:
            pg.evaluate("document.querySelector('#deco-picker-weapon [data-value=\"relic_weapon_skill_0a0d7a1a0dde_3_5\"]')?.click()"); pg.wait_for_timeout(100)
            skilltxt=' '.join(pg.locator('#manualResult').inner_text().split())
            if '도공 +5' not in skilltxt: errs.append(f'{width}:relic skill point not applied:{skilltxt}')
        results[-1].update({'slot3DecorationCount':dcount,'slot3DecorationSample':dtexts[:5]})

        # 2-slot으로 변경 시 2-slot 고정 장식만 노출
        pg.locator('#manualWeaponSlotFilter').select_option('2'); pg.locator('#manualWeaponSearchButton').click(); pg.wait_for_timeout(100)
        # 기존 3슬롯 장식은 prune되어야 함
        if pg.locator('.weapon-card .deco-chip').count()!=0: errs.append(f'{width}:slot change did not prune incompatible relic decoration')
        pg.locator('#deco-picker-weapon .search-select-input').click(); pg.wait_for_timeout(80)
        d2=pg.locator('#deco-picker-weapon .search-select-option:not(.empty-option)')
        for i in range(d2.count()):
            t=' '.join(d2.nth(i).inner_text().split())
            if '【2】' not in t: errs.append(f'{width}:non-slot2 relic decoration leaked:{t}')
        pg.keyboard.press('Escape')

        # 제작무기로 되돌리면 기존 필터 활성화, 다수 제작무기 검색 유지
        pg.locator('#manualWeaponModeFilter').select_option('crafted'); pg.wait_for_timeout(120)
        if pg.locator('#manualWeaponTypeFilter').is_disabled(): errs.append(f'{width}:crafted type filter still disabled')
        pg.locator('#manualWeaponSearchButton').click(); pg.wait_for_timeout(80)
        winp=pg.locator('#manual-weapon .search-select-input'); winp.click(); pg.wait_for_timeout(60)
        crafted_count=pg.locator('#manual-weapon .search-select-option:not(.empty-option)').count()
        if crafted_count<=1: errs.append(f'{width}:crafted weapon search unexpectedly fixed:{crafted_count}')
        pg.keyboard.press('Escape')

        results[-1].update({'craftedWeaponOptions':crafted_count})
        ctx.close()
    b.close()
report={'ok':not errs,'results':results,'errors':errs}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
