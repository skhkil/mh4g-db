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
        html=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1); pg.set_content(html,wait_until='load',timeout=120000); pg.wait_for_selector('#mainNav button[data-page="skill"]',timeout=30000)
        pg.click('#mainNav button[data-page="skill"]'); pg.wait_for_selector('#skillSearch',timeout=10000)
        pg.fill('#skillSearch','버섯마니아'); pg.wait_for_timeout(250)
        row=pg.locator('#skillTable tr.skill-db-row').first
        out['rows']=pg.locator('#skillTable tr.skill-db-row').count(); out['text']=row.inner_text()
        out['mushroomRows']=row.locator('.skill-effect-item').count()
        out['itemLinks']=row.locator('.skill-effect-item .inline-item-link').count()
        row.locator('.inline-item-link').first.click(); pg.wait_for_selector('#page-item.active',timeout=10000)
        out['openedItem']='푸른버섯' in pg.locator('#itemTable').inner_text()
        # footnotes removed, corrected strings searchable/rendered
        pg.click('#mainNav button[data-page="skill"]'); pg.fill('#skillSearch','주워먹기'); pg.wait_for_timeout(150)
        out['scavenger']='일정 확률' in pg.locator('#skillTable').inner_text()
        pg.fill('#skillSearch','흡입+2'); pg.wait_for_timeout(150)
        out['speedEating']='일반 소비 아이템' in pg.locator('#skillTable').inner_text()
        body=pg.locator('body').inner_text(); out['badChar']='�' in body
        out['errors']=errors
        b.close()
    out['ok']=out['rows']==1 and out['mushroomRows']==11 and out['itemLinks']==11 and out['openedItem'] and out['scavenger'] and out['speedEating'] and not out['badChar'] and not errors
    return out

res=[run(1365,900),run(390,844)]
out={'ok':all(x['ok'] for x in res),'runs':res}
(ROOT/'tools/step1_skill_notes_e2e_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
