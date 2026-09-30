#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tools'/'hotfix19_planner_mobile_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
 u=urllib.parse.urlparse(route.request.url);rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html';f=(ROOT/rel).resolve()
 if not str(f).startswith(str(ROOT)) or not f.is_file():route.fulfill(status=404,body='not found');return
 ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
 if f.suffix=='.js':ct='text/javascript'
 elif f.suffix=='.json':ct='application/json'
 route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def wait(page,t):page.wait_for_function("x=>document.querySelector('#pageTitle')?.textContent?.includes(x)",arg=t,timeout=120000)
errs=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage']);pg=b.new_page(viewport={'width':390,'height':844});pg.route('http://app.local/**',handler);pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None)
 pg.set_content(HTML,wait_until='load',timeout=120000);wait(pg,'스킬 시뮬레이터');pg.locator('[data-page="planner"]').click();wait(pg,'즐겨찾기 · 제작');pg.locator('#plannerClearFavorites').click();pg.locator('#plannerClearCraft').click()
 pg.locator('[data-submenu="bladeArmorSubNav"]').click();pg.locator('#bladeArmorSubNav [data-route="armor-detail"][data-rank="low"]').click();wait(pg,'방어구 상세');pg.locator('#armorSearch').fill('카브라헬름');pg.wait_for_timeout(250);row=pg.locator('#armorTable tr.armor-db-row').filter(has_text='카브라헬름').first;row.locator('[data-planner-craft-kind="armor"]').click();row=pg.locator('#armorTable tr.armor-db-row').filter(has_text='카브라헬름').first;row.locator('[data-planner-favorite-kind="armor"]').click()
 pg.locator('[data-page="planner"]').click();wait(pg,'즐겨찾기 · 제작');pg.wait_for_selector('#plannerMaterials .planner-material-row')
 metrics=pg.evaluate("""()=>({vw:innerWidth,doc:document.documentElement.scrollWidth,material:document.querySelector('#plannerMaterials')?.getBoundingClientRect().toJSON(),card:document.querySelector('.planner-craft-row')?.getBoundingClientRect().toJSON(),buttons:[...document.querySelectorAll('.planner-inline-action')].slice(0,2).map(x=>x.getBoundingClientRect().toJSON())})""")
 if metrics['doc']>metrics['vw']+2:errs.append(f"horizontal overflow {metrics['doc']} > {metrics['vw']}")
 if not metrics['material'] or metrics['material']['right']>metrics['vw']+1:errs.append('materials exceed viewport')
 if not metrics['card'] or metrics['card']['right']>metrics['vw']+1:errs.append('craft card exceeds viewport')
 b.close()
report={'version':'hotfix19','ok':not errs,'errors':errs,'metrics':metrics};OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
