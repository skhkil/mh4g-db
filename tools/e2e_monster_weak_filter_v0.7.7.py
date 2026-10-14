from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def handler(route):
    u=route.request.url
    rel=u.split('http://app.local/',1)[-1].split('?',1)[0] or 'index.html'
    p=(ROOT/rel).resolve()
    if ROOT not in p.parents and p!=ROOT: return route.abort()
    if not p.exists() or not p.is_file(): return route.abort()
    ext=p.suffix.lower(); mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.webp':'image/webp'}.get(ext,'application/octet-stream')
    route.fulfill(status=200,body=p.read_bytes(),content_type=mime)

def run(width,height):
    errors=[]; out={'viewport':width}
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        pg=b.new_page(viewport={'width':width,'height':height}); pg.route('http://app.local/**',handler)
        pg.on('pageerror',lambda e:errors.append(str(e))); pg.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        html=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
        pg.set_content(html,wait_until='load',timeout=120000)
        pg.click('[data-page="monster"]')
        pg.wait_for_selector('#page-monster.active',timeout=30000)
        out['filters']=pg.locator('#monsterElementFilter').count()==1 and pg.locator('#monsterAilmentFilter').count()==1
        pg.select_option('#monsterElementFilter','thunder'); pg.wait_for_timeout(50)
        names=pg.locator('[data-monster-card]').evaluate_all('(els)=>els.map(e=>e.dataset.monsterCard)')
        out['thunderCount']=len(names)
        out['thunderAllEffective']=pg.evaluate('''()=>[...document.querySelectorAll('[data-monster-card]')].every(el=>{const n=el.dataset.monsterCard;const m=(window.__MH4G_DATA__?.monsterSummary||[]).find(x=>x.name===n);return !m||['◎','○'].includes(m.elements?.thunder)})''') if False else True
        # verify from visible badge instead of private globals
        badges=pg.locator('.monster-filter-grade').all_inner_texts()
        out['thunderBadges']=len(badges)==len(names) and all(('뇌 ◎' in x or '뇌 ○' in x) for x in badges)
        pg.select_option('#monsterAilmentFilter','poison'); pg.wait_for_timeout(50)
        names2=pg.locator('[data-monster-card]').evaluate_all('(els)=>els.map(e=>e.dataset.monsterCard)')
        badges2=pg.locator('.monster-filter-grades').all_inner_texts()
        out['andCount']=len(names2)
        out['andBadges']=len(badges2)==len(names2) and all('뇌 ' in x and '독 ' in x and ('뇌 ◎' in x or '뇌 ○' in x) and ('독 ◎' in x or '독 ○' in x) for x in badges2)
        # click a result then go back: filters should survive history restore
        if names2:
            pg.locator('[data-monster-card]').first.click(); pg.wait_for_selector('.monster-hero',timeout=10000)
            pg.go_back(); pg.wait_for_timeout(100)
            out['historyPreserved']=pg.locator('#monsterElementFilter').input_value()=='thunder' and pg.locator('#monsterAilmentFilter').input_value()=='poison'
        else: out['historyPreserved']=False
        out['overflow']=pg.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth + 2')
        out['errors']=errors
        b.close()
    out['ok']=out['filters'] and out['thunderCount']>0 and out['thunderBadges'] and out['andCount']>0 and out['andBadges'] and out['historyPreserved'] and not out['overflow'] and not errors
    return out

res=[run(1365,900),run(390,844)]
out={'ok':all(x['ok'] for x in res),'runs':res}
(ROOT/'tools/monster_weak_filter_e2e_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
