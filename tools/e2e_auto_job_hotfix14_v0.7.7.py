#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'auto_job_hotfix14_e2e_v0.7.7.json'
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
        ctx=b.new_context(viewport={'width':width,'height':1100})
        ctx.add_init_script("""(()=>{const s={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>k in s?s[k]:null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k],clear:()=>Object.keys(s).forEach(k=>delete s[k])},configurable:true});})();""")
        pg=ctx.new_page(); pg.route('http://app.local/**',handler)
        pg.on('pageerror',lambda e,w=width:errs.append(f'{w}:pageerror:'+str(e)))
        pg.on('console',lambda m,w=width:errs.append(f'{w}:console:'+m.text) if m.type=='error' else None)
        pg.set_content(HTML,wait_until='load',timeout=30000)
        pg.wait_for_function("document.querySelector('#targetSkillPicker .search-select-input') && document.querySelector('#autoHunterType')",timeout=30000)
        # control order: job should be immediately before progression
        order=pg.eval_on_selector_all('.compact-skill-options > label','els=>els.map(x=>x.textContent.trim().replace(/\\s+/g," "))')
        if len(order)<2 or not order[0].startswith('직업') or not order[1].startswith('진행도'): errs.append(f'{width}:control order wrong:{order[:3]}')
        # add a common skill
        inp=pg.locator('#targetSkillPicker .search-select-input'); inp.click(); inp.fill('고급귀마개'); pg.wait_for_timeout(80)
        opts=pg.locator('#targetSkillPicker .search-select-option:not(.empty-option)')
        if opts.count()==0:
            errs.append(f'{width}:target skill search empty')
            ctx.close(); continue
        # prefer exact label containing 고급귀마개
        idx=0
        for i in range(opts.count()):
            if '고급귀마개' in opts.nth(i).inner_text(): idx=i; break
        opts.nth(idx).click(); pg.locator('#addTargetSkill').click(); pg.wait_for_timeout(100)
        newinp=pg.locator('#targetSkillPicker .search-select-input')
        val=newinp.input_value()
        if val!='': errs.append(f'{width}:skill picker not cleared after add:{val!r}')
        chip=' '.join(pg.locator('#targetSkills').inner_text().split())
        if '고급귀마개' not in chip: errs.append(f'{width}:target not added:{chip}')
        row={'width':width,'pickerCleared':val=='','target':chip,'controlOrder':order[:3]}
        # search each profession; card labels must match selection
        for hunter,label in [('blade','검사'),('gunner','거너')]:
            pg.locator('#autoHunterType').select_option(hunter)
            pg.locator('#autoWeaponSlots').select_option('3')
            pg.locator('#runSearch').click()
            pg.wait_for_function("!document.querySelector('#runSearch').disabled",timeout=30000)
            cards=pg.locator('#searchResults .build-card')
            texts=[' '.join(cards.nth(i).locator('h3').inner_text().split()) for i in range(min(cards.count(),20))]
            if not texts: errs.append(f'{width}:{hunter}:no complete result cards')
            bad=[t for t in texts if label not in t or (hunter=='blade' and '거너' in t) or (hunter=='gunner' and '검사' in t)]
            if bad: errs.append(f'{width}:{hunter}:mixed profession cards:{bad[:3]}')
            stats=' '.join(pg.locator('#searchStats').inner_text().split())
            if label not in stats: errs.append(f'{width}:{hunter}:stats missing profession:{stats}')
            row[hunter]={'cards':len(texts),'sample':texts[:2],'stats':stats}
        results.append(row); ctx.close()
    b.close()
report={'ok':not errs,'results':results,'errors':errs}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
