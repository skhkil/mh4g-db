#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
OUT=ROOT/'tools'/'charm_layout_hotfix_e2e_v0.7.7.json'
def handler(route):
    u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ct='text/javascript'
    elif f.suffix=='.json': ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def check(pg,w,h,touch=False):
    pg.set_viewport_size({'width':w,'height':h})
    pg.set_content(HTML,wait_until='load',timeout=30000)
    pg.wait_for_function("document.querySelector('#charmSkill1Picker .search-select-input')",timeout=30000)
    sels=['.manual-charm-inline .inline-field-label:nth-of-type(1)','#charmSkill1Picker','#charmPoint1','.manual-charm-inline .inline-field-label:nth-of-type(2)','#charmSkill2Picker','#charmPoint2','.manual-charm-inline .inline-field-label:nth-of-type(3)','#charmSlots']
    boxes=[pg.locator(s).bounding_box() for s in sels]
    ys=[round(b['y']+b['height']/2,1) for b in boxes if b]
    groups=[]
    for y in sorted(ys):
        if not groups or abs(y-groups[-1][-1])>12: groups.append([y])
        else: groups[-1].append(y)
    rows=len(groups)
    controls=pg.locator('.owned-charm-controls').bounding_box()
    return {'width':w,'rows':rows,'ys':ys,'controlsWidth':round(controls['width'],1) if controls else None}
errs=[];facts=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    for w,h in [(1365,960),(900,900),(390,844)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=(w<1000))
        ctx.add_init_script("""(()=>{const s={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])},configurable:true});})();""")
        pg=ctx.new_page(); pg.route('http://app.local/**',handler)
        r=check(pg,w,h); facts.append(r)
        if w>=641 and r['rows']>2: errs.append(f'{w}px charm editor should stay horizontal, rows={r["rows"]}')
        if w<641 and not (2<=r['rows']<=4): errs.append(f'{w}px charm editor should collapse compactly, rows={r["rows"]}')
        ctx.close()
    b.close()
report={'ok':not errs,'facts':facts,'errors':errs}; OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2)); raise SystemExit(0 if report['ok'] else 1)
