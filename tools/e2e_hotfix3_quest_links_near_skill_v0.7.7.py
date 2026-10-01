#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'hotfix3_quest_links_near_skill_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)

def handler(route):
    u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
    if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain');return
    ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    if f.suffix=='.js': ct='text/javascript'
    elif f.suffix=='.json': ct='application/json'
    route.fulfill(status=200,body=f.read_bytes(),content_type=ct)

def add_target(pg,name):
    inp=pg.locator('#targetSkillPicker .search-select-input'); inp.click(); inp.fill(name); pg.wait_for_timeout(80)
    opt=pg.locator('#targetSkillPicker .search-select-option').filter(has_text=name).first
    if not opt.count(): return False
    opt.click(); pg.locator('#addTargetSkill').click(); return True

errs=[];facts={}
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    pg=b.new_page(viewport={'width':1365,'height':960});pg.route('http://app.local/**',handler)
    pg.on('pageerror',lambda e:errs.append('pageerror:'+str(e)))
    pg.on('console',lambda m:errs.append('console:'+m.text) if m.type=='error' else None)
    pg.set_content(HTML,wait_until='load',timeout=60000)
    pg.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=60000)

    # Quest target monster regression
    pg.locator('[data-route="quest-view"][data-quest-view="event-g"]').evaluate('e=>e.click()')
    pg.wait_for_function("document.querySelector('#page-quest').classList.contains('active')",timeout=15000)
    pg.locator('#questSearch').fill('나의 루비');pg.wait_for_timeout(150)
    row=pg.locator('#questTable tbody tr').first
    mons=[x.inner_text().strip() for x in row.locator('td.quest-monsters button').all()]
    facts['ruby_monsters']=mons
    if mons!=['바살모스 아종']: errs.append('Ruby target mismatch:'+repr(mons))

    # Normalization regressions on ordinary quests
    pg.locator('[data-route="quest-view"][data-quest-view="village-detail"]').evaluate('e=>e.click()');pg.wait_for_timeout(120)
    for qtext,want in [('중량급의 여제','게넬·셀타스'),('무리의 우두머리, 도스재기!','도스재기')]:
        pg.locator('#questSearch').fill(qtext);pg.wait_for_timeout(120)
        r=pg.locator('#questTable tbody tr').first
        got=[x.inner_text().strip() for x in r.locator('td.quest-monsters button').all()]
        facts[qtext]=got
        if want not in got: errs.append(f'{qtext}: missing {want}: {got}')

    # Festival Drum Music -> existing Korean item -> Hunter Master use
    pg.locator('[data-route="quest-view"][data-quest-view="event-g"]').evaluate('e=>e.click()');pg.wait_for_timeout(120)
    pg.locator('#questSearch').fill('태고의 달인: 배북 난타전');pg.wait_for_timeout(120)
    r=pg.locator('#questTable tbody tr').first
    reward_btn=r.locator('td.quest-rewards button').filter(has_text='태고의 악보').first
    if not reward_btn.count(): errs.append('Festival Drum Music did not link to 태고의 악보')
    else:
        reward_btn.click();pg.wait_for_timeout(200)
        pg.wait_for_function("document.querySelector('#page-item').classList.contains('active')",timeout=15000)
        detail=pg.locator('.item-detail-card').first
        if not detail.count(): errs.append('Festival item detail not opened')
        else:
            txt=' '.join(detail.inner_text().split());facts['festival_detail']=txt[:800]
            if '무기 생산/강화' not in txt: errs.append('Festival use group missing')
            d=detail.locator('details[data-xref-kind="use-weapon"]')
            if d.count(): d.locator('summary').click();pg.wait_for_timeout(100)
            if '수렵의 달인' not in ' '.join(detail.inner_text().split()): errs.append('Festival Hunter Master use missing')

    # E-can external Palico usage links
    pg.locator('[data-page="item"]').click() if pg.locator('[data-page="item"]').count() else None
    pg.wait_for_timeout(100)
    if pg.locator('#itemSearch').count():
        pg.locator('#itemSearch').fill('E캔');pg.wait_for_timeout(120)
        itemrow=pg.locator('#itemTable [data-item-id="item_ae0c44459ddc"]').first
        if itemrow.count(): itemrow.click();pg.wait_for_timeout(120)
        detail=pg.locator('.item-detail-card').first
        if not detail.count(): errs.append('E-can detail not found')
        else:
            ex=detail.locator('details[data-xref-kind="use-external"]')
            if not ex.count(): errs.append('E-can external use group missing')
            else:
                ex.locator('summary').click();pg.wait_for_timeout(100)
                links=ex.locator('a.xref-link'); labels=[x.inner_text().strip() for x in links.all()]
                facts['ecan_uses']=labels
                for want in ['러시 해머 (오토모 무기)','록맨 메트 (오토모 머리)','록맨 슈트 (오토모 몸통)']:
                    if want not in labels: errs.append('E-can use missing:'+want)

    # Simulator: undefined hidden, activated rows ahead of pending; near miss is applicable
    pg.locator('[data-page="simulator"]').click() if pg.locator('[data-page="simulator"]').count() else None
    pg.wait_for_function("document.querySelector('#page-simulator').classList.contains('active')",timeout=15000)
    pg.locator('#clearTargets').click()
    for name in ['고급귀마개','통찰력+3','회피성능+3','예리도레벨+1','공격력UP【초】']:
        if not add_target(pg,name): errs.append('target add failed:'+name)
    pg.locator('#autoProgressionRank').select_option('g')
    pg.locator('#runSearch').click();pg.wait_for_function("!document.querySelector('#runSearch')?.disabled",timeout=20000)
    body=' '.join(pg.locator('#searchResults').inner_text().split());facts['search_excerpt']=body[:1200]
    if 'undefined 발동' in body or 'undefined' in body: errs.append('undefined leaked into simulator result')
    near=pg.locator('#searchResults [data-auto-near]').first
    if not near.count(): errs.append('no near miss card to test transfer')
    else:
        head_name=near.locator('.build-equipment').inner_text().split('\n')[:4]
        facts['near_before']=head_name
        near.click();pg.wait_for_timeout(150)
        manual=' '.join(pg.locator('#manualResult').inner_text().split())
        facts['manual_after_near']=manual[:700]
        if len(manual)<200 or '방어력' not in manual: errs.append('near miss transfer appears empty')
        if 'undefined 발동' in manual: errs.append('undefined leaked after near transfer')
        cells=[x.inner_text().strip() for x in pg.locator('#manualResult .skill-points tbody tr td:nth-child(3)').all()]
        ranks=[2 if x.startswith('미발동') else 0 for x in cells]
        facts['skill_status_order']=cells[:20]
        if ranks!=sorted(ranks): errs.append('activated/pending skill row order regressed:'+repr(cells[:20]))
    b.close()

rep={'ok':not errs,'facts':facts,'errors':errs}
OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rep,ensure_ascii=False,indent=2));raise SystemExit(0 if rep['ok'] else 1)
