#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'armor_set_resist_hotfix10_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
sets=json.loads((ROOT/'data'/'sim_armor_sets.json').read_text(encoding='utf-8'))

def sort_expected(key):
    if key=='defense':
        return sorted(sets,key=lambda s:(-int(s.get('maxDefense') or s.get('defense') or 0),-int(s.get('defense') or 0),s.get('name','')))[0]
    return sorted(sets,key=lambda s:(-int((s.get('resistances') or {}).get(key,0)),-int(s.get('maxDefense') or s.get('defense') or 0),s.get('name','')))[0]

def handler(route):
    u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain');return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js':ct='text/javascript'
    elif f.suffix=='.json':ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)

errs=[];results=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    for width in (1365,390):
        ctx=b.new_context(viewport={'width':width,'height':900})
        ctx.add_init_script("""(()=>{const s={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])},configurable:true});})();""")
        pg=ctx.new_page();pg.route('http://app.local/**',handler)
        pg.on('pageerror',lambda e:errs.append(f'{width}:pageerror:'+str(e)))
        pg.on('console',lambda m:errs.append(f'{width}:console:'+m.text) if m.type=='error' else None)
        pg.set_content(HTML,wait_until='load',timeout=30000)
        pg.wait_for_function("document.querySelector('#armorSetPicker .search-select-input') && document.querySelector('#armorSetSort')",timeout=30000)
        for key in ('defense','fire','water','thunder','ice','dragon'):
            pg.locator('#armorSetSort').select_option(key)
            inp=pg.locator('#armorSetPicker .search-select-input');inp.click();pg.wait_for_timeout(60)
            first=pg.locator('#armorSetPicker .search-select-option:not(.empty-option)').first
            label=first.locator('.search-select-label').inner_text().strip();meta=' '.join(first.locator('small').inner_text().split())
            expected=sort_expected(key)
            if label!=expected['name']: errs.append(f'{width}:{key}:first {label} != {expected["name"]}')
            for token in ('방어','화 ','수 ','뇌 ','빙 ','용 ','슬롯'):
                if token not in meta: errs.append(f'{width}:{key}:meta missing {token}:{meta}')
            results.append({'width':width,'sort':key,'first':label,'meta':meta})
            pg.keyboard.press('Escape')
        # mobile/desktop layout should stay within viewport
        box=pg.locator('.compact-set-picker').bounding_box();sortbox=pg.locator('#armorSetSort').bounding_box()
        if box and sortbox and sortbox['x']+sortbox['width']>width+1: errs.append(f'{width}:sort overflow')
        ctx.close()
    b.close()
report={'ok':not errs,'results':results,'errors':errs}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
