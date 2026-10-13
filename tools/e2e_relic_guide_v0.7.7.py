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
        pg.wait_for_selector('#weaponSubNav [data-special-page="relic-equipment"]',state='attached',timeout=30000)
        pg.click('.nav-group-toggle[data-submenu="weaponSubNav"]')
        pg.click('#weaponSubNav [data-special-page="relic-equipment"]')
        pg.wait_for_selector('#page-relic-equipment.active',timeout=30000)
        out['title']=pg.locator('#pageTitle').inner_text()
        out['allGroupCards']=pg.locator('.relic-group-card').count()
        pg.select_option('#relicMonsterFilter','라잔')
        pg.select_option('#relicWeaponTypeFilter','대검')
        pg.wait_for_timeout(100)
        txt=pg.locator('#relicEquipmentContent').inner_text()
        out['group9']='그룹 9' in txt and '라잔' in txt
        out['agito']='アギト' in txt
        out['silverSoulPool']='シルバーソル' in txt
        out['attackTable']=all(x in txt for x in ['240','340','1152','1632'])
        pg.fill('#relicAttackInput','1728'); pg.wait_for_timeout(50)
        out['attackInfer']='340 + 공격보정 20' in pg.locator('#relicAttackResult').inner_text()
        out['sourceLinks']=pg.locator('#relicEquipmentSources a').count()
        out['overflow']=pg.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth + 2')
        out['errors']=errors
        b.close()
    out['ok']=out['allGroupCards']==11 and out['group9'] and out['agito'] and out['silverSoulPool'] and out['attackTable'] and out['attackInfer'] and out['sourceLinks']>=4 and not out['overflow'] and not errors
    return out

res=[run(1365,900),run(390,844)]
out={'ok':all(x['ok'] for x in res),'runs':res}
(ROOT/'tools/relic_guide_e2e_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
